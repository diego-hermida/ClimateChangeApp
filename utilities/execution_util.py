from abc import abstractmethod
from functools import wraps
from queue import Queue
from threading import Condition, Thread
from utilities.util import enum

MessageType = enum('register', 'finished', 'report', 'exit')


class Runnable:
    """
        Provides the "run" method.
    """

    @abstractmethod
    def run(self):
        pass


class Supervisor:
    """
        Provides the "supervise" method.
    """

    @abstractmethod
    def supervise(self):
        pass


class SupervisorThreadRunner(Thread):
    """
        This class allows a Supervisor instance to be executed in its own thread.
        The thread is set as a Daemon thread, as we want the thread to be stopped when Main component exits.
    """
    def __init__(self, supervisor):
        self.supervisor = supervisor
        Thread.__init__(self)
        self.setDaemon(True)
        self.setName('SupervisorThread')

    def run(self):
        try:
            self.supervisor.supervise()
        except Exception:
            if self.supervisor.logger:
                self.supervisor.logger.exception('Supervisor execution has been aborted due to an error.')


class RunnableComponentThread(Thread):
    """
        The purpose of this class is to run a Runnable inside its own thread.
    """

    def __init__(self, runnable: Runnable, channel: Queue = None, condition: Condition = None):
        """
            Creates a Thread instance. Name is set as <Runnable>Thread, being <Runnable> the name of the
            Runnable class. This class must implement a "run" method.
            The thread is set as a Daemon thread, as we want the thread to be stopped when Main component exits.
            :param runnable: An object of class Runnable.
            :param channel: A synchronized queue, which allows passing messages between threads and the Supervisor.
            :param condition: A Condition object, to notify the Supervisor.
        """
        self._channel = channel
        self._condition = condition
        self._executable = runnable
        Thread.__init__(self)
        self.setDaemon(True)
        self.setName(self._executable.__str__() + 'Thread')

    def run(self):
        """
            Runs the StateMachine.
            Before running, sends a "register" message to the Supervisor (if "channel" and "condition" are set).
            Regardless of the execution result (errors are automatically handled), a "finished" message will be sent
            to the Supervisor (if "channel" and "condition" are set).
        """
        if self._channel and self._condition:
            Message(MessageType.register, content=self._executable).send(self._channel, self._condition)
        self._executable.run()
        if self._channel and self._condition:
            Message(MessageType.finished, content=self._executable).send(self._channel, self._condition)


class Message:
    """
        Provides an unified interface to send messages through a shared channel.
    """

    def __init__(self, message_type: MessageType, content=None):
        self.type = message_type
        self.content = content

    def send(self, channel: Queue, condition: Condition):
        """
            Sends the message itself through the channel.
            :param channel: A synchronized queue.Queue object.
            :param condition: A threading.Condition object, which notifies the receiver that a message has arrived.
        """
        condition.acquire()
        channel.put_nowait(self)
        condition.notify()
        condition.release()

    def __str__(self):
        return 'Message [\n\t(*) type: ' + self.type + '\n\t(*) content: ' + str(self.content) + ']'


class Before:
    """
        Executes an action before the decorated method execution.
        :param action: A function object.
        :return: Whatever callee returns.
    """

    def __init__(self, action):
        self.action = action

    def __call__(self, callee):
        @wraps(callee)
        def post_action(*args):
            self.action(args[0])
            return callee(args[0])  # args[0] is the calling object.
        return post_action


class AbortedStateReachedError(RuntimeError):
    """
        This Exception should be raised when 'ABORTED' state is reached.
    """

    def __init__(self, message='Unhandled exception caused execution to be aborted.', cause=None):
        super(AbortedStateReachedError, self).__init__(message)
        if cause:
            self.__cause__ = cause


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
        self.message = 'Transitioning from "%s" to "%s" by calling "%s".' % (
            current_state, next_state, actions.__name__)
        super(StateChanged, self).__init__(self.message)


class TransitionState:
    """
        This class represents a valid state within the set of StateMachine's states.
        Supports equality, comparisons and String representation.
    """

    def __init__(self, name: str, code: int, next_state, actions: callable):
        """
            Initializes an state.
            :param name: State's name (to make it more readable).
            :param code: An unique, numerical identifier (to make comparisons between states faster).
            :param next_state: If actions succeeded, this determines the subsequent state.
            :param actions: Callable object (i.e. function).
        """
        self.name = name
        self.code = code
        self.next_state = next_state
        self.actions = actions

    def __eq__(self, other):
        if isinstance(other, TransitionState):
            return self.code == other.code
        elif isinstance(other, int):
            return self.code == other
        else:
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')

    def __ne__(self, other):
        if isinstance(other, TransitionState):
            return self.code != other.code
        elif isinstance(other, int):
            return self.code != other
        else:
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')

    def __gt__(self, other):
        if isinstance(other, TransitionState):
            return self.code > other.code
        elif isinstance(other, int):
            return self.code > other
        else:
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')

    def __lt__(self, other):
        if isinstance(other, TransitionState):
            return self.code < other.code
        elif isinstance(other, int):
            return self.code < other
        else:
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')

    def __ge__(self, other):
        if isinstance(other, TransitionState):
            return self.code >= other.code
        elif isinstance(other, int):
            return self.code >= other
        else:
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')

    def __le__(self, other):
        if isinstance(other, TransitionState):
            return self.code <= other.code
        elif isinstance(other, int):
            return self.code <= other
        else:
            raise TypeError("<<class 'TransitionState'>> cannot be compared with <" + str(type(other)) + '>.')

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'TransitionState [' + '\n\t(*) name: ' + self.name + '\n\t(*) code: ' + str(
                self.code) + '\n\t(*) next_state: ' + self.next_state.__str__() + ']'
