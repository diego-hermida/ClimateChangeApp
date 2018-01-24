import datetime
import data_collector.data_collector as dc

from global_config.global_config import CONFIG as GLOBAL_CONFIG
from json import dumps
from pytz import UTC
from queue import Queue
from threading import Condition, Thread
from utilities.db_util import MongoDBCollection
from utilities.util import get_config, get_module_name, read_state, serialize_date, write_state

CONFIG = get_config(__file__)
EXECUTION_ID = read_state(__file__, CONFIG['EXECUTION_ID_STRUCT'])['execution_id'] + 1  # Updating execution ID count


class SupervisorThread(Thread):
    """
        This class allows a Supervisor instance to be executed in its own thread.
        The thread is set as a Daemon thread, as we want the thread to be stopped when Main component exits.
    """
    def __init__(self, queue: Queue, condition: Condition, log_to_file=True, log_to_stdout=True):
        self.supervisor = Supervisor(queue, condition, log_to_file=log_to_file, log_to_stdout=log_to_stdout)
        Thread.__init__(self)
        self.setDaemon(True)
        self.setName('SupervisorThread')

    def run(self):
        try:
            self.supervisor.supervise()
        except Exception:
            self.supervisor.logger.exception('Supervisor execution has been aborted due to an error.')


class Supervisor:

    def __init__(self, channel: Queue, condition: Condition, log_to_file=True, log_to_stdout=True):
        super().__init__()
        from utilities.log_util import get_logger

        self.__channel = channel
        self.__condition = condition
        self.logger = get_logger(__file__, 'SupervisorLogger', to_file=log_to_file, to_stdout=log_to_stdout)
        self.config = get_config(__file__)
        self.module_name = get_module_name(__file__)
        self.collection = MongoDBCollection(self.module_name)
        self.execution_report = self.collection.get_last_elements(amount=1)
        if not self.execution_report:
            self.execution_report = self.config['STATE_STRUCT']
        self.collection.close()
        self.registered = 0
        self.unregistered = 0
        self.registered_data_collectors = []
        self.successful_executions = []
        self.unsuccessful_executions = []

    def supervise(self):
        self.logger.info('Starting module supervision.')
        try:
            while True:
                self.__condition.acquire()
                while True:
                    if not self.__channel.empty():
                        message = self.__channel.get_nowait()
                        break
                    self.__condition.wait()
                self.__condition.release()
                if not message:
                    continue
                try:
                    assert isinstance(message, dc.Message)
                except AssertionError:
                    self.logger.warning('Messages should only be instances of the data_collector.Message class.')
                if message.type == dc.MessageType.register:
                    assert isinstance(message.content, dc.DataCollector)
                    self.registered_data_collectors.append(message.content)
                    self.registered += 1
                    self.logger.debug('Registered DataCollector "%s".' % (message.content))
                elif message.type == dc.MessageType.finished:
                    assert isinstance(message.content, dc.DataCollector)
                    self.unregistered += 1
                    self.logger.debug('Unregistered DataCollector "%s".' % (message.content))
                    self.verify_module_execution(message.content)
                elif message.type == dc.MessageType.report:
                    assert isinstance(message.content, float)
                    self.logger.info('Generating execution report.')
                    self.generate_report(message.content)
                elif message.type == dc.MessageType.exit:
                    if not self.__channel.empty():
                        self.logger.warning('Supervisor should not receive EXIT signal before all DataCollectors have '
                                'finished its execution.')
                    raise StopIteration('EXIT')
        except StopIteration:
            self.logger.info('Supervisor has received EXIT signal. Exiting now.\n')

    def verify_module_execution(self, data_collector: dc.DataCollector):
        try:
            states = data_collector.expose_transition_states(who=self)
            assert states is not None
            if states[-1] == dc.ABORTED and states[-2] >= dc.STATE_RESTORED and not data_collector.state[
                    'restart_required']:
                self.logger.warning('"%s" execution has been ABORTED, but module restart hasn\'t been '
                        'scheduled. This issue will be fixed now.' % (data_collector))
                try:
                    data_collector.state['restart_required'] = True
                    if data_collector.state['error']:
                        data_collector.execute_actions(state=dc.EXECUTION_CHECKED, who=self)
                    self.logger.info('Scheduled restart has been set for "%s". Errors and backoff time have been '
                                       'serialized.' % (data_collector))
                except Exception:
                    self.logger.exception('Unable to schedule "%s" restart.' % (data_collector))
            if data_collector.successful_execution():
                self.successful_executions.append(str(data_collector))
            else:
                self.unsuccessful_executions.append(str(data_collector))
        except Exception:
            self.logger.exception('An error occurred while verifying "%s" execution.' % (data_collector))

    def generate_report(self, duration: float):
        failed_modules = []
        modules_succeeded = 0
        modules_failed = 0
        collected_elements = 0
        inserted_elements = 0
        execution_succeeded = True
        for dc in self.registered_data_collectors:
            if not self.execution_report['aggregated']['per_module'].get(dc.module_name):
                self.execution_report['aggregated']['per_module'][dc.module_name] = {
                        'total_executions': 0, 'succeeded_executions': 0, 'failed_executions': 0, 'failure_details': []}
            self.execution_report['aggregated']['per_module'][dc.module_name]['total_executions'] += 1
            if dc.successful_execution():
                modules_succeeded += 1
                self.execution_report['aggregated']['per_module'][dc.module_name]['succeeded_executions'] += 1
            else:
                execution_succeeded = False
                modules_failed += 1
                failed_modules.append(dc.module_name)
                self.execution_report['aggregated']['per_module'][dc.module_name]['failed_executions'] += 1
                self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'].append({
                        'execution_id': EXECUTION_ID, 'cause': dc.state['error']})
            collected_elements += dc.state['data_elements'] if dc.state['data_elements'] else 0
            inserted_elements += dc.state['inserted_elements'] if dc.state['inserted_elements'] else 0
        # Current execution statistics
        self.execution_report['_id'] = EXECUTION_ID
        self.execution_report['last_execution']['id'] = EXECUTION_ID
        self.execution_report['last_execution']['subsystem_version'] = GLOBAL_CONFIG['SUBSYSTEM_VERSION']
        self.execution_report['last_execution']['timestamp'] = serialize_date(datetime.datetime.now(tz=UTC))
        self.execution_report['last_execution']['duration'] = duration
        self.execution_report['last_execution']['execution_succeeded'] = execution_succeeded
        self.execution_report['last_execution']['collected_elements'] = collected_elements
        self.execution_report['last_execution']['inserted_elements'] = inserted_elements
        self.execution_report['last_execution']['modules_executed'] = len(self.registered_data_collectors)
        self.execution_report['last_execution']['modules_succeeded'] = modules_succeeded
        self.execution_report['last_execution']['modules_failed']['amount'] = modules_failed
        # Aggregated executions
        self.execution_report['aggregated']['executions'] += 1
        self.execution_report['aggregated']['max_duration'] = self.execution_report['aggregated']['max_duration'] \
                if self.execution_report['aggregated']['max_duration'] and duration < self.execution_report[
                'aggregated']['max_duration'] else duration
        try:
            self.execution_report['aggregated']['mean_duration'] = ((self.execution_report['aggregated'][
                'mean_duration'] * (self.execution_report['aggregated']['executions'] - 1)) + duration) / \
                self.execution_report['aggregated']['executions']
        except ZeroDivisionError:
            self.execution_report['aggregated']['mean_duration'] = duration
        self.execution_report['aggregated']['min_duration'] = self.execution_report['aggregated']['min_duration'] if \
                self.execution_report['aggregated']['min_duration'] and duration > self.execution_report['aggregated'][
                'min_duration'] else duration
        self.execution_report['aggregated']['execution_time'] += duration
        self.execution_report['aggregated']['collected_elements'] += collected_elements
        self.execution_report['aggregated']['inserted_elements'] += inserted_elements
        if execution_succeeded:
            self.execution_report['aggregated']['succeeded_executions'] += 1
        else:
            self.execution_report['aggregated']['failed_executions'] += 1
            self.execution_report['last_execution']['modules_failed']['modules'] = failed_modules
        # Saving execution report to database
        self.collection.connect()
        self.collection.collection.insert_one(self.execution_report)
        self.collection.close()
        write_state({'execution_id': EXECUTION_ID}, __file__)
        del self.execution_report['_id']
        self.logger.debug('Execution results:\n%s' % (dumps(self.execution_report, indent=4, separators=(',', ': '))))
