from unittest import TestCase, main

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
        from os.path import exists
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
        from global_config.global_config import CONFIG

        file = '/foo/bar/baz/script.py'
        self.assertEqual(CONFIG['STATE_FILES_ROOT_FOLDER'] + 'script.state',
                         utilities.util.map_data_collector_path_to_state_file_path(file))

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
        from global_config.global_config import CONFIG

        # When file does not exist, 'repair_struct' is returned
        non_existing_file = './script.py'
        expected_file = CONFIG['STATE_FILES_ROOT_FOLDER'] + 'script.state'
        content = utilities.util.read_state(non_existing_file, repair_struct={'repair': True})
        self.assertTrue(exists(expected_file))
        self.assertEqual(content, {'repair': True})

        # Invalid JSON file
        with open(expected_file, 'w') as f:
            f.truncate()
            f.write('{invalid_json: {missing_brace: true}')
        content = utilities.util.read_state(non_existing_file, repair_struct={'repair': True})
        self.assertEqual(content, {'repair': True})

        # Valid JSON file
        valid_json = {'valid_json': True, 'reasons': [{'braces': True}, {'indent': None}, 'foo', 1]}
        with open(expected_file, 'w') as f:
            f.truncate()
            dump(valid_json, f)
        content = utilities.util.read_state(non_existing_file, repair_struct={'repair': True})
        self.assertEqual(content, valid_json)
        remove(expected_file)

    def test_write_state_and_remove(self):
        from os.path import exists
        from global_config.global_config import CONFIG

        # Write state
        file = './script.py'
        expected_file = CONFIG['STATE_FILES_ROOT_FOLDER'] + 'script.state'
        content = {'valid_json': True, 'reasons': [{'braces': True}, {'indent': None}, 'foo', 1]}
        utilities.util.create_state_file(expected_file)
        self.assertTrue(exists(expected_file))
        utilities.util.write_state(content, file)
        self.assertEqual(utilities.util.read_state(file, repair_struct={}), content)

        utilities.util.remove_state_file(file)
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
        for index in range(max_iterations):
            previous_value = backoff['value']
            utilities.util.next_exponential_backoff(backoff, max_backoff)
            if backoff['value'] == max_backoff:
                break
            self.assertGreater(backoff['value'], previous_value)
            iteration_count += 1
        self.assertLessEqual(iteration_count, max_iterations)
        self.assertEqual(max_backoff, backoff['value'])

        # TimeUnits = NEVER case
        backoff = {'value': None, 'units': TimeUnits.NEVER}
        utilities.util.next_exponential_backoff(backoff, max_backoff)
        self.assertEqual({'value': max_backoff, 'units': 's'}, backoff)

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

        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(None, {'value': 1, 'units': TimeUnits.year}))
        date = datetime.now(UTC)
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 5, 'units': TimeUnits.s}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.min}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.h}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.day}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.week}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.month}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.year}))
        self.assertFalse(utilities.util.date_plus_timedelta_gt_now(date, {'value': None, 'units': TimeUnits.NEVER}))
        date = date.replace(year=date.year - 1)
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.s}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.min}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.h}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.day}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.week}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.month}))
        self.assertTrue(utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.year}))

        # Negative case: Non-UTC date
        non_utc = timezone('US/Eastern')
        invalid_date = datetime.now().replace(tzinfo=non_utc)
        with self.assertRaises(ValueError):
            utilities.util.date_plus_timedelta_gt_now(invalid_date, {'value': 1, 'units': TimeUnits.year})

        # Negative case: Invalid TimeUnits value
        with self.assertRaises(AttributeError):
            utilities.util.date_plus_timedelta_gt_now(date, {'value': 1, 'units': TimeUnits.FOO})

    def test_time_limit(self):
        from time import sleep

        with self.assertRaises(TimeoutError):
            with utilities.util.time_limit(1):
                sleep(5)
