import os
from global_config.global_config import GLOBAL_CONFIG


def register_settings():
    from django.core.wsgi import get_wsgi_application
    from utilities.postgres_util import import_psycopg2
    import_psycopg2()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', __name__)
    get_wsgi_application()


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': GLOBAL_CONFIG['POSTGRES_DATABASE'],
        'USER': GLOBAL_CONFIG['POSTGRES_USERNAME'],
        'PASSWORD': GLOBAL_CONFIG['POSTGRES_USER_PASSWORD'],
        'HOST': os.environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
        'PORT': GLOBAL_CONFIG['POSTGRES_PORT'],
    }
}

INSTALLED_APPS = (
    'data_conversion_subsystem.data',
)

SECRET_KEY = 'secret'
