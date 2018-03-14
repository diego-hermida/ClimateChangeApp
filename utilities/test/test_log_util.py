from copy import deepcopy
from logging import DEBUG, INFO, CRITICAL, StreamHandler
from logging.handlers import RotatingFileHandler
from os.path import exists
from unittest import TestCase, mock

import utilities.log_util
from utilities.util import remove_all_under_directory
from global_config.config import GLOBAL_CONFIG

_CONFIG = deepcopy(utilities.log_util.CONFIG)
_GLOBAL_CONFIG = deepcopy(utilities.log_util.GLOBAL_CONFIG)

_CONFIG['MAX_LOG_FILE_SIZE'] = 4096
_GLOBAL_CONFIG['ENABLE_TELEGRAM_LOGGING'] = True
_GLOBAL_CONFIG['TELEGRAM_CHAT_ID'] = 138919127
_GLOBAL_CONFIG['TELEGRAM_LOGGING_LEVEL'] = 'CRITICAL'

@mock.patch('utilities.log_util.GLOBAL_CONFIG', _GLOBAL_CONFIG)
@mock.patch('utilities.log_util.CONFIG', _CONFIG)
class TestLogUtil(TestCase):

    def test_log_util(self):
        # Ensuring logger exists and is well configured
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + 'data_modules/my_module/my_module.py'
        expected = GLOBAL_CONFIG['ROOT_LOG_FOLDER'] + 'my_module.log'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=True, to_telegram=True)
        self.assertTrue(exists(expected))
        self.assertEqual(3, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], utilities.log_util.TelegramHandler)
        self.assertIsInstance(logger.logger.handlers[1], StreamHandler)
        self.assertIsInstance(logger.logger.handlers[2], RotatingFileHandler)
        self.assertEqual(CRITICAL, logger.logger.handlers[0].level)
        self.assertEqual(DEBUG, logger.logger.handlers[1].level)
        self.assertEqual(INFO, logger.logger.handlers[2].level)
        self.assertEqual(expected, logger.logger.handlers[2].baseFilename)
        # Testing log file removal
        utilities.log_util.remove_log_file(file)
        self.assertFalse(exists(file))

    @mock.patch('telegram.Bot')
    def test_telegram_handler(self, mock_bot):
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + 'data_modules/my_module/my_module.py'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_stdout=False, to_file=False, to_telegram=True)
        logger.error('Test ERROR message.')
        self.assertFalse(mock_bot.return_value.called)
        logger.critical('Test CRITICAL message.')
        self.assertEqual(1, mock_bot.return_value.send_message.call_count)

    @mock.patch('telegram.Bot')
    def test_telegram_handler_with_error(self, mock_bot):
        from telegram.error import Unauthorized
        from logging import WARNING
        mock_bot.return_value.send_message.side_effect = Unauthorized('Test error. This is OK.')
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + 'data_modules/my_module/my_module.py'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_stdout=False, to_file=False, to_telegram=True,
                                               component='TEST', is_subsystem=True, subsystem_id=1)
        with self.assertLogs('TestLogger', level=WARNING):
            logger.critical('Test CRITICAL message.')

    def test_telegram_handler_when_CHAT_ID_is_None(self):
        from logging import WARNING
        previous_chat_id = _GLOBAL_CONFIG['TELEGRAM_CHAT_ID']
        _GLOBAL_CONFIG['TELEGRAM_CHAT_ID'] = None
        try:
            file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + 'data_modules/my_module/my_module.py'
            logger = utilities.log_util.get_logger(file, 'TestLogger', to_stdout=False, to_file=False, to_telegram=True)
            with self.assertLogs('TestLogger', level=WARNING):
                logger.critical('Test CRITICAL message.')
        finally:
            _GLOBAL_CONFIG['TELEGRAM_CHAT_ID'] = previous_chat_id

    @mock.patch('smtplib.SMTP')
    def test_email_sent(self, mock_smtp):
        # setUp
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + 'data_modules/my_module/my_module.py'
        expected_dir = GLOBAL_CONFIG['ROOT_LOG_FOLDER']
        # Invocation
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=False)
        for i in range((int(4096 / 200) + 3) * utilities.log_util.CONFIG['MAX_BACKUP_FILES']):
            logger.info('This log message occupies 200 bytes (note that the message header has also been included in '
                        'the byte count).')
        # Assertions
        self.assertTrue(mock_smtp.return_value.login.called)
        self.assertTrue(mock_smtp.return_value.ehlo.called)
        self.assertTrue(mock_smtp.return_value.starttls.called)
        self.assertTrue(mock_smtp.return_value.sendmail.called)
        # tearDown
        remove_all_under_directory(expected_dir)

    def test_handlers_are_removed(self):
        # Ensuring logger exists and is well configured
        file = GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + 'data_modules/my_module/my_module.py'
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=True, to_telegram=True)
        self.assertEqual(3, len(logger.logger.handlers))
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=False, to_stdout=False, to_telegram=False)
        self.assertEqual(0, len(logger.logger.handlers))
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=True, to_stdout=False, to_telegram=False)
        self.assertEqual(1, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], RotatingFileHandler)
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=False, to_stdout=True, to_telegram=False)
        self.assertEqual(1, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], StreamHandler)
        logger = utilities.log_util.get_logger(file, 'TestLogger', to_file=False, to_stdout=False, to_telegram=True)
        self.assertEqual(1, len(logger.logger.handlers))
        self.assertIsInstance(logger.logger.handlers[0], utilities.log_util.TelegramHandler)
