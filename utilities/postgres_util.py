import re
from os import environ

from django.db.models import Q
from psycopg2cffi import connect
from psycopg2cffi._impl.connection import Connection
from psycopg2cffi.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from global_config.config import GLOBAL_CONFIG


def import_psycopg2():
    try:
        import psycopg2
    except ImportError:
        # Fall back to psycopg2cffi
        from psycopg2cffi import compat
        compat.register()


# This is required to work with PyPy.
import_psycopg2()


def get_connection(with_autocommit=True) -> Connection:
    """
        Creates a new database connection with the GLOBAL_CONFIG settings.
        :param with_autocommit: If True, sets the isolation level to ISOLATION_LEVEL_AUTOCOMMIT
        :return:
    """
    connection = connect(host=environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
                         port=environ.get(GLOBAL_CONFIG['POSTGRES_PORT'], 5432), user=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         password=GLOBAL_CONFIG['POSTGRES_ROOT_PASSWORD'], database=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         connect_timeout=GLOBAL_CONFIG['POSTGRES_MAX_SECONDS_WAIT'])
    if with_autocommit:
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return connection


def create_application_database(connection=None, close_after=False):
    """
        Creates the PostgreSQL application database.
        :param connection: If set, it will use the existing connection instead of creating a new one.
        :param close_after: If True, closes the connection after the operations.
        Postcondition: Database is empty (it will be dropped before being created if it previously existed).
        NOTE: Since user/table names cannot be passed as a parameter, string interpolation is used. However, these
              names are safe in a configuration file, so SQL-injection attacks should not be possible.
              Issue URL(s):
                - https://github.com/coleifer/peewee/issues/936
                - https://stackoverflow.com/questions/13793399/passing-table-name-as-a-parameter-in-psycopg2
    """
    connection = connect(host=environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
                         port=environ.get(GLOBAL_CONFIG['POSTGRES_PORT'], 5432), user=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         password=GLOBAL_CONFIG['POSTGRES_ROOT_PASSWORD'], database=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         connect_timeout=GLOBAL_CONFIG['POSTGRES_MAX_SECONDS_WAIT']) if not connection else connection
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    try:
        cursor.execute("DROP DATABASE IF EXISTS %s;" % GLOBAL_CONFIG['POSTGRES_DATABASE'])
        cursor.execute("CREATE DATABASE %s;" % GLOBAL_CONFIG['POSTGRES_DATABASE'])
    finally:
        cursor.close()
        try:
            if close_after:
                connection.close()
        except:
            pass


def drop_application_database(connection=None, close_after=False):
    """
        Drops the PostgreSQL application database.
        :param connection: If set, it will use the existing connection instead of creating a new one.
        :param close_after: If True, closes the connection after the operations.
        Postcondition: Database does not exist.
        NOTE: Since user/table names cannot be passed as a parameter, string interpolation is used. However, these
              names are safe in a configuration file, so SQL-injection attacks should not be possible.
              Issue URL(s):
                - https://github.com/coleifer/peewee/issues/936
                - https://stackoverflow.com/questions/13793399/passing-table-name-as-a-parameter-in-psycopg2
    """
    connection = connect(host=environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
                         port=environ.get(GLOBAL_CONFIG['POSTGRES_PORT'], 5432), user=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         password=GLOBAL_CONFIG['POSTGRES_ROOT_PASSWORD'], database=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         connect_timeout=GLOBAL_CONFIG['POSTGRES_MAX_SECONDS_WAIT']) if not connection else connection
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    try:
        cursor.execute("DROP DATABASE IF EXISTS %s;" % GLOBAL_CONFIG['POSTGRES_DATABASE'])
    finally:
        cursor.close()
        try:
            if close_after:
                connection.close()
        except:
            pass


def create_application_user(connection=None, close_after=False):
    """
        Creates the PostgreSQL application database user.
        If the user did already exist, it will be dropped before being created.
        :param connection: If set, it will use the existing connection instead of creating a new one.
        :param close_after: If True, closes the connection after the operations.
        Postcondition: The user has ALL PRIVILEGES on the application database.
        NOTE: Since user/table names cannot be passed as a parameter, string interpolation is used. However, these
              names are safe in a configuration file, so SQL-injection attacks should not be possible.
              Issue URL(s):
                - https://github.com/coleifer/peewee/issues/936
                - https://stackoverflow.com/questions/13793399/passing-table-name-as-a-parameter-in-psycopg2
    """
    connection = connect(host=environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
                         port=environ.get(GLOBAL_CONFIG['POSTGRES_PORT'], 5432), user=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         password=GLOBAL_CONFIG['POSTGRES_ROOT_PASSWORD'], database=GLOBAL_CONFIG['POSTGRES_ROOT'],
                         connect_timeout=GLOBAL_CONFIG['POSTGRES_MAX_SECONDS_WAIT']) if not connection else connection
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    try:
        cursor.execute("DROP USER IF EXISTS %s;" % GLOBAL_CONFIG['POSTGRES_USERNAME'])
        cursor.execute("CREATE USER %s WITH PASSWORD '%s';" % (
            GLOBAL_CONFIG['POSTGRES_USERNAME'], GLOBAL_CONFIG['POSTGRES_USER_PASSWORD']))
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE %s TO %s;" % (
            GLOBAL_CONFIG['POSTGRES_DATABASE'], GLOBAL_CONFIG['POSTGRES_USERNAME']))
    finally:
        cursor.close()
        try:
            if close_after:
                connection.close()
        except:
            pass


def ping_database(connection=None, close_after=False):
    """
        Attempts to connect to PostgreSQL. If the connection could not be established, an error will be raised.
        :param connection: If set, it will use the existing connection instead of creating a new one.
        :param close_after: If True, closes the connection after the operations.
    """
    try:
        conn = connect(host=environ.get(GLOBAL_CONFIG['POSTGRES_SERVER'], 'localhost'),
                       port=environ.get(GLOBAL_CONFIG['POSTGRES_PORT'], 5432), user=GLOBAL_CONFIG['POSTGRES_ROOT'],
                       password=GLOBAL_CONFIG['POSTGRES_ROOT_PASSWORD'], database=GLOBAL_CONFIG['POSTGRES_ROOT'],
                       connect_timeout=GLOBAL_CONFIG['POSTGRES_MAX_SECONDS_WAIT']) if not connection else connection
        if close_after:
            conn.close()
    except Exception as e:
        raise EnvironmentError('Connection could not be established.') from e


def normalize_query(query_string, findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    """
        Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together. Example:
            >>> normalize_query('  some random  words "with   quotes  " and   spaces')
            ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    """
    return [x for x in [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] if x != '']


def get_query(keywords: list, search_fields):
    """
        Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    """
    query = None  # Query to search for every search term
    for term in keywords:
        or_query = None  # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query
