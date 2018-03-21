import builtins

from copy import deepcopy
from json import dumps
from pymongo import InsertOne, UpdateOne
from queue import Queue
from threading import Condition

import data_gathering_subsystem.data_collector.data_collector as dc
from data_gathering_subsystem.config.config import DGS_CONFIG
from global_config.config import GLOBAL_CONFIG
from utilities.execution_util import Message, MessageType, Supervisor
from utilities.mongo_util import MongoDBCollection
from utilities.util import current_date_in_millis, get_config, get_module_name

CONFIG = get_config(__file__)


class DataCollectorSupervisor(Supervisor):
    """
        Supervisor class for the Data Gathering Subsystem.
        When the 'supervise' method is called, Supervisor accepts "register" messages from the DataCollectors. Once
        they have finished its work, they send a "finished" message, and the Supervisor unregisters them.
        When the Supervisor receives a "report" message, it will generate an execution report, using previously saved
        statistics. This report will be saved into database.
        Once these operations have been completed, an "exit" message will make the Supervisor end its execution.
    """

    def __init__(self, channel: Queue, condition: Condition, log_to_file=True, log_to_stdout=True,
                 log_to_telegram=None):
        """
           Creates a Supervisor instance.
           :param channel: A queue.Queue object. Acts as the message-passing shared channel.
           :param condition: A threading.Condition object. It will notify the Supervisor when a message has been put
                             into the channel.
           :param log_to_stdout: In True, Supervisor's logger will show log records by console.
           :param log_to_file: If True, Supervisor's logger will save log records to a file.
           :param log_to_telegram: If True, Supervisor's logger will send CRITICAL log records via Telegram messages.
       """
        super().__init__()
        from utilities.log_util import get_logger

        self._channel = channel
        self._condition = condition
        self.logger = get_logger(__file__, 'SupervisorLogger', to_file=log_to_file, to_stdout=log_to_stdout,
                                 subsystem_id=DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], component=DGS_CONFIG['COMPONENT'],
                                 root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'],
                                 to_telegram=log_to_telegram)
        self.config = get_config(__file__)
        self.module_name = get_module_name(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION'])
        self.collection = None
        self.execution_report = None
        self.registered = 0
        self.unregistered = 0
        self.registered_data_collectors = []
        self.successful_executions = []
        self.unsuccessful_executions = []

    def supervise(self):
        """
           Supervises DataConverter executions. To do so, the Supervisor must receive both "register" and "finished"
           messages.
           A "report" message will generate an execution report.
           An "exit" message will end the supervision.
       """
        self.logger.info('Starting module supervision.')
        try:
            while True:
                self._condition.acquire()
                while True:
                    if not self._channel.empty():
                        message = self._channel.get_nowait()
                        break
                    self._condition.wait()
                self._condition.release()
                if not message:
                    continue
                try:
                    assert isinstance(message, Message)
                except AssertionError:
                    self.logger.warning('Messages should only be instances of the data_collector.Message class.')
                    continue
                if message.type == MessageType.register:
                    assert isinstance(message.content, dc.DataCollector)
                    self.registered_data_collectors.append(message.content)
                    self.registered += 1
                    self.logger.debug('Registered DataCollector "%s".' % message.content)
                elif message.type == MessageType.finished:
                    assert isinstance(message.content, dc.DataCollector)
                    self.unregistered += 1
                    self.logger.debug('Unregistered DataCollector "%s".' % message.content)
                    self.verify_module_execution(message.content)
                elif message.type == MessageType.report:
                    assert isinstance(message.content, float)
                    self.logger.info('Generating execution report.')
                    self.generate_report(message.content)
                elif message.type == MessageType.exit:
                    if not self._channel.empty():
                        self.logger.warning('Supervisor should not receive EXIT signal before all DataCollectors have '
                                            'finished its execution.')
                    raise StopIteration('EXIT')
        except StopIteration:
            self.logger.info('Supervisor has received EXIT signal. Exiting now.\n')

    def verify_module_execution(self, data_collector: dc.DataCollector):
        """
            Verifies if a DataCollector execution is successful. If not, restores its state to its value before the
            current execution. Error values will be serialized, though.
            :param data_collector: DataCollector object, whose execution will be verified.
        """
        try:
            states = data_collector.expose_transition_states(who=self)
            assert states is not None
            if states[-1] == dc.ABORTED and states[-2] >= dc.STATE_RESTORED and not data_collector.state[
                'restart_required']:
                self.logger.warning('"%s" execution has been ABORTED, but module restart hasn\'t been '
                                    'scheduled. This issue will be fixed now.' % data_collector)
                try:
                    data_collector.state['restart_required'] = True
                    if data_collector.state['error']:
                        data_collector.execute_actions(state=dc.EXECUTION_CHECKED, who=self)
                        self.logger.info('Scheduled restart has been set for "%s". Errors and backoff time have been '
                                         'serialized.' % data_collector)
                except Exception:
                    self.logger.exception('Unable to schedule "%s" restart.' % data_collector)
            if data_collector.successful_execution():
                self.successful_executions.append(str(data_collector))
            else:
                self.unsuccessful_executions.append(str(data_collector))
        except Exception:
            self.logger.exception('An error occurred while verifying "%s" execution.' % data_collector)

    def generate_report(self, duration: float):
        """
            Generates an execution report. This report has two sections:
                - Execution statistics: Data from the current execution (number of modules, collected elements, etc.)
                - Aggregated statistics: Uses the execution statistics over time to generate mean values (mean duration,
                                         total elements converted, successful executions, etc.)
            :param duration: Duration of the current execution.
        """
        # Fetching last execution report. This operation has been moved from the constructor method -> optimization.
        self.logger.info('Fetching the last execution report from database.')
        self.collection = MongoDBCollection(collection_name=self.module_name, use_pool=True)
        self.execution_report = {'last_execution': self.config['STATE_STRUCT']['last_execution'],
                'aggregated': self.collection.get_last_elements(amount=1, filter={'_id': {'subsystem_id': DGS_CONFIG[
                'SUBSYSTEM_INSTANCE_ID'], 'type': 'aggregated'}})}
        if not self.execution_report['aggregated']:
            self.logger.warning('The last execution report could not be fetched. This will be indicated in the current '
                                'execution report by setting the flag "last_report_not_fetched" to "true".')
            self.execution_report = self.config['STATE_STRUCT']
            self.execution_report['last_execution']['last_report_not_fetched'] = True
        else:
            self.logger.info('Execution report successfully fetched from database.')
        self.collection.close()

        # Composing execution report
        failed_modules = []
        modules_with_pending_work = {}
        modules_succeeded = 0
        modules_failed = 0
        collected_elements = 0
        inserted_elements = 0
        execution_succeeded = True
        for dc in self.registered_data_collectors:
            if not self.execution_report['aggregated']['per_module'].get(dc.module_name):
                self.execution_report['aggregated']['per_module'][dc.module_name] = {'total_executions': 0,
                    'executions_with_pending_work': 0, 'succeeded_executions': 0, 'failed_executions': 0,
                    'failure_details': {}}
            self.execution_report['aggregated']['per_module'][dc.module_name]['total_executions'] += 1
            collected_elements += dc.state['data_elements'] if dc.state['data_elements'] else 0
            inserted_elements += dc.state['inserted_elements'] if dc.state['inserted_elements'] else 0
            if dc.successful_execution():
                modules_succeeded += 1
                self.execution_report['aggregated']['per_module'][dc.module_name]['succeeded_executions'] += 1
            else:
                execution_succeeded = False
                modules_failed += 1
                failed_modules.append(dc.module_name)
                self.execution_report['aggregated']['per_module'][dc.module_name]['failed_executions'] += 1
                cause = dc.state['error'] if dc.state['error'] else 'Unknown cause'
                if self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'].get(cause) is None:
                    self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'][cause] = []
                self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'][cause].append(
                        builtins.EXECUTION_ID)
            if dc.pending_work:
                modules_with_pending_work[dc.module_name] = {'collected_elements': dc.state['data_elements'],
                                                             'saved_elements': dc.state['inserted_elements']}
                self.execution_report['aggregated']['per_module'][dc.module_name]['executions_with_pending_work'] += 1
        if not modules_with_pending_work:
            modules_with_pending_work = None
        # Current execution statistics
        self.execution_report['last_execution']['_id']['execution_id'] = builtins.EXECUTION_ID
        self.execution_report['last_execution']['_id']['subsystem_id'] = DGS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        self.execution_report['last_execution']['subsystem_version'] = GLOBAL_CONFIG['APP_VERSION']
        self.execution_report['last_execution']['timestamp'] = current_date_in_millis()
        self.execution_report['last_execution']['duration'] = duration
        self.execution_report['last_execution']['execution_succeeded'] = execution_succeeded
        self.execution_report['last_execution']['collected_elements'] = collected_elements
        self.execution_report['last_execution']['inserted_elements'] = inserted_elements
        self.execution_report['last_execution']['modules_executed'] = len(self.registered_data_collectors)
        self.execution_report['last_execution']['modules_with_pending_work'] = modules_with_pending_work
        self.execution_report['last_execution']['modules_succeeded'] = modules_succeeded
        self.execution_report['last_execution']['modules_failed']['amount'] = modules_failed
        # Aggregated executions
        self.execution_report['aggregated']['_id']['subsystem_id'] = DGS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        self.execution_report['aggregated']['executions'] += 1
        self.execution_report['aggregated']['last_execution_id'] = builtins.EXECUTION_ID
        self.execution_report['aggregated']['timestamp'] = self.execution_report['last_execution']['timestamp']
        self.execution_report['aggregated']['max_duration'] = self.execution_report['aggregated']['max_duration'] if \
        self.execution_report['aggregated']['max_duration'] and duration < self.execution_report['aggregated'][
                'max_duration'] else duration
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
            self.execution_report['last_execution']['modules_failed']['modules'] = None
        else:
            self.execution_report['aggregated']['failed_executions'] += 1
            self.execution_report['last_execution']['modules_failed']['modules'] = failed_modules
        # Saving execution report to database
        self.collection.connect()
        operations = [UpdateOne({'_id': self.execution_report['aggregated']['_id']},
                                update={'$set': self.execution_report['aggregated']}, upsert=True),
                      InsertOne(self.execution_report['last_execution'])]
        self.collection.collection.bulk_write(operations)
        self.collection.close()
        # Improving report console output.
        copy = deepcopy(self.execution_report)
        del copy['last_execution']['_id']
        del copy['aggregated']['_id']
        del copy['aggregated']['last_execution_id']
        del copy['aggregated']['timestamp']
        copy['last_execution']['subsystem_id'] = DGS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        copy['aggregated']['subsystem_id'] = DGS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        copy['last_execution']['execution_id'] = builtins.EXECUTION_ID
        self.logger.debug('Execution results:\n%s' % (dumps(copy, indent=4, separators=(',', ': '))))
