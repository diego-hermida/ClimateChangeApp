import climate.validators as validators
from climate.services.service_impl import MessageActionType, MessageFilterType, TemperatureType
from django.test import SimpleTestCase
from django.test.client import RequestFactory


class ValidateCoordinatesTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_coordinates_valid_coordinates(self):
        lat, long = 13.001931, 179.9494194
        request = self.factory.post('/locations', {'latitude': str(lat), 'longitude': str(long)})
        latitude, longitude = validators.validate_coordinates(request)
        self.assertAlmostEqual(lat, latitude, 0.00001)
        self.assertAlmostEqual(long, longitude, 0.00001)

    def test_validate_coordinates_unparseable_latitude(self):
        lat, long = 'foo', 179.9494194
        with self.assertRaises(validators.ValidationError):
            request = self.factory.post('/locations', {'latitude': str(lat), 'longitude': str(long)})
            validators.validate_coordinates(request)

    def test_validate_coordinates_unparseable_longitude(self):
        lat, long = 13.001931, 'foo'
        with self.assertRaises(validators.ValidationError):
            request = self.factory.post('/locations', {'latitude': str(lat), 'longitude': str(long)})
            validators.validate_coordinates(request)

    def test_validate_coordinates_latitude_out_of_bounds(self):
        lat, long = 85.0000001, 179.9494194
        with self.assertRaises(validators.ValidationError):
            request = self.factory.post('/locations', {'latitude': str(lat), 'longitude': str(long)})
            validators.validate_coordinates(request)

    def test_validate_coordinates_longitude_out_of_bounds(self):
        lat, long = 13.001931, 181.0000001
        with self.assertRaises(validators.ValidationError):
            request = self.factory.post('/locations', {'latitude': str(lat), 'longitude': str(long)})
            validators.validate_coordinates(request)


class ValidateKeywordsTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_keywords_search_valid_keywords(self):
        input_keywords = 'foo baz bar'
        request = self.factory.post('/locations/search', {'keywords': input_keywords})
        keywords = validators.validate_keywords_search(request, 'keywords')
        self.assertListEqual(['foo', 'baz', 'bar'], keywords)

    def test_validate_keywords_search_whitespaces(self):
        input_keywords = '   foo     baz        bar   '
        request = self.factory.post('/locations/search', {'keywords': input_keywords})
        keywords = validators.validate_keywords_search(request, 'keywords')
        self.assertListEqual(['foo', 'baz', 'bar'], keywords)

    def test_validate_keywords_search_invalid_keywords_no_keywords(self):
        input_keywords = '                    '
        request = self.factory.post('/locations/search', {'keywords': input_keywords})
        with self.assertRaises(validators.ValidationError):
            validators.validate_keywords_search(request, 'keywords')

    def test_validate_keywords_search_invalid_keywords_out_of_bounds(self):
        input_keywords = 'fo'
        request = self.factory.post('/locations/search', {'keywords': input_keywords})
        with self.assertRaises(validators.KeywordsLengthValidationError):
            validators.validate_keywords_search(request, 'keywords')


class ValidateIntegerTestCase(SimpleTestCase):

    def test_validate_integer_valid(self):
        n = '-3'
        self.assertEqual(-3, validators.validate_integer(n, positive_only=False))

    def test_validate_integer_not_positive(self):
        n = '-3'
        with self.assertRaises(validators.ValidationError):
            validators.validate_integer(n, positive_only=True)

    def test_validate_integer_unparseable(self):
        n = '-3foo'
        with self.assertRaises(validators.ValidationError):
            validators.validate_integer(n)


class ValidateCountryCodeTestCase(SimpleTestCase):

    def test_validate_country_code_valid(self):
        country_code = '1A'
        self.assertEqual('1A', validators.validate_country_code(country_code))

    def test_validate_country_code_valid_only_letters(self):
        country_code = 'SP'
        self.assertEqual('SP', validators.validate_country_code(country_code))

    def test_validate_country_code_out_of_bounds(self):
        country_code = 'ESP'
        with self.assertRaises(validators.ValidationError):
            validators.validate_country_code(country_code)

    def test_validate_country_code_invalid(self):
        country_code = '12'
        with self.assertRaises(validators.ValidationError):
            validators.validate_country_code(country_code)


class ValidateAirPollutionParametersTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_air_pollution_parameters_valid(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 1224128400813, 1524128483000, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        location_id, start_date, end_date, plot_values = validators.validate_air_pollution_parameters(request)
        self.assertEqual(input_location_id, location_id)
        self.assertEqual(input_start_date, start_date)
        self.assertEqual(input_end_date, end_date)
        self.assertTrue(plot_values)

    def test_validate_air_pollution_parameters_valid_no_plot_values(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 1224128400813, 1524128483000, ''
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        location_id, start_date, end_date, plot_values = validators.validate_air_pollution_parameters(request)
        self.assertEqual(input_location_id, location_id)
        self.assertEqual(input_start_date, start_date)
        self.assertEqual(input_end_date, end_date)
        self.assertFalse(plot_values)

    def test_validate_air_pollution_parameters_location_id_out_of_bounds(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = -1, 1224128400813, 1524128483000, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('location_id', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_invalid_location_id(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 'foo', 1224128400813, 1524128483000, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('location_id', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_start_date_out_of_bounds(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, -1, 1524128483000, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('start_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_end_date_out_of_bounds(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 1224128400813, -1, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('end_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_invalid_start_date(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 'foo', 1524128483000, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('start_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_invalid_end_date(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 1224128400813, 'foo', 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('end_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_null_start_date(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, '', 1524128483000, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': input_start_date,
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('start_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_null_end_date(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 1224128400813, '', 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': input_end_date, 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('end_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_null_dates(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, '', '', 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': input_end_date, 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertEqual('end_date', e.exception.invalid_data)

    def test_validate_air_pollution_parameters_end_date_before_start_date(self):
        input_location_id, input_start_date, input_end_date, input_plot_values = 1, 2, 1, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_date': str(input_start_date),
                                     'end_date': str(input_end_date), 'plot_values': input_plot_values})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_air_pollution_parameters(request)
            self.assertListEqual(['start_date', 'end_date'], e.exception.invalid_data)


class ValidateHistoricalWeatherParametersTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_historical_weather_parameters_valid(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 1996, 2000, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        location_id, start_year, end_year, plot_values, phenomenon = validators.validate_historical_weather_parameters(
                request)
        self.assertEqual(input_location_id, location_id)
        self.assertEqual(input_start_year, start_year)
        self.assertEqual(input_end_year, end_year)
        self.assertTrue(plot_values)
        self.assertEqual(TemperatureType.MAX_TEMP, phenomenon)

    def test_validate_historical_weather_parameters_valid_no_plot_values(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 1996, 2000, '', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': input_phenomenon})
        location_id, start_year, end_year, phenomenon, plot_values = validators.validate_historical_weather_parameters(
                request)
        self.assertEqual(input_location_id, location_id)
        self.assertEqual(input_start_year, start_year)
        self.assertEqual(input_end_year, end_year)
        self.assertFalse(plot_values)
        self.assertEqual(TemperatureType.MAX_TEMP, phenomenon)

    def test_validate_historical_weather_parameters_location_id_out_of_bounds(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = -1, 1996, 2000, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual('location_id', e.exception.invalid_data)

    def test_validate_historical_weather_parameters_invalid_location_id(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 'foo', 1996, 2000, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual('location_id', e.exception.invalid_data)

    def test_validate_historical_weather_parameters_start_year_out_of_bounds(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, -1, 2000, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual('start_year', e.exception.invalid_data)

    def test_validate_historical_weather_parameters_end_year_out_of_bounds(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 1996, -1, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual('end_year', e.exception.invalid_data)

    def test_validate_historical_weather_parameters_invalid_start_year(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 'foo', 2000, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual('start_year', e.exception.invalid_data)

    def test_validate_historical_weather_parameters_invalid_end_year(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 1996, 'foo', 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual('start_year', e.exception.invalid_data)

    def test_validate_historical_weather_parameters_null_start_year(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, '', 2000, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': input_start_year,
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        location_id, start_year, end_year, phenomenon, plot_values = validators.validate_historical_weather_parameters(
                request)
        self.assertEqual(input_location_id, location_id)
        self.assertIsNone(start_year)
        self.assertEqual(input_end_year, end_year)
        self.assertTrue(plot_values)
        self.assertEqual(TemperatureType.MAX_TEMP, phenomenon)

    def test_validate_historical_weather_parameters_null_end_year(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 1996, '', 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': input_end_year, 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        location_id, start_year, end_year, phenomenon, plot_values = validators.validate_historical_weather_parameters(
                request)
        self.assertEqual(input_location_id, location_id)
        self.assertEqual(input_start_year, start_year)
        self.assertIsNone(end_year)
        self.assertTrue(plot_values)
        self.assertEqual(TemperatureType.MAX_TEMP, phenomenon)

    def test_validate_historical_weather_parameters_null_years(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, '', '', 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': input_start_year,
                                     'end_year': input_end_year, 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        location_id, start_year, end_year, phenomenon, plot_values = validators.validate_historical_weather_parameters(
                request)
        self.assertEqual(input_location_id, location_id)
        self.assertIsNone(start_year)
        self.assertIsNone(end_year)
        # If start_year and end_year are both None, then plot_values is set to False
        self.assertFalse(plot_values)
        self.assertEqual(TemperatureType.MAX_TEMP, phenomenon)

    def test_validate_historical_weather_parameters_end_year_before_start_year(self):
        input_location_id, input_start_year, input_end_year, input_plot_values, input_phenomenon = 1, 2000, 1996, 'on', 'max_temp'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'max_temp'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual(['start_year', 'end_year'], e.exception.invalid_data)

    def test_validate_historical_weather_parameters_phenomenon_does_not_exist(self):
        input_location_id, input_start_year, input_end_year, input_plot_values = 1, 1996, 1996, 'on'
        request = self.factory.post('/locations/air-pollution-data',
                                    {'location_id': str(input_location_id), 'start_year': str(input_start_year),
                                     'end_year': str(input_end_year), 'plot_values': input_plot_values,
                                     'phenomenon': 'foo'})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_historical_weather_parameters(request)
            self.assertEqual(['phenomenon'], e.exception.invalid_data)


class ValidateCredentialsTestCase(SimpleTestCase):

    def test_validate_credentials_valid(self):
        input_name, input_password = 'valid_name', 'valid_password'
        name, password = validators.validate_credentials(input_name, input_password)
        self.assertEqual(input_name, name)
        self.assertEqual(input_password, password)

    def test_validate_credentials_empty_name(self):
        input_name, input_password = '', 'valid_password'
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_credentials(input_name, input_password)
            self.assertEqual(['user'], e.exception.invalid_data)

    def test_validate_credentials_empty_password(self):
        input_name, input_password = 'valid_name', ''
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_credentials(input_name, input_password)
            self.assertEqual(['password'], e.exception.invalid_data)

    def test_validate_credentials_both_empty(self):
        input_name, input_password = '', ''
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_credentials(input_name, input_password)
            self.assertEqual(['user', 'password'], e.exception.invalid_data)


class ValidateContactFieldsTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_contact_fields_valid(self):
        input_subject, input_email, input_name, input_message = "I've found a bug", 'john.doe@foo.com', 'John Doe', 'Lorem ipsum dolor sit ament...'
        request = self.factory.post('/admin/login', {'subject': input_subject, 'email': input_email, 'name': input_name,
                                                     'message': input_message})
        subject, email, name, message = validators.validate_contact_fields(request)
        self.assertEqual(input_subject, subject)
        self.assertEqual(input_email, email)
        self.assertEqual(input_name, name)
        self.assertEqual(input_message, message)

    def test_validate_contact_empty_subject(self):
        input_subject, input_email, input_name, input_message = '', 'john.doe@foo.com', 'John Doe', 'Lorem ipsum dolor sit ament...'
        request = self.factory.post('/admin/login', {'subject': input_subject, 'email': input_email, 'name': input_name,
                                                     'message': input_message})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_contact_fields(request)
            self.assertEqual(['subject'], e.exception.invalid_data)

    def test_validate_contact_empty_email(self):
        input_subject, input_email, input_name, input_message = "I've found a bug", '', 'John Doe', 'Lorem ipsum dolor sit ament...'
        request = self.factory.post('/admin/login', {'subject': input_subject, 'email': input_email, 'name': input_name,
                                                     'message': input_message})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_contact_fields(request)
            self.assertEqual(['email'], e.exception.invalid_data)

    def test_validate_contact_empty_name(self):
        input_subject, input_email, input_name, input_message = "I've found a bug", 'john.doe@foo.com', '', 'Lorem ipsum dolor sit ament...'
        request = self.factory.post('/admin/login', {'subject': input_subject, 'email': input_email, 'name': input_name,
                                                     'message': input_message})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_contact_fields(request)
            self.assertEqual(['name'], e.exception.invalid_data)

    def test_validate_contact_empty_message(self):
        input_subject, input_email, input_name, input_message = "I've found a bug", 'john.doe@foo.com', 'John Doe', ''
        request = self.factory.post('/admin/login', {'subject': input_subject, 'email': input_email, 'name': input_name,
                                                     'message': input_message})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_contact_fields(request)
            self.assertEqual(['message'], e.exception.invalid_data)

    def test_validate_contact_empty_all(self):
        input_subject, input_email, input_name, input_message = '', '', '', ''
        request = self.factory.post('/admin/login', {'subject': input_subject, 'email': input_email, 'name': input_name,
                                                     'message': input_message})
        with self.assertRaises(validators.ValidationError) as e:
            validators.validate_contact_fields(request)
            self.assertEqual(['subject', 'email', 'name', 'message'], e.exception.invalid_data)


class ValidateMessageParametersTestCase(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_message_parameters_valid(self):
        input_message_filter, input_action, input_page = 'inbox', 'dismiss', '1'
        request = self.factory.get('/climate/admin/messages?filter=%s&action=%s&page=%s' % (
        input_message_filter, input_action, input_page))
        message_filter, action, page = validators.validate_message_parameters(request)
        self.assertEqual(MessageFilterType.INBOX, message_filter)
        self.assertEqual(MessageActionType.DISMISS, action)
        self.assertEqual(1, page)

    def test_validate_message_parameters_default_parameters(self):
        request = self.factory.get('/climate/admin/messages')
        message_filter, action, page = validators.validate_message_parameters(request)
        self.assertEqual(MessageFilterType.INBOX, message_filter)
        self.assertIsNone(action)
        self.assertEqual(1, page)

    def test_validate_message_parameters_unknow_filter(self):
        input_message_filter, input_action, input_page = 'foo', 'dismiss', '1'
        request = self.factory.get('/climate/admin/messages?filter=%s&action=%s&page=%s' % (
        input_message_filter, input_action, input_page))
        message_filter, action, page = validators.validate_message_parameters(request)
        self.assertEqual(MessageFilterType.INBOX, message_filter)
        self.assertEqual(MessageActionType.DISMISS, action)
        self.assertEqual(1, page)
