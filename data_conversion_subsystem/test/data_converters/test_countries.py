from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.countries.countries as countries

DATA = {"_id": "AW", "name": "Aruba", "region": {"id": "LCN", "value": "Latin America & Caribbean "},
    "incomeLevel": {"id": "HIC", "value": "High income"}, "capitalCity": "Oranjestad", "longitude": "-70.0167",
    "latitude": "12.5167", "iso3": "ABW", "_execution_id": 1}

DATA_UNEXPECTED = {"_id": None, "name": None, "region": {"id": "LCN", "value": "Latin America & Caribbean"},
    "incomeLevel": {"id": "HIC", "value": "High income"}, "capitalCity": "Oranjestad", "longitude": "-70.0167",
    "latitude": "12.5167", "iso3": "ABW", "_execution_id": 1}


class TestCountries(TestCase):

    @classmethod
    def setUpClass(cls):
        countries.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = countries.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        self.data_converter.remove_files()

    @mock.patch('data_conversion_subsystem.data_converters.countries.countries.IncomeLevel.objects.create',
                Mock(return_value=countries.IncomeLevel(iso3_code='HIC', name='High income')))
    @mock.patch('data_conversion_subsystem.data_converters.countries.countries.Region.objects.create',
                Mock(return_value=countries.Region(iso3_code='LCN', name='Latin America & Caribbean')))
    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(self.data_converter.state['created_regions'])
        self.assertTrue(self.data_converter.state['created_income_levels'])
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, countries.Country)]))

    @mock.patch('data_conversion_subsystem.data_converters.countries.countries.IncomeLevel.objects.all',
                Mock(return_value=[]))
    @mock.patch('data_conversion_subsystem.data_converters.countries.countries.Region.objects.all',
                Mock(return_value=[]))
    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.state['created_regions'] = True
        self.data_converter.state['created_income_levels'] = True
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.countries.countries.Country.objects.bulk_create',
                Mock(return_value=[1, 2, 3]))
    def test_save_data(self):
        self.data_converter.data = [1, 2, 3]
        self.data_converter._save_data()
        self.assertEqual(3, self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)

    def test_save_data_with_no_data(self):
        self.data_converter.data = None
        self.data_converter._save_data()
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)
