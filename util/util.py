import datetime
import threading
import yaml

from util.relativedelta import relativedelta


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
    with open(path, 'r') as f:
        config = yaml.load(f)
    return config


def get_module_name(path):
    return path.split('/')[-1].replace('.py', '')


TimeUnits = enum('s', 'm', 'h', 'day', 'month', 'year')


class Reader:
    def __init__(self):
        self.data = []

    def __call__(self, s):
        if not s.startswith('HDR'):
            self.data.append(s)


class DataCollector(threading.Thread):
    def __init__(self, data_module):
        self.data_module = data_module
        threading.Thread.__init__(self)

    def run(self):
        data = self.data_module.get_data()
        self.data_module.save_data(data)


class TimeDelta:
    def __init__(self, value: int, units: TimeUnits):
        self.value = value
        self.units = units

    def to_dict(self):
        return {'value': self.value, 'units': self.units}


def worktime(date: datetime, frequency: TimeDelta) -> bool:
    """
    Given a date, adds a relative time measure (derived from "frequency" object)
        :param date: Base date object.
        :param frequency: TimeDelta(value: int, units: TimeUnits) object, to be added to "date".
        :return: True if current timestamp is later than datetime plus timedelta.
        :rtype: bool
    """
    min_work_date = None
    if frequency.units == TimeUnits.s:
        min_work_date = date + relativedelta(seconds=frequency.value)
    elif frequency.units == TimeUnits.m:
        min_work_date = date + relativedelta(minutes=frequency.value)
    elif frequency.units == TimeUnits.h:
        min_work_date = date + relativedelta(hours=frequency.value)
    elif frequency.units == TimeUnits.day:
        min_work_date = date + relativedelta(days=frequency.value)
    elif frequency.units == TimeUnits.month:
        min_work_date = date + relativedelta(months=frequency.value)
    elif frequency.units == TimeUnits.year:
        min_work_date = date + relativedelta(years=frequency.value)
    else:
        raise ValueError('Unsupported TimeUnit value: ' + frequency.units)
    return min_work_date <= datetime.datetime.now()
