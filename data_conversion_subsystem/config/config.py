from os import environ
from utilities.util import get_config

DCS_CONFIG = get_config(__file__)
DCS_CONFIG = DCS_CONFIG if DCS_CONFIG else {}
DCS_CONFIG.update(get_config(__file__.replace('config.py', 'docker_config.py')) if environ.get('DOCKER_MODE', False)
        else get_config(__file__.replace('config.py', 'dev_config.py')))
DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'] = DCS_CONFIG[
        'DATA_CONVERSION_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'].replace(DCS_CONFIG['ID_WILDCARD_PATTERN'],
        '' if DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'] == 1 else '_' + str(DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']))
DCS_CONFIG['DATA_CONVERSION_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'] = DCS_CONFIG[
        'DATA_CONVERSION_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'].replace(DCS_CONFIG['ID_WILDCARD_PATTERN'],
        '' if DCS_CONFIG['SUBSYSTEM_INSTANCE_ID'] == 1 else '_' + str(DCS_CONFIG['SUBSYSTEM_INSTANCE_ID']))
