import json
import requests

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CurrentConditionsDataCollector()
    return __singleton


class __CurrentConditionsDataCollector(DataCollector):
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
            Obtains weather conditions data from the Open Weather Map via HTTP requests.
            M requests are made each time this function is called (M = max queries/min)
            Parameters are read from configuration file (weather_forecast.config)
        """
        requests_count = 0
        max_requests = self.__config['MAX_REQUESTS_PER_MINUTE']
        while requests_count < max_requests:
            url = self.__config['BASE_URL'].replace('{TOKEN}', self.__config['TOKEN']).replace('{LOC}',
                self.__config['LOC']).replace('{COUNTRY}', self.__config['COUNTRY'])
            r = requests.get(url)
            self.__data.append(json.loads(r.content.decode('utf-8')))
            requests_count += 1

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass
