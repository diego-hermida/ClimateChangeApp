# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the NASA servers via FTP.
        Parameters are read from configuration file (sea_level_rise.config)
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

from ftplib import FTP
from util.db_util import connect
from util.util import decimal_date_to_string, enum, get_config, get_module_name, Reader

__config = get_config(__file__)
__module_name = get_module_name(__file__)

__MeasureUnits = enum('mm')


def __get_data():
    ftp = FTP(__config['URL'])
    ftp.login()
    ftp.cwd(__config['DATA_DIR'])  # Accessing directory

    # File name changes every month, but it always starts with GMSL
    file_names = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith(__config['FILE_EXT'])]
    r = Reader()
    ftp.retrlines('RETR ' + file_names[0], r)
    ftp.quit()
    return __to_JSON(r.data)


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)


def __to_JSON(data):
    json_data = []
    for line in data:
        fields = line.split()
        date = decimal_date_to_string(float(fields[2]), __config['DATE_FORMAT'])
        altimeter = 'dual_frequency' if fields[0] == 0 else 'single_frequency'
        measure = {'_id': date, 'date': date, 'altimeter': altimeter, 'observations': fields[3],
                   'weighted_observations': fields[4], 'measures': []}
        measure['measures'].append({'variation': fields[5], 'units': __MeasureUnits.mm})
        measure['measures'].append({'deviation': fields[6], 'units': __MeasureUnits.mm})
        measure['measures'].append({'smoothed_variation': fields[7], 'units': __MeasureUnits.mm})
        measure['measures'].append({'variation_GIA': fields[8], 'units': __MeasureUnits.mm})
        measure['measures'].append({'deviation_GIA': fields[9], 'units': __MeasureUnits.mm})
        measure['measures'].append({'smoothed_variation_GIA': fields[10], 'units': __MeasureUnits.mm})
        measure['measures'].append({'smoothed_variation_GIA_annual_&_semi_annual_removed': fields[11],
                                    'units': __MeasureUnits.mm})
        json_data.append(measure)
    return json_data
