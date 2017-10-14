# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the NASA servers via FTP:
            - Antarctica ice mass.
            - Greenland ice mass.
            - Ocean mass height.
        Parameters are read from configuration file (ocean_mass.config)
        :return: A flat list of key-value objects, containing information from all measures.
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

import itertools

from ftplib import FTP
from utilities.db_util import connect
from utilities.util import decimal_date_to_string, enum, get_config, get_module_name, Reader

__config = get_config(__file__)
__module_name = get_module_name(__file__)

__MassType = enum('antarctica', 'greenland', 'ocean')
__MeasureUnits = enum('mm', 'Gt')


def __get_data():
    ftp = FTP(__config['URL'])
    ftp.login()
    ftp.cwd(__config['DATA_DIR'])  # Accessing directory
    file_names = sorted([x for x in ftp.nlst() if x.endswith(__config['FILE_EXT'])])
    data = []
    for name in file_names:
        r = Reader()
        ftp.retrlines('RETR ' + name, r)
        data.append(__to_JSON(r.data, __get_type(name)))
    ftp.quit()
    return list(itertools.chain.from_iterable(data))


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)


def __get_type(file_name):
    if __MassType.antarctica in file_name:
        return __MassType.antarctica
    elif __MassType.greenland in file_name:
        return __MassType.greenland
    elif __MassType.ocean in file_name:
        return __MassType.ocean


def __to_JSON(data, data_type):
    json_data = []
    if data_type is __MassType.ocean:
        for line in data:
            fields = line.split()
            date = decimal_date_to_string(float(fields[0]), __config['DATE_FORMAT'])
            measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
            measure['measures'].append({'height': fields[1], 'units': __MeasureUnits.mm})
            measure['measures'].append({'uncertainty': fields[2], 'units': __MeasureUnits.mm})
            measure['measures'].append({'height_deseasoned': fields[3], 'units': __MeasureUnits.mm})
            json_data.append(measure)
    else:
        for line in data:
            fields = line.split()
            date = decimal_date_to_string(float(fields[0]), __config['DATE_FORMAT'])
            measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
            measure['measures'].append({'mass': fields[1], 'units': __MeasureUnits.Gt})
            measure['measures'].append({'uncertainty': fields[2], 'units': __MeasureUnits.Gt})
            json_data.append(measure)
    return json_data
