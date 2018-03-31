from os import environ
from utilities.util import get_config

API_CONFIG = get_config(__file__)
API_CONFIG.update(get_config(__file__.replace('config.py', 'docker_config.py')) if environ.get('DOCKER_MODE', False)
        else get_config(__file__.replace('config.py', 'dev_config.py')))
