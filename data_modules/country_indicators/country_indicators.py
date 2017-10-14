import itertools
import json
import requests

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CountryIndicatorsDataCollector()
    return __singleton


class __CountryIndicatorsDataCollector(DataCollector):
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
            Obtains data from the World Bank API via HTTP requests.
            N * M requests are made each time this function is called (M = number of indicators, N = number of countries)
            Indicators and countries are both read from configuration file (country_indicators.config)
        """
        for indicator in self.__config['INDICATORS']:
            for country in self.__config['COUNTRIES']:
                url = self.__config['BASE_URL'].replace('{LANG}', self.__config['LANG']).replace('{COUNTRY}',
                    country).replace('{INDICATOR}', indicator).replace('{BEGIN_DATE}',
                    str(self.__config['BEGIN_DATE'])).replace('{END_DATE}', str(self.__config['END_DATE']))
                r = requests.get(url)
                self.__data.append(json.loads(r.content.decode('utf-8'))[1])  # Avoids saving indicator meta-info
        self.__data = list(itertools.chain.from_iterable(self.__data))  # Flattens the list of lists
        for value in self.__data:  # Creates '_id' attribute and removes non-utilities fields
            value['_id'] = value['indicator']['id'] + '_' + value['country']['id'] + '_' + value['date']
            del value['decimal']

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass
