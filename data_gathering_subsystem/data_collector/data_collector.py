import builtins

from abc import ABC, abstractmethod
from data_gathering_subsystem.config.config import DGS_CONFIG
from utilities.mongo_util import MongoDBCollection
from utilities.execution_util import Runnable, TransitionState, Before, AbortedStateReachedError, StateChanged
from utilities.util import date_plus_timedelta_gt_now, deserialize_date, get_config, get_exception_info, \
    get_module_name, next_exponential_backoff, read_state, serialize_date, write_state, remove_state_file, \
    current_timestamp


CREATED = 0
INITIALIZED = 10
STATE_RESTORED = 20
PENDING_WORK_CHECKED = 30
DATA_COLLECTED = 40
DATA_SAVED = 50
EXECUTION_CHECKED = 60
STATE_SAVED = 70
FINISHED = 80
ABORTED = 100

MIN_BACKOFF = {'value': 60, 'units': 's'}
MAX_BACKOFF_SECONDS = 86400  # One day
CONFIG = get_config(__file__)


class Reader:
    """
        This class is used by DataCollectors which access to NASA files, allowing to retrieve all its useful data.
    """
    def __init__(self, fetch_mass_trend=False):
        self._data = []
        self.fetch_mass_trend = fetch_mass_trend

    def __call__(self, s):
        if not s.startswith('HDR') or (self.fetch_mass_trend and 'Mass Trend' in s):
            self._data.append(s)

    def get_data(self) -> list:
        return self._data


