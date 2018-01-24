from datetime import datetime
from data_collector.data_collector import DataCollector
from global_config.global_config import CONFIG as GLOBAL_CONFIG
from pytz import UTC

__singleton = None


def instance(log_to_file=True, log_to_stdout=True) -> DataCollector:
    global __singleton
    if not __singleton or __singleton and __singleton.finished_execution():
        __singleton = __FutureEmissionsDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout)
    return __singleton


class __FutureEmissionsDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout)

    def _collect_data(self):
        """
            Collects data from the RPC Database. Data to be inserted has properly been converted and formatted.
            Original documents are available at: http://tntcat.iiasa.ac.at:8787/RcpDb/dsd?Action=htmlpage&page=download
        """
        super()._collect_data()
        self.data = []
        for file in self.config['FILE_NAMES']:
            with open(GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'] + self.config['DATA_DIR'] + file + self.config['FILE_EXT'],
                      'r') as f:
                for line in f:
                    fields = line.split()
                    d = {'_id': fields[0] + '_' + file, 'year': fields[0], 'scenario': file, 'measures': []}
                    for (index, value) in enumerate(fields[1:]):
                        measure = {'measure': self.config['MEASURES'][index], 'value': value,
                                   'units': self.config['UNITS'][index]}
                        d['measures'].append(measure)
                    self.data.append(d)
        self.state['update_frequency'] = self.config['UPDATE_FREQUENCY'] if self.data else self.config[
                'STATE_STRUCT']['update_frequency']
        self.state['last_request'] = datetime.now(UTC)
        self.state['data_elements'] = len(self.data)
        self.logger.info('RPC Database file(s) were correctly parsed. %d measures have been collected.'%(len(self.data)))
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'future_emissions'.
            Since no duplicates are allowed, collection is erased before saving data.
            Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.data:
            if not self.collection.is_empty():
                self.collection.remove_all()
                self.logger.debug('Cleared database collection so as to perform bulk-insert.')
            ids = self.collection.collection.insert_many(self.data)
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
