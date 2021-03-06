from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.future_emissions.future_emissions as future_emissions


class TestFutureEmissions(TestCase):

    @classmethod
    def setUpClass(cls):
        future_emissions.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(future_emissions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      future_emissions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = future_emissions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, future_emissions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    def test_correct_data_collection(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.is_empty.return_value = False
        mock_collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': x} for x in range(2221)]
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2221, self.data_collector.state['data_elements'])
        self.assertEqual(2221, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['UPDATE_FREQUENCY'], self.data_collector.state['update_frequency'])

    def test_data_collection_with_missing_file(self):
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['DATA_DIR'] = './foo/bar/baz/'
        self.data_collector.run()
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    def test_data_collection_with_not_all_items_saved(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': x} for x in range(1999)]
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2221, self.data_collector.state['data_elements'])
        self.assertEqual(1999, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['UPDATE_FREQUENCY'], self.data_collector.state['update_frequency'])

    def test_data_collection_with_too_much_items_not_saved(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': x} for x in range(1998)]
        # Actual execution
        self.data_collector = future_emissions.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2221, self.data_collector.state['data_elements'])
        self.assertEqual(1998, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])
