import json
import requests

from data_gathering_subsystem.data_collector.data_collector import DataCollector
from pymongo import UpdateOne
from utilities.db_util import MongoDBCollection
from utilities.util import current_timestamp_utc

_singleton = None


def instance(log_to_file=True, log_to_stdout=True) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _CurrentConditionsDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout)
    return _singleton


class _CurrentConditionsDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout)

    def _collect_data(self):
        """
            Collects current conditions' data from the Open Weather Map via HTTP requests.
            M requests are made (where M is the maximum amount of requests per minute)
            Parameters are read from configuration file (weather_forecast.config)
        """
        super()._collect_data()
        # Retrieves all locations with OpenWeatherMap Station IDs from database
        self.collection = MongoDBCollection(self.config['LOCATIONS_MODULE_NAME'])
        locations = self.collection.find(start_index=self.state['start_index'], count=self.config[
                'MAX_REQUESTS_PER_MINUTE'], fields={'_id': 1, 'name': 1, 'owm_station_id': 1}, conditions={
                'owm_station_id': {'$ne': None}}, sort='_id')
        self.collection.close()
        self.data = []
        unmatched = []
        locations_length = len(locations['data'])
        for index, location in enumerate(locations['data']):
            url = self.config['BASE_URL'].replace('{TOKEN}', self.config['TOKEN']).replace('{LOC_ID}',
                    str(location['owm_station_id']))
            r = requests.get(url)
            try:
                temp = json.loads(r.content.decode('utf-8', errors='replace'))
                if temp['coord'] and temp['weather'] and temp['main'] and temp['wind'] and temp['sys']:
                    temp['location_id'] = location['_id']
                    temp['_id'] = {'station_id': temp['id'], 'time': temp['dt']}
                    self.data.append(temp)
            # Adding json.decoder.JSONDecodeError FIXES [BUG-020]
            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                unmatched.append(location['name'])
            if index > 0 and index % 10 is 0:
                self.logger.debug('Collected data: %0.2f%%'%((((index + 1) / locations_length) * 100)))
        if unmatched:
            self.logger.warning('Current weather conditions data is unavailable for %d location(s): %s'%(len(unmatched),
                    sorted(unmatched)))
        self.state['last_request'] = current_timestamp_utc()
        # No available locations is not an error
        if not locations['data']:
            self.logger.info('No locations are available. Data collection will be stopped.')
            self.advisedly_no_data_collected = True
        self.state['start_index'] = locations.get('next_start_index')
        self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY'] if self.state['start_index'] or not \
            locations['data'] else self.config['MAX_UPDATE_FREQUENCY']
        self.state['data_elements'] = len(self.data)
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'locations'.
            Existent records are updated with new values, and new ones are inserted as new ones.
            Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.data:
            operations = []
            for value in self.data:
                operations.append(UpdateOne({'_id': value['_id']}, update={'$set': value}, upsert=True))
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