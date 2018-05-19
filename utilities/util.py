import datetime
import json
import signal
from contextlib import contextmanager
from os import makedirs, sep as os_file_separator
from os.path import exists
from random import randint

import errno
import pytz
import yaml


def enum(*args) -> type:
    """
        Emulates Java enumerated type.
        :param args: Enumerated values (separated by commas).
    """
    return type('Enum', (), dict(zip(args, args)))


TimeUnits = enum('s', 'min', 'h', 'day', 'NEVER')
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
    return int((date.replace(tzinfo=pytz.UTC) - datetime.datetime.utcfromtimestamp(0).replace(
        tzinfo=pytz.UTC)).total_seconds() * 1000.0)


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


def current_timestamp(utc=True) -> datetime.datetime:
    """
        Retrieves current timestamp as a datetime.datetime object.
        :param utc: If True, uses UTC as the timezone. Otherwise, uses the default one (is set to None)
        :return: datetime.datetime.now()
    """
    if utc:
        return datetime.datetime.now(tz=pytz.UTC)
    else:
        return datetime.datetime.now()


def current_date_in_millis() -> int:
    """
        Retrieves the current UTC date in milliseconds.
    """
    return date_to_millis_since_epoch(datetime.datetime.now(tz=pytz.UTC))


def recursive_makedir(path: str, is_file=False):
    """
        Recursively creates all directories under a base directory. If a directory does already exist, silently performs
        the operation (FileExistsError is handled).
        :param path: A valid directory path. Example: /var/log/DataGatheringSubsystem/data_modules, where 'data_modules'
                     is a directory (can be non-existent).
        :param is_file: If True, indicates that the path is a filepath, and its directory filepath should be calculated.
        :raise PermissionError: If an attempt to create a directory without the necessary privileges is made.
    """
    try:
        target = path if not is_file else os_file_separator.join(path.split(os_file_separator)[:-1])
        makedirs(target)
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
    return config if config else {}


def map_data_collector_path_to_state_file_path(path: str, root_dir: str) -> str:
    """
        Given the path to a file, returns the path to a '.state' file (with the same name as the original one) under the
        STATE_FILES_ROOT_FOLDER (from config.config.CONFIG).
        :param path: Path to the target file.
        :param root_dir: Depending on this parameter, the root directory for '.state' files will be different.
        :return: Path to the '.state' file, under STATE_FILES_ROOT_FOLDER.
        :rtype: str
    """
    return root_dir + get_module_name(path) + '.state'


def create_state_file(path: str):
    """
        Given the path to a '.state' file, creates it. If directory hierarchy does not exist it is also created.
    """
    recursive_makedir(path[:path.rfind(os_file_separator)])
    open(path, 'w').close()


def remove_state_file(path: str, root_dir: str):
    """
        Given the path to a data module, removes its attached '.state' file.
        :param path: Path to the .py file.
        :param root_dir: Depending on this parameter, the root directory for '.state' files will be different.
    """
    from os import remove
    remove(map_data_collector_path_to_state_file_path(path, root_dir=root_dir))


def read_state(path: str, repair_struct: dict, root_dir: str) -> dict:
    """
        Given the file path to a '.py' file (DataCollector module), retrieves the data inside the  '.state'
        file (located under the STATE_FILES_ROOT_FOLDER or a subdirectory). If
        Precondition: If file exists, file content is a serialized JSON document.
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :param repair_struct: If the document is unparseable, this structure allows the '.state' file to reach a
                              consistent state. This structure is dumped into the '.state' file if it's unparseable.
        :param root_dir: Depending on this parameter, the root directory for '.state' files will be different.
        :return: A dict, containing all data inside the '.state' file, or 'repair_struct' if the '.state' file is
                 unparseable.
    """
    path = map_data_collector_path_to_state_file_path(path, root_dir=root_dir)
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


def write_state(state: dict, path: str, root_dir: str) -> str:
    """
        Given the file path to a '.py' file (DataCollector module), serializes the 'state' variable into the '.state'
        file (under the same directory as the module).
        Precondition: The 'state' variable is valid JSON document.
        :param state: A valid JSON document (as a dict object).
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :param root_dir: Depending on this parameter, the root directory for '.state' files will be different.
        :return: The file path to the written '.state' file.
    """
    state_path = map_data_collector_path_to_state_file_path(path, root_dir=root_dir)
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
    return {'class': exception.__class__.__name__, 'message': exception.__str__()}


