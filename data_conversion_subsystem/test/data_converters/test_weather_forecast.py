from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.weather_forecast.weather_forecast as weather_forecast

DATA = {"_id": "5a92ad0fdd571bdf0ff3f163", "station_id": 360630, "_execution_id": 2,
    "city": {"id": 360630, "name": "Cairo", "coord": {"lat": 30.0626, "lon": 31.2497}, "country": "EG"}, "cnt": 40,
    "cod": "200", "list": [{"dt": 1519570800,
        "main": {"temp": 21.99, "temp_min": 21.4, "temp_max": 21.99, "pressure": 1010.15, "sea_level": 1023.65,
            "grnd_level": 1010.15, "humidity": 33, "temp_kf": 0.59},
        "weather": [{"id": 803, "main": "Clouds", "description": "broken clouds", "icon": "04d"}],
        "clouds": {"all": 80}, "wind": {"speed": 1.91, "deg": 293.503}, "sys": {"pod": "d"},
        "dt_txt": "2018-02-25 15:00:00"}, {"dt": 1519581600,
        "main": {"temp": 15.64, "temp_min": 15.25, "temp_max": 15.64, "pressure": 1010.17, "sea_level": 1023.79,
            "grnd_level": 1010.17, "humidity": 51, "temp_kf": 0.39},
        "weather": [{"id": 803, "main": "Clouds", "description": "broken clouds", "icon": "04n"}],
        "clouds": {"all": 80}, "wind": {"speed": 1.32, "deg": 331.506}, "sys": {"pod": "n"},
        "dt_txt": "2018-02-25 18:00:00"}], "location_id": 1, "message": 0.0107}

DATA_UNEXPECTED = {"_id": "5a92ad0fdd571bdf0ff3f163", "station_id": 360630, "_execution_id": 2,
    "city": {"id": 360630, "name": "Cairo", "coord": {"lat": 30.0626, "lon": 31.2497}, "country": "EG"}, "cnt": 40,
    "cod": "200", "list": [{"dt": None,
        "main": {"temp": 21.99, "temp_min": 21.4, "temp_max": 21.99, "pressure": 1010.15, "sea_level": 1023.65,
            "grnd_level": 1010.15, "humidity": 33, "temp_kf": 0.59},
        "weather": [{"id": 803, "main": "Clouds", "description": "broken clouds", "icon": "04d"}],
        "clouds": {"all": 80}, "wind": {"speed": 1.91, "deg": 293.503}, "sys": {"pod": "d"},
        "dt_txt": "2018-02-25 15:00:00"}, {"dt": None,
        "main": {"temp": 15.64, "temp_min": 15.25, "temp_max": 15.64, "pressure": 1010.17, "sea_level": 1023.79,
            "grnd_level": 1010.17, "humidity": 51, "temp_kf": 0.39},
        "weather": [{"id": 803, "main": "Clouds", "description": "broken clouds", "icon": "04n"}],
        "clouds": {"all": 80}, "wind": {"speed": 1.32, "deg": 331.506}, "sys": {"pod": "n"},
        "dt_txt": "2018-02-25 18:00:00"}], "location_id": 1, "message": 0.0107}

MEASURES_PER_DATA = 2

class TestWeatherForecast(TestCase):

    @classmethod
    def setUpClass(cls):
        weather_forecast.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = weather_forecast.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        self.data_converter.remove_files()

    @mock.patch('data_conversion_subsystem.data_converters.weather_forecast.weather_forecast.WeatherType.objects.'
                'count', Mock(return_value=127))
    @mock.patch('data_conversion_subsystem.data_converters.weather_forecast.weather_forecast.Location.objects.'
                'count', Mock(return_value=304))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.weather_forecast.weather_forecast.WeatherType.objects.'
                'count', Mock(return_value=0))
    @mock.patch('data_conversion_subsystem.data_converters.weather_forecast.weather_forecast.Location.objects.'
                'count', Mock(return_value=0))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3 * MEASURES_PER_DATA, len(self.data_converter.data))
        self.assertTrue(all(
                [x for x in self.data_converter.data if isinstance(x, weather_forecast.WeatherForecastObservation)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('django.db.connection.cursor', Mock())
    @mock.patch('data_conversion_subsystem.data_converters.weather_forecast.weather_forecast.'
                'WeatherForecastObservation.objects.bulk_create', Mock(return_value=[1, 2, 3]))
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
