from abc import ABC, abstractmethod
from functools import wraps

from utilities.db_util import MongoDBCollection
from utilities.log_util import get_logger
from utilities.util import date_plus_timedelta_gt_now, deserialize_date, get_config, get_exception_info, \
    get_module_name, next_exponential_backoff, read_state, serialize_date, write_state


CREATED = 0
INITIALIZED = 10
STATE_RESTORED = 20
PENDING_WORK_CHECKED = 30
DATA_COLLECTED = 40
CLEAN_ACTIONS_ON_COLLECT_DATA = 41
DATA_SAVED = 50
CLEAN_ACTIONS_ON_SAVE_DATA = 51
EXECUTION_CHECKED = 60
CLEAN_ACTIONS_ON_CHECK_EXECUTION = 61
STATE_SAVED = 70
CLEAN_ACTIONS_ON_SAVE_STATE = 71
FINISHED = 80
ABORTED = 100

MIN_BACKOFF = {'value': 1, 'units': 's'}
MAX_BACKOFF_SECONDS = 86400  # One day


class Reader:
    """
        This class is used by DataCollectors which access to NASA files, allowing to retrieve all its useful data.
    """
    def __init__(self):
        self.data = []

    def __call__(self, s):
        if not s.startswith('HDR'):
            self.data.append(s)


class Before:
    """
    Executes an action before the DataCollector's decorated method execution.
    :param action: A function object.
    :return: Whatever callee returns.
    """
    def __init__(self, action):
        self.action = action

    def __call__(self, callee):
        @wraps(callee)
        def __post_action(*args):
            self.action(args[0])
            return callee(args[0])  # args[0] is the DataCollector object.

        return __post_action


class AbortedStateReachedError(RuntimeError):
    """
    This Exception should be raised when 'ABORTED' state is reached.
    """
    def __init__(self, message='Unhandled exception caused execution to be aborted.'):
        super(AbortedStateReachedError, self).__init__(message)


class StateChanged(BaseException):
    """
        This Exception does not represent an error. It's used to indicate the next state and the actions that need to be
        performed to reach it.
    """

    def __init__(self, current_state, next_state, actions):
        """
            Initializes the Exception.
            :param current_state: State from which the Exception is raised.
            :param next_state: State to reach.
            :param actions: A function that needs to be executed to reach that state.
        """
        self.actions = actions
        self.current_state = current_state
        self.next_state = next_state
        self.message = 'Transitioning from "%s" to "%s" by calling "%s".'%(current_state, next_state, actions.__name__)
        super(StateChanged, self).__init__(self.message)


class TransitionState:
    """
        This class represents a valid state within the set of data collector's states.
        Supports equality, comparisons and String representation.
    """

    def __init__(self, name: str, code: int, next_state, actions, on_error_state=None, clean_actions=None):
        """
            Initializes an state.
            :param name: State's name (to make it more readable). By convention, same name as variable.
            :param code: An unique, numerical identifier (to make comparisons between states faster).
        """
        self.name = name
        self.code = code
        self.next_state = next_state
        self.on_error_state = on_error_state
        self.actions = actions
        self.clean_actions = clean_actions

    def __eq__(self, other):
        if not isinstance(other, TransitionState):
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')
        return self.code == other.code

    def __gt__(self, other):
        if not isinstance(other, TransitionState):
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')
        return self.code > other.code

    def __lt__(self, other):
        if not isinstance(other, TransitionState):
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')
        return self.code < other.code

    def __ge__(self, other):
        if not isinstance(other, TransitionState):
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')
        return self.code >= other.code

    def __le__(self, other):
        if not isinstance(other, TransitionState):
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')
        return self.code <= other.code

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'TransitionState [' + \
               '\n\t(*) name: ' + self.name + \
               '\n\t(*) code: ' + str(self.code) + \
               '\n\t(*) next_state: ' + self.next_state.__str__() + \
               '\n\t(*) on_error: ' + self.on_error_state.__str__() + ']'


