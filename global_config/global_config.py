from os import environ

from utilities.util import get_config

CONFIG = get_config(__file__)
CONFIG.update(get_config(__file__.replace('global_config.py', 'docker_global_config.py')) if environ.get('DOCKER_MODE',
        False) else get_config(__file__.replace('global_config.py', 'dev_global_config.py')))
