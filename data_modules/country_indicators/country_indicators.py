# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the World Bank API via HTTP requests.
        N * M requests are made each time this function is called (M = number of indicators, N = number of countries)
        Indicators and countries are both read from configuration file (country_indicators.config)
        :return: A flat list of key-value objects, containing information from all indicators.
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

import itertools
import json
import requests

from utilities.db_util import connect
from utilities.util import get_config, get_module_name

__config = get_config(__file__)
__module_name = get_module_name(__file__)


def __get_data():
    data = []
    for indicator in __config['INDICATORS']:
        for country in __config['COUNTRIES']:
            url = __config['BASE_URL'].replace('{LANG}', __config['LANG']).replace('{COUNTRY}', country).replace(
                '{INDICATOR}', indicator).replace('{BEGIN_DATE}', str(__config['BEGIN_DATE'])).replace(
                '{END_DATE}', str(__config['END_DATE']))
            r = requests.get(url)
            data.append(json.loads(r.content.decode('utf-8'))[1])  # Avoids saving indicator meta-info
            break
    data = list(itertools.chain.from_iterable(data))  # Flattens the list of lists
    for value in data:  # Creates '_id' attribute and removes non-utilities fields
        value['_id'] = value['indicator']['id'] + '_' + value['country']['id'] + '_' + value['date']
        del value['decimal']
    return data


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)
