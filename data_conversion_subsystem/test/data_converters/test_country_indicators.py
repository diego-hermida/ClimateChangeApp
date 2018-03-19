from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.country_indicators.country_indicators as country_indicators


DATA = {"_id": "5a92ac02dd571bdf0ff2456c", "country_id": "ES", "indicator": "SP.POP.TOTL", "year": "2016",
    "_execution_id": 1, "value": "46443959"}

DATA_UNEXPECTED = {"_id": "5a92ac02dd571bdf0ff2456c", "country_id": "ES", "indicator": "SP.POP.TOTL", "year": None,
    "_execution_id": 1, "value": "46443959"}


class TestCountryIndicators(TestCase):

    @classmethod
    def setUpClass(cls):
        country_indicators.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, country_indicators.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_conversion_subsystem.data_converters.country_indicators.country_indicators.Country.objects.count',
                Mock(return_value=304))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.country_indicators.country_indicators.Country.objects.count',
                Mock(return_value=0))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    @mock.patch('yaml.load', Mock(return_value={'INDICATOR_DETAILS': {'indicator1': {'name': 'Indicator 1'}}}))
    def test_perform_data_conversion_indicators_have_unexpected_format(self):
        self.data_converter.state['created_indicators'] = False
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(0, len(self.data_converter.data))

    @mock.patch('data_conversion_subsystem.data_converters.country_indicators.country_indicators.IndicatorDetails.'
                'objects.bulk_create', Mock(return_value=list(range(54))))
    def test_perform_data_conversion_with_all_values_set_indicators_not_created(self):
        self.data_converter.state['created_indicators'] = False
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(
                all([x for x in self.data_converter.data if isinstance(x, country_indicators.CountryIndicator)]))

    def test_perform_data_conversion_with_unexpected_data_indicators_created(self):
        self.data_converter.state['created_indicators'] = True
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertTrue(self.data_converter.advisedly_no_data_converted)
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.country_indicators.country_indicators.CountryIndicator.'
                'objects.bulk_create', Mock(return_value=[1, 2, 3]))
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
