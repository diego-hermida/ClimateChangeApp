import requests

from util.util import get_config

config = get_config(__file__)


def get_data():
    data = {}
    for indicator in config['INDICATORS']:
        indicator_data = []
        for country in config['COUNTRIES']:
            url = config['BASE_URL'].replace('{LANG}', config['LANG']).replace('{COUNTRY}', country).replace(
                '{INDICATOR}', indicator).replace('{BEGIN_DATE}', config['BEGIN_DATE']).replace('{END_DATE}',
                config['END_DATE'])
            r = requests.get(url)
            indicator_data.append(r.content)
        data[indicator] = indicator_data
    return data


if __name__ == '__main__':
    data = get_data()
