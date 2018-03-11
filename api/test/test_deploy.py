from unittest import TestCase, mock
from unittest.mock import Mock

from pymongo.errors import DuplicateKeyError

import api.deploy as deploy
from api.config.config import API_CONFIG


@mock.patch('sys.argv', ['deploy.py'])
@mock.patch('api.deploy.environ', {})
@mock.patch('api.deploy.recursive_makedir', Mock())
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
    @mock.patch('api.deploy.create_user', Mock())
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_all_with_tests_everything_ok(self, mock_args, mock_auth_users, mock_test_runner):
        import yaml
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests_coverage = False
        args.with_tests_coverage = False
        args.all = True
        args.db_user = False
        args.add_users = False
        args.remove_files = False
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        with open(API_CONFIG['AUTHORIZED_USERS_FILEPATH'], 'r', encoding='utf-8') as f:
            users = yaml.load(f)
        mock_auth_users.return_value = len(users['authorized_users'].keys())
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_auth_users.called)

    @mock.patch('api.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('api.deploy.bulk_create_authorized_users')
    @mock.patch('api.deploy.create_user', Mock())
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('api.deploy.environ', {'DEPLOY_ARGS': '--all --with-tests'})
    def test_all_with_tests_everything_ok_with_args_from_env_variable(self, mock_auth_users):
        import yaml
        with open(API_CONFIG['AUTHORIZED_USERS_FILEPATH'], 'r', encoding='utf-8') as f:
            users = yaml.load(f)
        mock_auth_users.return_value = len(users['authorized_users'].keys())
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_auth_users.called)

    @mock.patch('api.deploy.create_user', Mock(side_effect=DuplicateKeyError('User already exists')))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_create_api_user_when_it_does_already_exist(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = False
        args.all = False
        args.db_user = True
        args.add_users = False
        args.remove_files = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)

    @mock.patch('api.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_tests_failed(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = True
        args.with_tests_coverage = False
        args.all = False
        args.db_user = False
        args.add_users = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
        self.assertTrue(mock_args.called)

    @mock.patch('argparse.ArgumentParser',
                Mock(side_effect=Exception('Test error (to verify anomalous exit). This is OK.')))
    def test_anomalous_exit(self):
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('argparse.ArgumentParser')
    def test_skip_all(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = True
        args.with_tests = False
        args.with_tests_coverage = False
        args.all = False
        args.db_user = False
        args.add_users = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(0, e.exception.code)
        self.assertTrue(mock_args.called)

    @mock.patch('api.deploy.ping_database',
                Mock(side_effect=EnvironmentError('Test error to verify deploy is aborted.')))
    def test_deploy_aborts_if_database_down(self):
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('api.deploy.bulk_create_authorized_users', Mock(return_value=0))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_deploy_aborts_if_not_all_authorized_users_are_inserted(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = False
        args.all = False
        args.db_user = False
        args.add_users = True
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
        self.assertTrue(mock_args.called)

    @mock.patch('yaml.load', Mock(return_value={'authorized_users': {'user1': {'token': 'test_token'}}}))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_deploy_aborts_if_authorized_users_do_not_have_scope(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = False
        args.all = False
        args.db_user = False
        args.add_users = True
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
        self.assertTrue(mock_args.called)

    @mock.patch('yaml.load', Mock(return_value={'authorized_users': {'user1': {'scope': 1}}}))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_deploy_aborts_if_authorized_users_do_not_have_token(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = False
        args.all = False
        args.db_user = False
        args.add_users = True
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
        self.assertTrue(mock_args.called)

    @mock.patch('coverage.Coverage')
    @mock.patch('api.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_generated_if_tests_ok(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = True
        args.all = False
        args.db_user = False
        args.add_users = False
        args.remove_files = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(1, mock_coverage.return_value.save.call_count)

    @mock.patch('coverage.Coverage')
    @mock.patch('api.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('api.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_not_generated_if_tests_fail(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.skip_all = False
        args.with_tests = False
        args.with_tests_coverage = True
        args.all = False
        args.db_user = False
        args.add_users = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(0, mock_coverage.return_value.save.call_count)
