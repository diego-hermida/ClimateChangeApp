from utilities.postgres_util import import_psycopg2

import_psycopg2()

from unittest import mock
from django.test import SimpleTestCase
from climate.services.cache_service_impl import CacheLikeService, CacheLocationService, CacheCountryService, \
    CacheGlobalClimateChangeService


class CacheLikeServiceTestCase(SimpleTestCase):

    @mock.patch('climate.services.cache_service_impl.LikeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_increase_like_counter_not_in_cache(self, mock_cache, mock_service):
        mock_cache.incr.side_effect = ValueError('Test exception raised to verify a test method (this is OK)')
        mock_service.increase_like_counter.return_value = 1
        result = CacheLikeService.increase_like_counter()
        self.assertTrue(mock_service.increase_like_counter.called)
        self.assertTrue(mock_cache.incr.called)
        self.assertEqual(1, result)

    @mock.patch('climate.services.cache_service_impl.LikeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_increase_like_counter_in_cache(self, mock_cache, mock_service):
        mock_service.increase_like_counter.return_value = 1
        result = CacheLikeService.increase_like_counter()
        self.assertTrue(mock_service.increase_like_counter.called)
        self.assertTrue(mock_cache.incr.called)
        self.assertEqual(1, result)

    @mock.patch('climate.services.cache_service_impl.LikeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_like_count_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = 3
        result = CacheLikeService.get_like_count()
        self.assertEqual(3, result)
        self.assertTrue(mock_cache.get.called)
        self.assertFalse(mock_cache.set.called)
        self.assertFalse(mock_service.called)

    @mock.patch('climate.services.cache_service_impl.LikeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_like_count_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_like_count.return_value = 3
        result = CacheLikeService.get_like_count()
        self.assertEqual(3, result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_like_count.called)


class CacheLocationServiceTestCase(SimpleTestCase):

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_has_air_pollution_measures(self, mock_service):
        CacheLocationService.has_air_pollution_measures(13)
        self.assertTrue(mock_service.has_air_pollution_measures.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_single_air_pollution_measure(self, mock_service):
        CacheLocationService.get_single_air_pollution_measure(13)
        self.assertTrue(mock_service.get_single_air_pollution_measure.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_has_historical_weather_measures(self, mock_service):
        CacheLocationService.has_historical_weather_measures(13)
        self.assertTrue(mock_service.has_historical_weather_measures.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_weather_forecast_data(self, mock_service):
        CacheLocationService.get_weather_forecast_data(13)
        self.assertTrue(mock_service.get_weather_forecast_data.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_single_current_conditions_measure(self, mock_service):
        CacheLocationService.get_single_current_conditions_measure(13)
        self.assertTrue(mock_service.get_single_current_conditions_measure.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_nearest_location_from_coordinates(self, mock_service):
        CacheLocationService.get_nearest_location_from_coordinates(latitude=43.0097384, longitude=-7.55675819)
        self.assertTrue(mock_service.get_nearest_location_from_coordinates.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_locations_by_keywords(self, mock_service):
        CacheLocationService.get_locations_by_keywords(keywords='foo baz bar')
        self.assertTrue(mock_service.get_locations_by_keywords.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_air_pollution_data(self, mock_service):
        CacheLocationService.get_air_pollution_data(location_id=13, start_epoch=0, end_epoch=1)
        self.assertTrue(mock_service.get_air_pollution_data.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_air_pollution_colors(self, mock_service):
        CacheLocationService.get_air_pollution_colors()
        self.assertTrue(mock_service.get_air_pollution_colors.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_air_pollution_pollutants_display(self, mock_service):
        CacheLocationService.get_air_pollution_pollutants_display()
        self.assertTrue(mock_service.get_air_pollution_pollutants_display.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_historical_weather_data(self, mock_service):
        CacheLocationService.get_historical_weather_data(location_id=13, temperature_type=0)
        self.assertTrue(mock_service.get_historical_weather_data.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    def test_get_historical_weather_stats(self, mock_service):
        CacheLocationService.get_historical_weather_stats(location_id=13)
        self.assertTrue(mock_service.get_historical_weather_stats.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_all_locations_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = []
        result = CacheLocationService.get_all_locations()
        self.assertListEqual([], result)
        self.assertTrue(mock_cache.get.called)
        self.assertFalse(mock_cache.set.called)
        self.assertFalse(mock_service.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_all_locations_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_all_locations.return_value = []
        result = CacheLocationService.get_all_locations()
        self.assertListEqual([], result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_all_locations.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_single_location_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = 'foo'
        result = CacheLocationService.get_single_location(13)
        self.assertEqual('foo', result)
        self.assertTrue(mock_cache.get.called)
        self.assertFalse(mock_cache.set.called)
        self.assertFalse(mock_service.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_single_location_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_single_location.return_value = 'foo'
        result = CacheLocationService.get_single_location(13)
        self.assertEqual('foo', result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_single_location.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_single_location_not_in_cache_returns_none(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_single_location.return_value = None
        result = CacheLocationService.get_single_location(13)
        self.assertIsNone(result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_single_location.called)

    @mock.patch('climate.services.cache_service_impl.LocationService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_single_location_not_in_cache_from_cached_none_value(self, mock_cache, mock_service):
        mock_cache.get.return_value = (None, 'from_cache')
        result = CacheLocationService.get_single_location(13)
        self.assertIsNone(result)
        self.assertTrue(mock_cache.get.called)
        self.assertFalse(mock_cache.set.called)
        self.assertFalse(mock_service.get_single_location.called)


class CacheCountryServiceTestCase(SimpleTestCase):

    @mock.patch('climate.services.cache_service_impl.CountryService')
    def test_get_countries_by_keywords(self, mock_service):
        CacheCountryService.get_countries_by_keywords(keywords='foo baz bar')
        self.assertTrue(mock_service.get_countries_by_keywords.called)

    @mock.patch('climate.services.cache_service_impl.CountryService')
    def test_get_data_from_indicators(self, mock_service):
        CacheCountryService.get_data_from_indicators(country_id='XX', indicators=['foo', 'baz', 'bar'])
        self.assertTrue(mock_service.get_data_from_indicators.called)

    @mock.patch('climate.services.cache_service_impl.CountryService')
    def test_count_monitored_locations(self, mock_service):
        CacheCountryService.count_monitored_locations(country_id='XX')
        self.assertTrue(mock_service.count_monitored_locations.called)

    @mock.patch('climate.services.cache_service_impl.CountryService')
    def test_fetch_monitored_location_id(self, mock_service):
        CacheCountryService.fetch_monitored_location_id(country_id='XX')
        self.assertTrue(mock_service.fetch_monitored_location_id.called)

    @mock.patch('climate.services.cache_service_impl.CountryService')
    def test_get_population_data(self, mock_service):
        CacheCountryService.get_population_data(country_id='XX')
        self.assertTrue(mock_service.get_population_data.called)

    @mock.patch('climate.services.cache_service_impl.CountryService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_single_country_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = 'foo'
        result = CacheCountryService.get_single_country('XX')
        self.assertEqual('foo', result)
        self.assertTrue(mock_cache.get.called)
        self.assertFalse(mock_cache.set.called)
        self.assertFalse(mock_service.called)

    @mock.patch('climate.services.cache_service_impl.CountryService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_single_country_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_single_country.return_value = 'foo'
        result = CacheCountryService.get_single_country('XX')
        self.assertEqual('foo', result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_single_country.called)


class CacheGlobalClimateChangeServiceTestCase(SimpleTestCase):

    @mock.patch('climate.services.cache_service_impl.GlobalClimateChangeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_sea_level_rise_data_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = []
        result = CacheGlobalClimateChangeService.get_sea_level_rise_data()
        self.assertListEqual([], result)
        self.assertTrue(mock_cache.get.called)
        self.assertFalse(mock_service.get_sea_level_rise_data.called)

    @mock.patch('climate.services.cache_service_impl.GlobalClimateChangeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_sea_level_rise_data_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_sea_level_rise_data.return_value = []
        result = CacheGlobalClimateChangeService.get_sea_level_rise_data()
        self.assertListEqual([], result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_sea_level_rise_data.called)

    @mock.patch('climate.services.cache_service_impl.GlobalClimateChangeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_ice_extent_data_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = []
        result = CacheGlobalClimateChangeService.get_ice_extent_data()
        self.assertTrue(mock_cache.get.called)
        self.assertListEqual([], result)
        self.assertFalse(mock_service.get_ice_extent_data.called)

    @mock.patch('climate.services.cache_service_impl.GlobalClimateChangeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_ice_extent_data_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_ice_extent_data.return_value = []
        result = CacheGlobalClimateChangeService.get_ice_extent_data()
        self.assertListEqual([], result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_ice_extent_data.called)

    @mock.patch('climate.services.cache_service_impl.GlobalClimateChangeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_future_emissions_data_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = []
        result = CacheGlobalClimateChangeService.get_future_emissions_data()
        self.assertTrue(mock_cache.get.called)
        self.assertListEqual([], result)
        self.assertFalse(mock_service.get_future_emissions_data.called)

    @mock.patch('climate.services.cache_service_impl.GlobalClimateChangeService')
    @mock.patch('climate.services.cache_service_impl.cache')
    def test_get_future_emissions_data_not_in_cache(self, mock_cache, mock_service):
        mock_cache.get.return_value = None
        mock_service.get_future_emissions_data.return_value = []
        result = CacheGlobalClimateChangeService.get_future_emissions_data()
        self.assertListEqual([], result)
        self.assertTrue(mock_cache.get.called)
        self.assertTrue(mock_cache.set.called)
        self.assertTrue(mock_service.get_future_emissions_data.called)
