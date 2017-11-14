import datetime
import json
import pytz
import requests

from data_collector.data_collector import DataCollector
from pymongo import UpdateOne
from utilities.db_util import MongoDBCollection
from utilities.util import date_plus_timedelta_gt_now, deserialize_date, serialize_date, date_to_millis_since_epoch

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __HistoricalWeatherDataCollector()
    return __singleton


class __HistoricalWeatherDataCollector(DataCollector):

    def __init__(self):
        super().__init__(file_path=__file__)
        self.__single_mode_check = False

    def _restore_state(self):
        """
            Deserializes the date of the last scheduled check.
        """
        super()._restore_state()
        self.state['single_location_last_check'] = deserialize_date(self.state['single_location_last_check'])

    def _has_pending_work(self):
        """
            Determines the need of performing a check operation.
        """
        super()._has_pending_work()
        self.__single_mode_check = date_plus_timedelta_gt_now(self.state['single_location_last_check'],
                                                              self.state['single_location_update_frequency'])

    def _collect_data(self):
        """
            Collects data from the Wunderground API via HTTP requests.
            T * MAX requests are made (where T is the number of available tokens; and MAX, the maximum amount of
            requests per minute and token).
            This module can be in two modes:
                - Single location mode (collects data for a single location until no more data are available).
                - Normal mode (collects recent historical data for all locations).
        """
        super()._collect_data()
        self.data = []
        # SINGLE MODE
        if self.state.get('single_location_mode', False):  # Checking if single location mode is enabled
            self.logger.info('Single location mode is enabled. Collecting all available data for a single location.')
            if not self.state['single_location_date']:
                self.state['single_location_date'] = self.__query_date()
            # Finding current location in database
            self.collection = MongoDBCollection(self.config['LOCATIONS_MODULE_NAME'])
            location = self.collection.collection.find_one({'_id': self.state['single_location_ids'][0]})
            self.collection.connect(collection_name=self.module_name)
            try:
                for token_index, token in enumerate(self.config['TOKENS']):
                    current_request = 0
                    while current_request < self.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
                        url = self.config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}', self.state[
                                'single_location_date']).replace('{LANG}', self.config['LANG']).replace('{LOC_ID}',
                                location['wunderground_loc_id'])
                        r = requests.get(url)
                        temp = json.loads(r.content.decode('utf-8'))
                        print(temp)
                        if temp['history']['observations'] and temp['history']['dailysummary']:
                            temp['location_id'] = location['_id']
                            date = datetime.datetime(year=int(temp['history']['date']['year']),
                                    month=int(temp['history']['date']['mon']), day=int(temp['history']['date']['mday']),
                                    hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)
                            temp['_id'] = {'loc_id': location['_id'],
                                           'date_utc': date_to_millis_since_epoch(date)}
                            self.data.append(temp)
                        else:
                            self.state['consecutive_unmeasured_days'] += 1
                            # N days without measures indicate that no data is available before last successful date.
                            if self.state['consecutive_unmeasured_days'] == self.config['MAX_DAY_COUNT']:
                                self.logger.info('No historical data available for "%s" before %s.'%(location['name'],
                                        self.__sum_days(self.state['single_location_date'], self.config[
                                        'MAX_DAY_COUNT'] - 1, date_format_out='%d/%m/%Y')))
                                raise StopIteration()
                        current_request += 1
                        self.state['single_location_date'] = self.__sum_days(self.state['single_location_date'], -1)
                    self.logger.debug('Collected data: %0.2f%%' % ((token_index + 1) * self.config[
                        'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']))
            except StopIteration:  # No more historical data for such location
                self.state['single_location_date'] = None
                self.state['single_location_ids'] = self.state['single_location_ids'][1:] if self.state[
                    'single_location_ids'] else None
                self.state['single_location_mode'] = False if self.state['single_location_ids'] is None else \
                    len(self.state['single_location_ids']) > 0
                self.state['consecutive_unmeasured_days'] = 0
                if not self.state['single_location_mode']:
                    self.logger.info('All historical data for outdated locations has been collected. Stopping '
                            'single location mode.')
                self.advisedly_no_data_collected = True
        else:
            # NORMAL MODE
            if self.__single_mode_check: # Testing if check is scheduled
                self.logger.info('Scheduled check for outdated locations activated.')
                # Checking for new locations
                self.collection = MongoDBCollection(collection_name=self.module_name)
                current_locations = self.collection.collection.distinct('location_id')
                self.collection.connect(self.config['LOCATIONS_MODULE_NAME'])
                locations_count = self.collection.collection.count()
                if len(current_locations) < locations_count:
                    self.state['single_location_ids'] = [x['_id'] for x in self.collection.find(fields={'_id': 1},
                            sort='_id', conditions={'wunderground_loc_id': {'$ne': None},
                            '_id': {'$nin': current_locations}})['data']]
                    self.logger.info('One or more locations must have been recently added, since not all locations have'
                            ' recent historical data collected.')
                # If no new locations, checking if existing ones have missing recent data
                else:
                    self.collection.connect(collection_name=self.module_name)
                    target_date = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) - \
                            datetime.timedelta(days=(self.config['TIME_INTERVAL'] + self.config['TIMEDELTA']))
                    missing_db_locations = list(set([x['location_id'] for x in self.collection.find(sort='_id',
                            fields={'location_id': 1}, conditions={'_id.date_utc': {'$not': {'$gt':target_date}}})['data']]))
                    if missing_db_locations:
                        self.collection.connect(self.config['LOCATIONS_MODULE_NAME'])
                        self.state['single_location_ids'] = [x['_id'] for x in self.collection.find(fields={'_id': 1},
                                sort='_id', conditions={'wunderground_loc_id': {'$ne': None},
                                '_id': {'$nin': current_locations}})['data']]
                        self.logger.info('%d location(s) have missing recent data.'%(len(missing_db_locations)))
                # Missing data or locations
                if self.state['single_location_ids']:
                    self.logger.info('Check operation has detected missing data. Single location mode will be enabled '
                            'from now on.')
                    self.state['single_location_mode'] = True
                    self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
                # No missing data or locations
                else:
                    self.logger.info('All locations are up to date. Next execution will be carried out normally.')
                self.advisedly_no_data_collected = True
                self.state['single_location_last_check'] = datetime.datetime.now()
            # Check is not scheduled, so performing normal execution
            else:
                self.state['date'] = self.state['date'] if self.state['date'] else self.__query_date()
                MAX_REQUESTS = len(self.config['TOKENS'] * self.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'])
                # Retrieves all locations with Wunderground station IDs from database
                self.collection = MongoDBCollection(collection_name=self.config['LOCATIONS_MODULE_NAME'])
                locations = self.collection.find(last_id=self.state['last_id'], count=MAX_REQUESTS,
                        fields={'_id': 1, 'name': 1, 'wunderground_loc_id': 1}, sort='_id',
                        conditions={'wunderground_loc_id': {'$ne': None}})
                locations_iter = iter(locations['data'])
                locations_length = len(locations['data'])
                self.collection.connect(collection_name=self.module_name)
                unmatched = []
                try:
                    for token_index, token in enumerate(self.config['TOKENS']):
                        current_request = 0
                        while current_request < self.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
                            location = next(locations_iter)
                            url = self.config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}',
                                    self.state['date']).replace('{LANG}', self.config['LANG']).replace('{LOC_ID}',
                                    location['wunderground_loc_id'])
                            r = requests.get(url)
                            temp = json.loads(r.content.decode('utf-8', errors='replace'))
                            if temp['history']['observations'] and temp['history']['dailysummary']:
                                temp['location_id'] = location['_id']
                                date = datetime.datetime(year=int(temp['history']['date']['year']),
                                        month=int(temp['history']['date']['mon']), day=int(temp['history']['date']
                                        ['mday']), hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)
                                temp['_id'] = {'loc_id': location['_id'], 'date_utc': date_to_millis_since_epoch(date)}
                                self.data.append(temp)
                            else:
                                unmatched.append(location['name'])
                            current_request += 1
                        self.logger.debug('Collected data: %0.2f%%'%((((token_index + 1) * self.config[
                                'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']) / locations_length) * 100))
                except StopIteration:  # No more locations in locations_iter
                    pass
                self.state['last_id'] = locations['data'][-1]['_id'] if locations['more'] else None
                self.state['date'] = self.state['date'] if locations['more'] else None
                self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY'] if self.__lt(self.state['date'],
                        self.__query_date()) else self.config['MAX_UPDATE_FREQUENCY']
                if unmatched:
                    self.logger.warning('No historical weather data available for %d locations: %s'%(len(unmatched),
                            sorted(unmatched)))
        self.state['last_request'] = datetime.datetime.now()
        self.state['data_elements'] = len(self.data)
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'historical_weather'.
            Existent records are not updated, and new ones are inserted as new ones.
            Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.data:
            operations = []
            for value in self.data:
                operations.append(UpdateOne({'_id': value['_id']}, update={'$setOnInsert': value}, upsert=True))
            result = self.collection.collection.bulk_write(operations)
            self.state['inserted_elements'] = result.bulk_api_result['nInserted'] + result.bulk_api_result['nMatched'] \
                    + result.bulk_api_result['nUpserted']
            if self.state['inserted_elements'] == len(self.data):
                self.logger.debug('Successfully inserted %d elements into database.'%(self.state['inserted_elements']))
            else:
                self.logger.warning('Some elements were not inserted (%d out of %d)'%(self.state['inserted_elements'],
                        self.state['data_elements']))
            self.collection.close()
            self.data = None  # Allowing GC to collect data object's memory
        else:
            self.logger.info('No elements were saved because no elements have been collected.')
            self.state['inserted_elements'] = 0

    def _save_state(self):
        """
            Serializes the date of the last scheduled check.
        """
        self.state['single_location_last_check'] = serialize_date(self.state['single_location_last_check'])
        super()._save_state()

    def __query_date(self, date_format='%Y%m%d') -> str:
        """
            In order to retrieve historical data, if 'yesterday' date was used, some locations could not have such data
            yet, due to timezones. Thus, a TIME_INTERVAL is left.
        """
        return (datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(
                days=self.config['TIME_INTERVAL'])).strftime(date_format)

    @staticmethod
    def __sum_days(day: str, num_days: int, date_format_in='%Y%m%d', date_format_out='%Y%m%d') -> str:
        """
            Given a date as a String, sums a specific number of days to it, formats the resulting date and returns it.
            :param day: Original date
            :param num_days: Number of days to sum
            :param date_format_in: 'day' date format
            :param date_format_out: return value date format
            :return: A 'str' containing the value of the original date plus 'num_days'.
            :rtype: str
        """
        return (datetime.datetime.strptime(day, date_format_in) + datetime.timedelta(days=num_days)).strftime(
                date_format_out)

    @staticmethod
    def __lt(day1: str, day2: str, date_format_1='%Y%m%d', date_format_2='Y%m%d') -> bool:
        """
            Given two dates formatted as String, makes a '<' operation between them.
            :param date_format_1: Date format of 'day1'
            :param date_format_2: Date format of 'day2'
            :rtype: bool
        """
        return datetime.datetime.strptime(day1, date_format_1) < datetime.datetime.strptime(day2, date_format_2)
