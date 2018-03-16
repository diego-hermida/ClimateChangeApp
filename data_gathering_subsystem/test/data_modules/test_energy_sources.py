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
        self.data_collector.remove_files()

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_data_collection_stops_when_reached_limit(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.status_code = 429
        response.content = '{"message": "API rate limit exceeded"}'.encode()
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        self.assertTrue(self.data_collector.advisedly_no_data_collected)

    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_data_collection_with_no_countries(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertTrue(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_data_collection_invalid_data_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = INVALID_DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertFalse(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_data_collection_with_rejected_request_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 'ES', 'name': 'Spain'}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = ERROR
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertFalse(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 'ES', 'name': 'Spain'},
                                                           {'_id': 'AR', 'name': 'Argentina'}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}

        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()

        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.energy_sources.energy_sources.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([{'_id': 'ES', 'name': 'Spain'},
                                                           {'_id': 'AR', 'name': 'Argentina'}], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}

        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = energy_sources.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()

        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
