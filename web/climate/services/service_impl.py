from functools import wraps

import climate.dto as dto
from climate.config.config import WEB_CONFIG
from climate.webmodels.models import ContactMessage, LikeCount
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Avg, Case, Count, Max, Min, When

from data_conversion_subsystem.data.models import AirPollutionMeasure, Country, CountryIndicator, \
    CurrentConditionsObservation, HistoricalWeatherObservation, Location, OceanMassMeasure, RpcDatabaseEmission, \
    SeaLevelRiseMeasure, WeatherForecastObservation
from utilities.postgres_util import get_query
from utilities.util import current_timestamp
from .abstract_services import AbstractAdminService, AbstractCountryService, AbstractGlobalClimateChangeService, \
    AbstractLikeService, AbstractLocationService, AbstractMessageService


class TemperatureType:
    MAX_TEMP = 1
    MEAN_TEMP = 2
    MIN_TEMP = 3

    _values = {MAX_TEMP: 'max_temp', MIN_TEMP: 'min_temp', MEAN_TEMP: 'mean_temp'}
    _representations = {_values[MAX_TEMP]: MAX_TEMP, _values[MIN_TEMP]: MIN_TEMP, _values[MEAN_TEMP]: MEAN_TEMP}

    @staticmethod
    def get_representation(key: int) -> str:
        return TemperatureType._values.get(key)

    @staticmethod
    def from_representation(value: str) -> int:
        return TemperatureType._representations.get(value)


class MessageFilterType:
    DISMISSED = 1
    REPLIED = 2
    INBOX = 3
    _values = {DISMISSED: 'dismissed', REPLIED: 'replied', INBOX: 'inbox'}
    _representations = {_values[DISMISSED]: DISMISSED, _values[REPLIED]: REPLIED, _values[INBOX]: INBOX}

    @staticmethod
    def get_representation(key: int) -> str:
        return MessageFilterType._values.get(key)

    @staticmethod
    def from_representation(value: str) -> int:
        return MessageFilterType._representations.get(value)


class MessageActionType:
    REPLY = 1
    DISMISS = 2
    RESTORE = 3
    DELETE = 4
    # When linking actions with filters, None means that the current filter will be used
    _actions_filters = {REPLY: MessageFilterType.get_representation(MessageFilterType.REPLIED),
                        DISMISS: MessageFilterType.get_representation(MessageFilterType.DISMISSED),
                        RESTORE: MessageFilterType.get_representation(MessageFilterType.INBOX), DELETE: None}
    _values = {DISMISS: 'dismiss', REPLY: 'reply', RESTORE: 'restore', DELETE: 'delete'}
    _representations = {_values[REPLY]: REPLY, _values[DISMISS]: DISMISS, _values[RESTORE]: RESTORE,
                        _values[DELETE]: DELETE}

    @staticmethod
    def get_filter_name(key: int, current_filter_name=None):
        result = MessageActionType._actions_filters.get(key, current_filter_name)
        return result if result else current_filter_name

    @staticmethod
    def get_representation(key: int) -> str:
        return MessageActionType._values.get(key)

    @staticmethod
    def from_representation(value: str) -> int:
        return MessageActionType._representations.get(value)


def require_valid_entity(entity, field_name):
    """
        By decorating a method with this,
        :param entity: Django model class, which must inherit from django.db.models.Model
        :param field_name: Name of the arg or kwarg parameter representing an object identifier
        :raises: <entity>.DoesNotExist, if such object does not exist.
    """

    def real_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # args[0] is the first argument of the callee (which is the location_id).
            identifier = kwargs.get(field_name, args[0])
            if not entity.objects.filter(pk=identifier).exists():
                raise entity.DoesNotExist()
            return f(*args, **kwargs)

        return wrapper

    return real_decorator


class LikeService(AbstractLikeService):

    @staticmethod
    def increase_like_counter() -> bool:
        try:
            success = LikeCount.increment_atomic()
            # Creating counter if it did not exist FIXES [BUG-042]
            if not success and not LikeCount.objects.filter(pk=0).exists():
                LikeCount.objects.create()
                return LikeCount.increment_atomic()
            return True
        except Exception:
            return False

    @staticmethod
    def get_like_count():
        try:
            return LikeCount.objects.get(pk=0).counter  # Fetching the current "like" count from database
        except LikeCount.DoesNotExist:
            LikeCount.objects.create()
            return 0


