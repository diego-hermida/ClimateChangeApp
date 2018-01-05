from unittest import TestCase, mock
from unittest.mock import Mock

import exec.main as main
from data_collector.data_collector import CONFIG
from test.data_collector.test_data_collector import SimpleDataCollector
from timeit import default_timer as timer
from utilities.util import time_limit

def sleep5(*args, **kwargs):
    from time import sleep
    sleep(5)

class TestMain(TestCase):

    @mock.patch('exec.main.exit', Mock())
    @mock.patch('exec.main.import_modules', side_effect=sleep5)
    def test_timeout(self, mock_import):
        with self.assertRaises(TimeoutError):
            start = timer()
            with time_limit(2):
                main.main()
            self.assertLessEqual(2.0, timer() - start)

    @mock.patch('supervisor.supervisor.write_state', Mock())
    @mock.patch('exec.main.exit', Mock())
    @mock.patch('data_collector.data_collector.get_config', Mock(return_value=CONFIG))
    @mock.patch('exec.main.import_modules')
    def test_execution_succeeded_regardless_of_modules(self, mock_modules):
        mock_module1 = Mock()
        mock_module1.instance.return_value = SimpleDataCollector(fail_on='_save_data')
        mock_module2 = Mock()
        mock_module2.instance.return_value = SimpleDataCollector(fail_on='_check_execution')
        mock_modules.return_value = [mock_module1, mock_module2]
        main.main()
        self.assertFalse(mock_module1.instance().successful_execution())
        self.assertFalse(mock_module2.instance().successful_execution())
