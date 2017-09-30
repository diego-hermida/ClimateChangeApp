import requests

from util.util import get_config

config = get_config(__file__)


def get_data():
    data = []
    token_iter = iter(config['TOKENS'])
    token = next(token_iter)

    url = config['BASE_URL'].replace('{TOKEN}', token).replace('{YYYYMMDD}', config['DATE']).replace('{LANG}', config[
        'LANG']).replace('{STATE|COUNTRY}', config['COUNTRY']).replace('{CITY}', config['CITY'])
    r = requests.get(url)
    data.append(r.content)
    return data


if __name__ == '__main__':
    data = get_data()
