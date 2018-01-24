from json import dumps
from unittest import TestCase, main, mock
from unittest.mock import Mock

from itertools import chain, repeat

import data_modules.country_indicators.country_indicators as country_indicators


class TestCountryIndicators(TestCase):

    @classmethod
    def setUpClass(cls):
        country_indicators.instance(log_to_stdout=False).remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 11 * len(self.data_collector.config['INDICATORS']), 'nMatched': 0,
                                         'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])], len(self.data_collector.config['INDICATORS'])))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * len(self.data_collector.config['INDICATORS']), self.data_collector.state['data_elements'])
        self.assertEqual(11 * len(self.data_collector.config['INDICATORS']),
                         self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection_with_single_page(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4 * len(self.data_collector.config['INDICATORS']), 'nMatched': 0,
                                         'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 1, "per_page": "4", "total": 4}, None]),
                                   dumps([None, [data, data, data, data]])],
                                  len(self.data_collector.config['INDICATORS'])))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(4 * len(self.data_collector.config['INDICATORS']), self.data_collector.state['data_elements'])
        self.assertEqual(4 * len(self.data_collector.config['INDICATORS']),
                         self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_with_no_new_data(self, mock_requests):
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": None, "decimal": "1", "date": "2016"}
        response.content.decode = Mock(return_value=dumps([None, [data]]))
        # Actual execution
        self.data_collector = country_indicators.instance(log_to_stdout=False)
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
        self.data_collector = country_indicators.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 10 * len(self.data_collector.config['INDICATORS']), 'nMatched': 0,
                                         'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])], len(self.data_collector.config['INDICATORS'])))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * len(self.data_collector.config['INDICATORS']), self.data_collector.state['data_elements'])
        self.assertEqual(10 * len(self.data_collector.config['INDICATORS']),
                         self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_items_not_saved(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 9 * len(self.data_collector.config['INDICATORS']), 'nMatched': 0,
                                         'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        data = {"indicator": {"id": "SP.URB.GROW", "value": "Urban population growth (annual %)"},
                "country": {"id": "ES", "value": "Spain"}, "value": 0.2717837115824, "decimal": "1", "date": "2016"}
        side_effect = list(repeat([dumps([{"page": 1, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 2, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data, data]]),
                                   dumps([{"page": 3, "pages": 3, "per_page": "4", "total": 11}, None]),
                                   dumps([None, [data, data, data]])], len(self.data_collector.config['INDICATORS'])))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * len(self.data_collector.config['INDICATORS']), self.data_collector.state['data_elements'])
        self.assertEqual(9 * len(self.data_collector.config['INDICATORS']),
                         self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_requests):
        self.data_collector = country_indicators.instance(log_to_stdout=False)
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
                                   dumps([None, [data, data, data]])], len(self.data_collector.config['INDICATORS'])))
        side_effect = list(chain.from_iterable(side_effect))
        side_effect.insert(0, dumps([None, [data]]))
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(11 * len(self.data_collector.config['INDICATORS']), self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])
