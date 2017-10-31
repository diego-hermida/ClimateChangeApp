import datetime

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name, read_state, write_state, worktime, \
    serialize_date, deserialize_date

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __FutureEmissionsDataCollector()
    return __singleton


class __FutureEmissionsDataCollector(DataCollector):
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
        self.__state['last_request'] = deserialize_date(self.__state['last_request'])  # Creates datetime object

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
            Obtains data from the RPC Database. Documents have previously been downloaded and properly formatted.
            Data location is read from configuration file (future_emissions.config)
        """
        self.__data = []
        for file in self.__config['FILE_NAMES']:
            with open(self.__config['DATA_DIR'] + file + self.__config['FILE_EXT'], 'r') as f:
                for line in f:
                    fields = line.split()
                    d = {'_id': fields[0] + '_' + file, 'year': fields[0], 'scenario': file, 'measures': []}
                    for (index, value) in enumerate(fields[1:]):
                        measure = {'measure': self.__config['MEASURES'][index], 'value': value,
                                   'units': self.__config['UNITS'][index]}
                        d['measures'].append(measure)
                    self.__data.append(d)
        self.__state['last_request'] = datetime.datetime.now()

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
        write_state(self.__state, __file__)

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']\n'
