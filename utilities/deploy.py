import argparse
import coverage
import sys
import xmlrunner.runner

from global_config.global_config import GLOBAL_CONFIG
from os import environ
from utilities.config.config import UTIL_CONFIG
from unittest import TestLoader, TextTestRunner
from utilities.log_util import get_logger
from utilities.util import recursive_makedir


def _execute_tests(xml_results=False) -> bool:
    """
        Executes all API tests.
        :param xml_results: If True, it will generate an XML test report in a directory (TEST_RESULTS_DIR).
        :return: True, if test execution was successful; False, otherwise.
    """
    suite = TestLoader().discover(UTIL_CONFIG['ROOT_UTIL_FOLDER'])
    recursive_makedir(GLOBAL_CONFIG['TEST_RESULTS_DIR'])
    with open(GLOBAL_CONFIG['TEST_RESULTS_DIR'] + UTIL_CONFIG['TESTS_FILENAME'], 'w') as f:
        runner = TextTestRunner(failfast=True, verbosity=2) if not xml_results else xmlrunner.runner.XMLTestRunner(
            failfast=True, verbosity=2, output=f)
        results = runner.run(suite)
    return results.wasSuccessful()


def deploy(log_to_stdout=True):
    # Getting a logger instance
    logger = get_logger(__file__, 'DeployUtilitiesLogger', to_file=False, to_stdout=log_to_stdout,
                        is_subsystem=False, component=['COMPONENT'], to_telegram=False)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--with-tests', help='executes all the Telegram Configurator tests', required=False,
                action='store_true')
        parser.add_argument('--with-test-reports', help='executes all the Telegram Configurator tests and generates'
                'a coverage report and a XML test results report', required=False, action='store_true')
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
        elif not any([args.with_tests, args.with_test_reports]) and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--with-tests" as the default option.')
            args = argparse.Namespace(with_tests=True, with_test_reports=False)

        # 1. Executing all tests
        if args.with_tests or args.with_test_reports:
            if args.with_test_reports:
                logger.info('Running all the Utilities tests with branch coverage.')
                # Measuring coverage
                coverage_filepath = GLOBAL_CONFIG['COVERAGE_DIR'] + UTIL_CONFIG['COVERAGE_FILENAME']
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
                logger.info('Running all the Utilities tests.')
                success = _execute_tests()
            sys.stderr.flush()
            logger = get_logger(__file__, 'DeployUtilitiesLogger', to_stdout=log_to_stdout,
                    is_subsystem=False, component=UTIL_CONFIG['COMPONENT'], to_telegram=False)
            if success:
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_stdout=True)
