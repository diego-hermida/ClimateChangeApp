import datetime
import json
import requests

from pymongo import UpdateOne
from pytz import UTC
from data_gathering_subsystem.data_collector.data_collector import DataCollector
from utilities.mongo_util import MongoDBCollection
from utilities.util import date_to_millis_since_epoch, current_timestamp

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _HistoricalWeatherDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                     log_to_telegram=log_to_telegram)
    return _singleton


class _HistoricalWeatherDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)
        self.location_changed = False

    def _restore_state(self):
        """
            Deserializes the date of the last scheduled check.
        """
        super()._restore_state()
        if not self.state.get('tokens', False):
            self.state['tokens'] = {}
            for token in self.config['TOKENS']:
                self.state['tokens'][token] = {'daily_requests': 0, 'usable': True}

    def _has_pending_work(self):
        """
            Determines the need of performing a check operation.
        """
        super()._has_pending_work()
        if self.pending_work:
            # Resetting tokens if all tokens weren't usable and the module has pending work --> A MAX_UPDATE_FREQUENCY
            # period has passed.
            if not [x for x in self.config['TOKENS'] if self.state['tokens'][x]['usable']]:
                for token in self.config['TOKENS']:
                    # FIXES [BUG-022]
                    if not self.state['tokens'][token]['usable']:
                        self.logger.info('Resetting daily requests for token "%s", since it is usable again.'%(token))
                        self.state['tokens'][token]['daily_requests'] = 0
                        self.state['tokens'][token]['usable'] = True
            # FIXES [BUG-026]
            self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']

    def _collect_data(self):
        """
            Collects data from the Wunderground API via HTTP requests.
            T * MAX requests are made (where T is the number of available tokens; and MAX, the maximum amount of
            requests per minute and token).
            This module can be in two modes:
                - Normal mode (collects data for a single location until no more data are available).
                - Check mode: Determines if exists missing data.
        """
        super()._collect_data()
        self.data = []
        if self.state['missing_data_check']:
            # CHECK MODE
            self.logger.info('Scheduled check for outdated locations activated.')
            # Checking for new locations
            self.collection = MongoDBCollection(collection_name=self.module_name)
            current_locations = self.collection.collection.distinct('location_id')
            self.collection.connect(self.config['LOCATIONS_MODULE_NAME'])
            locations_count = self.collection.collection.count()
            if locations_count == 0:
                self.logger.info('No locations are available. Data collection will be stopped.')
                self.advisedly_no_data_collected = True
                # FIXES [BUG-027]
                self.state['current_date'] = None
                self.state['missing_data_check'] = True
                self.state['data_elements'] = 0
                self.data = None
                return
            if len(current_locations) < locations_count:
                self.state['missing_data_ids'] = [x['_id'] for x in self.collection.find(fields={'_id': 1}, 
                        sort='_id', conditions={'wunderground_loc_id': {'$ne': None}, '_id': {'$nin': 
                        current_locations}})[0]]
                self.logger.info('One or more locations must have been recently added, since not all locations have '
                        'recent historical data collected.')
            # If no new locations, checking if existing ones have missing recent data
            else:
                self.collection.connect(collection_name=self.module_name)
                target_date = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0,
                                                                tzinfo=UTC) - datetime.timedelta(
                    days=(self.config['TIME_INTERVAL'] + self.config['TIMEDELTA']))
                self.state['missing_data_ids'] = list(set([x['location_id'] for x in self.collection.find(sort='_id',
                        fields={'location_id': 1}, conditions={'_id.date_utc': {'$not': {'$gt': target_date}}})[0]]))
                if self.state['missing_data_ids']:
                    self.logger.info(
                        '%d location(s) have missing recent data.' % (len(self.state['missing_data_ids'])))
            # Missing data or locations
            if self.state['missing_data_ids']:
                self.logger.info('Check operation has detected missing data. Data collection will begin since next '
                                 'execution.')
                self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
            # No missing data or locations
            else:
                self.logger.info('All location(s) are up to date. Next execution will be carried out normally.')
                self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
            self.state['missing_data_check'] = False
            # FIXES [BUG-027]
            self.state['current_date'] = None
            self.advisedly_no_data_collected = True
        else:
            # NORMAL MODE
            if not self.state['missing_data_ids']:
                self.logger.warning('No locations are available. A check will be made in the next execution.')
                self.state['missing_data_check'] = True
                # FIXES [BUG-027]
                self.state['current_date'] = None
                self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
                self.advisedly_no_data_collected = True
            else:
                if not self.state['current_date']:
                    self.state['current_date'] = self._query_date()
                # Finding current location in database
                self.collection = MongoDBCollection(self.config['LOCATIONS_MODULE_NAME'])
                location = self.collection.collection.find_one({'_id': self.state['missing_data_ids'][0]})
                self.collection.connect(collection_name=self.module_name)
                try:
                    tokens = [x for x in self.config['TOKENS'] if self.state['tokens'][x]['usable']]
                    token_count = len(tokens)
                    while tokens:
                        token = tokens[0]
                        current_request = 0
                        while current_request < self.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
                            self.state['tokens'][token]['usable'] = self.state['tokens'][token]['daily_requests'] < \
                                    self.config['MAX_DAILY_REQUESTS_PER_TOKEN']
                            if not self.state['tokens'][token]['usable']:
                                self.logger.info('API token "%s" has reached the maximum daily requests allowed.'%(token))
                                tokens.remove(token)
                                break
                            current_request += 1
                            self.state['tokens'][token]['daily_requests'] += 1
                            url = self.config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}', self.state[
                                    'current_date']).replace('{LANG}', self.config['LANG']).replace('{LOC_ID}',
                                    str(location['wunderground_loc_id']))
                            r = requests.get(url)
                            try:
                                temp = json.loads(r.content.decode('utf-8', errors='replace'))
                                # Removing the "_id" field FIXES [BUG-032].
                                if temp['history']['observations'] and temp['history']['dailysummary']:
                                    temp['location_id'] = location['_id']
                                    date = datetime.datetime(year=int(temp['history']['date']['year']), month=int(temp[
                                            'history']['date']['mon']), day=int(temp['history']['date']['mday']),
                                            hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
                                    temp['date_utc'] = date_to_millis_since_epoch(date)
                                    self.data.append(temp)
                                    # A new value resets unmeasured days. FIXES [BUG-018]
                                    self.state['consecutive_unmeasured_days'] = 0
                                else:
                                    self.state['consecutive_unmeasured_days'] += 1
                            # Adding json.decoder.JSONDecodeError FIXES [BUG-020]
                            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                                self.state['consecutive_unmeasured_days'] += 1
                            # N days without measures indicate that no data is available before last successful date.
                            # Replacing '==' with '>=' FIXES [BUG-021]
                            if self.state['consecutive_unmeasured_days'] >= self.config['MAX_DAY_COUNT']:
                                self.logger.info('No historical data available for "%s" before %s.' % (location['name'],
                                        self._sum_days( self.state['current_date'], self.config['MAX_DAY_COUNT'] - 1,
                                        date_format_out='%d/%m/%Y')))
                                self.state['missing_data_ids'] = self.state['missing_data_ids'][1:] if len(
                                        self.state['missing_data_ids']) > 1 else None
                                self.location_changed = True
                                # FIXES [BUG-027]
                                self.state['current_date'] = None
                                raise StopIteration()
                            else:
                                self.state['current_date'] = self._sum_days(self.state['current_date'], -1)
                        try:
                            tokens.remove(token)
                        except ValueError:
                            pass  # Item has already been removed
                        self.logger.debug('Collected data: %0.2f%%' % (((token_count - len(tokens)) / token_count) * 100))
                except StopIteration:  # All missing data for a location has been collected
                    pass
                if not [x for x in self.config['TOKENS'] if self.state['tokens'][x]['usable']]:
                    self.logger.info('All API token(s) have reached the maximum daily requests allowed.')
                    self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
                    self.advisedly_no_data_collected = len(self.data) == 0
                if self.state['consecutive_unmeasured_days'] > 0:
                    self.advisedly_no_data_collected = len(self.data) == 0
                if not self.state['missing_data_ids']:
                    self.logger.info('All outdated locations have the most recent data. A new check will be made soon.')
                    self.state['current_date'] = None
                    self.state['consecutive_unmeasured_days'] = 0
                    self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
                    self.state['missing_data_check'] = True
        self.state['last_request'] = current_timestamp(utc=True)
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
                operations.append(UpdateOne({'location_id': value['location_id'], 'date_utc': value['date_utc']},
                        update={'$setOnInsert': value}, upsert=True))
            result = self.collection.collection.bulk_write(operations)
            self.state['inserted_elements'] = result.bulk_api_result['nInserted'] + result.bulk_api_result['nMatched'] \
                    + result.bulk_api_result['nUpserted']
            if self.state['inserted_elements'] - (result.bulk_api_result['nInserted'] + result.bulk_api_result[
                    'nUpserted']) >= self.config['DB_EXISTING_DATA_LIMIT']:
                self.logger.warning('Collected data does already exist in database for the current location.')
                if self.state['missing_data_ids'] and self.location_changed:
                    self.logger.info('Current location has already been set to the next one.')
                elif self.state['missing_data_ids'] and len(self.state['missing_data_ids']) > 0:
                    self.state['missing_data_ids'] = self.state['missing_data_ids'][1:] if len(self.state[
                            'missing_data_ids']) > 1 else None
                    # FIXES [BUG-027]
                    self.state['current_date'] = None
                    if self.state['missing_data_ids']:
                        self.logger.info('Current location has been be set to the next one.')
                    else:
                        self.logger.info('All locations have already the most recent data. Update frequency will be set'
                                ' to its MAX value (if it wasn\'t done yet).')
                        self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
            else:
                self.logger.debug('Collected data is new.')
            if self.state['inserted_elements'] == len(self.data):
                self.logger.debug('Successfully inserted %d element(s) into database.'%(self.state['inserted_elements']))
            else:
                self.logger.warning('Some element(s) were not inserted (%d out of %d)'%(self.state['inserted_elements'],
                        self.state['data_elements']))
            self.collection.close()
            self.data = None  # Allowing GC to collect data object's memory
        else:
            self.logger.info('No elements were saved because no elements have been collected.')
            self.state['inserted_elements'] = 0

    def _query_date(self, date_format='%Y%m%d') -> str:
        """
            In order to retrieve historical data, if 'yesterday' date was used, some locations could not have such data
            yet, due to timezones. Thus, a TIME_INTERVAL is left.
        """
        return (datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC) -
                datetime.timedelta(days=self.config['TIME_INTERVAL'])).strftime(date_format)

    @staticmethod
    def _sum_days(day: str, num_days: int, date_format_in='%Y%m%d', date_format_out='%Y%m%d') -> str:
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
