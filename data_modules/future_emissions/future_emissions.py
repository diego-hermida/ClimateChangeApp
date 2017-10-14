# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the RPC Database. Documents have previously been downloaded and properly formatted.
        Data location is read from configuration file (future_emissions.config)
        :return: A flat list of key-value objects, containing parsed information from all files.
        :rtype: list
    """
    return __get_data()


def save_data(data):
    """
       Saves data into a persistent storage system (Currently, a MongoDB instance).
       Data is saved in a collection with the same name as the module.
       :param data: A list of values to persist, which might be empty.
    """
    __save_data(data)


# ---------------------------------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------------------------------

from utilities.db_util import connect
from utilities.util import get_config, get_module_name

__config = get_config(__file__)
__module_name = get_module_name(__file__)


def __get_data():
    data = []
    for file in __config['FILE_NAMES']:
        with open(__config['DATA_DIR'] + file + __config['FILE_EXT'], 'r') as f:
            for line in f:
                fields = line.split()
                d = {'_id': fields[0] + '_' + file, 'year': fields[0], 'scenario': file, 'measures': []}
                for (index, value) in enumerate(fields[1:]):
                    measure = {'measure': __config['MEASURES'][index], 'value': value,
                               'units': __config['UNITS'][index]}
                    d['measures'].append(measure)
                data.append(d)
    return data


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)
