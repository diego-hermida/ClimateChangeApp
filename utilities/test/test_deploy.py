from unittest import TestCase, mock
from unittest.mock import Mock

import utilities.deploy as deploy


@mock.patch('sys.argv', ['deploy.py'])
@mock.patch('utilities.deploy.environ', {})
@mock.patch('utilities.deploy.recursive_makedir', Mock())
class TestDeploy(TestCase):

    @mock.patch('utilities.deploy.TextTestRunner')
    @mock.patch('utilities.deploy.TestLoader', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_with_tests_everything_ok(self, mock_args, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = True
        args.with_tests_coverage = False
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('utilities.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('utilities.deploy.environ', {'DEPLOY_ARGS': '--with-tests'})
    def test_all_with_tests_everything_ok_with_env_args(self):
        from logging import INFO
        deploy.deploy(log_to_stdout=False)
        self.assertLogs('DeployTelegramConfiguratorLogger', level=INFO)

    @mock.patch('utilities.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('utilities.deploy.environ', {})
    @mock.patch('sys.argv', ['deploy.py'])
    @mock.patch('argparse.ArgumentParser')
    def test_default_option(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = False
        deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_args.called)

    @mock.patch('utilities.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('argparse.ArgumentParser')
    def test_with_tests_failed_tests(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = True
        args.with_tests_coverage = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_stdout=False)
        self.assertEqual(1, e.exception.code)
        self.assertTrue(mock_args.called)

    @mock.patch('argparse.ArgumentParser', Mock(side_effect=Exception(
            'Test error (to verify anomalous exit). This is OK.')))
    def test_anomalous_exit(self):
        with self.assertRaises(SystemExit) as ex:
            deploy.deploy(log_to_stdout=False)
        self.assertEqual(1, ex.exception.code)

    @mock.patch('argparse.ArgumentParser')
    def test_skip_all(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = True
        args.with_tests = False
        args.with_tests_coverage = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertEqual(0, e.exception.code)

    @mock.patch('coverage.Coverage')
    @mock.patch('utilities.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_generated_if_tests_ok(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = True
        deploy.deploy(log_to_stdout=False)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(1, mock_coverage.return_value.save.call_count)

    @mock.patch('coverage.Coverage')
    @mock.patch('utilities.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_not_generated_if_tests_fail(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = True
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_stdout=False)
        self.assertEqual(1, e.exception.code)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(0, mock_coverage.return_value.save.call_count)
