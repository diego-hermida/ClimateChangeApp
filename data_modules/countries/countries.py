import json
import requests

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CountriesDataCollector()
    return __singleton


class __CountriesDataCollector(DataCollector):
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
            Obtains data from the World Bank API via HTTP requests. A single request is performed.
            Base URL is read from configuration file (countries.config)
        """
        url = self.__config['BASE_URL'].replace('{LANG}', self.__config['LANG'])
        r = requests.get(url)
        self.__data = json.loads(r.content.decode('utf-8'))[1]  # Avoids saving indicator meta-info
        for value in self.__data:  # Creates '_id' attribute and removes non-utilities fields
            value['_id'] = value['id']
            del value['id']
            del value['adminregion']
            del value['lendingType']

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass
