from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

from itertools import chain, repeat

import data_gathering_subsystem.data_modules.country_indicators.country_indicators as country_indicators


class TestCountryIndicators(TestCase):

    @classmethod
    def setUpClass(cls):
        country_indicators.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 11 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                                         'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])],
                                  self.data_collector.config['MAX_INDICATORS_PER_EXECUTION']))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['indicator_index'])
        self.assertEqual(11 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['data_elements'])
        self.assertEqual(11 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection_with_single_page(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                                         'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 1, "per_page": "4", "total": 4}, None]),
                                   dumps([None, [data, data, data, data]])],
                                  self.data_collector.config['MAX_INDICATORS_PER_EXECUTION']))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(4 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['data_elements'])
        self.assertEqual(4 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_with_no_new_data(self, mock_requests):
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": None, "decimal": "1", "date": "2016"}
        response.content.decode = Mock(return_value=dumps([None, [data]]))
        # Actual execution
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_invalid_data_from_server(self, mock_requests):
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {'invalid': 'data'}
        response.content.decode = Mock(return_value=dumps([None, [data]]))
        # Actual execution
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 10 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                                         'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])],
                                  self.data_collector.config['MAX_INDICATORS_PER_EXECUTION']))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['data_elements'])
        self.assertEqual(10 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_items_not_saved(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 9 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                                         'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])],
                                  self.data_collector.config['MAX_INDICATORS_PER_EXECUTION']))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['data_elements'])
        self.assertEqual(9 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])],
                                  self.data_collector.config['MAX_INDICATORS_PER_EXECUTION']))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * self.data_collector.config['MAX_INDICATORS_PER_EXECUTION'],
                         self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection_less_indicators_than_max_per_execution(self, mock_collection, mock_requests):
        INDICATORS = 5
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['INDICATORS'] = self.data_collector.config['INDICATORS'][:INDICATORS]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 11 * INDICATORS, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])], INDICATORS))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['indicator_index'])
        self.assertEqual(11 * INDICATORS, self.data_collector.state['data_elements'])
        self.assertEqual(11 * INDICATORS, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection_with_end_date_less_than_current_year(self, mock_collection, mock_requests):
        INDICATORS = 5
        YEAR = 2000
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['end_date'] = YEAR
        self.data_collector.config['INDICATORS'] = self.data_collector.config['INDICATORS'][:INDICATORS]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 11 * INDICATORS, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])], INDICATORS))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        response.status_code = 200
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['indicator_index'])
        self.assertEqual(11 * INDICATORS, self.data_collector.state['data_elements'])
        self.assertEqual(11 * INDICATORS, self.data_collector.state['inserted_elements'])
        self.assertEqual(YEAR, self.data_collector.state['begin_date'])
        self.assertEqual(YEAR + 1, self.data_collector.state['end_date'])
        self.assertEqual(self.data_collector.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collector_omits_data_collection_when_HTTP_error_code(self, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        mock_requests.return_value = response = Mock()
        response.content.decode.return_value = dumps([None, [data]])
        response.status_code = 500
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        self.assertTrue(self.data_collector.advisedly_no_data_collected)
