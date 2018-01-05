from data_collector.data_collector import DataCollectorThread, Message, MessageType
from global_config.global_config import CONFIG
from supervisor.supervisor import SupervisorThread
from os import environ
from queue import Queue
from sys import exit
from timeit import default_timer as timer
from threading import Condition
from utilities.import_dir import import_modules
from utilities.log_util import get_logger


__condition = Condition()
__channel = None


if __name__ == '__main__':

    # Measuring total execution time
    start_time = timer()

    # Getting logger instance
    logger = get_logger(__file__, 'MainLogger', to_stdout=True, to_file=True)
    logger.info('Starting Data Gathering Subsystem.')

    # Provisional solution to [BUG-015]
    if not environ.get('LOCALHOST_IP', False):
        logger.critical('LOCALHOST_IP must exist as an ENVIRONMENT VARIABLE at execution time. Aborting Subsystem.')
        exit(1)
    else:
        logger.info('Environment variable LOCALHOST_IP found, with value: "%s". To override it, use --env LOCALHOST_IP='
                '<IP> when invoking "docker run [...]".'%(environ.get('LOCALHOST_IP')))

    # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
    modules = import_modules(CONFIG['DATA_MODULES_PATH'], recursive=True,
                             base_package=CONFIG['DATA_COLLECTOR_BASE_PACKAGE'])
    if not modules:
        logger.critical('Data modules could not be instantiated. Aborting Data Gathering Subsystem.')
        exit(1)
    if len(modules) > CONFIG['MAX_RECOMMENDED_DATA_COLLECTORS']:
        logger.warning('The number of DataCollector modules (%d) exceeds the recommended amount: %d. This may lead into'
                ' performance penalties.'%(len(modules), CONFIG['MAX_RECOMMENDED_DATA_COLLECTORS']))

    # Enabling a channel to pass messages between DataCollectors and Supervisor.
    __channel = Queue(maxsize=(len(modules) * 2) + 2)
    logger.debug('Created shared channel for message passing, with length %d.'%(__channel.maxsize))

    # Creating an starting Supervisor
    supervisor = SupervisorThread(__channel, __condition)
    supervisor.start()
    logger.debug('Created Supervisor and started supervision.')

    # Creates a Thread per DataCollector, and starts them.
    threads = []
    for module in modules:
        thread = DataCollectorThread(module, __channel, __condition)
        threads.append(thread)
        thread.start()
    # Waits until all DataCollectors have finished execution.
    for thread in threads:
        thread.join()

    # When all DataCollectors have finished execution, Supervisor is able to generate an execution report.
    time = timer() - start_time
    Message(MessageType.report, content=time).send(__channel, __condition)

    # Once Supervisor has generated its report, it can exit.
    Message(MessageType.exit).send(__channel, __condition)
    supervisor.join()

    # Logging total execution time (which is report time + report generation time + Supervisor's thread join)
    m, s = divmod(timer() - start_time, 60)
    h, m = divmod(m, 60)
    logger.info('Data Gathering Subsystem has finished its execution. Total elapsed time is %d h, %d min and %d s.'%
            (h, m, s))
