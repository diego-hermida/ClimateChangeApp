from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.ocean_mass.ocean_mass as ocean_mass
from utilities.util import deserialize_date, serialize_date


class TestOceanMass(TestCase):

    @classmethod
    def setUpClass(cls):
        ocean_mass.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(ocean_mass.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      ocean_mass.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = ocean_mass.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, ocean_mass.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_correct_data_collection(self, mock_ftp, mock_reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [['HDR Greenland Mass Trend (04/2002 - 06/2017): -285.85 +/-21.01 Gt/yr\n',
                        '2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n']]
        mock_reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_ftp.called)
        self.assertTrue(mock_reader.called)
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
        data = mock_collection.mock_calls[0][1][0]
        for v in data:
            if v._doc['$setOnInsert']['type'] == ocean_mass.MassType.antarctica:
                self.assertAlmostEqual(-285.85, v._doc['$setOnInsert']['measures'][2]['trend'], 0.01)
            else:
                self.assertIsNone(v._doc['$setOnInsert']['measures'][2]['trend'])

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_correct_data_collection_with_unnecesary_files(self, mock_ftp, mock_reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt', 'unnecesary_file.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [['HDR Greenland Mass Trend (04/2002 - 06/2017): -285.85 +/-21.01 Gt/yr\n',
                        '2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n'],
                       ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n']]

        mock_reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_ftp.called)
        self.assertTrue(mock_reader.called)
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

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_not_all_files_updated_since_last_check(self, mock_ftp, mock_reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [['HDR Greenland Mass Trend (04/2002 - 06/2017): -285.85 +/-21.01 Gt/yr\n',
                        '2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n'],
                       ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n']]

        mock_reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_ftp.called)
        self.assertTrue(mock_reader.called)
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

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_no_new_data(self, mock_ftp):
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        last_request = serialize_date(
                deserialize_date('20170801221800.1234', self.data_collector.config['FTP_DATE_FORMAT']))
        self.data_collector.config['STATE_STRUCT']['antarctica']['last_modified'] = last_request
        self.data_collector.config['STATE_STRUCT']['greenland']['last_modified'] = last_request
        self.data_collector.run()
        self.assertTrue(mock_ftp.called)
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

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_no_new_data_and_unnecessary_files(self, mock_ftp):
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt', 'unnecessary_file.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        last_request = serialize_date(
                deserialize_date('20170801221800.1234', self.data_collector.config['FTP_DATE_FORMAT']))
        self.data_collector.config['STATE_STRUCT']['antarctica']['last_modified'] = last_request
        self.data_collector.config['STATE_STRUCT']['greenland']['last_modified'] = last_request
        self.data_collector.run()
        self.assertTrue(mock_ftp.called)
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

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_invalid_data_from_server(self, mock_ftp, mock_reader):
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        mock_reader.return_value.get_data.return_value = ['Invalid data', 'Cannot be parsed']
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.run()
        self.assertTrue(mock_ftp.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_not_all_items_saved(self, mock_ftp, mock_reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 7, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [
            ['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n', '2002.29       0.00     164.18\n',
             '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n', '2002.29       0.00     113.95\n',
             '2002.35      14.61      66.61\n']]

        mock_reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_ftp.called)
        self.assertTrue(mock_reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(8, self.data_collector.state['data_elements'])
        self.assertEqual(7, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['antarctica']['update_frequency'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['greenland']['update_frequency'])
        

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_too_much_items_not_saved(self, mock_ftp, mock_reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 6, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [
            ['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n', '2002.29       0.00     164.18\n',
             '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n', '2002.29       0.00     113.95\n',
             '2002.35      14.61      66.61\n']]

        mock_reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_ftp.called)
        self.assertTrue(mock_reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(8, self.data_collector.state['data_elements'])
        self.assertEqual(6, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.ocean_mass.ocean_mass.FTP')
    def test_data_collection_with_no_items_saved(self, mock_ftp, mock_reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_ftp.return_value.nlst.return_value = ['antarctica_mass_200204_201701.txt',
                                                   'greenland_mass_200204_201701.txt']
        mock_ftp.return_value.sendcmd.return_value = '123420170801221800'
        side_effect = [
            ['2002.29       0.00     164.18\n', '2002.35      62.12     103.45\n', '2002.29       0.00     164.18\n',
             '2002.35      62.12     103.45\n'],
            ['2002.29       0.00     113.95\n', '2002.35      14.61      66.61\n', '2002.29       0.00     113.95\n',
             '2002.35      14.61      66.61\n']]

        mock_reader.return_value.get_data = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = ocean_mass.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_ftp.called)
        self.assertTrue(mock_reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(8, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
