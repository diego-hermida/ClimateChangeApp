from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock

import data_gathering_subsystem.data_modules.historical_weather.historical_weather as historical_weather

DATA = {"response": {"version": "0.1", "termsofService": "http://www.wunderground.com/weather/api/d/terms.html",
                     "features": {"history": 1}}, "history": {
    "date": {"pretty": "April 5, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "12", "min": "00",
             "tzname": "America/Los_Angeles"},
    "utcdate": {"pretty": "April 5, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "19", "min": "00",
                "tzname": "UTC"}, "observations": [{
        "date": {"pretty": "12:56 AM PDT on April 05, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "00",
                 "min": "56", "tzname": "America/Los_Angeles"},
        "utcdate": {"pretty": "7:56 AM GMT on April 05, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "07",
                    "min": "56", "tzname": "UTC"}, "tempm": "10.0", "tempi": "50.0", "dewptm": "7.2", "dewpti": "45.0",
        "hum": "83", "wspdm": "0.0", "wspdi": "0.0", "wgustm": "-9999.0", "wgusti": "-9999.0", "wdird": "0",
        "wdire": "North", "vism": "16.1", "visi": "10.0", "pressurem": "1004.8", "pressurei": "29.68",
        "windchillm": "-999", "windchilli": "-999", "heatindexm": "-9999", "heatindexi": "-9999", "precipm": "-9999.00",
        "precipi": "-9999.00", "conds": "Mostly Cloudy", "icon": "mostlycloudy", "fog": "0", "rain": "0", "snow": "0",
        "hail": "0", "thunder": "0", "tornado": "0",
        "metar": "METAR KSFO 050756Z 00000KT 10SM FEW036 BKN046 BKN055 10/07 A2967 RMK AO2 SLP048 T01000072 401390094"}, ],
    "dailysummary": [{
        "date": {"pretty": "12:00 PM PDT on April 05, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "12",
                 "min": "00", "tzname": "America/Los_Angeles"}, "fog": "0", "rain": "1", "snow": "0",
        "snowfallm": "0.00", "snowfalli": "0.00", "monthtodatesnowfallm": "", "monthtodatesnowfalli": "",
        "since1julsnowfallm": "", "since1julsnowfalli": "", "snowdepthm": "", "snowdepthi": "", "hail": "0",
        "thunder": "0", "tornado": "0", "meantempm": "11", "meantempi": "52", "meandewptm": "7", "meandewpti": "44",
        "meanpressurem": "1012", "meanpressurei": "29.88", "meanwindspdm": "11", "meanwindspdi": "7", "meanwdire": "",
        "meanwdird": "255", "meanvism": "15", "meanvisi": "10", "humidity": "", "maxtempm": "14", "maxtempi": "57",
        "mintempm": "9", "mintempi": "48", "maxhumidity": "93", "minhumidity": "59", "maxdewptm": "8",
        "maxdewpti": "46", "mindewptm": "6", "mindewpti": "42", "maxpressurem": "1020", "maxpressurei": "30.12",
        "minpressurem": "1005", "minpressurei": "29.67", "maxwspdm": "34", "maxwspdi": "21", "minwspdm": "0",
        "minwspdi": "0", "maxvism": "16", "maxvisi": "10", "minvism": "13", "minvisi": "8", "gdegreedays": "2",
        "heatingdegreedays": "12", "coolingdegreedays": "0", "precipm": "6.86", "precipi": "0.27", "precipsource": "",
        "heatingdegreedaysnormal": "", "monthtodateheatingdegreedays": "", "monthtodateheatingdegreedaysnormal": "",
        "since1sepheatingdegreedays": "", "since1sepheatingdegreedaysnormal": "", "since1julheatingdegreedays": "",
        "since1julheatingdegreedaysnormal": "", "coolingdegreedaysnormal": "", "monthtodatecoolingdegreedays": "",
        "monthtodatecoolingdegreedaysnormal:": "", "since1sepcoolingdegreedays": "",
        "since1sepcoolingdegreedaysnormal": "", "since1jancoolingdegreedays": "",
        "since1jancoolingdegreedaysnormal": ""}]}}

DATA = dumps(DATA).encode()

MISSING_DATA = {"response": {"version": "0.1", "termsofService": "http://www.wunderground.com/weather/api/d/terms.html",
                             "features": {"history": 1}}, "history": {
    "date": {"pretty": "April 5, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "12", "min": "00",
             "tzname": "America/Los_Angeles"},
    "utcdate": {"pretty": "April 5, 2006", "year": "2006", "mon": "04", "mday": "05", "hour": "19", "min": "00",
                "tzname": "UTC"}, "observations": [], "dailysummary": []}}
MISSING_DATA = dumps(MISSING_DATA).encode()


class TestHistoricalWeather(TestCase):

    @classmethod
    def setUpClass(cls):
        historical_weather.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(historical_weather.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      historical_weather.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = historical_weather.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, historical_weather.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.read_state')
    @mock.patch('requests.get')
    def test_daily_requests_is_properly_reset(self, mock_requests, mock_state):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 10
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'location_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2},
                     {'location_id': 3, 'name': 'City 3', 'wunderground_loc_id': 3},
                     {'location_id': 4, 'name': 'City 4', 'wunderground_loc_id': 4},
                     {'location_id': 5, 'name': 'City 5', 'wunderground_loc_id': 5},
                     {'location_id': 6, 'name': 'City 6', 'wunderground_loc_id': 6},
                     {'location_id': 7, 'name': 'City 7', 'wunderground_loc_id': 7},
                     {'location_id': 8, 'name': 'City 8', 'wunderground_loc_id': 8},
                     {'location_id': 9, 'name': 'City 9', 'wunderground_loc_id': 9},
                     {'location_id': 10, 'name': 'City 10', 'wunderground_loc_id': 10}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 10, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Mocking read_state
        mock_state.return_value = {"update_frequency": {"value": 1, "units": "min"},
                                   "last_request": "2018-01-18T08:35:13.536796Z", "data_elements": None,
                                   "inserted_elements": None, "restart_required": False, "last_error": None,
                                   "error": None, "errors": {}, "backoff_time": {"value": 1, "units": "s"},
                                   "missing_data_check": False, "current_date": None,
                                   "missing_data_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                                   "consecutive_unmeasured_days": 0,
                                   "tokens": {"5f06ae04f7342abf": {"daily_requests": 1, "usable": False},
                                              "e63c2d687265be99": {"daily_requests": 1, "usable": False},
                                              "4ea749ef53da4c65": {"daily_requests": 1, "usable": False},
                                              "3d93ef701440b478": {"daily_requests": 1, "usable": False},
                                              "bb866b8bda7036f4": {"daily_requests": 1, "usable": False},
                                              "8649251baef91434": {"daily_requests": 1, "usable": False},
                                              "0e85d055e5337977": {"daily_requests": 1, "usable": False},
                                              "330521663b1024c9": {"daily_requests": 1, "usable": False},
                                              "9309f4166988f1e3": {"daily_requests": 1, "usable": False},
                                              "5e1dd9d990fef0f8": {"daily_requests": 1, "usable": False}}}
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_DAILY_REQUESTS_PER_TOKEN'] = 1
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_state.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(10, self.data_collector.state['data_elements'])
        self.assertEqual(10, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        for token in self.data_collector.config['TOKENS']:
            t = self.data_collector.state['tokens'][token]
            self.assertFalse(t['usable'])
            self.assertEqual(1, t['daily_requests'])

    def test_missing_data_check_no_updated_data_for_all_locations(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.distinct.return_value = [{'location_id': 1}, {'location_id': 2}]
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 2
        mock_collection.find.return_value = ([{'location_id': 1}, {'location_id': 1}, {'location_id': 1},
                                                           {'location_id': 2}], None)
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_check'] = True
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertListEqual([1, 2], self.data_collector.state['missing_data_ids'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    def test_missing_data_check_no_missing_data(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.distinct.return_value = [{'location_id': 1}, {'location_id': 2}]
        mock_collection.find.return_value = ([], None)
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 2
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_check'] = True
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    def test_data_collection_with_no_locations_in_database(self):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 0
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_check'] = True
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_correct_data_collection(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': len(self.data_collector.config['TOKENS']) * self.data_collector.config[
                'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._sum_days(self.data_collector._query_date(),
                                                      -(len(self.data_collector.config['TOKENS'])) *
                                                      self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']),
                        self.data_collector.state['current_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(
            len(self.data_collector.config['TOKENS']) * self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'],
            self.data_collector.state['data_elements'])
        self.assertEqual(
            len(self.data_collector.config['TOKENS']) * self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'],
            self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_correct_data_collection_max_daily_reached(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_DAILY_REQUESTS_PER_TOKEN'] = self.data_collector.config[
                                                                         'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] - 5
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': len(self.data_collector.config['TOKENS']) * self.data_collector.config[
                'MAX_DAILY_REQUESTS_PER_TOKEN'], 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._sum_days(self.data_collector._query_date(),
                                                      -(len(self.data_collector.config['TOKENS'])) *
                                                      self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN']),
                        self.data_collector.state['current_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(
                len(self.data_collector.config['TOKENS']) * self.data_collector.config['MAX_DAILY_REQUESTS_PER_TOKEN'],
                self.data_collector.state['data_elements'])
        self.assertEqual(
                len(self.data_collector.config['TOKENS']) * self.data_collector.config['MAX_DAILY_REQUESTS_PER_TOKEN'],
                self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        for token in self.data_collector.config['TOKENS']:
            t = self.data_collector.state['tokens'][token]
            self.assertFalse(t['usable'])
            self.assertEqual(self.data_collector.config['MAX_DAILY_REQUESTS_PER_TOKEN'], t['daily_requests'])

    @mock.patch('requests.get')
    def test_correct_data_collection_max_daily_reached_from_the_beginning(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector.config['MAX_DAILY_REQUESTS_PER_TOKEN'] = 0
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertFalse(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._sum_days(self.data_collector._query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['current_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        for token in self.data_collector.config['TOKENS']:
            t = self.data_collector.state['tokens'][token]
            self.assertFalse(t['usable'])
            self.assertEqual(0, t['daily_requests'])

    @mock.patch('requests.get')
    def test_update_frequency_is_reset_when_tokens_are_usable_again(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.config['STATE_STRUCT'] = {'update_frequency': {'value': 1, 'units': 'day'},
                                                      'last_request': None, 'data_elements': 0, 'inserted_elements': 0,
                                                      'restart_required': False, 'last_error': None, 'error': None,
                                                      'errors': {}, 'backoff_time': {'value': 1, 'units': 's'},
                                                      'missing_data_check': False, 'current_date': '20180116',
                                                      'missing_data_ids': [1], 'consecutive_unmeasured_days': 0,
                                                      'tokens': {
                                                          '5f06ae04f7342abf': {'daily_requests': 0, 'usable': False},
                                                          'e63c2d687265be99': {'daily_requests': 0, 'usable': False},
                                                          '4ea749ef53da4c65': {'daily_requests': 0, 'usable': False},
                                                          '3d93ef701440b478': {'daily_requests': 0, 'usable': False},
                                                          'bb866b8bda7036f4': {'daily_requests': 0, 'usable': False},
                                                          '8649251baef91434': {'daily_requests': 0, 'usable': False},
                                                          '0e85d055e5337977': {'daily_requests': 0, 'usable': False},
                                                          '330521663b1024c9': {'daily_requests': 0, 'usable': False},
                                                          '9309f4166988f1e3': {'daily_requests': 0, 'usable': False},
                                                          '5e1dd9d990fef0f8': {'daily_requests': 0, 'usable': False}}}

        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': len(self.data_collector.config['TOKENS']) * self.data_collector.config[
                'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_unparseable_data_but_not_all(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 1
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': (len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
                'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        unparseable = dumps({'unparseable': True})
        data = DATA.decode('utf-8', errors='replace')
        response.content.decode = Mock(
                side_effect=[data, data, data, data, data, data, data, unparseable, unparseable, unparseable])
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._sum_days(self.data_collector._query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['current_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual((len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['data_elements'])
        self.assertEqual((len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_unmeasured_days_gets_reseted(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 1
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': (len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
                'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        unparseable = dumps({'unparseable': True})
        data = DATA.decode('utf-8', errors='replace')
        response.content.decode = Mock(
                side_effect=[data, data, data, data, data, data, unparseable, unparseable, unparseable, data])
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._sum_days(self.data_collector._query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['current_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual((len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['data_elements'])
        self.assertEqual((len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        self.assertEqual(0, self.data_collector.state['consecutive_unmeasured_days'])

    @mock.patch('requests.get')
    def test_max_unmeasured_days_reached_multiple_missing_locations(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'unparseable': True}).encode()
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1, 2]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._sum_days(self.data_collector._query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['current_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        self.assertListEqual([2], self.data_collector.state['missing_data_ids'])

    @mock.patch('requests.get')
    def test_max_unmeasured_days_reached_one_location(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'unparseable': True}).encode()
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
        self.assertTrue(self.data_collector.state['missing_data_check'])

    def test_data_collection_with_no_locations_will_schedule_check(self):
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.run()
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertTrue(self.data_collector.state['missing_data_check'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    def test_data_collection_parseable_data_missing_fields(self, mock_requests):
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = MISSING_DATA
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1, 2]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])

    @mock.patch('requests.get')
    def test_data_collection_with_not_all_items_saved(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 2
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'location_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 98, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1, 2]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(100, self.data_collector.state['data_elements'])
        self.assertEqual(98, self.data_collector.state['inserted_elements'])

    @mock.patch('requests.get')
    def test_data_collection_with_no_items_saved(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 2
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'location_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1, 2]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(100, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])

    @mock.patch('requests.get')
    def test_data_collection_with_existing_items_in_db_but_location_unchanged(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 2
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'location_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 95, 'nMatched': 5, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1, 2]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(100, self.data_collector.state['data_elements'])
        self.assertEqual(100, self.data_collector.state['inserted_elements'])
        self.assertListEqual([2], self.data_collector.state['missing_data_ids'])

    @mock.patch('requests.get')
    def test_data_collection_with_existing_items_in_db_location_changed(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 2
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}
        mock_collection.find.return_value = ([{'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'location_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 5, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        unparseable = dumps({'unparseable': True})
        data = DATA.decode('utf-8', errors='replace')
        response.content.decode = Mock(
                side_effect=[data, data, data, data, data, data, unparseable, unparseable, unparseable, data])
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 1
        self.data_collector.config['MAX_DAY_COUNT'] = 3
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1, 2]
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(6, self.data_collector.state['data_elements'])
        self.assertEqual(6, self.data_collector.state['inserted_elements'])
        self.assertTrue(self.data_collector.location_changed)
        self.assertListEqual([2], self.data_collector.state['missing_data_ids'])

    @mock.patch('requests.get')
    def test_data_collection_with_existing_items_in_db_last_location(self, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection = Mock()
        mock_collection.close.return_value = None
        mock_collection.count.return_value = 1
        mock_collection.find_one.return_value = {'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}
        mock_collection.find.return_value = (
            [{'location_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}], None)
        mock_collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 95, 'nMatched': 5, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['STATE_STRUCT']['missing_data_ids'] = [1]
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 10
        self.data_collector.collection = mock_collection
        self.data_collector.run()
        self.assertTrue(mock_collection.method_calls)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['current_date'])
        self.assertEqual(100, self.data_collector.state['data_elements'])
        self.assertEqual(100, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['missing_data_ids'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
