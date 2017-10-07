import json

from ftplib import FTP
from util.db_util import connect
from util.util import decimal_date_to_string, enum, get_config, get_module_name, Reader

config = get_config(__file__)
module_name = get_module_name(__file__)

MassType = enum('antarctica', 'greenland', 'ocean')
MeasureUnits = enum('mm', 'Gt')


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
    ftp = FTP(config['URL'])
    ftp.login()
    ftp.cwd(config['DATA_DIR'])  # Accessing directory

    file_names = sorted([x for x in ftp.nlst() if x.endswith(config['FILE_EXT'])])
    data = []

    for name in file_names:
        r = Reader()
        ftp.retrlines('RETR ' + name, r)
        data.append(to_JSON(r.data, get_type(name)))
    ftp.quit()
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


def get_type(file_name):
    if MassType.antarctica in file_name:
        return MassType.antarctica
    elif MassType.greenland in file_name:
        return MassType.greenland
    elif MassType.ocean in file_name:
        return MassType.ocean


def to_JSON(data, data_type):
    json_data = []
    if data_type is MassType.ocean:
        for line in data:
            fields = line.split()
            date = decimal_date_to_string(float(fields[0]), config['DATE_FORMAT'])
            measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
            measure['measures'].append({'height': fields[1], 'units': MeasureUnits.mm})
            measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.mm})
            measure['measures'].append({'height_deseasoned': fields[3], 'units': MeasureUnits.mm})
            json_data.append(measure)
    else:
        for line in data:
            fields = line.split()
            date = decimal_date_to_string(float(fields[0]), config['DATE_FORMAT'])
            measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
            measure['measures'].append({'mass': fields[1], 'units': MeasureUnits.Gt})
            measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.Gt})
            json_data.append(measure)
    return json_data


if __name__ == '__main__':
    data = get_data()
    save_data(data)
