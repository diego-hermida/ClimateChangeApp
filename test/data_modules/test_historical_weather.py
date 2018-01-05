import datetime
from json import dumps
from unittest import TestCase, main, mock
from unittest.mock import Mock

from pytz import UTC

import data_modules.historical_weather.historical_weather as historical_weather
from utilities.util import serialize_date

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
        historical_weather.instance().remove_files()

    def tearDown(self):
        self.data_collector.remove_files()

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_correct_data_collection_normal_mode_last_date(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 2, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(2, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_correct_data_collection_normal_mode_not_last_date(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 2, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(), -1)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(2, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_normal_mode_unparseable_data_but_not_all(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        unparseable = dumps({'unparseable': True})
        data = DATA.decode('utf-8', errors='replace')
        response.content.decode = Mock(
                side_effect=[data, unparseable])
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['single_location_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_single_mode_check_less_locations_with_data_than_actual_locations(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.collection.distinct.return_value = [{'location_id': 1}]
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2},
                     {'_id': 3, 'name': 'Borough', 'wunderground_loc_id': 3}], 'more': False}
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector.state['single_location_mode'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertListEqual([2, 3], self.data_collector.state['single_location_ids'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_single_mode_check_no_updated_data_for_all_locations(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.collection.distinct.return_value = [{'location_id': 1}, {'location_id': 2}]
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'location_id': 1}, {'location_id': 1}, {'location_id': 1}, {'location_id': 2}], 'more': False}
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector.state['single_location_mode'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertListEqual([1, 2], self.data_collector.state['single_location_ids'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_single_mode_check_no_missing_data(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.collection.distinct.return_value = [{'location_id': 1}, {'location_id': 2}]
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.state['single_location_mode'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_correct_data_collection_single_mode(self, mock_collection, mock_requests):
        self.data_collector = historical_weather.instance()
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.find_one.return_value = {'_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': len(self.data_collector.config['TOKENS']) * self.data_collector.config[
                'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['single_location_mode'] = True
        self.data_collector.config['STATE_STRUCT']['single_location_ids'] = [1]
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['single_location_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(len(self.data_collector.config['TOKENS']) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['data_elements'])
        self.assertEqual(len(self.data_collector.config['TOKENS']) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_single_mode_unparseable_data_but_not_all(self, mock_collection, mock_requests):
        self.data_collector = historical_weather.instance()
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 1
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.find_one.return_value = {'_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
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
        self.data_collector.config['STATE_STRUCT']['single_location_mode'] = True
        self.data_collector.config['STATE_STRUCT']['single_location_ids'] = [1]
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['single_location_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual((len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['data_elements'])
        self.assertEqual((len(self.data_collector.config['TOKENS']) - 3) * self.data_collector.config[
            'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'], self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_max_unmeasured_days_reached_multiple_single_mode_locations(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.find_one.return_value = {'_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'unparseable': True}).encode()
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['MAX_DAY_COUNT'] = len(self.data_collector.config['TOKENS'])
        self.data_collector.config['STATE_STRUCT']['single_location_mode'] = True
        self.data_collector.config['STATE_STRUCT']['single_location_ids'] = [1, 2]
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector.state['single_location_mode'])
        self.assertTrue(self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['single_location_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_max_unmeasured_days_reached_one_single_mode_location(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.find_one.return_value = {'_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'unparseable': True}).encode()
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['MAX_DAY_COUNT'] = len(self.data_collector.config['TOKENS'])
        self.data_collector.config['STATE_STRUCT']['single_location_mode'] = True
        self.data_collector.config['STATE_STRUCT']['single_location_ids'] = [1]
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.state['single_location_mode'])
        self.assertTrue(self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['single_location_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_max_unmeasured_days_reached_more_days_than_requests_allowed(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.find_one.return_value = {'_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = dumps({'unparseable': True}).encode()
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['MAX_DAY_COUNT'] = len(self.data_collector.config['TOKENS']) * \
                                                      self.data_collector.config[
                                                          'MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] + 1
        self.data_collector.config['STATE_STRUCT']['single_location_mode'] = True
        self.data_collector.config['STATE_STRUCT']['single_location_ids'] = [1, 2]
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector.state['single_location_mode'])
        self.assertEqual(
            len(self.data_collector.config['TOKENS']) * self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'],
            self.data_collector.state['consecutive_unmeasured_days'])
        self.assertTrue(self.data_collector._HistoricalWeatherDataCollector__sum_days(
                self.data_collector._HistoricalWeatherDataCollector__query_date(),
                -(len(self.data_collector.config['TOKENS'])) * self.data_collector.config[
                    'MAX_REQUESTS_PER_MINUTE_AND_TOKEN']), self.data_collector.state['single_location_date'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_correct_data_collection_with_more_items_than_allowed_requests(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1}], 'more': True}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.config['TOKENS'] = ['ABCDEFG']
        self.data_collector.config['MAX_REQUESTS_PER_MINUTE_AND_TOKEN'] = 1
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNotNone(self.data_collector.state['last_id'])
        self.assertEqual(1, self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_with_no_locations_normal_mode(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = {'data': [], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_with_no_locations_check_scheduled(self, mock_collection):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.collection.distinct.return_value = []
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 0
        mock_collection.return_value.find.return_value = {'data': [], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_normal_mode_parseable_data_missing_fields(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        unparseable = dumps({'unparseable': True})
        data = DATA.decode('utf-8', errors='replace')
        response.content.decode = Mock(side_effect=[data, unparseable])
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_single_location_mode_parseable_data_missing_fields(self, mock_collection, mock_requests):
        self.data_collector = historical_weather.instance()
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.find_one.return_value = {'_id': 1, 'name': 'Belleville',
                                                                         'wunderground_loc_id': 1}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {
            'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = MISSING_DATA
        # Actual execution
        self.data_collector.config['STATE_STRUCT']['single_location_mode'] = True
        self.data_collector.config['STATE_STRUCT']['single_location_ids'] = [1, 2]
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector.state['single_location_mode'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_with_not_all_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_modules.historical_weather.historical_weather.MongoDBCollection')
    def test_data_collection_with_no_items_saved(self, mock_collection, mock_requests):
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.count.return_value = 2
        mock_collection.return_value.find.return_value = {
            'data': [{'_id': 1, 'name': 'Belleville', 'wunderground_loc_id': 1},
                     {'_id': 2, 'name': 'Brampton', 'wunderground_loc_id': 2}], 'more': False}
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        response.content = DATA
        # Actual execution
        self.data_collector = historical_weather.instance()
        self.data_collector.config['STATE_STRUCT']['single_location_last_check'] = serialize_date(
                datetime.datetime.now(tz=UTC))
        self.data_collector.config['STATE_STRUCT'][
            'date'] = self.data_collector._HistoricalWeatherDataCollector__query_date()
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(2, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertIsNone(self.data_collector.state['last_id'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
