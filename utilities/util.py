import datetime
import json
import yaml

from abc import ABC, abstractmethod
from utilities.relativedelta import relativedelta


def decimal_date_to_string(decimal_date, date_format):
    decimal_date = float(decimal_date)
    year = int(decimal_date)
    rem = decimal_date - year
    base = datetime.datetime(year, 1, 1)
    result = base + datetime.timedelta(seconds=(base.replace(year=base.year + 1) - base).total_seconds() * rem)
    return result.strftime(date_format)


def enum(*args):
    enums = dict(zip(args, args))
    return type('Enum', (), enums)


def get_config(path):
    path = path.replace('.py', '.config')
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.load(f)
    return config


def read_state(path, repair_struct={}):
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


def write_state(state, path):
    path = path.replace('.py', '.state')
    with open(path, 'w') as f:
        json.dump(state, f)


def serialize_date(date: datetime):
    return None if date is None else datetime.datetime.isoformat(date)


def deserialize_date(date: str, date_format='%Y-%m-%dT%H:%M:%S.%f'):
    return None if date is None else datetime.datetime.fromtimestamp(
        datetime.datetime.strptime(date, date_format).timestamp())


def get_module_name(path):
    return path.split('/')[-1].replace('.py', '')


TimeUnits = enum('s', 'm', 'h', 'day', 'week', 'month', 'year', 'NEVER')
MeasureUnits = enum('mm', 'm', 'km', 'Gt')
MassType = enum('antarctica', 'greenland', 'ocean')


def worktime(date: datetime, frequency: dict) -> bool:
    """
    Given a date, adds a relative time measure (derived from "frequency" object)
        :param date: Base date object. If "date" is None, True will always be returned.
        :param frequency: A dict object ({value: int, units: TimeUnits}) to be added to "date".
        :return: True if current timestamp is later than datetime plus timedelta.
        :rtype: bool
    """
    if date is None:
        return True
    if frequency['units'] == TimeUnits.s:
        min_work_date = date + relativedelta(seconds=frequency['value'])
    elif frequency['units'] == TimeUnits.m:
        min_work_date = date + relativedelta(minutes=frequency['value'])
    elif frequency['units'] == TimeUnits.h:
        min_work_date = date + relativedelta(hours=frequency['value'])
    elif frequency['units'] == TimeUnits.day:
        min_work_date = date + relativedelta(days=frequency['value'])
    elif frequency['units'] == TimeUnits.week:
        min_work_date = date + relativedelta(weeks=frequency['value'])
    elif frequency['units'] == TimeUnits.month:
        min_work_date = date + relativedelta(months=frequency['value'])
    elif frequency['units'] == TimeUnits.year:
        min_work_date = date + relativedelta(years=frequency['value'])
    elif frequency['units'] == TimeUnits.NEVER:
        return False
    else:
        raise ValueError('Unsupported TimeUnit value: ' + frequency['units'])
    return min_work_date <= datetime.datetime.now()


class Reader:
    def __init__(self):
        self.data = []

    def __call__(self, s):
        if not s.startswith('HDR'):
            self.data.append(s)


class DataCollector(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def restore_state(self):
        pass

    @abstractmethod
    def worktime(self) -> bool:
        pass

    @abstractmethod
    def collect_data(self):
        pass

    @abstractmethod
    def save_data(self):
        pass

    @abstractmethod
    def save_state(self):
        pass
