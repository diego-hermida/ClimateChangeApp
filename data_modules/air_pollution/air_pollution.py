import datetime
import json
import requests

from data_collector.data_collector import DataCollector
from pymongo import UpdateOne
from utilities.db_util import MongoDBCollection

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __AirPollutionDataCollector()
    return __singleton


class __AirPollutionDataCollector(DataCollector):

    def __init__(self):
        super().__init__(file_path=__file__)

    def _collect_data(self):
        """
            Obtains data from the WAQI API via HTTP requests. L requests are made, where L is the number of locations.
        """
        super()._collect_data()
        # Retrieves locations with WAQI Station ID from database
        self.collection = MongoDBCollection(collection_name=self.config['LOCATIONS_MODULE_NAME'])
        locations = self.collection.find(last_id=self.state['last_id'], count=self.config['MAX_REQUESTS_PER_MINUTE'],
                fields={'_id': 1, 'name': 1, 'waqi_station_id': 1}, sort='_id', conditions={'waqi_station_id':
                {'$ne': None}})
        self.collection.close()
        self.data = []
        unmatched = []
        locations_length = len(locations['data'])
        for index, location in enumerate(locations['data']):
            url = self.config['BASE_URL'].replace('{STATION_ID}', str(location['waqi_station_id'])).replace('{TOKEN}',
                    self.config['TOKEN'])
            r = requests.get(url)
            temp = json.loads(r.content.decode('utf-8'))
            # Adding only verified data
            if temp['status'] == 'ok':
                temp['location_id'] = location['_id']
                temp['_id'] = {'station_id': location['waqi_station_id'], 'time_utc': int(temp['data']['time']['v']) * 1000}
                self.data.append(temp)
            else:
                unmatched.append(location['name'])
            if index > 0 and index % 10 is 0:
                self.logger.debug('Collected data: %.2f%%' % (((index / locations_length) * 100)))
        if unmatched:
            self.logger.warning('%d location(s) do not have recent air pollution data: %s'%(len(unmatched),
                    sorted(unmatched)))
        self.state['last_id'] = locations['data'][-1]['_id'] if locations['more'] else None
        self.state['last_request'] = datetime.datetime.now()
        self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY'] if locations['more'] else self.config[
            'MAX_UPDATE_FREQUENCY']
        self.state['data_elements'] = len(self.data)
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'air_pollution'.
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
