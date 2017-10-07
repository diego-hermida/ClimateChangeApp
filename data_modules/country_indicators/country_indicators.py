import itertools
import json
import requests

from util.db_util import connect
from util.util import get_config, get_module_name

config = get_config(__file__)
module_name = get_module_name(__file__)


def get_data():
    """
        Obtains data from the World Bank API via HTTP requests.
        N * M requests are made each time this function is called (M = number of indicators, N = number of countries)

        Indicators and countries are both read from configuration file (country_indicators.config)

        :return: A flat list of key-value objects, containing information from all indicators.
        :rtype: list
    """
    data = []
    for indicator in config['INDICATORS']:
        for country in config['COUNTRIES']:
            url = config['BASE_URL'].replace('{LANG}', config['LANG']).replace('{COUNTRY}', country).replace(
                '{INDICATOR}', indicator).replace('{BEGIN_DATE}', str(config['BEGIN_DATE'])).replace(
                '{END_DATE}', str(config['END_DATE']))
            r = requests.get(url)
            data.append(json.loads(r.content.decode('utf-8'))[1])  # Avoids saving indicator meta-info
            break
    data = list(itertools.chain.from_iterable(data))  # Flattens the list of lists
    for value in data:  # Creates '_id' attribute and removes non-util fields
        value['_id'] = value['indicator']['id'] + '_' + value['country']['id'] + '_' + value['date']
        del value['decimal']
    return data


def save_data(data):
    connection = connect(module_name)
    connection.insert_many(data)


if __name__ == '__main__':
    data = get_data()
    save_data(data)
