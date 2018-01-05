import datetime
import data_collector.data_collector as dc

from pytz import UTC
from queue import Queue
from threading import Condition, Thread
from utilities.log_util import get_logger
from utilities.util import get_config, read_state, serialize_date, write_state

__singleton = None


def instance(queue: Queue, condition: Condition):
    global __singleton
    if __singleton is None:
        __singleton = Supervisor(queue, condition)
    return __singleton


class SupervisorThread(Thread):
    """
        This class allows a Supervisor instance to be executed in its own thread.
    """
    def __init__(self, queue: Queue, condition: Condition):
        self.__supervisor = instance(queue, condition)
        Thread.__init__(self)
        self.setName('SupervisorThread')

    def run(self):
        try:
            self.__supervisor.supervise()
        except Exception:
            self.__supervisor.logger.exception('Supervisor execution has been aborted due to an error.')


class Supervisor:

    def __init__(self, channel: Queue, condition: Condition):
        super().__init__()
        self.__channel = channel
        self.__condition = condition
        self.logger = get_logger(__file__, 'SupervisorLogger', to_stdout=True)
        self.config = get_config(__file__)
        self.state = read_state(__file__, repair_struct=self.config['STATE_STRUCT'])
        self.registered = 0
        self.unregistered = 0
        self.registered_data_collectors = []
        self.successful_executions = []
        self.unsuccessful_executions = []

    def supervise(self):
        self.logger.info('Starting module supervision.')
        try:
            while True:
                message = None
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
        from json import dumps

        modules_succeeded = 0
        modules_failed = 0
        collected_elements = 0
        inserted_elements = 0
        execution_succeeded = True
        for dc in self.registered_data_collectors:
            if dc.successful_execution():
                modules_succeeded += 1
            else:
                execution_succeeded = False
                modules_failed += 1
            collected_elements += dc.state['data_elements'] if dc.state['data_elements'] else 0
            inserted_elements += dc.state['inserted_elements'] if dc.state['inserted_elements'] else 0
        self.state['last_execution']['duration'] = duration
        self.state['last_execution']['modules_executed'] = len(self.registered_data_collectors)
        self.state['last_execution']['modules_succeeded'] = modules_succeeded
        self.state['last_execution']['modules_failed'] = modules_failed
        self.state['last_execution']['collected_elements'] = collected_elements
        self.state['last_execution']['inserted_elements'] = inserted_elements
        self.state['last_execution']['execution_succeeded'] = execution_succeeded
        self.state['last_execution']['timestamp'] = serialize_date(datetime.datetime.now(tz=UTC))
        self.state['aggregated']['total_executions'] = self.state['aggregated']['total_executions'] + 1
        self.state['aggregated']['total_execution_time'] = self.state['aggregated']['total_execution_time'] + duration
        self.state['aggregated']['max_duration'] = self.state['aggregated']['max_duration'] if self.state['aggregated'][
                'max_duration'] and duration < self.state['aggregated']['max_duration'] else duration
        self.state['aggregated']['mean_duration'] = (self.state['aggregated']['mean_duration'] * (self.state[
                'aggregated']['total_executions'] - 1) + duration) / (self.state['aggregated']['total_executions'])
        self.state['aggregated']['min_duration'] = self.state['aggregated']['min_duration'] if self.state['aggregated'][
                'min_duration'] and duration > self.state['aggregated']['min_duration'] else duration
        self.state['aggregated']['total_succeeded_executions'] = self.state['aggregated'][
                'total_succeeded_executions'] + 1 if execution_succeeded else self.state['aggregated'][
                'total_succeeded_executions']
        self.state['aggregated']['total_failed_executions'] = self.state['aggregated']['total_failed_executions'] \
                + 1 if not execution_succeeded else self.state['aggregated']['total_failed_executions']
        self.state['aggregated']['total_collected_elements'] = self.state['aggregated']['total_collected_elements'] \
                + collected_elements
        self.state['aggregated']['total_inserted_elements'] = self.state['aggregated']['total_inserted_elements'] \
                + inserted_elements
        path = write_state(self.state, __file__)
        self.logger.info('An execution report has been saved to "%s".' % (path))
        self.logger.debug('Execution results:\n%s'%(dumps(self.state, indent=4, separators=(',', ': '))))
