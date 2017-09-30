import requests

from util.util import get_config

config = get_config(__file__)


def get_data():
    data = []
    for loc in config['LOCATIONS']:
        r = requests.get(config['BASE_URL'] + loc + '/?token=' + config['TOKEN'])
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
    print(data)
