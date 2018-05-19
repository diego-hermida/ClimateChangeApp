import climate.dto as dto
from climate.config.config import WEB_CONFIG
from climate.webmodels.models import ContactMessage, LikeCount
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Avg, Case, Count, Max, Min, When

from data_conversion_subsystem.data.models import AirPollutionMeasure, Country, CountryIndicator, \
    HistoricalWeatherObservation, Location, OceanMassMeasure, RpcDatabaseEmission, SeaLevelRiseMeasure
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
    def get_representation(key):
        return TemperatureType._values.get(key)

    @staticmethod
    def from_representation(value):
        return TemperatureType._representations.get(value)


class MessageFilterType:
    DISMISSED = 1
    REPLIED = 2
    INBOX = 3
    _values = {DISMISSED: 'dismissed', REPLIED: 'replied', INBOX: 'inbox'}
    _representations = {_values[DISMISSED]: DISMISSED, _values[REPLIED]: REPLIED, _values[INBOX]: INBOX}

    @staticmethod
    def get_representation(key):
        return MessageFilterType._values.get(key)

    @staticmethod
    def from_representation(value):
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
    def get_representation(key):
        return MessageActionType._values.get(key)

    @staticmethod
    def from_representation(value):
        return MessageActionType._representations.get(value)


class LikeService(AbstractLikeService):

    @staticmethod
    def increase_like_counter() -> bool:
        try:
            return LikeCount.increment_atomic()
        except LikeCount.DoesNotExist:
            try:
                LikeCount.objects.create()
                return True
            except Exception:
                return False
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
            sql = "SELECT * FROM data_location ORDER BY ((latitude - %s) * (latitude - %s)) + ((longitude - %s) * (longitude - %s)) LIMIT 1"
            return Location.objects.raw(sql, [latitude, latitude, longitude, longitude])[0]
        except Location.DoesNotExist:
            return None

    @staticmethod
    def get_all_locations(fields, order_by: tuple = ('name',), as_objects=True) -> list:
        try:
            data = Location.objects.only(*fields).order_by(*order_by)
            return list(data) if as_objects else list(data.values())
        except Location.DoesNotExist:
            return []

    @staticmethod
    def get_locations_by_keywords(keywords, max_results: int = 10):
        return _get_entity_by_keywords(Location, keywords, max_results, ['name'], 'name')

    @staticmethod
    def get_single_location(id) -> dto.LocationDto:
        try:
            return dto.LocationDto.from_location_id(id) if isinstance(id, int) else dto.LocationDto.from_location(id)
        except Location.DoesNotExist:
            return None

    @staticmethod
    def get_air_pollution_data(location_id: int, start_epoch: int, end_epoch: int, as_objects=True):
        try:
            db_data = AirPollutionMeasure.objects.only('timestamp_epoch', 'co_aqi', 'no2_aqi', 'o3_aqi', 'pm25_aqi',
                                                       'pm10_aqi', 'dominant_pollutant', 'so2_aqi').filter(
                    location_id=location_id, timestamp_epoch__range=(start_epoch, end_epoch)).order_by(
                    'timestamp_epoch')
            return list(db_data) if as_objects else [
                (x.timestamp_epoch, x.co_aqi, x.no2_aqi, x.o3_aqi, x.pm25_aqi, x.pm10_aqi) for x in db_data], [
                       (x.dominant_pollutant) for x in db_data]
        except AirPollutionMeasure.DoesNotExist:
            return []

    @staticmethod
    def get_air_pollution_colors() -> list:
        return AirPollutionMeasure.get_color_list()

    @staticmethod
    def get_air_pollution_pollutants_display() -> list:
        return AirPollutionMeasure.get_pollutants_display()

    @staticmethod
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
        try:
            return list(data) if as_objects else [(x.date_epoch, getattr(x, field)) for x in data], no_year_range
        except HistoricalWeatherObservation.DoesNotExist:
            return [], no_year_range

    @staticmethod
    def get_historical_weather_stats(location_id: int, start_year: int = None, end_year: int = None) -> (list, bool):
        data = HistoricalWeatherObservation.objects.filter(location_id=location_id).values('year').annotate(
                highest_max=Max('max_temp'), lowest_max=Min('max_temp'), highest_min=Max('min_temp'),
                lowest_min=Min('min_temp'), year_avg=Avg('mean_temp'), fog=Count(Case(When(fog=True, then=1))),
                hail=Count(Case(When(hail=True, then=1))), thunder=Count(Case(When(thunder=True, then=1))),
                tornado=Count(Case(When(tornado=True, then=1))), rain=Count(Case(When(rain=True, then=1))),
                snow=Count(Case(When(snow=True, then=1))))
        data, no_year_range = _filter_by_year_range(data, start_year, end_year)
        try:
            return [tuple(x.values()) for x in data.order_by('year')], no_year_range
        except HistoricalWeatherObservation.DoesNotExist:
            return [], no_year_range


class CountryService(AbstractCountryService):

    @staticmethod
    def get_countries_by_keywords(keywords: list, max_results: int) -> (list, bool):
        return _get_entity_by_keywords(Country, keywords, max_results, ['name'], 'name')

    @staticmethod
    def get_single_country(id) -> dto.CountryDto:
        try:
            return dto.CountryDto.from_country_code(id) if isinstance(id, str) else dto.CountryDto.from_country(id)
        except Country.DoesNotExist:
            return None

    @staticmethod
    def get_data_from_indicators(country_id: str, indicators: list, start_year: int = None, end_year: int = None,
                                 null_values: bool = False) -> list:
        data = CountryIndicator.objects.filter(value__isnull=null_values, country_id=country_id,
                                               indicator_id__in=indicators)
        if start_year is not None and end_year is not None:
            data = data.filter(year__range=(start_year, end_year))
        elif start_year is not None:
            data = data.filter(year__gte=start_year)
        elif end_year is not None:
            data = data.filter(year__lte=end_year)
        try:
            return list(data.order_by('indicator', 'year'))
        except CountryIndicator.DoesNotExist:
            return []


class GlobalClimateChangeService(AbstractGlobalClimateChangeService):

    @staticmethod
    def get_sea_level_rise_data() -> list:
        return list(SeaLevelRiseMeasure.objects.values_list('timestamp_epoch',
                                                            'smoothed_variation_GIA_annual_semi_annual_removed',
                                                            'year').order_by('timestamp_epoch'))

    @staticmethod
    def get_ice_extent_data():
        return list(OceanMassMeasure.objects.filter(
                type__in=[OceanMassMeasure.ANTARCTICA, OceanMassMeasure.GREENLAND]).values_list('timestamp_epoch',
                                                                                                'mass', 'year', 'type',
                                                                                                'trend').order_by(
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
    def create_message(subject, email, name, message):
        try:
            ContactMessage.objects.create(email=email, name=name, message=message, subject=subject)
            return True
        except Exception:
            return False

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
            kwargs['last_modified'] = current_timestamp(utc=True)
            ContactMessage.objects.filter(pk=message_id).update(**kwargs)
            return True
        except ContactMessage.DoesNotExist:
            return None
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


def _get_entity_by_keywords(entity: object, keywords: list, max_results: int, search_fields: list, order_by: str) -> (
        list, bool):
    try:
        result = list(entity.objects.filter(get_query(keywords, search_fields)).order_by(order_by)[:(max_results + 1)])
        if len(result) > max_results:
            return result[:-1], True
        else:
            return result, False
    except entity.DoesNotExist:
        return [], False


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
