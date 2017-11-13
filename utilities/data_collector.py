from abc import ABC, abstractmethod
from functools import wraps
from utilities.db_util import MongoDBCollection
from utilities.log_util import get_logger
from utilities.util import get_config, get_module_name, read_state, write_state, date_plus_timedelta_gt_now, \
    serialize_date, deserialize_date


# ---------------------------- Utilities ----------------------------

class CatchAndRaise:
    """
    Uses Aspect Oriented Programming (AOP) to decouple a __transition_state's logic from exception handling. By decorating
    a method with this code, any exception raised by the callee is wrapped to the exception passed by argument. Example:

        @CatchAndRaise(MyError('Error!'))          (w/o decorator)      def divide(a: int, b: int) -> float
        def divide(a: int, b: int) -> float:              ->                  try:
            return a/b                                                          return a/b
                                                                            except ZeroDivisionError as ex:
                                                                                raise MyError('Error') from ex

        Explanation: If b=0, an ZeroDivisionError will be raised. If we want such method to raise a custom exception
        (like a MyError) without explicitly catching ZeroDivisionError and raising the custom exception, this
        decorator automatically does that job for us.
    :param exception: A Exception (or any subclass) instance, which will wrap any raised exception.
    :return: Whatever callee returns (if no exception is raised).
    :raises: Exception (or any subclass), if original __transition_state raises an exception.
    """

    def __init__(self, exception: Exception):
        self.__exception = exception

    def __call__(self, callee):
        @wraps(callee)
        def __catcher(*args, **kwargs):
            try:
                return callee(*args, **kwargs)
            except Exception as callee_exception:
                raise self.__exception from callee_exception

        return __catcher


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


# ---------------------------- Exceptions ----------------------------

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
        self.message = 'Transitioning from: ' + current_state.__str__() + ' to: ' + next_state.__str__() + \
                       ' by calling: ' + self.actions.__name__
        super(StateChanged, self).__init__(self.message)


class CleanActionsError(RuntimeError):
    """
        This Exception is used to encapsulate any error that might be caused during the execution of a <clean actions>
        method.
    """

    def __init__(self, message='An error occurred while performing clean actions.'):
        super(CleanActionsError, self).__init__(message)


# ---------------------------- Constants ----------------------------

CREATED = 0
INITIALIZED = 10
STATE_RESTORED = 20
PENDING_WORK_CHECKED = 30
DATA_COLLECTED = 40
DATA_SAVED = 50
STATE_SAVED = 60
EXECUTION_CHECKED = 70
FINISHED = 80
ABORTED = -1


