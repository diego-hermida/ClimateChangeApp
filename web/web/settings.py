import os
from global_config.config import GLOBAL_CONFIG
from climate.config.config import WEB_CONFIG
from django.utils.translation import ugettext_lazy as _


# Base config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WSGI_APPLICATION = 'web.wsgi.application'
ROOT_URLCONF = 'web.urls'
ALLOWED_HOSTS = ['localhost']
INTERNAL_IPS = ['localhost', '127.0.0.1']
DEBUG = True


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap4',
    'bootstrap_daterangepicker',
    'widget_tweaks',
    'data_conversion_subsystem.data',
    'climate.webmodels',
    'climate',
    'debug_toolbar'
]

# Middleware definition
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]


# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [''],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'climate.context_processor.base',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': GLOBAL_CONFIG['POSTGRES_DATABASE'],
        'USER': GLOBAL_CONFIG['POSTGRES_USERNAME'],
        'PASSWORD': GLOBAL_CONFIG['POSTGRES_USER_PASSWORD'],
        'HOST': os.environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
        'PORT': int(os.environ.get(GLOBAL_CONFIG['POSTGRES_PORT'], 5432)),
    }
}


# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': WEB_CONFIG['CACHE_ENDPOINT'],
    }
}


# Session settings
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'cg#p$g+j9tax!#a3cup@1$8obt2_+&k3q+pmu)5%asj6yjpkag')
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # An hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = (
    ('en', _('English')),
    ('es', _('Spanish'))
)
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')
STATIC_URL = '/static/'
STATIC_PREFIX = 'climate/static' if DEBUG else 'static'
STATICFILES_DIRS = [os.path.join(BASE_DIR, STATIC_PREFIX)]
