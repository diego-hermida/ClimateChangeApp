import unidecode
from django.utils.translation import ugettext_lazy as _

from .config.config import WEB_CONFIG
from .services.factories import LikeServiceFactory

like_service = LikeServiceFactory.get_instance()


def base(request):
    """
        Menu links and "Like" counter are passed to every page.
        :param request: Request to be processed
        :return: A 'dict' object, with the links and the "Like" counter.
    """

    def get_historical_weather_max_days() -> int:
        return WEB_CONFIG['HISTORICAL_WEATHER_MAX_YEARS_WITHOUT_SHOWING_BROAD_RANGE_ALERT']

    def get_air_pollution_max_days() -> int:
        return WEB_CONFIG['AIR_POLLUTION_MAX_DAYS_WITHOUT_SHOWING_BROAD_RANGE_ALERT']

    def get_like_count() -> int:
        """
            Passing the "Like" counter as a callable object will only execute this code if the function is called.
            :return: The current number of "Likes" for the app.
        """
        return like_service.get_like_count()

    def get_sections() -> list:
        """
            Passing the sections as a callable object will only execute this code if the function is called.
            :return: A 'list', including all menu links (navbar).
        """
        return [{'url': '/locations', 'name': _('Locations')}, {'url': '/countries', 'name': _('Countries')},
                {'url': '/global', 'name': _('Global')}]

    def get_admin_sections() -> list:
        """
            Passing the sections as a callable object will only execute this code if the function is called.
            :return: A 'list', including all admin menu links (navbar).
        """
        return [{'url': '/admin/profile', 'name': _('Manage profile')},
                {'url': '/admin/messages', 'name': _('Manage messages')}]

    def get_like_given() -> bool:
        return request.session.get('like_given', False)

    def get_preselected_regions() -> list:
        base = '/countries/'
        return sorted([{'name': _('World'), 'url': base + '1W'}, {'name': _('Africa'), 'url': base + 'A9'},
                       {'name': _('European Union'), 'url': base + 'EU'}, {'name': _('Euro area'), 'url': base + 'XC'},
                       {'name': _('Europe & Central Asia'), 'url': base + 'Z7'},
                       {'name': _('North America'), 'url': base + 'XU'},
                       {'name': _('Central America'), 'url': base + 'L6'},
                       {'name': _('Latin America & Caribbean'), 'url': base + 'L4'},
                       {'name': _('Arab World'), 'url': base + '1A'},
                       {'name': _('East Asia & Pacific'), 'url': base + 'Z4'},
                       {'name': _('Middle East & North Africa'), 'url': base + 'ZQ'},
                       {'name': _('South Asia'), 'url': base + '8S'},
                       {'name': _('Sub-Saharan Africa'), 'url': base + 'ZG'}],
                      key=lambda v: unidecode.unidecode(v['name']))

    def get_preselected_income_levels() -> list:
        base = '/countries/'
        return sorted(
                [{'name': _('High income'), 'url': base + 'XD'}, {'name': _('Lower middle income'), 'url': base + 'XN'},
                 {'name': _('Low income'), 'url': base + 'XM'}, {'name': _('Middle income'), 'url': base + 'XP'},
                 {'name': _('Upper middle income'), 'url': base + 'XT'}], key=lambda v: unidecode.unidecode(v['name']))

    return {'admin_sections': get_admin_sections, 'sections': get_sections, 'like_count': get_like_count,
            'like_given': get_like_given, 'country_regions': get_preselected_regions,
            'country_income_levels': get_preselected_income_levels,
            'historical_weather_max_days': get_historical_weather_max_days,
            'air_pollution_max_days': get_air_pollution_max_days}
