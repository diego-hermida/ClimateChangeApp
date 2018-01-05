from unittest import TestCase, main, mock
from unittest.mock import Mock

import data_modules.ocean_mass.ocean_mass as ocean_mass
from utilities.util import deserialize_date, serialize_date


class TestOceanMass(TestCase):

    @classmethod
    def setUpClass(cls):
        ocean_mass.instance().remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 6, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n'],
                       ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n'],
                       ['2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n']]

        mock_Reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(6, self.data_collector.state['data_elements'])
        self.assertEqual(6, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['ocean']['update_frequency'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection_with_unnecesary_files(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 6, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt', 'unnecesary_file.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n'],
                       ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n'],
                       ['2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n']]

        mock_Reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(6, self.data_collector.state['data_elements'])
        self.assertEqual(6, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['ocean']['update_frequency'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_files_updated_since_last_check(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n'],
                       ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n']]

        mock_Reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance()
        last_request = serialize_date(
                deserialize_date('20170801221800.1234', self.data_collector.config['FTP_DATE_FORMAT']))
        self.data_collector.config['STATE_STRUCT']['ocean']['last_modified'] = last_request
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(4, self.data_collector.state['data_elements'])
        self.assertEqual(4, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['ocean']['update_frequency'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_no_new_data(self, mock_FTP):
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        # Actual execution
        self.data_collector = ocean_mass.instance()
        last_request = serialize_date(
                deserialize_date('20170801221800.1234', self.data_collector.config['FTP_DATE_FORMAT']))
        self.data_collector.config['STATE_STRUCT']['antarctica']['last_modified'] = last_request
        self.data_collector.config['STATE_STRUCT']['greenland']['last_modified'] = last_request
        self.data_collector.config['STATE_STRUCT']['ocean']['last_modified'] = last_request
        self.data_collector.run()
        self.assertTrue(mock_FTP.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['ocean']['update_frequency'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_no_new_data_and_unnecessary_files(self, mock_FTP):
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt', 'unnecessary_file.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        # Actual execution
        self.data_collector = ocean_mass.instance()
        last_request = serialize_date(
                deserialize_date('20170801221800.1234', self.data_collector.config['FTP_DATE_FORMAT']))
        self.data_collector.config['STATE_STRUCT']['antarctica']['last_modified'] = last_request
        self.data_collector.config['STATE_STRUCT']['greenland']['last_modified'] = last_request
        self.data_collector.config['STATE_STRUCT']['ocean']['last_modified'] = last_request
        self.data_collector.run()
        self.assertTrue(mock_FTP.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['ocean']['update_frequency'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_invalid_data_from_server(self, mock_FTP, mock_Reader):
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        mock_Reader.return_value.get_data.return_value = ['Invalid data', 'Cannot be parsed']
        # Actual execution
        self.data_collector = ocean_mass.instance()
        self.data_collector.run()
        self.assertTrue(mock_FTP.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 11, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [
            ['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n', '2002.29       0.00     164.18\n',
             '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n', '2002.29       0.00     113.95\n',
             '2002.35      14.61      66.61\n'],
            ['2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n',
             '2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n']]

        mock_Reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(12, self.data_collector.state['data_elements'])
        self.assertEqual(11, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['ocean']['update_frequency'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_items_not_saved(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 9, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [
            ['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n', '2002.29       0.00     164.18\n',
             '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n', '2002.29       0.00     113.95\n',
             '2002.35      14.61      66.61\n'],
            ['2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n',
             '2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n']]

        mock_Reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(12, self.data_collector.state['data_elements'])
        self.assertEqual(9, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_modules.ocean_mass.ocean_mass.FTP')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt', 'ocean_mass_200204_201701.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [
            ['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n', '2002.29       0.00     164.18\n',
             '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n', '2002.29       0.00     113.95\n',
             '2002.35      14.61      66.61\n'],
            ['2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n',
             '2002.29    0.00    0.94    0.00\n', '2002.35    0.47    0.65   -0.23\n']]

        mock_Reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(12, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
