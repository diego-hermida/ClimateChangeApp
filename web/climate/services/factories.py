from abc import ABC, abstractstaticmethod

from climate.config.config import WEB_CONFIG

from .abstract_services import AbstractCountryService, AbstractGlobalClimateChangeService, AbstractLikeService, \
    AbstractLocationService
from .cache_service_impl import CacheCountryService, CacheGlobalClimateChangeService, CacheLikeService, \
    CacheLocationService
from .service_impl import CountryService, GlobalClimateChangeService, LikeService, LocationService


class Factory(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_instance():
        pass


class LikeServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractLikeService:
        """
            Depending on the value of the USE_CACHE parameter (WEB_CONFIG), the cache service or the normal one
            will be instanced.
            :return: The class of the selected service.
        """
        return CacheLikeService if WEB_CONFIG['USE_CACHE'] else LikeService


class LocationServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractLocationService:
        """
            Depending on the value of the USE_CACHE parameter (WEB_CONFIG), the cache service or the normal one
            will be instanced.
            :return: The class of the selected service.
        """
        return CacheLocationService if WEB_CONFIG['USE_CACHE'] else LocationService


class CountryServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractCountryService:
        """
            Depending on the value of the USE_CACHE parameter (WEB_CONFIG), the cache service or the normal one
            will be instanced.
            :return: The class of the selected service.
        """
        return CacheCountryService if WEB_CONFIG['USE_CACHE'] else CountryService


class GlobalClimateChangeServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractGlobalClimateChangeService:
        """
            Depending on the value of the USE_CACHE parameter (WEB_CONFIG), the cache service or the normal one
            will be instanced.
            :return: The class of the selected service.
        """
        return CacheGlobalClimateChangeService if WEB_CONFIG['USE_CACHE'] else GlobalClimateChangeService
