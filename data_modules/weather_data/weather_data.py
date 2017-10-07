import json
import requests

from util.db_util import connect
from util.util import get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)


def get_data():
    """
        Obtains data from the Wunderground API via HTTP requests. Currently only historical data is gathered.
        N * M requests are made each time this function is called (N = number of tokens, M = max queries/min per token)

        Parameters are read from configuration file (weather_data.config)

        :return: A flat list of key-value objects.
        :rtype: list
    """
    data = []
    for token in config['TOKENS'] * config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']:
        # TODO: By adding /conditions/forecast to BASE_URL gets more data in a single request
        url = config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}', config['DATE']).replace('{LANG}',
            config['LANG']).replace('{STATE|COUNTRY}', config['COUNTRY']).replace('{CITY}', config['CITY'])
        r = requests.get(url)
        data.append(json.loads(r.content.decode('utf-8'))['history'])
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    save_data(data)
