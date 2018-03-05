from utilities.util import get_config
from os import environ

TELEGRAM_CONFIG = get_config(__file__)
TELEGRAM_CONFIG = TELEGRAM_CONFIG if TELEGRAM_CONFIG else {}
TELEGRAM_CONFIG.update(get_config(__file__.replace('config.py', 'docker_config.py')) if environ.get('DOCKER_MODE', False)
        else get_config(__file__.replace('config.py', 'dev_config.py')))
