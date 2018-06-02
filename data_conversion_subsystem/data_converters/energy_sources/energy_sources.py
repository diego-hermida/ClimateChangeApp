from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import EnergySourcesMeasure, Country
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_date_utc
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _EnergySourcesDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                 log_to_telegram=log_to_telegram)
    return _singleton


class _EnergySourcesDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Country.objects.exists()

    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from EnergySourcesDataCollector) and the Location
            Django model.
        """
        self.data = []
        for value in self.elements_to_convert:
            try:
                country = value['country_id']
                # Setting timezone to pytz.UTC FIXES [BUG-039].
                timestamp = parse_date_utc(value['time_utc'])
                carbon_intensity = parse_float(value['data'].get('carbonIntensity'))
                fossil_fuel = parse_float(value['data'].get('fossilFuelPercentage'))
                self.data.append(EnergySourcesMeasure(country_id=country, timestamp=timestamp,
                        carbon_intensity=carbon_intensity, fossil_fuel=fossil_fuel))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. EnergySourcesMeasure with ID "%s" will not'
                                      ' be converted.' % _id)

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            self.state['inserted_elements'] = len(EnergySourcesMeasure.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
