from pymongo.errors import DuplicateKeyError
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.deploy as deploy


@mock.patch('sys.argv', ['deploy.py'])
@mock.patch('data_gathering_subsystem.deploy.environ', {})
@mock.patch('data_gathering_subsystem.deploy.recursive_makedir', Mock())
class TestDeploy(TestCase):

    @mock.patch('data_gathering_subsystem.deploy.remove_all_under_directory', Mock())
    @mock.patch('data_gathering_subsystem.deploy.TextTestRunner')
    @mock.patch('data_gathering_subsystem.deploy.TestLoader', Mock())
    @mock.patch('data_gathering_subsystem.deploy.import_modules')
    @mock.patch('data_gathering_subsystem.deploy.create_user', Mock())
    @mock.patch('data_gathering_subsystem.deploy.drop_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.MongoDBCollection')
    @mock.patch('argparse.ArgumentParser')
    def test_all_with_tests_everything_ok(self, mock_args, mock_collection, mock_modules, mock_test_runner):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = True
        args.skip_all = False
        args.db_user = False
        args.create_indexes = True
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = True
        args.with_test_reports = False
        args.remove_files = False
        mock_collection.return_value.create_indexes.return_value = []
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

    @mock.patch('data_gathering_subsystem.deploy.remove_all_under_directory', Mock())
    @mock.patch('data_gathering_subsystem.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('data_gathering_subsystem.deploy.import_modules')
    @mock.patch('data_gathering_subsystem.deploy.create_user', Mock())
    @mock.patch('data_gathering_subsystem.deploy.drop_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.MongoDBCollection')
    @mock.patch('data_gathering_subsystem.deploy.environ', {'DEPLOY_ARGS': '--all --with-tests'})
    def test_all_with_tests_everything_ok_with_env_args(self, mock_collection, mock_modules):
        mock_module1 = Mock(name='Mock module')
        mock_module1.return_value.instance.return_value = runnable = Mock()
        mock_collection.return_value.create_indexes.return_value = []
        runnable.is_runnable.return_value = True
        mock_modules.return_value = [mock_module1]
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_modules.called)

    @mock.patch('data_gathering_subsystem.deploy.create_user',
                Mock(side_effect=DuplicateKeyError('User already exists')))
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_create_user_duplicated_user(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = True
        args.create_indexes = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)

    @mock.patch('data_gathering_subsystem.deploy.import_modules')
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_verify_modules_not_instantiable(self, mock_args, mock_modules):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
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

    @mock.patch('data_gathering_subsystem.deploy.exit')
    @mock.patch('data_gathering_subsystem.deploy.TextTestRunner')
    @mock.patch('data_gathering_subsystem.deploy.TestLoader', Mock())
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.Namespace')
    @mock.patch('argparse.ArgumentParser')
    def test_tests_failed(self, mock_args, mock_namespace, mock_test_runner, mock_exit):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = True
        args.with_test_reports = False
        args.remove_files = False
        mock_namespace.return_value.all = False
        mock_namespace.return_value.skip_all = False
        mock_namespace.return_value.db_user = False
        mock_namespace.return_value.drop_database = False
        mock_namespace.return_value.verify_modules = False
        mock_namespace.return_value.with_tests = True
        mock_namespace.return_value.remove_files = False
        mock_test_runner.return_value.run = results = Mock()
        results.return_value.wasSuccessful.return_value = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_test_runner.called)
        self.assertTrue(mock_exit.called)

    @mock.patch('data_gathering_subsystem.deploy.remove_all_under_directory',
                Mock(side_effect=FileNotFoundError('Directory not found')))
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_remove_files_directories_not_found(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = True
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)

    @mock.patch('data_gathering_subsystem.deploy.exit')
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser',
                Mock(side_effect=Exception('Test error (to verify anomalous exit). This is OK.')))
    def test_anomalous_exit(self, mock_exit):
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_exit.called)

    @mock.patch('argparse.ArgumentParser')
    def test_skip_all(self, mock_args):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = True
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertEqual(0, e.exception.code)

    @mock.patch('data_gathering_subsystem.deploy.ping_database',
                Mock(side_effect=EnvironmentError('Test error to verify deploy is aborted.')))
    def test_deploy_fails_if_database_down(self):
        with self.assertRaises(SystemExit) as e:
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, e.exception.code)

    @mock.patch('data_gathering_subsystem.deploy.remove_all_under_directory', Mock())
    @mock.patch('data_gathering_subsystem.deploy.import_modules')
    @mock.patch('data_gathering_subsystem.deploy.create_user', Mock())
    @mock.patch('data_gathering_subsystem.deploy.drop_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.MongoDBCollection')
    @mock.patch('argparse.ArgumentParser')
    def test_default_option(self, mock_args, mock_collection, mock_modules):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        mock_collection.return_value.create_indexes.return_value = []
        mock_module1 = Mock(name='Mock module')
        mock_module1.return_value.instance.return_value = runnable = Mock()
        runnable.is_runnable.return_value = True
        mock_modules.return_value = [mock_module1]
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertTrue(mock_args.called)
        self.assertTrue(mock_modules.called)

    @mock.patch('coverage.Coverage')
    @mock.patch('data_gathering_subsystem.deploy._execute_tests', Mock(return_value=True))
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_generated_if_tests_ok(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = True
        args.remove_files = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(1, mock_coverage.return_value.start.call_count)
        self.assertEqual(1, mock_coverage.return_value.stop.call_count)
        self.assertEqual(1, mock_coverage.return_value.save.call_count)

    @mock.patch('coverage.Coverage')
    @mock.patch('data_gathering_subsystem.deploy._execute_tests', Mock(return_value=False))
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_coverage_report_is_not_generated_if_tests_fail(self, mock_args, mock_coverage):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = False
        args.drop_database = False
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

    @mock.patch('data_gathering_subsystem.deploy.get_config', Mock(return_value={'MONGODB_INDEXES': {
        'country_indicators': {'keys': [{'year': -1}, {'country_id': 1}, {'indicator': 1}], 'unique': True},
        'sea_level_rise': {'keys': [{'time_utc': -1}]},
        'weather_forecast': {'keys': [{'station_id': 1}], 'name': 'Index'}}}))
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('data_gathering_subsystem.deploy.MongoDBCollection')
    @mock.patch('argparse.ArgumentParser')
    def test_correct_name_when_generating_index_names(self, mock_args, mock_collection):
        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = True
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.assertEqual(3, mock_collection.return_value.create_index.call_count)
        result = [x[1]['name'] for x in mock_collection.return_value.create_index.call_args_list]
        self.assertListEqual(
                ['country_indicators__index_on__year__country_id__indicator', 'sea_level_rise__index_on__time_utc',
                 'Index'], result)

    @mock.patch('data_gathering_subsystem.deploy.get_config', Mock(return_value={'MONGODB_INDEXES': {}}))
    @mock.patch('data_gathering_subsystem.deploy.ping_database', Mock())
    @mock.patch('argparse.ArgumentParser')
    def test_no_indexes_are_created_if_index_file_is_empty(self, mock_args):
        from logging import INFO

        mock_args.return_value.parse_args.return_value = args = Mock()
        args.all = False
        args.skip_all = False
        args.db_user = False
        args.create_indexes = True
        args.drop_database = False
        args.verify_modules = False
        args.with_tests = False
        args.with_test_reports = False
        args.remove_files = False
        with self.assertLogs('DeployDataGatheringSubsystemLogger', level=INFO):
            deploy.deploy(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
