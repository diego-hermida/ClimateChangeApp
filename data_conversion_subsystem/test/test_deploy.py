from unittest import TestCase, mock
from unittest.mock import Mock

import data_conversion_subsystem.deploy as deploy


@mock.patch('sys.argv', ['deploy.py'])
@mock.patch('data_conversion_subsystem.deploy.environ', {})
@mock.patch('data_conversion_subsystem.deploy.recursive_makedir', Mock())
class TestDeploy(TestCase):

    @mock.patch('data_conversion_subsystem.deploy.remove_all_under_directory', Mock())
    @mock.patch('data_conversion_subsystem.deploy.TextTestRunner')
    @mock.patch('data_conversion_subsystem.deploy.TestLoader', Mock())
    @mock.patch('data_conversion_subsystem.deploy.import_modules')
    @mock.patch('data_conversion_subsystem.deploy.execute', Mock())
    @mock.patch('data_conversion_subsystem.deploy.create_application_user', Mock())
    @mock.patch('data_conversion_subsystem.deploy.create_application_database', Mock())
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_all_with_tests_everything_ok(self, mock_args, mock_modules, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = True
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = True
        args.with_test_reports = False
        args.remove_files = False
        mock_module1 = Mock(name='Mock module')
        mock_module1.return_value.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = True
        mock_modules.return_value = [mock_module1]
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = True
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_modules.called)
        self.assertTrue(mock_test_runner.called)

    @mock.patch('data_conversion_subsystem.deploy.remove_all_under_directory', Mock())
    @mock.patch('data_conversion_subsystem.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('data_conversion_subsystem.deploy.import_modules')
    @mock.patch('data_conversion_subsystem.deploy.execute', Mock())
    @mock.patch('data_conversion_subsystem.deploy.create_application_user', Mock())
    @mock.patch('data_conversion_subsystem.deploy.create_application_database', Mock())
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('data_conversion_subsystem.deploy.environ', {'DEPLOY_ARGS': '--all --with-tests'})
    def test_all_with_tests_everything_ok_with_env_args(self, mock_modules):
        mock_module1 = Mock(name='Mock module')
        mock_module1.return_value.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = True
        mock_modules.return_value = [mock_module1]
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_modules.called)

    @mock.patch('data_conversion_subsystem.deploy.import_modules')
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_verify_modules_not_instantiable(self, mock_args, mock_modules):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = True
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        mock_module1 = Mock(name='Mock module')
        mock_module1.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = False
        mock_modules.return_value = [mock_module1]
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_modules.called)

    @mock.patch('data_conversion_subsystem.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_tests_failed(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = True
        args.with_test_reports = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('data_conversion_subsystem.deploy.remove_all_under_directory', 
                Mock(side_effect=FileNotFoundError('Directory not found')))
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_remove_files_directories_not_found(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = True
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)

    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser', Mock(side_effect=Exception(
            'Test error (to verify anomalous exit). This is OK.')))
    def test_anomalous_exit(self):
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
    
    @mock.patch('argparse.ArgumentParser')
    def test_skip_all(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = True
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertEqual(0, e.exception.code)

    @mock.patch('data_conversion_subsystem.deploy.ping_database',
                Mock(side_effect=EnvironmentError('Test error to verify deploy is aborted.')))
    def test_deploy_fails_if_database_down(self):
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('data_conversion_subsystem.deploy.remove_all_under_directory', Mock())
    @mock.patch('data_conversion_subsystem.deploy.import_modules')
    @mock.patch('data_conversion_subsystem.deploy.execute', Mock())
    @mock.patch('data_conversion_subsystem.deploy.create_application_user', Mock())
    @mock.patch('data_conversion_subsystem.deploy.create_application_database', Mock())
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_default_option(self, mock_args, mock_modules):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        mock_module1 = Mock(name='Mock module')
        mock_module1.return_value.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = True
        mock_modules.return_value = [mock_module1]
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_modules.called)

    @mock.patch('coverage.Coverage')
    @mock.patch('data_conversion_subsystem.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_generated_if_tests_ok(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = True
        args.remove_files = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(1, mock_coverage.return_value.save.call_count)

    @mock.patch('coverage.Coverage')
    @mock.patch('data_conversion_subsystem.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('data_conversion_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_not_generated_if_tests_fail(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.prepare_db = False
        args.make_migrations = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = True
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(0, mock_coverage.return_value.save.call_count)
