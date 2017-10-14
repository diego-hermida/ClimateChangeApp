import json
import requests

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __AirPollutionDataCollector()
    return __singleton


class __AirPollutionDataCollector(DataCollector):
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
            Obtains data from the WAQI API via HTTP requests.
            L requests are made each time this function is called (L = number of locations)
            Parameters are read from configuration file (air_pollution.config)
        """
        for loc in self.__config['LOCATIONS']:
            url = self.__config['BASE_URL'].replace('{LOC}', loc) + self.__config['TOKEN']
            r = requests.get(url)
            self.__data.append(json.loads(r.content.decode('utf-8')))
            # TODO: Check errors. Examples:
            # TODO:  - [b'{"status":"error","data":"Invalid key"}', b'{"status":"error","data":"Invalid key"}']
            # TODO:  - [b'{"status":"error","message":"404"}', b'{"status":"error","message":"404"}']

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass
