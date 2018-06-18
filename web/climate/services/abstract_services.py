from abc import ABC, abstractstaticmethod

import climate.dto as dto
from climate.webmodels.models import ContactMessage
from django.core.paginator import Paginator

from data_conversion_subsystem.data.models import AirPollutionMeasure, CurrentConditionsObservation, Location


class AbstractLikeService(ABC):

    @staticmethod
    @abstractstaticmethod
    def increase_like_counter() -> bool:
        """
            Atomically increments the application's like counter.
            :return: True if the counter has been incremented, False otherwise.
            :rtype: bool
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_like_count() -> int:
        """
            Retrieves the current value of the application's like counter.
            :return: An `int`.
            :rtype: int
        """
        raise NotImplemented


class AbstractLocationService(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_nearest_location_from_coordinates(latitude: float, longitude: float) -> Location:
        """
            Given a pair of coordinates, retrieves the nearest location to them. If no locations are available,
            this operation will return None instead.
            :param latitude: A `float` object, representing the latitude.
            :param longitude: A `float` object, representing the longitude.
            :return: A `Location`, the nearest one to the given coordinates.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_all_locations(fields, order_by, as_objects) -> list:
        """
            Retrieves all locations. If no locations are available, an empty list will be returned.
            :param fields: If set, retrieves only those specific attributes.
            :param order_by: Orders the list of Locations by the given fields. Must be a `list` of `str`.
            :param as_objects: If True, retrieves the Locations as objects. Otherwise, a location will be represented
                               as a `dict`, where the keys are the entity attributes.
            :return: A `list` of `Location` objects, or a `list` of `dict` objects, depending on the value of
                     `as_objects`.
            :rtype: list
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_locations_by_keywords(keywords, max_results: int) -> tuple:
        """
            Given a list of keywords, retrieves those ones where at least, one keyword partially matches their name.
            Matching is performed as an OR operation, and is case-insensitive.
            :param keywords: A `list` of `str` objects.
            :param max_results: At most, `max_results` results will be retrieved.
            :return: A `tuple` of two values: A `list` of `Location` objects, or an empty list, if no matches; and a
                     `bool` object, which will be True if there were more results available; and False, otherwise.
            :rtype: tuple
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_location(id) -> dto.LocationDto:
        """
            Given an identifier of a Location, retrieves a LocationDto.
            :param id: It can be either an `int` (the PK of the Location object), or the Location object itself.
            :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
            :return: A LocationDto object, with all the necessary data for displaying the location info.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_air_pollution_data(location_id: int, start_epoch: int, end_epoch: int, as_objects):
        """
            Retrieves air pollution data for a given location.
            :param location_id: PK to a `Location` object.
            :param start_epoch: Start timestamp, represented as milliseconds since epoch.
            :param end_epoch: End timestamp, represented as milliseconds since epoch.
            :param as_objects: If True, retrieved values will be instances of the class `AirPollutionMeasure`.
                               Otherwise, a `tuple` containing the `list` of values (`dict` objects) and the dominant
                               pollutant's data, as a `list`, as well.
            :return: Read the `as_objects` description.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_air_pollution_colors() -> list:
        """
            Retrieves a list of air pollution colors, defined by the model.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_air_pollution_pollutants_display() -> list:
        """
            Retrieves a list of air pollution colors (HEX), defined by the model.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def has_air_pollution_measures(location_id: int) -> bool:
        """
            Determines if a location has air pollution data.
            :param location_id: PK to a Location object.
            :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
            :return: True, if some value exists, False otherwise.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_air_pollution_measure(measure_id: int) -> AirPollutionMeasure:
        """
            Retrieves an air pollution measure by identifier.
            :param measure_id: PK to an AirPollutionMeasure object.
            :return: An AirPollutionMeasure object; or None, if that object does not exist.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def has_historical_weather_measures(location_id: int) -> bool:
        """
           Determines if a location has historical weather data.
           :param location_id: PK to a Location object.
           :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
           :return: True, if some value exists, False otherwise.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_weather_forecast_data(location_id: int) -> (list, list):
        """
            Retrieves weather forecast data for a given location.
            :param location_id: PK to a Location object.
            :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
            :return: A `tuple` of two lists: one contains the WeatherForecastObservation values, and the other one
                     aggregates the values of the max and min temperatures, for each day.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_current_conditions_measure(location_id: int) -> CurrentConditionsObservation:
        """
            Given an identifier of a Location, retrieves its CurrentConditionsObservation (remember these entities
            maintain an 1:1 relationship)
            :param id: PK to a Location object
            :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
            :return: A CurrentConditionsObservation object.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_historical_weather_data(location_id: int, temperature_type: int, start_year: int, end_year: int,
                                    as_objects) -> (list, bool):
        """
            Retrieves historical weather data.
            :param location_id: PK to a Location object.
            :param temperature_type: A key to a TemperatureType value.
            :param start_year: An `int`, representing the start year; or None.
            :param end_year: An `int`, representing the end year; or None.
            :param as_objects: If True, values will be retrieved as HistoricalWeatherObservation object. Otherwise,
                               `dict` objects will be retrieved.
            :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
            :return: A `tuple`. The first element is the `list` of data. The second one is a `bool` object, which
                     represents whether the date range has been set or not.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_historical_weather_stats(location_id: int, start_year, end_year) -> (list, bool):
        """
            Retrieves historical weather statistics.
            :param location_id: PK to a Location object.
            :param start_year: An `int`, representing the start year; or None.
            :param end_year: An `int`, representing the end year; or None.
            :raises: Location.DoesNotExist, if the identifier points to a non-existent object.
            :return: A `tuple`. The first element is the `list` of data. The second one is a `bool` object, which
                     represents whether the date range has been set or not.
        """
        raise NotImplemented


