from functools import wraps

import climate.validators as validators
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from utilities.util import current_timestamp
from . import dto
from .config.config import WEB_CONFIG
from .services.factories import CountryServiceFactory, GlobalClimateChangeServiceFactory, LikeServiceFactory, \
    LocationServiceFactory
from .services.services import AdminService, MessageActionType, MessageFilterType, MessageService

# Getting services from factories, in order to decouple cached services from the business logic
like_service = LikeServiceFactory.get_instance()
location_service = LocationServiceFactory.get_instance()
country_service = CountryServiceFactory.get_instance()
global_climate_change_service = GlobalClimateChangeServiceFactory.get_instance()

from django.utils.translation import ugettext_lazy as _


def require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        request = args[0]
        if not request.user or not request.user.is_authenticated:
            return redirect('/admin/login')
        else:
            return f(*args, **kwargs)

    return wrapped


def require_nonauth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        request = args[0]
        if not request.user or not request.user.is_authenticated:
            return f(*args, **kwargs)
        else:
            return redirect('/admin')

    return wrapped


@require_GET
def index(request):
    return render(request, 'climate/index.html', request.session.pop('logout', {}))


@require_POST
def like_count(request):
    success = like_service.increase_like_counter()
    if success:
        request.session['like_given'] = True
        request.session.modified = True
    return JsonResponse(data={'success': success})


def _retrieve_nearest_location(request) -> dict:
    context = {'from_geo': True}
    latitude, longitude = validators.validate_coordinates(request)
    geo = {'latitude': latitude, 'longitude': longitude}
    loc = location_service.get_nearest_location_from_coordinates(latitude, longitude)
    if not loc:
        context['location_error'] = True
    else:
        geo['nearest_location_id'] = loc.id
        geo['nearest_country_id'] = loc.country_id
        request.session['geolocation'] = geo
        context['geolocation'] = geo
        request.session.modified = True
    return context


@require_GET
def locations(request):
    context = {'geolocation': request.session.get('geolocation'),
               'no_matching_location': request.session.pop('no_matching_location', False)}
    if context.get('geolocation', False) and context['geolocation'].get('nearest_location_id', False):
        context['current_location'] = location_service.get_single_location(
                context['geolocation']['nearest_location_id'])
    else:
        locs = location_service.get_all_locations(('id', 'latitude', 'longitude', 'name', 'country_id'), tuple(),
                                                  as_objects=False)
        for loc in locs:
            loc['name'] = _(loc['name'])
        context['map_locations'] = locs
    return render(request, 'climate/locations.html', context)


@require_POST
def locations__search(request):
    context = {'from_search': True, 'geolocation': request.session.get('geolocation')}
    try:
        keywords = validators.validate_keywords_search(request, 'loc')
        result, more_results = location_service.get_locations_by_keywords(keywords, WEB_CONFIG['MAX_SEARCH_RESULTS'])
        context['results'] = len(result)
        if context['results'] == 1:
            context['current_location'] = location_service.get_single_location(result[0])
            context['AQI_colors'] = location_service.get_air_pollution_colors()
        else:
            context['locations'] = [{'name': _(x.name), 'id': x.id, 'latitude': x.latitude, 'longitude': x.longitude,
                                     'country_id': x.country_id} for x in result]
            context['more_results'] = more_results
            context['map_locations'] = context['locations']
    except validators.ValidationError as e:
        context['validation_error'] = True
        context['invalid_data'] = e.invalid_data
        locs = location_service.get_all_locations(('id', 'latitude', 'longitude', 'name', 'country_id'), tuple(),
                                                  as_objects=False)
        for loc in locs:
            loc['name'] = _(loc['name'])
        context['map_locations'] = locs
    return render(request, 'climate/locations.html', context)


@require_POST
def locations__geolocation(request):
    try:
        context = _retrieve_nearest_location(request)
        context['current_location'] = location_service.get_single_location(
                context['geolocation']['nearest_location_id'])
        context['AQI_colors'] = location_service.get_air_pollution_colors() if context['current_location'] else None
    except validators.ValidationError as e:
        return render(request, 'climate/locations.html', {'validation_error': True, 'invalid_data': e.invalid_data})
    return render(request, 'climate/locations.html', context)


@require_GET
def locations__all(request):
    context = {'from_all': True, 'map_locations': location_service.get_all_locations(
            ('id', 'latitude', 'longitude', 'name', 'country_id'), tuple(), as_objects=False),
               'geolocation': request.session.get('geolocation')}
    return render(request, 'climate/locations.html', context)


