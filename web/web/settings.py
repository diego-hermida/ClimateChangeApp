import os
from global_config.config import GLOBAL_CONFIG
from climate.config.config import WEB_CONFIG
from django.utils.translation import ugettext_lazy as _


# Base config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WSGI_APPLICATION = 'web.wsgi.application'
ROOT_URLCONF = 'web.urls'
ALLOWED_HOSTS = ['localhost']
INTERNAL_IPS = ['localhost']


# Application definition
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'climate',
    'climate.webmodels',
    'data_conversion_subsystem.data',
    'debug_toolbar',
    'bootstrap4',
    'bootstrap_daterangepicker',
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
        'LOCATION': os.environ.get(WEB_CONFIG['CACHE_SERVER_IP'], 'localhost') + ':' + os.environ.get(
                WEB_CONFIG['CACHE_SERVER_PORT'], '11211'),
    }
}


# Security
SECURE_SSL_REDIRECT = False
DEBUG = False
SESSION_COOKIE_HTTPONLY = False
CSRF_COOKIE_HTTPONLY = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


# Test config
TEST_XML_RUNNER = 'utilities.xmltestrunner.XMLTestRunner'
TEST_OUTPUT_VERBOSE = 2
TEST_OUTPUT_DIR = GLOBAL_CONFIG['TEST_RESULTS_DIR']
TEST_OUTPUT_FILE_NAME = WEB_CONFIG['TESTS_FILENAME']

# Session settings
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'cg#p$g+j9tax!#a3cup@1$8obt2_+&k3q+pmu)5%asj6yjpkag')
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
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
STATIC_PREFIX = 'climate/static'
STATICFILES_DIRS = [os.path.join(BASE_DIR, STATIC_PREFIX)]
