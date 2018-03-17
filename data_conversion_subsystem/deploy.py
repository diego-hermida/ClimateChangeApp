import argparse
import coverage
import sys

from data_conversion_subsystem.config.config import DCS_CONFIG
from data_conversion_subsystem.manage import execute
from global_config.config import GLOBAL_CONFIG
from os import environ
from unittest import TestLoader, TextTestRunner
from utilities.postgres_util import create_application_user, create_application_database, ping_database
from utilities.import_dir import import_modules
from utilities.log_util import get_logger
from utilities.util import remove_all_under_directory, recursive_makedir
from xmlrunner.runner import XMLTestRunner


def _execute_tests(xml_results=False) -> bool:
    """
        Executes all API tests.
        :param xml_results: If True, it will generate an XML test report in a directory (TEST_RESULTS_DIR).
        :return: True, if test execution was successful; False, otherwise.
    """
    suite = TestLoader().discover(DCS_CONFIG['ROOT_DATA_CONVERSION_SUBSYSTEM_FOLDER'])
    recursive_makedir(GLOBAL_CONFIG['TEST_RESULTS_DIR'])
    with open(GLOBAL_CONFIG['TEST_RESULTS_DIR'] + DCS_CONFIG['TESTS_FILENAME'], 'wb') as f:
        runner = TextTestRunner(failfast=True, verbosity=2) if not xml_results else XMLTestRunner(failfast=True,
                verbosity=2, output=f)
        results = runner.run(suite)
    return results.wasSuccessful()