@require_GET
def locations__single(request, location_id: int):
    context = {'geolocation': request.session.get('geolocation')}
    try:
        location_id = validators.validate_integer(location_id)
    except validators.ValidationError as e:
        context['validation_error'] = True
        context['invalid_data'] = e.invalid_data
        request.session['no_matching_location'] = True
        return redirect('/locations')
    loc = location_service.get_single_location(location_id)
    if loc is None:
        request.session['no_matching_location'] = True
        return redirect('/locations')
    else:
        context['current_location'] = loc
        context['AQI_colors'] = location_service.get_air_pollution_colors()
    return render(request, 'climate/locations.html', context)


@require_POST
def locations__air_pollution(request):
    try:
        location_id, start_date, end_date, plot_values = validators.validate_air_pollution_parameters(request)
        data, dominant_pollutant_data = location_service.get_air_pollution_data(location_id, start_date, end_date,
                                                                                as_objects=False)
        total_dominant_pollutant, dominant_pollutant_data = dto.AirPollutionDto.get_pollutant_statistics(
                dominant_pollutant_data)
        stats = dto.AirPollutionDto.get_statistics(data)
        return JsonResponse(
                data={'columns': location_service.get_air_pollution_pollutants_display(), 'plot_values': plot_values,
                      'data': data if plot_values else None, 'stats': stats, 'total_data': len(data),
                      'start': data[0][0] if data else None, 'end': data[-1][0] if data else None,
                      'dom': dominant_pollutant_data, 'total_dom': total_dominant_pollutant})
    except validators.ValidationError as e:
        return JsonResponse(data={'validation_error': True, 'invalid_data': e.invalid_data})


@require_POST
def locations__historical_weather(request):
    try:
        location_id, start_year, end_year, field, plot_values = validators.validate_historical_weather_parameters(
                request)
        if plot_values:
            data, no_year_range = location_service.get_historical_weather_data(location_id, field, start_year, end_year,
                                                                               as_objects=False)
            total_data, start, end, start_year, end_year, data = dto.HistoricalWeatherDto.normalize_data(data)
            year_stats = location_service.get_historical_weather_stats(location_id, start_year, end_year)[
                0] if total_data else []
        else:
            total_data, start, end, data = 0, None, None, []
            year_stats, no_year_range = location_service.get_historical_weather_stats(location_id, start_year, end_year)
        years = [x[0] for x in year_stats]
        start_year = min(years) if start_year is None and years else start_year
        end_year = max(years) if end_year is None and years else end_year
        return JsonResponse(data={'plot_values': plot_values, 'data': data if plot_values and data else None,
                                  'total_data': total_data, 'start': start, 'end': end, 'start_year': start_year,
                                  'end_year': end_year, 'stats': year_stats if year_stats else None,
                                  'no_year_range': no_year_range})
    except validators.ValidationError as e:
        return JsonResponse(data={'validation_error': True, 'invalid_data': e.invalid_data})


@require_GET
def locations__list(request):
    locs = location_service.get_all_locations(('id', 'latitude', 'longitude', 'name', 'country_id'), tuple(),
                                              as_objects=False)
    for loc in locs:
        loc['name'] = _(loc['name'])
    return render(request, 'climate/locations_list.html', {'locations': locs, 'total': len(locs)})


@require_GET
def countries(request):
    context = {'geolocation': request.session.get('geolocation')}
    if context.get('geolocation', False) and context['geolocation'].get('nearest_country_id', False):
        context['current_country'] = country_service.get_single_country(context['geolocation']['nearest_country_id'])
        context['last_updated'] = current_timestamp(utc=False)
    return render(request, 'climate/countries.html', context)


@require_GET
def countries__all(request):
    context = {'from_all': True, 'geolocation': request.session.get('geolocation')}
    return render(request, 'climate/countries.html', context)


@require_POST
def countries__search(request):
    context = {'from_search': True, 'geolocation': request.session.get('geolocation')}
    try:
        keywords = validators.validate_keywords_search(request, 'country')
        result, more_results = country_service.get_countries_by_keywords(keywords, WEB_CONFIG['MAX_SEARCH_RESULTS'])
        context['results'] = len(result)
        if context['results'] == 1:
            context['current_country'] = country_service.get_single_country(result[0])
        else:
            context['countries'] = [{'name': _(x.name), 'id': x.iso2_code} for x in result]
            context['more_results'] = more_results
    except validators.ValidationError as e:
        context['validation_error'] = True
        context['invalid_data'] = e.invalid_data
    return render(request, 'climate/countries.html', context)


