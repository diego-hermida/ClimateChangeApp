from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.energy_sources.energy_sources as energy_sources

DATA = dumps({
    "countryCode": "ES",
    "data": {
        "carbonIntensity": 92.97078744790771,
        "fossilFuelPercentage": 12.028887656434616
    },
    "status": "ok",
    "units": {
        "carbonIntensity": "gCO2eq/kWh"
    }
})
DATA = DATA.encode()

INVALID_DATA = dumps({
    "countryCode": "ES",
    "data": {},
    "status": "ok",
    "units": {
        "carbonIntensity": "gCO2eq/kWh"
    }
})
INVALID_DATA = INVALID_DATA.encode()

ERROR = dumps({"error":"Unknown server error"})
ERROR = ERROR.encode()


class TestEnergySources(TestCase):

    @classmethod
    def setUp(cls):
        energy_sources.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('requests.get')
    def test_correct_data_collection(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_stops_when_reached_limit(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.status_code = 429
        response.content = '{"message": "API rate limit exceeded"}'.encode()
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        self.assertTrue(self.data_collector.advisedly_no_data_collected)

    def test_data_collection_with_no_countries(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertTrue(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_invalid_data_from_server(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = INVALID_DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertFalse(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_with_rejected_request_from_server(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = ERROR
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertFalse(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_with_not_all_items_saved(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 'ES', 'name': 'Spain'},
                                                           {'_id': 'AR', 'name': 'Argentina'}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}

        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_with_no_items_saved(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find.return_value = ([{'_id': 'ES', 'name': 'Spain'},
                                                           {'_id': 'AR', 'name': 'Argentina'}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}

        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
