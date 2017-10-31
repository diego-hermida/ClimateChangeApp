import datetime

from ftplib import FTP
from utilities.db_util import connect
from utilities.util import DataCollector, decimal_date_to_string, get_config, get_module_name, Reader, MeasureUnits, \
    read_state, serialize_date, deserialize_date, worktime, write_state

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __SeaLevelDataCollector()
    return __singleton


class __SeaLevelDataCollector(DataCollector):
    def __init__(self):
        super().__init__()
        self.__data = None
        self.__state = None
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def restore_state(self):
        """
           Restores previous saved state (.state) if valid. Otherwise, creates a valid structure
           for .state file from the STATE_STRUCT key in .config file.
        """
        self.__state = read_state(__file__, repair_struct=self.__config['STATE_STRUCT'])
        self.__state['last_request'] = deserialize_date(self.__state['last_request'])
        self.__state['last_modified'] = deserialize_date(self.__state['last_modified'])

    def worktime(self) -> bool:
        """
            Determines whether this module is ready or not to perform new work, according to update policy and
            last request's timestamp.
            :return: True if it's work time, False otherwise.
            :rtype: bool
        """
        return worktime(self.__state['last_request'], self.__state['update_frequency'])

    def collect_data(self):
        """
            Obtains data from the NASA servers via FTP.
            Parameters are read from configuration file (sea_level_rise.config)
        """
        ftp = FTP(self.__config['URL'], timeout=self.__config['FTP_TIMEOUT'])
        ftp.login()
        ftp.cwd(self.__config['DATA_DIR'])  # Accessing directory

        # File name changes every month, but it always starts with GMSL
        file_names = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith(self.__config['FILE_EXT'])]

        # Getting file's date modified
        last_modified = ftp.sendcmd('MDTM ' + file_names[0])
        last_modified = deserialize_date(last_modified[4:] + '.' + last_modified[0:3],
                                         date_format=self.__config['FTP_DATE_FORMAT'])

        if True if self.__state['last_modified'] is None else last_modified > self.__state[
            'last_modified']:  # Collecting data only if file has been modified
            r = Reader()
            ftp.retrlines('RETR ' + file_names[0], r)
            ftp.quit()
            self.__data = self.__to_json(r.data)
            self.__state['last_modified'] = last_modified
            # Restoring original update frequency
            self.__state['update_frequency'] = self.__config['STATE_STRUCT']['update_frequency']
        else:
            # Setting update frequency to a shorter time interval (file is near to be modified)
            self.__state['update_frequency'] = self.__config['MIN_UPDATE_FREQUENCY']
        self.__state['last_request'] = datetime.datetime.now()
        self.__data = self.__data if self.__data else None

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        if self.__data is None:
            pass
        else:
            connection = connect(self.__module_name)
            connection.insert_many(self.__data)

    def save_state(self):
        """
            Serializes state to .state file in such a way that can be deserialized later.
        """
        self.__state['last_request'] = serialize_date(self.__state['last_request'])
        self.__state['last_modified'] = serialize_date(self.__state['last_modified'])
        write_state(self.__state, __file__)

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

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'
