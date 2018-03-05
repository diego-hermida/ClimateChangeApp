import datetime
import itertools
import json
import requests

from data_gathering_subsystem.data_collector.data_collector import DataCollector
from pymongo import UpdateOne
from utilities.util import current_timestamp_utc

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _CountryIndicatorsDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                     log_to_telegram=log_to_telegram)
    return _singleton


class _CountryIndicatorsDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)
        self._finished_data_collection = False
        self._http_error = False

    def _restore_state(self):
        super()._restore_state()
        self.state['end_date'] = datetime.datetime.today().year - 1 if not self.state['end_date'] else self.state[
                'end_date']

    def _collect_data(self):
        """
            Obtains data from the World Bank API via HTTP requests.
            N * P requests are made (being N the number of indicators, and P the number of pages in which requests have
            been split)
            Indicators are read from configuration file (country_indicators.config)
        """
        super()._collect_data()
        self.data = []
        if self.state['indicator_index'] is None:
            url = self.config['VALIDATION_QUERY'].replace('{BEGIN_DATE}', str(self.state['begin_date'])).replace(
                    '{END_DATE}', str(self.state['end_date']))
            r = requests.get(url)
            validation_data = json.loads(r.content.decode('utf-8', errors='replace'))[1][0]
            self.advisedly_no_data_collected = validation_data['value'] is None
            if self.advisedly_no_data_collected:
                self.logger.info('Validation query succeeded and found suitable data to be collected.')
                self.logger.info('Collecting data from %d indicators.' % len(self.config['INDICATORS']))
        else:
            self.advisedly_no_data_collected = False
        if not self.advisedly_no_data_collected:
            indicators_length = len(self.config['INDICATORS'])
            if self.state['indicator_index'] is None:
                self.state['indicator_index'] = 0
            max_index = self.state['indicator_index'] + self.config['MAX_INDICATORS_PER_EXECUTION']
            if max_index >= indicators_length:
                max_index = indicators_length
                self._finished_data_collection = True
                self.logger.debug('This execution should collect data from the latest indicators.')
            self.config['INDICATORS'] = self.config['INDICATORS'][self.state['indicator_index']:max_index]
            indicators_length = len(self.config['INDICATORS'])
            self.logger.info('In the current execution, collecting data from %d indicators: %s' %
                    (len(self.config['INDICATORS']), self.config['INDICATORS']))
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
                    # Skipping failed requests FIXES [BUG-030].
                    if r.status_code == 200:
                        metadata = json.loads(r.content.decode('utf-8', errors='replace'))[0]
                        temp_data = json.loads(r.content.decode('utf-8', errors='replace'))[1]
                        remaining_data = not metadata['page'] == metadata['pages']  # True if this page is last page
                        self.logger.debug('Collected %d elements for indicator "%s". Current page is %d (out of %d).'%
                                (len(temp_data), indicator, metadata['page'], metadata['pages']))
                        self.data.append(temp_data)
                        page += 1
                    else:
                        self.logger.warning('Data for indicator "%s" could not be retrieved.' % indicator)
                        remaining_data = False
                        self._http_error = True
                        continue
                self.logger.debug('Data collected: %0.2f%%'%(((index + 1) / indicators_length) * 100))
            # Flattens list of lists
            self.data = list(itertools.chain.from_iterable(self.data)) if self.data else []
            # Removing the "_id" field FIXES [BUG-032].
            for value in self.data:
                value['indicator'] = value['indicator']['id']
                value['country_id'] = value['country']['id']
                value['year'] = value['date']
                del value['decimal']
                del value['country']
                del value['date']
            if self._http_error and not self.data:
                self.logger.info('Since data could not be retrieved due to World Bank API errors, data collection will'
                        ' be omitted.')
                self.advisedly_no_data_collected = True
            if not self._finished_data_collection:
                self.state['update_frequency'] = self.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY']
                self.state['indicator_index'] += self.config['MAX_INDICATORS_PER_EXECUTION']
            else:
                self.logger.info('Data collection has finished for all indicators.')
                self.state['begin_date'] = self.state['end_date']
                self.state['end_date'] += 1
                self.state['indicator_index'] = None
                self.state['update_frequency'] = self.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'] if self.state[
                        'end_date'] <= (datetime.datetime.today().year - 1) else self.config['MAX_UPDATE_FREQUENCY']
                if self.state['update_frequency'] == self.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY']:
                    self.logger.info('Since end year is prior to last year, data collection will be resumed in the next'
                                     ' execution from that year: %d' % self.state['begin_date'])
        else:
            self.logger.info('Country indicators have not been updated since last data collection. The period '
                    'between checks will be shortened, since data is expected to be updated soon.')
            # Setting update frequency to a shorter time interval (data will be updated soon)
            self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
        self.state['data_elements'] = len(self.data)
        self.state['last_request'] = current_timestamp_utc()
        self.data = self.data if self.data else None

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
                operations.append(UpdateOne({'indicator': value['indicator'], 'country_id': value['country_id'], 'year':
                        value['year']}, update={'$setOnInsert': value}, upsert=True))
            result = self.collection.collection.bulk_write(operations)
            self.state['inserted_elements'] = result.bulk_api_result['nInserted'] + result.bulk_api_result['nMatched'] \
                    + result.bulk_api_result['nUpserted']
            if self.state['inserted_elements'] == len(self.data):
                self.logger.debug('Successfully inserted %d elements into database.'%(self.state['inserted_elements']))
            elif (self.state['data_elements'] - self.state['inserted_elements']) * 10 > self.state['data_elements']:
                self.logger.error('Since uninserted elements(s) > 10%% (%d out of %d), data collection will be '
                        'aborted.'%((self.state['data_elements'] - self.state['inserted_elements']),
                        self.state['data_elements']))
                raise Exception('Data collection has been aborted. Insufficient saved values.')
            else:
                self.logger.warning('Some elements were not inserted (%d out of %d)'%(self.state['inserted_elements'],
                        self.state['data_elements']))
            self.collection.close()
            self.data = None  # Allowing GC to collect data object's memory
        else:
            self.logger.info('No elements were saved because no elements have been collected.')
            self.state['inserted_elements'] = 0


if __name__ == '__main__':
    instance().run()