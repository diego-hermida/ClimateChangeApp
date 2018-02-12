import json
from unittest import TestCase, mock
from unittest.mock import Mock

from pymongo.errors import DuplicateKeyError

from api import main as main
from global_config.global_config import GLOBAL_CONFIG
from utilities.db_util import create_application_user, create_authorized_user, drop_application_database, \
    drop_application_user


class TestMain(TestCase):

    @classmethod
    def setUpClass(cls):
        GLOBAL_CONFIG['DATABASE'] += '_test'
        try:
            create_application_user()
        except DuplicateKeyError:
            pass
        create_authorized_user(GLOBAL_CONFIG['DB_API_AUTHORIZED_USERNAME'], GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN'])

    def setUp(self):
        main._modules = None
        main._modules_last_update = None
        main._api_alive = None
        main._api_alive_last_update = None
        self.app = main.app.test_client()

    @classmethod
    def tearDownClass(cls):
        drop_application_user()
        drop_application_database()

    def test_execution_fails_if_environment_variable_does_not_exist(self):
        from os import environ
        localhost_ip = environ.get('LOCALHOST_IP')
        if localhost_ip:
            del environ['LOCALHOST_IP']
        with self.assertRaises(SystemExit):
            main.main(log_to_stdout=False, log_to_file=False)
        if localhost_ip is not None:
            environ['LOCALHOST_IP'] = localhost_ip

    @mock.patch('api.main.ping_database', Mock(side_effect=EnvironmentError(
            'Test error to verify 503 HTTP status code is obtained.')))
    def test_authorized_calls_return_503_if_database_down(self):
        r = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(503, r.status_code)

    def test_require_auth_succeed(self):
        r = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(200, r.status_code)

    def test_require_auth_rejected_invalid_token(self):
        r = self.app.get('/modules', headers={'Authorization': 'Bearer INVALID_TOKEN_K0R9A1NWOIvwCBO2fR'})
        self.assertEqual(401, r.status_code)

    def test_require_auth_rejected_no_token(self):
        r = self.app.get('/modules')
        self.assertEqual(401, r.status_code)

    @mock.patch('api.main.MongoDBCollection')
    def test_modules_endpoint(self, mock_collection):
        mock_collection.return_value.collection.find_one.return_value = {'_id': 'aggregated', 'per_module':
                {'air_pollution': {}, 'countries': {}}}
        r = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(200, r.status_code)
        self.assertListEqual(['air_pollution', 'countries'], data['modules'])

    def test_modules_endpoint_with_no_modules(self):
        r = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(200, r.status_code)
        self.assertListEqual([], data['modules'])

    @mock.patch('api.main.MongoDBCollection')
    def test_modules_endpoint_close_requests_use_cache(self, mock_collection):
        mock_collection.return_value.collection.find_one.return_value = {'_id': 'aggregated',
                'per_module': {'air_pollution': {}, 'countries': {}}}
        r1 = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        r1_data = r1.get_data()
        self.assertEqual(200, r1.status_code)
        self.assertEqual(1, mock_collection.call_count)
        r2 = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        r2_data = r2.get_data()
        self.assertEqual(1, mock_collection.call_count)
        self.assertEqual(200, r2.status_code)
        self.assertEqual(r1_data, r2_data)

    @mock.patch('api.main.MongoDBCollection')
    @mock.patch('api.main.MODULES_CACHE_TIME', -1)
    def test_modules_endpoint_distant_requests_do_not_use_cache(self, mock_collection):
        mock_collection.return_value.collection.find_one.return_value = {'_id': 'aggregated',
                'per_module': {'air_pollution': {}, 'countries': {}}}
        r1 = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        r1_data = json.loads(r1.get_data().decode('utf-8'))
        self.assertEqual(200, r1.status_code)
        self.assertEqual(1, mock_collection.call_count)
        r2 = self.app.get('/modules', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        r2_data = json.loads(r2.get_data().decode('utf-8'))
        self.assertEqual(2, mock_collection.call_count)
        self.assertEqual(200, r2.status_code)
        self.assertEqual(r1_data['modules'], r2_data['modules'])
        self.assertNotEqual(r1_data['updated'], r2_data['updated'])

    @mock.patch('api.main.MongoDBCollection')
    def test_execution_stats_endpoint_last_execution(self, mock_collection):
        mock_collection.return_value.collection.find_one = Mock(
                side_effect=[{'_id': 'aggregated', 'last_execution_id': 1},
                             {"more_values": "should_go_here", "execution_id": 1}])
        r = self.app.get('/executionStats', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(200, r.status_code)
        self.assertEqual(1, data['execution_id'])

    @mock.patch('api.main.MongoDBCollection')
    def test_execution_stats_endpoint_last_execution_and_subsystem_not_executed(self, mock_collection):
        mock_collection.return_value.collection.find_one.return_value = None
        r = self.app.get('/executionStats', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(404, r.status_code)

    def test_execution_stats_endpoint_with_execution_id_invalid_type(self):
        r = self.app.get('/executionStats?executionId=foo', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r.status_code)

    def test_execution_stats_endpoint_with_execution_id_negative(self):
        r = self.app.get('/executionStats?executionId=-1', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r.status_code)

    @mock.patch('api.main.MongoDBCollection')
    def test_execution_stats_endpoint_with_execution_id_non_existing_but_subsystem_executed(self, mock_collection):
        mock_collection.return_value.collection.find_one = Mock(
                side_effect=[None, {'_id': 'aggregated', 'last_execution_id': 1}])
        r = self.app.get('/executionStats?executionId=2', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(404, r.status_code)
        self.assertEqual(1, data['last_execution_id'])

    @mock.patch('api.main.MongoDBCollection')
    def test_execution_stats_endpoint_with_execution_id_non_existing_and_subsystem_not_executed(self, mock_collection):
        mock_collection.return_value.collection.find_one.return_value = None
        r = self.app.get('/executionStats?executionId=2', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(404, r.status_code)
        self.assertIsNone(data.get('last_execution_id'))

    @mock.patch('api.main.MongoDBCollection')
    def test_data_endpoint_no_parameters(self, mock_collection):
        data = []
        for i in range(1, 6):
            data.append({'_id': i, 'value': i})
        mock_collection.return_value.find.return_value = {'data': data}
        mock_collection.return_value.collection.find_one.return_value = {'_id': 'aggregated', 'per_module': {'module':
                {}}}
        r = self.app.get('/data/module', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        result = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(200, r.status_code)
        self.assertListEqual(data, result['data'])

    def test_data_endpoint_with_last_index_invalid_type(self):
        r = self.app.get('/data/module?startIndex=foo',
                         headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r.status_code)

    @mock.patch('api.main.MongoDBCollection')
    def test_data_endpoint_with_last_index_compatible_datatype(self, mock_collection):
        data = []
        for i in range(5, 9):
            data.append({'_id': i, 'value': i})
        mock_collection.return_value.find.return_value = {'data': data}
        mock_collection.return_value.collection.find_one.return_value = {'_id': 'aggregated',
                                                                         'per_module': {'module': {}}}
        r = self.app.get('/data/module?startIndex=4',
                         headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        result = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(200, r.status_code)
        self.assertListEqual(data, result['data'])

    def test_data_endpoint_with_limit_invalid_type(self):
        r = self.app.get('/data/module?limit=foo',
                         headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r.status_code)

    def test_data_endpoint_with_limit_invalid_value(self):
        r1 = self.app.get('/data/module?limit=0',
                          headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        r2 = self.app.get('/data/module?limit=-1',
                          headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r1.status_code)
        self.assertEqual(400, r2.status_code)

    def test_data_endpoint_with_execution_id_invalid_type(self):
        r = self.app.get('/data/module?executionId=foo',
                         headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r.status_code)

    def test_data_endpoint_with_execution_id_invalid_value(self):
        r1 = self.app.get('/data/module?executionId=0',
                          headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        r2 = self.app.get('/data/module?executionId=-1',
                          headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(400, r1.status_code)
        self.assertEqual(400, r2.status_code)

    @mock.patch('api.main.MongoDBCollection')
    def test_data_endpoint_with_invalid_module(self, mock_collection):
        mock_collection.return_value.collection.find_one.return_value = {'_id': 'aggregated', 'per_module':
                {'air_pollution': {}, 'countries': {}}}
        r = self.app.get('/data/invalid_module', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG[
                'DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(404, r.status_code)

    def test_alive_endpoint(self):
        r = self.app.get('/alive')
        self.assertEqual(200, r.status_code)
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertTrue(data['alive'])

    def test_alive_endpoint_with_authenticated_request(self):
        r = self.app.get('/alive', headers={'Authorization': 'Bearer ' + GLOBAL_CONFIG['DB_API_AUTHORIZED_USER_TOKEN']})
        self.assertEqual(200, r.status_code)
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertTrue(data['alive'])

    @mock.patch('api.main.ping_database', Mock(side_effect=EnvironmentError('Database is down!')))
    def test_alive_endpoint_with_inactive_database(self):
        r = self.app.get('/alive')
        self.assertEqual(503, r.status_code)
        data = json.loads(r.get_data().decode('utf-8'))
        self.assertFalse(data['alive'])

    @mock.patch('api.main.ping_database',
                Mock(side_effect=Exception('Test error (to verify anomalous exit). This is OK.')))
    def test_alive_endpoint_with_inactive_database_uncaught_exception(self):
        r = self.app.get('/alive')
        self.assertEqual(500, r.status_code)

    def test_unknown_endpoint_requests_are_rejected(self):
        r = self.app.get('/unknown_endpoint')
        self.assertEqual(404, r.status_code)

    @mock.patch('api.main.ping_database')
    def test_alive_endpoint_close_requests_use_cache(self, mock_ping):
        r1 = self.app.get('/alive')
        r1_data = r1.get_data()
        self.assertEqual(200, r1.status_code)
        self.assertEqual(1, mock_ping.call_count)
        r2 = self.app.get('/alive')
        r2_data = r2.get_data()
        self.assertEqual(1, mock_ping.call_count)
        self.assertEqual(200, r2.status_code)
        self.assertEqual(r1_data, r2_data)

    @mock.patch('api.main.ping_database')
    @mock.patch('api.main.API_ALIVE_CACHE_TIME', -1)
    def test_alive_endpoint_distant_requests_do_not_use_cache(self, mock_ping):
        r1 = self.app.get('/alive')
        r1_data = json.loads(r1.get_data().decode('utf-8'))
        self.assertEqual(200, r1.status_code)
        self.assertEqual(1, mock_ping.call_count)
        r2 = self.app.get('/alive')
        r2_data = json.loads(r2.get_data().decode('utf-8'))
        self.assertEqual(2, mock_ping.call_count)
        self.assertEqual(200, r2.status_code)
        self.assertEqual(r1_data['alive'], r2_data['alive'])
        self.assertNotEqual(r1_data['updated'], r2_data['updated'])