class DataCollector(ABC, Runnable):
    """
       Base class for all DataCollectors. This class provides:
           - Default implementation in some methods.
           - Automatic flow control (by calling the 'run' method, all operations will also be invoked, in proper order).
           - Error handling: Any raised error is automatically handled, logged and execution suspended.
       To define a DataCollector that inherits from this class, it's strongly recommended to read this page in the
       repository Wiki: https://github.com/diego-hermida/ClimateChangeApp/wiki/Adding-a-DataCollector-module
    """

    def _initialize_states(self):
        """
            Private method that creates the TransitionState instances that will represent the module valid states and
            their interactions.
        """
        self._ABORTED = TransitionState(name='ABORTED', code=ABORTED, next_state=None, actions=None)
        self._FINISHED = TransitionState(name='FINISHED', code=FINISHED, next_state=None, actions=None)
        self._STATE_SAVED = TransitionState(name='STATE_SAVED', code=STATE_SAVED, next_state=self._FINISHED,
                actions=self._finish_execution)
        self._EXECUTION_CHECKED = TransitionState(name='EXECUTION_CHECKED', code=EXECUTION_CHECKED,
                next_state=self._STATE_SAVED, actions=self._save_state)
        self._DATA_SAVED = TransitionState(name='DATA_SAVED', code=DATA_SAVED, next_state=self._EXECUTION_CHECKED,
                actions=self._check_execution)
        self._DATA_COLLECTED = TransitionState(name='DATA_COLLECTED', code=DATA_COLLECTED,
                next_state=self._DATA_SAVED, actions=self._save_data)
        self._PENDING_WORK_CHECKED = TransitionState(name='PENDING_WORK_CHECKED', code=PENDING_WORK_CHECKED,
                next_state=self._DATA_COLLECTED, actions=self._collect_data)
        self._STATE_RESTORED = TransitionState(name='STATE_RESTORED', code=STATE_RESTORED,
                next_state=self._PENDING_WORK_CHECKED, actions=self._has_pending_work)
        self._INITIALIZED = TransitionState(name='INITIALIZED', code=INITIALIZED, next_state=self._STATE_RESTORED,
                actions=self._restore_state)
        self._CREATED = TransitionState(name='CREATED', code=CREATED, next_state=self._INITIALIZED, actions=None)

    def is_runnable(self) -> bool:
        """
            Checks whether or not this DataCollector can execute the run() method.
            :return: True, if the DataCollector can execute run(); False, otherwise.
        """
        return self._transition_state == self._INITIALIZED

    def finished_execution(self) -> bool:
        """
            Checks if this DataCollector has finished its work.
            This can be done either by reaching the FINISHED state, or raising an error (and subsequently reaching the
            ABORTED state).
        """
        return self._transition_state == self._FINISHED or self._transition_state == self._ABORTED

    def successful_execution(self):
        """
            Checks if this DataCollector was successful, i.e. if the last state is FINISHED, and the result of the
            '_check_execution' method was positive.
        """
        return self._transition_state == self._FINISHED and self.check_result

    def remove_files(self):
        """
            Removes the files attached to this DataCollector: log file and '.state' file (if exist).
        """
        from utilities.log_util import remove_log_file

        try:
            remove_state_file(self._file_path, root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
        except FileNotFoundError:
            pass
        try:
            remove_log_file(self._file_path, root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
        except FileNotFoundError:
            pass

    def run(self):
        """
            This method must NOT be overridden. Once a DataCollector instance is created, simply invoke this method to
            perform all operations. By inheriting from DataCollector, flow control and unexpected error handling are
            automatically provided.
            Further info available at: https://github.com/diego-hermida/ClimateChangeApp/wiki/Subsystem-Structure
        """
        if self._transition_state != self._ABORTED:
            self.logger.info('Starting Data Collector execution.')
            while self._transition_state > self._CREATED and self._transition_state != self._FINISHED:
                try:
                    self._transition_state.actions()
                    self._transition_state = self._transition_state.next_state
                    self._state_transitions.append(self._transition_state)
                except StateChanged as state_transition_info:
                    self._transition_state.next_state = state_transition_info.next_state
                    self._transition_state.actions = state_transition_info.actions
                except Exception as actions_error:
                    error = AbortedStateReachedError(cause=actions_error)
                    self.logger.exception(error)
                    # If state has been restored, saving error info into self.state
                    if self._state_transitions and self._state_transitions[-1] >= self._STATE_RESTORED:
                        self.state['error'] = get_exception_info(actions_error)
                    self._transition_state = self._ABORTED
                    self._state_transitions.append(self._transition_state)
                    break
        self._close_db_resources()
        self.logger.info(self._pretty_format_transitions() + '\n')

    def __init__(self, file_path, log_to_stdout=True, log_to_file=True, log_to_telegram=None):
        """
            This method can be overridden, and MUST invoke super().__init__ before performing further actions.
            Any DataCollector which inherits from this class has the following (public) attributes:
                - advisedly_no_data_collected: Used to omit an error message when checking execution. This value must
                                               be set to True if the DataCollector deliberately omits data collection.
                - collection: An abstraction to a MongoDB Collection, with a valid connection to the database, which
                              will be initialized the first time it's used.
                - config: Stores the module configuration (deserializes the '.config' file).
                - data: Stores the collected data (in-memory).
                - logger: A custom logging.logger instance.
                - module_name: The name of the current module (got from 'file_path').
                - pending_work: True if module needs to download data, False otherwise. This
                                attribute will be initialized later, in '_has_pending_work'.
                - state: Stores the module conditions (deserializes the '.state' file).  This attribute will be
                         initialized later, in '_restore_state'.
            :param file_path: File path to '.py' file. '__file__' should always be passed as the 'file_path' parameter.
            :param log_to_stdout: In True, DataCollector's logger will show log records by console.
            :param log_to_file: If True, DataCollector's logger will save log records to a file.
            :param log_to_telegram: If True, DataCollector's logger will send CRITICAL log records via Telegram messages.
        """
        from utilities.log_util import get_logger
        self._initialize_states()
        self._file_path = file_path
        self.module_name = get_module_name(self._file_path)
        # Needs to be initialized to log errors.
        self.logger = get_logger(file_path, self.module_name, to_stdout=log_to_stdout, to_file=log_to_file,
                                 subsystem_id=DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], component=DGS_CONFIG['COMPONENT'],
                                 root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'],
                                 to_telegram=log_to_telegram)
        self._transition_state = self._CREATED
        try:
            self._state_transitions = []
            self._backoff_prevented_execution = False
            self._state_transitions.append(self._transition_state)
            self.check_result = None
            self.collection = MongoDBCollection(self.module_name)  # Proxy collection (lazily initialized)
            self.data = None
            self.pending_work = None
            self.state = None
            self.config = get_config(self._file_path)
            self.advisedly_no_data_collected = False
            # Ensuring that the STATE_STRUCT contains the minimum required fields. If not, a KeyError will be raised.
            missing_keys = []
            for key in CONFIG['STATE_STRUCT']:
                try:
                    self.config['STATE_STRUCT'][key]
                except KeyError:
                    missing_keys.append(key)
            if missing_keys:
                raise AttributeError(
                        'STATE_STRUCT (".config" module file) must contain, at least, the fields defined in the default'
                        ' STATE_STRUCT (file: "data_collector.config"). Missing ones are: %s'%(missing_keys))
            self._transition_state = self._INITIALIZED
        except Exception:
            self._transition_state = self._ABORTED
            self.logger.exception('Module "%s" could not be initialized.'%(self))
        self._state_transitions.append(self._transition_state)

    def _restore_state(self):
        """
            This method can be overridden, and must invoke super()._restore_state before performing further actions.
            Deserializes the '.state' file into a Python dict object. It also deserializes inner objects, such as
            datetime.datetime and others, and initializes 'volatile' fields.
        """
        self.state = read_state(self._file_path, repair_struct=self.config['STATE_STRUCT'],
                                root_dir=DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
        if self.state == self.config['STATE_STRUCT']:
            self.logger.warning('State file could not be read. Restoring state with STATE_STRUCT.')
        self.state['last_request'] = deserialize_date(self.state['last_request'])  # Creates datetime object
        self.state['error'] = None
        self.state['data_elements'] = None
        self.state['inserted_elements'] = None

    def _has_pending_work(self):
        """
            This method can be overridden, and must invoke super()._has_pending_work before performing further actions.
            Checks whether module has to collect data or not. The result must be saved in the 'pending_work' instance
            attribute.
        """
        if self.state['restart_required']:
            self.pending_work = date_plus_timedelta_gt_now(self.state['last_request'], self.state['backoff_time'])
            if self.pending_work:
                self.state['restart_required'] = False
            else:
                self._backoff_prevented_execution = True
                self.logger.info('Exponential backoff prevented data collection. Current backoff is: %d %s.' %
                        (self.state['backoff_time']['value'], self.state['backoff_time']['units']))
        else:
            self.pending_work = True
        self.pending_work = all([self.pending_work, date_plus_timedelta_gt_now(self.state['last_request'],
                                                                               self.state['update_frequency'])])

    def _decide_on_pending_work(self):
        """
            Private function that allows to change state with a logical decision.
            :raise StateChanged: If the logical decision is evaluated to False.
        """
        if not self.pending_work:
            raise StateChanged(self._transition_state, self._EXECUTION_CHECKED, self._check_execution)

    @Before(action=_decide_on_pending_work)
    @abstractmethod
    def _collect_data(self):
        """
            This method MUST be overridden, and must invoke super()._collect_data before performing further actions.
            Collects data from a data source, either from the Internet or from a local file.
        """
        pass

    @abstractmethod
    def _save_data(self):
        """
            This method MUST be overridden, and must invoke super()._save_data before performing further actions.
            Stores data into the persistent storage system. If wasn't done before, the 'collection' instance attribute
            is initialized at this point to be used.
            Precondition: Collected data must be JSON serializable, and saved in the 'data' instance attribute.
        """
        if not self.data and self.collection:
            self.collection.close()
            return
        for data in self.data:
            data[DGS_CONFIG['EXECUTION_ID_DOCUMENT_FIELD']] = builtins.EXECUTION_ID

    def _check_execution(self):
        """
            This method can be overridden, and must invoke super()._check_execution before performing further actions.
            Allows the data module to ensure all operations have successfully been executed, and determine if there is a
            need to relaunch the module, or not.
            This check can lead to positive or negative results, saved into the 'self.check_result' variable:
                - True if all collected elements were saved.
                - True if there was no pending work (self.pending_work is False).
                - True if data collection was deliberately stopped (self.advisedly_no_data_collected is True).
                - False otherwise.
        """
        if self.pending_work:
            if self.state['data_elements'] and self.state['inserted_elements']:
                if self.state['data_elements'] == self.state['inserted_elements']:
                    self.logger.info('All collected elements were saved. Execution was successful.')
                    self.check_result = True
                elif self.state['data_elements'] > self.state['inserted_elements']:
                    self.logger.warning('Data was collected, but not all elements were saved.')
                elif self.state['data_elements'] < self.state['inserted_elements']:
                    self.logger.error('More elements have been saved than collected. This should not be possible.')
            else:
                if self.advisedly_no_data_collected:
                    self.logger.info('Data collection has been deliberately omitted. This is OK.')
                    self.check_result = True
                elif self.state['data_elements'] > 0 and not self.state['inserted_elements']:
                    self.logger.warning('Data was collected, but not saved.')
        else:
            self.logger.info('There is no pending work. Execution was successful.')
            self.check_result = True

    def _save_state(self):
        """
            This method can be overridden, and must invoke super()._save_state AFTER performing further actions.
            Serializes all fields in the 'state' instance attribute to the '.state' file. All inner fields must be
            serialized before invoking super().
            Errors are also serialized, and current error's counter incremented, if there was an error and it's the same
            as the last error.
        """
        self.state['restart_required'] = True if self.state['error'] else False
        if self.state['error']:
            self.state['error'] = self.state['error']['class']
            self.state['errors'][self.state['error']] = self.state['errors'].get(self.state['error'], 0) + 1
            if self.state['last_error'] and self.state['error'] != self.state['last_error']:
                self.state['backoff_time'] = MIN_BACKOFF
            else:
                value, units = next_exponential_backoff(self.state['backoff_time'], MAX_BACKOFF_SECONDS)
                self.state['backoff_time'] = {'value': value, 'units': units}
            self.state['last_error'] = self.state['error']
            self.state['last_request'] = self.state['last_request'] if self.state['last_request'] \
                    else current_timestamp(utc=True)
        # FIXES [BUG-033].
        elif not self._backoff_prevented_execution:
            self.state['backoff_time'] = MIN_BACKOFF
        else:
            self.state['restart_required'] = True
        self.state['last_request'] = serialize_date(self.state['last_request'])
        write_state(self.state, self._file_path, DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
        self.logger.info('Successfully serialized state.')

    def _finish_execution(self):
        """
            Private function that allows the State Machine to reach the 'FINISHED' state.
        """
        pass

    def _pretty_format_transitions(self) -> str:
        """
            Formats the list of state transitions to be printed in a "friendly" way.
        """
        line = 'Execution States: '
        for transition in self._state_transitions:
            line += transition.name + ' -> '
        return line[:-4]  # Removing last ' -> '

    def _close_db_resources(self):
        """
            Attempts to close database resources (MongoDB collection), if those were initialized.
        """
        if self.collection:
            try:
                self.collection.close()
            except Exception:
                self.logger.exception('An error occurred while closing database resources.')

    def expose_transition_states(self, who) -> list:
        """
            Exposes internal transition states, but only to its "friend", a Supervisor instance.
            Caution: Only supervisor.Supervisor instances are allowed to use this method, since 'type' is used to check
            class membership, preventing malicious code (which inherit from the Supervisor class) from using this method.
            :param who: Any class who wants to know the internal transition states.
            :return: A list, containing the transition states if 'who' is a Supervisor; or None, otherwise.
        """
        from data_gathering_subsystem.supervisor.supervisor import DataCollectorSupervisor

        return self._state_transitions if type(who) is DataCollectorSupervisor else None

    def execute_actions(self, state: int, who) -> bool:
        """
            Executes the actions attached to a TransitionState, but only to its "friend", a Supervisor instance.
            Caution: Only supervisor.Supervisor instances are allowed to use this method, since 'type' is used to check
            class membership, preventing malicious code (which inherit from the Supervisor class) from using this method.
            :param state: TransitionState code.
            :param who: Any class who wants to execute TransitionState's actions.
            :return: True, if actions have been executed; otherwise, False.
        """
        from data_gathering_subsystem.supervisor.supervisor import DataCollectorSupervisor

        if not type(who) is DataCollectorSupervisor:
            return False
        if state == self._INITIALIZED and self._INITIALIZED.actions:
            self._INITIALIZED.actions()
        elif state == self._STATE_RESTORED and self._STATE_RESTORED.actions:
            self._STATE_RESTORED.actions()
        elif state == self._PENDING_WORK_CHECKED and self._PENDING_WORK_CHECKED.actions:
            self._PENDING_WORK_CHECKED.actions()
        elif state == self._DATA_COLLECTED and self._DATA_COLLECTED.actions:
            self._DATA_COLLECTED.actions()
        elif state == self._DATA_SAVED and self._DATA_SAVED.actions:
            self._DATA_SAVED.actions()
        elif state == self._EXECUTION_CHECKED and self._EXECUTION_CHECKED.actions:
            self._EXECUTION_CHECKED.actions()
        elif state == self._STATE_SAVED and self._STATE_SAVED.actions:
            self._STATE_SAVED.actions()
        return True

    def __str__(self):
        return self.__class__.__name__.replace('__', '')

    def __repr__(self):
        return str(self) + ' [' + \
               '\n\t(*) config: ' + self.config.__repr__() + \
               '\n\t(*) data: ' + self.data.__repr__() + \
               '\n\t(*) file path: ' + self._file_path.__repr__() + \
               '\n\t(*) transition_state: ' + self._transition_state.__str__() + \
               '\n\t(*) module_name: ' + self.module_name.__repr__() + \
               '\n\t(*) state: ' + self.state.__repr__() + ']\n'
