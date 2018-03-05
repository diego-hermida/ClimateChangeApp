import builtins
import datetime
import logging
import smtplib
import sys
import telegram
import threading

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from global_config.global_config import GLOBAL_CONFIG
from logging.handlers import BaseRotatingHandler, RotatingFileHandler
from os import sep as os_file_separator, remove
from os.path import basename, exists
from pytz import UTC
from shutil import copyfile
from telegram_bot.config.config import TELEGRAM_CONFIG
from utilities.util import get_config, recursive_makedir, serialize_date, get_module_name, get_exception_info

CONFIG = get_config(__file__)


class TelegramHandler(logging.Handler):
    """
        This class allows sending messages to a Telegram chat. A Telegram Bot is used to achieve this.
        If any Telegram error occurs during the process, a WARNING log record will be emitted.
        Telegram bot configuration is read from 'telegram_config.config' and 'global_config.config'.
        Telegram messages will be sent in their own Thread.
    """
    def __init__(self):
        super().__init__()
        self.logger = None

    def _send_message(self, record):
        bot = telegram.Bot(TELEGRAM_CONFIG['TOKEN'])
        message = 'An error occurred. Details:\n  - Component: `%s`\n  - Error level: `%s`\n  - Logger name: `%s`' \
                  '\n  - Subsystem ID: `%s`\n  - Execution ID: `%s`\n  - Timestamp: `%s`\n  - Caller: `%s:%d (%s)' \
                  ' @ %s`\n  - Message: `%s`\n  - Stack trace: `%s`' % (
                  record.component if hasattr(record, 'component') else 'N/A', record.levelname, record.name,
                  record.subsystem_id if hasattr(record, 'subsystem_id') else 'N/A',
                  record.execution_id if hasattr(record, 'execution_id') else 'N/A', record.asctime if
                  hasattr(record, 'asctime') else 'N/A', record.filename, record.lineno, record.funcName,
                  record.threadName, record.msg, record.stack_info if record.stack_info else 'N/A')
        try:
            bot.send_message(chat_id=GLOBAL_CONFIG['TELEGRAM_CHAT_ID'], text=message,
                             parse_mode=telegram.ParseMode.MARKDOWN)
            pass
        except telegram.error.TelegramError as ex:
            self.logger.warning('Error message could not be sent via Telegram. Cause: %s' % get_exception_info(ex))

    def emit(self, record):
        if GLOBAL_CONFIG.get('TELEGRAM_CHAT_ID'):
            threading.Thread(target=self._send_message(record)).start()
        else:
            self.logger.warning('Error message could not be sent via Telegram. Cause: TELEGRAM_CHAT_ID is None '
                                '(global_config.config).')


class SMTPRotatingFileHandler(RotatingFileHandler):
    """
        This class customizes the RotatingFileHandler class, by sending the oldest log file automatically before being
        deleted.
        When the oldest log file is about to be deleted (i.e. a {filename}.log.{backupCount} does already exist), this
        file is copied (to avoid locking files) to {filename}.oldest.log, and sent by e-mail.
        The e-mail operation can be executed both synchronously and async (by default).
        E-mail settings (to, from, server, port, etc.) are read from the 'log_util.config' configuration file.
    """
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False, async_email=True):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.async_email=async_email

    def emit(self, record):
        """
            Emits a record. If shouldRollover evaluates to True, it also sends the oldest log file by email.
            The file is sent
        """
        try:
            if self.shouldRollover(record):
                last_log_file = self.rotation_filename("%s.%d" % (self.baseFilename, self.backupCount))
                if exists(last_log_file):
                    # Copies the file in order to avoid race conditions
                    dest_file_name = self.baseFilename.replace('.log', '.oldest.log')
                    copyfile(last_log_file, dest_file_name)
                    if self.async_email:
                        threading.Thread(target=self.send_oldest_by_email(dest_file_name)).start()
                    else:
                        self.send_oldest_by_email(dest_file_name)
                self.doRollover()
            logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def send_oldest_by_email(self, path: str):
        """
            Sends an e-mail with an attachement, a log file.
            If an error occurs, it will be handled with the 'self.handleError()' method.
            :param path: Path to the log file which will be attached to the e-mail.
        """
        try:
            smtp = smtplib.SMTP(CONFIG['EMAIL_SERVER'], CONFIG['EMAIL_PORT'], timeout=CONFIG['EMAIL_TIMEOUT'])
            msg = MIMEMultipart()
            msg['From'] = CONFIG['EMAIL_FROM']
            msg['To'] = CONFIG['EMAIL_TO']
            msg['Date'] = serialize_date(datetime.datetime.now(tz=UTC))
            msg['Subject'] = CONFIG['EMAIL_SUBJECT']

            body_text = 'This e-mail has been automatically generated by the Climate Change Application. \n' \
                        'If you do not want to keep receiving these e-mails, please contact the Subsystem ' \
                        'administrator: ' + CONFIG['EMAIL_SUBSYSTEM_ADMIN'] + '\n\n' \
                        '------------------------------------\n' \
                        'Climate Change Application \nDiego Hermida Carrera\'s Final Degree Project.\n' \
                        '2017-2018, University of A Coruña (Spain).\n\n\n'

            body = MIMEText(body_text, 'plain')
            msg.attach(body)

            with open(path, "r") as fd:
                attachment = MIMEText(fd.read())
                attachment.add_header("Content-Disposition", "attachment", filename=basename(path))
                msg.attach(attachment)

            if CONFIG['EMAIL_USE_TLS']:
                smtp.ehlo()
                smtp.starttls()
            smtp.login(CONFIG['EMAIL_FROM'], CONFIG['EMAIL_PASSWORD'])
            smtp.sendmail(CONFIG['EMAIL_FROM'], CONFIG['EMAIL_TO'], msg.as_string())
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError('[ERROR] An error occurred while sending log file by email.')
        finally:
            try:
                remove(path)
            except:
                self.handleError('[WARNING] Unable to delete log copy file.')


