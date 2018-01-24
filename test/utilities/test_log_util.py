from global_config.global_config import CONFIG as GLOBAL_CONFIG
from logging.handlers import RotatingFileHandler
from logging import StreamHandler, DEBUG, INFO
from os.path import exists
from shutil import rmtree
from unittest import TestCase, mock

import utilities.log_util


class TestLogUtil(TestCase):

    @classmethod
    def setUpClass(cls):
        utilities.log_util.CONFIG['MAX_LOG_FILE_SIZE'] = 4096

    def test_log_util(self):
        # Ensuring logger exists and is well configured
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + '/data_modules/my_module/my_module.py'
        expected = GLOBAL_CONFIG['ROOT_LOG_FOLDER'] + 'data_modules/my_module/my_module.log'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=True)
        self.assertTrue(exists(expected))
        self.assertEqual(2, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], StreamHandler)
        self.assertIsInstance(logger.logger.handlers[1], RotatingFileHandler)
        self.assertEqual(DEBUG, logger.logger.handlers[0].level)
        self.assertEqual(INFO, logger.logger.handlers[1].level)
        self.assertEqual(expected, logger.logger.handlers[1].baseFilename)
        # Testing log file removal
        utilities.log_util.remove_log_file(file)
        self.assertFalse(exists(file))

    @mock.patch('smtplib.SMTP.sendmail')
    @mock.patch('smtplib.SMTP.login')
    def test_email_sent(self, mock_login, mock_sendmail):
        # setUp
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + '/data_modules/my_module/my_module.py'
        expected_dir = GLOBAL_CONFIG['ROOT_LOG_FOLDER'] + 'data_modules/my_module/'
        # Invocation
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=False)
        for i in range((int(4096 / 200) + 3) * utilities.log_util.CONFIG['MAX_BACKUP_FILES']):
            logger.info('This log message occupies 200 bytes (note that the message header has also been included in '
                        'the byte count).')
        # Assertions
        self.assertTrue(mock_login.called)
        self.assertTrue(mock_sendmail.called)
        # tearDown
        rmtree(expected_dir)

    def test_handlers_are_removed(self):
        # Ensuring logger exists and is well configured
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + '/data_modules/my_module/my_module.py'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=True)
        self.assertEqual(2, len(logger.logger.handlers))
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=False, to_stdout=False)
        self.assertEqual(0, len(logger.logger.handlers))
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=False)
        self.assertEqual(1, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], RotatingFileHandler)
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=False, to_stdout=True)
        self.assertEqual(1, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], StreamHandler)
