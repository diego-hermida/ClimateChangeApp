from unittest import TestCase, mock
from unittest.mock import Mock

import utilities.execution_util


class TestExecutionUtil(TestCase):

    def test_message(self):
        from queue import Queue
        from threading import Condition

        channel = Queue(maxsize=1)
        condition = Condition()
        message = utilities.execution_util.Message(utilities.execution_util.MessageType.exit, content='Exit NOW')
        message.send(channel, condition)
        self.assertTrue(channel.not_empty)
        self.assertTrue(message, channel.get_nowait())

    def test_state_machine_thread(self):
        from queue import Queue
        from threading import Condition

        channel = Queue(maxsize=2)
        condition = Condition()
        runnable = utilities.execution_util.Runnable()
        thread = utilities.execution_util.RunnableComponentThread(runnable, channel, condition)
        thread.start()
        thread.join()
        self.assertTrue(channel.not_empty)
        self.assertEqual(2, channel.qsize())
        self.assertEqual(utilities.execution_util.MessageType.register, channel.get_nowait().type)
        self.assertEqual(utilities.execution_util.MessageType.finished, channel.get_nowait().type)

    def test_transition_state_comparison_errors(self):
        transition = utilities.execution_util.TransitionState('START', 0, None, None)

        with self.assertRaises(TypeError):
            self.assertLess(transition, 'foo')
        with self.assertRaises(TypeError):
            self.assertLessEqual(transition, 'foo')
        with self.assertRaises(TypeError):
            self.assertEqual(transition, 'foo')
        with self.assertRaises(TypeError):
            self.assertGreater(transition, 'foo')
        with self.assertRaises(TypeError):
            self.assertGreaterEqual(transition, 'foo')
        with self.assertRaises(TypeError):
            self.assertNotEqual(transition, 'foo')

    def test_transition_state_comparisons_with_TransitionState(self):
        transition2 = utilities.execution_util.TransitionState('FINISH', 1, None, None)
        transition1_copy = utilities.execution_util.TransitionState('START', 0, transition2, None)
        transition1 = utilities.execution_util.TransitionState('START', 0, transition2, None)

        self.assertGreater(transition2, transition1)
        self.assertGreaterEqual(transition2, transition1)
        self.assertLess(transition1, transition2)
        self.assertLessEqual(transition1, transition2)
        self.assertEqual(transition1, transition1_copy)
        self.assertNotEqual(transition1, transition2)

    def test_transition_state_comparisons_with_int(self):
        transition = utilities.execution_util.TransitionState('FINISH', 1, None, None)

        self.assertGreater(2, transition)
        self.assertGreaterEqual(1, transition)
        self.assertLess(0, transition)
        self.assertLessEqual(1, transition)
        self.assertEqual(1, transition)
        self.assertNotEqual(-1, transition)

    @mock.patch('utilities.execution_util.Supervisor.supervise', Mock(side_effect=Exception('Test error!')))
    def test_supervisor_with_error(self):
        s = utilities.execution_util.Supervisor()
        s.logger = Mock()
        utilities.execution_util.SupervisorThreadRunner(s).run()
        self.assertTrue(s.logger.exception.called)