def next_exponential_backoff(previous_backoff: dict, max_backoff: int) -> (int, str):
    """
        Calculates a random time, yielding between 2 and 10 times the previous wait time.
        :param previous_backoff: A dict, with the following structure: {'value': <int>, 'units': TimeUnits}. Examples:
                                     - {'value': 2, 'units': s}
                                     - {'value': 3, 'units': week}
        :param max_backoff: If the operation yields a value higher than 'max_backoff', then the result is 'max_backoff'.
        :return: A tuple with the new value and time units
    """
    if previous_backoff['units'] == TimeUnits.NEVER:
        return max_backoff, TimeUnits.s
    else:
        value = randint(2, 10) * previous_backoff['value']
        value = value if value < max_backoff else max_backoff
        return value, previous_backoff['units']


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
    else:
        date_millis = date_to_millis_since_epoch(date)
        if frequency['units'] == TimeUnits.s:
            result_date = date_millis + frequency['value'] * 1000
        elif frequency['units'] == TimeUnits.min:
            result_date = date_millis + frequency['value'] * 60000
        elif frequency['units'] == TimeUnits.h:
            result_date = date_millis + frequency['value'] * 3600000
        elif frequency['units'] == TimeUnits.day:
            result_date = date_millis + frequency['value'] * 86400000
        elif frequency['units'] == TimeUnits.NEVER:
            return False
        else:
            # Raising exception avoids referencing a variable before it's assigned, and FIXES [BUG-031].
            raise AttributeError('TimeUnits "%s" is unrecognized.' % frequency['units'])
        return result_date <= current_date_in_millis()


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


def nonempty_str(value: str, nullable=True, min_length=None, max_length=None) -> str:
    """
        Validates a "str" object (must be non-empty). If the value is already a "str" object, this is a no-op.
        :param value: String to be parsed.
        :param nullable: Allows returning None. Defaults to True.
        :param min_length: Minimum allowed length.
        :param max_length: Maximum allowed length.
        :return: The parsed value; or None, if "nullable" is True and the value cannot be parsed.
        :raises ValueError: If nullable=False, and value cannot be parsed.
    """
    try:
        if nullable and value is None:
            return None
        elif value is None:
            raise ValueError('Input must be a "str" object, not None.')
        value = str(value)
        if value == '':
            raise ValueError('Input cannot be an empty "str" object.')
        elif min_length is not None and max_length is not None and not min_length <= len(value) <= max_length:
            raise AttributeError('Input must be between %d-%d characters long' % (min_length, max_length))
        else:
            return value
    except ValueError:
        if nullable:
            return None
        else:
            raise
    except AttributeError as e:
        raise ValueError('Validation failed.') from e


def parse_float(value: str, nullable=True) -> float:
    """
        Parses a "str" object into a "float" object. If the value is already a "float" object, this is a no-op.
        :param value: String to be parsed.
        :param nullable: Allows returning None. Defaults to True.
        :return: The parsed value; or None, if "nullable" is True and the value cannot be parsed.
        :raises ValueError: If nullable=False, and value cannot be parsed.
    """
    if isinstance(value, float):
        return value
    elif value is None and nullable:
        return None
    elif value is None:
        raise ValueError('Input must be a "str" object, not None.')
    try:
        return float(value)
    except ValueError:
        if nullable:
            return None
        else:
            raise


def parse_int(value: str, nullable=True) -> int:
    """
        Parses a "str" object into a "int" object. If the value is already an "int" object, this is a no-op.
        :param value: String to be parsed.
        :param nullable: Allows returning None. Defaults to True.
        :return: The parsed value; or None, if "nullable" is True and the value cannot be parsed.
        :raises ValueError: If nullable=False, and value cannot be parsed.
    """
    if isinstance(value, int):
        return value
    elif value is None and nullable:
        return None
    elif value is None:
        raise ValueError('Input must be a "str" object, not None.')
    try:
        return int(value)
    except ValueError:
        if nullable:
            return None
        else:
            raise


def parse_bool(value: str, nullable=True) -> bool:
    """
        Parses a "str" object into a "bool" object. If the value is already a "bool" object, this is a no-op. Examples:
            - "0" will be evaluated to False.
            - "2" will be evaluated to True.
            - "True" will be evaluated to True.
            - "FalSE" will be evaluated to False.
            - "foo" will return None (or raise ValueError, if nullable=False).
        :param value: String to be parsed.
        :param nullable: Allows returning None. Defaults to True.
        :return: The parsed value; or None, if "nullable" is True and the value cannot be parsed.
        :raises ValueError: If nullable=False, and value cannot be parsed.
    """
    if isinstance(value, bool):
        return value
    elif value is None and nullable:
        return None
    elif value is None:
        raise ValueError('Input must be a "str" object, not None.')
    try:
        return int(value) > 0
    except ValueError:
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        else:
            if nullable:
                return None
            else:
                raise


def parse_date_utc(value: str):
    """
        Parses an "int" or "str" serialized integer into a "datetime.datetime" object.
        Date timezone will be set to 'pytz.UTC'.
        :param value: String to be parsed.
        :return: The parsed value.
        :raises ValueError: If the value cannot be parsed.
    """
    try:
        return datetime.datetime.fromtimestamp(parse_int(value, nullable=False) / 1000, tz=pytz.UTC)
    except Exception as e:
        raise ValueError from e


def compute_wind_direction(wind_degrees: float) -> str:
    """
        Given wind degrees, calculates its wind direction.
        Source: http://snowfence.umn.edu/Components/winddirectionanddegreeswithouttable3.htm
        :param wind_degrees: Must be a number (int or float), bounded between 0 and 360.
        :return: None, if the input is None,
    """
    return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][
        int((wind_degrees / 22.5) + .5) % 16] if wind_degrees is not None else None
