from data_gathering_subsystem import main as main

from data_gathering_subsystem.data_collector.data_collector import CONFIG
from data_gathering_subsystem.test.data_collector.test_data_collector import SimpleDataCollector
from time import sleep
from timeit import default_timer as timer
from unittest import TestCase, mock
from unittest.mock import Mock
from utilities.util import time_limit


def sleep5(*args, **kwargs):
    sleep(5)


class TestMain(TestCase):

    @mock.patch('data_gathering_subsystem.main.get_and_increment_execution_id', Mock(return_value=1))
    @mock.patch('data_gathering_subsystem.main.ping_database', Mock())
    @mock.patch('data_gathering_subsystem.main.exit', Mock())
    @mock.patch('data_gathering_subsystem.main.import_modules', side_effect=sleep5)
    def test_timeout(self, mock_import):
        start = timer()
        with self.assertRaises(TimeoutError):
            with time_limit(1):
                main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        end = timer()
        self.assertTrue(mock_import.called)
        self.assertLessEqual(1.0, end - start)
        self.assertGreater(2.0, end - start)

    @mock.patch('data_gathering_subsystem.main.get_and_increment_execution_id', Mock(return_value=1))
    @mock.patch('data_gathering_subsystem.main.ping_database', Mock())
    @mock.patch('data_gathering_subsystem.supervisor.supervisor.MongoDBCollection')
    @mock.patch('data_gathering_subsystem.main.exit', Mock())
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    @mock.patch('data_gathering_subsystem.main.import_modules')
    def test_execution_succeeded_regardless_of_modules(self, mock_modules, mock_collection):
        mock_collection.return_value.get_last_elements.return_value = None
        mock_module1 = Mock()
        mock_module1.instance.return_value = SimpleDataCollector(fail_on='_save_data', log_to_file=False,
                log_to_stdout=False, log_to_telegram=False)
        mock_module2 = Mock()
        mock_module2.instance.return_value = SimpleDataCollector(fail_on='_check_execution', log_to_stdout=False, log_to_telegram=False,
                log_to_file=False)
        mock_modules.return_value = [mock_module1, mock_module2]
        main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertTrue(mock_modules.called)
        self.assertTrue(mock_collection.called)
        self.assertFalse(mock_module1.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False).successful_execution())
        self.assertFalse(mock_module2.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False).successful_execution())

    @mock.patch('data_gathering_subsystem.main.ping_database', Mock(side_effect=EnvironmentError('Database is down!')))
    def test_execution_fails_if_database_down(self):
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('data_gathering_subsystem.main.environ', {})
    def test_execution_fails_if_environment_variable_doesnt_exist(self):
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)