def get_logger(path: str, name: str, root_dir: str = GLOBAL_CONFIG['ROOT_LOG_FOLDER'], level=logging.INFO,
               date_format=CONFIG['LOG_DATE_FORMAT'], line_format=CONFIG['LOG_SUBSYSTEM_RECORD_FORMAT'],
               to_stdout=False, stdout_level=logging.DEBUG, to_file=True, oldest_to_email=True, async_email=True,
               is_subsystem=True, subsystem_id=None, component=None,
               to_telegram=None) -> logging.LoggerAdapter:
    """
        Configures a logging.Logger object.
        Log file maximum size is limited to MAX_LOG_FILE_SIZE. If max size is reached, current log file is closed and
        renamed to '{log file name}.1'. Next time MAX_LOG_FILE_SIZE is reached, a '{log file name}.2' will be created;
        and so on, until MAX_BACKUP_FILES are created. Oldest log file is deleted when MAX_BACKUP_FILES have been filled,
        and a new backup file is created.
        To see where log files are saved, read _get_log_filepath() documentation (log_util.py:54).
        :param path: Path of the calling module (expected: __file__ ).
        :param name: Logger's name.
        :param root_dir: Log files' root directory.
        :param level: Minimum issue level to include log records into log file.
        :param date_format: Date format. Default format is 'dd-MM-yyyy hh:mm:ss.fff'
        :param line_format: Line format. Default format is '[<level>] <timestamp> <file:line @ threadName>: <message>'
        :param to_stdout: If True, prints log records to stdout.
        :param stdout_level: Stdout's issue level.
        :param to_file: If True, saves log records to a log file.
        :param oldest_to_email: If True, sends the oldest log file by email.
        :param async_email: If True, sends the e-mails in their own thread.
        :param is_subsystem: If True, logging records will have the LOG_SUBSYSTEM_RECORD_FORMAT.
        :param subsystem_id: The ID of the Subsystem. If the ID is > 1, the log file will be stored under a directory
                             named: <root directory>_<subsystem ID>
        :param component: Name of the component (Data Gathering Subsystem, API...)
        :param to_telegram: If True, sends CRITICAL and (optionally) ERROR records to a Telegram chat. Defaults to None,
                            which means that this property will be set to the value specified in the
                            'global_config.config' file.
        :return: A logging.LoggerAdapter object, configured and initialized with arguments.
        :rtype: logging.LoggerAdapter
    """
    to_telegram = GLOBAL_CONFIG['ENABLE_TELEGRAM_LOGGING'] if to_telegram is None else to_telegram
    logger = logging.getLogger(name)
    formatter = logging.Formatter(line_format if is_subsystem else CONFIG['LOG_RECORD_FORMAT'], datefmt=date_format)
    # Configuring stream handler
    if to_stdout and not _has_stream_handler(logger):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(stdout_level)
        logger.addHandler(stream_handler)
    elif not to_stdout:
        _remove_stream_handlers(logger)
    # Configuring file handler
    if to_file and not _has_rotating_file_handler(logger):
        path = _get_log_filepath(path, root_dir=root_dir)
        recursive_makedir(path[:path.rfind(os_file_separator)])
        if oldest_to_email:
            file_handler = SMTPRotatingFileHandler(filename=path, maxBytes=CONFIG['MAX_LOG_FILE_SIZE'],
                    encoding=CONFIG['LOG_FILE_ENCODING'], backupCount=CONFIG['MAX_BACKUP_FILES'],
                    async_email=async_email)
        else:
            file_handler = RotatingFileHandler(filename=path, maxBytes=CONFIG['MAX_LOG_FILE_SIZE'],
                    encoding=CONFIG['LOG_FILE_ENCODING'], backupCount=CONFIG['MAX_BACKUP_FILES'])
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    elif not to_file:
        _remove_rotating_file_handlers(logger)
    # Configuring Telegram handler
    telegram_handler = None
    if to_telegram and not _has_telegram_handler(logger):
        telegram_handler = TelegramHandler()
        telegram_handler.setFormatter(formatter)
        telegram_handler.setLevel(logging.ERROR if GLOBAL_CONFIG['TELEGRAM_LOGGING_LEVEL'] == 'ERROR'
                else logging.CRITICAL)
        logger.addHandler(telegram_handler)
    elif not to_telegram:
        _remove_telegram_handlers(logger)
    logger.setLevel(min(level, stdout_level))  # Logger must have the minimum level
    # Getting execution ID to display it in all log records
    if is_subsystem:
        try:
            builtins.EXECUTION_ID
        except AttributeError:
            builtins.EXECUTION_ID = None
        adapter = logging.LoggerAdapter(logger, {'execution_id': 'N/A' if builtins.EXECUTION_ID is None else str(
                builtins.EXECUTION_ID), 'subsystem_id': 'N/A' if subsystem_id is None else str(subsystem_id),
                'component': 'N/A' if not component else component})
        if telegram_handler:
            telegram_handler.logger = adapter
        return adapter
    else:
        adapter = logging.LoggerAdapter(logger, {'component': 'N/A' if not component else str(component)})
        if telegram_handler:
            telegram_handler.logger = adapter
        return adapter