class LocationService(AbstractLocationService):

    @staticmethod
    def get_nearest_location_from_coordinates(latitude: float, longitude: float) -> Location:
        try:
            sql = "SELECT * FROM data_location ORDER BY ((latitude - %s) * (latitude - %s)) + " \
                  "((longitude - %s) * (longitude - %s)) LIMIT 1"
            return Location.objects.raw(sql, [latitude, latitude, longitude, longitude])[0]
        except (Location.DoesNotExist, IndexError):
            return None

    @staticmethod
    def get_all_locations(fields=None, order_by: tuple = ('name',), as_objects=True) -> list:
        data = Location.objects.only(*fields).order_by(*order_by) if fields else Location.objects.order_by(*order_by)
        # Filtering only necessary values FIXES [BUG-043]
        return list(data) if as_objects else list(
                [{field: getattr(value, field) for field in fields} for value in data] if fields else data.values())

    @staticmethod
    def get_locations_by_keywords(keywords: list, max_results: int = WEB_CONFIG['MAX_SEARCH_RESULTS']):
        return _get_entity_by_keywords(Location, keywords, max_results, ['name'], 'name', case_sensitive=False)

    @staticmethod
    def get_single_location(id) -> dto.LocationDto:
        try:
            location = id if isinstance(id, Location) else Location.objects.get(pk=id)
            has_air_pollution_data = location.air_pollution_data and LocationService.has_air_pollution_measures(
                    location.id)
            has_historical_weather_data = location.wunderground_data and LocationService.has_historical_weather_measures(
                    location.id)
            air_pollution_last_measure = None if not location.air_pollution_last_measure_id else \
                LocationService.get_single_air_pollution_measure(location.air_pollution_last_measure_id)
            current_conditions = None if not location.owm_data else \
                LocationService.get_single_current_conditions_measure(location.id)
            weather_forecast = [], [] if not location.owm_data else LocationService.get_weather_forecast_data(
                    location.id)
            return dto.LocationDto(location, has_air_pollution_data, has_historical_weather_data,
                                   air_pollution_last_measure, current_conditions, weather_forecast)
        except Location.DoesNotExist:
            return None

    @staticmethod
    @require_valid_entity(Location, 'location_id')
    def get_air_pollution_data(location_id: int, start_epoch: int, end_epoch: int, as_objects=True):
        db_data = AirPollutionMeasure.objects.only('timestamp_epoch', 'co_aqi', 'no2_aqi', 'o3_aqi', 'pm25_aqi',
                                                   'pm10_aqi', 'dominant_pollutant', 'so2_aqi').filter(
                location_id=location_id, timestamp_epoch__range=(start_epoch, end_epoch)).order_by('timestamp_epoch')
        return list(db_data) if as_objects else [
            (x.timestamp_epoch, x.co_aqi, x.no2_aqi, x.o3_aqi, x.pm25_aqi, x.pm10_aqi) for x in db_data], [
                   x.dominant_pollutant for x in db_data]

    @staticmethod
    def get_air_pollution_colors() -> list:
        return AirPollutionMeasure.get_color_list()

    @staticmethod
    def get_air_pollution_pollutants_display() -> list:
        return AirPollutionMeasure.get_pollutants_display()

    @staticmethod
    def has_air_pollution_measures(location_id: int) -> bool:
        if not Location.objects.filter(pk=location_id).exists():
            raise Location.DoesNotExist
        return AirPollutionMeasure.objects.filter(location_id=location_id).exists()

    @staticmethod
    def get_single_air_pollution_measure(measure_id: int) -> AirPollutionMeasure:
        try:
            return AirPollutionMeasure.objects.get(pk=measure_id)
        except AirPollutionMeasure.DoesNotExist:
            return None

    @staticmethod
    @require_valid_entity(Location, 'location_id')
    def has_historical_weather_measures(location_id: int) -> bool:
        return HistoricalWeatherObservation.objects.filter(location_id=location_id).exists()

    @staticmethod
    @require_valid_entity(Location, 'location_id')
    def get_weather_forecast_data(location_id: int) -> (list, list):
        return list(
            WeatherForecastObservation.objects.filter(location_id=location_id).select_related('weather').values('date',
                    'time', 'weather__icon_code', 'weather__description').order_by('date',
                    'time')), WeatherForecastObservation.objects.filter(location_id=location_id).values(
                    'date').annotate(Max('temperature'), Min('temperature')).order_by('date')

    @staticmethod
    @require_valid_entity(Location, 'location_id')
    def get_single_current_conditions_measure(location_id: int) -> CurrentConditionsObservation:
        try:
            return CurrentConditionsObservation.objects.get(pk=location_id)
        except CurrentConditionsObservation.DoesNotExist:
            return None

    @staticmethod
    @require_valid_entity(Location, 'location_id')
    def get_historical_weather_data(location_id: int, temperature_type: int, start_year: int = None,
                                    end_year: int = None, as_objects=True) -> (list, bool):
        if temperature_type == TemperatureType.MIN_TEMP:
            field = 'min_temp'
        elif temperature_type == TemperatureType.MEAN_TEMP:
            field = 'mean_temp'
        else:
            field = 'max_temp'
        data, no_year_range = _filter_by_year_range(
                HistoricalWeatherObservation.objects.only('date_epoch', field).filter(location_id=location_id),
                start_year, end_year)
        data = data.order_by('date_epoch')
        return list(data) if as_objects else [(x.date_epoch, getattr(x, field)) for x in data], no_year_range

    @staticmethod
    @require_valid_entity(Location, 'location_id')
    def get_historical_weather_stats(location_id: int, start_year: int = None, end_year: int = None) -> (list, bool):
        data = HistoricalWeatherObservation.objects.filter(location_id=location_id).values('year').annotate(
                highest_max=Max('max_temp'), lowest_max=Min('max_temp'), highest_min=Max('min_temp'),
                lowest_min=Min('min_temp'), year_avg=Avg('mean_temp'), fog=Count(Case(When(fog=True, then=1))),
                hail=Count(Case(When(hail=True, then=1))), thunder=Count(Case(When(thunder=True, then=1))),
                tornado=Count(Case(When(tornado=True, then=1))), rain=Count(Case(When(rain=True, then=1))),
                snow=Count(Case(When(snow=True, then=1))))
        data, no_year_range = _filter_by_year_range(data, start_year, end_year)
        return [tuple(x.values()) for x in data.order_by('year')], no_year_range


