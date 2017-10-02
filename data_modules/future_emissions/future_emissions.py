from util.util import get_config

config = get_config(__file__)


def get_data():
    data = []
    for file in config['FILE_NAMES']:
        with open(config['DATA_DIR'] + file + config['FILE_EXT'], 'r') as f:
            for line in f:
                fields = line.split()
                d = {'year': fields[0], 'scenario': file, 'measures': []}
                for (index, value) in enumerate(fields[1:]):
                    measure = {'measure': config['MEASURES'][index], 'value': value, 'units': config['UNITS'][index]}
                    d['measures'].append(measure)
                data.append(d)
    return data


if __name__ == '__main__':
    data = get_data()
