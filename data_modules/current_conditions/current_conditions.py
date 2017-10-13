# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains weather conditions data from the Open Weather Map via HTTP requests.
        M requests are made each time this function is called (M = max queries/min)
        Parameters are read from configuration file (weather_forecast.config)
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

from util.db_util import connect
from util.util import get_config, get_module_name

__config = get_config(__file__)
__module_name = get_module_name(__file__)


def __get_data():
    data = []
    requests_count = 0
    max_requests = __config['MAX_REQUESTS_PER_MINUTE']
    while requests_count < max_requests:
        url = __config['BASE_URL'].replace('{TOKEN}', __config['TOKEN']).replace('{LOC}', __config['LOC']).replace(
            '{COUNTRY}', __config['COUNTRY'])
        r = requests.get(url)
        data.append(json.loads(r.content.decode('utf-8')))
        requests_count += 1
    return data


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)
