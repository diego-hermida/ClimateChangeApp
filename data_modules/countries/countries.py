import datetime
import json
import requests

from data_collector.data_collector import DataCollector

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CountriesDataCollector()
    return __singleton


class __CountriesDataCollector(DataCollector):

    def __init__(self):
        super().__init__(file_path=__file__)

    def _collect_data(self):
        """
            Collects data from the World Bank API via HTTP requests. A single request is made.
        """
        super()._collect_data()
        url = self.config['BASE_URL'].replace('{LANG}', self.config['LANG'])
        r = requests.get(url)
        metadata = json.loads(r.content.decode('utf-8'))[0]
        temp_data = json.loads(r.content.decode('utf-8'))[1]
        self.data = []
        for value in temp_data:  # Creates '_id' attribute and removes non-utilities fields
            value['_id'] = value['iso2Code']
            value['iso3'] = value['id']
            del value['iso2Code']
            del value['id']
            del value['adminregion']
            del value['lendingType']
            self.data.append(value)
        self.state['last_request'] = datetime.datetime.now()
        self.state['update_frequency'] = self.config['UPDATE_FREQUENCY']
        self.state['data_elements'] = len(self.data)
        self.logger.info('WorldBank API request has been successfully processed. Data from %d countries (out of %d) has'
                         ' been collected.'%(len(self.data), metadata['total']))
        self.data = self.data if self.data else None

    def _save_data(self):
        """
        Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'countries'.
        Since no duplicates are allowed, collection is erased before saving data.
        Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.collection:
            if not self.collection.is_empty():
                self.collection.remove_all()
                self.logger.debug('Cleared database collection so as to perform bulk-insert.')
            ids = self.collection.collection.insert_many(self.data)
            inserted = len(ids.inserted_ids)
            self.state['inserted_elements'] = inserted
            if inserted == len(self.data):
                self.logger.debug('Successfully inserted %d elements into database.'%(inserted))
            else:
                self.logger.warning('Some elements were not inserted (%d out of %d).'%(inserted,
                        self.state['data_elements']))
            self.collection.close()
            self.data = None  # Allowing GC to collect data object's memory
        else:
            self.logger.info('No elements were saved because no elements have been collected.')
            self.state['inserted_elements'] = 0
