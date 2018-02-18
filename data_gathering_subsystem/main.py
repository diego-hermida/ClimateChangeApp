import builtins
from os import environ
from queue import Queue
from data_gathering_subsystem.data_collector.data_collector import DataCollectorThread, Message, MessageType
from data_gathering_subsystem.config.config import DGS_CONFIG
from data_gathering_subsystem.supervisor.supervisor import SupervisorThread
from timeit import default_timer as timer
from threading import Condition
from utilities.db_util import ping_database, get_and_increment_execution_id
from utilities.log_util import get_logger
from utilities.import_dir import import_modules
from utilities.util import time_limit

__logger = None


def main(log_to_file=True, log_to_stdout=True):
    """
        This function is the entry point to the Data Gathering Subsystem.
        Imports all DataCollectors, generates and sets up Supervisor, waits until all work has been done, and exits.
        A timeout is set, just in case a deadlock occurs.
        :raise TimeoutError: If the timeout is reached.
    """
    global __logger

    # Measuring total execution time
    start_time = timer()
    builtins.EXECUTION_ID = None

    # Getting logger instance
    __logger = get_logger(__file__, 'MainLogger', to_stdout=log_to_stdout, to_file=log_to_file, subsystem_id=
            DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'])

    # This provisional solution FIXES [BUG-015]
    if environ.get('LOCALHOST_IP') is None:
        __logger.critical('LOCALHOST_IP must exist as an ENVIRONMENT VARIABLE at execution time. Aborting Subsystem.')
        exit(1)
    else:
        __logger.debug('Environment variable LOCALHOST_IP found, with value: "%s". To override it, use --env '
                       'LOCALHOST_IP=<IP> when invoking "docker run".' % (environ.get('LOCALHOST_IP')))

    # Pinging database before any other operation.
    try:
        ping_database()
        builtins.EXECUTION_ID = get_and_increment_execution_id()
        __logger = get_logger(__file__, 'MainLogger', to_stdout=log_to_stdout, to_file=log_to_file, subsystem_id=
                DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'])
        __logger.debug('MongoDB daemon is up and reachable.')
    except EnvironmentError:
        __logger.critical('The MongoDB server is down. The Subsystem will be exit now, since it\'s useless to collect '
                          'data for not being able to save them.')
        exit(1)

    if builtins.EXECUTION_ID is not None:
        __logger.info('Starting Data Gathering Subsystem. Execution ID is: %d' % (builtins.EXECUTION_ID))
    else:
        __logger.warning('Starting Data Gathering Subsystem. Execution ID is unknown. This may difficult debug operations.')

    # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
    modules = import_modules(DGS_CONFIG['DATA_MODULES_PATH'], recursive=True,
            base_package=DGS_CONFIG['DATA_COLLECTOR_BASE_PACKAGE'])
    if not modules:
        __logger.critical('Data modules could not be instantiated. Aborting Data Gathering Subsystem.')
        exit(1)
    if len(modules) > DGS_CONFIG['MAX_RECOMMENDED_DATA_COLLECTORS']:
        __logger.warning('The number of DataCollector modules (%d) exceeds the recommended amount: %d. This may lead '
                'into performance penalties.'%(len(modules), DGS_CONFIG['MAX_RECOMMENDED_DATA_COLLECTORS']))

    # Enabling a channel to pass messages between DataCollectors and Supervisor.
    channel = Queue(maxsize=(len(modules) * 2) + 2)
    condition = Condition()
    __logger.debug('Created shared channel for message passing, with length %d.'%(channel.maxsize))

    # Creating an starting Supervisor
    supervisor = SupervisorThread(channel, condition, log_to_file=log_to_file, log_to_stdout=log_to_stdout)
    supervisor.start()
    __logger.debug('Created Supervisor and started supervision.')

    # Creates a Thread per DataCollector, and starts them.
    threads = []
    for module in modules:
        thread = DataCollectorThread(module, channel, condition, log_to_file=log_to_file, log_to_stdout=log_to_stdout)
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
    __logger.info('Data Gathering Subsystem has finished its execution. Total elapsed time is %d h, %d min and %d s.'%
            (h, m, s))


if __name__ == '__main__':
    try:
        with time_limit(DGS_CONFIG['SUBSYSTEM_TIMEOUT']):
            main()
    except TimeoutError:
        __logger.critical('The Subsystem execution has been timed out. This error should be revised, since the causes '
                'might be:\n\t1. A deadlock (or, in general a concurrency error) has occurred. Timeout: OK'
                '\n\t2. The Subsystem was performing actual work. Timeout: BAD\n')
    except Exception:
        __logger.exception('An unexpected error occurred while executing the Subsystem.')
        exit(1)