import json
import requests

from data_gathering_subsystem.data_collector.data_collector import DataCollector
from pymongo import UpdateOne
from utilities.mongo_util import MongoDBCollection
from utilities.util import date_to_millis_since_epoch, current_timestamp_utc

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _EnergySourcesDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                 log_to_telegram=log_to_telegram)
    return _singleton


class _EnergySourcesDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _collect_data(self):
        """
            Collects data from the CO2 Signal API via HTTP requests. C requests are made, where C is the number of 
            available countries in database.
        """
        super()._collect_data()
        # Retrieves countries from database
        self.collection = MongoDBCollection(collection_name=self.config['COUNTRIES_MODULE_NAME'])
        countries, next_start_index = self.collection.find(fields={'_id': 1, 'name': 1}, sort='_id')
        self.collection.close()
        self.data = []
        unmatched = []
        # Filtering countries with numbers (World Bank API aggregations)
        countries = [x for x in countries if not any(char.isdigit() for char in x['_id'])]
        countries_length = len(countries)
        date = self.get_last_date_to_millis()
        for index, country in enumerate(countries):
            url = self.config['BASE_URL'].replace('{COUNTRY_CODE}', country['_id'])
            r = requests.get(url, headers={'auth-token': self.config['TOKEN']})
            try:
                temp = json.loads(r.content.decode('utf-8', errors='replace'))
                # FIXES [BUG-028]
                message = temp.get('message')
                if r.status_code != 200 and message:
                    self.logger.info('API rate limit has been exceeded. Stopping data collection. Current country is %s'
                            '. Collected data for %d (out of %d) countries.'%(country['_id'], index, countries_length))
                    if not self.data:  # This won't cause the PendingWorkAndNoDataCollectedError.
                        self.advisedly_no_data_collected = True
                        self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
                    break  # Stopping current data collection (but allowing saving previous data if present)
                # Adding only verified data
                # Removing the "_id" field FIXES [BUG-032].
                if temp['status'] == 'ok' and temp['data']:
                    temp['country_id'] = country['_id']
                    temp['time_utc'] = date
                    try:
                        del temp['countryCode']
                        del temp['status']
                        del temp['_disclaimer']
                    except KeyError:
                        pass
                    self.data.append(temp)
                else:
                    unmatched.append(country['name'])
            # Adding json.decoder.JSONDecodeError FIXES [BUG-020]
            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                unmatched.append(country['name'])
            if index > 0 and index % 10 is 0:
                self.logger.debug('Collected data: %.2f%%' % ((index / countries_length) * 100))
        if unmatched:
            self.logger.warning('%d country(ies) do not have recent energy sources data: %s' % (len(unmatched),
                    sorted(unmatched)))
        # No available countries is not an error
        if not countries:
            self.logger.info('No countries are available. Data collection will be stopped.')
            self.advisedly_no_data_collected = True
            self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
        self.state['last_request'] = current_timestamp_utc()
        if self.data:
            self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
        self.state['data_elements'] = len(self.data)
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'energy_sources'.
            Existent records are not updated, and new ones are inserted as new ones.
            Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.data:
            operations = []
            for value in self.data:
                operations.append(UpdateOne({'country_id': value['country_id'], 'time_utc': value['time_utc']},
                        update={'$setOnInsert': value}, upsert=True))
            result = self.collection.collection.bulk_write(operations)
            self.state['inserted_elements'] = result.bulk_api_result['nInserted'] + result.bulk_api_result['nMatched'] \
                    + result.bulk_api_result['nUpserted']
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

    @staticmethod
    def get_last_date_to_millis() -> int:
        date = current_timestamp_utc()
        if date.minute < 15:
            date = date.replace(minute=0, second=0, microsecond=0)
        elif date.minute < 30:
            date = date.replace(minute=15, second=0, microsecond=0)
        elif date.minute < 45:
            date = date.replace(minute=30, second=0, microsecond=0)
        else:
            date = date.replace(minute=45, second=0, microsecond=0)
        return date_to_millis_since_epoch(date)
