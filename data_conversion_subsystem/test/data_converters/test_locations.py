from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.locations.locations as locations

DATA = {"_id": 51, "country_code": "AE", "elevation": {"value": "", "units": "m"}, "last_modified": 1417478400000,
    "latitude": 25.0657, "longitude": 55.17128, "name": "Dubai", "owm_station_id": "292223", "population": "1137347",
    "timezone": "Asia/Dubai", "waqi_station_id": None, "wunderground_loc_id": "/q/zmw:00000.1.41194"}

DATA_UNEXPECTED = {"_id": 51, "country_code": "AE", "elevation": {"value": "", "units": "m"}, "last_modified": None,
    "latitude": 25.0657, "longitude": 55.17128, "name": "Dubai", "owm_station_id": "292223", "population": "1137347",
    "timezone": "Asia/Dubai", "waqi_station_id": None, "wunderground_loc_id": "/q/zmw:00000.1.41194"}


class TestLocations(TestCase):

    @classmethod
    def setUpClass(cls):
        locations.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = locations.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(locations.instance(), locations.instance())
        i1 = locations.instance()
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, locations.instance())

    @mock.patch('data_conversion_subsystem.data_converters.locations.locations.Country.objects.count',
                Mock(return_value=304))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.locations.locations.Country.objects.count',
                Mock(return_value=0))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, locations.Location)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.locations.locations.Location.objects')
    def test_save_data_when_no_locations_exist(self, mock_location_objects):
        mock_location_objects.filter.return_value.exists.return_value = False
        obj = Mock()
        obj.id = 1
        mock_location_objects.bulk_create.return_value = [1, 2, 3]
        self.data_converter.data = [obj, obj, obj]
        self.data_converter._save_data()
        self.assertEqual(3, mock_location_objects.filter.return_value.exists.call_count)
        self.assertEqual(1, mock_location_objects.bulk_create.call_count)
        self.assertEqual(3, self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.locations.locations.Location.objects')
    def test_save_data_when_all_locations_exist(self, mock_location_objects):
        mock_location_objects.filter.return_value.exists.return_value = True
        mock_location_objects.filter.return_value.update = Mock()
        obj = Mock()
        obj.id = 1
        self.data_converter.data = [obj, obj, obj]
        self.data_converter._save_data()
        self.assertEqual(3, mock_location_objects.filter.return_value.exists.call_count)
        self.assertEqual(3, mock_location_objects.filter.return_value.update.call_count)
        self.assertEqual(0, mock_location_objects.bulk_create.call_count)
        self.assertEqual(3, self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.locations.locations.Location.objects')
    def test_save_data_when_some_locations_exist(self, mock_location_objects):
        mock_location_objects.filter.return_value.exists = Mock(side_effect=[True, False, True])
        mock_location_objects.filter.return_value.update = Mock()
        mock_location_objects.bulk_create.return_value = [2]
        obj = Mock()
        obj.id = 1
        self.data_converter.data = [obj, obj, obj]
        self.data_converter._save_data()
        self.assertEqual(3, mock_location_objects.filter.return_value.exists.call_count)
        self.assertEqual(1, mock_location_objects.bulk_create.call_count)
        self.assertEqual(3, self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)

    def test_save_data_with_no_data(self):
        self.data_converter.data = None
        self.data_converter._save_data()
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)
