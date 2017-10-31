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
        __singleton = __HistoricalWeatherDataCollector()
    return __singleton


class __HistoricalWeatherDataCollector(DataCollector):
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
        self.__state['date'] = self.__state['date'] if self.__state['date'] else self.__config['MIN_DATE']

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
            Obtains data from the Wunderground API via HTTP requests. Currently only historical data is gathered.
            N * M requests are made each time this function is called (N = number of tokens, M = max queries/min per token)
            Parameters are read from configuration file (historical_weather.config)
        """
        MAX_REQUESTS = len(self.__config['TOKENS'] * self.__config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'])
        locations = find(self.__config['LOCATIONS_MODULE_NAME'], last_id=self.__state['last_id'], count=MAX_REQUESTS,
                         fields={'_id': 1, 'name': 1, 'country_code': 1})
        # If not remaining data, starting over
        locations_iter = iter(locations['data'])
        self.__data = []
        try:
            for token in self.__config['TOKENS']:
                current_request = 0
                while current_request < self.__config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
                    location = next(locations_iter)
                    url = self.__config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}',
                        self.__state['date']).replace('{LANG}', self.__config['LANG']).replace('{STATE|COUNTRY}',
                        location['country_code']).replace('{LOC}', location['name'])
                    r = requests.get(url)
                    temp = json.loads(r.content.decode('utf-8'))
                    temp['location_id'] = location['_id']
                    current_request += 1
                    self.__data.append(temp)
        except StopIteration:  # No more locations in locations_iter
            pass
        self.__state['last_id'] = locations['data'][-1]['_id'] if locations['more'] else None
        self.__state['date'] = self.__state['date'] if locations['more'] else self.__next_day(self.__state['date'])
        self.__state['update_frequency'] = self.__config['MAX_UPDATE_FREQUENCY'] if \
            self.__ge_today(self.__state['date']) else self.__config['MIN_UPDATE_FREQUENCY']
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
        write_state(self.__state, __file__)

    @staticmethod
    def __next_day(day: str, format='%Y%m%d') -> str:
        day = datetime.datetime.strptime(day, format)
        day += datetime.timedelta(days=1)  # Adding one day
        return day.strftime(format)

    @staticmethod
    def __ge_today(day: str, format='%Y%m%d'):  # ge: greater or equal
        return datetime.datetime.strptime(day, format) >= \
               datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'
