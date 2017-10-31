import datetime
import itertools

from ftplib import FTP
from utilities.db_util import connect
from utilities.util import MassType, DataCollector, decimal_date_to_string, get_config, get_module_name, Reader, \
    MeasureUnits, read_state, serialize_date, deserialize_date, worktime, write_state

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __OceanMassDataCollector()
    return __singleton


class __OceanMassDataCollector(DataCollector):
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
        self.__state['antarctica']['last_modified'] = deserialize_date(self.__state['antarctica']['last_modified'])
        self.__state['greenland']['last_modified'] = deserialize_date(self.__state['greenland']['last_modified'])
        self.__state['ocean']['last_modified'] = deserialize_date(self.__state['ocean']['last_modified'])

    def worktime(self) -> bool:
        """
            Determines whether this module is ready or not to perform new work, according to update policy and
            last request's timestamp.
            :return: True if it's work time, False otherwise.
            :rtype: bool
        """
        return worktime(self.__state['last_request'], self.__state['antarctica']['update_frequency']) or \
               worktime(self.__state['last_request'], self.__state['greenland']['update_frequency']) or \
               worktime(self.__state['last_request'], self.__state['ocean']['update_frequency'])

    def collect_data(self):
        """
            Obtains data from the NASA servers via FTP:
                - Antarctica ice mass.
                - Greenland ice mass.
                - Ocean mass height.
            Parameters are read from configuration file (ocean_mass.config)
        """
        ftp = FTP(self.__config['URL'])
        ftp.login()
        ftp.cwd(self.__config['DATA_DIR'])  # Accessing directory
        file_names = sorted([x for x in ftp.nlst() if x.endswith(self.__config['FILE_EXT'])])
        self.__data = []
        for name in file_names:
            last_modified = ftp.sendcmd('MDTM ' + name)
            last_modified = deserialize_date(last_modified[4:] + '.' + last_modified[0:3],
                                             date_format=self.__config['FTP_DATE_FORMAT'])
            type_name = self.__get_type(name)
            if True if self.__state[type_name]['last_modified'] is None else last_modified > \
                    self.__state[type_name]['last_modified']:  # Collecting data only if file has been modified
                r = Reader()
                ftp.retrlines('RETR ' + name, r)
                self.__data.append(self.__to_json(r.data, type_name))
                self.__state[type_name]['last_modified'] = last_modified
                # Restoring original update frequency
                self.__state[type_name]['update_frequency'] = self.__config['STATE_STRUCT'][type_name]['update_frequency']
            else:
                # Setting update frequency to a shorter time interval (file is near to be modified)
                self.__state[type_name]['update_frequency'] = self.__config['MIN_UPDATE_FREQUENCY']
        self.__state['last_request'] = datetime.datetime.now()
        ftp.quit()
        self.__data = list(itertools.chain.from_iterable(self.__data)) if self.__data else None  # Flattens list of lists

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
        self.__state['antarctica']['last_modified'] = serialize_date(self.__state['antarctica']['last_modified'])
        self.__state['greenland']['last_modified'] = serialize_date(self.__state['greenland']['last_modified'])
        self.__state['ocean']['last_modified'] = serialize_date(self.__state['ocean']['last_modified'])
        write_state(self.__state, __file__)

    @staticmethod
    def __get_type(file_name):
        if MassType.antarctica in file_name:
            return MassType.antarctica
        elif MassType.greenland in file_name:
            return MassType.greenland
        elif MassType.ocean in file_name:
            return MassType.ocean
        else:
            raise ValueError('No MassType matched with file name: ' + file_name)

    def __to_json(self, data, data_type):
        json_data = []
        if data_type is MassType.ocean:
            for line in data:
                fields = line.split()
                date = decimal_date_to_string(float(fields[0]), self.__config['DATE_FORMAT'])
                measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
                measure['measures'].append({'height': fields[1], 'units': MeasureUnits.mm})
                measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.mm})
                measure['measures'].append({'height_deseasoned': fields[3], 'units': MeasureUnits.mm})
                json_data.append(measure)
        else:
            for line in data:
                fields = line.split()
                date = decimal_date_to_string(float(fields[0]), self.__config['DATE_FORMAT'])
                measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
                measure['measures'].append({'mass': fields[1], 'units': MeasureUnits.Gt})
                measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.Gt})
                json_data.append(measure)
        return json_data

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'

if __name__ == '__main__':
    obj = instance()
    obj.restore_state()
    obj.collect_data()