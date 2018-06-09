from utilities.postgres_util import import_psycopg2

import_psycopg2()

from unittest import mock
from django.test import TestCase, SimpleTestCase
from climate.services.service_impl import LikeService, LocationService, CountryService, TemperatureType, \
    GlobalClimateChangeService, AdminService, MessageService, MessageActionType, MessageFilterType
from climate.webmodels.models import ContactMessage, LikeCount
from data_conversion_subsystem.data.models import IncomeLevel, Region, Country, Location, AirPollutionMeasure, \
    HistoricalWeatherObservation, CountryIndicator, IndicatorDetails, CurrentConditionsObservation, \
    WeatherForecastObservation, WeatherType, SeaLevelRiseMeasure, RpcDatabaseEmission, OceanMassMeasure


class TemperatureTypeTestCase(SimpleTestCase):

    def test_get_representation(self):
        self.assertEqual('max_temp', TemperatureType.get_representation(TemperatureType.MAX_TEMP))
        self.assertEqual('mean_temp', TemperatureType.get_representation(TemperatureType.MEAN_TEMP))
        self.assertEqual('min_temp', TemperatureType.get_representation(TemperatureType.MIN_TEMP))

    def test_from_representation(self):
        self.assertEqual(TemperatureType.MAX_TEMP, TemperatureType.from_representation('max_temp'))
        self.assertEqual(TemperatureType.MEAN_TEMP, TemperatureType.from_representation('mean_temp'))
        self.assertEqual(TemperatureType.MIN_TEMP, TemperatureType.from_representation('min_temp'))


class MessageFilterTypeTestCase(SimpleTestCase):

    def test_get_representation(self):
        self.assertEqual('dismissed', MessageFilterType.get_representation(MessageFilterType.DISMISSED))
        self.assertEqual('replied', MessageFilterType.get_representation(MessageFilterType.REPLIED))
        self.assertEqual('inbox', MessageFilterType.get_representation(MessageFilterType.INBOX))

    def test_from_representation(self):
        self.assertEqual(MessageFilterType.DISMISSED, MessageFilterType.from_representation('dismissed'))
        self.assertEqual(MessageFilterType.REPLIED, MessageFilterType.from_representation('replied'))
        self.assertEqual(MessageFilterType.INBOX, MessageFilterType.from_representation('inbox'))


class MessageActionTypeTestCase(SimpleTestCase):

    def test_get_representation(self):
        self.assertEqual('dismiss', MessageActionType.get_representation(MessageActionType.DISMISS))
        self.assertEqual('reply', MessageActionType.get_representation(MessageActionType.REPLY))
        self.assertEqual('restore', MessageActionType.get_representation(MessageActionType.RESTORE))
        self.assertEqual('delete', MessageActionType.get_representation(MessageActionType.DELETE))

    def test_from_representation(self):
        self.assertEqual(MessageActionType.DISMISS, MessageActionType.from_representation('dismiss'))
        self.assertEqual(MessageActionType.REPLY, MessageActionType.from_representation('reply'))
        self.assertEqual(MessageActionType.RESTORE, MessageActionType.from_representation('restore'))
        self.assertEqual(MessageActionType.DELETE, MessageActionType.from_representation('delete'))

    def test_get_filter_name(self):
        self.assertEqual('dismissed', MessageActionType.get_filter_name(MessageActionType.DISMISS))
        self.assertEqual('replied', MessageActionType.get_filter_name(MessageActionType.REPLY))
        self.assertEqual('inbox', MessageActionType.get_filter_name(MessageActionType.RESTORE))
        self.assertIsNone(MessageActionType.get_filter_name(MessageActionType.DELETE))
        self.assertEqual('inbox', MessageActionType.get_filter_name(MessageActionType.DELETE, 'inbox'))


