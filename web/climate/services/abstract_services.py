from abc import ABC, abstractstaticmethod

import climate.dto as dto
from climate.webmodels.models import ContactMessage
from django.core.paginator import Paginator

from data_conversion_subsystem.data.models import AirPollutionMeasure, CurrentConditionsObservation, Location


class AbstractLikeService(ABC):

    @staticmethod
    @abstractstaticmethod
    def increase_like_counter():
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_like_count():
        raise NotImplemented


class AbstractLocationService(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_nearest_location_from_coordinates(latitude: float, longitude: float) -> Location:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_all_locations(fields, order_by, as_objects) -> list:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_locations_by_keywords(keywords, max_results: int) -> list:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_location(id) -> dto.LocationDto:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_air_pollution_data(location_id: int, start_epoch: int, end_epoch: int, as_objects):
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_air_pollution_colors() -> list:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_air_pollution_pollutants_display() -> list:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def has_air_pollution_measures(location_id: int) -> bool:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_air_pollution_measure(measure_id: int) -> AirPollutionMeasure:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def has_historical_weather_measures(location_id: int) -> bool:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_weather_forecast_data(location_id: int) -> (list, list):
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_current_conditions_measure(location_id: int) -> CurrentConditionsObservation:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_historical_weather_data(location_id: int, temperature_type: int, start_year: int, end_year: int,
                                    as_objects) -> (list, bool):
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_historical_weather_stats(location_id: int, start_year, end_year) -> (list, bool):
        raise NotImplemented


class AbstractCountryService(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_countries_by_keywords(keywords: list, max_results: int) -> (list, bool):
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_country(id) -> dto.CountryDto:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_data_from_indicators(country_id: str, indicators: list, start_year: int, end_year: int,
                                 null_values: bool) -> list:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def count_monitored_locations(country_id: str) -> int:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def fetch_monitored_location_id(country_id: str) -> int:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_population_data(country_id: str) -> (int, int, int, int, float):
        raise NotImplemented


class AbstractGlobalClimateChangeService(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_sea_level_rise_data() -> list:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_ice_extent_data():
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_future_emissions_data():
        raise NotImplemented


class AbstractAdminService(ABC):

    @staticmethod
    @abstractstaticmethod
    def login(user: str, password: str, request) -> bool:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def logout(request) -> bool:
        raise NotImplemented


class AbstractMessageService(ABC):

    @staticmethod
    @abstractstaticmethod
    def create_message(subject, email, name, message) -> ContactMessage:
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def update_or_delete(message_id: int, action: int):
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def filter_messages(message_filter, page_number: int) -> (Paginator, int):
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def count_unread_messages():
        raise NotImplemented
