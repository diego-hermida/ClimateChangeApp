from functools import wraps

import climate.dto as dto
from django.core.cache import cache

from data_conversion_subsystem.data.models import Location
from .abstract_services import AbstractCountryService, AbstractGlobalClimateChangeService, AbstractLikeService, \
    AbstractLocationService
from .services import CountryService, GlobalClimateChangeService, LikeService, LocationService


def fetch_from_cache(key, timeout):
    def real_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            actual_key = key(*args, **kwargs) if callable(key) else key
            cached_value = cache.get(actual_key)
            if cached_value is None:
                value = f(*args, **kwargs)
                if value is not None:  # Avoiding caching function calls which doesn't return a value
                    cache.set(actual_key, value, timeout)
                return value
            else:
                return cached_value

        return wrapper

    return real_decorator


class CacheLikeService(AbstractLikeService):

    @staticmethod
    def increase_like_counter() -> bool:
        result = LikeService.increase_like_counter()
        if result:
            try:
                cache.incr('like_counter', 1)
            except ValueError:
                pass  # Key does not exist in cache, will be retrieved from database
        return result

    @staticmethod
    @fetch_from_cache('like_counter', 30)
    def get_like_count():
        return LikeService.get_like_count()


class CacheLocationService(AbstractLocationService):

    @staticmethod
    def get_nearest_location_from_coordinates(latitude: float, longitude: float) -> Location:
        return LocationService.get_nearest_location_from_coordinates(latitude, longitude)

    @staticmethod
    @fetch_from_cache('locations', 60 * 15)
    def get_all_locations(fields, order_by: tuple = ('name',), as_objects=True) -> list:
        return LocationService.get_all_locations(fields, order_by, as_objects)

    @staticmethod
    def get_locations_by_keywords(keywords, max_results: int = 10):
        return LocationService.get_locations_by_keywords(keywords, max_results)

    @staticmethod
    @fetch_from_cache(lambda n: 'location__%d' % (n if isinstance(n, int) else n.id), 60 * 15)
    def get_single_location(id):
        return LocationService.get_single_location(id)

    @staticmethod
    def get_air_pollution_data(location_id: int, start_epoch: int, end_epoch: int, as_objects=True):
        return LocationService.get_air_pollution_data(location_id, start_epoch, end_epoch, as_objects)

    @staticmethod
    def get_air_pollution_colors() -> list:
        return LocationService.get_air_pollution_colors()

    @staticmethod
    def get_air_pollution_pollutants_display() -> list:
        return LocationService.get_air_pollution_pollutants_display()

    @staticmethod
    def get_historical_weather_data(location_id: int, temperature_type: int, start_year: int = None,
                                    end_year: int = None, as_objects=True) -> (list, bool):
        return LocationService.get_historical_weather_data(location_id, temperature_type, start_year, end_year,
                                                           as_objects)

    @staticmethod
    def get_historical_weather_stats(location_id: int, start_year: int = None, end_year: int = None) -> (list, bool):
        return LocationService.get_historical_weather_stats(location_id, start_year, end_year)


class CacheCountryService(AbstractCountryService):

    @staticmethod
    def get_countries_by_keywords(keywords: list, max_results: int) -> (list, bool):
        return CountryService.get_countries_by_keywords(keywords, max_results)

    @staticmethod
    @fetch_from_cache(lambda n: 'country__%s' % (n if isinstance(n, str) else n.iso2_code), 60 * 60 * 12)
    def get_single_country(id) -> dto.CountryDto:
        # Using the decorator inside the function, in order to dynamically set the cache key
        return CountryService.get_single_country(id)

    @staticmethod
    def get_data_from_indicators(country_id: str, indicators: list, start_year: int = None, end_year: int = None,
                                 null_values: bool = False) -> list:
        return CountryService.get_data_from_indicators(country_id, indicators, start_year, end_year, null_values)


class CacheGlobalClimateChangeService(AbstractGlobalClimateChangeService):

    @staticmethod
    @fetch_from_cache('sea_level_rise', 60 * 60 * 12)
    def get_sea_level_rise_data() -> list:
        return GlobalClimateChangeService.get_sea_level_rise_data()

    @staticmethod
    @fetch_from_cache('ice_extent', 60 * 60 * 12)
    def get_ice_extent_data():
        return GlobalClimateChangeService.get_ice_extent_data()

    @staticmethod
    @fetch_from_cache('future_emissions', 60 * 60 * 12)
    def get_future_emissions_data():
        return GlobalClimateChangeService.get_future_emissions_data()
