from pymongo.errors import DuplicateKeyError
from unittest import TestCase, mock
from unittest.mock import Mock

import exec.deploy as deploy


class TestDeploy(TestCase):

    @mock.patch('exec.deploy.remove_all_under_directory', Mock())
    @mock.patch('exec.deploy.TextTestRunner')
    @mock.patch('exec.deploy.TestLoader', Mock())
    @mock.patch('exec.deploy.import_modules')
    @mock.patch('exec.deploy.create_application_user', Mock())
    @mock.patch('exec.deploy.drop_application_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_all_with_tests_everything_ok(self, mock_args, mock_modules, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = True
        args.db_user = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = True
        args.remove_files = False
        mock_module1 = Mock(name='Mock module')
        mock_module1.return_value.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = True
        mock_modules.return_value = [mock_module1]
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        deploy.deploy()
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_modules.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('exec.deploy.create_application_user', Mock(side_effect=DuplicateKeyError('User already exists')))
    @mock.patch('argparse.ArgumentParser')
    def test_create_user_duplicated_user(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.db_user = True
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.remove_files = False
        deploy.deploy()
        self.assertTrue(mock_args.called)

    @mock.patch('exec.deploy.import_modules')
    @mock.patch('argparse.ArgumentParser')
    def test_verify_modules_not_instantiable(self, mock_args, mock_modules):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.db_user = False
        args.drop_database = False
        args.verify_modules = True
        args.with_tests = False
        args.remove_files = False
        mock_module1 = Mock(name='Mock module')
        mock_module1.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = False
        mock_modules.return_value = [mock_module1]
        deploy.deploy()
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_modules.called)

    @mock.patch('exec.deploy.exit')
    @mock.patch('exec.deploy.TextTestRunner')
    @mock.patch('exec.deploy.TestLoader', Mock())
    @mock.patch('argparse.Namespace')
    @mock.patch('argparse.ArgumentParser')
    def test_tests_failed(self, mock_args, mock_namespace, mock_test_runner, mock_exit):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.db_user = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = True
        args.remove_files = False
        mock_namespace.return_value.all = False
        mock_namespace.return_value.db_user = False
        mock_namespace.return_value.drop_database = False
        mock_namespace.return_value.verify_modules = False
        mock_namespace.return_value.with_tests = True
        mock_namespace.return_value.remove_files = False
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = False
        deploy.deploy()
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_test_runner.called)
        self.assertTrue(mock_exit.called)

    @mock.patch('exec.deploy.remove_all_under_directory', Mock(side_effect=FileNotFoundError('Directory not found')))
    @mock.patch('argparse.ArgumentParser')
    def test_remove_files_directories_not_found(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.db_user = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.remove_files = True
        deploy.deploy()
        self.assertTrue(mock_args.called)

    @mock.patch('exec.deploy.exit')
    @mock.patch('argparse.ArgumentParser', Mock(side_effect=Exception('Unexpected error')))
    def test_anomalous_exit(self, mock_exit):
        deploy.deploy()
        self.assertTrue(mock_exit.called)
