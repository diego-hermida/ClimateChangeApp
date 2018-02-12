from unittest import TestCase, mock
from unittest.mock import Mock

import api.deploy as deploy


class TestDeploy(TestCase):

    def tearDown(self):
        from os import environ
        try:
            del environ['SKIP_DEPLOY']
        except KeyError:
            pass

    @mock.patch('api.deploy.TextTestRunner')
    @mock.patch('api.deploy.TestLoader', Mock())
    @mock.patch('api.deploy.bulk_create_authorized_users')
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_all_with_tests_everything_ok(self, mock_args, mock_auth_users, mock_test_runner):
        from global_config.global_config import GLOBAL_CONFIG
        import yaml
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = True
        with open(GLOBAL_CONFIG['ROOT_API_FOLDER'] + 'doc/authorized_users.config', 'r', encoding='utf-8') as f:
            users = yaml.load(f)
        mock_auth_users.return_value = len(users['authorized_users'].keys())
        deploy.deploy(log_to_file=False, log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_auth_users.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('api.deploy.TextTestRunner')
    @mock.patch('api.deploy.TestLoader', Mock())
    @mock.patch('api.deploy.bulk_create_authorized_users')
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_tests_failed(self, mock_args, mock_auth_users, mock_test_runner):
        from global_config.global_config import GLOBAL_CONFIG
        import yaml
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.with_tests = True
        args.skip_all = False
        with open(GLOBAL_CONFIG['ROOT_API_FOLDER'] + 'doc/authorized_users.config', 'r', encoding='utf-8') as f:
            users = yaml.load(f)
        mock_auth_users.return_value = len(users['authorized_users'].keys())
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = False
        with self.assertRaises(SystemExit):
            deploy.deploy(log_to_file=False, log_to_stdout=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_auth_users.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('argparse.ArgumentParser', Mock(side_effect=Exception(
            'Test error (to verify anomalous exit). This is OK.')))
    def test_anomalous_exit(self):
        with self.assertRaises(SystemExit):
            deploy.deploy(log_to_file=False, log_to_stdout=False)

    @mock.patch('argparse.ArgumentParser')
    def test_skip_all(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = True
        args.with_tests = False
        with self.assertRaises(SystemExit):
            deploy.deploy(log_to_file=False, log_to_stdout=False)
        self.assertTrue(mock_args.called)