@require_GET
def countries__single(request, country_code: str):
    try:
        country_code = validators.validate_country_code(country_code)
        context = {'geolocation': request.session.get('geolocation'), 'last_updated': current_timestamp(utc=False),
                   'current_country': country_service.get_single_country(country_code)}
        context['no_matching_country'] = context['current_country'] is None
    except validators.ValidationError as e:
        context = {'validation_error': True, 'invalid_data': e.invalid_data}
    return render(request, 'climate/countries.html', context)


@require_POST
def countries__geolocation(request):
    try:
        context = _retrieve_nearest_location(request)
        context['current_country'] = country_service.get_single_country(context['geolocation']['nearest_country_id'])
        context['no_matching_country'] = context['current_country'] is None
    except validators.ValidationError as e:
        return render(request, 'climate/countries.html', {'validation_error': True, 'invalid_data': e.invalid_data})
    return render(request, 'climate/countries.html', context)


@require_POST
def countries__energy(request):
    try:
        country_id = validators.validate_country_code(request.POST.get('country_id'))
        start_year, end_year = validators.validate_integer_range(request, 'start_year', 'end_year', nullable=True,
                                                                 positive_only=True, strict_comparison=True)
        data = country_service.get_data_from_indicators(country_id, WEB_CONFIG['ENERGY_INDICATORS'], start_year,
                                                        end_year)
        co2_index = next((i for i, x in enumerate(data) if x.indicator_id == 'EN.ATM.CO2E.KT'), 0)
        data_pollution = dto.CountryIndicatorDto.get_pollution_statistics_and_normalize_data(data[co2_index:])
        data_energy = dto.CountryIndicatorDto.get_energy_statistics_and_normalize_data(data[:co2_index],
                                                                                       WEB_CONFIG['ENERGY_INDICATORS'][
                                                                                       :-1])
        return JsonResponse(data={'pollution': data_pollution, 'energy': data_energy})
    except validators.ValidationError as e:
        return JsonResponse(data={'validation_error': True, 'invalid_data': e.invalid_data})


@require_POST
def countries__environment(request):
    try:
        country_id = validators.validate_country_code(request.POST.get('country_id'))
        start_year, end_year = validators.validate_integer_range(request, 'start_year', 'end_year', nullable=True,
                                                                 positive_only=True)
        data = country_service.get_data_from_indicators(country_id, WEB_CONFIG['ENVIRONMENT_INDICATORS'], start_year,
                                                        end_year)
        environment_data = dto.CountryIndicatorDto.get_environment_statistics_and_normalize_data(data, WEB_CONFIG[
            'ENVIRONMENT_INDICATORS'], ['urban_land', 'forest_area', 'protected_areas', 'improved_water'])
        return JsonResponse(data=environment_data)
    except validators.ValidationError as e:
        return JsonResponse(data={'validation_error': True, 'invalid_data': e.invalid_data})


@require_GET
def global_change(request):
    return render(request, 'climate/global_change.html')


@require_POST
def global__sea_level_rise(_request):
    data = global_climate_change_service.get_sea_level_rise_data()
    total_data = len(data)
    start = data[0][0] if total_data else None
    end = data[-1][0] if total_data else None
    last = data[-1][1] if total_data else None
    last_year, mean = dto.SeaLevelRiseDto.get_last_year_stats(data)
    return JsonResponse(
            data={'data': [(x[0], x[1]) for x in data], 'total_data': total_data, 'last': last, 'start': start,
                  'end': end, 'last_year': last_year, 'last_year_mean': mean})


