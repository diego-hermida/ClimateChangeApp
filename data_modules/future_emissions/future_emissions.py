from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __FutureEmissionsDataCollector()
    return __singleton


class __FutureEmissionsDataCollector(DataCollector):
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
            Obtains data from the RPC Database. Documents have previously been downloaded and properly formatted.
            Data location is read from configuration file (future_emissions.config)
        """
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

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass
