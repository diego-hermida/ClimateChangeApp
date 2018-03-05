from unittest import TestCase, mock
from unittest.mock import Mock

import telegram_bot.deploy as deploy


class TestDeploy(TestCase):

    @mock.patch('telegram_bot.deploy.TextTestRunner')
    @mock.patch('telegram_bot.deploy.TestLoader', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_with_tests_everything_ok(self, mock_args, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = True
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_test_runner.called)
    
    @mock.patch('telegram_bot.deploy.TextTestRunner')
    @mock.patch('telegram_bot.deploy.TestLoader', Mock())
    @mock.patch('telegram_bot.deploy.environ', {'DEPLOY_ARGS': '--with-tests'})
    def test_all_with_tests_everything_ok_with_env_args(self, mock_test_runner):
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('telegram_bot.deploy.TextTestRunner')
    @mock.patch('telegram_bot.deploy.TestLoader', Mock())
    @mock.patch('telegram_bot.deploy.environ', {})
    @mock.patch('sys.argv', ['deploy.py'])
    @mock.patch('argparse.ArgumentParser')
    def test_default_option(self, mock_args, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('telegram_bot.deploy.TextTestRunner')
    @mock.patch('telegram_bot.deploy.TestLoader', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_with_tests_failed_tests(self, mock_args, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = True
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_stdout=False)
        self.assertEqual(1, e.exception.code)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('argparse.ArgumentParser', Mock(side_effect=Exception(
            'Test error (to verify anomalous exit). This is OK.')))
    def test_anomalous_exit(self):
        with self.assertRaises(SystemExit) as ex:
            deploy.deploy(log_to_stdout=False)
        self.assertEqual(1, ex.exception.code)
    
    @mock.patch('argparse.ArgumentParser')
    def test_skip_all(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = True
        args.db_user = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertEqual(0, e.exception.code)
