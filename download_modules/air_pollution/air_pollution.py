import requests

BASE_URL = 'https://api.waqi.info/feed/'
LOCATIONS = ['Madrid', 'Barcelona']
TOKEN = '/?token=' + 'acb2cc5e80eca1f4aec3fa17785bc7a42f877cdf'


def get_data():
    data = []
    for loc in LOCATIONS:
        r = requests.get(BASE_URL + loc + TOKEN)
        data.append(r.content)
    return data
    # r.content --> contiene el objeto JSON
    # 'status' --> lo primero que hay que mirar. Puede ser:
    #   'ok'
    #   'error' (ahora hay que mirar 'message'):
    #       'overQuota'
    #       'invalidKey'
    #       'unknownCity'


if __name__ == '__main__':
    data = get_data()
