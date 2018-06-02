import json
import requests

from data_gathering_subsystem.data_collector.data_collector import DataCollector
from utilities.util import current_timestamp

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _CountriesDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                             log_to_telegram=log_to_telegram)
    return _singleton


class _CountriesDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _collect_data(self):
        """
            Collects data from the World Bank API via HTTP requests. A single request is made.
        """
        super()._collect_data()
        url = self.config['BASE_URL'].replace('{LANG}', self.config['LANG'])
        r = requests.get(url)
        metadata = json.loads(r.content.decode('utf-8', errors='replace'))[0]
        temp_data = json.loads(r.content.decode('utf-8', errors='replace'))[1]
        self.data = []
        unmatched = 0
        try:
            for value in temp_data:  # Creates '_id' attribute and removes non-utilities fields
                value['_id'] = value['iso2Code']
                value['iso3'] = value['id']
                del value['iso2Code']
                del value['id']
                del value['adminregion']
                del value['lendingType']
                self.data.append(value)
        except (AttributeError, KeyError, TypeError, ValueError):
            unmatched += 1
        if unmatched and unmatched * 10 > metadata['total']:
            self.logger.error('Since malformed data > 10%% (%d out of %d), data collection will be aborted.'%
                    (unmatched, metadata['total']))
            raise Exception('Data collection has been aborted. So many bad values.')
        elif unmatched:
            self.logger.warning('%d countries (out of %d) have malformed data.'%(unmatched, metadata['total']))
        self.state['last_request'] = current_timestamp(utc=True)
        self.state['update_frequency'] = self.config['UPDATE_FREQUENCY'] if self.data else self.config['STATE_STRUCT'][
                'update_frequency']
        self.state['data_elements'] = len(self.data)
        if self.data:
            self.logger.info('WorldBank API request has been successfully processed. Data from %d countri(es) (out of '
                    '%d) has been collected.'%(len(self.data), metadata['total']))
        else:
            self.logger.warning('No data has been collected. Data collection will be retried in the next execution.')
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'countries'.
            Since no duplicates are allowed, collection is erased before saving data.
            Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.data:
            if not self.collection.is_empty():
                self.collection.remove_all()
                self.logger.debug('Cleared database collection so as to perform bulk-insert.')
            ids = self.collection.insert_many(self.data)
            inserted = len(ids.inserted_ids)
            self.state['inserted_elements'] = inserted
            if inserted == len(self.data):
                self.logger.debug('Successfully inserted %d element(s) into database.'%(inserted))
            elif (self.state['data_elements'] - inserted) * 10 > self.state['data_elements']:
                self.logger.error('Since uninserted elements(s) > 10%% (%d out of %d), data collection will be '
                        'aborted.'%((self.state['data_elements'] - inserted), self.state['data_elements']))
                raise Exception('Data collection has been aborted. Insufficient saved values.')
            else:
                self.logger.warning('Some elements were not inserted (%d out of %d).'%
                        (self.state['data_elements'] - inserted, self.state['data_elements']))
            self.collection.close()
            self.data = None  # Allowing GC to collect data object's memory
        else:
            self.logger.info('No elements were saved because no elements have been collected.')
            self.state['inserted_elements'] = 0
