from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'about', views.about, name='about'),
    url(r'contact', views.contact, name='contact'),
    url(r'countries/([A-Z0-9][A-Z0-9])', views.countries__single, name='countries__single'),
    url(r'countries/all', views.countries__all, name='countries__all'),
    url(r'countries/enable-geo', views.countries__geolocation, name='countries__geolocation'),
    url(r'countries/search', views.countries__search, name='countries_search'),
    url(r'countries/energy-consumption-data', views.countries__energy, name='countries__energy_consumption_data'),
    url(r'countries/environment-data', views.countries__environment, name='countries__environment_data'),
    url(r'countries', views.countries, name='countries'),
    url(r'global/future-projections', views.global__future_projections, name='global__future_projections'),
    url(r'global/ice-extent', views.global__ice_extent, name='global__sea_level_rise'),
    url(r'global/sea-level-rise', views.global__sea_level_rise, name='global__sea_level_rise'),
    url(r'global', views.global_change, name='global'),
    url(r'locations/(\d+)', views.locations__single, name='locations__single'),
    url(r'locations/air-pollution-data', views.locations__air_pollution, name='locations__air_pollution'),
    url(r'locations/list-all', views.locations__list, name='locations__list'),
    url(r'locations/all', views.locations__all, name='locations__all'),
    url(r'locations/enable-geo', views.locations__geolocation, name='locations__geolocation'),
    url(r'locations/historical-weather-data', views.locations__historical_weather, name='locations__historical_weather'),
    url(r'locations/search', views.locations__search, name='locations_search'),
    url(r'locations', views.locations, name='locations'),
    url(r'like-count', views.like_count, name='like_count'),
    url(r'admin/login', views.admin_login, name='admin_login'),
    url(r'admin/logout', views.admin_logout, name='admin_logout'),
    url(r'admin/profile', views.admin_profile, name='admin_profile'),
    url(r'admin/messages', views.admin_messages, name='admin_messages'),
    url(r'admin', views.admin, name='admin'),
    url(r'^$', views.index, name='index'),
]
