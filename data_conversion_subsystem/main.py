import builtins
import json
import os
import requests
from queue import Queue
from data_conversion_subsystem.data_converter.data_converter import DataConverterThread, Message, MessageType
from data_conversion_subsystem.config.config import DCS_CONFIG
from data_conversion_subsystem.supervisor.supervisor import SupervisorThread
from django.core.wsgi import get_wsgi_application
from global_config.config import GLOBAL_CONFIG
from timeit import default_timer as timer
from threading import Condition
from utilities.postgres_util import import_psycopg2, ping_database
from utilities.log_util import get_logger
from utilities.import_dir import import_modules
from utilities.util import time_limit

# This is required to work with PyPy.
import_psycopg2()


_logger = None


def get_execution_id() -> int:
    """
        Gets the current execution ID for the Data Conversion Subsystem. If the execution ID did not exist, it is
        previously created.
        :return: An integer, which represents the current execution ID.
        Postcondition: The execution ID is auto-incremented after retrieving it.
    """
    from data_conversion_subsystem.data.models import ExecutionId
    row, created = ExecutionId.objects.get_or_create(pk=DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'])
    execution_id = row.execution_id
    row.save()
    return execution_id
    

def main(log_to_file=True, log_to_stdout=True, log_to_telegram=None):
    """
        This function is the entry point to the Data Conversion Subsystem.
        Imports all DataCollectors, generates and sets up Supervisor, waits until all work has been done, and exits.
        A timeout is set, just in case a deadlock occurs.
        :raise TimeoutError: If the timeout is reached.
    """
    global _logger

    # Measuring total execution time
    start_time = timer()
    builtins.EXECUTION_ID = None

    # Getting logger instance
    _logger = get_logger(__file__, 'MainLogger', to_stdout=log_to_stdout, to_file=log_to_file, subsystem_id=
            DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'], root_dir=DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'],
            component=DCS_CONFIG['COMPONENT'], to_telegram=log_to_telegram)

    # This provisional solution FIXES [BUG-015]
    if os.environ.get('POSTGRES_IP') is None:
        _logger.critical('POSTGRES_IP must exist as an ENVIRONMENT VARIABLE at execution time. Aborting Subsystem.')
        exit(1)
    else:
        _logger.debug('Environment variable POSTGRES_IP found, with value: "%s". To override it, use --env '
                       'POSTGRES_IP=<IP> when invoking "docker run".' % (os.environ.get('POSTGRES_IP')))
    
    # Ensuring API_IP environment variable exists
    if os.environ.get('API_IP') is None:
        _logger.critical('API_IP must exist as an ENVIRONMENT VARIABLE at execution time. Aborting Subsystem.')
        exit(1)
    else:
        _logger.debug('Environment variable API_IP found, with value: "%s". To override it, use --env '
                       'API_IP=<IP> when invoking "docker run".' % (os.environ.get('API_IP')))

    # Pinging database before any other operation.
    _logger.info('Determining if the PostgreSQL server is up.')
    try:
        ping_database(close_after=True)
        builtins.EXECUTION_ID = get_execution_id()
        _logger = get_logger(__file__, 'MainLogger', to_stdout=log_to_stdout, to_file=log_to_file, subsystem_id=
                DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'], component=DCS_CONFIG['COMPONENT'], root_dir=DCS_CONFIG[
                'DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'], to_telegram=log_to_telegram)
        _logger.info('PostgreSQL server is up and reachable.')
    except EnvironmentError:
        _logger.critical('The PostgreSQL server is down. The Subsystem will exit now, since it\'s useless to '
                          'convert data for not being able to save them.')
        exit(1)    
        
    # Testing Data Gathering Subsystem's API is alive.
    _logger.info('Determining if the Data Gathering Subsystem API is up.')
    try:
        r = requests.get(DCS_CONFIG['API_ALIVE_ENDPOINT_URL'].replace('{IP}', os.environ['API_IP']).replace('{PORT}',
                str(os.environ.get(GLOBAL_CONFIG['API_PORT'], 5000))), timeout=5)
    except requests.RequestException:
        _logger.critical('An HTTP error occurred. The Subsystem will exit now, since the Data Gathering Subsystem API'
                ' is unreachable.')
        exit(1)
    try:
        content = json.loads(r.content.decode('utf-8', errors='replace'))
    except json.JSONDecodeError:
        content = 'Unparseable content.'
    if r.status_code == 200 and isinstance(content, dict) and content['alive'] is True:
        _logger.debug('Data Gathering Subsystem\'s API is alive.')
    else:
        _logger.critical('Received response from API with HTTP error code %d and content: %s' %
                        (r.status_code, content))
        _logger.critical('The Subsystem will exit now, since the Data Gathering Subsystem API is unreachable.')
        exit(1)

    # Start message
    if builtins.EXECUTION_ID is not None:
        _logger.info('Starting Data Conversion Subsystem. Execution ID is: %d' % (builtins.EXECUTION_ID))
    else:
        _logger.warning('Starting Data Conversion Subsystem. Execution ID is unknown. This may difficult debug operations.')

    # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
    modules = import_modules(DCS_CONFIG['DATA_CONVERTERS_PATH'], recursive=True,
            base_package=DCS_CONFIG['DATA_CONVERTERS_BASE_PACKAGE'])
    if not modules:
        _logger.critical('Data Converters could not be instantiated. Aborting Data Conversion Subsystem.')
        exit(1)
    if len(modules) > DCS_CONFIG['MAX_RECOMMENDED_DATA_CONVERTERS']:
        _logger.warning('The number of DataConverter modules (%d) exceeds the recommended amount: %d. This may lead '
                'into performance penalties.'%(len(modules), DCS_CONFIG['MAX_RECOMMENDED_DATA_CONVERTERS']))

    # Enabling a channel to pass messages between DataCollectors and Supervisor.
    channel = Queue(maxsize=(len(modules) * 2) + 2)
    condition = Condition()
    _logger.debug('Created shared channel for message passing, with length %d.' % channel.maxsize)

    # Creating an starting Supervisor
    supervisor = SupervisorThread(channel, condition, log_to_file=log_to_file, log_to_stdout=log_to_stdout)
    supervisor.start()
    _logger.debug('Created Supervisor and started supervision.')

    # Creates a Thread per DataCollector, and starts them.
    threads = []
    for module in modules:
        thread = DataConverterThread(module, channel, condition, log_to_file=log_to_file, log_to_stdout=log_to_stdout)
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
    _logger.info('Data Conversion Subsystem has finished its execution. Total elapsed time is %d h, %d min and %d s.'%
            (h, m, s))


if __name__ == '__main__':
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        get_wsgi_application()
        with time_limit(DCS_CONFIG['SUBSYSTEM_TIMEOUT']):
            main(log_to_stdout=True, log_to_file=True, log_to_telegram=None)
    except TimeoutError:
        _logger.critical('The Subsystem execution has been timed out. This error should be revised, since the causes '
                'might be:\n\t1. A deadlock (or, in general a concurrency error) has occurred. Timeout: OK'
                '\n\t2. The Subsystem was performing actual work. Timeout: BAD\n')
    except Exception:
        _logger.exception('An unexpected error occurred while executing the Subsystem.')
        exit(1)
