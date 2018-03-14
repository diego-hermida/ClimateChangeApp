from copy import deepcopy
from os import environ
from unittest import TestCase, mock
from unittest.mock import Mock

from data_conversion_subsystem.data_converter.data_converter import CONFIG, Message, MessageType
from data_conversion_subsystem.supervisor import supervisor as supervisor
from data_conversion_subsystem.test.data_converter.test_data_converter import SimpleDataConverter

ENVIRON = deepcopy(environ)
ENVIRON['API_IP'] = 'test_ip'
ENVIRON['POSTGRES_IP'] = 'test_ip'


def _side_effect(*args, **kwargs):
    raise supervisor.AggregatedStatistics.DoesNotExist('Test error.')


@mock.patch('data_conversion_subsystem.data_converter.data_converter.write_state', Mock())
@mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config', Mock(return_value=CONFIG))
@mock.patch('os.environ', ENVIRON)
class TestSupervisor(TestCase):

    @mock.patch('requests.get')
    def test_supervise(self, mock_requests):
        from queue import Queue
        from threading import Condition

        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}]}'.encode()

        channel = Queue(maxsize=5)
        condition = Condition()
        # Creating supervisor and DataCollectors
        thread = supervisor.SupervisorThread(channel, condition, log_to_file=False, log_to_stdout=False,
                                             log_to_telegram=False)
        thread.supervisor.state = thread.supervisor.config['STATE_STRUCT']
        d1 = SimpleDataConverter(elements_to_convert=1, data_converted=1, data_inserted=1, log_to_stdout=False,
                                 log_to_telegram=False)
        d2 = SimpleDataConverter(fail_on='_has_pending_work', log_to_stdout=False, log_to_telegram=False)
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
        self.assertEqual(2, thread.supervisor.registered)
        self.assertEqual(2, thread.supervisor.unregistered)
        self.assertListEqual([d1, d2], thread.supervisor.registered_data_converters)
        self.assertListEqual([str(d1)], thread.supervisor.successful_executions)
        self.assertListEqual([str(d2)], thread.supervisor.unsuccessful_executions)
        # Checking that failed modules have serialized errors and a restart is scheduled
        self.assertTrue(d2.state['restart_required'])
        self.assertIsNotNone(d2.state['error'])

    @mock.patch('requests.get')
    @mock.patch('data_conversion_subsystem.supervisor.supervisor.ExecutionStatistics', Mock())
    @mock.patch('data_conversion_subsystem.supervisor.supervisor.AggregatedStatistics.save', Mock())
    @mock.patch('data_conversion_subsystem.supervisor.supervisor.AggregatedStatistics.objects.get',
                Mock(side_effect=_side_effect))
    def test_generate_report_first_time(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}]}'.encode()

        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        # First execution
        d1 = SimpleDataConverter(fail_on='_has_pending_work', log_to_stdout=False, log_to_telegram=False)
        d2 = SimpleDataConverter(elements_to_convert=1, data_converted=1, data_inserted=1, log_to_stdout=False,
                                 log_to_telegram=False)
        d1.run()
        d2.run()
        s.verify_module_execution(d1)
        s.verify_module_execution(d2)
        s.registered_data_converters = [d1, d2]
        s.registered = 2
        s.unregistered = 2
        time1 = 17.842170921
        s.generate_report(time1)
        self.assertEqual(time1, s.execution_report['last_execution']['duration'])
        self.assertEqual(2, s.execution_report['last_execution']['modules_executed'])
        self.assertDictEqual(
                {'simple_data_converter': {'elements_to_convert': 1, 'converted_elements': 1, 'inserted_elements': 1}},
                s.execution_report['last_execution']['modules_with_pending_work'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_succeeded'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertEqual(['simple_data_converter'], s.execution_report['last_execution']['modules_failed']['modules'])
        self.assertEqual(2, s.execution_report['aggregated']['per_module']['simple_data_converter']['total_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['per_module']['simple_data_converter'][
            'succeeded_executions'])
        self.assertEqual(1,
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failed_executions'])
        self.assertEqual(1, s.execution_report['last_execution']['elements_to_convert'])
        self.assertEqual(1, s.execution_report['last_execution']['converted_elements'])
        self.assertEqual(1, s.execution_report['last_execution']['inserted_elements'])
        self.assertFalse(s.execution_report['last_execution']['execution_succeeded'])
        self.assertEqual(1, s.execution_report['aggregated']['executions'])
        self.assertEqual(time1, s.execution_report['aggregated']['execution_time'])
        self.assertEqual(time1, s.execution_report['aggregated']['max_duration'])
        self.assertEqual(time1, s.execution_report['aggregated']['mean_duration'])
        self.assertEqual(time1, s.execution_report['aggregated']['min_duration'])
        self.assertEqual(0, s.execution_report['aggregated']['succeeded_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['failed_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['elements_to_convert'])
        self.assertEqual(1, s.execution_report['aggregated']['converted_elements'])
        self.assertEqual(1, s.execution_report['aggregated']['inserted_elements'])
        self.assertEqual([None],
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failure_details'][
                             'Exception'])

    @mock.patch('data_conversion_subsystem.supervisor.supervisor.AggregatedStatistics.objects')
    @mock.patch('data_conversion_subsystem.supervisor.supervisor.AggregatedStatistics', Mock())
    @mock.patch('data_conversion_subsystem.supervisor.supervisor.ExecutionStatistics', Mock())
    @mock.patch('requests.get')
    def test_generate_report(self, mock_requests, mock_aggregated_statistics):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}]}'.encode()
        mock_aggregated_statistics.get.return_value = data = Mock()
        data.data = supervisor.CONFIG['STATE_STRUCT']['aggregated']

        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        # First execution
        d1 = SimpleDataConverter(fail_on='_has_pending_work', log_to_stdout=False, log_to_telegram=False)
        d2 = SimpleDataConverter(elements_to_convert=1, data_converted=1, data_inserted=1, log_to_stdout=False,
                                 log_to_telegram=False)
        d1.run()
        d2.run()
        s.verify_module_execution(d1)
        s.verify_module_execution(d2)
        s.registered_data_converters = [d1, d2]
        s.registered = 2
        s.unregistered = 2
        time1 = 17.842170921
        s.generate_report(time1)
        self.assertEqual(time1, s.execution_report['last_execution']['duration'])
        self.assertEqual(2, s.execution_report['last_execution']['modules_executed'])
        self.assertDictEqual(
                {'simple_data_converter': {'elements_to_convert': 1, 'converted_elements': 1, 'inserted_elements': 1}},
                s.execution_report['last_execution']['modules_with_pending_work'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_succeeded'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertEqual(['simple_data_converter'], s.execution_report['last_execution']['modules_failed']['modules'])
        self.assertEqual(2, s.execution_report['aggregated']['per_module']['simple_data_converter']['total_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['per_module']['simple_data_converter'][
            'succeeded_executions'])
        self.assertEqual(1,
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failed_executions'])
        self.assertEqual(1, s.execution_report['last_execution']['elements_to_convert'])
        self.assertEqual(1, s.execution_report['last_execution']['converted_elements'])
        self.assertEqual(1, s.execution_report['last_execution']['inserted_elements'])
        self.assertFalse(s.execution_report['last_execution']['execution_succeeded'])
        self.assertEqual(1, s.execution_report['aggregated']['executions'])
        self.assertEqual(time1, s.execution_report['aggregated']['execution_time'])
        self.assertEqual(time1, s.execution_report['aggregated']['max_duration'])
        self.assertEqual(time1, s.execution_report['aggregated']['mean_duration'])
        self.assertEqual(time1, s.execution_report['aggregated']['min_duration'])
        self.assertEqual(0, s.execution_report['aggregated']['succeeded_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['failed_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['elements_to_convert'])
        self.assertEqual(1, s.execution_report['aggregated']['converted_elements'])
        self.assertEqual(1, s.execution_report['aggregated']['inserted_elements'])
        self.assertEqual([None],
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failure_details'][
                             'Exception'])
        # Second execution
        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        d3 = SimpleDataConverter(elements_to_convert=1234, data_converted=1234, data_inserted=1234)
        d4 = SimpleDataConverter(pending_work=False)
        d5 = SimpleDataConverter(elements_to_convert=1, data_converted=1, data_inserted=1)
        d3.run()
        d4.run()
        d5.run()
        s.verify_module_execution(d3)
        s.verify_module_execution(d4)
        s.verify_module_execution(d5)
        s.registered_data_converters = [d3, d4, d5]
        s.registered = 3
        s.unregistered = 3
        time2 = 89.8219821
        s.generate_report(time2)
        self.assertEqual(time2, s.execution_report['last_execution']['duration'])
        self.assertEqual(3, s.execution_report['last_execution']['modules_executed'])
        self.assertEqual(3, s.execution_report['last_execution']['modules_succeeded'])
        self.assertDictEqual(
                {'simple_data_converter': {'elements_to_convert': 1, 'converted_elements': 1, 'inserted_elements': 1}},
                s.execution_report['last_execution']['modules_with_pending_work'])
        self.assertEqual(0, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertIsNone(s.execution_report['last_execution']['modules_failed']['modules'])
        self.assertEqual(5, s.execution_report['aggregated']['per_module']['simple_data_converter']['total_executions'])
        self.assertEqual(4, s.execution_report['aggregated']['per_module']['simple_data_converter'][
            'executions_with_pending_work'])
        self.assertEqual(4, s.execution_report['aggregated']['per_module']['simple_data_converter'][
            'succeeded_executions'])
        self.assertEqual(1,
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failed_executions'])
        self.assertEqual(1235, s.execution_report['last_execution']['elements_to_convert'])
        self.assertEqual(1235, s.execution_report['last_execution']['converted_elements'])
        self.assertEqual(1235, s.execution_report['last_execution']['inserted_elements'])
        self.assertTrue(s.execution_report['last_execution']['execution_succeeded'])
        self.assertEqual(2, s.execution_report['aggregated']['executions'])
        self.assertEqual(time2, s.execution_report['aggregated']['max_duration'])
        self.assertAlmostEqual(((time1 + time2) / 2), s.execution_report['aggregated']['mean_duration'], places=3)
        self.assertEqual(time1, s.execution_report['aggregated']['min_duration'])
        self.assertEqual(time1 + time2, s.execution_report['aggregated']['execution_time'])
        self.assertEqual(1, s.execution_report['aggregated']['succeeded_executions'])
        self.assertEqual(1, s.execution_report['aggregated']['failed_executions'])
        self.assertEqual(1236, s.execution_report['aggregated']['elements_to_convert'])
        self.assertEqual(1236, s.execution_report['aggregated']['converted_elements'])
        self.assertEqual(1236, s.execution_report['aggregated']['inserted_elements'])

        # Third execution
        s = supervisor.Supervisor(None, None, log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        d6 = SimpleDataConverter(elements_to_convert=1, data_converted=1, data_inserted=1)
        d7 = SimpleDataConverter(fail_on='_restore_state')
        d8 = SimpleDataConverter(elements_to_convert=0, data_converted=0, data_inserted=0, log_to_stdout=False,
                                 log_to_telegram=False)
        d6.run()
        d7.run()
        d8.run()
        s.verify_module_execution(d6)
        s.verify_module_execution(d7)
        s.verify_module_execution(d8)
        s.registered_data_converters = [d6, d7, d8]
        s.registered = 3
        s.unregistered = 3
        time3 = 11.8219821
        s.generate_report(time3)
        self.assertEqual(time3, s.execution_report['last_execution']['duration'])
        self.assertEqual(3, s.execution_report['last_execution']['modules_executed'])
        self.assertEqual(1, s.execution_report['last_execution']['modules_succeeded'])
        self.assertDictEqual(
                {'simple_data_converter': {'elements_to_convert': 0, 'converted_elements': 0, 'inserted_elements': 0}},
                s.execution_report['last_execution']['modules_with_pending_work'])
        self.assertEqual(2, s.execution_report['last_execution']['modules_failed']['amount'])
        self.assertEqual(['simple_data_converter', 'simple_data_converter'],
                         s.execution_report['last_execution']['modules_failed']['modules'])
        self.assertEqual(8, s.execution_report['aggregated']['per_module']['simple_data_converter']['total_executions'])
        self.assertEqual(6, s.execution_report['aggregated']['per_module']['simple_data_converter'][
            'executions_with_pending_work'])
        self.assertEqual(5, s.execution_report['aggregated']['per_module']['simple_data_converter'][
            'succeeded_executions'])
        self.assertEqual(3,
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failed_executions'])
        self.assertEqual(1, s.execution_report['last_execution']['elements_to_convert'])
        self.assertEqual(1, s.execution_report['last_execution']['converted_elements'])
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
        self.assertEqual(1237, s.execution_report['aggregated']['elements_to_convert'])
        self.assertEqual(1237, s.execution_report['aggregated']['converted_elements'])
        self.assertEqual(1237, s.execution_report['aggregated']['inserted_elements'])
        self.assertEqual([None, None],
                         s.execution_report['aggregated']['per_module']['simple_data_converter']['failure_details'][
                             'Unknown cause'])
