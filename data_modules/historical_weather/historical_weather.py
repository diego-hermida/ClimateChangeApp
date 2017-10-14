import json
import requests

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __HistoricalWeatherDataCollector()
    return __singleton


class __HistoricalWeatherDataCollector(DataCollector):
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
            Obtains data from the Wunderground API via HTTP requests. Currently only historical data is gathered.
            N * M requests are made each time this function is called (N = number of tokens, M = max queries/min per token)
            Parameters are read from configuration file (historical_weather.config)
        """
        for token in self.__config['TOKENS'] * self.__config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
            url = self.__config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}',
                self.__config['DATE']).replace('{LANG}', self.__config['LANG']).replace('{STATE|COUNTRY}',
                self.__config['COUNTRY']).replace('{LOC}', self.__config['LOC'])
            r = requests.get(url)
            self.__data.append(json.loads(r.content.decode('utf-8')))

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass
