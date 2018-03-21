from unittest import TestCase
from global_config.config import GLOBAL_CONFIG
import utilities.util


class TestUtil(TestCase):

    def test_enum(self):
        enum_1 = utilities.util.enum('a', 'b', 'c')
        self.assertEqual(enum_1.a, 'a')
        self.assertEqual(enum_1.b, 'b')
        self.assertEqual(enum_1.c, 'c')

    def test_date_to_millis_since_epoch(self):
        from datetime import datetime
        from pytz import UTC, timezone

        # Positive cases
        epoch = datetime(1970, 1, 1, 0, 0, 0, 0, UTC)  # epoch is UNIX time, 01/01/1970 00:00:00 GTM
        epoch_expected = 0
        future_date = datetime(2000, 1, 1, 0, 0, 0, 0, UTC)
        future_expected = 946684800000
        past_date = datetime(1900, 1, 1, 0, 0, 0, 0, UTC)
        past_expected = -2208988800000
        self.assertEqual(epoch_expected, utilities.util.date_to_millis_since_epoch(epoch))
        self.assertEqual(future_expected, utilities.util.date_to_millis_since_epoch(future_date))
        self.assertEqual(past_expected, utilities.util.date_to_millis_since_epoch(past_date))

        # Negative case
        non_utc = timezone('US/Eastern')
        invalid_date = datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=non_utc)
        with self.assertRaises(ValueError):
            utilities.util.date_to_millis_since_epoch(invalid_date)

    def test_decimal_date_to_millis_since_epoch(self):

        epoch = 1970.0000  # epoch is UNIX time, 01/01/1970 00:00:00 GTM
        epoch_expected = 0
        future_date = 2000.0000
        future_expected = 946684800000
        past_date = 1900.0000
        past_expected = -2208988800000
        self.assertEqual(epoch_expected, utilities.util.decimal_date_to_millis_since_epoch(epoch))
        self.assertEqual(future_expected, utilities.util.decimal_date_to_millis_since_epoch(future_date))
        self.assertEqual(past_expected, utilities.util.decimal_date_to_millis_since_epoch(past_date))

    def test_recursive_makedir(self):
        from os.path import exists, isdir
        from os import getcwd
        from shutil import rmtree

        # Non existing directory
        non_existing_dir = './foo/baz/bar'
        existing_dir = getcwd()
        utilities.util.recursive_makedir(non_existing_dir)
        self.assertTrue(exists(non_existing_dir))

        # Now directory exists
        rmtree('./foo')
        utilities.util.recursive_makedir(existing_dir)
        self.assertTrue(exists(existing_dir))

        # Now path is a filepath
        non_existing_file = './foo/baz/bar.txt'
        utilities.util.recursive_makedir(non_existing_file, is_file=True)
        self.assertTrue(exists('./foo/baz'))
        self.assertTrue(isdir('./foo/baz'))
        rmtree('./foo')

    def test_get_config(self):
        from os import remove

        # Correct YAML syntax
        config_file = __file__.replace('py', 'config')
        with open(config_file, 'w+') as f:
            f.truncate()
            f.write('FOO: 1\n\n'
                    'BAR: {key1: value1, key2: 2}\n\n'
                    'BAZ: baz')
        config = utilities.util.get_config(__file__)
        self.assertIsNotNone(config)
        self.assertEqual(config['FOO'], 1)
        self.assertEqual(config['BAR'], {'key1': 'value1', 'key2': 2})
        self.assertEqual(config['BAZ'], 'baz')
        remove(config_file)

        # Incorrect YAML syntax
        with open(config_file, 'w+') as f:
            f.truncate()
            f.write('windows_drive: c:')
        with self.assertRaises(Exception):
            utilities.util.get_config(__file__)
        remove(config_file)

    def test_map_data_collector_path_to_state_file_path(self):
        file = '/temp/ClimateChangeApp/data_gathering_subsystem/data_modules/module/module.py'
        self.assertEqual('/temp/state/module.state', utilities.util.map_data_collector_path_to_state_file_path(file,
                         root_dir='/temp/state/'))

    def test_create_state_file(self):
        from os import remove
        from os.path import exists

        file = './script.state'
        utilities.util.create_state_file(file)
        self.assertTrue(exists(file))
        remove(file)

    def test_read_state(self):
        from json import dump
        from os import remove
        from os.path import exists

        # When file does not exist, 'repair_struct' is returned
        non_existing_file = './script.py'
        expected_file = GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'] + 'script.state'
        content = utilities.util.read_state(non_existing_file, repair_struct={'repair': True},
                                            root_dir=GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'])
        self.assertTrue(exists(expected_file))
        self.assertEqual(content, {'repair': True})

        # Invalid JSON file
        with open(expected_file, 'w') as f:
            f.truncate()
            f.write('{invalid_json: {missing_brace: true}')
        content = utilities.util.read_state(non_existing_file, repair_struct={'repair': True},
                                            root_dir=GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'])
        self.assertEqual(content, {'repair': True})

        # Valid JSON file
        valid_json = {'valid_json': True, 'reasons': [{'braces': True}, {'indent': None}, 'foo', 1]}
        with open(expected_file, 'w') as f:
            f.truncate()
            dump(valid_json, f)
        content = utilities.util.read_state(non_existing_file, repair_struct={'repair': True},
                                            root_dir=GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'])
        self.assertEqual(content, valid_json)
        remove(expected_file)

    def test_write_state_and_remove(self):
        from os.path import exists

        # Write state
        file = './script.py'
        expected_file = GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'] + 'script.state'
        content = {'valid_json': True, 'reasons': [{'braces': True}, {'indent': None}, 'foo', 1]}
        utilities.util.create_state_file(expected_file)
        self.assertTrue(exists(expected_file))
        utilities.util.write_state(content, file, root_dir=GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'])
        self.assertEqual(utilities.util.read_state(file, repair_struct={},
                root_dir=GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER']), content)
        utilities.util.remove_state_file(file, root_dir=GLOBAL_CONFIG['STATE_FILES_ROOT_FOLDER'])
        self.assertFalse(exists(expected_file))

    def test_serialize_date(self):
        from datetime import datetime
        from pytz import UTC, timezone

        # Positive cases
        epoch = datetime(1970, 1, 1, 0, 0, 0, 0, UTC)  # epoch is UNIX time, 01/01/1970 00:00:00 GTM
        expected = '1970-01-01T00:00:00Z'
        self.assertEqual(expected, utilities.util.serialize_date(epoch))
        self.assertIsNone(utilities.util.serialize_date(None))

        # Negative case
        non_utc = timezone('US/Eastern')
        invalid_date = datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=non_utc)
        with self.assertRaises(ValueError):
            utilities.util.serialize_date(invalid_date)

    def test_deserialize_date(self):
        from datetime import datetime
        from pytz import UTC

        date = '1970-01-01T0:0:0.0Z'
        expected = datetime(1970, 1, 1, 0, 0, 0, 0, UTC)  # epoch is UNIX time, 01/01/1970 00:00:00 GTM
        self.assertEqual(expected, utilities.util.deserialize_date(date))
        self.assertIsNone(utilities.util.deserialize_date(None))

    def test_get_module_name(self):
        file = '/foo/bar/baz/my_module.py'
        expected = 'my_module'
        self.assertEqual(expected, utilities.util.get_module_name(file))

    def test_get_exception_info(self):
        try:
            1 / 0
        except ZeroDivisionError as exception:
            info = utilities.util.get_exception_info(exception)
            self.assertEqual({'class': 'ZeroDivisionError', 'message': 'division by zero'}, info)

    def test_next_exponential_backoff(self):
        from utilities.util import TimeUnits

        backoff = {'value': 1, 'units': 's'}
        max_iterations = 11  # Each call multiplies 'value' * [2..10]. Max iterations to reach 1000 = 11 (1 * 2^10)
        max_backoff = 1000
        iteration_count = 0

        # Common case
        previous_value = backoff['value']
        value = backoff['value']
        for index in range(max_iterations):
            value, units = utilities.util.next_exponential_backoff(backoff, max_backoff)
            if value == max_backoff:
                break
            self.assertGreater(value, previous_value)
            iteration_count += 1
            previous_value = value
            backoff['value'] = value
            backoff['units'] = units
        self.assertLessEqual(iteration_count, max_iterations)
        self.assertEqual(max_backoff, value)

        # TimeUnits = NEVER case
        backoff = {'value': None, 'units': TimeUnits.NEVER}
        value, units = utilities.util.next_exponential_backoff(backoff, max_backoff)
        self.assertEqual(value, max_backoff)
        self.assertEqual(units, 's')

    def test_check_coordinates(self):
        cairo = {'_id': 1, 'country_code': 'EG', 'latitude': 30.06263, 'longitude': 31.24967}
        lat = 30.98765
        long = 31.43354
        # Positive case
        self.assertTrue(utilities.util.check_coordinates(cairo['latitude'], cairo['longitude'], lat, long))
        # Negative case
        self.assertFalse(utilities.util.check_coordinates(cairo['latitude'], cairo['longitude'], lat, long, margin=0.2))
        self.assertFalse(utilities.util.check_coordinates(cairo['latitude'], cairo['longitude'], lat, long, margin=0.3))
        # Limit case (positive)
        lat = 30.06263 + 0.2
        long = 31.24967 + 0.2
        self.assertTrue(utilities.util.check_coordinates(cairo['latitude'], cairo['longitude'], lat, long, margin=0.2))
        # Limit case (negative)
        lat = 30.06263 + 0.20001
        long = 31.24967 + 0.20001
        self.assertFalse(utilities.util.check_coordinates(cairo['latitude'], cairo['longitude'], lat, long, margin=0.2))

    def test_date_plus_timedelta_gt_now(self):
        from utilities.util import TimeUnits
        from datetime import datetime
        from pytz import UTC, timezone
        date = datetime.now(UTC)
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 5, 'units': TimeUnits.s}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.min}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.h}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.day}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': None, 'units': TimeUnits.NEVER}))
        date = date.replace(year=date.year - 1)
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.s}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.min}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.h}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.day}))

        # Negative case: Non-UTC date
        non_utc = timezone('US/Eastern')
        invalid_date = datetime.now().replace(tzinfo=non_utc)
        with self.assertRaises(ValueError):
            utilities.util.date_plus_timedelta_gt_now(invalid_date, {'value': 1, 'units': TimeUnits.day})

        # Negative case: Invalid TimeUnits value
        with self.assertRaises(AttributeError):
            utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.FOO})

        # Negative case: Invalid value, but not TimeUnits.
        with self.assertRaises(AttributeError):
            utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': "foo"})

    def test_time_limit(self):
        from time import sleep

        with self.assertRaises(TimeoutError):
            with utilities.util.time_limit(1):
                sleep(5)

    def test_parse_float(self):
        self.assertEqual(5.1, utilities.util.parse_float(5.1, nullable=True))
        self.assertEqual(5.1, utilities.util.parse_float(5.1, nullable=False))
        self.assertAlmostEqual(5.1, utilities.util.parse_float('5.1', nullable=True), 0.001)
        self.assertAlmostEqual(5.1, utilities.util.parse_float('5.1', nullable=False), 0.001)
        self.assertIsNone(utilities.util.parse_float('', nullable=True))
        self.assertIsNone(utilities.util.parse_float(None, nullable=True))
        with self.assertRaises(ValueError):
            utilities.util.parse_float('', nullable=False)
        with self.assertRaises(ValueError):
            utilities.util.parse_float(None, nullable=False)

    def test_parse_int(self):
        self.assertEqual(5, utilities.util.parse_int(5, nullable=True))
        self.assertEqual(5, utilities.util.parse_int(5, nullable=False))
        self.assertEqual(5, utilities.util.parse_int('5', nullable=True))
        self.assertEqual(5, utilities.util.parse_int('5', nullable=False))
        self.assertIsNone(utilities.util.parse_int('', nullable=True))
        self.assertIsNone(utilities.util.parse_int(None, nullable=True))
        with self.assertRaises(ValueError):
            utilities.util.parse_int('', nullable=False)
        with self.assertRaises(ValueError):
            utilities.util.parse_int(None, nullable=False)

    def test_parse_bool(self):
        self.assertEqual(True, utilities.util.parse_bool(True, nullable=True))
        self.assertEqual(False, utilities.util.parse_bool(False, nullable=False))
        self.assertTrue(utilities.util.parse_bool('5', nullable=True))
        self.assertTrue(utilities.util.parse_bool('TrUE', nullable=False))
        self.assertFalse(utilities.util.parse_bool('0', nullable=True))
        self.assertFalse(utilities.util.parse_bool('FAlsE', nullable=False))
        self.assertIsNone(utilities.util.parse_bool('foo', nullable=True))
        self.assertIsNone(utilities.util.parse_bool(None, nullable=True))
        with self.assertRaises(ValueError):
            utilities.util.parse_bool('', nullable=False)
        with self.assertRaises(ValueError):
            utilities.util.parse_bool(None, nullable=False)

    def test_compute_wind_direction(self):
        self.assertEqual('N', utilities.util.compute_wind_direction(349))
        self.assertEqual('N', utilities.util.compute_wind_direction(360))
        self.assertEqual('N', utilities.util.compute_wind_direction(0))
        self.assertEqual('N', utilities.util.compute_wind_direction(11))
        self.assertEqual('NNE', utilities.util.compute_wind_direction(12))
        self.assertEqual('NNE', utilities.util.compute_wind_direction(33))
        self.assertEqual('NE', utilities.util.compute_wind_direction(34))
        self.assertEqual('NE', utilities.util.compute_wind_direction(56))
        self.assertEqual('ENE', utilities.util.compute_wind_direction(57))
        self.assertEqual('ENE', utilities.util.compute_wind_direction(78))
        self.assertEqual('E', utilities.util.compute_wind_direction(79))
        self.assertEqual('E', utilities.util.compute_wind_direction(101))
        self.assertEqual('ESE', utilities.util.compute_wind_direction(102))
        self.assertEqual('ESE', utilities.util.compute_wind_direction(123))
        self.assertEqual('SE', utilities.util.compute_wind_direction(124))
        self.assertEqual('SE', utilities.util.compute_wind_direction(146))
        self.assertEqual('SSE', utilities.util.compute_wind_direction(147))
        self.assertEqual('SSE', utilities.util.compute_wind_direction(168))
        self.assertEqual('S', utilities.util.compute_wind_direction(169))
        self.assertEqual('S', utilities.util.compute_wind_direction(191))
        self.assertEqual('SSW', utilities.util.compute_wind_direction(192))
        self.assertEqual('SSW', utilities.util.compute_wind_direction(213))
        self.assertEqual('SW', utilities.util.compute_wind_direction(214))
        self.assertEqual('SW', utilities.util.compute_wind_direction(236))
        self.assertEqual('WSW', utilities.util.compute_wind_direction(237))
        self.assertEqual('WSW', utilities.util.compute_wind_direction(258))
        self.assertEqual('W', utilities.util.compute_wind_direction(259))
        self.assertEqual('W', utilities.util.compute_wind_direction(281))
        self.assertEqual('WNW', utilities.util.compute_wind_direction(282))
        self.assertEqual('WNW', utilities.util.compute_wind_direction(303))
        self.assertEqual('NW', utilities.util.compute_wind_direction(304))
        self.assertEqual('NW', utilities.util.compute_wind_direction(326))
        self.assertEqual('NNW', utilities.util.compute_wind_direction(327))
        self.assertEqual('NNW', utilities.util.compute_wind_direction(348))
        self.assertIsNone(utilities.util.compute_wind_direction(None))