class AbstractCountryService(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_countries_by_keywords(keywords: list, max_results: int) -> (list, bool):
        """
            Given a list of keywords, retrieves those ones where at least, one keyword partially matches their name.
            Matching is performed as an OR operation, and is case-insensitive.
            :param keywords: A `list` of `str` objects.
            :param max_results: At most, `max_results` results will be retrieved.
            :return: A `tuple` of two values: A `list` of `Country` objects, or an empty list, if no matches; and a
                     `bool` object, which will be True if there were more results available; and False, otherwise.
            :rtype: tuple
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_single_country(id) -> dto.CountryDto:
        """
            Given an identifier of a Country, retrieves a CountryDto.
            :param id: It can be either an `int` (the PK of the Country object), or the Country object itself.
            :raises: Country.DoesNotExist, if the identifier points to a non-existent object.
            :return: A CountryDto object, with all the necessary data for displaying the country info.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_data_from_indicators(country_id: str, indicators: list, start_year: int, end_year: int,
                                 null_values: bool) -> list:
        """
            Retrieves historical weather data.
            :param country_id: PK to a Location object.
            :param indicators: A list of PK to CountryIndicatorDetails objects.
            :param start_year: An `int`, representing the start year; or None.
            :param end_year: An `int`, representing the end year; or None.
            :raises: Country.DoesNotExist, if the identifier points to a non-existent object.
            :return: A `list` of CountryIndicator objects. Values will be sorted by indicator and year.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def count_monitored_locations(country_id: str) -> int:
        """
            Counts the amount of monitored locations.
            :param id: PK to a Country object.
            :raises: Country.DoesNotExist, if the identifier points to a non-existent object.
            :return: An `int`.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def fetch_monitored_location_id(country_id: str) -> int:
        """
            Fetches the PK of a monitored location, where such location has the given country ID.
            Note: This operation should be only used if the number of monitored locations equals 1. Otherwise, the
            operation will fail.
            :param country_id: PK to a Country object. The retrieved location will be in that country.
            :return: The PK to the Location object.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_population_data(country_id: str) -> (int, int, int, int, float):
        """
            Computes population data for a given country.
            :param country_id: PK to a Country object.
            :return: A tuple, containing: last year, last year's value, previous year, previous year's value and the
                     difference between the two values, in percentage.
        """
        raise NotImplemented


class AbstractGlobalClimateChangeService(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_sea_level_rise_data() -> list:
        """
            Retrieves a list with all the SeaLevelRise objects.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_ice_extent_data() -> list:
        """
            Retrieves a list with all the OceanMass objects.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def get_future_emissions_data() -> list:
        """
            Retrieves a list with all the RpcDatabaseEmission objects.
        """
        raise NotImplemented


class AbstractAdminService(ABC):

    @staticmethod
    @abstractstaticmethod
    def login(user: str, password: str, request) -> bool:
        """
            Performs a login operation.
            :param user: Username.
            :param password: Password.
            :param request: A request object, required by Django.
            :return: Whether the user has been successfully authenticated.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def logout(request) -> bool:
        """
            Performs a logout operation.
            :param request: A request object, required by Django.
            :return: Whether the user has been successfully logged out.
        """
        raise NotImplemented


class AbstractMessageService(ABC):

    @staticmethod
    @abstractstaticmethod
    def create_message(subject, email, name, message) -> ContactMessage:
        """
            Creates a ContactMessage object.
            :param subject: Subject of the message.
            :param email: Email of the user.
            :param name: Name of the user.
            :param message: Body of the message.
            :return: The created instance.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def update_or_delete(message_id: int, action: int):
        """
            Executes an update or a delete operation on a message, depending on the value of the `action` parameter.
            :param message_id: PK to a ContactMessage object.
            :param action: A value of MessageActionType.
            :return: True, if the operation was successful. False, if not. None, if the ContactMessage does not exist.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def filter_messages(message_filter, page_number: int) -> (Paginator, int):
        """
            Performs a paginated query of messages. Messages will also be filtered, depending on the value of the
            `message_filter` parameter.
            :param message_filter: A value of MessageFilterType.
            :param page_number: The number of the page. Will default to 1, if not set.
            :return: A Paginator object, containing the ContactMessage objects, and the total amount of pages.
        """
        raise NotImplemented

    @staticmethod
    @abstractstaticmethod
    def count_unread_messages() -> int:
        """
            Retrieves the count of unreaded messages.
            :return: An `int`, or None, if an error occurred.
        """
        raise NotImplemented