class DataCollector(ABC):
    """
       Base class for all DataCollectors. This class provides:
           - Default implementation in some methods.
           - Automatic flow control (by calling the 'run' method, all operations will also be invoked, in proper order).
           - Error handling: Any raised error is automatically handled, either by aborting the module execution, or
                             invoking a "cleaning" method (depending on the method it's currently being executed, and
                             whether cleaning actions are defined or not).
       To define a DataCollector that inherits from this class, it's strongly recommended to read this page in the
       repository Wiki: https://github.com/diego-hermida/DataGatheringSubsystem/wiki/Adding-a-DataCollector-module
    """

    def __initialize_states(self):
        """
            Private method that creates the TransitionState instances that will represent the module valid states and
            their interactions.
        """
        self.__ABORTED = TransitionState(name='ABORTED', code=ABORTED, next_state=None, actions=None)
        self.__FINISHED = TransitionState(name='FINISHED', code=FINISHED, next_state=None, actions=None)
        self.__CLEAN_ACTIONS_ON_SAVE_STATE = TransitionState(name='CLEAN_ACTIONS_ON_SAVE_STATE',
                code=CLEAN_ACTIONS_ON_SAVE_STATE, next_state=self.__FINISHED, actions=self.__finish_execution,
                on_error_state=self.__ABORTED, clean_actions=self._clean_actions_on_save_state)
        self.__STATE_SAVED = TransitionState(name='STATE_SAVED', code=STATE_SAVED, next_state=self.__FINISHED,
                actions=self.__finish_execution, on_error_state=self.__CLEAN_ACTIONS_ON_SAVE_STATE)
        self.__EXECUTION_CHECKED = TransitionState(name='EXECUTION_CHECKED', code=EXECUTION_CHECKED,
                next_state=self.__STATE_SAVED, actions=self._save_state,
                on_error_state=self.__CLEAN_ACTIONS_ON_SAVE_STATE)
        self.__CLEAN_ACTIONS_ON_CHECK_EXECUTION = TransitionState(name='CLEAN_ACTIONS_ON_CHECK_EXECUTION',
                code=CLEAN_ACTIONS_ON_CHECK_EXECUTION,next_state=self.__STATE_SAVED,  actions=self._save_state,
                on_error_state=self.__ABORTED, clean_actions=self._clean_actions_on_check_execution)
        self.__DATA_SAVED = TransitionState(name='DATA_SAVED', code=DATA_SAVED, next_state=self.__EXECUTION_CHECKED,
                actions=self._check_execution, on_error_state=self.__CLEAN_ACTIONS_ON_CHECK_EXECUTION)
        self.__CLEAN_ACTIONS_ON_SAVE_DATA = TransitionState(name='CLEAN_ACTIONS_ON_SAVE_DATA',
                code=CLEAN_ACTIONS_ON_SAVE_DATA, next_state=self.__EXECUTION_CHECKED, actions=self._check_execution,
                on_error_state=self.__ABORTED, clean_actions=self._clean_actions_on_save_data)
        self.__DATA_COLLECTED = TransitionState(name='DATA_COLLECTED', code=DATA_COLLECTED,
                next_state=self.__DATA_SAVED, actions=self._save_data, on_error_state=self.__CLEAN_ACTIONS_ON_SAVE_DATA)
        self.__CLEAN_ACTIONS_ON_COLLECT_DATA = TransitionState(name='CLEAN_ACTIONS_ON_COLLECT_DATA',
                code=CLEAN_ACTIONS_ON_COLLECT_DATA, next_state=self.__EXECUTION_CHECKED, actions=self._check_execution,
                on_error_state=self.__ABORTED, clean_actions=self._clean_actions_on_collect_data)
        self.__PENDING_WORK_CHECKED = TransitionState(name='PENDING_WORK_CHECKED', code=PENDING_WORK_CHECKED,
                next_state=self.__DATA_COLLECTED, actions=self._collect_data,
                on_error_state=self.__CLEAN_ACTIONS_ON_COLLECT_DATA)
        self.__STATE_RESTORED = TransitionState(name='STATE_RESTORED', code=STATE_RESTORED,
                next_state=self.__PENDING_WORK_CHECKED, actions=self._has_pending_work, on_error_state=self.__ABORTED)
        self.__INITIALIZED = TransitionState(name='INITIALIZED', code=INITIALIZED, next_state=self.__STATE_RESTORED,
                actions=self._restore_state, on_error_state=self.__ABORTED)
        self.__CREATED = TransitionState(name='CREATED', code=CREATED, next_state=self.__INITIALIZED, actions=None,
                on_error_state=self.__ABORTED)

    def run(self, close_db_resources_on_failure=True):
        """
            This method must NOT be overridden. Once a DataCollector instance is created, simply invoke this method to
            perform all operations. By inheriting from DataCollector, flow control and unexpected error handling are
            automatically provided.
            Further info available at: https://github.com/diego-hermida/DataGatheringSubsystem/wiki/Subsystem-Structure
        """
        if self.__transition_state != self.__ABORTED:
            self.logger.info('Starting Data Collector execution.')
            while self.__transition_state > self.__CREATED and self.__transition_state != self.__FINISHED:
                try:
                    self.__transition_state.actions()
                    self.__state_transitions.append(self.__transition_state.name)
                    self.__transition_state = self.__transition_state.next_state
                except StateChanged as state_transition_info:
                    self.__transition_state.next_state = state_transition_info.next_state
                    self.__transition_state.actions = state_transition_info.actions
                except Exception as actions_error:
                    error = AbortedStateReachedError()
                    self.__transition_state = self.__transition_state.on_error_state
                    if self.__transition_state > self.__STATE_RESTORED:  # Adding error info to 'state'
                        self.state['error'] = get_exception_info(actions_error)
                        if close_db_resources_on_failure and self.collection:
                            try:
                                self.collection.close()
                            except Exception:
                                self.logger.exception('An error occurred while closing database resources.')
                        if self.__transition_state.clean_actions:
                            try:
                                self.__transition_state.clean_actions()
                                self.logger.debug('Clean actions successfully performed for state "%s".'%
                                        (self.__transition_state))
                                continue
                            except NotImplementedError:
                                self.logger.error('An error was detected and clean actions were not defined for state '
                                        '"%s".'%(self.__transition_state))
                                self.__state_transitions.append(self.__transition_state.name)
                                self.__transition_state = self.__transition_state.on_error_state
                                error.__cause__ = actions_error
                                try:
                                    raise error
                                except AbortedStateReachedError as error:
                                    self.logger.exception(error)
                            except Exception as clean_actions_error:
                                self.__state_transitions.append(self.__transition_state.name)
                                clean_actions_error.__cause__ = actions_error
                                error.__cause__ = clean_actions_error
                                self.logger.exception('Clean actions failed for state "%s".'%(self.__transition_state))
                                self.__transition_state = self.__transition_state.on_error_state
                        else:
                            error.__cause__ = actions_error
                            self.logger.exception(error)
                    break
        self.__state_transitions.append(self.__transition_state.name)
        self.logger.info(self.__pretty_format_transitions() + '\n')

    def __init__(self, file_path):
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
        """
        self.__initialize_states()
        self.logger = get_logger(file_path, to_stdout=True)  # Needs to be initialized to log errors.
        self.__transition_state = self.__CREATED
        try:
            self.__file_path = file_path
            self.__state_transitions = []
            self.__state_transitions.append(self.__transition_state.name)
            self.collection = None
            self.data = None
            self.module_name = get_module_name(self.__file_path)
            self.pending_work = None
            self.state = None
            self.config = get_config(self.__file_path)
            self.advisedly_no_data_collected = False
            # Ensuring STATE_STRUCT has required fields. If not, a KeyError will be raised.
            missing_keys = []
            for key in get_config(__file__)['STATE_STRUCT']:
                try:
                    self.config['STATE_STRUCT'][key]
                except KeyError:
                    missing_keys.append(key)
            if missing_keys:
                raise AttributeError(
                        'STATE_STRUCT (".config" module file) must contain, at least, the fields defined in the default'
                        ' STATE_STRUCT (file: "data_collector.config"). Missing ones are: %s'%(missing_keys))
            self.__transition_state = self.__INITIALIZED
        except Exception:
            self.__transition_state = self.__ABORTED
            self.logger.exception('Module "%s" could not be initialized.'%(self))

    def _restore_state(self):
        """
            This method can be overridden, and must invoke super()._restore_state before performing further actions.
            Deserializes the '.state' file into a Python dict object. It also deserializes inner objects, such as
            datetime.datetime and others, and initializes 'volatile' fields.
        """
        self.state = read_state(self.__file_path, repair_struct=self.config['STATE_STRUCT'])
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
        self.pending_work = date_plus_timedelta_gt_now(self.state['last_request'], self.state['update_frequency'])
        if self.state['restart_required']:
            self.pending_work = date_plus_timedelta_gt_now(self.state['last_request'], self.state['backoff_time'])
            if self.pending_work:
                self.state['restart_required'] = False
            else:
                self.logger.info('Exponential backoff prevented data collection. Current backoff is: %d %s.'%
                        (self.state['backoff_time']['value'], self.state['backoff_time']['units']))

    def __decide_on_pending_work(self):
        """
            Private function that allows to change state with a logical decision.
            :raise StateChanged: If the logical decision is evaluated to False.
        """
        if not self.pending_work:
            raise StateChanged(self.__transition_state, self.__EXECUTION_CHECKED, self._check_execution)

    @Before(action=__decide_on_pending_work)
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
        if not self.data:
            self.collection.close()
        elif not self.collection:
            self.collection = MongoDBCollection(self.module_name)
        else:
            self.collection.connect(self.module_name)

    def _save_state(self):
        """
            This method can be overridden, and must invoke super()._save_state AFTER performing further actions.
            Serializes all fields in the 'state' instance attribute to the '.state' file. All inner fields must be
            serialized before invoking super().
            Errors are also serialized, and current error's counter incremented, if there was an error and it's the same
            as the last error.
        """
        if self.state['error']:
            self.state['error'] = self.state['error']['class']
            self.state['errors'][self.state['error']] = self.state['errors'].get(self.state['error'], 0) + 1
            if self.state['error'] == self.state['last_error']:
                next_exponential_backoff(self.state['backoff_time'], MAX_BACKOFF_SECONDS)
            else:
                self.state['backoff_time'] = MIN_BACKOFF
            self.state['last_error'] = self.state['error']
        self.state['last_request'] = serialize_date(self.state['last_request'])
        write_state(self.state, self.__file_path)
        self.logger.info('Successfully serialized state.')

    def _check_execution(self):
        """
            This method can be overridden, and must invoke super()._check_execution before performing further actions.
            Allows the data module to ensure all operations have successfully been executed, and determine if there is a
            need to relaunch the module, or not.
        """
        error = self.state.get('error', None)
        if error:
            self.logger.error(
                    'An error was detected. Cause is: \n' + self.state['error']['class'] + ': ' + self.state['error'][
                        'message'])
            if self.pending_work:
                self.state['restart_required'] = True
                self.logger.info('Data collection will be retried the next time Subsystem is launched.')
            else:
                self.logger.info('Since there is no pending work, next module execution will be carried out normally.')
        else:
            if self.pending_work:
                if self.state['data_elements'] and self.state['inserted_elements']:
                    if self.state['data_elements'] == self.state['inserted_elements']:
                        self.logger.info('All collected elements were saved. Execution was successful.')
                    elif self.state['data_elements'] > 0 and self.state['inserted_elements'] == 0:
                        self.logger.warning('Data was collected, but not saved.')
                    elif self.state['data_elements'] > self.state['inserted_elements']:
                        self.logger.warning('Data was collected, but not all elements were saved.')
                else:
                    if self.advisedly_no_data_collected:
                        self.logger.info('Data collection has been deliberately omitted. This is OK.')
                    else:
                        self.logger.warning('No error was detected. All the same, there was pending work but no data '
                                'has been saved. This issue should be revised.')
            else:
                self.logger.info('There is no pending work. Execution was successful.')

    def _clean_actions_on_collect_data(self):
        """
            This method can be overridden, and must NOT invoke the super() call.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_collect_data'. If an error occurs during the execution of this method, it will be automatically handled.
            Further info available at the repository Wiki:
                https://github.com/diego-hermida/DataGatheringSubsystem/wiki/Adding-a-DataCollector-module#clean-actions
        """
        raise NotImplementedError('Clean actions have not been implemented.')

    def _clean_actions_on_save_data(self):
        """
            This method can be overridden, and must NOT invoke the super() call.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_save_data'. If an error occurs during the execution of this method, it will be automatically handled.
            Further info available at the repository Wiki:
                https://github.com/diego-hermida/DataGatheringSubsystem/wiki/Adding-a-DataCollector-module#clean-actions
        """
        raise NotImplementedError('Clean actions have not been implemented.')

    def _clean_actions_on_save_state(self):
        """
            This method can be overridden, and must NOT invoke the super() call.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_save_state'. If an error occurs during the execution of this method, it will be automatically handled.
            Further info available at the repository Wiki:
                https://github.com/diego-hermida/DataGatheringSubsystem/wiki/Adding-a-DataCollector-module#clean-actions
        """
        raise NotImplementedError('Clean actions have not been implemented.')

    def _clean_actions_on_check_execution(self):
        """
            This method can be overridden, and must NOT invoke the super() call.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_check_execution'. If an error occurs during the execution of this method, it will be automatically
            handled.
            Further info available at the repository Wiki:
                https://github.com/diego-hermida/DataGatheringSubsystem/wiki/Adding-a-DataCollector-module#clean-actions
        """
        raise NotImplementedError('Clean actions have not been implemented.')

    def __finish_execution(self):
        """
            Private function that allows the State Machine to reach the 'FINISHED' state.
        """
        pass

    def __pretty_format_transitions(self) -> str:
        """
            Formats the list of state transitions to be printed in a "friendly" way.
        """
        line = 'Execution States: '
        for transition in self.__state_transitions:
            line += str(transition) + ' -> '
        return line[:-4] # Removing last ' -> '

    def __str__(self):
        return self.__class__.__name__.replace('__', '')

    def __repr__(self):
        return str(self) + ' [' + \
               '\n\t(*) config: ' + self.config.__repr__() + \
               '\n\t(*) data: ' + self.data.__repr__() + \
               '\n\t(*) file path: ' + self.__file_path.__repr__() + \
               '\n\t(*) transition_state: ' + self.__transition_state.__str__() + \
               '\n\t(*) module_name: ' + self.module_name.__repr__() + \
               '\n\t(*) state: ' + self.state.__repr__() + ']\n'
