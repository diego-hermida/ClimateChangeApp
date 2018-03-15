from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

import utilities.postgres_util

_GLOBAL_CONFIG = deepcopy(utilities.postgres_util.GLOBAL_CONFIG)
_GLOBAL_CONFIG['POSTGRES_DATABASE'] = _GLOBAL_CONFIG['POSTGRES_DATABASE'] + '_test'


@mock.patch('utilities.postgres_util.GLOBAL_CONFIG', _GLOBAL_CONFIG)
class TestPostgresUtil(TestCase):

    def test_create_application_database(self):
        connection = utilities.postgres_util.get_connection()
        utilities.postgres_util.create_application_database(connection)
        c = connection.cursor()
        c.execute('SELECT EXISTS(SELECT 1 FROM pg_database WHERE DATNAME = %(dname)s)',
                  {'dname': _GLOBAL_CONFIG['POSTGRES_DATABASE']})
        exists = c.fetchone()
        c.close()
        connection.close()
        self.assertTrue(exists)

    def test_get_connection(self):
        connection = utilities.postgres_util.get_connection()
        self.assertEqual(0, connection.closed)
        connection.close()
        self.assertNotEqual(0, connection.closed)

    def test_create_application_user(self):
        connection = utilities.postgres_util.get_connection()
        utilities.postgres_util.create_application_user(connection)
        c = connection.cursor()
        c.execute('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE ROLNAME = %(usrname)s)',
                  {'usrname': _GLOBAL_CONFIG['POSTGRES_USERNAME']})
        exists = c.fetchone()
        c.close()
        connection.close()
        self.assertTrue(exists)

    @mock.patch('utilities.postgres_util.connect')
    def test_ping_database_ok(self, mock_connect):
        utilities.postgres_util.ping_database(close_after=True)
        self.assertEqual(1, mock_connect.call_count)
        self.assertEqual(1, mock_connect.return_value.close.call_count)

    @mock.patch('utilities.postgres_util.connect', Mock(side_effect=Exception('Test error (this is OK).')))
    def test_ping_database_failure(self):
        with self.assertRaises(EnvironmentError):
            utilities.postgres_util.ping_database(close_after=True)

    def test_remove_database(self):
        connection = utilities.postgres_util.get_connection()
        utilities.postgres_util.drop_application_database(connection)
        c = connection.cursor()
        c.execute('SELECT EXISTS(SELECT 1 FROM pg_database WHERE DATNAME = %(dname)s)',
                  {'dname': _GLOBAL_CONFIG['POSTGRES_DATABASE']})
        exists = c.fetchone()[0]
        c.close()
        connection.close()
        self.assertFalse(exists)

