from os import environ
from utilities.util import get_config

GLOBAL_CONFIG = get_config(__file__)
GLOBAL_CONFIG = GLOBAL_CONFIG if GLOBAL_CONFIG else {}
GLOBAL_CONFIG.update(get_config(__file__.replace('config.py', 'docker_config.py')) if environ.get('DOCKER_MODE', False) 
        else get_config(__file__.replace('config.py', 'dev_config.py')))