class CountryService(AbstractCountryService):

    @staticmethod
    def get_countries_by_keywords(keywords: list, max_results: int = WEB_CONFIG['MAX_SEARCH_RESULTS']) -> (list, bool):
        return _get_entity_by_keywords(Country, keywords, max_results, ['name'], 'name')

    @staticmethod
    def get_single_country(id) -> dto.CountryDto:
        try:
            country = id if isinstance(id, Country) else Country.objects.select_related('region', 'income_level').get(
                    pk=id)
            monitored_locations = CountryService.count_monitored_locations(
                    country.iso2_code) if country.region.iso3_code != 'NA' and country.income_level.iso3_code != 'NA' else 0
            monitored_location_id = CountryService.fetch_monitored_location_id(
                    country.iso2_code) if monitored_locations == 1 else None
            population_data = CountryService.get_population_data(country.iso2_code)
            return dto.CountryDto(country, monitored_locations, monitored_location_id, population_data)
        except Country.DoesNotExist:
            return None

    @staticmethod
    def get_data_from_indicators(country_id: str, indicators: list, start_year: int = None, end_year: int = None,
                                 null_values: bool = False) -> list:
        data = \
            _filter_by_year_range(CountryIndicator.objects.filter(country_id=country_id, indicator_id__in=indicators),
                                  start_year, end_year)[0]
        data = data if null_values else data.filter(value__isnull=False)
        return list(data.order_by('indicator', 'year'))

    @staticmethod
    @require_valid_entity(Country, 'country_id')
    def count_monitored_locations(country_id: str) -> int:
        return Location.objects.filter(country_id=country_id).count()

    @staticmethod
    @require_valid_entity(Country, 'country_id')
    def fetch_monitored_location_id(country_id: str) -> int:
        try:
            return Location.objects.filter(country_id=country_id).values_list('id').get()[0]
        except Location.DoesNotExist:
            return None

    @staticmethod
    @require_valid_entity(Country, 'country_id')
    def get_population_data(country_id: str) -> (int, int, int, int, float):
        last_year = CountryIndicator.objects.filter(country_id=country_id, indicator_id='SP.POP.TOTL').exclude(
                value__isnull=True).aggregate(Max('year'))['year__max']
        previous_year = \
        CountryIndicator.objects.filter(country_id=country_id, year__lt=last_year, indicator_id='SP.POP.TOTL').exclude(
                value__isnull=True).aggregate(Max('year'))['year__max'] if last_year else None
        if last_year and previous_year:
            data = CountryIndicator.objects.filter(country_id=country_id, indicator_id='SP.POP.TOTL',
                                                   year__in=[last_year, previous_year]).values_list('value').order_by(
                    '-year')
            pop = int(data[0][0])
            previous_pop = int(data[1][0])
            return pop, last_year, previous_pop, previous_year, (
                    ((pop - previous_pop) / previous_pop) * 100) if pop and previous_pop else None
        else:
            return None, None, None, None, None


