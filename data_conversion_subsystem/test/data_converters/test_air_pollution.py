from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.air_pollution.air_pollution as air_pollution

DATA = {"_id": "5a92ad36dd571bdf0ff3f1ab", "station_id": 8179, "time_utc": "1519578000000", "_execution_id": 2,
        "data": {"aqi": 170, "idx": 8179, "attributions": [
            {"url": "http://cpcb.nic.in/", "name": "CPCB - India Central Pollution Control Board"}],
                 "city": {"geo": [28.6522734, 77.1564994], "name": "Shadipur, Delhi",
                          "url": "http://aqicn.org/city/delhi/shadipur/"}, "dominentpol": "pm25",
                 "iaqi": {"co": {"v": 1.3}, "no2": {"v": 9.3}, "o3": {"v": 22.8}, "pm25": {"v": 170},
                          "so2": {"v": 4.7}}, "time": {"s": "2018-02-25 17:00:00", "tz": "+05:30", "v": 1519578000}},
        "location_id": 2, "status": "ok"}

DATA_2 = {"_id": "5a92ad36dd571bdf0ff3f1ab", "station_id": 8179, "time_utc": "1519578000000", "_execution_id": 2,
          "data": {"aqi": 170, "idx": 8179, "attributions": [
              {"url": "http://www.foo.com", "name": "FOO - The Foo-Baz-Bar Pollution Control Board"}],
                   "city": {"geo": [28.6522734, 77.1564994], "name": "Shadipur, Delhi",
                            "url": "http://aqicn.org/city/delhi/shadipur/"}, "dominentpol": "pm25",
                   "iaqi": {"co": {"v": 1.3}, "no2": {"v": 9.3}, "o3": {"v": 22.8}, "pm25": {"v": 170},
                            "so2": {"v": 4.7}}, "time": {"s": "2018-02-25 17:00:00", "tz": "+05:30", "v": 1519578000}},
          "location_id": 2, "status": "ok"}

DATA_3 = {"_id": "5a92ad36dd571bdf0ff3f1ab", "station_id": 8179, "time_utc": "1519578000000", "_execution_id": 2,
          "data": {"aqi": 170, "idx": 8179, "attributions": [],
                   "city": {"geo": [28.6522734, 77.1564994], "name": "Shadipur, Delhi",
                            "url": "http://aqicn.org/city/delhi/shadipur/"}, "dominentpol": "pm25",
                   "iaqi": {"co": {"v": 1.3}, "no2": {"v": 9.3}, "o3": {"v": 22.8}, "pm25": {"v": 170},
                            "so2": {"v": 4.7}}, "time": {"s": "2018-02-25 17:00:00", "tz": "+05:30", "v": 1519578000}},
          "location_id": 2, "status": "ok"}

DATA_4 = {"_id": "5a92ad36dd571bdf0ff3f1ab", "station_id": 8179, "time_utc": "1519578000000", "_execution_id": 2,
          "data": {"aqi": 170, "idx": 8179, "attributions": [],
                   "city": {"geo": [28.6522734, 77.1564994], "name": "Shadipur, Delhi",
                            "url": "http://aqicn.org/city/delhi/shadipur/"}, "dominentpol": "pm25",
                   "iaqi": {"co": {"v": 1.3}, "no2": {"v": 9.3}, "o3": {"v": 22.8}, "pm25": {"v": 170},
                            "so2": {"v": 4.7}}, "time": {"s": "2018-02-25 17:00:00", "tz": "+05:30", "v": 1519578000}},
          "location_id": 1, "status": "ok"}

DATA_UNEXPECTED = {"_id": "5a92ad36dd571bdf0ff3f1ab", "station_id": 8179, "time_utc": None, "_execution_id": 2,
                   "data": {"aqi": 170, "idx": 8179, "attributions": [
                       {"url": "http://cpcb.nic.in/", "name": "CPCB - India Central Pollution Control Board"}],
                            "city": {"geo": [28.6522734, 77.1564994], "name": "Shadipur, Delhi",
                                     "url": "http://aqicn.org/city/delhi/shadipur/"}, "dominentpol": "pm25",
                            "iaqi": {"co": {"v": 1.3}, "no2": {"v": 9.3}, "o3": {"v": 22.8}, "pm25": {"v": 170},
                                     "so2": {"v": 4.7}},
                            "time": {"s": "2018-02-25 17:00:00", "tz": "+05:30", "v": 1519578000}}, "location_id": 2,
                   "status": "ok"}


class TestAirPollution(TestCase):

    @classmethod
    def setUpClass(cls):
        air_pollution.instance(log_to_stdout=False, log_to_file=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False), air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, air_pollution.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_conversion_subsystem.data_converters.air_pollution.air_pollution.Location.objects.exists',
                Mock(return_value=True))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.air_pollution.air_pollution.Location.objects.exists',
                Mock(return_value=False))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    def test_perform_data_conversion_data_without_attributions(self):
        self.data_converter.elements_to_convert = [DATA_3, DATA_3, DATA_3]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertDictEqual({}, self.data_converter.state['cache'])
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, air_pollution.AirPollutionMeasure)]))

    @mock.patch('data_conversion_subsystem.data_converters.air_pollution.air_pollution.Location.objects.get', Mock())
    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertListEqual(DATA['data']['attributions'], self.data_converter.state['cache'][2])
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, air_pollution.AirPollutionMeasure)]))

    @mock.patch('data_conversion_subsystem.data_converters.air_pollution.air_pollution.Location.objects.get', Mock())
    def test_perform_data_conversion_with_all_values_set_multiple_attributions(self):
        self.data_converter.elements_to_convert = [DATA, DATA_2, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        l = DATA['data']['attributions']
        l2 = DATA_2['data']['attributions']
        self.assertListEqual(l + l2, self.data_converter.state['cache'][2])
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, air_pollution.AirPollutionMeasure)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.air_pollution.air_pollution.AirPollutionMeasure.objects.'
                'bulk_create')
    @mock.patch('data_conversion_subsystem.data_converters.air_pollution.air_pollution.Location.objects.get')
    def test_save_data(self, mock_locations, mock_bulk_create):
        self.data_converter.elements_to_convert = [DATA, DATA_2, DATA_3, DATA_4]
        self.data_converter._perform_data_conversion()
        mock_bulk_create.return_value = self.data_converter.data
        self.data_converter._save_data()
        self.assertEqual(4, self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)
        self.assertEqual(3, mock_locations.call_count)

    def test_save_data_with_no_data(self):
        self.data_converter.data = None
        self.data_converter._save_data()
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)
