from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.historical_weather.historical_weather as historical_weather

DATA = {"_id": "5a92b4c9dd571bdf0ff91f45", "date_utc": 1518220800000, "location_id": 1, "_execution_id": 3, "history": {
    "date": {"pretty": "February 10, 2018", "year": "2018", "mon": "02", "mday": "10", "hour": "00", "min": "00",
        "tzname": "Africa/Cairo"},
    "utcdate": {"pretty": "February 9, 2018", "year": "2018", "mon": "02", "mday": "09", "hour": "22", "min": "00",
        "tzname": "UTC"}, "observations": [{
        "date": {"pretty": "2:00 AM EET on February 10, 2018", "year": "2018", "mon": "02", "mday": "10", "hour": "02",
            "min": "00", "tzname": "Africa/Cairo"},
        "utcdate": {"pretty": "12:00 AM GMT on February 10, 2018", "year": "2018", "mon": "02", "mday": "10",
            "hour": "00", "min": "00", "tzname": "UTC"}, "tempm": "16", "tempi": "62", "dewptm": "16", "dewpti": "61",
        "hum": "94", "wspdm": "16.7", "wspdi": "10.4", "wgustm": "", "wgusti": "", "wdird": "30", "wdire": "NNE",
        "vism": "3.0", "visi": "2", "pressurem": "1012", "pressurei": "29.88", "windchillm": "-999",
        "windchilli": "-999", "heatindexm": "-9999", "heatindexi": "-9999", "precipm": "", "precipi": "",
        "conds": "Mist", "icon": "hazy", "fog": "0", "rain": "0", "snow": "0", "hail": "0", "thunder": "0",
        "tornado": "0", "metar": "AAXX 10004 62366 34930 00309 10165 20159 40117 57012 71000"}], "dailysummary": [{
        "date": {"pretty": "12:00 AM EET on February 10, 2018", "year": "2018", "mon": "02", "mday": "10", "hour": "00",
            "min": "00", "tzname": "Africa/Cairo"}, "fog": "0", "rain": "0", "snow": "0", "snowfallm": "",
        "snowfalli": "", "monthtodatesnowfallm": "", "monthtodatesnowfalli": "", "since1julsnowfallm": "",
        "since1julsnowfalli": "", "snowdepthm": "", "snowdepthi": "", "hail": "0", "thunder": "0", "tornado": "0",
        "meantempm": "22", "meantempi": "72", "meandewptm": "10", "meandewpti": "49", "meanpressurem": "1007.84",
        "meanpressurei": "29.77", "meanwindspdm": "12", "meanwindspdi": "7", "meanwdire": "SSE", "meanwdird": "163",
        "meanvism": "3.5", "meanvisi": "2.2", "humidity": "50", "maxtempm": "32", "maxtempi": "89", "mintempm": "12",
        "mintempi": "55", "maxhumidity": "94", "minhumidity": "8", "maxdewptm": "16", "maxdewpti": "61",
        "mindewptm": "1", "mindewpti": "34", "maxpressurem": "1012", "maxpressurei": "29.89", "minpressurem": "1006",
        "minpressurei": "29.70", "maxwspdm": "26", "maxwspdi": "16", "minwspdm": "0", "minwspdi": "0",
        "maxvism": "10.0", "maxvisi": "6.0", "minvism": "1.5", "minvisi": "0.9", "gdegreedays": "22",
        "heatingdegreedays": "0", "coolingdegreedays": "7", "precipm": "0.0", "precipi": "0.00",
        "precipsource": "3Or6HourObs", "heatingdegreedaysnormal": "", "monthtodateheatingdegreedays": "",
        "monthtodateheatingdegreedaysnormal": "", "since1sepheatingdegreedays": "",
        "since1sepheatingdegreedaysnormal": "", "since1julheatingdegreedays": "",
        "since1julheatingdegreedaysnormal": "", "coolingdegreedaysnormal": "", "monthtodatecoolingdegreedays": "",
        "monthtodatecoolingdegreedaysnormal": "", "since1sepcoolingdegreedays": "",
        "since1sepcoolingdegreedaysnormal": "", "since1jancoolingdegreedays": "",
        "since1jancoolingdegreedaysnormal": ""}]},
    "response": {"version": "0.1", "termsofService": "http://www.wunderground.com/weather/api/d/terms.html",
        "features": {"history": 1}}}

DATA_UNEXPECTED = deepcopy(DATA)
DATA_UNEXPECTED['location_id'] = None


class TestHistoricalWeather(TestCase):

    @classmethod
    def setUpClass(cls):
        historical_weather.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = historical_weather.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        self.data_converter.remove_files()

    @mock.patch('data_conversion_subsystem.data_converters.historical_weather.historical_weather.Location.objects.'
                'count', Mock(return_value=91))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.historical_weather.historical_weather.Location.objects.'
                'count', Mock(return_value=0))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(all([x for x in self.data_converter.data if
                             isinstance(x, historical_weather.HistoricalWeatherObservation)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.historical_weather.historical_weather.'
                'HistoricalWeatherObservation.objects.bulk_create', Mock(return_value=[1, 2, 3]))
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