@require_POST
def global__ice_extent(_request):
    data = global_climate_change_service.get_ice_extent_data()
    arctic_data, antarctica_data = dto.OceanMassMeasureDto.normalize_data(data)
    arctic_total = len(arctic_data)
    arctic_start = arctic_data[0][0] if arctic_total else None
    arctic_end = arctic_data[-1][0] if arctic_total else None
    arctic_last = arctic_data[-1][1] if arctic_total else None
    arctic_trend = arctic_data[-1][4] if arctic_total else None
    antarctica_total = len(antarctica_data)
    antarctica_start = antarctica_data[0][0] if arctic_total else None
    antarctica_end = antarctica_data[-1][0] if arctic_total else None
    antarctica_last = antarctica_data[-1][1] if arctic_total else None
    antarctica_trend = antarctica_data[-1][4] if arctic_total else None
    return JsonResponse(data={
        'arctic': {'data': [(x[0], x[1]) for x in arctic_data], 'total_data': arctic_total, 'last': arctic_last,
                   'start': arctic_start, 'end': arctic_end, 'trend': arctic_trend},
        'antarctica': {'data': [(x[0], x[1]) for x in antarctica_data], 'total_data': antarctica_total,
                       'last': antarctica_last, 'start': antarctica_start, 'end': antarctica_end,
                       'trend': antarctica_trend}})


@require_POST
def global__future_projections(_request):
    return JsonResponse(
            data=dto.RpcDatabaseEmissionDto.normalize_data(global_climate_change_service.get_future_emissions_data()))


@require_GET
def about(request):
    return render(request, 'climate/about.html')


@require_http_methods(['GET', 'POST'])
def contact(request):
    if request.method == 'POST':
        try:
            subject, email, name, message = validators.validate_contact_fields(request)
            return JsonResponse(data={'success': MessageService.create_message(subject, email, name, message)})
        except validators.ValidationError as e:
            return JsonResponse({'validation_error': True, 'invalid_data': e.invalid_data})
    else:
        return render(request, 'climate/contact.html', {
            'lengths': {'min_name': WEB_CONFIG['MIN_NAME_LENGTH'], 'min_email': WEB_CONFIG['MIN_EMAIL_LENGTH'],
                        'min_message': WEB_CONFIG['MIN_MESSAGE_LENGTH'],
                        'min_subject': WEB_CONFIG['MIN_SUBJECT_LENGTH'], 'max_name': WEB_CONFIG['MAX_NAME_LENGTH'],
                        'max_email': WEB_CONFIG['MAX_EMAIL_LENGTH'], 'max_message': WEB_CONFIG['MAX_MESSAGE_LENGTH'],
                        'max_subject': WEB_CONFIG['MAX_SUBJECT_LENGTH']}})


@require_nonauth
@require_http_methods(['GET', 'POST'])
def admin_login(request):
    if request.method == 'POST':
        try:
            username, password = validators.validate_credentials(request)
            context = {'success': AdminService.login(username, password, request), 'invalid_fields': None}
            context['url'] = '/admin' if context['success'] else None
        except validators.ValidationError as e:
            context = {'validation_error': True, 'invalid_fields': e.invalid_data}
        return JsonResponse(data=context)
    else:
        return render(request, 'climate/admin_login.html')


@require_auth
@require_GET
def admin_logout(request):
    request.session['logout'] = {'from_logout': True, 'success': AdminService.logout(request)}
    return redirect('/')


@require_auth
@require_GET
def admin(request):
    return render(request, 'climate/admin.html')


@require_auth
@require_GET
def admin_profile(request):
    return render(request, 'climate/profile.html')


@require_auth
@require_GET
def admin_messages(request):
    message_filter, action, page = validators.validate_message_parameters(request)
    if action:
        try:
            message_id = validators.validate_integer(request.GET.get('msgid'), positive_only=True)
            request.session['message_id'] = message_id
            if action == MessageActionType.DELETE:
                request.session['from_delete'] = True
            result = MessageService.update_or_delete(message_id, action)
            if result is None:
                request.session['message_does_not_exist'] = True
            else:
                request.session['error'] = not result
            return redirect('/admin/messages?filter=%s' % MessageActionType.get_filter_name(action,
                                                                                            current_filter_name=MessageFilterType.get_representation(
                                                                                                    message_filter)))
        except validators.ValidationError:
            return redirect('/admin/messages')
    else:
        unread_messages = MessageService.count_unread_messages()
        messages, total_pages = MessageService.filter_messages(message_filter, page)
        message_filter = MessageFilterType.get_representation(message_filter)
        context = {'msgs': messages, 'new_msgs': unread_messages, 'filter': message_filter, 'page': page,
                   'total_pages': total_pages, 'from_delete': request.session.pop('from_delete', False),
                   'error': request.session.pop('error', False), 'message_id': request.session.pop('message_id', None),
                   'message_does_not_exist': request.session.pop('message_does_not_exist', False)}
        return render(request, 'climate/messages.html', context)
