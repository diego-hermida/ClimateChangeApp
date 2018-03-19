import builtins
import data_conversion_subsystem.data_converter.data_converter as dc
from copy import deepcopy
from data_conversion_subsystem.config.config import DCS_CONFIG
from global_config.config import GLOBAL_CONFIG
from json import dumps
from queue import Queue
from threading import Condition, Thread
from utilities.util import get_config, get_module_name, current_date_in_millis, read_state

from data_conversion_subsystem.settings import register_settings
# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import AggregatedStatistics, ExecutionStatistics

CONFIG = get_config(__file__)


class SupervisorThread(Thread):
    """
        This class allows a Supervisor instance to be executed in its own thread.
        The thread is set as a Daemon thread, as we want the thread to be stopped when Main component exits.
    """
    def __init__(self, queue: Queue, condition: Condition, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        self.supervisor = Supervisor(queue, condition, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                     log_to_telegram=log_to_telegram)
        Thread.__init__(self)
        self.setDaemon(True)
        self.setName('SupervisorThread')

    def run(self):
        try:
            self.supervisor.supervise()
        except Exception:
            self.supervisor.logger.exception('Supervisor execution has been aborted due to an error.')


class Supervisor:

    def __init__(self, channel: Queue, condition: Condition, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__()
        from utilities.log_util import get_logger

        self._channel = channel
        self._condition = condition
        self.logger = get_logger(__file__, 'SupervisorLogger', to_file=log_to_file, to_stdout=log_to_stdout,
                subsystem_id=DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'], component=DCS_CONFIG['COMPONENT'],
                root_dir=DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'], to_telegram=log_to_telegram)
        self.config = get_config(__file__)
        self.module_name = get_module_name(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION'])
        self.registered = 0
        self.unregistered = 0
        self.registered_data_converters = []
        self.successful_executions = []
        self.unsuccessful_executions = []

    def supervise(self):
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
                    assert isinstance(message, dc.Message)
                except AssertionError:
                    self.logger.warning('Messages should only be instances of the data_converter.Message class.')
                if message.type == dc.MessageType.register:
                    assert isinstance(message.content, dc.DataConverter)
                    self.registered_data_converters.append(message.content)
                    self.registered += 1
                    self.logger.debug('Registered DataConverter "%s".' % message.content)
                elif message.type == dc.MessageType.finished:
                    assert isinstance(message.content, dc.DataConverter)
                    self.unregistered += 1
                    self.logger.debug('Unregistered DataConverter "%s".' % message.content)
                    self.verify_module_execution(message.content)
                elif message.type == dc.MessageType.report:
                    assert isinstance(message.content, float)
                    self.logger.info('Generating execution report.')
                    self.generate_report(message.content)
                elif message.type == dc.MessageType.exit:
                    if not self._channel.empty():
                        self.logger.warning('Supervisor should not receive EXIT signal before all DataConverters have '
                                'finished its execution.')
                    raise StopIteration('EXIT')
        except StopIteration:
            self.logger.info('Supervisor has received EXIT signal. Exiting now.\n')

    def verify_module_execution(self, data_converter: dc.DataConverter):
        try:
            states = data_converter.expose_transition_states(who=self)
            assert states is not None
            if states[-1] == dc.ABORTED and states[-2] >= dc.STATE_RESTORED and not data_converter.state[
                    'restart_required']:
                self.logger.warning('"%s" execution has been ABORTED, but module restart hasn\'t been '
                        'scheduled. This issue will be fixed now.' % data_converter)
                try:
                    if data_converter.state['error']:
                        last_state = read_state(data_converter._file_path, data_converter.config['STATE_STRUCT'],
                                root_dir=DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
                        last_state['last_request'] = data_converter.state['last_request']
                        last_state['error'] = data_converter.state['error']
                        last_state['errors'] = data_converter.state['errors']
                        last_state['last_error'] = data_converter.state['last_error']
                        last_state['backoff_time'] = data_converter.state['backoff_time']
                        last_state['restart_required'] = True
                        data_converter.state = last_state
                        data_converter.execute_actions(state=dc.EXECUTION_CHECKED, who=self)
                        self.logger.info('Scheduled restart has been set for "%s". Errors and backoff time have been '
                                'serialized. The remaining state variables were reset to the values before the current '
                                'execution.' % data_converter)
                except Exception:
                    self.logger.exception('Unable to schedule "%s" restart.' % data_converter)
            if data_converter.successful_execution():
                self.successful_executions.append(str(data_converter))
            else:
                self.unsuccessful_executions.append(str(data_converter))
        except Exception:
            self.logger.exception('An error occurred while verifying "%s" execution.' % data_converter)

    def generate_report(self, duration: float):
        # Fetching last execution report. This operation has been moved from the constructor method -> optimization.
        self.logger.info('Fetching the last execution report from database.')
        try:
            self.execution_report = {'last_execution': self.config['STATE_STRUCT']['last_execution'], 'aggregated':
                    AggregatedStatistics.objects.get(subsystem_id=DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']).data}
        except AggregatedStatistics.DoesNotExist:
            self.logger.warning('The last execution report could not be fetched. This will be indicated in the current '
                                'execution report by setting the flag "last_report_not_fetched" to "true".')
            self.execution_report = self.config['STATE_STRUCT']
            self.execution_report['last_execution']['last_report_not_fetched'] = True
        else:
            self.logger.debug('Execution report successfully fetched from database.')

        # Composing execution report
        failed_modules = []
        modules_with_pending_work = {}
        modules_succeeded = 0
        modules_failed = 0
        elements_to_convert = 0
        converted_elements = 0
        inserted_elements = 0
        execution_succeeded = True
        for dc in self.registered_data_converters:
            if not self.execution_report['aggregated']['per_module'].get(dc.module_name):
                self.execution_report['aggregated']['per_module'][dc.module_name] = {
                        'total_executions': 0, 'executions_with_pending_work': 0, 'succeeded_executions': 0,
                        'failed_executions': 0, 'failure_details': {}}
            self.execution_report['aggregated']['per_module'][dc.module_name]['total_executions'] += 1
            elements_to_convert += dc.state['elements_to_convert'] if dc.state['elements_to_convert'] else 0
            converted_elements += dc.state['converted_elements'] if dc.state['converted_elements'] else 0
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
                if self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'].get(
                        cause) is None:
                    self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'][cause] = []
                self.execution_report['aggregated']['per_module'][dc.module_name]['failure_details'][cause].append(
                        builtins.EXECUTION_ID)
            if dc.pending_work:
                modules_with_pending_work[dc.module_name] = {'elements_to_convert': dc.state['elements_to_convert'],
                                                             'converted_elements': dc.state['converted_elements'],
                                                             'inserted_elements': dc.state['inserted_elements']}
                self.execution_report['aggregated']['per_module'][dc.module_name]['executions_with_pending_work'] += 1
        if not modules_with_pending_work:
            modules_with_pending_work = None
        # Current execution statistics
        self.execution_report['last_execution']['_id']['execution_id'] = builtins.EXECUTION_ID
        self.execution_report['last_execution']['_id']['subsystem_id'] = DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        self.execution_report['last_execution']['subsystem_version'] = GLOBAL_CONFIG['APP_VERSION']
        self.execution_report['last_execution']['timestamp'] = current_date_in_millis()
        self.execution_report['last_execution']['duration'] = duration
        self.execution_report['last_execution']['execution_succeeded'] = execution_succeeded
        self.execution_report['last_execution']['elements_to_convert'] = elements_to_convert
        self.execution_report['last_execution']['converted_elements'] = converted_elements
        self.execution_report['last_execution']['inserted_elements'] = inserted_elements
        self.execution_report['last_execution']['modules_executed'] = len(self.registered_data_converters)
        self.execution_report['last_execution']['modules_with_pending_work'] = modules_with_pending_work
        self.execution_report['last_execution']['modules_succeeded'] = modules_succeeded
        self.execution_report['last_execution']['modules_failed']['amount'] = modules_failed
        # Aggregated executions
        self.execution_report['aggregated']['_id']['subsystem_id'] = DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        self.execution_report['aggregated']['executions'] += 1
        self.execution_report['aggregated']['last_execution_id'] = builtins.EXECUTION_ID
        self.execution_report['aggregated']['timestamp'] = self.execution_report['last_execution']['timestamp']
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
        self.execution_report['aggregated']['elements_to_convert'] += elements_to_convert
        self.execution_report['aggregated']['converted_elements'] += converted_elements
        self.execution_report['aggregated']['inserted_elements'] += inserted_elements
        if execution_succeeded:
            self.execution_report['aggregated']['succeeded_executions'] += 1
            self.execution_report['last_execution']['modules_failed']['modules'] = None
        else:
            self.execution_report['aggregated']['failed_executions'] += 1
            self.execution_report['last_execution']['modules_failed']['modules'] = failed_modules

        # Saving execution report to database
        AggregatedStatistics(subsystem_id=DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'],
                             data=self.execution_report['aggregated']).save()
        ExecutionStatistics.objects.create(subsystem_id=DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'],
                                           execution_id=builtins.EXECUTION_ID,
                                           data=self.execution_report['last_execution'])
        # Improving report console output.
        copy = deepcopy(self.execution_report)
        del copy['last_execution']['_id']
        del copy['aggregated']['_id']
        del copy['aggregated']['last_execution_id']
        del copy['aggregated']['timestamp']
        copy['last_execution']['subsystem_id'] = DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        copy['aggregated']['subsystem_id'] = DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']
        copy['last_execution']['execution_id'] = builtins.EXECUTION_ID
        self.logger.debug('Execution results:\n%s' % (dumps(copy, indent=4, separators=(',', ': '))))
