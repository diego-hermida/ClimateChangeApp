import argparse
import sys

from os import environ
from telegram_bot.config.config import TELEGRAM_CONFIG
from unittest import TestLoader, TextTestRunner
from utilities.log_util import get_logger


def deploy(log_to_stdout=True):
    # Getting a logger instance
    logger = get_logger(__file__, 'DeployTelegramConfiguratorLogger', to_file=False, to_stdout=log_to_stdout,
                        is_subsystem=False, component=TELEGRAM_CONFIG['COMPONENT'], to_telegram=False)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--with-tests', help='executes all the Subsystem tests', required=False,
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
        elif not args.with_tests and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--with-tests" as the default option.')
            args = argparse.Namespace(with_tests=True)

        # 1. Executing all tests
        if args.with_tests:
            logger.info('Running all the Telegram Configurator tests.')
            loader = TestLoader()
            suite = loader.discover(TELEGRAM_CONFIG['ROOT_TELEGRAM_CONFIGURATOR_FOLDER'])
            runner = TextTestRunner(failfast=True, verbosity=2)
            results = runner.run(suite)
            sys.stderr.flush()
            logger = get_logger(__file__, 'DeployTelegramConfiguratorLogger', to_file=False, to_stdout=log_to_stdout,
                                is_subsystem=False, component=TELEGRAM_CONFIG['COMPONENT'], to_telegram=False)
            if results.wasSuccessful():
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_stdout=True)
