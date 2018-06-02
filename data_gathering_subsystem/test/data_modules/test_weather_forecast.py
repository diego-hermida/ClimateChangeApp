from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.weather_forecast.weather_forecast as weather_forecast

RESPONSE = dumps({"cod": "200", "message": 0.0036, "cnt": 40, "list": [{"dt": 1485799200, "main": {"temp": 261.45,
        "temp_min": 259.086, "temp_max": 261.45, "pressure": 1023.48, "sea_level": 1045.39, "grnd_level": 1023.48,
        "humidity": 79, "temp_kf": 2.37}, "weather": [ {"id": 800, "main": "Clear", "description": "clear sky", "icon":
        "02n"}], "clouds": {"all": 8}, "wind": {"speed": 4.77, "deg": 232.505}, "snow": {}, "sys": {"pod": "n"},
        "dt_txt": "2017-01-30 18:00:00"},{"dt": 1485810000,"main": {"temp": 261.41, "temp_min": 259.638, "temp_max":
        261.41, "pressure": 1022.41, "sea_level": 1044.35, "grnd_level": 1022.41, "humidity": 76, "temp_kf": 1.78},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01n"}], "clouds": {"all": 32},
        "wind": {"speed": 4.76, "deg": 240.503}, "snow": {"3h": 0.011}, "sys": {"pod": "n"}, "dt_txt": "2017-01-30 "
        "21:00:00"}], "city": {"id": 524901, "name": "Moscow", "coord": {"lat": 55.7522, "lon": 37.6156}, "country":
        "none"}}).encode()


class TestCurrentConditions(TestCase):

    @classmethod
    def setUpClass(cls):
        weather_forecast.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(weather_forecast.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      weather_forecast.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = weather_forecast.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, weather_forecast.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('requests.get')
    def test_correct_data_collection(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = (
            [{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}, {'_id': 2, 'name': 'City 2', 'owm_station_id': 2}],
            None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 2, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = RESPONSE
        # Actual execution
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(2, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['start_index'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_correct_data_collection_with_more_items_than_allowed_requests(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}], 1)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = RESPONSE
        # Actual execution
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
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
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
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
        mock_collection.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'data': ['invalid', 'data', 'structure']}).encode()
        # Actual execution
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
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
        mock_collection.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "error", "message": "Over quota"}).encode()
        # Actual execution
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
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
        mock_collection.find.return_value = (
            [{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}, {'_id': 2, 'name': 'City 2', 'owm_station_id': 2}],
            None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = RESPONSE
        # Actual execution
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
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
        mock_collection.find.return_value = (
            [{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}, {'_id': 2, 'name': 'City 2', 'owm_station_id': 2}],
            None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = RESPONSE
        # Actual execution
        self.data_collector = weather_forecast.instance(log_to_stdout=False, log_to_telegram=False)
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
