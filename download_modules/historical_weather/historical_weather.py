import requests

BASE_URL = 'http://api.wunderground.com/api/{TOKEN}/history_{YYYYMMDD}/lang:{LANG}/q/{STATE|COUNTRY}/{CITY}.json'
LANG = 'EN'
COUNTRY = 'SPAIN'
CITY = 'Madrid'
DATE = '20170929'
TOKENS = ['5f06ae04f7342abf', 'e63c2d687265be99']


def get_data():
    data = []
    token_iter = iter(TOKENS)
    token = next(token_iter)

    url = BASE_URL.replace('{TOKEN}', token).replace('{YYYYMMDD}', DATE).replace('{LANG}', LANG). \
        replace('{STATE|COUNTRY}', COUNTRY).replace('{CITY}', CITY)
    r = requests.get(url)
    data.append(r.content)

    return data


if __name__ == '__main__':
    data = get_data()
