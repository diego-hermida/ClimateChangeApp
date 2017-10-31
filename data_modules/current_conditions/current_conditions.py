import datetime
import json
import requests

from utilities.db_util import connect, find
from utilities.util import DataCollector, get_config, get_module_name, worktime, read_state, write_state, \
    serialize_date, deserialize_date

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CurrentConditionsDataCollector()
    return __singleton


class __CurrentConditionsDataCollector(DataCollector):
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
            Obtains weather forecast data from the Open Weather Map via HTTP requests.
            M requests are made each time this function is called (M = max queries/min)
            Parameters are read from configuration file (weather_forecast.config)
        """
        locations = find(self.__config['LOCATIONS_MODULE_NAME'], last_id=self.__state['last_id'],
                         count=self.__config['MAX_REQUESTS_PER_MINUTE'],
                         fields={'_id': 1, 'name': 1, 'country_code': 1})
        self.__data = []
        for location in locations['data']:
            url = self.__config['BASE_URL'].replace('{TOKEN}', self.__config['TOKEN']).replace('{LOC}',
                location['name']).replace('{COUNTRY}', location['country_code'])
            r = requests.get(url)
            temp = json.loads(r.content.decode('utf-8'))
            temp['location_id'] = location['_id']
            self.__data.append(temp)
        self.__state['last_id'] = locations['data'][-1]['_id'] if locations['more'] else None
        self.__state['last_request'] = datetime.datetime.now()
        self.__state['update_frequency'] = self.__config['MIN_UPDATE_FREQUENCY'] if locations['more'] \
            else self.__config['MAX_UPDATE_FREQUENCY']
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
        write_state(self.__state, __file__)

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'
