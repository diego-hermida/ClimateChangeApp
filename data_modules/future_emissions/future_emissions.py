from util.db_util import connect
from util.util import get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)


def get_data():
    """
        Obtains data from the RPC Database. Documents have previously been downloaded and properly formatted.

        Data location is read from configuration file (future_emissions.config)

        :return: A flat list of key-value objects, containing parsed information from all files.
        :rtype: list
    """
    data = []
    for file in config['FILE_NAMES']:
        with open(config['DATA_DIR'] + file + config['FILE_EXT'], 'r') as f:
            for line in f:
                fields = line.split()
                d = {'_id': fields[0] + '_' + file, 'year': fields[0], 'scenario': file, 'measures': []}
                for (index, value) in enumerate(fields[1:]):
                    measure = {'measure': config['MEASURES'][index], 'value': value, 'units': config['UNITS'][index]}
                    d['measures'].append(measure)
                data.append(d)
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    save_data(data)
