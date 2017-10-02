import requests

from util.util import get_config

config = get_config(__file__)


def get_data():
    data = []
    for loc in config['LOCATIONS']:
        url = config['BASE_URL'].replace('{LOC}', loc) + config['TOKEN']
        r = requests.get(url)
        data.append(r.content)
    return data

    # r.content --> contiene el objeto JSON
    # 'status' --> lo primero que hay que mirar. Puede ser:
    #   'ok'
    #   'error' (ahora hay que mirar 'message'):
    #       'overQuota'
    #       'invalidKey'
    #       'unknownCity'
    # Ejemplos:
    #   - [b'{"status":"error","data":"Invalid key"}', b'{"status":"error","data":"Invalid key"}']
    #   - [b'{"status":"error","message":"404"}', b'{"status":"error","message":"404"}']


if __name__ == '__main__':
    data = get_data()
