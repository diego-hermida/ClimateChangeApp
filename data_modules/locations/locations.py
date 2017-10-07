import datetime
import requests
import zipfile

from io import BytesIO
from util.db_util import connect
from util.util import enum, get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)
MeasureUnits = enum('m')


def get_data():
    """
        Obtains data from GeoNames.org via HTTP requests. A single request is performed, and a .zip file is obtained.
        Files are not written to disk, all operations are in-memory.

        Parameters are read from configuration file (locations.config)

        :return: A flat list of key-value objects, containing information from all locations with population > 1000.
        :rtype: list
    """
    url = config['BASE_URL'] + config['ZIP_FILE']
    r = requests.get(url)
    data = []
    with zipfile.ZipFile(BytesIO(r.content)).open(config['FILE']) as f:
        for line in f:
            fields = line.decode('utf-8').replace('\n', '').split('\t')
            # Converting date from "yyyy-mm-dd" to "dd-mm-yyyy"
            year = datetime.datetime.strptime(fields[18], "%Y-%m-%d").strftime("%d-%m-%Y")
            location = {'name': fields[1], 'latitude': fields[4], 'longitude': fields[5], 'country_code': fields[8],
                        'population': fields[14], 'elevation': {'value': fields[15], 'units': MeasureUnits.m},
                        'timezone': fields[17], 'last_modified': year}
            data.append(location)
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    save_data(data)
