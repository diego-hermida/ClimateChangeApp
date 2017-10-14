import datetime
import requests
import zipfile

from io import BytesIO
from utilities.db_util import connect
from utilities.util import DataCollector, get_config, get_module_name, MeasureUnits

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __LocationsDataCollector()
    return __singleton


class __LocationsDataCollector(DataCollector):
    def __init__(self):
        super().__init__()
        self.__data = []
        self.__state = None
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def restore_state(self):
        pass

    def worktime(self) -> bool:
        pass

    def get_data(self):
        """
            Obtains data from GeoNames.org via HTTP requests. A single request is performed, and a .zip file is obtained.
            Files are not written to disk, all operations are in-memory.
            Parameters are read from configuration file (locations.config)
        """
        url = self.__config['BASE_URL'] + self.__config['ZIP_FILE']
        r = requests.get(url)
        with zipfile.ZipFile(BytesIO(r.content)).open(self.__config['FILE']) as f:
            for line in f:
                fields = line.decode('utf-8').replace('\n', '').split('\t')
                # Converting date from "yyyy-mm-dd" to "dd-mm-yyyy"
                year = datetime.datetime.strptime(fields[18], "%Y-%m-%d").strftime("%d-%m-%Y")
                location = {'name': fields[1], 'latitude': fields[4], 'longitude': fields[5], 'country_code': fields[8],
                            'population': fields[14], 'elevation': {'value': fields[15], 'units': MeasureUnits.m},
                            'timezone': fields[17], 'last_modified': year}
                self.__data.append(location)

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass


