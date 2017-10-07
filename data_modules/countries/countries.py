import json
import requests

from util.db_util import connect
from util.util import get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)


def get_data():
    """
        Obtains data from the World Bank API via HTTP requests. A single request is performed.

        Base URL is read from configuration file (countries.config)

        :return: A flat list of key-value objects, containing information from all countries.
        :rtype: list
    """
    url = config['BASE_URL'].replace('{LANG}', config['LANG'])
    r = requests.get(url)
    data = json.loads(r.content.decode('utf-8'))[1]  # Avoids saving indicator meta-info
    for value in data:  # Creates '_id' attribute and removes non-util fields
        value['_id'] = value['iso2Code']
        del value['id']
        del value['iso2Code']
        del value['adminregion']
        del value['lendingType']
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    save_data(data)
