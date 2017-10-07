import json
import requests

from util.db_util import connect
from util.util import get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)


def get_data():
    """
        Obtains data from the WAQI API via HTTP requests.
        L requests are made each time this function is called (L = number of locations)

        Parameters are read from configuration file (air_pollution.config)

        :return: A flat list of key-value objects.
        :rtype: list
    """
    data = []
    for loc in config['LOCATIONS']:
        url = config['BASE_URL'].replace('{LOC}', loc) + config['TOKEN']
        r = requests.get(url)
        data.append(json.loads(r.content.decode('utf-8')))
    return data

    # TODO: Check errors. Examples:
    # TODO:  - [b'{"status":"error","data":"Invalid key"}', b'{"status":"error","data":"Invalid key"}']
    # TODO:  - [b'{"status":"error","message":"404"}', b'{"status":"error","message":"404"}']


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    with open('file.txt', 'w') as f:
        f.write(json.dumps(data, indent=4, separators=(',', ': ')))
    #save_data(data)
