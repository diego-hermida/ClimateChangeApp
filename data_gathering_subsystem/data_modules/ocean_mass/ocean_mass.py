import itertools

from data_gathering_subsystem.data_collector.data_collector import DataCollector, Reader
from ftplib import FTP
from pymongo import UpdateOne
from utilities.util import deserialize_date, serialize_date, decimal_date_to_millis_since_epoch, MassType, \
        MeasureUnits, current_timestamp_utc

_singleton = None


def instance(log_to_file=True, log_to_stdout=True) -> DataCollector:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _OceanMassDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout)
    return _singleton


class _OceanMassDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout)

    def _restore_state(self):
        """
            Deserializes 'last-modified' dates, one for each file.
        """
        super()._restore_state()
        self.state['antarctica']['last_modified'] = deserialize_date(self.state['antarctica']['last_modified'])
        self.state['greenland']['last_modified'] = deserialize_date(self.state['greenland']['last_modified'])
        self.state['ocean']['last_modified'] = deserialize_date(self.state['ocean']['last_modified'])

    def _collect_data(self):
        """
            Collects data from the NASA servers via FTP requests. Original files are available at:
            ftp://podaac.jpl.nasa.gov/allData/tellus/L3/mascon/RL05/JPL/CRI/mass_variability_time_series/
            This data collector gathers data from:
                - Antarctica ice mass.
                - Greenland ice mass.
                - Ocean sea mass.
        """
        super()._collect_data()
        ftp = FTP(self.config['URL'])
        ftp.login()
        ftp.cwd(self.config['DATA_DIR'])  # Accessing FTP directory

        file_names = sorted([x for x in ftp.nlst() if x.endswith(self.config['FILE_EXT'])])
        self.logger.info('%d file(s) were found under NASA FTP directory: %s'%(len(file_names), file_names))

        self.data = []
        not_modified = []
        for name in file_names:
            # Getting file's date modified
            last_modified = ftp.sendcmd('MDTM ' + name)
            last_modified = deserialize_date(
                    last_modified[4:] + '.' + last_modified[0:3],
                    date_format=self.config['FTP_DATE_FORMAT'])
            try:
                type_name = self._get_type(name)
            except ValueError:
                self.logger.debug('Omitting unnecessary file: %s'%(name))
                file_names.remove(name)
                continue
            # Collecting data only if file has been modified
            if True if not self.state[type_name]['last_modified'] or not last_modified else \
                    last_modified > self.state[type_name]['last_modified']:
                self._data_modified = True
                r = Reader()
                ftp.retrlines('RETR ' + name, r)
                temp_data = self._to_json(r.get_data(), type_name)
                self.data.append(temp_data)
                self.state[type_name]['last_modified'] = last_modified
                self.logger.debug('NASA file "%s" has been correctly parsed. %d measures have been collected.'%(name,
                        len(temp_data)))

                # Restoring original update frequency
                self.state[type_name]['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
            else:
                # Setting update frequency to a shorter time interval (file is near to be modified)
                self.state[type_name]['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
                not_modified.append(type_name)
        if not_modified:
            self.logger.info(('Some ' if len(not_modified) < len(file_names) else '') + 'NASA file(s) have not been '
                    'updated since last data collection: %s. The period between checks will be shortened, since data is'
                    ' expected to be updated soon.'%(not_modified))
        ftp.quit()
        self.state['last_request'] = current_timestamp_utc()
        self.data = list(itertools.chain.from_iterable(self.data))  # Flattens list of lists
        self.state['data_elements'] = len(self.data)
        if len(not_modified) < len(file_names):
            self.logger.info('NASA files have been correctly parsed. %d measures have been collected.'%(len(self.data)))
        else:
            self.advisedly_no_data_collected = True
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'ocean_mass'.
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
            Serializes 'last-modified' dates, one for each file.
        """
        self.state['antarctica']['last_modified'] = serialize_date(self.state['antarctica']['last_modified'])
        self.state['greenland']['last_modified'] = serialize_date(self.state['greenland']['last_modified'])
        self.state['ocean']['last_modified'] = serialize_date(self.state['ocean']['last_modified'])
        super()._save_state()

    @staticmethod
    def _to_json(data: list, data_type: MassType):
        """
            Converts all lines split from a NASA file into a valid JSON document.
            :param data: List of String values
            :param data_type: Each file has a different structure. This parameter ensures that JSON document is generated
                              with accuracy, referring to the true file.
            :return: A list, containing all data formatted as a JSON document.
        """
        json_data = []
        if data_type is MassType.ocean:
            for line in data:
                fields = line.split()
                date = decimal_date_to_millis_since_epoch(float(fields[0]))
                measure = {'_id': {'type': data_type, 'utc_date': date}, 'measures': []}
                measure['measures'].append({'height': fields[1], 'units': MeasureUnits.mm})
                measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.mm})
                measure['measures'].append({'height_deseasoned': fields[3], 'units': MeasureUnits.mm})
                json_data.append(measure)
        else:
            for line in data:
                fields = line.split()
                date = decimal_date_to_millis_since_epoch(float(fields[0]))
                measure = {'_id': {'type': data_type, 'utc_date': date}, 'measures': []}
                measure['measures'].append({'mass': fields[1], 'units': MeasureUnits.Gt})
                measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.Gt})
                json_data.append(measure)
        return json_data

    @staticmethod
    def _get_type(file_name) -> MassType:
        """
            Given a file name, gets its MassType.
        """
        if MassType.antarctica in file_name:
            return MassType.antarctica
        elif MassType.greenland in file_name:
            return MassType.greenland
        elif MassType.ocean in file_name:
            return MassType.ocean
        else:
            raise ValueError('No MassType matched with file name: %s'%(file_name))
