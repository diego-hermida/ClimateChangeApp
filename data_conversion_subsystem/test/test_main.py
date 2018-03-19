from data_conversion_subsystem import main as main
from json import dumps
from os import environ
from data_conversion_subsystem.data_converter.data_converter import CONFIG
from data_conversion_subsystem.test.data_converter.test_data_converter import SimpleDataConverter
from requests import RequestException
from time import sleep
from timeit import default_timer as timer
from unittest import TestCase, mock
from unittest.mock import Mock
from utilities.util import time_limit

PREVIOUS_LOCALHOST_IP = environ.get('MONGODB_IP')


def sleep5(*args, **kwargs):
    sleep(5)


class TestMain(TestCase):

    @mock.patch('data_conversion_subsystem.main.ping_database', Mock(side_effect=sleep5))
    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip', 'API_IP': 'test_ip'})
    def test_timeout(self):
        start = timer()
        with self.assertRaises(SystemExit) as e:
            with time_limit(1):
                main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)
        end = timer()
        self.assertLessEqual(1.0, end - start)
        self.assertGreater(2.0, end - start)

    @mock.patch('data_conversion_subsystem.main.get_execution_id', Mock(return_value=1))
    @mock.patch('data_conversion_subsystem.main.ping_database', Mock())
    @mock.patch('data_conversion_subsystem.supervisor.supervisor.Supervisor.generate_report', Mock())
    @mock.patch('requests.get')
    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip', 'API_IP': 'test_ip'})
    @mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config', Mock(return_value=CONFIG))
    @mock.patch('data_conversion_subsystem.main.import_modules')
    def test_execution_succeeded_regardless_of_modules(self, mock_modules, mock_requests):
        mock_requests.return_value = response = Mock()
        response.content.decode = Mock(side_effect=['{"alive": true}', '{"data": [{"foo": true}, {"baz": false}]}'])
        response.status_code = 200
        mock_module1 = Mock()
        mock_module1.instance.return_value = SimpleDataConverter(fail_on='_has_pending_work')
        mock_module2 = Mock()
        mock_module2.instance.return_value = SimpleDataConverter(elements_to_convert=2, data_converted=2,
                data_inserted=2)
        mock_modules.return_value = [mock_module1, mock_module2]
        main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertTrue(mock_modules.called)
        self.assertFalse(mock_module1.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False).successful_execution())
        self.assertTrue(mock_module2.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False).successful_execution())

    @mock.patch('data_conversion_subsystem.main.get_execution_id', Mock(return_value=None))
    @mock.patch('data_conversion_subsystem.main.ping_database', Mock())
    @mock.patch('requests.get')
    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip', 'API_IP': 'test_ip'})
    @mock.patch('data_conversion_subsystem.main.import_modules')
    def test_execution_fails_if_data_converters_cannot_be_instantiated(self, mock_modules, mock_requests):
        mock_requests.return_value = response = Mock()
        response.content = '{"alive": true}'.encode()
        response.status_code = 200
        mock_modules.return_value = []
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('data_conversion_subsystem.main.ping_database', Mock(side_effect=EnvironmentError('Database is down!')))
    def test_execution_fails_if_database_down(self):
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('requests.get')
    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip', 'API_IP': 'test_ip'})
    @mock.patch('data_conversion_subsystem.main.get_execution_id', Mock(return_value=1))
    @mock.patch('data_conversion_subsystem.main.ping_database', Mock())
    def test_execution_fails_if_api_down_parseable_value(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.content = dumps({'alive': False}).encode()
        response.status_code = 200
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('requests.get', Mock(side_effect=RequestException('Test error. This is OK.')))
    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip', 'API_IP': 'test_ip'})
    @mock.patch('data_conversion_subsystem.main.get_execution_id', Mock(return_value=1))
    @mock.patch('data_conversion_subsystem.main.ping_database', Mock())
    def test_execution_fails_if_api_down_HTTP_error(self):
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('requests.get')
    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip', 'API_IP': 'test_ip'})
    @mock.patch('data_conversion_subsystem.main.get_execution_id', Mock(return_value=1))
    @mock.patch('data_conversion_subsystem.main.ping_database', Mock())
    def test_execution_fails_if_api_down_unparseable_value(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.content = '<html><h1>Internal Error</h1></html>'.encode()
        response.status_code = 500
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('os.environ', {'API_IP': 'test_ip'})
    def test_execution_fails_if_POSTGRES_IP_env_variable_doesnt_exist(self):
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('os.environ', {'POSTGRES_IP': 'test_ip'})
    def test_execution_fails_if_API_IP_env_variable_doesnt_exist(self):
        with self.assertRaises(SystemExit) as e:
            main.main(log_to_stdout=False, log_to_telegram=False, log_to_file=False)
        self.assertEqual(1, e.exception.code)
