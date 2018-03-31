from os import environ
from utilities.util import get_config

DGS_CONFIG = get_config(__file__)
DGS_CONFIG.update(get_config(__file__.replace('config.py', 'docker_config.py')) if environ.get('DOCKER_MODE', False)
        else get_config(__file__.replace('config.py', 'dev_config.py')))
DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'] = DGS_CONFIG[
        'DATA_GATHERING_SUBSYSTEM_LOG_FILES_ROOT_FOLDER'].replace(DGS_CONFIG['ID_WILDCARD_PATTERN'],
        '' if DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'] == 1 else '_' + str(DGS_CONFIG['SUBSYSTEM_INSTANCE_ID']))
DGS_CONFIG['DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'] = DGS_CONFIG[
        'DATA_GATHERING_SUBSYSTEM_STATE_FILES_ROOT_FOLDER'].replace(DGS_CONFIG['ID_WILDCARD_PATTERN'],
        '' if DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'] == 1 else '_' + str(DGS_CONFIG['SUBSYSTEM_INSTANCE_ID']))
