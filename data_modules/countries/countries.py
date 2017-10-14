# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def get_data():
    """
        Obtains data from the World Bank API via HTTP requests. A single request is performed.
        Base URL is read from configuration file (countries.config)
        :return: A flat list of key-value objects, containing information from all countries.
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
    url = __config['BASE_URL'].replace('{LANG}', __config['LANG'])
    r = requests.get(url)
    data = json.loads(r.content.decode('utf-8'))[1]  # Avoids saving indicator meta-info
    for value in data:  # Creates '_id' attribute and removes non-utilities fields
        value['_id'] = value['id']
        del value['id']
        del value['adminregion']
        del value['lendingType']
    return data


def __save_data(data):
    connection = connect(__module_name)
    connection.insert_many(data)

if __name__ == '__main__':
    data = get_data()
    save_data(data)