from logging import Logger, INFO
from unittest import TestCase, main

import utilities.log_util


class TestLogUtil(TestCase):

    def test_log_util(self):
        from global_config.global_config import CONFIG
        from logging.handlers import RotatingFileHandler
        from logging import StreamHandler, DEBUG, INFO
        from os.path import exists

        # Ensuring logger exists and is well configured
        file = CONFIG['ROOT_PROJECT_FOLDER'] + '/data_modules/my_module/my_module.py'
        expected = CONFIG['ROOT_LOG_FOLDER'] + 'data_modules/my_module/my_module.log'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=True)
        self.assertTrue(exists(expected))
        self.assertEqual(2, len(logger.handlers))
        self.assertIsInstance(logger.handlers[0], StreamHandler)
        self.assertIsInstance(logger.handlers[1], RotatingFileHandler)
        self.assertEqual(DEBUG, logger.handlers[0].level)
        self.assertEqual(INFO, logger.handlers[1].level)
        self.assertEqual(expected, logger.handlers[1].baseFilename)

        # Testing log file removal
        utilities.log_util.remove_log_file(file)
        self.assertFalse(exists(file))
