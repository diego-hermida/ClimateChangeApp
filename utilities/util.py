import datetime
import errno
import json
import pytz
import signal
import yaml

from contextlib import contextmanager
from os import makedirs, sep as os_file_separator
from os.path import exists
from random import randint
from doc.relativedelta import relativedelta


def enum(*args) -> type:
    """
        Emulates Java enumerated type.
        :param args: Enumerated values (separated by commas).
    """
    return type('Enum', (), dict(zip(args, args)))


TimeUnits = enum('s', 'min', 'h', 'day', 'week', 'month', 'year', 'NEVER')
MeasureUnits = enum('mm', 'm', 'km', 'Gt')
MassType = enum('antarctica', 'greenland', 'ocean')


def date_to_millis_since_epoch(date: datetime.datetime) -> int:
    """
        Given a date, converts it to milliseconds since epoch (UNIX time, 01/01/1970 00:00:00.0 UTC).
        :param date: A datetime.datetime object, whose timezone must be UTC.
        :raise ValueError: If input date is not UTC.
        :return: An int, representing milliseconds since epoch.
        :rtype: int
    """
    if date.tzinfo != pytz.UTC:
        raise ValueError('Date timezone must be UTC')
    return int((date.replace(tzinfo=pytz.UTC) - datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.UTC)).
            total_seconds() * 1000.0)


def decimal_date_to_millis_since_epoch(decimal_date: float) -> int:
    """
        Given a decimal date (float), converts it to milliseconds since epoch (UNIX time, 01/01/1970 00:00:00.0 UTC).
        :param decimal_date: A float, representing a decimal date in UTC timezone.
        :return: An int, representing milliseconds since epoch.
        :rtype: int
    """
    decimal_date = float(decimal_date)
    year = int(decimal_date)
    rem = decimal_date - year
    base = datetime.datetime(year, 1, 1).replace(tzinfo=pytz.UTC)
    result = base + datetime.timedelta(seconds=(base.replace(year=base.year + 1) - base).total_seconds() * rem)
    return date_to_millis_since_epoch(result)


def recursive_makedir(path: str):
    """
        Recursively creates all directories under a base directory. If a directory does already exist, silently performs
        the operation (FileExistsError is handled).
        :param path: A valid directory path. Example: /var/log/DataGatheringSubsystem/data_modules, where 'data_modules'
                     is a directory (can be non-existent).
        :raise PermissionError: If an attempt to create a directory without the necessary privileges is made.
    """
    try:
        makedirs(path)
    except FileExistsError as ex:
        assert ex.errno == errno.EEXIST


def get_config(path: str) -> dict:
    """
        Given the file path to a '.py' file (DataCollector module), retrieves the configuration inside the  '.config'
        file (under the same directory as the module).
        Precondition: The '.config' file is a valid YAML file.
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :return: A dict object, containing all data inside the '.config' file.
        :rtype: dict
    """
    path = path.replace('.py', '.config')
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.load(f)
    return config


def map_data_collector_path_to_state_file_path(path: str) -> str:
    """
    Given the path to a file, returns the path to a '.state' file (with the same name as the original one) under the
    STATE_FILES_ROOT_FOLDER (from global_config.global_config.CONFIG).
    :param path: Path to the target file.
    :return: Path to the '.state' file, under STATE_FILES_ROOT_FOLDER.
    :rtype: str
    """
    from global_config.global_config import CONFIG

    file_name = get_module_name(path)
    return CONFIG['STATE_FILES_ROOT_FOLDER'] + file_name + '.state'


def create_state_file(path: str):
    """
        Given the path to a '.state' file, creates it. If directory hierarchy does not exist it is also created.
    """
    recursive_makedir(path[:path.rfind(os_file_separator)])
    open(path, 'w').close()

def remove_state_file(path: str):
    """
        Given the path to a data module, removes its attached '.state' file.
        :param path:
    """
    from os import remove
    remove(map_data_collector_path_to_state_file_path(path))


def read_state(path: str, repair_struct: dict) -> dict:
    """
        Given the file path to a '.py' file (DataCollector module), retrieves the data inside the  '.state'
        file (located under the STATE_FILES_ROOT_FOLDER or a subdirectory). If
        Precondition: If file exists, file content is a serialized JSON document.
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :param repair_struct: If the document is unparseable, this structure allows the '.state' file to reach a
                              consistent state. This structure is dumped into the '.state' file if it's unparseable.
        :return: A dict, containing all data inside the '.state' file, or 'repair_struct' if the '.state' file is
                 unparseable.
    """
    path = map_data_collector_path_to_state_file_path(path)
    if not exists(path):
        create_state_file(path)
    with open(path, 'r') as f:
        try:
            state = json.load(f)
        except json.decoder.JSONDecodeError:  # State is invalid, creating empty state according to REPAIR_STRUCT
            f.close()
            with open(path, 'w') as f2:
                json.dump(repair_struct, f2)
            return repair_struct
    return state


def write_state(state: dict, path: str) -> str:
    """
        Given the file path to a '.py' file (DataCollector module), serializes the 'state' variable into the '.state'
        file (under the same directory as the module).
        Precondition: The 'state' variable is valid JSON document.
        :param state: A valid JSON document (as a dict object).
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :return: The file path to the written '.state' file.
    """
    state_path = map_data_collector_path_to_state_file_path(path)
    with open(state_path, 'w') as f:
        json.dump(state, f)
    return state_path