# ---------------------------- Classes ----------------------------

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
        return isinstance(other, TransitionState) and self.code == other.code

    def __gt__(self, other):
        return isinstance(other, TransitionState) and self.code > other.code

    def __lt__(self, other):
        return isinstance(other, TransitionState) and self.code < other.code

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
           - Automatic flow control (by invoking the 'run' method, all operations will also be invoked, in proper order).
           - Error handling: Any raised error is automatically handled, either by aborting the module execution, or
                             invoking a "cleaning" method (depending on the method it's currently being executed).
    """

    def __initialize_states(self):
        """
        Private method that creates the TransitionState instances that will represent the module valid states and their
        interactions.
        """
        self.__ABORTED = TransitionState('ABORTED', ABORTED, None, None, None)
        self.__FINISHED = TransitionState('FINISHED', FINISHED, None, None)
        self.__EXECUTION_CHECKED = TransitionState('EXECUTION_CHECKED', EXECUTION_CHECKED, self.__FINISHED,
                                                   self.__finish_execution, self.__FINISHED)
        self.__STATE_SAVED = TransitionState('STATE_SAVED', STATE_SAVED, self.__EXECUTION_CHECKED,
                                             self._check_execution, self.__EXECUTION_CHECKED,
                                             self._clean_actions_on_check_execution)
        self.__DATA_SAVED = TransitionState('DATA_SAVED', DATA_SAVED, self.__STATE_SAVED, self._save_state,
                                            self.__STATE_SAVED, self._clean_actions_on_save_state)
        self.__DATA_COLLECTED = TransitionState('DATA_COLLECTED', DATA_COLLECTED, self.__DATA_SAVED, self._save_data,
                                                self.__STATE_SAVED, self._clean_actions_on_save_data)
        self.__PENDING_WORK_CHECKED = TransitionState('PENDING_WORK_CHECKED', PENDING_WORK_CHECKED,
                                                      self.__DATA_COLLECTED, self._collect_data, self.__STATE_SAVED,
                                                      self._clean_actions_on_collect_data)
        self.__STATE_RESTORED = TransitionState('STATE_RESTORED', STATE_RESTORED, self.__PENDING_WORK_CHECKED,
                                                self._has_pending_work, self.__ABORTED)
        self.__INITIALIZED = TransitionState('INITIALIZED', INITIALIZED, self.__STATE_RESTORED, self._restore_state,
                                             self.__ABORTED)
        self.__CREATED = TransitionState('CREATED', CREATED, self.__INITIALIZED, None, self.__ABORTED)

    def run(self):
        """

        :return:
        """
        try:
            assert self.__transition_state == self.__INITIALIZED
        except AssertionError:
            self.logger.error('Aborting execution due to bad initialization.')
        if self.__transition_state != self.__ABORTED:
            while self.__transition_state != self.__FINISHED:
                try:
                    self.__transition_state.actions()
                    self.__state_transitions.append(self.__transition_state.name)
                    self.__transition_state = self.__transition_state.next_state
                except StateChanged as state_transition_info:
                    self.__transition_state.next_state = state_transition_info.next_state
                    self.__transition_state.actions = state_transition_info.actions
                except Exception as actions_error:
                    try:
                        self.__transition_state.clean_actions()
                        self.logger.info('Clean actions (' + self.__transition_state.clean_actions.__name__ +
                                         ') successfully performed. Next state: ' +
                                         self.__transition_state.next_state.__str__())
                        self.__transition_state = self.__transition_state.next_state
                    except CleanActionsError as clean_actions_error:
                        # Error: AbortedStateReachedError (caused by) CleanActionsError (caused by) Exception, raised
                        # while performing clean actions, (caused by) Exception, raised while performing main actions.
                        clean_actions_error.__cause__.__cause__ = actions_error
                        aborted_state_error = AbortedStateReachedError()
                        aborted_state_error.__cause__ = clean_actions_error
                        self.logger.exception(aborted_state_error)
                        self.__transition_state = self.__ABORTED
                        break
        self.__state_transitions.append(self.__transition_state.name)
        self.logger.info('States (' + self.__class__.__name__.replace('__', '') + '): ' + str(self.__state_transitions))

    def __init__(self, file_path):
        """
        This method can be overridden, and must invoke super().__init__ before performing further actions.
        Any DataCollector which inherits from this class has the following (public) attributes:
            - collection: An abstraction to a MongoDB Collection, with a valid connection to the database, which will
                          be initialized the first time it's used.
            - config: Stores the module configuration (deserializes the '.config' file).
            - data: Stores the collected data (in-memory).
            - logger: A custom logging.logger instance.
            - module_name: The name of the current module (got from 'file_path').
            - pending_work: True if module needs to download data, False otherwise. This
                            attribute will be initialized later, in '_has_pending_work'.
            - state: Stores the module conditions (deserializes the '.state' file).  This attribute will be initialized
                     later, in '_restore_state'.
        :param file_path: File path to '.py' file. '__file__' should always be passed as the 'file_path' parameter.
                          Example:
                              # Previous actions
                              data_collector = MyDataCollector(file_path=__file__)
                              # Following actions
        """
        self.__initialize_states()
        self.logger = get_logger(file_path, to_stdout=True)  # Needs to be initialized to log any error.
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
            self.__transition_state = self.__INITIALIZED
        except Exception:
            self.__transition_state = self.__ABORTED
            self.logger.exception('Module "' + self.__str__() + '" could not be initialized.')

    def _restore_state(self):
        """
            This method can be overridden, and must invoke super()._restore_state before performing further actions.
            Deserializes the '.state' file into a Python dict object. It also deserializes inner objects, such as
            datetime.datetime and others.
        """
        self.state = read_state(self.__file_path, repair_struct=self.config['STATE_STRUCT'])
        if self.state == self.config['STATE_STRUCT']:
            self.logger.warning('State file could not be read. Restoring state with STATE_STRUCT.')
        self.state['last_request'] = deserialize_date(self.state['last_request'])  # Creates datetime object

    def _has_pending_work(self):
        """
            This method can be overridden, and must invoke super()._has_pending_work before performing further actions.
            Checks whether module has to collect data or not. The result must be saved in the 'pending_work' instance
            attribute.
        """
        self.pending_work = date_plus_timedelta_gt_now(self.state['last_request'], self.state['update_frequency'])

    def __decide_on_pending_work(self):
        """
            Private function that allows to change state with a logical decision.
            :raise StateChanged: If the logical decision is evaluated to False.
        """
        if not self.pending_work:
            raise StateChanged(self.__transition_state, self.__STATE_SAVED, self._save_state)

    @Before(action=__decide_on_pending_work)
    @abstractmethod
    def _collect_data(self):
        """
            This method MUST be overridden, and must invoke super()._collect_data before performing further actions.
            Collects data from a data source, either from the Internet or from a local file. As a postcondition,
            collected data must be JSON serializable, and saved in the 'data' instance attribute.
        """
        pass

    @abstractmethod
    def _save_data(self):
        """
            This method MUST be overridden, and must invoke super()._save_data before performing further actions.
            Stores data into the persistent storage system. If wasn't done before, the 'collection' instance attribute is
            initialized at this point to be used.
        """
        if not self.data:
            return
        else:
            # Initializing database connection to collection
            self.collection = MongoDBCollection(self.module_name)

    def _save_state(self):
        """
            This method can be overridden, and must invoke super()._save_state AFTER performing further actions.
            Serializes all fields in the 'state' instance attribute to the '.state' file. All inner fields must be
            serialized before invoking super().
        """
        self.state['last_request'] = serialize_date(self.state['last_request'])
        write_state(self.state, self.__file_path)
        self.logger.info('Successfully serialized state.')

    @abstractmethod
    def _check_execution(self):
        """
            This method MUST be overridden, and must invoke super()._check_execution before performing further actions.
            Allows the data module to ensure all operations have successfully been executed, and determine if there is a
            need to relaunch the module, or not.
        """
        pass

    @CatchAndRaise(exception=CleanActionsError())
    def _clean_actions_on_collect_data(self):
        """
            This method MUST be overridden, and must invoke super()._clean_actions_on_collect_data before performing
            further actions.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_collect_data'. If an error occurs during the execution of this method, it will be encapsulated and
            re-raised as a CleanActionsError, and automatically handled.
        """
        pass

    @CatchAndRaise(exception=CleanActionsError())
    def _clean_actions_on_save_data(self):
        """
            This method MUST be overridden, and must invoke super()._clean_actions_on_save_data before performing
            further actions.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_save_data'. If an error occurs during the execution of this method, it will be encapsulated and
            re-raised as a CleanActionsError, and automatically handled.
        """
        pass

    @CatchAndRaise(exception=CleanActionsError())
    def _clean_actions_on_save_state(self):
        """
            This method MUST be overridden, and must invoke super()._clean_actions_on_save_state before performing
            further actions.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_save_state'. If an error occurs during the execution of this method, it will be encapsulated and
            re-raised as a CleanActionsError, and automatically handled.
        """
        pass

    @CatchAndRaise(exception=CleanActionsError())
    def _clean_actions_on_check_execution(self):
        """
            This method MUST be overridden, and must invoke super()._clean_actions_on_check_execution before performing
            further actions.
            If overridden, allows the data module to establish cleaning actions if an error occurs during the execution
            of '_check_execution'. If an error occurs during the execution of this method, it will be encapsulated and
            re-raised as a CleanActionsError, and automatically handled.
        """
        pass

    def __finish_execution(self):
        """
            Private mock function that allows reaching the 'FINISHED' state.
        """
        pass

    def __str__(self):
        return self.__class__.__name__.replace('__', '')

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.config.__repr__() + \
            '\n\t(*) data: ' + self.data.__repr__() + \
            '\n\t(*) file path: ' + self.__file_path.__repr__() + \
            '\n\t(*) transition_state: ' + self.__transition_state.__str__() + \
            '\n\t(*) module_name: ' + self.module_name.__repr__() + \
            '\n\t(*) state: ' + self.state.__repr__() + ']\n'
