import argparse

from global_config.global_config import CONFIG
from os import environ
from pymongo.errors import DuplicateKeyError
from sys import exit
from unittest import TestLoader, TextTestRunner
from utilities.db_util import create_application_user, drop_application_database
from utilities.import_dir import import_modules
from utilities.log_util import get_logger
from utilities.util import remove_all_under_directory


def deploy():

    # Getting a logger instance
    logger = get_logger(__file__, 'DeployLogger', to_stdout=True, to_file=False)
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
        args = parser.parse_args()
        # Fixes [BUG-019]
        if args.skip_all or (bool(environ.get('SKIP_DEPLOY')) and environ.get('SKIP_DEPLOY').upper() == 'TRUE'):
            logger.info('Deploy operations have been skipped.')
            exit(0)
        if args.all and (args.db_user or args.drop_database or args.verify_modules or args.remove_files):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not (args.all or args.db_user or args.drop_database or args.verify_modules or args.remove_files or args.with_tests):
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True)

        # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
        modules = import_modules(CONFIG['DATA_MODULES_PATH'], recursive=True,
                                 base_package=CONFIG['DATA_COLLECTOR_BASE_PACKAGE'])

        # 1. Creating MongoDB user.
        if args.all or args.db_user:
            logger.info('Creating MongoDB user.')
            try:
                create_application_user()
                logger.info('Successfully created user and database.')
            except DuplicateKeyError:
                logger.warning('MongoDB user already exists in database.')

        # 2. Ensuring database is brand new.
        if args.all or args.drop_database:
            logger.info('Deleting previous database content.')
            drop_application_database()
            logger.info('Database has been cleared.')

        # 3. Verifying all modules are instantiable and runnable.
        if args.all or args.verify_modules:
            logger.info('Verifying DataCollector(s) are instantiable.')
            failed = []
            for module in modules:
                data_collector = module.instance()
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
            loader = TestLoader()
            suite = loader.discover(CONFIG['ROOT_PROJECT_FOLDER'])
            runner = TextTestRunner(failfast=True, verbosity=2)
            results = runner.run(suite)
            if results.wasSuccessful():
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

        # 5. Emptying Subsystem's logs and '.state' files.
        if args.all or args.remove_files:
            logger.info('Removing log base directory: %s' % (CONFIG['ROOT_LOG_FOLDER']))
            try:
                remove_all_under_directory(CONFIG['ROOT_LOG_FOLDER'])
            except FileNotFoundError:
                logger.info('Log base directory does not exist, so it cannot be removed.')
            try:
                logger.info('Removing .state files\' base directory: %s' % (CONFIG['STATE_FILES_ROOT_FOLDER']))
                remove_all_under_directory(CONFIG['STATE_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('.state files\' base directory does not exist, so it cannot be removed.')

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy()