from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.current_conditions.current_conditions as current_conditions

DATA = {"_id": "5a92b0dfdd571bdf0ff648c1", "station_id": 360630, "time_utc": 1519560000000, "_execution_id": None,
        "base": "stations", "clouds": {"all": 0}, "cod": 200, "coord": {"lon": 31.25, "lat": 30.06}, "dt": 1519560000,
        "location_id": 1, "main": {"temp": 22, "pressure": 1011, "humidity": 46, "temp_min": 22, "temp_max": 22},
        "name": "Cairo",
        "sys": {"type": 1, "id": 6392, "message": 0.0029, "country": "EG", "sunrise": 1519532697, "sunset": 1519573884},
        "visibility": 10000, "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "wind": {"speed": 2.1, "deg": 300}}

DATA_UNEXPECTED = {"_id": "5a92b0dfdd571bdf0ff648c1", "station_id": 360630, "time_utc": None,
                   "_execution_id": None, "base": "stations", "clouds": {"all": 0}, "cod": 200,
                   "coord": {"lon": 31.25, "lat": 30.06}, "dt": 1519560000, "location_id": 1,
                   "main": {"temp": 22, "pressure": 1011, "humidity": 46, "temp_min": 22, "temp_max": 22},
                   "name": "Cairo",
                   "sys": {"type": 1, "id": 6392, "message": 0.0029, "country": "EG", "sunrise": 1519532697,
                           "sunset": 1519573884}, "visibility": 10000,
                   "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                   "wind": {"speed": 2.1, "deg": 300}}


class TestCurrentConditions(TestCase):

    @classmethod
    def setUpClass(cls):
        current_conditions.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = current_conditions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(current_conditions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      current_conditions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = current_conditions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, current_conditions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_conversion_subsystem.data_converters.current_conditions.current_conditions.Location.objects.'
                'exists', Mock(return_value=True))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.current_conditions.current_conditions.Location.objects.'
                'exists', Mock(return_value=False))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    @mock.patch('yaml.load', Mock(return_value={'WEATHER_TYPES': [{'id': 200, 'foo': 'baz'}]}))
    def test_perform_data_conversion_indicators_have_unexpected_format(self):
        self.data_converter.state['created_indicators'] = False
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(0, len(self.data_converter.data))

    @mock.patch('data_conversion_subsystem.data_converters.current_conditions.current_conditions.'
                'WeatherType.objects.bulk_create', Mock(return_value=list(range(127))))
    def test_perform_data_conversion_with_all_values_set_weather_types_not_created(self):
        self.data_converter.state['weather_types_created'] = False
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(all([x for x in self.data_converter.data if
                             isinstance(x, current_conditions.CurrentConditionsObservation)]))

    def test_perform_data_conversion_with_unexpected_data_weather_types_created(self):
        self.data_converter.state['weather_types_created'] = True
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertTrue(self.data_converter.advisedly_no_data_converted)
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.current_conditions.current_conditions.'
                'CurrentConditionsObservation.objects.all', Mock())
    @mock.patch('data_conversion_subsystem.data_converters.current_conditions.current_conditions.'
                'CurrentConditionsObservation.objects.bulk_create', Mock(return_value=[1, 2, 3]))
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