def deploy(log_to_file=True, log_to_stdout=True, log_to_telegram=None):
    """
        Executes deployment actions. Possible actions are:
            - Recreating the PostgreSQL database and user.
            - Creating database tables from Django models.
            - Verifying that all DataConverters are instantiable and runnable.
            - Removing all '.state' and log files.
            - Executing all the tests. Depending on the invocation (parameters '--with-tests' or '--with-test-reports')
              coverage and test results reports will be generated.
        :param log_to_file: If True, saves log records into a log file.
        :param log_to_stdout: If True, emits log records to stdout.
        :param log_to_telegram: If True, sends CRITICAL log records via Telegram messages. Defaults to None, which means
                                that the default configuration will be used (global_config.config).
    """
    # Getting a logger instance
    logger = get_logger(__file__, 'DeployDataConversionSubsystemLogger', to_file=log_to_file, to_stdout=log_to_stdout,
            is_subsystem=False, component=DCS_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--all', help='executes all deploy actions. This is the default option. If chosen, the '
                'other options will be ignored. Tests are not executed by default.', required=False, action='store_true')
        parser.add_argument('--prepare-db', help='creates the PostgreSQL user and database',
                required=False, action='store_true')
        parser.add_argument('--make-migrations', help='creates database tables from Django models',
                required=False, action='store_true')
        parser.add_argument('--verify-modules', help='verifies all modules are instantiable and runnable',
                required=False, action='store_true')
        parser.add_argument('--remove-files', help='removes all .log and .state files (and its directories)',
                required=False, action='store_true')
        parser.add_argument('--with-tests', help='executes all the Subsystem tests', required=False, action='store_true')
        parser.add_argument('--with-test-reports', help='executes all the Subsystem tests and generates a coverage '
                'report and a XML test results report', required=False, action='store_true')
        parser.add_argument('--skip-all', help='does not execute any deploy step', required=False, action='store_true')

        # Deploy args can be added from the "install.sh" script using environment variables.
        env_args = environ.get('DEPLOY_ARGS', None)
        if env_args:
            for arg in env_args.split(' '):
                sys.argv.append(arg)
        args = parser.parse_args()

        # If --skip-all, then the operations will be omitted.
        if args.skip_all:
            logger.info('Deploy operations have been skipped.')
            exit(0)
        if args.all and any([args.prepare_db, args.make_migrations, args.verify_modules, args.remove_files]):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not any([args.all, args.prepare_db, args.make_migrations, args.verify_modules, args.remove_files,
                args.with_tests, args.with_test_reports]) and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True, with_tests=False, with_test_reports=False)

        # 1. [Default] Verifying PostgreSQL is up (required both for deploy operations and tests).
        try:
            # All PosgreSQL operations will use the same connection instance.
            connection = ping_database(close_after=False)
            logger.info('PostgreSQL server is up and reachable.')
        except EnvironmentError:
            logger.error(
                    'PostgreSQL server is down. Deploy will be aborted, since an active PostgreSQL server '
                    'is required for this operations.')
            exit(1)

        # 1. Ensuring database is brand new, and creating user.
        if args.all or args.prepare_db:
            logger.info('Creating PostgreSQL database.')
            create_application_database(connection=connection)
            logger.info('Successfully created database.')
            logger.info('Creating Data Conversion Subsystem database owner.')
            create_application_user(connection=connection, close_after=True)
            logger.info('Successfully created user.')

        if args.all or args.make_migrations:
            logger.info('Creating database tables from Django models.')
            execute(['makemigrations'])
            execute(['migrate'])
            logger.info('Migrations were successfully made.')
            logger.info('Removing migrations history.')
            remove_all_under_directory(DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_MIGRATIONS_FOLDER'])
            with open(DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_MIGRATIONS_FOLDER'] + '__init__.py', 'w'):
                pass  # Touching the "__init__.py" file. If not created, Django won't find the "migrations" file.
            logger.info('Migrations history successfully removed.')

        # 3. Verifying all modules are instantiable and runnable.
        if args.all or args.verify_modules:
            logger.info('Verifying DataConverter(s) are instantiable.')
            # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
            modules = import_modules(DCS_CONFIG['DATA_CONVERTERS_PATH'], recursive=True,
                                     base_package=DCS_CONFIG['DATA_CONVERTERS_BASE_PACKAGE'])
            failed = []
            for module in modules:
                data_collector = module.instance(log_to_stdout=False, log_to_file=False)
                try:
                    assert data_collector.is_runnable()
                except AssertionError:
                    failed.append(str(data_collector))
                    logger.error('"%s" is not instantiable nor runnable.' % (data_collector))
            if failed:
                logger.warning('Some DataConverter(s) are not runnable (%d out of %d): %s' %
                        (len(failed), len(modules), failed))
            else:
                logger.info('All DataConverter class(es) are instantiable and runnable.')

        # 4. Executing all tests
        if args.with_tests or args.with_test_reports:
            if args.with_test_reports:
                logger.info('Running all the Data Conversion Subsystem tests with branch coverage.')
                # Measuring coverage
                coverage_filepath = GLOBAL_CONFIG['COVERAGE_DIR'] + DCS_CONFIG['COVERAGE_FILENAME']
                coverage_analyzer = coverage.Coverage(source=[GLOBAL_CONFIG['ROOT_PROJECT_FOLDER']], branch=True,
                                                      concurrency="thread", data_file=coverage_filepath,
                                                      config_file=GLOBAL_CONFIG['COVERAGE_CONFIG_FILEPATH'])
                coverage_analyzer.start()
                success = _execute_tests(xml_results=True)
                coverage_analyzer.stop()
                sys.stderr.flush()
                logger = get_logger(__file__, 'DeployDataConversionSubsystemLogger', to_file=log_to_file,
                                    to_stdout=log_to_stdout, is_subsystem=False, component=DCS_CONFIG['COMPONENT'],
                                    to_telegram=log_to_telegram)
                if success:
                    logger.info('Saving coverage report to "%s".' % coverage_filepath)
                    recursive_makedir(coverage_filepath, is_file=True)
                    coverage_analyzer.save()
            else:
                logger.info('Running all the Data Conversion Subsystem tests.')
                success = _execute_tests()
                sys.stderr.flush()
                logger = get_logger(__file__, 'DeployDataConversionSubsystemLogger', to_file=log_to_file,
                        to_stdout=log_to_stdout, is_subsystem=False, component=DCS_CONFIG['COMPONENT'],
                        to_telegram=log_to_telegram)
            if success:
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

        # 5. Emptying Subsystem's logs and '.state' files.
        if args.all or args.remove_files:
            logger.info('Removing log base directory: %s' % (DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER']))
            try:
                remove_all_under_directory(DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('Log base directory does not exist, so it cannot be removed.')
            try:
                logger.info('Removing .state files\' base directory: %s' % (DCS_CONFIG[
                        'DATA_CONVERSION_SUBSYSTEM_STATE_FILES_ROOT_FOLDER']))
                remove_all_under_directory(DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('.state files\' base directory does not exist, so it cannot be removed.')

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_file=False, log_to_stdout=True, log_to_telegram=None)
