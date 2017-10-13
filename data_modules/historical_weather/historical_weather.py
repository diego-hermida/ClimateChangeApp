# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the Wunderground API via HTTP requests. Currently only historical data is gathered.
        N * M requests are made each time this function is called (N = number of tokens, M = max queries/min per token)
        Parameters are read from configuration file (historical_weather.config)
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
    for token in __config['TOKENS'] * __config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
        url = __config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}', __config['DATE']).replace(
            '{LANG}', __config['LANG']).replace('{STATE|COUNTRY}', __config['COUNTRY']).replace('{LOC}',
                                                                                                __config['LOC'])
        r = requests.get(url)
        data.append(json.loads(r.content.decode('utf-8')))
    return data


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)
