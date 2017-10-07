from ftplib import FTP
from util.db_util import connect
from util.util import decimal_date_to_string, enum, get_config, get_module_name, Reader

config = get_config(__file__)
module_name = get_module_name(__file__)

MeasureUnits = enum('mm')


def get_data():
    """
        Obtains data from the NASA servers via FTP.

        Parameters are read from configuration file (sea_level_rise.config)

        :return: A flat list of key-value objects, containing information from all measures.
        :rtype: list
    """
    ftp = FTP(config['URL'])
    ftp.login()
    ftp.cwd(config['DATA_DIR'])  # Accessing directory

    # File name changes every month, but it always starts with GMSL
    file_names = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith(config['FILE_EXT'])]
    r = Reader()

    ftp.retrlines('RETR ' + file_names[0], r)
    ftp.quit()
    return to_JSON(r.data)


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


def to_JSON(data):
    json_data = []
    for line in data:
        fields = line.split()
        date = decimal_date_to_string(float(fields[2]), config['DATE_FORMAT'])
        altimeter = 'dual_frequency' if fields[0] == 0 else 'single_frequency'
        measure = {'_id': date, 'date': date, 'altimeter': altimeter, 'observations': fields[3],
                   'weighted_observations': fields[4], 'measures': []}
        measure['measures'].append({'variation': fields[5], 'units': MeasureUnits.mm})
        measure['measures'].append({'deviation': fields[6], 'units': MeasureUnits.mm})
        measure['measures'].append({'smoothed_variation': fields[7], 'units': MeasureUnits.mm})
        measure['measures'].append({'variation_GIA': fields[8], 'units': MeasureUnits.mm})
        measure['measures'].append({'deviation_GIA': fields[9], 'units': MeasureUnits.mm})
        measure['measures'].append({'smoothed_variation_GIA': fields[10], 'units': MeasureUnits.mm})
        measure['measures'].append({'smoothed_variation_GIA_annual_&_semi_annual_removed': fields[11],
                                    'units': MeasureUnits.mm})
        json_data.append(measure)
    return json_data


if __name__ == '__main__':
    data = get_data()
    save_data(data)
