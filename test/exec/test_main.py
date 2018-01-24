import exec.main as main

from data_collector.data_collector import CONFIG
from os import environ
from test.data_collector.test_data_collector import SimpleDataCollector
from time import sleep
from timeit import default_timer as timer
from unittest import TestCase, mock
from unittest.mock import Mock
from utilities.util import time_limit

PREVIOUS_LOCALHOST_IP = environ.get('LOCALHOST_IP')


def sleep5(*args, **kwargs):
    sleep(5)


class TestMain(TestCase):

    def setUp(self):
        environ['LOCALHOST_IP'] = '0.0.0.0 (test IP)'

    @classmethod
    def tearDownClass(cls):
        if PREVIOUS_LOCALHOST_IP is not None:
            environ['LOCALHOST_IP'] = PREVIOUS_LOCALHOST_IP
        else:
            del environ['LOCALHOST_IP']

    @mock.patch('exec.main.ping_database', Mock())
    @mock.patch('exec.main.exit', Mock())
    @mock.patch('exec.main.import_modules', side_effect=sleep5)
    def test_timeout(self, mock_import):
        start = timer()
        with self.assertRaises(TimeoutError):
            with time_limit(1):
                main.main(log_to_stdout=False, log_to_file=False)
        end = timer()
        self.assertTrue(mock_import.called)
        self.assertLessEqual(1.0, end - start)
        self.assertGreater(2.0, end - start)

    @mock.patch('exec.main.ping_database', Mock())
    @mock.patch('supervisor.supervisor.MongoDBCollection')
    @mock.patch('exec.main.exit', Mock())
    @mock.patch('data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    @mock.patch('exec.main.import_modules')
    def test_execution_succeeded_regardless_of_modules(self, mock_modules, mock_collection):
        mock_collection.return_value.get_last_elements.return_value = None
        mock_module1 = Mock()
        mock_module1.instance.return_value = SimpleDataCollector(fail_on='_save_data', log_to_file=False,
                log_to_stdout=False)
        mock_module2 = Mock()
        mock_module2.instance.return_value = SimpleDataCollector(fail_on='_check_execution', log_to_stdout=False,
                log_to_file=False)
        mock_modules.return_value = [mock_module1, mock_module2]
        main.main(log_to_stdout=False, log_to_file=False)
        self.assertTrue(mock_modules.called)
        self.assertTrue(mock_collection.called)
        self.assertFalse(mock_module1.instance().successful_execution())
        self.assertFalse(mock_module2.instance().successful_execution())

    @mock.patch('exec.main.ping_database', Mock(side_effect=EnvironmentError('Database is down!')))
    def test_execution_fails_if_database_down(self):
        with self.assertRaises(SystemExit):
            main.main(log_to_stdout=False, log_to_file=False)

    def test_execution_fails_if_environment_variable_doesnt_exist(self):
        from os import environ
        del environ['LOCALHOST_IP']
        with self.assertRaises(SystemExit):
            main.main(log_to_stdout=False, log_to_file=False)
