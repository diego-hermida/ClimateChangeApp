from utilities.util import get_config
from os import environ

UTIL_CONFIG = get_config(__file__)
UTIL_CONFIG.update(get_config(__file__.replace('config.py', 'docker_config.py')) if environ.get('DOCKER_MODE', False)
        else get_config(__file__.replace('config.py', 'dev_config.py')))