def remove_log_file(path: str, root_dir: str = GLOBAL_CONFIG['ROOT_LOG_FOLDER']):
    """
        Given the file path to a '.py' file (DataCollector module), deletes the log file attached to it.
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :param root_dir: Log files' root directory.
    """
    from os import remove
    remove(_get_log_filepath(path, root_dir=root_dir))


def _get_log_filepath(path: str, root_dir: str = GLOBAL_CONFIG['ROOT_LOG_FOLDER']) -> str:
    """
    By convention, any log record generated by a module is stored in a file which is located under a base log directory,
    ROOT_LOG_FOLDER (log_util.config). To ease finding log files, paths from DataGatheringSubsystem's base directory are
    preserved. So, in order to get the log filepath of an arbitrary file, what we do is to append the  calling module's
    path from DataGatheringSubsystem's root folder to ROOT_LOG_FOLDER. Example:
            - ROOT_LOG_FOLDER: /var/log/DataGatheringSubsystem
            - Calling module: .../DataGatheringSubsystem/data_modules/historical_weather/historical_weather.py
            - Log file: /var/log/DataGatheringSubsystem/data_modules/historical_weather/historical_weather.log
    :param path: A <str> containing a valid path (see the example above).
    :param root_dir: Log files' root directory.
    :return: The log file path of a file.
    """
    filename = get_module_name(path) + '.log'
    return root_dir + filename if not root_dir[-1] == '/' else root_dir + '/' + filename


def _has_rotating_file_handler(logger: logging.Logger) -> bool:
    """
        Given a logging.Logger object, determines if it 'handlers' attribute contains an instance of BaseRotatingHandler.
        :param logger: A logging.logger object.
        :return: True, if 'logger.handlers' contains an 'BaseRotatingHandler' handler; False, otherwise.
    """
    for h in logger.handlers:
        if isinstance(h, BaseRotatingHandler):
            return True
    return False


def _has_stream_handler(logger: logging.Logger) -> bool:
    """
        Given a logging.Logger object, determines if it 'handlers' attribute contains an instance of StreamHandler.
        :param logger: A logging.logger object.
        :return: True, if 'logger.handlers' contains an 'StreamHandler' handler; False, otherwise.
    """
    for h in logger.handlers:
        if type(h) is logging.StreamHandler:
            return True
    return False


def _has_telegram_handler(logger: logging.Logger) -> bool:
    """
        Given a logging.Logger object, determines if it 'handlers' attribute contains an instance of TelegramHandler.
        :param logger: A logging.logger object.
        :return: True, if 'logger.handlers' contains an 'TelegramHandler' handler; False, otherwise.
    """
    for h in logger.handlers:
        if type(h) is TelegramHandler:
            return True
    return False


def _remove_stream_handlers(logger: logging.Logger):
    """
        Given a logging.Logger object, removes all StreamHandler handlers contained in 'logger.handlers'.
        If 'logger.handlers' does not have StreamHandler handlers, it's a no-op.
        :param logger: A logging.logger object.
    """
    for h in logger.handlers:
        if type(h) is logging.StreamHandler:
            logger.removeHandler(h)


def _remove_rotating_file_handlers(logger: logging.Logger):
    """
        Given a logging.Logger object, removes all BaseRotatingHandler handlers contained in 'logger.handlers'.
        If 'logger.handlers' does not have BaseRotatingHandler handlers, it's a no-op.
        :param logger: A logging.logger object.
    """
    for h in logger.handlers:
        if isinstance(h, BaseRotatingHandler):
            logger.removeHandler(h)


def _remove_telegram_handlers(logger: logging.Logger):
    """
        Given a logging.Logger object, removes all TelegramHandlers handlers contained in 'logger.handlers'.
        If 'logger.handlers' does not have Telegram handlers, it's a no-op.
        :param logger: A logging.logger object.
    """
    for h in logger.handlers:
        if type(h) is TelegramHandler:
            logger.removeHandler(h)
