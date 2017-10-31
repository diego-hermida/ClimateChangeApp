import datetime
import itertools
import json
import requests

from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name, worktime, read_state, write_state, \
    serialize_date, deserialize_date

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CountryIndicatorsDataCollector()
    return __singleton


class __CountryIndicatorsDataCollector(DataCollector):
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
        self.__state['begin_date'] = self.__state['begin_date'] if self.__state['begin_date'] else self.__config[
            'MIN_DATE']
        self.__state['end_date'] = self.__state['end_date'] if self.__state['end_date'] else datetime.date.today().year

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
            Obtains data from the World Bank API via HTTP requests.
            N * P requests are made each time this function is called (N = number of indicators, P = number of pages in
            which data has been splitted)
            Indicators and countries are both read from configuration file (country_indicators.config)
        """
        self.__data = []
        try:
            for indicator in self.__config['INDICATORS']:
                # Data is processed by paging requests (lighter, leading to less probability of failure)
                remaining_data = True
                page = 1
                while remaining_data:
                    url = self.__config['BASE_URL'].replace('{LANG}', self.__config['LANG']). \
                        replace('{INDICATOR}', indicator).replace('{BEGIN_DATE}', str(self.__state['begin_date'])). \
                        replace('{END_DATE}', str(self.__state['end_date'])).replace('{PAGE}', str(page)). \
                        replace('{ITEMS_PER_PAGE}', str(self.__config['ITEMS_PER_PAGE']))
                    r = requests.get(url)
                    temp = json.loads(r.content.decode('utf-8'))
                    remaining_data = not temp[0]['page'] == temp[0]['pages']  # True if this page is last page
                    page += 1
                    self.__data.append(temp[1])
                # TODO: Think about using a 'verification request', lighter, for one country -->
                # TODO: Verifying correct dates with less data (instead of retrieving all countries' info per indicator)
                # The World Bank API returns all indicator's data if 'begin_date' and 'end_date' are higher than API
                # values. Thus, self.__data would contain a huge list of useless information. So, a check operation
                # must be performed with first country's data: if dates are not between 'begin_date' and 'end_date',
                # StopIteration will be raised, and data won't be added (avoiding processing N-1 countries).
                # Ideally, only one comparison is performed, since API returns data ordered by descending date.
                # for value in temp:
                #     if self.__state['begin_date'] > int(value['date']):
                #         raise StopIteration  # Bad dates
                # self.__data.append(temp)
                # TODO: End previous TODO
        except StopIteration:
            self.__data = None
            # Setting update frequency to a shorter time interval (data will be updated soon)
            self.__state['update_frequency'] = self.__config['TEMP_UPDATE_FREQUENCY']
        else:
            # Flattens list of lists
            self.__data = list(itertools.chain.from_iterable(self.__data)) if self.__data else None
            if self.__data:
                for value in self.__data:  # Creates '_id' attribute and removes non-utilities fields
                    value['_id'] = value['indicator']['id'] + '_' + value['country']['id'] + '_' + value['date']
                    del value['decimal']
            self.__state['begin_date'] = self.__state['end_date']
            self.__state['end_date'] += 1
            self.__state['update_frequency'] = self.__config['MAX_UPDATE_FREQUENCY']
        self.__state['last_request'] = datetime.datetime.now()
        print(self.__data.__len__())

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
