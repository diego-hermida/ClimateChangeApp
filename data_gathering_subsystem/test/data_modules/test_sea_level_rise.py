from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise as sea_level_rise
from utilities.util import deserialize_date, serialize_date


class TestSeaLevelRise(TestCase):

    @classmethod
    def setUpClass(cls):
        sea_level_rise.instance(log_to_stdout=False).remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.FTP')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 2, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['GMSL_TPJAOS_V4.jpg', 'GMSL_TPJAOS_V4_199209_201708.txt',
                                                   'README_GMSL_folder_contents.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        data = [
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n']

        mock_Reader.return_value.get_data.return_value = data
        # Actual execution
        self.data_collector = sea_level_rise.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_FTP.called)
        self.assertTrue(mock_Reader.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(2, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.FTP')
    def test_data_collection_with_no_new_data(self, mock_FTP):
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['GMSL_TPJAOS_V4.jpg', 'GMSL_TPJAOS_V4_199209_201708.txt',
                                                   'README_GMSL_folder_contents.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        # Actual execution
        self.data_collector = sea_level_rise.instance(log_to_stdout=False)
        last_request = serialize_date(
                deserialize_date('20170801221800.1234', self.data_collector.config['FTP_DATE_FORMAT']))
        self.data_collector.config['STATE_STRUCT']['last_modified'] = last_request
        self.data_collector.run()
        self.assertTrue(mock_FTP.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.FTP')
    def test_data_collection_invalid_data_from_server(self, mock_FTP, mock_Reader):
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['GMSL_TPJAOS_V4.jpg', 'GMSL_TPJAOS_V4_199209_201708.txt',
                                                   'README_GMSL_folder_contents.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        mock_Reader.return_value.get_data.return_value = ['Invalid data', 'Cannot be parsed']
        # Actual execution
        self.data_collector = sea_level_rise.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_FTP.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])

    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.FTP')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 11, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['GMSL_TPJAOS_V4.jpg', 'GMSL_TPJAOS_V4_199209_201708.txt',
                                                   'README_GMSL_folder_contents.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        data = [
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n']

        mock_Reader.return_value.get_data.return_value = data
        # Actual execution
        self.data_collector = sea_level_rise.instance(log_to_stdout=False)
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
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.FTP')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_items_not_saved(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 9, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['GMSL_TPJAOS_V4.jpg', 'GMSL_TPJAOS_V4_199209_201708.txt',
                                                   'README_GMSL_folder_contents.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        data = [
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n']

        mock_Reader.return_value.get_data.return_value = data
        # Actual execution
        self.data_collector = sea_level_rise.instance(log_to_stdout=False)
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

    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.Reader')
    @mock.patch('data_gathering_subsystem.data_modules.sea_level_rise.sea_level_rise.FTP')
    @mock.patch('data_gathering_subsystem.data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_FTP, mock_Reader):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking FTP operations
        mock_FTP.return_value.nlst.return_value = ['GMSL_TPJAOS_V4.jpg', 'GMSL_TPJAOS_V4_199209_201708.txt',
                                                   'README_GMSL_folder_contents.txt']
        mock_FTP.return_value.sendcmd.return_value = '123420170801221800'
        data = [
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n',
            '0  11  1993.0114746    466466 337280.00    -40.28     97.64    -40.64    -40.27     97.64    -40.63    -41.15\n',
            '0  12  1993.0386963    460890 334038.00    -44.20    100.97    -41.90    -44.19    100.96    -41.89    -41.74\n']

        mock_Reader.return_value.get_data.return_value = data
        # Actual execution
        self.data_collector = sea_level_rise.instance(log_to_stdout=False)
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
