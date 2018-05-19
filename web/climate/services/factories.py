from abc import ABC, abstractstaticmethod

from climate.config.config import WEB_CONFIG

from .abstract_services import AbstractCountryService, AbstractGlobalClimateChangeService, AbstractLikeService, \
    AbstractLocationService
from .cache_services import CacheCountryService, CacheGlobalClimateChangeService, CacheLikeService, CacheLocationService
from .services import CountryService, GlobalClimateChangeService, LikeService, LocationService


class Factory(ABC):

    @staticmethod
    @abstractstaticmethod
    def get_instance():
        pass


class LikeServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractLikeService:
        return CacheLikeService if WEB_CONFIG['USE_CACHE'] else LikeService


class LocationServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractLocationService:
        return CacheLocationService if WEB_CONFIG['USE_CACHE'] else LocationService


class CountryServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractCountryService:
        return CacheCountryService if WEB_CONFIG['USE_CACHE'] else CountryService


class GlobalClimateChangeServiceFactory(Factory):

    @staticmethod
    def get_instance() -> AbstractGlobalClimateChangeService:
        return CacheGlobalClimateChangeService if WEB_CONFIG['USE_CACHE'] else GlobalClimateChangeService
