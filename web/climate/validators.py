from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from utilities.postgres_util import normalize_query
from utilities.util import nonempty_str, parse_float, parse_int
from .config.config import WEB_CONFIG
from .services.services import MessageActionType, MessageFilterType, TemperatureType


class ValidationError(ValueError):

    def __init__(self, invalid_data):
        super(ValidationError, self).__init__('A validation error occurred')
        self.invalid_data = invalid_data


def validate_coordinates(request):
    invalid_data = []
    try:
        latitude = parse_float(request.POST.get('latitude'), nullable=False)
    except ValueError:
        invalid_data.append(request.POST.get('latitude'))
    try:
        longitude = parse_float(request.POST.get('longitude'), nullable=False)
    except ValueError:
        invalid_data.append(request.POST.get('longitude'))
    if len(invalid_data) == 0:
        return latitude, longitude
    else:
        raise ValidationError(invalid_data)


def validate_keywords_search(request, field_name):
    try:
        keywords = normalize_query(nonempty_str(request.POST.get(field_name), nullable=False))
        if not keywords:
            raise ValueError('Keywords are invalid')
        else:
            return keywords
    except ValueError as e:
        raise ValidationError(request.POST.get(field_name)) from e


def validate_integer(value, positive_only=False):
    try:
        result = parse_int(value, nullable=False)
        if positive_only and result < 0:
            raise ValueError('Value must be a positive integer')
        else:
            return result
    except ValueError as e:
        raise ValidationError(value) from e


def validate_country_code(country_code):
    try:
        country_code = nonempty_str(country_code, nullable=False, min_length=2, max_length=2).upper()
        if not country_code.isalnum():
            raise ValueError('Value must be alphanumeric')
        else:
            return country_code
    except ValueError as e:
        raise ValidationError(country_code) from e


def validate_air_pollution_parameters(request):
    try:
        location_id = parse_int(request.POST.get('location_id'), nullable=False)
    except ValueError as e:
        raise ValidationError(invalid_data=['location_id']) from e
    start_date, end_date = validate_integer_range(request, 'start_date', 'end_date', nullable=False, positive_only=True)
    plot_values = request.POST.get('plot_values', 'false').lower() in ['on', 'true', '1', 'ok']
    return location_id, start_date, end_date, plot_values


def validate_historical_weather_parameters(request):
    try:
        location_id = parse_int(request.POST.get('location_id'), nullable=False)
    except ValueError as e:
        raise ValidationError(invalid_data=['location_id']) from e
    try:
        phenomenon = TemperatureType.from_representation(nonempty_str(request.POST.get('phenomenon'), nullable=False))
        if not phenomenon:
            raise ValueError('Value is not a valid option')
    except ValueError as e:
        raise ValidationError(invalid_data=['phenomenon']) from e
    start_year, end_year = validate_integer_range(request, 'start_year', 'end_year', nullable=True, positive_only=True)
    plot_values = request.POST.get('plot_values', 'false').lower() in ['on', 'true', '1', 'ok']
    if start_year is None and end_year is None:
        plot_values = False
    return location_id, start_year, end_year, phenomenon, plot_values


def validate_integer_range(request, start_year_name: str, end_year_name: str, nullable=True, positive_only=False,
                           strict_comparison=False):
    try:
        start_year = parse_int(request.POST.get(start_year_name), nullable=nullable)
        if start_year is not None and positive_only and start_year < 0:
            raise ValueError('Value must be a positive integer')
    except ValueError as e:
        raise ValidationError(invalid_data=[start_year_name]) from e
    try:
        end_year = parse_int(request.POST.get(end_year_name), nullable=nullable)
        if end_year is not None and positive_only and end_year < 0:
            raise ValueError('Value must be a positive integer')
    except ValueError as e:
        raise ValidationError(invalid_data=[end_year_name]) from e
    if start_year is not None and end_year is not None and (
            start_year >= end_year if strict_comparison else start_year > end_year):
        raise ValidationError(invalid_data=[start_year_name, end_year_name])
    return start_year, end_year


def validate_credentials(request):
    invalid_fields = []
    try:
        username = nonempty_str(request.POST.get('user'), nullable=False)
    except ValueError:
        invalid_fields.append('user')
    try:
        password = nonempty_str(request.POST.get('password'), nullable=False)
    except ValueError:
        invalid_fields.append('password')
    if len(invalid_fields) == 0:
        return username, password
    else:
        raise ValidationError(invalid_fields)


def validate_contact_fields(request) -> (str, str, str, str):
    invalid_fields = []
    try:
        subject = nonempty_str(request.POST.get('subject'), min_length=WEB_CONFIG['MIN_SUBJECT_LENGTH'],
                               max_length=WEB_CONFIG['MAX_SUBJECT_LENGTH'], nullable=False)
    except ValueError:
        invalid_fields.append('subject')
    try:
        email = nonempty_str(request.POST.get('email'), min_length=WEB_CONFIG['MIN_EMAIL_LENGTH'],
                             max_length=WEB_CONFIG['MAX_EMAIL_LENGTH'], nullable=False)
        validate_email(email)
    except (ValueError, DjangoValidationError):
        invalid_fields.append('email')
    try:
        name = nonempty_str(request.POST.get('name'), min_length=WEB_CONFIG['MIN_NAME_LENGTH'],
                            max_length=WEB_CONFIG['MAX_NAME_LENGTH'], nullable=False)
    except ValueError:
        invalid_fields.append('name')
    try:
        message = nonempty_str(request.POST.get('message'), min_length=WEB_CONFIG['MIN_MESSAGE_LENGTH'],
                               max_length=WEB_CONFIG['MAX_MESSAGE_LENGTH'], nullable=False)
    except ValueError:
        invalid_fields.append('message')
    if len(invalid_fields) != 0:
        raise ValidationError(invalid_data=invalid_fields)
    else:
        return subject, email, name, message


def validate_message_parameters(request):
    message_filter = request.GET.get('filter', 'inbox')
    if message_filter not in WEB_CONFIG['MESSAGE_FILTERS']:
        message_filter = 'inbox'  # Falling back to default filter
    action = nonempty_str(request.GET.get('action'), nullable=True)
    if action is not None:
        action = MessageActionType.from_representation(action)
    try:
        page = parse_int(request.GET.get('page'), nullable=False)
    except ValueError:
        page = 1
    message_filter = MessageFilterType.from_representation(message_filter)
    return message_filter, action, page