class LikeServiceTestCase(TestCase):

    def test_get_like_count(self):
        self.assertEqual(0, LikeService.get_like_count())  # First time, an entity should be created.
        self.assertEqual(0, LikeService.get_like_count())  # Then, simple queries

    def test_increase_like_counter(self):
        self.assertTrue(LikeService.increase_like_counter())
        self.assertEqual(1, LikeService.get_like_count())
        self.assertTrue(LikeService.increase_like_counter())
        self.assertEqual(2, LikeService.get_like_count())

    def test_increase_like_counter_no_counter(self):
        LikeCount.objects.all().delete()
        self.assertTrue(LikeService.increase_like_counter())
        self.assertEqual(1, LikeService.get_like_count())

    @mock.patch('climate.services.service_impl.LikeCount.increment_atomic',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_increase_like_counter_with_anomalous_error(self):
        self.assertFalse(LikeService.increase_like_counter())


class LocationServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        from .data_for_testing import REGIONS, INCOME_LEVELS, COUNTRIES, LOCATION_WITH_ALL_DATA, LOCATIONS_WITH_NO_DATA, \
            AIR_POLLUTION_DATA, HISTORICAL_WEATHER_DATA, WEATHER_TYPES, CURRENT_CONDITIONS, WEATHER_FORECAST

        Region.objects.bulk_create(REGIONS)
        IncomeLevel.objects.bulk_create(INCOME_LEVELS)
        Country.objects.bulk_create(COUNTRIES)
        Location.objects.bulk_create((LOCATION_WITH_ALL_DATA,) + LOCATIONS_WITH_NO_DATA)
        AirPollutionMeasure.objects.bulk_create(AIR_POLLUTION_DATA)
        HistoricalWeatherObservation.objects.bulk_create(HISTORICAL_WEATHER_DATA)
        Location.objects.filter(pk=13).update(air_pollution_last_measure_id=56156)
        WeatherType.objects.bulk_create(WEATHER_TYPES)
        CurrentConditionsObservation.objects.bulk_create((CURRENT_CONDITIONS,))
        WeatherForecastObservation.objects.bulk_create(WEATHER_FORECAST)

    def test_get_nearest_location_from_coordinates(self):
        nearest_id = LocationService.get_nearest_location_from_coordinates(latitude=43.0097384, longitude=-7.55675819)
        self.assertTrue(13, nearest_id)  # Madrid
        nearest_id = LocationService.get_nearest_location_from_coordinates(latitude=39.91987, longitude=32.85427)
        self.assertTrue(11, nearest_id)  # Ankara

    def test_get_nearest_location_from_coordinates_no_locations(self):
        Location.objects.all().delete()
        nearest_id = LocationService.get_nearest_location_from_coordinates(latitude=43.0097384, longitude=-7.55675819)
        self.assertIsNone(nearest_id)  # Madrid

    def test_get_all_locations(self):
        locations = LocationService.get_all_locations(order_by=('id',))
        self.assertTrue(all([isinstance(x, Location) for x in locations]))
        self.assertEqual(4, len(locations))
        self.assertListEqual([11, 12, 13, 27], [x.id for x in locations])

    def test_get_all_locations_not_as_objects(self):
        locations = LocationService.get_all_locations(order_by=('id',), as_objects=False)
        self.assertTrue(all([isinstance(x, dict) for x in locations]))
        self.assertEqual(4, len(locations))
        self.assertListEqual([11, 12, 13, 27], [x['id'] for x in locations])

    def test_get_all_locations_as_objects_only_certain_fields(self):
        locations = LocationService.get_all_locations(fields=('id', 'name'), order_by=('id',), as_objects=False)
        for loc in locations:
            with self.assertRaises(KeyError):
                return loc['latitude']

    def test_get_all_locations_no_locations(self):
        Location.objects.all().delete()
        locations = LocationService.get_all_locations()
        self.assertListEqual([], locations)

    def test_get_single_location(self):
        loc = LocationService.get_single_location(13)  # Madrid
        self.assertEqual(13, loc.location.id)
        self.assertEqual('Madrid', loc.location.name)

    def test_get_single_location_from_location_object(self):
        identifier = Location.objects.get(pk=13)  # Madrid
        loc = LocationService.get_single_location(identifier)
        self.assertEqual(13, loc.location.id)
        self.assertEqual('Madrid', loc.location.name)

    def test_get_single_location_non_existent_id(self):
        loc = LocationService.get_single_location(-1)
        self.assertIsNone(loc)

    def test_get_locations_by_keywords(self):
        search_result, more_results = LocationService.get_locations_by_keywords(['A'], max_results=4)
        self.assertEqual(4, len(search_result))
        self.assertFalse(more_results)
        self.assertListEqual(['Ankara', 'Antananarivo', 'Brasília', 'Madrid'], [x.name for x in search_result])

    def test_get_locations_by_keywords_more_results(self):
        search_result, more_results = LocationService.get_locations_by_keywords(['A'], max_results=2)
        self.assertEqual(2, len(search_result))
        self.assertTrue(more_results)
        self.assertListEqual(['Ankara', 'Antananarivo'], [x.name for x in search_result])

    def test_get_locations_by_keywords_no_results(self):
        search_result, more_results = LocationService.get_locations_by_keywords(['foo', 'baz'], max_results=2)
        self.assertListEqual([], search_result)
        self.assertFalse(more_results)

    def test_get_locations_by_keywords_no_locations(self):
        Location.objects.all().delete()
        search_result, more_results = LocationService.get_locations_by_keywords(['A'], max_results=2)
        self.assertListEqual([], search_result)
        self.assertFalse(more_results)

    def test_get_air_pollution_data(self):
        data, dom_data = LocationService.get_air_pollution_data(13, start_epoch=0, end_epoch=10000000000000)
        self.assertTrue(all([isinstance(x, AirPollutionMeasure) for x in data]))
        self.assertTrue(all([isinstance(x, str) for x in dom_data]))
        self.assertEqual(5, len(data))
        self.assertEqual(5, len(dom_data))

    def test_get_air_pollution_data_not_as_objects(self):
        data, dom_data = LocationService.get_air_pollution_data(13, start_epoch=0, end_epoch=10000000000000,
                                                                as_objects=False)
        self.assertTrue(all([isinstance(x, tuple) for x in data]))
        self.assertTrue(all([isinstance(x, str) for x in dom_data]))
        self.assertEqual(5, len(data))
        self.assertEqual(5, len(dom_data))

    def test_get_air_pollution_data_no_data(self):
        AirPollutionMeasure.objects.all().delete()
        data, dom_data = LocationService.get_air_pollution_data(13, start_epoch=0, end_epoch=10000000000000)
        self.assertListEqual([], data)
        self.assertListEqual([], dom_data)

    def test_get_air_pollution_data_no_such_location(self):
        with self.assertRaises(Location.DoesNotExist):
            LocationService.get_air_pollution_data(-1)

    def test_has_air_pollution_measures(self):
        self.assertTrue(LocationService.has_air_pollution_measures(13))  # Madrid

    def test_has_air_pollution_measures_no_measures(self):
        self.assertFalse(LocationService.has_air_pollution_measures(11))  # Ankara

    def test_has_air_pollution_measures_no_such_location(self):
        with self.assertRaises(Location.DoesNotExist):
            LocationService.has_air_pollution_measures(-1)

    def test_get_single_air_pollution_measure(self):
        self.assertIsInstance(LocationService.get_single_air_pollution_measure(56156), AirPollutionMeasure)  # Madrid

    def test_get_single_air_pollution_measure_no_measure(self):
        self.assertIsNone(LocationService.get_single_air_pollution_measure(-1))

    def test_has_historical_weather_measures(self):
        self.assertTrue(LocationService.has_historical_weather_measures(13))  # Madrid

    def test_has_historical_weather_measures_no_measures(self):
        self.assertFalse(LocationService.has_historical_weather_measures(11))  # Ankara

    def test_has_historical_weather_measures_no_such_location(self):
        with self.assertRaises(Location.DoesNotExist):
            LocationService.has_historical_weather_measures(-1)

    def test_has_current_conditions_measure(self):
        self.assertIsInstance(LocationService.get_single_current_conditions_measure(13),
                              CurrentConditionsObservation)  # Madrid

    def test_has_current_conditions_measure_no_measure(self):
        self.assertIsNone(LocationService.get_single_current_conditions_measure(11))  # Ankara

    def test_has_current_conditions_measure_no_such_location(self):
        with self.assertRaises(Location.DoesNotExist):
            LocationService.get_single_current_conditions_measure(-1)

    def test_get_historical_weather_data_all(self):
        for temperature_type in (TemperatureType.MIN_TEMP, TemperatureType.MEAN_TEMP, TemperatureType.MAX_TEMP):
            data, no_year_range = LocationService.get_historical_weather_data(13, temperature_type)
            self.assertTrue(all([isinstance(x, HistoricalWeatherObservation) for x in data]))
            self.assertTrue(no_year_range)
            self.assertEqual(7, len(data))

    def test_get_historical_weather_data_all_not_as_objects(self):
        for temperature_type in (TemperatureType.MIN_TEMP, TemperatureType.MEAN_TEMP, TemperatureType.MAX_TEMP):
            data, no_year_range = LocationService.get_historical_weather_data(13, temperature_type, as_objects=False)
            self.assertTrue(all([isinstance(x, tuple) for x in data]))
            self.assertTrue(all([len(x) == 2 for x in data]))
            self.assertTrue(no_year_range)
            self.assertEqual(7, len(data))

    def test_get_historical_weather_data_bounded_min_year(self):
        for temperature_type in (TemperatureType.MIN_TEMP, TemperatureType.MEAN_TEMP, TemperatureType.MAX_TEMP):
            data, no_year_range = LocationService.get_historical_weather_data(13, temperature_type, start_year=2018)
            self.assertTrue(all([isinstance(x, HistoricalWeatherObservation) for x in data]))
            self.assertFalse(no_year_range)
            self.assertEqual(1, len(data))

    def test_get_historical_weather_data_bounded_max_year(self):
        for temperature_type in (TemperatureType.MIN_TEMP, TemperatureType.MEAN_TEMP, TemperatureType.MAX_TEMP):
            data, no_year_range = LocationService.get_historical_weather_data(13, temperature_type, end_year=2017)
            self.assertTrue(all([isinstance(x, HistoricalWeatherObservation) for x in data]))
            self.assertFalse(no_year_range)
            self.assertEqual(6, len(data))

    def test_get_historical_weather_data_bounded_min_year_max_year(self):
        for temperature_type in (TemperatureType.MIN_TEMP, TemperatureType.MEAN_TEMP, TemperatureType.MAX_TEMP):
            data, no_year_range = LocationService.get_historical_weather_data(13, temperature_type, start_year=2016,
                                                                              end_year=2017)
            self.assertTrue(all([isinstance(x, HistoricalWeatherObservation) for x in data]))
            self.assertFalse(no_year_range)
            self.assertEqual(4, len(data))

    def test_get_historical_weather_data_no_data(self):
        HistoricalWeatherObservation.objects.all().delete()
        for temperature_type in (TemperatureType.MIN_TEMP, TemperatureType.MEAN_TEMP, TemperatureType.MAX_TEMP):
            data, no_year_range = LocationService.get_historical_weather_data(13, temperature_type)
            self.assertListEqual([], data)
            self.assertTrue(no_year_range)

    def test_get_historical_weather_data_no_such_location(self):
        with self.assertRaises(Location.DoesNotExist):
            LocationService.get_historical_weather_data(-1)

    def test_historical_weather_stats(self):
        stats, no_year_range = LocationService.get_historical_weather_stats(13)
        self.assertTrue(no_year_range)
        self.assertEqual(4, len(stats))
        self.assertTrue(all([isinstance(x, tuple) for x in stats]))
        self.assertEqual([2015, 2016, 2017, 2018], [x[0] for x in stats])

    def test_historical_weather_stats_bounded_min_year(self):
        stats, no_year_range = LocationService.get_historical_weather_stats(13, start_year=2016)
        self.assertFalse(no_year_range)
        self.assertEqual(3, len(stats))
        self.assertTrue(all([isinstance(x, tuple) for x in stats]))
        self.assertEqual([2016, 2017, 2018], [x[0] for x in stats])

    def test_historical_weather_stats_bounded_max_year(self):
        stats, no_year_range = LocationService.get_historical_weather_stats(13, end_year=2016)
        self.assertFalse(no_year_range)
        self.assertEqual(2, len(stats))
        self.assertTrue(all([isinstance(x, tuple) for x in stats]))
        self.assertEqual([2015, 2016], [x[0] for x in stats])

    def test_historical_weather_stats_bounded_min_year_max_year(self):
        stats, no_year_range = LocationService.get_historical_weather_stats(13, start_year=2015, end_year=2015)
        self.assertFalse(no_year_range)
        self.assertEqual(1, len(stats))
        self.assertTrue(all([isinstance(x, tuple) for x in stats]))
        self.assertEqual([2015], [x[0] for x in stats])

    def test_get_historical_weather_stats_no_data(self):
        HistoricalWeatherObservation.objects.all().delete()
        stats, no_year_range = LocationService.get_historical_weather_stats(13)
        self.assertListEqual([], stats)
        self.assertTrue(no_year_range)

    def test_get_historical_weather_stats_no_such_location(self):
        with self.assertRaises(Location.DoesNotExist):
            LocationService.get_historical_weather_stats(-1)


class CountryServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        from .data_for_testing import REGIONS, INCOME_LEVELS, COUNTRIES, INDICATOR_DETAILS, COUNTRY_INDICATORS, LOCATION_WITH_ALL_DATA, LOCATIONS_WITH_NO_DATA

        Region.objects.bulk_create(REGIONS)
        IncomeLevel.objects.bulk_create(INCOME_LEVELS)
        Country.objects.bulk_create(COUNTRIES)
        Location.objects.bulk_create((LOCATION_WITH_ALL_DATA,) + LOCATIONS_WITH_NO_DATA)
        IndicatorDetails.objects.bulk_create(INDICATOR_DETAILS)
        CountryIndicator.objects.bulk_create(COUNTRY_INDICATORS)

    def test_get_countries_by_keywords(self):
        search_result, more_results = CountryService.get_countries_by_keywords(['A'], max_results=4)
        self.assertEqual(4, len(search_result))
        self.assertFalse(more_results)
        self.assertListEqual(['Brazil', 'France', 'Madagascar', 'Spain'], [x.name for x in search_result])

    def test_get_countries_by_keywords_more_results(self):
        search_result, more_results = CountryService.get_countries_by_keywords(['A'], max_results=2)
        self.assertEqual(2, len(search_result))
        self.assertTrue(more_results)
        self.assertListEqual(['Brazil', 'France'], [x.name for x in search_result])

    def test_get_countries_by_keywords_no_results(self):
        search_result, more_results = CountryService.get_countries_by_keywords(['foo', 'baz'], max_results=2)
        self.assertListEqual([], search_result)
        self.assertFalse(more_results)

    def test_get_countries_by_keywords_no_countries(self):
        Country.objects.all().delete()
        search_result, more_results = CountryService.get_countries_by_keywords(['A'], max_results=2)
        self.assertListEqual([], search_result)
        self.assertFalse(more_results)

    def test_get_single_country(self):
        country = CountryService.get_single_country('ES')  # Spain
        self.assertEqual('ES', country.country.iso2_code)
        self.assertEqual('Spain', country.country.name)

    def test_get_single_country_from_country_object(self):
        identifier = Country.objects.get(pk='ES')  # Spain
        country = CountryService.get_single_country(identifier)
        self.assertEqual('ES', country.country.iso2_code)
        self.assertEqual('Spain', country.country.name)

    def test_get_single_country_non_existent_id(self):
        country = CountryService.get_single_country('XX')
        self.assertIsNone(country)

    def test_get_data_from_indicators(self):
        indicator_codes = ('AG.LND.EL5M.UR.ZS', 'AG.LND.FRST.ZS', 'ER.PTD.TOTL.ZS', 'SH.H2O.SAFE.ZS')
        indicators = CountryService.get_data_from_indicators('ES', indicators=indicator_codes, null_values=True)
        retrieved_codes = tuple(set([x.indicator_id for x in indicators]))
        self.assertEqual(indicator_codes, retrieved_codes)
        self.assertEqual(112, len(indicators))

    def test_get_data_from_indicators_no_null_values(self):
        indicator_codes = ('AG.LND.EL5M.UR.ZS', 'AG.LND.FRST.ZS', 'ER.PTD.TOTL.ZS', 'SH.H2O.SAFE.ZS')
        indicators = CountryService.get_data_from_indicators('ES', indicators=indicator_codes, null_values=False)
        retrieved_codes = tuple(set([x.indicator_id for x in indicators]))
        self.assertTrue(all([x.value is not None for x in indicators]))
        self.assertEqual(indicator_codes, retrieved_codes)
        self.assertEqual(58, len(indicators))

    def test_count_monitored_locations(self):
        count = CountryService.count_monitored_locations('ES')
        self.assertEqual(1, count)

    def test_count_monitored_locations_no_locations(self):
        Country.objects.create(iso2_code='XX', iso3_code='XXX', name='Foo')
        count = CountryService.count_monitored_locations('XX')
        self.assertEqual(0, count)

    def test_country_monitored_locations_no_such_country(self):
        with self.assertRaises(Country.DoesNotExist):
            CountryService.count_monitored_locations('XX')

    def test_fetch_monitored_location_id(self):
        location_id = CountryService.fetch_monitored_location_id('ES')
        self.assertEqual(13, location_id)

    def test_fetch_monitored_location_id_no_locations(self):
        Country.objects.create(iso2_code='XX', iso3_code='XXX', name='Foo')
        location_id = CountryService.fetch_monitored_location_id('XX')
        self.assertIsNone(location_id)

    def test_fetch_monitored_location_id_no_such_country(self):
        with self.assertRaises(Country.DoesNotExist):
            CountryService.fetch_monitored_location_id('XX')

    def test_get_population_data(self):
        population, last_year, previous_population, previous_year, percentage_diff = CountryService.get_population_data(
            'ES')
        self.assertEqual(45000000, population)
        self.assertEqual(2015, last_year)
        self.assertEqual(44000000, previous_population)
        self.assertEqual(2013, previous_year)
        self.assertAlmostEqual(2.27272727, percentage_diff)

    def test_get_population_data_no_data(self):
        Country.objects.create(iso2_code='XX', iso3_code='XXX', name='Foo')
        population, last_year, previous_population, previous_year, percentage_diff = CountryService.get_population_data(
                'XX')
        self.assertIsNone(population)
        self.assertIsNone(last_year)
        self.assertIsNone(previous_population)
        self.assertIsNone(previous_year)
        self.assertIsNone(percentage_diff)

    def test_get_population_data_only_data_for_last_year(self):
        population, last_year, previous_population, previous_year, percentage_diff = CountryService.get_population_data(
                'FR')
        self.assertIsNone(population)
        self.assertIsNone(last_year)
        self.assertIsNone(previous_population)
        self.assertIsNone(previous_year)
        self.assertIsNone(percentage_diff)

    def test_get_population_data_no_such_country(self):
        with self.assertRaises(Country.DoesNotExist):
            CountryService.get_population_data('XX')


class GlobalClimateChangeServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        from .data_for_testing import SEA_LEVEL_RISE, OCEAN_MASS, RPC_DATA

        SeaLevelRiseMeasure.objects.bulk_create(SEA_LEVEL_RISE)
        OceanMassMeasure.objects.bulk_create(OCEAN_MASS)
        RpcDatabaseEmission.objects.bulk_create(RPC_DATA)

    def test_get_sea_level_rise_data(self):
        data = GlobalClimateChangeService.get_sea_level_rise_data()
        self.assertTrue(data)

    def test_get_sea_level_rise_data_no_data(self):
        SeaLevelRiseMeasure.objects.all().delete()
        data = GlobalClimateChangeService.get_sea_level_rise_data()
        self.assertListEqual([], data)

    def test_get_ice_extent_data(self):
        data = GlobalClimateChangeService.get_ice_extent_data()
        self.assertTrue(data)

    def test_get_ice_extent_data_no_data(self):
        OceanMassMeasure.objects.all().delete()
        data = GlobalClimateChangeService.get_ice_extent_data()
        self.assertListEqual([], data)

    def test_get_future_emissions_data(self):
        data = GlobalClimateChangeService.get_future_emissions_data()
        self.assertTrue(data)

    def test_get_future_emissions_data_no_data(self):
        RpcDatabaseEmission.objects.all().delete()
        data = GlobalClimateChangeService.get_future_emissions_data()
        self.assertListEqual([], data)


class AdminServiceTestCase(SimpleTestCase):

    @mock.patch('climate.services.service_impl.login')
    @mock.patch('climate.services.service_impl.authenticate')
    def test_login(self, mock_authenticate, mock_login):
        mock_authenticate.return_value.is_active = True
        self.assertTrue(AdminService.login('valid_user', 'valid_password', None))
        self.assertTrue(mock_authenticate.called)
        self.assertTrue(mock_login.called)

    @mock.patch('climate.services.service_impl.authenticate')
    def test_login_invalid_user(self, mock_authenticate):
        mock_authenticate.return_value = None
        self.assertFalse(AdminService.login('foo', 'bar', None))
        self.assertTrue(mock_authenticate.called)

    @mock.patch('climate.services.service_impl.logout')
    def test_logout(self, mock_logout):
        mock_logout.return_value = None
        self.assertTrue(AdminService.logout(None))
        self.assertTrue(mock_logout.called)

    @mock.patch('climate.services.service_impl.logout',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_logout_unexpected_error(self):
        self.assertFalse(AdminService.logout(None))


class MessageServiceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        from .data_for_testing import MESSAGE_DISMISSED, MESSAGE_INBOX, MESSAGE_REPLIED

        ContactMessage.objects.bulk_create((MESSAGE_INBOX, MESSAGE_REPLIED, MESSAGE_DISMISSED))

    def test_create_message(self):
        self.assertIsInstance(
                MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                              message='Lorem ipsum dolor sit ament...'), ContactMessage)

    @mock.patch('climate.services.service_impl.ContactMessage.objects.create',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_create_message_with_unexpected_error(self):
        self.assertIsNone(
                MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                              message='Lorem ipsum dolor sit ament...'))

    def test_count_unread_messages(self):
        self.assertEqual(1, MessageService.count_unread_messages())
        MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                      message='Lorem ipsum dolor sit ament...')
        self.assertEqual(2, MessageService.count_unread_messages())

    def test_count_unread_messages_no_messages(self):
        ContactMessage.objects.all().delete()
        self.assertEqual(0, MessageService.count_unread_messages())

    @mock.patch('climate.services.service_impl.ContactMessage.objects.filter',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_count_unread_messages_unexpected_error(self):
        self.assertIsNone(MessageService.count_unread_messages())

    def test_update_or_delete_reply(self):
        message = MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                                message='Lorem ipsum dolor sit ament...')
        self.assertTrue(MessageService.update_or_delete(message.id, MessageActionType.REPLY))
        self.assertTrue(ContactMessage.objects.get(pk=message.id).replied)

    def test_update_or_delete_reply_no_such_message(self):
        self.assertIsNone(MessageService.update_or_delete(-1, MessageActionType.REPLY))

    def test_update_or_delete_dismiss(self):
        message = MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                                message='Lorem ipsum dolor sit ament...')
        self.assertTrue(MessageService.update_or_delete(message.id, MessageActionType.DISMISS))
        self.assertTrue(ContactMessage.objects.get(pk=message.id).dismissed)

    def test_update_or_delete_dismiss_no_such_message(self):
        self.assertIsNone(MessageService.update_or_delete(-1, MessageActionType.DISMISS))

    def test_update_or_delete_restore_from_dismissed(self):
        message = ContactMessage.objects.filter(dismissed=True)[0]
        self.assertTrue(MessageService.update_or_delete(message.id, MessageActionType.RESTORE))
        self.assertFalse(ContactMessage.objects.get(pk=message.id).dismissed)

    def test_update_or_delete_restore_from_replied(self):
        message = ContactMessage.objects.filter(replied=True)[0]
        self.assertTrue(MessageService.update_or_delete(message.id, MessageActionType.RESTORE))
        self.assertFalse(ContactMessage.objects.get(pk=message.id).replied)

    def test_update_or_delete_restore_no_such_message(self):
        self.assertIsNone(MessageService.update_or_delete(-1, MessageActionType.RESTORE))

    def test_update_or_delete_delete(self):
        message = MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                                message='Lorem ipsum dolor sit ament...')
        self.assertTrue(MessageService.update_or_delete(message.id, MessageActionType.DELETE))
        with self.assertRaises(ContactMessage.DoesNotExist):
            ContactMessage.objects.get(pk=message.id)

    def test_update_or_delete_delete_no_such_message(self):
        self.assertIsNone(MessageService.update_or_delete(-1, MessageActionType.DELETE))

    @mock.patch('climate.services.service_impl.ContactMessage.objects.filter',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_update_or_delete_reply_unexpected_error(self):
        self.assertFalse(MessageService.update_or_delete(-1, MessageActionType.REPLY))

    @mock.patch('climate.services.service_impl.ContactMessage.objects.filter',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_update_or_delete_dismiss_unexpected_error(self):
        self.assertFalse(MessageService.update_or_delete(-1, MessageActionType.DISMISS))

    @mock.patch('climate.services.service_impl.ContactMessage.objects.filter',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_update_or_delete_restore_unexpected_error(self):
        self.assertFalse(MessageService.update_or_delete(-1, MessageActionType.RESTORE))

    @mock.patch('climate.services.service_impl.ContactMessage.objects.filter',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_update_or_delete_delete_unexpected_error(self):
        self.assertFalse(MessageService.update_or_delete(-1, MessageActionType.DELETE))

    def test_filter_messages_replied(self):
        from .data_for_testing import MESSAGE_REPLIED
        messages, total_pages = MessageService.filter_messages(MessageFilterType.REPLIED, 1)
        self.assertEqual(1, total_pages)
        self.assertListEqual([MESSAGE_REPLIED], list(messages))

    def test_filter_messages_inbox(self):
        from .data_for_testing import MESSAGE_INBOX
        messages, total_pages = MessageService.filter_messages(MessageFilterType.INBOX, 1)
        self.assertEqual(1, total_pages)
        self.assertListEqual([MESSAGE_INBOX], list(messages))

    @mock.patch('climate.services.service_impl.WEB_CONFIG', {'PAGE_SIZE': 2})
    def test_filter_messages_inbox_multiple_pages(self):
        from .data_for_testing import MESSAGE_INBOX
        message2 = MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                                 message='Lorem ipsum dolor sit ament...')
        message3 = MessageService.create_message(subject='Lorem ipsum', email='john.doe@foo.com', name='John Doe',
                                                 message='Lorem ipsum dolor sit ament...')
        messages, total_pages = MessageService.filter_messages(MessageFilterType.INBOX, 1)
        self.assertEqual(2, total_pages)
        self.assertListEqual([message3, message2], list(messages))

        messages, total_pages = MessageService.filter_messages(MessageFilterType.INBOX, 2)
        self.assertEqual(2, total_pages)
        self.assertListEqual([MESSAGE_INBOX], list(messages))

    def test_filter_messages_inbox_no_messages(self):
        ContactMessage.objects.all().delete()
        messages, total_pages = MessageService.filter_messages(MessageFilterType.INBOX, 1)
        self.assertListEqual([], list(messages))
        self.assertEqual(1, total_pages)

    @mock.patch('climate.services.service_impl.ContactMessage.objects.filter',
                mock.Mock(side_effect=Exception('Test exception raised to verify a test method (this is OK)')))
    def test_filter_messages_unexpected_error(self):
        messages, total_pages = MessageService.filter_messages(MessageFilterType.INBOX, 1)
        self.assertIsNone(messages)
        self.assertIsNone(total_pages)

    def test_filter_messages_dismissed(self):
        from .data_for_testing import MESSAGE_DISMISSED
        messages, total_pages = MessageService.filter_messages(MessageFilterType.DISMISSED, 1)
        self.assertEqual(1, total_pages)
        self.assertListEqual([MESSAGE_DISMISSED], list(messages))