def serialize_date(date: datetime.datetime) -> str:
    """
        Serializes a date using the ISO format.
        :return: The serialized date, if date is valid; or None, if the date is None.
        :raise ValueError: If input date is not UTC.
        :rtype: str
    """
    if date and date.tzinfo != pytz.UTC:
        raise ValueError('Date timezone must be UTC')
    return None if date is None else datetime.datetime.isoformat(date).replace('+00:00', 'Z')


def deserialize_date(date: str, date_format='%Y-%m-%dT%H:%M:%S.%fZ') -> datetime.datetime:
    """
        Deserializes a date using an specific date format.
        Postcondition: Date is in UTC format.
        :param date: A previously serialized date, as a String.
        :param date_format: Date format.
        :return: A date, if the serialized date is valid (parseable); or None, if the date is None.
        :rtype: datetime.datetime
    """
    return None if date is None else datetime.datetime.fromtimestamp(
        datetime.datetime.strptime(date, date_format).timestamp()).replace(tzinfo=pytz.UTC)


def get_module_name(path: str) -> str:
    """
        Given the file path to a '.py' file, retrieves its module name (its file name without the file extension).
        :param path: File path to the '.py' file. '__file__' is the expected value for this parameter.
        :return: The name of the module.
        :rtype: str
    """
    return path.split(os_file_separator)[-1].replace('.py', '')


def get_exception_info(exception: BaseException) -> dict:
    """
        Given an Exception object, retrieves some information about it: class and message.
        :param exception: An exception which inherits from the BaseException class.
        :return: A dict, containing two values:
                    - class: The name of the exception's class.
                    - message: The message attached to the exception, if exists.
    """
    return {'class': exception.__class__.__name__,
            'message': exception.__str__()}


def next_exponential_backoff(previous_backoff: dict, max_backoff: int):
    """
        Calculates a random time, yielding between 2 and 10 times the previous wait time.
        Postcondition: The 'previous_backoff' value it's modified in-place.
        :param previous_backoff: A dict, with the following structure: {'value': <int>, 'units': TimeUnits}. Examples:
                                     - {'value': 2, 'units': s}
                                     - {'value': 3, 'units': week}
        :param max_backoff: If the operation yields a value higher than 'max_backoff', then the result is 'max_backoff'.
    """
    if previous_backoff['units'] == TimeUnits.NEVER:
        previous_backoff['value'] = max_backoff
        previous_backoff['units'] = TimeUnits.s
    else:
        value = randint(2, 10) * previous_backoff['value']
        value = value if value < max_backoff else max_backoff
        previous_backoff['value'] = value


def check_coordinates(loc_lat: float, loc_long: float, data_lat: float, data_long: float, margin=1.0) -> bool:
    """
        Compares a pair of coordinates (latitude and longitude) to ensure proximity to a maximum value ('margin').
        :param loc_lat: Latitude 1
        :param loc_long: Longitude 1
        :param data_lat: Latitude 2
        :param data_long: Longitude 2
        :param margin: Maximum error margin to be accepted. A value greater than 'margin' yields False.
        :return: True if the difference between coordinates (in absolute value) is less than margin (for both latitude
                 and longitude), and False otherwise.
        :rtype: bool
    """
    return abs(loc_lat - data_lat) <= margin and abs(loc_long - data_long) <= margin


def date_plus_timedelta_gt_now(date: datetime.datetime, frequency: dict) -> bool:
    """
        Given a date, adds a relative amount of time to it, and checks if the result date is greater than the current
        time.
        :param date: Base date object. If "date" is None, True will always be returned.
        :param frequency: A dict object ({value: int, units: TimeUnits}) to be added to "date".
        :raise ValueError: If input date is not UTC.
        :return: True if current timestamp is later than datetime plus timedelta.
        :rtype: bool
    """
    if date is None:
        return True
    elif date.tzinfo != pytz.UTC:
        raise ValueError('Date timezone must be UTC')
    if frequency['units'] == TimeUnits.s:
        result_date = date + relativedelta(seconds=frequency['value'])
    elif frequency['units'] == TimeUnits.min:
        result_date = date + relativedelta(minutes=frequency['value'])
    elif frequency['units'] == TimeUnits.h:
        result_date = date + relativedelta(hours=frequency['value'])
    elif frequency['units'] == TimeUnits.day:
        result_date = date + relativedelta(days=frequency['value'])
    elif frequency['units'] == TimeUnits.week:
        result_date = date + relativedelta(weeks=frequency['value'])
    elif frequency['units'] == TimeUnits.month:
        result_date = date + relativedelta(months=frequency['value'])
    elif frequency['units'] == TimeUnits.year:
        result_date = date + relativedelta(years=frequency['value'])
    elif frequency['units'] == TimeUnits.NEVER:
        return False
    else:
        pass # AttributeError will be raised if frequency['units'] is not a valid TimeUnits value.
    return result_date <= datetime.datetime.now(pytz.UTC)


def remove_all_under_directory(path: str):
    """
        Given a path to a directory, removes all files and directories under it. The original directory is NOT removed.
        :param path: Path to a directory. Must not be a symbolic link.
    """
    import os
    import shutil

    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


@contextmanager
def time_limit(seconds):
    """
    Uses the signal module to timeout a function. This function implements contextmanager, so it can be used as follows:
                                try:
                                    with time_limit(N):
                                        long_function()
                                except TimeoutError:
                                    pass
    :param seconds:
    :raise TimeoutError: If the execution time is greater than the time limit.
    """
    def signal_handler(signum, frame):
        raise TimeoutError('Execution has been timed out.')
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
