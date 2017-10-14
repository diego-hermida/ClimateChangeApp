from ftplib import FTP

from utilities.db_util import connect
from utilities.util import DataCollector, decimal_date_to_string, get_config, get_module_name, Reader, MeasureUnits

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __SeaLevelDataCollector()
    return __singleton


class __SeaLevelDataCollector(DataCollector):
    def __init__(self):
        super().__init__()
        self.__data = []
        self.__state = None
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def restore_state(self):
        pass

    def worktime(self) -> bool:
        pass

    def get_data(self):
        """
            Obtains data from the NASA servers via FTP.
            Parameters are read from configuration file (sea_level_rise.config)
        """
        ftp = FTP(self.__config['URL'])
        ftp.login()
        ftp.cwd(self.__config['DATA_DIR'])  # Accessing directory

        # File name changes every month, but it always starts with GMSL
        file_names = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith(self.__config['FILE_EXT'])]
        r = Reader()
        ftp.retrlines('RETR ' + file_names[0], r)
        ftp.quit()
        self.__data = self.__to_json(r.data)

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass

    def __to_json(self, data):
        json_data = []
        for line in data:
            fields = line.split()
            date = decimal_date_to_string(float(fields[2]), self.__config['DATE_FORMAT'])
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
