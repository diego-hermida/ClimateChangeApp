import datetime

from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import Country, Region, IncomeLevel
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from django.db import transaction
from utilities.util import parse_float

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _CountriesDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                             log_to_telegram=log_to_telegram)
    return _singleton


class _CountriesDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    @transaction.atomic
    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from CountriesDataCollector) and the Country
            Django model.
        """
        self.data = []
        regions = []
        income_levels = []
        if self.state['created_regions']:
            regions = list(Region.objects.all())
        if self.state['created_income_levels']:
            income_levels = list(IncomeLevel.objects.all())
        for value in self.elements_to_convert:
            try:
                iso2_code = value['_id']
                iso3_code = value['iso3']
                name = value.get('name').strip()
                capital_city_name = value.get('capitalCity').strip()
                latitude = parse_float(value.get('latitude'))
                longitude = parse_float(value.get('longitude'))
                region = next((r for r in regions if r.iso3_code == value['region']['id']), default=None)
                income_level = next((r for r in income_levels if r.iso3_code == value['incomeLevel']['id']),
                        default=None)
                if not region:
                    region = Region.objects.create(iso3_code=value['region']['id'], name=value['region']['value'].
                            strip())
                    regions.append(region)
                    self.state['created_regions'] = True
                    self.logger.debug('Created Region object with ID: "%s", and name: "%s".' %
                            (region.iso3_code, region.name))
                if not income_level:
                    income_level = IncomeLevel.objects.create(iso3_code=value['incomeLevel']['id'], name=value[
                            'incomeLevel']['value'].strip())
                    income_levels.append(income_level)
                    self.state['created_income_levels'] = True
                    self.logger.debug('Created IncomeLevel object with ID: "%s", and name: "%s".' %
                            (income_level.iso3_code, income_level.name))
                self.data.append(Country(iso2_code=iso2_code, iso3_code=iso3_code, capital_city_name=capital_city_name,
                        latitude=latitude, longitude=longitude, region=region, income_level=income_level, name=name))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. Country with ID "%s" will not be converted'
                                      '.' % _id)

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            self.state['inserted_elements'] = len(Country.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
