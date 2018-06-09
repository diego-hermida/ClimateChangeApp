import os

from django.core.wsgi import get_wsgi_application

from utilities.postgres_util import import_psycopg2

# This is required to work with PyPy.
import_psycopg2()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")

application = get_wsgi_application()
