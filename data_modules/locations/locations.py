import datetime
import requests
import zipfile

from io import BytesIO
from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name, MeasureUnits, \
    read_state, serialize_date, deserialize_date, worktime, write_state

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __LocationsDataCollector()
    return __singleton


class __LocationsDataCollector(DataCollector):
    def __init__(self):
        super().__init__()
        self.__data = None
        self.__state = None
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def restore_state(self):
        """
           Restores previous saved state (.state) if valid. Otherwise, creates a valid structure
           for .state file from the STATE_STRUCT key in .config file.
        """
        self.__state = read_state(__file__, repair_struct=self.__config['STATE_STRUCT'])
        self.__state['last_request'] = deserialize_date(self.__state['last_request'])
        self.__state['last_modified'] = deserialize_date(self.__state['last_modified'])

    def worktime(self) -> bool:
        """
            Determines whether this module is ready or not to perform new work, according to update policy and
            last request's timestamp.
            :return: True if it's work time, False otherwise.
            :rtype: bool
        """
        return worktime(self.__state['last_request'], self.__state['update_frequency'])

    def collect_data(self):
        """
            Obtains data from GeoNames.org via HTTP requests. A single request is performed, and a .zip file is obtained.
            Files are not written to disk, all operations are in-memory.
            Parameters are read from configuration file (locations.config), and locations are filtered according to
            values in LOCATIONS key (.config file)
        """
        url = self.__config['BASE_URL'] + self.__config['ZIP_FILE']
        r = requests.get(url)
        zf = zipfile.ZipFile(BytesIO(r.content))  # Downloaded file is compressed in a .zip file.
        for info in zf.infolist():
            last_modified = datetime.datetime(
                *info.date_time + (1,))  # Adding 1 millisecond (date_format compatibility)
            break
        if True if self.__state['last_modified'] is None else last_modified > self.__state[
            'last_modified']:  # Collecting data only if file has been modified
            self.__data = []
            with zf.open(self.__config['FILE']) as f:
                auto_increment_id = 1
                for line in f:
                    fields = line.decode('utf-8').replace('\n', '').split('\t')
                    # Converting date from "yyyy-mm-dd" to "dd-mm-yyyy"
                    date = datetime.datetime.strptime(fields[18], "%Y-%m-%d").strftime("%d-%m-%Y")
                    location = {'name': fields[1], 'latitude': float(fields[4]), 'longitude': float(fields[5]),
                                'country_code': fields[8],
                                'population': fields[14], 'elevation': {'value': fields[15], 'units': MeasureUnits.m},
                                'timezone': fields[17], 'last_modified': date}
                    # Filtering locations to monitored locations
                    loc = self.__config['LOCATIONS'].get(location['name'], None)
                    if loc is not None:
                        loc['name'] = location['name']
                        if self.__is_selected_location(loc['name'], loc['country_code'], loc['latitude'],
                                                       loc['longitude'], location['name'], location['country_code'],
                                                       location['latitude'], location['longitude']):
                            loc['OK'] = True  # Debug-only
                            location['_id'] = auto_increment_id
                            auto_increment_id += 1
                            self.__data.append(location)
            self.__state['last_modified'] = last_modified
        self.__state['last_request'] = datetime.datetime.now()
        self.__data = self.__data if self.__data else None
        # Debug info (Locations in location list but not added will be printed)
        for name in self.__config['LOCATIONS']:
            location = self.__config['LOCATIONS'][name]
            if not location.get('OK', False):
                print('[WARNING]\t' + name + ', ' + location['country_code'] + ' (' + str(location['latitude'])
                      + ', ' + str(location['longitude']) + ') was not found at: ' + url + ' (last modified: '
                      + serialize_date(last_modified) + ')')

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        if self.__data is None:
            pass
        else:
            connection = connect(self.__module_name)
            connection.insert_many(self.__data)

    def save_state(self):
        """
            Serializes state to .state file in such a way that can be deserialized later.
        """
        self.__state['last_request'] = serialize_date(self.__state['last_request'])
        self.__state['last_modified'] = serialize_date(self.__state['last_modified'])
        write_state(self.__state, __file__)

    @staticmethod
    def __is_selected_location(loc_name: str, loc_cc: str, loc_lat: float, loc_long: float, data_name: str, data_cc: str,
                             data_lat: float, data_long: float) -> bool:
        return loc_name == data_name and loc_cc == data_cc and \
               abs(loc_lat - data_lat) < 1 and abs(loc_long - data_long) < 1

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'
