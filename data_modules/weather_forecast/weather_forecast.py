import json

import requests

from util.db_util import connect
from util.util import get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)


def get_data():
    """
        Obtains weather forecast data from the Open Weather Map via HTTP requests.
        M requests are made each time this function is called (M = max queries/min)

        Parameters are read from configuration file (weather_forecast.config)

        :return: A flat list of key-value objects.
        :rtype: list
    """
    data = []
    requests_count = 0
    max_requests = config['MAX_REQUESTS_PER_MINUTE']
    while requests_count < max_requests:
        url = config['BASE_URL'].replace('{TOKEN}', config['TOKEN']).replace('{LOC}', config['LOC']).replace(
            '{COUNTRY}', config['COUNTRY'])
        r = requests.get(url)
        data.append(json.loads(r.content.decode('utf-8')))
        requests_count += 1
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    save_data(data)
