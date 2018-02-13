import argparse
import sys

from data_gathering_subsystem.config.config import DGS_CONFIG
from global_config.global_config import GLOBAL_CONFIG
from os import environ
from pymongo.errors import DuplicateKeyError
from unittest import TestLoader, TextTestRunner
from utilities.db_util import create_application_user, drop_application_database
from utilities.import_dir import import_modules
from utilities.log_util import get_logger
from utilities.util import remove_all_under_directory


def deploy(log_to_file=True, log_to_stdout=True):

    # Getting a logger instance
    logger = get_logger(__file__, 'DeployDataGatheringSubsystemLogger', to_file=log_to_file, to_stdout=log_to_stdout,
            is_subsystem=False)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        group = parser.add_argument_group()
        parser.add_argument('-a', '--all', help='executes all deploy actions. This is the default option. If chosen, the '
                'other options will be ignored. Tests are not executed by default.', required=False, action='store_true')
        group.add_argument('-u', '--db-user', help='creates the application MongoDB user', required=False,
                action='store_true')
        group.add_argument('-d', '--drop-database', help='drops all contents in application database', required=False,
                action='store_true')
        group.add_argument('-v', '--verify-modules', help='verifies all modules are instantiable and runnable',
                required=False, action='store_true')
        group.add_argument('-r', '--remove-files', help='removes all .log and .state files (and its directories)',
                required=False, action='store_true')
        parser.add_argument('-t', '--with-tests', help='executes all the Subsystem tests', required=False, action='store_true')
        parser.add_argument('-s', '--skip-all', help='does not execute any deploy step', required=False,
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
        if args.all and (args.db_user or args.drop_database or args.verify_modules or args.remove_files):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True, with_tests=False)

        # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
        modules = import_modules(DGS_CONFIG['DATA_MODULES_PATH'], recursive=True,
                                 base_package=DGS_CONFIG['DATA_COLLECTOR_BASE_PACKAGE'])

        # 1. Ensuring database is brand new.
        if args.all or args.drop_database:
            logger.info('Deleting previous database content.')
            drop_application_database()
            logger.info('Database has been cleared.')

        # 2. Creating MongoDB user.
        if args.all or args.db_user:
            logger.info('Creating Data Gathering Subsystem database owner.')
            try:
                create_application_user()
                logger.info('Successfully created user.')
            except DuplicateKeyError:
                logger.warning('User was not created because it did already exist in database.')

        # 3. Verifying all modules are instantiable and runnable.
        if args.all or args.verify_modules:
            logger.info('Verifying DataCollector(s) are instantiable.')
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

        # 4. Executing all tests
        if args.with_tests:
            logger.info('Running all the Data Gathering Subsystem tests.')
            loader = TestLoader()
            suite = loader.discover(DGS_CONFIG['ROOT_DATA_GATHERING_SUBSYSTEM_FOLDER'])
            runner = TextTestRunner(failfast=True, verbosity=2)
            results = runner.run(suite)
            sys.stderr.flush()
            logger = get_logger(__file__, 'DeployDataGatheringSubsystemLogger', to_file=log_to_file,
                    to_stdout=log_to_stdout, is_subsystem=False)
            if results.wasSuccessful():
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

        # 5. Emptying Subsystem's logs and '.state' files.
        if args.all or args.remove_files:
            logger.info('Removing log base directory: %s' % (GLOBAL_CONFIG['ROOT_LOG_FOLDER']))
            try:
                remove_all_under_directory(GLOBAL_CONFIG['ROOT_LOG_FOLDER'])
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
    deploy(log_to_file=False, log_to_stdout=True)
