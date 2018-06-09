from utilities.postgres_util import import_psycopg2

import_psycopg2()

import argparse
from os import environ

import coverage
import sys
from climate.config.config import WEB_CONFIG
from django.conf import settings
from django.test.utils import get_runner
from manage import create_superuser, execute

import web.settings as web_settings
from global_config.config import GLOBAL_CONFIG
from utilities.log_util import get_logger
from utilities.postgres_util import ping_database
from utilities.util import recursive_makedir

from django.core.wsgi import get_wsgi_application

get_wsgi_application()


def _execute_tests(xml_results=False) -> bool:
    """
        Executes all tests.
        :param xml_results: If True, it will generate an XML test report in a directory (TEST_RESULTS_DIR).
        :return: True, if test execution was successful; False, otherwise.
    """
    if xml_results:
        recursive_makedir(GLOBAL_CONFIG['TEST_RESULTS_DIR'])
        settings.TEST_RUNNER = web_settings.TEST_XML_RUNNER
    test_runner_class = get_runner(settings)
    runner = test_runner_class(verbosity=2, failfast=True)
    failures = runner.run_tests(["climate.test"])
    return failures == 0


def deploy(log_to_file=True, log_to_stdout=True, log_to_telegram=None):
    """
        Executes deployment actions. Possible actions are:
            - Creating database tables from Django models.
            - Creating the web application superuser.
            - Executing all the tests. Depending on the invocation (parameters '--with-tests' or '--with-test-reports')
              coverage and test results reports will be generated.
        :param log_to_file: If True, saves log records into a log file.
        :param log_to_stdout: If True, emits log records to stdout.
        :param log_to_telegram: If True, sends CRITICAL log records via Telegram messages. Defaults to None, which means
                                that the default configuration will be used (global_config.config).
    """
    # Getting a logger instance
    logger = get_logger(__file__, 'DeployWebApplicationSubsystemLogger', to_file=log_to_file, to_stdout=log_to_stdout,
                        is_subsystem=False, component=WEB_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--all', help='executes all deploy actions. This is the default option. If chosen, the '
                                          'other options will be ignored. Tests are not executed by default.',
                            required=False, action='store_true')
        parser.add_argument('--make-migrations', help='creates database tables from (web) Django models',
                            required=False, action='store_true')
        parser.add_argument('--create_superuser', help='creates an admin superuser for the application', required=False,
                            action='store_true')
        parser.add_argument('--with-tests', help='executes all the Subsystem tests', required=False,
                            action='store_true')
        parser.add_argument('--with-test-reports', help='executes all the Subsystem tests and generates a coverage '
                                                        'report and a XML test results report', required=False,
                            action='store_true')
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
        if args.all and any([args.make_migrations, args.create_superuser]):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not any([args.all, args.make_migrations, args.create_superuser, args.with_tests,
                      args.with_test_reports]) and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True, with_tests=False, with_test_reports=False)

        # 1. [Default] Verifying PostgreSQL is up (required both for deploy operations and tests).
        try:
            ping_database(close_after=True)
            logger.info('PostgreSQL server is up and reachable.')
        except EnvironmentError:
            logger.error('PostgreSQL server is down. Deploy will be aborted, since an active PostgreSQL server '
                         'is required for this operations.')
            exit(1)

        # 2. Creating Web models
        if args.all or args.make_migrations:
            logger.info('Creating database tables from (web) Django models.')
            execute(['manage.py', 'makemigrations'])
            execute(['manage.py', 'migrate', 'webmodels'])
            execute(['manage.py', 'migrate'])  # This also migrates other apps, such as admin, auth, sessions...
            logger.info('Migrations were successfully applied.')

        # 3. Creating superuser
        if args.all or args.create_superuser:
            from climate.validators import ValidationError

            logger.info('Creating the Web Application Subsystem superuser.')
            try:
                if create_superuser():
                    logger.info('Superuser was successfully created.')
                else:
                    logger.error('An error occurred while creating the superuser. Deploy will be aborted.')
                    exit(1)
            except ValidationError:
                logger.error('Environment variables %s and %s were not set for creating the superuser. If you want to '
                             'omit this step, do not use "--all" or "--create-superuser" as deployment actions.' % (
                                 WEB_CONFIG['SUPERUSER_USERNAME'], WEB_CONFIG['SUPERUSER_PASSWORD']))
                exit(1)

        # 4. Executing all tests
        if args.with_tests or args.with_test_reports:
            if args.with_test_reports:
                logger.info('Running all the Web Application Subsystem tests with branch coverage.')
                # Measuring coverage
                coverage_filepath = GLOBAL_CONFIG['COVERAGE_DIR'] + WEB_CONFIG['COVERAGE_FILENAME']
                coverage_analyzer = coverage.Coverage(source=[GLOBAL_CONFIG['ROOT_PROJECT_FOLDER']], branch=True,
                                                      concurrency="thread", data_file=coverage_filepath,
                                                      config_file=GLOBAL_CONFIG['COVERAGE_CONFIG_FILEPATH'])
                coverage_analyzer.start()
                success = _execute_tests(xml_results=True)
                coverage_analyzer.stop()
                sys.stderr.flush()
                logger = get_logger(__file__, 'DeployWebApplicationSubsystemLogger', to_file=log_to_file,
                                    to_stdout=log_to_stdout, is_subsystem=False, component=WEB_CONFIG['COMPONENT'],
                                    to_telegram=log_to_telegram)
                if success:
                    logger.info('Saving coverage report to "%s".' % coverage_filepath)
                    recursive_makedir(coverage_filepath, is_file=True)
                    coverage_analyzer.save()
            else:
                logger.info('Running all the Web Application Subsystem tests.')
                success = _execute_tests()
                sys.stderr.flush()
                logger = get_logger(__file__, 'DeployWebApplicationSubsystemLogger', to_file=log_to_file,
                                    to_stdout=log_to_stdout, is_subsystem=False, component=WEB_CONFIG['COMPONENT'],
                                    to_telegram=log_to_telegram)
            if success:
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_file=False, log_to_stdout=True, log_to_telegram=None)
