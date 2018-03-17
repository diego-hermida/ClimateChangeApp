from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.current_conditions.current_conditions as current_conditions


class TestCurrentConditions(TestCase):

    @classmethod
    def setUpClass(cls):
        current_conditions.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(current_conditions.instance(), current_conditions.instance())
        i1 = current_conditions.instance()
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, current_conditions.instance())

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1},
                {'_id': 2, 'name': 'City 2', 'owm_station_id': 2}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 2, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"coord": {"lon": 145.77, "lat": -16.92}, "weather": [
            {"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03n"}], "base": "stations",
            "main": {"temp": 300.15, "pressure": 1007, "humidity": 74, "temp_min": 300.15, "temp_max": 300.15},
            "visibility": 10000, "wind": {"speed": 3.6, "deg": 160}, "clouds": {"all": 40}, "dt": 1485790200,
            "sys": {"type": 1, "id": 8166, "message": 0.2064, "country": "AU", "sunrise": 1485720272, "sunset":
            1485766550}, "id": 2172797, "name": "Cairns", "cod": 200}).encode()
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
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
    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_correct_data_collection_with_more_items_than_allowed_requests(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}], 1)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"coord": {"lon": 145.77, "lat": -16.92}, "weather": [
            {"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03n"}], "base": "stations",
            "main": {"temp": 300.15, "pressure": 1007, "humidity": 74, "temp_min": 300.15, "temp_max": 300.15},
            "visibility": 10000, "wind": {"speed": 3.6, "deg": 160}, "clouds": {"all": 40}, "dt": 1485790200,
            "sys": {"type": 1, "id": 8166, "message": 0.2064, "country": "AU", "sunrise": 1485720272, "sunset":
            1485766550}, "id": 2172797, "name": "Cairns", "cod": 200}).encode()
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
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

    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_data_collection_with_no_locations(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
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
    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_data_collection_invalid_data_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'data': ['invalid', 'data', 'structure']}).encode()
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
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
    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_data_collection_with_rejected_request_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 1, 'name': 'Belleville', 'owm_station_id': 1}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"status": "error", "message": "Over quota"}).encode()
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
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
    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1},
                {'_id': 2, 'name': 'City 2', 'owm_station_id': 2}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"coord": {"lon": 145.77, "lat": -16.92}, "weather": [
            {"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03n"}], "base": "stations",
            "main": {"temp": 300.15, "pressure": 1007, "humidity": 74, "temp_min": 300.15, "temp_max": 300.15},
            "visibility": 10000, "wind": {"speed": 3.6, "deg": 160}, "clouds": {"all": 40}, "dt": 1485790200,
            "sys": {"type": 1, "id": 8166, "message": 0.2064, "country": "AU", "sunrise": 1485720272, "sunset":
            1485766550}, "id": 2172797, "name": "Cairns", "cod": 200}).encode()
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
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
    @mock.patch('data_gathering_subsystem.data_modules.current_conditions.current_conditions.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([{'_id': 1, 'name': 'City 1', 'owm_station_id': 1},
                {'_id': 2, 'name': 'City 2', 'owm_station_id': 2}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({"coord": {"lon": 145.77, "lat": -16.92}, "weather": [
            {"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03n"}], "base": "stations",
            "main": {"temp": 300.15, "pressure": 1007, "humidity": 74, "temp_min": 300.15, "temp_max": 300.15},
            "visibility": 10000, "wind": {"speed": 3.6, "deg": 160}, "clouds": {"all": 40}, "dt": 1485790200,
            "sys": {"type": 1, "id": 8166, "message": 0.2064, "country": "AU", "sunrise": 1485720272, "sunset":
            1485766550}, "id": 2172797, "name": "Cairns", "cod": 200}).encode()
        # Actual execution
        self.data_collector = current_conditions.instance(log_to_stdout=False, log_to_telegram=False)
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
