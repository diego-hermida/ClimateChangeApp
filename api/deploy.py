import argparse
import coverage
import sys
import yaml

from api.config.config import API_CONFIG
from global_config.config import GLOBAL_CONFIG
from os import environ
from pymongo.errors import DuplicateKeyError
from unittest import TestLoader, TextTestRunner
from utilities.mongo_util import bulk_create_authorized_users, ping_database, create_user
from utilities.log_util import get_logger
from utilities.util import remove_all_under_directory, recursive_makedir
from xmlrunner.runner import XMLTestRunner


def _execute_tests(xml_results=False) -> bool:
    """
        Executes all API tests.
        :param xml_results: If True, it will generate an XML test report in a directory (TEST_RESULTS_DIR).
        :return: True, if test execution was successful; False, otherwise.
    """
    suite = TestLoader().discover(API_CONFIG['ROOT_API_FOLDER'])
    recursive_makedir(GLOBAL_CONFIG['TEST_RESULTS_DIR'])
    with open(GLOBAL_CONFIG['TEST_RESULTS_DIR'] + API_CONFIG['TESTS_FILENAME'], 'wb') as f:
        runner = TextTestRunner(failfast=True, verbosity=2) if not xml_results else XMLTestRunner(failfast=True,
                verbosity=2, output=f)
        results = runner.run(suite)
    return results.wasSuccessful()