class GlobalClimateChangeService(AbstractGlobalClimateChangeService):

    @staticmethod
    def get_sea_level_rise_data() -> list:
        return list(
                SeaLevelRiseMeasure.objects.values_list('timestamp_epoch', 'value', 'year').order_by('timestamp_epoch'))

    @staticmethod
    def get_ice_extent_data():
        return list(
            OceanMassMeasure.objects.filter().values_list('timestamp_epoch', 'mass', 'year', 'type', 'trend').order_by(
                'timestamp_epoch'))

    @staticmethod
    def get_future_emissions_data():
        return list(RpcDatabaseEmission.objects.filter(
                scenario__in=[RpcDatabaseEmission.RPC_26, RpcDatabaseEmission.RPC_45, RpcDatabaseEmission.RPC_60,
                              RpcDatabaseEmission.RPC_85]).values_list('year', 'co2', 'scenario').order_by('scenario',
                                                                                                           'year'))


class AdminService(AbstractAdminService):

    @staticmethod
    def login(user: str, password: str, request) -> bool:
        user = authenticate(username=user, password=password, request=request)
        if user is not None and user.is_active:
            login(request, user)
            return True
        else:
            return False

    @staticmethod
    def logout(request) -> bool:
        try:
            logout(request)
            return True
        except Exception:
            return False


class MessageService(AbstractMessageService):

    @staticmethod
    def create_message(subject, email, name, message) -> ContactMessage:
        try:
            return ContactMessage.objects.create(email=email, name=name, message=message, subject=subject)
        except Exception:
            return None

    @staticmethod
    def _delete_message(message_id: int):
        try:
            num_deleted = ContactMessage.objects.filter(pk=message_id).delete()[0]
            if num_deleted == 0:
                return None
            else:
                return num_deleted == 1
        except Exception:
            return False

    @staticmethod
    def _update_message(message_id: int, **kwargs):
        try:
            # Changing implementation FIXES [BUG-046]
            kwargs['last_modified'] = current_timestamp(utc=True)
            return True if ContactMessage.objects.filter(pk=message_id).update(**kwargs) == 1 else None
        except Exception:
            return False

    @staticmethod
    def update_or_delete(message_id: int, action: int):
        if action == MessageActionType.REPLY:
            return MessageService._update_message(message_id, replied=True)
        elif action == MessageActionType.DISMISS:
            return MessageService._update_message(message_id, dismissed=True)
        elif action == MessageActionType.RESTORE:
            return MessageService._update_message(message_id, dismissed=False, replied=False)
        elif action == MessageActionType.DELETE:
            return MessageService._delete_message(message_id)

    @staticmethod
    def filter_messages(message_filter, page_number: int) -> (Paginator, int):
        try:
            if message_filter == MessageFilterType.REPLIED:
                query = ContactMessage.objects.filter(replied=True, dismissed=False).order_by('-last_modified')
            elif message_filter == MessageFilterType.DISMISSED:
                query = ContactMessage.objects.filter(dismissed=True).order_by('-last_modified')
            else:
                query = ContactMessage.objects.filter(replied=False, dismissed=False).order_by('-last_modified')
            paginator = Paginator(query, WEB_CONFIG['PAGE_SIZE'])
            total_pages = paginator.num_pages
            return paginator.page(page_number), total_pages
        except EmptyPage:
            return paginator.page(paginator.num_pages), total_pages if paginator else None, None
        except Exception:
            return None, None

    @staticmethod
    def count_unread_messages():
        try:
            return ContactMessage.objects.filter(replied=False, dismissed=False).count()
        except Exception:
            return None


def _get_entity_by_keywords(entity: object, keywords: list, max_results: int, search_fields: list, order_by: str,
                            case_sensitive=True) -> (list, bool):
    keywords = keywords if case_sensitive else [word.lower() for word in keywords]
    result = list(entity.objects.filter(get_query(keywords, search_fields)).order_by(order_by)[:(max_results + 1)])
    if len(result) > max_results:
        return result[:-1], True
    else:
        return result, False


def _filter_by_year_range(data, start, end):
    no_year_range = False
    if start is not None and end is not None:
        data = data.filter(year__range=(start, end))
    elif start is not None:
        data = data.filter(year__gte=start)
    elif end is not None:
        data = data.filter(year__lte=end)
    else:
        no_year_range = True
    return data, no_year_range
