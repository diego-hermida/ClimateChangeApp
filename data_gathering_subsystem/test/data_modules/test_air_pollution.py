from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.air_pollution.air_pollution as air_pollution


class TestAirPollution(TestCase):

    @classmethod
    def setUp(cls):
        air_pollution.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('requests.get')
    def test_correct_data_collection(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
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
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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
    def test_correct_data_collection_with_more_items_than_allowed_requests(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}], 1)
        mock_collection.bulk_write.return_value = insert_result = Mock()
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
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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

    def test_data_collection_with_no_locations(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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
    def test_data_collection_invalid_data_from_server(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'data': ['invalid', 'data', 'structure']}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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
    def test_data_collection_with_rejected_request_from_server(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'waqi_station_id': 1}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "error", "message": "Over quota"}).encode()
        # Actual execution
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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
    def test_data_collection_with_not_all_items_saved(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'waqi_station_id': 1},
                     {'location_id': 2, 'name': 'Brampton, Ontario', 'waqi_station_id': 2}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
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
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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
    def test_data_collection_with_no_items_saved(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'waqi_station_id': 1},
                     {'location_id': 2, 'name': 'Brampton, Ontario', 'waqi_station_id': 2}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
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
        self.data_collector = air_pollution.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
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
