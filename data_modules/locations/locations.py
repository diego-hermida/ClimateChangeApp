import datetime
import json
import requests
import zipfile

from data_collector.data_collector import DataCollector
from io import BytesIO
from pymongo import UpdateOne
from pytz import UTC
from unidecode import unidecode
from utilities.db_util import MongoDBCollection
from utilities.util import check_coordinates, date_to_millis_since_epoch, deserialize_date, MeasureUnits, serialize_date

__singleton = None


def instance(log_to_file=True, log_to_stdout=True) -> DataCollector:
    global __singleton
    if not __singleton or __singleton and __singleton.finished_execution():
        __singleton = __LocationsDataCollector(log_to_file=log_to_file, log_to_stdout=log_to_stdout)
    return __singleton


class __LocationsDataCollector(DataCollector):

    def __init__(self, log_to_file=True, log_to_stdout=True):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout)

    def _restore_state(self):
        """
            Deserializes GeoNames file's 'last-modified' date.
        """
        super()._restore_state()
        self.state['last_modified'] = deserialize_date(self.state['last_modified'])

    def _collect_data(self):
        """
            Collects data from GeoNames.org via HTTP requests. A single request is performed, and a .zip file is
            downloaded. Files are not written to disk, all operations are in-memory.
            Locations are filtered according to the values of LOCATIONS (.config file)
        """
        super()._collect_data()
        url = self.config['BASE_URL'] + self.config['ZIP_FILE']
        r = requests.get(url)
        last_modified = None
        # Downloaded file is compressed in a .zip file, which contains a single .txt file.
        zf = zipfile.ZipFile(BytesIO(r.content))
        for info in zf.infolist():
            last_modified = datetime.datetime(
                    *info.date_time + (1,), tzinfo=UTC)  # Adding 1 millisecond (date_format compatibility)
            break
        self.data = []
        unmatched = []
        unmatched_waqi = []
        multiple_waqi = []
        multiple = []
        # Collecting data only if file has been modified
        if True if not self.state['last_modified'] or not last_modified else last_modified > self.state['last_modified']:
            # Optimization: Only updating missing locations.
            self.collection = MongoDBCollection(self.module_name)
            missing_locations = self.collection.find(fields={'name': 1}, conditions={'$and': [{'waqi_station_id':
                    {'$ne': None}}, {'wunderground_loc_id': {'$ne': None}}, {'owm_station_id': {'$ne': None}}]}, sort='_id')
            self.collection.close()
            omitted = 0
            locations_length = len(self.config['LOCATIONS'])
            for loc in missing_locations['data']:
                try:
                    del self.config['LOCATIONS'][loc['name']]
                    omitted += 1
                except KeyError:
                    pass
            if omitted and omitted == locations_length:
                self.logger.info('Stopping data collection, since all locations are up to date.')
                self.advisedly_no_data_collected = True
                self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
            elif omitted:
                self.logger.info('%d locations were omitted, since they are up to date.' % (omitted))
            else:
                self.logger.info('Collecting data for all locations.')
            index = 1
            locations_length = len(self.config['LOCATIONS'])
            for location in self.config['LOCATIONS']:
                loc = self.config['LOCATIONS'][location]
                loc['missing'] = True
            with zf.open(self.config['FILE']) as f:
                for line in f:
                    fields = line.decode('utf-8').replace('\n', '').split('\t')
                    # Filtering locations to monitored locations
                    loc = self.config['LOCATIONS'].get(fields[1], None)
                    if loc:
                        date = date_to_millis_since_epoch(datetime.datetime.strptime(fields[18], "%Y-%m-%d").replace(tzinfo=UTC))
                        location = {'name': fields[1], 'latitude': float(fields[4]), 'longitude': float(fields[5]),
                                'country_code': fields[8], 'population': fields[14], 'elevation': {'value': fields[15],
                                'units': MeasureUnits.m}, 'timezone': fields[17], 'last_modified': date, '_id':
                                loc['_id']}
                        loc['name'] = location['name']
                        if self.__is_selected_location(loc['name'], loc['country_code'], loc['latitude'],
                                loc['longitude'], location['name'], location['country_code'], location['latitude'],
                                location['longitude']):
                            loc['missing'] = False

                            # Finding Station ID for Wunderground API requests
                            r = requests.get(self.config['URL_WUNDERGROUND'] + unidecode(loc['name'].split(',')[0]) +
                                    '&c=' + loc['country_code'])
                            # Filtering results by proximity, to avoid saving false positives
                            matches = None
                            try:
                                matches = [x for x in json.loads(r.content.decode('utf-8', errors='replace'))[
                                        'RESULTS'] if check_coordinates(float(loc['latitude']), float(loc['longitude']),
                                        float(x['lat']), float(x['lon']), margin=0.35)]
                                if len(matches) > 1:
                                    multiple.append(loc['name'])
                                elif not matches:
                                    unmatched.append(loc['name'])
                            # Adding json.decoder.JSONDecodeError FIXES: [BUG-020]
                            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                                unmatched.append(location['name'])
                            location['wunderground_loc_id'] = matches[0]['l'] if matches else None

                            # Finding Station ID for WAQI API requests
                            r = requests.get(self.config['URL_WAQI'].replace('{LOC}', unidecode(loc['name'].split(',')[0])))
                            temp = json.loads(r.content.decode('utf-8', errors='replace'))
                            matches = None
                            try:
                                if temp['status'] == 'ok':
                                    # Filtering results by proximity, to avoid saving false positives
                                    matches = [x for x in temp['data'] if check_coordinates(float(loc['latitude']),
                                            float(loc['longitude']), float(x['station']['geo'][0]), float(x['station']
                                            ['geo'][1]), margin=0.35)]
                                    if len(matches) > 1:
                                        multiple_waqi.append(loc['name'])
                                    elif not matches:
                                        unmatched_waqi.append(loc['name'])
                            # Adding json.decoder.JSONDecodeError FIXES: [BUG-020]
                            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                                unmatched.append(location['name'])
                            location['waqi_station_id'] = matches[0]['uid'] if matches else None

                            self.data.append(location)
                            if index > 0 and index % 10 is 0:
                                self.logger.debug('Collected data: %.2f%%'%(((index / locations_length) * 100)))
                            index += 1
            if multiple:
                self.logger.warning('%d location(s) have multiple matches at Wunderground API. As a result, API requests '
                        'might not be accurate for the following location(s): %s'%(len(multiple), sorted(multiple)))
            if unmatched:
                self.logger.warning('%d location(s) have no matches at Wunderground API. As a result, historical weather '
                        'will not be available for the following location(s): %s' % (len(unmatched), sorted(unmatched)))
            if multiple_waqi:
                self.logger.warning('%d location(s) have multiple matches at WAQI API. As a result, API requests might '
                        'not be accurate for the following location(s): %s'%(len(multiple_waqi), sorted(multiple_waqi)))
            if unmatched_waqi:
                self.logger.warning('%d location(s) have no matches at WAQI API. As a result, air pollution data will not'
                        ' be available for the following location(s): %s' % (len(unmatched_waqi), sorted(unmatched_waqi)))
            unmatched.clear()
            multiple.clear()

            # Finding Station ID for Open Weather Map API requests
            r = requests.get(self.config['URL_OPEN_WEATHER'])
            open_weather_data = r.content.decode('utf-8', errors='replace').split('\n')
            # Sorting locations by country code (as in 'open_weather_data')
            locations = sorted([x for x in list(self.config['LOCATIONS'].values()) if not x.get('missing', True)], key=lambda k: k['country_code'])
            for loc in locations:
                loc['name'] = unidecode(loc['name'])
            for line in open_weather_data[1:-1]:
                values = line.split('\t')
                loc = None
                for location in locations:
                    if location['name'].split()[0] in values[1]:
                        loc = location
                        break
                if loc is None:
                    continue
                # Filtering results by proximity and country, to avoid saving false positives
                loc['owm_station_id'] = values[0] if check_coordinates(loc['latitude'], loc['longitude'], float(
                        values[2]), float(values[3]), margin=0.35) and loc['country_code'] == values[4] else None
                if loc['owm_station_id']:
                    locations.remove(loc) # Removing found location (so that false positives cannot overwrite the ID)
            for loc in self.data:
                loc['owm_station_id'] = self.config['LOCATIONS'][loc['name']].get('owm_station_id', None)
                if loc['owm_station_id'] is None:
                    unmatched.append(loc['name'])
            if unmatched:
                self.logger.warning('%d location(s) have no matches at OpenWeatherMap API. As a result, current weather '
                        'and weather forecast data will not be available for the following location(s): %s'%
                        (len(unmatched), sorted(unmatched)))

            unmatched.clear()
            # Debug info (Locations in location list but not added will be logged)
            for name in self.config['LOCATIONS']:
                loc = self.config['LOCATIONS'][name]
                if loc['missing']:
                    unmatched.append(name)
            if unmatched:
                self.logger.warning('Unable to find %d location(s): %s'%(len(unmatched), sorted(unmatched)))
            self.logger.info('GeoNames file "%s" has been correctly parsed. %d location(s) (out of %d) were found.'%
                    (self.config['FILE'], len(self.data), len(self.config['LOCATIONS'])))
            # Restoring original update frequency
            self.state['update_frequency'] = self.config['MAX_UPDATE_FREQUENCY']
            self.state['last_modified'] = last_modified
        else:
            self.logger.info('GeoNames file has not been updated since last data collection. The period '
                             'between checks will be shortened, since data is expected to be updated soon.')
            # Setting update frequency to a shorter time interval (file is near to be modified)
            self.state['update_frequency'] = self.config['MIN_UPDATE_FREQUENCY']
            self.advisedly_no_data_collected = True
        self.state['last_request'] = datetime.datetime.now(tz=UTC)
        self.state['data_elements'] = len(self.data)
        self.data = self.data if self.data else None

    def _save_data(self):
        """
            Saves collected data (stored in 'self.data' variable), into a MongoDB collection called 'locations'.
            Existent locations are updated with new values, and new ones are inserted as new ones.
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

    def _save_state(self):
        """
            Serializes GeoNames file's 'last-modified' date.
        """
        self.state['last_modified'] = serialize_date(self.state['last_modified'])
        super()._save_state()

    @staticmethod
    def __is_selected_location(loc_name: str, loc_cc: str, loc_lat: float, loc_long: float, data_name: str,
                               data_cc: str, data_lat: float, data_long: float, margin=1.0) -> bool:
        """
            Compares location data, both from '.config' file and downloaded data, in order to determine if data refers
            to the same location.
            :param loc_name: Name of the location from '.config' file.
            :param loc_cc: Country code of the location from '.config' file.
            :param loc_lat: Latitude of the location from '.config' file.
            :param loc_long: Longitude of the location from '.config' file.
            :param data_name: Name of the location from '.config' file.
            :param data_cc: Country code of the location from '.config' file.
            :param data_lat: Latitude of the location from '.config' file.
            :param data_long: Longitude of the location from '.config' file.
            :param margin: Maximum accepted difference (in absolute value) between latitudes and longitudes (in both
                           '.config' file and data).
            :return: True, if location names and country codes are the same, and latitudes/longitudes doesn't exceed
                     'margin' difference.
            :rtype: bool
        """
        return loc_name == data_name and loc_cc == data_cc and check_coordinates(loc_lat, loc_long, data_lat, data_long,
                margin=margin)

if __name__ == '__main__':
    instance().run()