import datetime
import itertools
import json
import requests

from data_collector.data_collector import DataCollector
from pymongo import UpdateOne

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __CountryIndicatorsDataCollector()
    return __singleton


class __CountryIndicatorsDataCollector(DataCollector):

    def __init__(self):
        super().__init__(file_path=__file__)

    def _collect_data(self):
        """
            Obtains data from the World Bank API via HTTP requests.
            N * P requests are made (being N the number of indicators, and P the number of pages in which requests have
            been split)
            Indicators are read from configuration file (country_indicators.config)
        """
        super()._collect_data()
        self.data = []
        url = self.config['VALIDATION_QUERY'].replace('{BEGIN_DATE}', str(self.state['begin_date'])).replace(
                '{END_DATE}', str(self.state['end_date']))
        r = requests.get(url)
        validation_data = json.loads(r.content.decode('utf-8'))[1][0]
        self.advisedly_no_data_collected = validation_data['value'] is None
        if not self.advisedly_no_data_collected:
            self.logger.info('Validation query succeeded and found suitable data to be collected.')
            self.logger.info('Collecting data from %d indicators.'%(len(self.config['INDICATORS'])))
            indicators_length = len(self.config['INDICATORS'])
            for index, indicator in enumerate(self.config['INDICATORS']):
                # Data is processed by paging requests (lighter, leading to less probability of failure)
                remaining_data = True
                page = 1
                while remaining_data:
                    url = self.config['BASE_URL'].replace('{LANG}', self.config['LANG']).replace('{INDICATOR}',
                            indicator).replace('{BEGIN_DATE}', str(self.state['begin_date'])).replace('{END_DATE}',
                            str(self.state['end_date'])).replace('{PAGE}', str(page)).replace('{ITEMS_PER_PAGE}',
                            str(self.config['ITEMS_PER_PAGE']))
                    r = requests.get(url)
                    metadata = json.loads(r.content.decode('utf-8'))[0]
                    temp_data = json.loads(r.content.decode('utf-8'))[1]
                    remaining_data = not metadata['page'] == metadata['pages']  # True if this page is last page
                    page += 1
                    self.logger.debug('Collected %d elements for indicator "%s". Current page is %d (out of %d).'%
                            (len(temp_data), indicator, metadata['page'], metadata['pages']))
                    self.data.append(temp_data)
                self.logger.debug('Data collected: %0.2f%%'%(((index + 1) / indicators_length) * 100))
            # Flattens list of lists
            self.data = list(itertools.chain.from_iterable(self.data)) if self.data else None
            for value in self.data:
                value['_id'] = {'indicator': value['indicator']['id'], 'country': value['country']['id'],
                                'year': value['date']}
                value['description'] = value['indicator']['value']
                del value['decimal']
                del value['indicator']
                del value['country']
                del value['date']
            self.state['begin_date'] = self.state['end_date']
            self.state['end_date'] += 1
            self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
        else:
            self.logger.info('Country indicators have not been updated since last data collection. The period '
                    'between checks will be shortened, since data is expected to be updated soon.')
            # Setting update frequency to a shorter time interval (data will be updated soon)
            self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
        self.state['data_elements'] = len(self.data)
        self.state['last_request'] = datetime.datetime.now()

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'country_indicators'.
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
