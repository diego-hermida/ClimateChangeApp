from json import dumps
from unittest import TestCase, main, mock
from unittest.mock import Mock

import data_modules.countries.countries as countries


class TestCountries(TestCase):

    @classmethod
    def setUpClass(cls):
        countries.instance(log_to_stdout=False).remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_correct_data_collection(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.is_empty.return_value = False
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': 1}, {'_id': 2}, {'_id': 3}, {'_id': 4}, {'_id': 5}, {'_id': 6}]
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps([{"page": 1, "pages": 1, "per_page": "10000", "total": 6}, [
            {"id": "ABW", "iso2Code": "AW", "name": "Aruba",
             "region": {"id": "LCN", "value": "Latin America & Caribbean "}, "adminregion": {"id": "", "value": ""},
             "incomeLevel": {"id": "HIC", "value": "High income"},
             "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad",
             "longitude": "-70.0167", "latitude": "12.5167"},
            {"id": "AFG", "iso2Code": "AF", "name": "Afghanistan", "region": {"id": "SAS", "value": "South Asia"},
             "adminregion": {"id": "SAS", "value": "South Asia"}, "incomeLevel": {"id": "LIC", "value": "Low income"},
             "lendingType": {"id": "IDX", "value": "IDA"}, "capitalCity": "Kabul", "longitude": "69.1761",
             "latitude": "34.5228"},
            {"id": "AFR", "iso2Code": "A9", "name": "Africa", "region": {"id": "NA", "value": "Aggregates"},
             "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "NA", "value": "Aggregates"},
             "lendingType": {"id": "", "value": "Aggregates"}, "capitalCity": "", "longitude": "", "latitude": ""},
            {"id": "AGO", "iso2Code": "AO", "name": "Angola", "region": {"id": "SSF", "value": "Sub-Saharan Africa "},
             "adminregion": {"id": "SSA", "value": "Sub-Saharan Africa (excluding high income)"},
             "incomeLevel": {"id": "LMC", "value": "Lower middle income"},
             "lendingType": {"id": "IBD", "value": "IBRD"}, "capitalCity": "Luanda", "longitude": "13.242",
             "latitude": "-8.81155"}, {"id": "ALB", "iso2Code": "AL", "name": "Albania",
              "region": {"id": "ECS", "value": "Europe & Central Asia"}, "adminregion": {"id": "ECA",
              "value": "Europe & Central Asia (excluding high income)"}, "incomeLevel": {"id": "UMC", "value":
              "Upper middle income"}, "lendingType": {"id": "IBD", "value": "IBRD"}, "capitalCity": "Tirane",
              "longitude": "19.8172", "latitude": "41.3317"},
            {"id": "AND", "iso2Code": "AD", "name": "Andorra",
             "region": {"id": "ECS", "value": "Europe & Central Asia"}, "adminregion": {"id": "", "value": ""},
             "incomeLevel": {"id": "HIC", "value": "High income"},
             "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Andorra la Vella",
             "longitude": "1.5218", "latitude": "42.5075"}]]).encode()
        # Actual execution
        self.data_collector = countries.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(6, self.data_collector.state['data_elements'])
        self.assertEqual(6, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['UPDATE_FREQUENCY'], self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_no_countries(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = []
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps([{"page": 1, "pages": 1, "per_page": "10000", "total": 0}, []]).encode()
        # Actual execution
        self.data_collector = countries.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertFalse(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['update_frequency'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_invalid_data_from_server(self, mock_collection, mock_requests):
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps([{"page": 1, "pages": 1, "per_page": "10000", "total": 2}, ['invalid data',
                {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region": {"id": "LCN", "value": "Latin America & "
                "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High "
                "income"}, "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad",
                "longitude": "-70.0167", "latitude": "12.5167"}]]).encode()
        # Actual execution
        self.data_collector = countries.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertFalse(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])


    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_rejected_request_from_server(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': 1}]
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'error': 500, 'message': 'Server is unavailable.'}).encode()
        # Actual execution
        self.data_collector = countries.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertFalse(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': 1}, {'_id': 2}, {'_id': 3}, {'_id': 4}, {'_id': 5}, {'_id': 6}, {'_id': 7},
                                      {'_id': 8}, {'_id': 9}]
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps([{"page": 1, "pages": 1, "per_page": "10000", "total": 10}, [
            {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region": {"id": "LCN", "value": "Latin America & "
            "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High income"},
            "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad", "longitude":
            "-70.0167", "latitude": "12.5167"}, {"id": "AFG", "iso2Code": "AF", "name": "Afghanistan", "region": {"id":
            "SAS", "value": "South Asia"}, "adminregion": {"id": "SAS", "value": "South Asia"}, "incomeLevel": {"id":
            "LIC", "value": "Low income"}, "lendingType": {"id": "IDX", "value": "IDA"}, "capitalCity": "Kabul",
            "longitude": "69.1761", "latitude": "34.5228"}, {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region":
            {"id": "LCN", "value": "Latin America & "
            "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High income"},
            "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad", "longitude":
            "-70.0167", "latitude": "12.5167"}, {"id": "AFG", "iso2Code": "AF", "name": "Afghanistan", "region": {"id":
            "SAS", "value": "South Asia"}, "adminregion": {"id": "SAS", "value": "South Asia"}, "incomeLevel": {"id":
            "LIC", "value": "Low income"}, "lendingType": {"id": "IDX", "value": "IDA"}, "capitalCity": "Kabul",
            "longitude": "69.1761", "latitude": "34.5228"}, {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region":
            {"id": "LCN", "value": "Latin America & "
            "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High income"},
            "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad", "longitude":
            "-70.0167", "latitude": "12.5167"}, {"id": "AFG", "iso2Code": "AF", "name": "Afghanistan", "region": {"id":
            "SAS", "value": "South Asia"}, "adminregion": {"id": "SAS", "value": "South Asia"}, "incomeLevel": {"id":
            "LIC", "value": "Low income"}, "lendingType": {"id": "IDX", "value": "IDA"}, "capitalCity": "Kabul",
            "longitude": "69.1761", "latitude": "34.5228"}, {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region":
            {"id": "LCN", "value": "Latin America & "
            "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High income"},
            "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad", "longitude":
            "-70.0167", "latitude": "12.5167"}, {"id": "AFG", "iso2Code": "AF", "name": "Afghanistan", "region": {"id":
            "SAS", "value": "South Asia"}, "adminregion": {"id": "SAS", "value": "South Asia"}, "incomeLevel": {"id":
            "LIC", "value": "Low income"}, "lendingType": {"id": "IDX", "value": "IDA"}, "capitalCity": "Kabul",
            "longitude": "69.1761", "latitude": "34.5228"}, {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region":
            {"id": "LCN", "value": "Latin America & "
            "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High income"},
            "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad", "longitude":
            "-70.0167", "latitude": "12.5167"}, {"id": "AFG", "iso2Code": "AF", "name": "Afghanistan", "region": {"id":
            "SAS", "value": "South Asia"}, "adminregion": {"id": "SAS", "value": "South Asia"}, "incomeLevel": {"id":
            "LIC", "value": "Low income"}, "lendingType": {"id": "IDX", "value": "IDA"}, "capitalCity": "Kabul",
            "longitude": "69.1761", "latitude": "34.5228"}]]).encode()
        # Actual execution
        self.data_collector = countries.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(10, self.data_collector.state['data_elements'])
        self.assertEqual(9, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['UPDATE_FREQUENCY'], self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_collector.data_collector.MongoDBCollection')
    def test_data_collection_with_too_much_items_not_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.insert_many.return_value = insert_result = Mock()
        insert_result.inserted_ids = [{'_id': 1}]
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps([{"page": 1, "pages": 1, "per_page": "10000", "total": 2}, [
            {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region": {"id": "LCN", "value": "Latin America & "
            "Caribbean "}, "adminregion": {"id": "", "value": ""}, "incomeLevel": {"id": "HIC", "value": "High "
            "income"}, "lendingType": {"id": "LNX", "value": "Not classified"}, "capitalCity": "Oranjestad",
            "longitude": "-70.0167", "latitude": "12.5167"}, {"id": "ABW", "iso2Code": "AW", "name": "Aruba", "region":
            {"id": "LCN", "value": "Latin America & Caribbean"}, "adminregion": {"id": "", "value": ""}, "incomeLevel":
            {"id": "HIC", "value": "High income"}, "lendingType": {"id": "LNX", "value": "Not classified"},
            "capitalCity": "Oranjestad", "longitude": "-70.0167", "latitude": "12.5167"}]]).encode()
        # Actual execution
        self.data_collector = countries.instance(log_to_stdout=False)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertEqual(self.data_collector.config['STATE_STRUCT']['update_frequency'],
                         self.data_collector.state['update_frequency'])
