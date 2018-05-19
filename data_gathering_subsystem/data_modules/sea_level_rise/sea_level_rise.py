from ftplib import FTP
from pymongo import UpdateOne
from data_gathering_subsystem.data_collector.data_collector import DataCollector, Reader
from utilities.util import decimal_date_to_millis_since_epoch, serialize_date, deserialize_date, MeasureUnits, \
    current_timestamp

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _SeaLevelDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                            log_to_telegram=log_to_telegram)
    return _singleton


class _SeaLevelDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _restore_state(self):
        """
            Deserializes NASA file's 'last-modified' date.
        """
        super()._restore_state()
        self.state['last_modified'] = deserialize_date(self.state['last_modified'])

    def _collect_data(self):
        """
            Collects data from the NASA servers via FTP requests. Original files are available at:
            ftp://podaac.jpl.nasa.gov/allData/merged_alt/L2/TP_J1_OSTM/global_mean_sea_level/
            This data collector gathers data from:
                - Global mean sea level.
        """
        super()._collect_data()
        ftp = FTP(self.config['URL'], timeout=self.config['FTP_TIMEOUT'])
        ftp.login()
        ftp.cwd(self.config['DATA_DIR'])  # Accessing directory

        # File name changes every month, but it always starts with GMSL
        file_names = [x for x in ftp.nlst() if x.startswith('GMSL_TPJAOS') and x.endswith(self.config['FILE_EXT'])]
        self.logger.info('%d file(s) were found under NASA FTP directory: %s'%(len(file_names), file_names))

        # Getting file's date modified
        last_modified = ftp.sendcmd('MDTM ' + file_names[0])
        last_modified = deserialize_date(
                last_modified[4:] + '.' + last_modified[0:3],
                date_format=self.config['FTP_DATE_FORMAT'])

        self.data = []
        # Collecting data only if file has been modified
        if True if not self.state['last_modified'] or not last_modified else \
                last_modified > self.state['last_modified']:
            self._data_modified = True
            r = Reader()
            ftp.retrlines('RETR ' + file_names[0], r)
            self.data = self._to_json(r.get_data())
            self.state['last_modified'] = last_modified
            self.logger.debug('NASA file "%s" has been correctly parsed. %d measures have been collected.'%
                    (self.config['FILE_NAME'], len(self.data)))
            # Restoring original update frequency
            self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
        else:
            self.logger.info('NASA file has not been updated since last data collection. The period '
                             'between checks will be shortened, since data is expected to be updated soon.')
            # Setting update frequency to a shorter time interval (file is near to be modified)
            self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
            self.advisedly_no_data_collected = True
        ftp.quit()
        self.state['last_request'] = current_timestamp(utc=True)
        self.state['data_elements'] = len(self.data)
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'global__sea_level_rise'.
            Existent records are not updated, and new ones are inserted as new ones.
            Postcondition: 'self.data' variable is dereferenced to allow GC to free up memory.
        """
        super()._save_data()
        if self.data:
            operations = []
            for value in self.data:
                operations.append(UpdateOne({'time_utc': value['time_utc']}, update={'$setOnInsert': value}, upsert=True))
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

    def _save_state(self):
        """
           Serializes NASA file's 'last-modified' date.
        """
        self.state['last_modified'] = serialize_date(self.state['last_modified'])
        super()._save_state()

    def _to_json(self, data):
        """
            Converts all lines split from a NASA file into a valid JSON document.
            :param data: List of String values
            :return: A list, containing all data formatted as a JSON document.
        """
        json_data = []
        for line in data:
            fields = line.split()
            altimeter = 'dual_frequency' if fields[0] == 0 else 'single_frequency'
            # Removing the "_id" field FIXES [BUG-032].
            measure = {'time_utc': decimal_date_to_millis_since_epoch(float(fields[2])), 'altimeter': altimeter,
                    'observations': fields[3], 'weighted_observations': fields[4], 'measures': {}, 
                    'units': MeasureUnits.mm}
            measure['measures']['variation'] = fields[5]
            measure['measures']['deviation'] = fields[6]
            measure['measures']['smoothed_variation'] = fields[7]
            measure['measures']['variation_GIA'] = fields[8]
            measure['measures']['deviation_GIA'] = fields[9]
            measure['measures']['smoothed_variation_GIA'] = fields[10]
            measure['measures']['smoothed_variation_GIA_annual_&_semi_annual_removed'] = fields[11]
            json_data.append(measure)
        return json_data
