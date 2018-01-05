from data_collector.data_collector import CONFIG, Message, MessageType
from test.data_collector.test_data_collector import SimpleDataCollector
from unittest import TestCase, main, mock
from unittest.mock import Mock

import supervisor.supervisor as supervisor


class TestSupervisor(TestCase):

    @mock.patch('data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    @mock.patch('supervisor.supervisor.read_state', Mock())
    def test_supervise(self):
        from queue import Queue
        from threading import Condition
        channel = Queue(maxsize=5)
        condition = Condition()
        s = supervisor.instance(channel, condition)
        s.state = s.config['STATE_STRUCT']
        # Creating supervisor and DataCollectors
        thread = supervisor.SupervisorThread(channel, condition)
        d1 = SimpleDataCollector(data_collected=1, data_inserted=1)
        d2 = SimpleDataCollector(fail_on='_save_data')
        # Starting supervisor
        thread.start()
        # Registering DataCollectors
        Message(MessageType.register, content=d1).send(channel, condition)
        Message(MessageType.register, content=d2).send(channel, condition)
        # Simulating run
        d1.run()
        d2.run()
        # Unregistering DataCollectors
        Message(MessageType.finished, content=d1).send(channel, condition)
        Message(MessageType.finished, content=d2).send(channel, condition)
        # Make Supervisor exit, and waiting until it has finished
        Message(MessageType.exit).send(channel, condition)
        thread.join()
        self.assertEqual(2, s.registered)
        self.assertEqual(2, s.unregistered)
        self.assertListEqual([d1, d2], s.registered_data_collectors)
        self.assertListEqual([str(d1)], s.successful_executions)
        self.assertListEqual([str(d2)], s.unsuccessful_executions)
        # Checking that failed modules have serialized errors and a restart is scheduled
        self.assertTrue(d2.state['restart_required'])
        self.assertIsNotNone(d2.state['error'])

    @mock.patch('data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    @mock.patch('supervisor.supervisor.write_state', Mock())
    @mock.patch('supervisor.supervisor.read_state', Mock(return_value='/foo/bar/baz/supervisor.state'))
    def test_generate_report(self):
        s = supervisor.Supervisor(None, None)
        s.state = s.config['STATE_STRUCT']
        # First execution
        d1 = SimpleDataCollector(data_collected=1, data_inserted=1)
        d2 = SimpleDataCollector(fail_on='_save_data')
        d1.run()
        d2.run()
        s.registered_data_collectors = [d1, d2]
        s.registered = 2
        s.unregistered = 2
        s.successful_executions = [str(d1)]
        s.unsuccessful_executions = [str(d2)]
        time1 = 17.842170921
        s.generate_report(time1)
        self.assertEqual(time1, s.state['last_execution']['duration'])
        self.assertEqual(2, s.state['last_execution']['modules_executed'])
        self.assertEqual(1, s.state['last_execution']['modules_succeeded'])
        self.assertEqual(1, s.state['last_execution']['modules_failed'])
        self.assertEqual(1, s.state['last_execution']['collected_elements'])
        self.assertEqual(1, s.state['last_execution']['inserted_elements'])
        self.assertFalse(s.state['last_execution']['execution_succeeded'])
        self.assertEqual(1, s.state['aggregated']['total_executions'])
        self.assertEqual(time1, s.state['aggregated']['total_execution_time'])
        self.assertEqual(time1, s.state['aggregated']['mean_duration'])
        self.assertEqual(0, s.state['aggregated']['total_succeeded_executions'])
        self.assertEqual(1, s.state['aggregated']['total_failed_executions'])
        self.assertEqual(1, s.state['aggregated']['total_collected_elements'])
        self.assertEqual(1, s.state['aggregated']['total_inserted_elements'])

        # Second execution
        state = s.state
        s = supervisor.Supervisor(None, None)
        s.state = state
        d3 = SimpleDataCollector(data_collected=1234, data_inserted=1234)
        d4 = SimpleDataCollector(data_collected=2, data_inserted=2)
        d5 = SimpleDataCollector(data_collected=1, data_inserted=1)
        d3.run()
        d4.run()
        d5.run()
        s.registered_data_collectors = [d3, d4, d5]
        s.registered = 3
        s.unregistered = 3
        s.successful_executions = [str(d3), str(d4), str(d5)]
        s.unsuccessful_executions = []
        time2 = 89.8219821
        s.generate_report(time2)
        self.assertEqual(time2, s.state['last_execution']['duration'])
        self.assertEqual(3, s.state['last_execution']['modules_executed'])
        self.assertEqual(3, s.state['last_execution']['modules_succeeded'])
        self.assertEqual(0, s.state['last_execution']['modules_failed'])
        self.assertEqual(1237, s.state['last_execution']['collected_elements'])
        self.assertEqual(1237, s.state['last_execution']['inserted_elements'])
        self.assertTrue(s.state['last_execution']['execution_succeeded'])
        self.assertEqual(2, s.state['aggregated']['total_executions'])
        self.assertAlmostEqual(((time1 + time2) / 2), s.state['aggregated']['mean_duration'], places=3)
        self.assertEqual(time1 + time2, s.state['aggregated']['total_execution_time'])
        self.assertEqual(1, s.state['aggregated']['total_succeeded_executions'])
        self.assertEqual(1, s.state['aggregated']['total_failed_executions'])
        self.assertEqual(1238, s.state['aggregated']['total_collected_elements'])
        self.assertEqual(1238, s.state['aggregated']['total_inserted_elements'])
