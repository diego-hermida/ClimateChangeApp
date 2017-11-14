import datetime
import json
from random import randint

import yaml
import pytz

from utilities.relativedelta import relativedelta


def enum(*args) -> type:
    """
        Emulates Java enumerated type.
        :param args: Enumerated values (separated by commas).
    """
    enums = dict(zip(args, args))
    return type('Enum', (), enums)


TimeUnits = enum('s', 'min', 'h', 'day', 'week', 'month', 'year', 'NEVER')
MeasureUnits = enum('mm', 'm', 'km', 'Gt')
MassType = enum('antarctica', 'greenland', 'ocean')


def date_to_millis_since_epoch(date: datetime.datetime) -> int:
    """
        Given a date, converts it to milliseconds since epoch (UNIX time, 01/01/1970 00:00:00.0 UTC).
        :param date: A datetime.datetime object, whose timezone will be converted to UTC.
        :return: An int, representing milliseconds since epoch.
        :rtype: int
    """
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


def read_state(path: str, repair_struct: dict) -> dict:
    """
        Given the file path to a '.py' file (DataCollector module), retrieves the data inside the  '.state'
        file (under the same directory as the module).
        Precondition: The '.state' file is a serialized JSON document.
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
        :param repair_struct: If the document is unparseable, this structure allows the '.state' file to reach a
                              consistent state.
        :return: A dict, containing all data inside the '.state' file, or 'repair_struct' if the '.state' file is
                 unparseable.
    """
    path = path.replace('.py', '.state')
    with open(path, 'r') as f:
        try:
            state = json.load(f)
        except json.decoder.JSONDecodeError:  # State is invalid, creating empty state according to REPAIR_STRUCT
            f.close()
            with open(path, 'w') as f2:
                json.dump(repair_struct, f2)
            return repair_struct
    return state


def write_state(state: dict, path: str):
    """
        Given the file path to a '.py' file (DataCollector module), serializes the 'state' variable into the '.state'
        file (under the same directory as the module).
        Precondition: The 'state' variable is valid JSON document.
        :param state: A valid JSON document (as a dict object).
        :param path: File path to the DataCollector module. '__file__' is the expected value for this parameter.
    """
    path = path.replace('.py', '.state')
    with open(path, 'w') as f:
        json.dump(state, f)


def serialize_date(date: datetime) -> str:
    """
        Serializes a date using the ISO format.
        :return: The serialized date, if date is valid; or None, if the date is None.
        :rtype: str
    """
    return None if date is None else datetime.datetime.isoformat(date)


def deserialize_date(date: str, date_format='%Y-%m-%dT%H:%M:%S.%f') -> datetime.datetime:
    """
        Deserializes a date using an specific date format.
        :param date: A previously serialized date, as a String.
        :param date_format: Date format.
        :return: A date, if the serialized date is valid (parseable); or None, if the date is None.
        :rtype: datetime.datetime
    """
    return None if date is None else datetime.datetime.fromtimestamp(
        datetime.datetime.strptime(date, date_format).timestamp())


def get_module_name(path: str) -> str:
    """
        Given the file path to a '.py' file, retrieves its module name (its file name without the file extension).
        :param path: File path to the '.py' file. '__file__' is the expected value for this parameter.
        :return: The name of the module.
        :rtype: str
    """
    return path.split('/')[-1].replace('.py', '')


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
    value = randint(1, 10) * previous_backoff['value']
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


def date_plus_timedelta_gt_now(date: datetime, frequency: dict) -> bool:
    """
        Given a date, adds a relative amount of time to it, and checks if the result date is greater than the current
        time.
        :param date: Base date object. If "date" is None, True will always be returned.
        :param frequency: A dict object ({value: int, units: TimeUnits}) to be added to "date".
        :return: True if current timestamp is later than datetime plus timedelta.
        :rtype: bool
    """
    if date is None:
        return True
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
        raise ValueError('Unsupported TimeUnit value: ' + frequency['units'])
    return result_date <= datetime.datetime.now()
