from unittest import TestCase, mock
from unittest.mock import Mock

import supervisor.supervisor as supervisor
from data_collector.data_collector import CONFIG, Message, MessageType
from test.data_collector.test_data_collector import SimpleDataCollector


class TestSupervisor(TestCase):

    @mock.patch('supervisor.supervisor.MongoDBCollection')
    @mock.patch('data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    def test_supervise(self, mock_collection):
        from queue import Queue
        from threading import Condition

        mock_collection.return_value.get_last_elements.return_value = None
        channel = Queue(maxsize=5)
        condition = Condition()
        # Creating supervisor and DataCollectors
        thread = supervisor.SupervisorThread(channel, condition, log_to_file=False, log_to_stdout=False)
        thread.supervisor.state = thread.supervisor.config['STATE_STRUCT']
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
        self.assertTrue(mock_collection.called)
        self.assertEqual(2, thread.supervisor.registered)
        self.assertEqual(2, thread.supervisor.unregistered)
        self.assertListEqual([d1, d2], thread.supervisor.registered_data_collectors)
        self.assertListEqual([str(d1)], thread.supervisor.successful_executions)
        self.assertListEqual([str(d2)], thread.supervisor.unsuccessful_executions)
        # Checking that failed modules have serialized errors and a restart is scheduled
        self.assertTrue(d2.state['restart_required'])
        self.assertIsNotNone(d2.state['error'])

    @mock.patch('supervisor.supervisor.write_state', Mock())
    @mock.patch('supervisor.supervisor.read_state', Mock(return_value={'execution_id': 0}))
    @mock.patch('supervisor.supervisor.MongoDBCollection')
    @mock.patch('data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    def test_generate_report(self, mock_collection):
        mock_collection.return_value.get_last_elements.return_value = None
        supervisor.EXECUTION_ID = 1
        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False)
        # First execution
        d1 = SimpleDataCollector(data_collected=1, data_inserted=1)
        d2 = SimpleDataCollector(fail_on='_save_data')
        d1.run()
        d2.run()
        s.verify_module_execution(d1)
        s.verify_module_execution(d2)
        s.registered_data_collectors = [d1, d2]
        s.registered = 2
        s.unregistered = 2
        time1 = 17.842170921
        s.generate_report(time1)
        self.assertTrue(mock_collection.called)
        self.assertEqual(time1, s.execution_report['last_execution']['duration'])
        self.assertEqual(2, s.execution_report['last_execution']['modules_executed'])
        self.assertEqual(2, s.execution_report['last_execution']['modules_with_pending_work'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_succeeded'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertEqual(['simple_data_collector'], s.execution_report['last_execution']['modules_failed']['modules'])
        self.assertEqual(2, s.execution_report['aggregated']['per_module']['simple_data_collector']['total_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['per_module']['simple_data_collector'][
            'succeeded_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['per_module']['simple_data_collector'][
            'succeeded_executions'])
        self.assertEqual(1, s.execution_report['last_execution']['collected_elements'])
        self.assertEqual(1, s.execution_report['last_execution']['inserted_elements'])
        self.assertFalse(s.execution_report['last_execution']['execution_succeeded'])
        self.assertEqual(1, s.execution_report['aggregated']['executions'])
        self.assertEqual(time1, s.execution_report['aggregated']['execution_time'])
        self.assertEqual(time1, s.execution_report['aggregated']['max_duration'])
        self.assertEqual(time1, s.execution_report['aggregated']['mean_duration'])
        self.assertEqual(time1, s.execution_report['aggregated']['min_duration'])
        self.assertEqual(0, s.execution_report['aggregated']['succeeded_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['failed_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['collected_elements'])
        self.assertEqual(1, s.execution_report['aggregated']['inserted_elements'])
        self.assertEqual([1],
                         s.execution_report['aggregated']['per_module']['simple_data_collector']['failure_details'][
                             'Exception'])

        # Second execution
        supervisor.EXECUTION_ID += 1
        execution_report = s.execution_report
        mock_collection.return_value.get_last_elements = Mock(return_value=execution_report['aggregated'])
        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False)
        d3 = SimpleDataCollector(data_collected=1234, data_inserted=1234)
        d4 = SimpleDataCollector(pending_work=False)
        d5 = SimpleDataCollector(data_collected=1, data_inserted=1)
        d3.run()
        d4.run()
        d5.run()
        s.verify_module_execution(d3)
        s.verify_module_execution(d4)
        s.verify_module_execution(d5)
        s.registered_data_collectors = [d3, d4, d5]
        s.registered = 3
        s.unregistered = 3
        time2 = 89.8219821
        s.generate_report(time2)
        self.assertTrue(mock_collection.called)
        self.assertEqual(time2, s.execution_report['last_execution']['duration'])
        self.assertEqual(3, s.execution_report['last_execution']['modules_executed'])
        self.assertEqual(3, s.execution_report['last_execution']['modules_succeeded'])
        self.assertEqual(0, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertIsNone(s.execution_report['last_execution']['modules_failed']['modules'])
        self.assertEqual(5, s.execution_report['aggregated']['per_module']['simple_data_collector']['total_executions'])
        self.assertEqual(4, s.execution_report['aggregated']['per_module']['simple_data_collector'][
            'executions_with_pending_work'])
        self.assertEqual(4, s.execution_report['aggregated']['per_module']['simple_data_collector'][
            'succeeded_executions'])
        self.assertEqual(1,
                         s.execution_report['aggregated']['per_module']['simple_data_collector']['failed_executions'])
        self.assertEqual(1235, s.execution_report['last_execution']['collected_elements'])
        self.assertEqual(1235, s.execution_report['last_execution']['inserted_elements'])
        self.assertTrue(s.execution_report['last_execution']['execution_succeeded'])
        self.assertEqual(2, s.execution_report['aggregated']['executions'])
        self.assertEqual(time2, s.execution_report['aggregated']['max_duration'])
        self.assertAlmostEqual(((time1 + time2) / 2), s.execution_report['aggregated']['mean_duration'], places=3)
        self.assertEqual(time1, s.execution_report['aggregated']['min_duration'])
        self.assertEqual(time1 + time2, s.execution_report['aggregated']['execution_time'])
        self.assertEqual(1, s.execution_report['aggregated']['succeeded_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['failed_executions'])
        self.assertEqual(1236, s.execution_report['aggregated']['collected_elements'])
        self.assertEqual(1236, s.execution_report['aggregated']['inserted_elements'])

        # Third execution
        supervisor.EXECUTION_ID += 1
        execution_report = s.execution_report
        mock_collection.return_value.get_last_elements = Mock(return_value=execution_report['aggregated'])
        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False)
        d6 = SimpleDataCollector(data_collected=1, data_inserted=1)
        d7 = SimpleDataCollector(fail_on='_restore_state')
        d8 = SimpleDataCollector(data_collected=0, data_inserted=0, pending_work=True, log_to_stdout=False)
        d6.run()
        d7.run()
        d8.run()
        s.verify_module_execution(d6)
        s.verify_module_execution(d7)
        s.verify_module_execution(d8)
        s.registered_data_collectors = [d6, d7, d8]
        s.registered = 3
        s.unregistered = 3
        time3 = 11.8219821
        s.generate_report(time3)
        self.assertTrue(mock_collection.called)
        self.assertEqual(time3, s.execution_report['last_execution']['duration'])
        self.assertEqual(3, s.execution_report['last_execution']['modules_executed'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_succeeded'])
        self.assertEqual(2, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertEqual(['simple_data_collector', 'simple_data_collector'], s.execution_report['last_execution'][
                'modules_failed']['modules'])
        self.assertEqual(8, s.execution_report['aggregated']['per_module']['simple_data_collector']['total_executions'])
        self.assertEqual(6, s.execution_report['aggregated']['per_module']['simple_data_collector'][
            'executions_with_pending_work'])
        self.assertEqual(5, s.execution_report['aggregated']['per_module']['simple_data_collector'][
            'succeeded_executions'])
        self.assertEqual(3,
                         s.execution_report['aggregated']['per_module']['simple_data_collector']['failed_executions'])
        self.assertEqual(1, s.execution_report['last_execution']['collected_elements'])
        self.assertEqual(1, s.execution_report['last_execution']['inserted_elements'])
        self.assertFalse(s.execution_report['last_execution']['execution_succeeded'])
        self.assertEqual(3, s.execution_report['aggregated']['executions'])
        self.assertEqual(time2, s.execution_report['aggregated']['max_duration'])
        self.assertAlmostEqual(((time1 + time2 + time3) / 3), s.execution_report['aggregated']['mean_duration'],
                               places=3)
        self.assertEqual(time3, s.execution_report['aggregated']['min_duration'])
        self.assertEqual(time1 + time2 + time3, s.execution_report['aggregated']['execution_time'])
        self.assertEqual(1, s.execution_report['aggregated']['succeeded_executions'])
        self.assertEqual(2, s.execution_report['aggregated']['failed_executions'])
        self.assertEqual(1237, s.execution_report['aggregated']['collected_elements'])
        self.assertEqual(1237, s.execution_report['aggregated']['inserted_elements'])
        self.assertEqual([3],
                         s.execution_report['aggregated']['per_module']['simple_data_collector']['failure_details'][
                             'Unknown cause'])
        self.assertEqual([3],
                         s.execution_report['aggregated']['per_module']['simple_data_collector']['failure_details'][
                             'PendingWorkAndNoDataCollectedError'])
