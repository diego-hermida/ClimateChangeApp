import datetime
import json
import requests

from utilities.db_util import connect, find
from utilities.util import DataCollector, get_config, get_module_name, worktime, read_state, write_state, \
    serialize_date, deserialize_date

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __AirPollutionDataCollector()
    return __singleton


class __AirPollutionDataCollector(DataCollector):
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
            Obtains data from the WAQI API via HTTP requests.
            L requests are made each time this function is called (L = number of locations)
            Parameters are read from configuration file (air_pollution.config)
        """
        locations = find(self.__config['LOCATIONS_MODULE_NAME'], last_id=10,
                         count=self.__config['MAX_REQUESTS_PER_MINUTE'],
                         fields={'_id': 1, 'latitude': 1, 'longitude': 1})
        self.__data = []
        for location in locations['data']:
            url = self.__config['BASE_URL'].replace('{LAT}', str(location['latitude'])). \
                replace('{LONG}', str(location['longitude'])).replace('{TOKEN}', self.__config['TOKEN'])
            r = requests.get(url)
            temp = json.loads(r.content.decode('utf-8'))
            # Adding only verified data
            if temp['status'] == 'ok' and temp['data']['city']['geo'] and self.__check_coords(
                    temp['data']['city']['geo'][0], temp['data']['city']['geo'][1], location['latitude'],
                    location['longitude']):
                temp['location_id'] = location['_id']
                self.__data.append(temp)
        self.__state['last_id'] = locations['data'][-1]['_id'] if locations['more'] else None
        self.__state['last_request'] = datetime.datetime.now()
        self.__state['update_frequency'] = self.__config['MIN_UPDATE_FREQUENCY'] if locations['more'] \
            else self.__config['MAX_UPDATE_FREQUENCY']
        self.__data = self.__data if self.__data else None
        # TODO: Check errors. Examples:
        #   - {"status":"error","data":"Invalid key"}
        #   - {"status":"error","message":"404"}

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
        write_state(self.__state, __file__)

    @staticmethod
    def __check_coords(loc_lat: float, loc_long: float, data_lat: float, data_long: float, margin=1) -> bool:
        """
        Compares the coordinates of the weather stations with locations' ones, in order to ensure proximity between
        weather stations and locations.
        :param loc_lat: Location's latitude
        :param loc_long: Location's longitude
        :param data_lat: Weather station's latitude
        :param data_long: Weather stations' longitude
        :param margin: Maximum error margin to be accepted (an error > margin returns False).
        :return: True if difference between coordinates is less than margin, False otherwise.
        :rtype: bool
        """
        return abs(loc_lat - data_lat) <= margin and abs(loc_long - data_long) <= margin

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'
