import argparse
import coverage
import sys
import xmlrunner.runner

from data_gathering_subsystem.config.config import DGS_CONFIG
from global_config.global_config import GLOBAL_CONFIG
from os import environ
from pymongo.errors import DuplicateKeyError
from unittest import TestLoader, TextTestRunner
from utilities.db_util import create_user, drop_database, ping_database, MongoDBCollection
from utilities.import_dir import import_modules
from utilities.log_util import get_logger
from utilities.util import remove_all_under_directory, get_config, recursive_makedir


def _execute_tests(xml_results=False) -> bool:
    """
        Executes all API tests.
        :param xml_results: If True, it will generate an XML test report in a directory (TEST_RESULTS_DIR).
        :return: True, if test execution was successful; False, otherwise.
    """
    suite = TestLoader().discover(DGS_CONFIG['ROOT_DATA_GATHERING_SUBSYSTEM_FOLDER'])
    recursive_makedir(GLOBAL_CONFIG['TEST_RESULTS_DIR'])
    with open(GLOBAL_CONFIG['TEST_RESULTS_DIR'] + DGS_CONFIG['TESTS_FILENAME'], 'w') as f:
        runner = TextTestRunner(failfast=True, verbosity=2) if not xml_results else xmlrunner.runner.XMLTestRunner(
            failfast=True, verbosity=2, output=f)
        results = runner.run(suite)
    return results.wasSuccessful()


def deploy(log_to_file=True, log_to_stdout=True, log_to_telegram=None):

    # Getting a logger instance
    logger = get_logger(__file__, 'DeployDataGatheringSubsystemLogger', to_file=log_to_file, to_stdout=log_to_stdout,
            is_subsystem=False, component=DGS_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--all', help='executes all deploy actions. This is the default option. If chosen, all '
                'other options will be ignored. Tests are not executed by default.', required=False, action='store_true')
        parser.add_argument('--db-user', help='creates the Data Gathering Subsystem MongoDB user', required=False,
                action='store_true')
        parser.add_argument('--drop-database', help='drops all contents in application database', required=False,
                action='store_true')
        parser.add_argument('--create-indexes', help='creates indexes specified in the "deploy.config" file',
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
        if args.all and any([args.db_user, args.drop_database, args.verify_modules, args.remove_files,
                args.create_indexes]):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not any([args.all, args.db_user, args.drop_database, args.verify_modules, args.remove_files,
                args.with_tests, args.with_test_reports, args.create_indexes]) and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True, with_tests=False, with_test_reports=False)

        # 1. [Default] Verifying MongoDB is up (required both for deploy operations and tests).
        try:
            ping_database()
            logger.info('MongoDB daemon is up and reachable.')
        except EnvironmentError:
            logger.error(
                'MongoDB service is down. Deploy will be aborted, since an active MongoDB service is required '
                'for this operations.')
            exit(1)

        # 1. Ensuring database is brand new.
        if args.all or args.drop_database:
            logger.info('Deleting previous database content.')
            drop_database()
            logger.info('Database has been cleared.')

        # 2. Creating MongoDB user.
        if args.all or args.db_user:
            logger.info('Creating Data Gathering Subsystem user, the database owner.')
            try:
                create_user(username=GLOBAL_CONFIG['MONGODB_USERNAME'], password=GLOBAL_CONFIG['MONGODB_USER_PASSWORD'],
                            roles=[{"role": "dbOwner", "db": GLOBAL_CONFIG['MONGODB_DATABASE']}])
                logger.info('Successfully created user.')
            except DuplicateKeyError:
                logger.warning('User was not created because it did already exist in database.')

        # 3. Creating MongoDB indexes.
        if args.all or args.create_indexes:
            logger.info('Creating database indexes. Configuration is read from the "deploy.config" file.')
            index_info = get_config(__file__)['MONGODB_INDEXES']
            for collection_name in index_info:
                keys = []
                unique = index_info[collection_name].get('unique', False)
                name = index_info[collection_name].get('name')
                if name is None:
                    name = collection_name + '__index_on__'
                    _keys = [list(x.keys())[0] for x in index_info[collection_name]['keys']]
                    for k in _keys:
                        name += k + '__'
                    name = name[:-2]
                for i in index_info[collection_name]['keys']:
                    keys.append(list(i.items())[0])
                c = MongoDBCollection(collection_name=collection_name, use_pool=True)
                c.collection.create_index(keys=keys, unique=unique, name=name)
                if name in c.collection.index_information():
                    logger.info('Index "%s" has been successfully created.' % name)

        # 4. Verifying all modules are instantiable and runnable.
        if args.all or args.verify_modules:
            logger.info('Verifying DataCollector(s) are instantiable.')
            # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
            modules = import_modules(DGS_CONFIG['DATA_MODULES_PATH'], recursive=True,
                                     base_package=DGS_CONFIG['DATA_COLLECTOR_BASE_PACKAGE'])
            failed = []
            for module in modules:
                data_collector = module.instance(log_to_stdout=False, log_to_file=False)
                try:
                    assert data_collector.is_runnable()
                except AssertionError:
                    failed.append(str(data_collector))
                    logger.error('"%s" is not instantiable nor runnable.' % (data_collector))
            if failed:
                logger.warning(
                    'Some DataCollector(s) are not runnable (%d out of %d): %s' % (len(failed), len(modules), failed))
            else:
                logger.info('All DataCollector class(es) are instantiable and runnable.')

        # 5. Executing all tests
        if args.with_tests or args.with_test_reports:
            if args.with_test_reports:
                logger.info('Running all the Data Gathering Subsystem tests with branch coverage.')
                # Measuring coverage
                coverage_filepath = GLOBAL_CONFIG['COVERAGE_DIR'] + DGS_CONFIG['COVERAGE_FILENAME']
                coverage_analyzer = coverage.Coverage(source=[GLOBAL_CONFIG['ROOT_PROJECT_FOLDER']], branch=True,
                                                      concurrency="thread", data_file=coverage_filepath)
                coverage_analyzer.start()
                success = _execute_tests(xml_results=True)
                coverage_analyzer.stop()
                if success:
                    logger.info('Saving coverage report to "%s".' % coverage_filepath)
                    recursive_makedir(coverage_filepath, is_file=True)
                    coverage_analyzer.save()
            else:
                logger.info('Running all the Data Gathering Subsystem tests.')
                success = _execute_tests()
            sys.stderr.flush()
            logger = get_logger(__file__, 'DeployDataGatheringSubsystemLogger', to_file=log_to_file,
                    to_stdout=log_to_stdout, is_subsystem=False, component=DGS_CONFIG['COMPONENT'],
                    to_telegram=log_to_telegram)
            if success:
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

        # 6. Emptying Subsystem's logs and '.state' files.
        if args.all or args.remove_files:
            logger.info('Removing log base directory: %s' % (DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER']))
            try:
                remove_all_under_directory(DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('Log base directory does not exist, so it cannot be removed.')
            try:
                logger.info('Removing .state files\' base directory: %s' % (DGS_CONFIG[
                        'DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER']))
                remove_all_under_directory(DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('.state files\' base directory does not exist, so it cannot be removed.')

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_file=False, log_to_stdout=True, log_to_telegram=None)
