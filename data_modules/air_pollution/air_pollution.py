# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the WAQI API via HTTP requests.
        L requests are made each time this function is called (L = number of locations)
        Parameters are read from configuration file (air_pollution.config)
        :return: A flat list of key-value objects.
        :rtype: list
    """
    return __get_data()


def save_data(data):
    """
       Saves data into a persistent storage system (Currently, a MongoDB instance).
       Data is saved in a collection with the same name as the module.
       :param data: A list of values to persist, which might be empty.
    """
    __save_data(data)


# ---------------------------------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------------------------------

import json
import requests

from utilities.db_util import connect
from utilities.util import get_config, get_module_name

__config = get_config(__file__)
__module_name = get_module_name(__file__)


def __get_data():
    data = []
    for loc in __config['LOCATIONS']:
        url = __config['BASE_URL'].replace('{LOC}', loc) + __config['TOKEN']
        r = requests.get(url)
        data.append(json.loads(r.content.decode('utf-8')))
    return data

    # TODO: Check errors. Examples:
    # TODO:  - [b'{"status":"error","data":"Invalid key"}', b'{"status":"error","data":"Invalid key"}']
    # TODO:  - [b'{"status":"error","message":"404"}', b'{"status":"error","message":"404"}']


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)
