import datetime

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
    path = path.split('/')[-1].replace('.py', '.config')
    with open(path, 'r') as f:
        config = yaml.load(f)
    return config


class Reader:
    def __init__(self):
        self.data = []

    def __call__(self, s):
        if not s.startswith('HDR'):
            self.data.append(s)


if __name__ == '__main__':
    pass
    # uri = 'mongodb://climatechange_data_gathering_subsystem:TFG_Diego_Hermida_Carrera@localhost/'
    # client = pymongo.MongoClient('127.0.0.1', 27017)
    # client.admin.authenticate('climatechange_data_gathering_subsystem', 'TFG_Diego_Hermida_Carrera',
    #                           mechanism='SCRAM-SHA-1')