def deploy(log_to_file=True, log_to_stdout=True, log_to_telegram=None):
    """
        Executes deployment actions. Possible actions are:
            - Creating the API MongoDB user.
            - Adding a list of authorized users to database.
            - Executing all the tests. Depending on the invocation (parameters '--with-tests' or '--with-test-reports')
              coverage and test results reports will be generated.
            - Removing all '.state' and log files.
        :param log_to_file: If True, saves log records into a log file.
        :param log_to_stdout: If True, emits log records to stdout.
        :param log_to_telegram: If True, sends CRITICAL log records via Telegram messages. Defaults to None, which means
                                that the default configuration will be used (global_config.config).
    """

    # Getting a logger instance
    logger = get_logger(__file__, 'DeployAPILogger', to_file=log_to_file, to_stdout=log_to_stdout, is_subsystem=False,
                        component=API_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--all', help='executes all deploy actions. This is the default option. If chosen, all '
                'other options will be ignored. Tests are not executed by default.', required=False, action='store_true')
        parser.add_argument('--db-user', help='creates the API MongoDB user', required=False, action='store_true')
        parser.add_argument('--add-users', help='adds the authorized users contained in the "authorized_users.config" '
                'file', required=False, action='store_true')
        parser.add_argument('--remove-files', help='removes all API .log files', required=False, action='store_true')
        parser.add_argument('--with-tests', help='executes all the API tests', required=False, action='store_true')
        parser.add_argument('--with-test-reports', help='executes all the API tests and generates a coverage report '
                'and a XML test results report', required=False, action='store_true')
        parser.add_argument('--skip-all', help='does not execute any deploy step', required=False, action='store_true')

        parser.add_argument('--adapt-legacy-data', help='adds climate zones to existent locations', required=False,
                            action='store_true')

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
        if args.all and any([args.db_user, args.add_users, args.remove_files]):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not any([args.all, args.db_user, args.add_users, args.remove_files, args.with_tests,
                      args.with_test_reports]) and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True, with_tests=False, with_test_reports=False)

        # 1. [Default] Verifying MongoDB is up (required both for adding users and tests).
        try:
            ping_database()
            logger.info('MongoDB daemon is up and reachable.')
        except EnvironmentError:
            logger.error('MongoDB service is down. Deploy will be aborted, since an active MongoDB service is required '
                    'for this operations.')
            exit(1)

        # 2. Creating MongoDB user.
        if args.all or args.db_user:
            logger.info('Creating Data Gathering Subsystem API user.')
            try:
                create_user(username=GLOBAL_CONFIG['MONGODB_API_USERNAME'],
                            password=GLOBAL_CONFIG['MONGODB_API_USER_PASSWORD'],
                            roles=[{"role": "read", "db": GLOBAL_CONFIG['MONGODB_DATABASE']}])
                logger.info('Successfully created API user.')
            except DuplicateKeyError:
                logger.warning('User was not created because it did already exist in database.')

        # 3. Adding API authorized users.
        if args.all or args.add_users:
            logger.info('Adding API authorized users to database.')
            with open(API_CONFIG['AUTHORIZED_USERS_FILEPATH'], 'r', encoding='utf-8') as f:
                users = yaml.load(f)
            authorized_users = []
            for user in users['authorized_users']:
                user_data = users['authorized_users'][user]
                if user_data.get('token') is None or user_data.get('scope') is None:
                    logger.error('Authorized user "%s" does not have the required fields. This may lead to unexpected '
                                 'errors while using API. Deploy will be aborted.' % user)
                    exit(1)
                authorized_users.append({'_id': user, 'token': user_data['token'], 'scope': user_data['scope']})
            added_users = bulk_create_authorized_users(authorized_users)
            if len(authorized_users) == added_users:
                logger.info('All API authorized users have been added (%d).' % added_users)
            else:
                logger.error('Some API authorized users have not been added (%d out of %d). Deploy will be aborted. '%(
                        added_users, len(authorized_users)))
                exit(1)

        # 4. Executing all tests
        if args.with_tests or args.with_test_reports:
            if args.with_test_reports:
                logger.info('Running all the API tests with branch coverage.')
                # Measuring coverage
                coverage_filepath = GLOBAL_CONFIG['COVERAGE_DIR'] + API_CONFIG['COVERAGE_FILENAME']
                coverage_analyzer = coverage.Coverage(source=[GLOBAL_CONFIG['ROOT_PROJECT_FOLDER']], branch=True,
                                                      concurrency="thread", data_file=coverage_filepath,
                                                      config_file=GLOBAL_CONFIG['COVERAGE_CONFIG_FILEPATH'])
                coverage_analyzer.start()
                success = _execute_tests(xml_results=True)
                coverage_analyzer.stop()
                sys.stderr.flush()
                logger = get_logger(__file__, 'DeployAPILogger', to_file=log_to_file, to_stdout=log_to_stdout,
                                    is_subsystem=False, component=API_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
                if success:
                    logger.info('Saving coverage report to "%s".' % coverage_filepath)
                    recursive_makedir(coverage_filepath, is_file=True)
                    coverage_analyzer.save()
            else:
                logger.info('Running all the API tests.')
                success = _execute_tests()
                sys.stderr.flush()
                logger = get_logger(__file__, 'DeployAPILogger', to_file=log_to_file, to_stdout=log_to_stdout,
                        is_subsystem=False, component=API_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
            if success:
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

        # 5. Emptying API logs and '.state' files.
        if args.all or args.remove_files:
            logger.info('Removing log base directory: %s' % (API_CONFIG['API_LOG_FILES_ROOT_FOLDER']))
            try:
                remove_all_under_directory(API_CONFIG['API_LOG_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('Log base directory does not exist, so it cannot be removed.')

        if args.adapt_legacy_data:
            from data_gathering_subsystem.data_modules.locations.locations import instance
            from utilities.mongo_util import MongoDBCollection
            from pymongo import InsertOne

            obj = instance()
            c = MongoDBCollection('locations', use_pool=False)
            locations, more = c.find()
            ops = []
            for location in locations:
                try:
                    location['climate_zone'] = obj.config['LOCATIONS'][location['name']]['climate_zone']
                except KeyError:
                    continue
                ops.append(InsertOne(location))
            c.remove_all()
            c.collection.bulk_write(ops)

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_file=False, log_to_stdout=True)
