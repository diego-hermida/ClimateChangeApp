from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.air_pollution.air_pollution as air_pollution


class TestAirPollution(TestCase):

    @classmethod
    def setUp(cls):
        air_pollution.instance(log_to_stdout=False).remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}]}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "ok", "data": {"aqi": 25, "idx": 1, "attributions": [
            {"url": "http://www.airqualityontario.com/",
             "name": "Air Quality Ontario - the Ontario Ministry of the Environment and Climate Change"}],
             "city": {"geo": [44.150528, -77.3955], "name": "Belleville, Ontario",
             "url": "http://aqicn.org/city/canada/ontario/belleville/"}, "dominentpol": "o3",
             "iaqi": {"h": {"v": 63}, "no2": {"v": 3.8}, "o3": {"v": 24.8}, "p": {"v": 1026}, "pm25": {"v": 13},
             "t": {"v": -20.85}}, "time": {"s": "2017-12-31 05:00:00", "tz": "-05:00", "v": 1514696400}}}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_correct_data_collection_with_more_items_than_allowed_requests(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}], 'next_start_index': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "ok", "data": {"aqi": 25, "idx": 1, "attributions": [
            {"url": "http://www.airqualityontario.com/",
             "name": "Air Quality Ontario - the Ontario Ministry of the Environment and Climate Change"}],
             "city": {"geo": [44.150528, -77.3955], "name": "Belleville, Ontario",
             "url": "http://aqicn.org/city/canada/ontario/belleville/"}, "dominentpol": "o3",
             "iaqi": {"h": {"v": 63}, "no2": {"v": 3.8}, "o3": {"v": 24.8}, "p": {"v": 1026}, "pm25": {"v": 13},
             "t": {"v": -20.85}}, "time": {"s": "2017-12-31 05:00:00", "tz": "-05:00", "v": 1514696400}}}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['start_index'])
        self.assertEqual(1, self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_data_collection_with_no_locations(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {'data': []}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_data_collection_invalid_data_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}]}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'data': ['invalid', 'data', 'structure']}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_data_collection_with_rejected_request_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}]}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "error", "message": "Over quota"}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'waqi_station_id': 1},
                     {'_id': 2, 'name': 'Brampton, Ontario', 'waqi_station_id': 2}]}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "ok", "data": {"aqi": 25, "idx": 1, "attributions": [
            {"url": "http://www.airqualityontario.com/",
             "name": "Air Quality Ontario - the Ontario Ministry of the Environment and Climate Change"}],
             "city": {"geo": [44.150528, -77.3955], "name": "Belleville, Ontario",
             "url": "http://aqicn.org/city/canada/ontario/belleville/"}, "dominentpol": "o3",
             "iaqi": {"h": {"v": 63}, "no2": {"v": 3.8}, "o3": {"v": 24.8}, "p": {"v": 1026}, "pm25": {"v": 13},
             "t": {"v": -20.85}}, "time": {"s": "2017-12-31 05:00:00", "tz": "-05:00", "v": 1514696400}}}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.air_pollution.air_pollution.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'waqi_station_id': 1},
                     {'_id': 2, 'name': 'Brampton, Ontario', 'waqi_station_id': 2}]}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "ok", "data": {"aqi": 25, "idx": 1, "attributions": [
            {"url": "http://www.airqualityontario.com/",
             "name": "Air Quality Ontario - the Ontario Ministry of the Environment and Climate Change"}],
             "city": {"geo": [44.150528, -77.3955], "name": "Belleville, Ontario",
             "url": "http://aqicn.org/city/canada/ontario/belleville/"}, "dominentpol": "o3",
             "iaqi": {"h": {"v": 63}, "no2": {"v": 3.8}, "o3": {"v": 24.8}, "p": {"v": 1026}, "pm25": {"v": 13},
             "t": {"v": -20.85}}, "time": {"s": "2017-12-31 05:00:00", "tz": "-05:00", "v": 1514696400}}}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
