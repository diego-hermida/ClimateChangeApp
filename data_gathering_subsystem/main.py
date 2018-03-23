import builtins

from os import environ
from queue import Queue
from threading import Condition
from timeit import default_timer as timer

from data_gathering_subsystem.config.config import DGS_CONFIG
from data_gathering_subsystem.supervisor.supervisor import DataCollectorSupervisor
from global_config.config import GLOBAL_CONFIG
from utilities.execution_util import Message, MessageType, RunnableComponentThread, SupervisorThreadRunner
from utilities.import_dir import import_modules
from utilities.log_util import get_logger
from utilities.mongo_util import get_and_increment_execution_id, ping_database
from utilities.util import time_limit

_logger = None


def main(log_to_file=True, log_to_stdout=True, log_to_telegram=None):
    """
        This function is the entry point to the Data Gathering Subsystem.
        Imports all DataCollectors, generates and sets up Supervisor, waits until all work has been done, and exits.
        A timeout is set, just in case a deadlock occurs.
        :raise TimeoutError: If the timeout is reached.
    """
    global _logger

    # Measuring total execution time
    start_time = timer()
    builtins.EXECUTION_ID = None

    # Getting logger instance
    _logger = get_logger(__file__, 'MainLogger', to_stdout=log_to_stdout, to_file=log_to_file,
                         subsystem_id=DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], component=DGS_CONFIG['COMPONENT'],
                         to_telegram=log_to_telegram,
                         root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'])

    # This provisional solution FIXES [BUG-015]
    if environ.get('MONGODB_IP') is None:
        _logger.critical('MONGODB_IP must exist as an ENVIRONMENT VARIABLE at execution time. Aborting Subsystem.')
        exit(1)
    else:
        _logger.debug('Environment variable MONGODB_IP found, with value: "%s". To override it, use --env '
                      'MONGODB_IP=<IP> when invoking "docker run".' % environ.get('MONGODB_IP'))

    # Pinging database before any other operation.
    try:
        ping_database()
        builtins.EXECUTION_ID = get_and_increment_execution_id(DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'])
        _logger = get_logger(__file__, 'MainLogger', to_stdout=log_to_stdout, to_file=log_to_file,
                             subsystem_id=DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], component=DGS_CONFIG['COMPONENT'],
                             root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'],
                             to_telegram=log_to_telegram)
        _logger.debug('MongoDB daemon is up and reachable.')
    except EnvironmentError:
        _logger.critical('The MongoDB server is down. The Subsystem will exit now, since it\'s useless to collect '
                         'data for not being able to save them.', exc_info=True)
        exit(1)

    if builtins.EXECUTION_ID is not None:
        _logger.info('Starting Data Gathering Subsystem. Execution ID is: %d' % builtins.EXECUTION_ID)
    else:
        _logger.warning(
                'Starting Data Gathering Subsystem. Execution ID is unknown. This may difficult debug operations.')

    # Displaying version
    _logger.info('Data Gathering Subsystem\'s version is: %s' % GLOBAL_CONFIG['APP_VERSION'])

    # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
    modules = import_modules(DGS_CONFIG['DATA_MODULES_PATH'], recursive=True,
                             base_package=DGS_CONFIG['DATA_COLLECTOR_BASE_PACKAGE'])
    if not modules:
        _logger.critical('Data modules could not be instantiated. Aborting Data Gathering Subsystem.')
        exit(1)
    if len(modules) > DGS_CONFIG['MAX_RECOMMENDED_DATA_COLLECTORS']:
        _logger.warning('The number of DataCollector modules (%d) exceeds the recommended amount: %d. This may lead '
                        'into performance penalties.' % (len(modules), DGS_CONFIG['MAX_RECOMMENDED_DATA_COLLECTORS']))

    # Enabling a channel to pass messages between DataCollectors and Supervisor.
    channel = Queue(maxsize=(len(modules) * 2) + 2)
    condition = Condition()
    _logger.debug('Created shared channel for message passing, with length %d.' % channel.maxsize)

    # Creating an starting Supervisor
    s = DataCollectorSupervisor(channel, condition, log_to_file, log_to_stdout, log_to_telegram)
    supervisor = SupervisorThreadRunner(s)
    supervisor.start()
    _logger.debug('Created Supervisor and started supervision.')

    # Creates a Thread per DataCollector, and starts them.
    threads = []
    for module in modules:
        runnable = module.instance(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                   log_to_telegram=log_to_telegram)
        thread = RunnableComponentThread(runnable, channel=channel, condition=condition)
        threads.append(thread)
        thread.start()
    # Waits until all DataCollectors have finished execution.
    for thread in threads:
        thread.join()

    # When all DataCollectors have finished execution, Supervisor is able to generate an execution report.
    time = timer() - start_time
    Message(MessageType.report, content=time).send(channel, condition)

    # Once Supervisor has generated its report, it can exit.
    Message(MessageType.exit).send(channel, condition)
    supervisor.join()

    # Logging total execution time (which is report time + report generation time + Supervisor's thread join)
    m, s = divmod(timer() - start_time, 60)
    h, m = divmod(m, 60)
    _logger.info('Data Gathering Subsystem has finished its execution. Total elapsed time is %d h, %d min and %d s.' %
                 (h, m, s))


if __name__ == '__main__':
    try:
        with time_limit(DGS_CONFIG['SUBSYSTEM_TIMEOUT']):
            main(log_to_stdout=True, log_to_file=True, log_to_telegram=None)
    except TimeoutError:
        _logger.critical('The Subsystem execution has been timed out. This error should be revised, since the causes '
                         'might be:\n\t1. A deadlock (or, in general a concurrency error) has occurred. Timeout: OK'
                         '\n\t2. The Subsystem was performing actual work. Timeout: BAD\n')
    except Exception:
        _logger.exception('An unexpected error occurred while executing the Subsystem.')
        exit(1)
