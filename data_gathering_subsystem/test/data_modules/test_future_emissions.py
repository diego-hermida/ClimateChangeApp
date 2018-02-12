from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.future_emissions.future_emissions as future_emissions


class TestFutureEmissions(TestCase):

    @classmethod
    def setUpClass(cls):
        future_emissions.instance(log_to_stdout=False).remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.is_empty.return_value = False
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': x} for x in range(2221)]
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2221, self.data_collector.state['data_elements'])
        self.assertEqual(2221, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['UPDATE_FREQUENCY'], self.data_collector.state['update_frequency'])

    def test_data_collection_with_missing_file(self):
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False)
        self.data_collector.config['DATA_DIR'] = './foo/bar/baz/'
        self.data_collector.run()
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': x} for x in range(1999)]
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2221, self.data_collector.state['data_elements'])
        self.assertEqual(1999, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['UPDATE_FREQUENCY'], self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_items_not_saved(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': x} for x in range(1998)]
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2221, self.data_collector.state['data_elements'])
        self.assertEqual(1998, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])
