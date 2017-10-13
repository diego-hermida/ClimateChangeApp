import datetime
import threading
import yaml


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
