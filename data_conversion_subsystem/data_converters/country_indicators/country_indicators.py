import yaml

from data_conversion_subsystem.config.config import DCS_CONFIG
from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import CountryIndicator, IndicatorDetails, Country
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from django.db import transaction
from utilities.util import parse_float, parse_int

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _CountryIndicatorsDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                     log_to_telegram=log_to_telegram)
    return _singleton


class _CountryIndicatorsDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Country.objects.exists()

    @transaction.atomic
    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from CountryIndicatorsDataCollector) and the Country
            Django model.
        """
        self.data = []
        if not self.state['created_indicators']:
            with open(DCS_CONFIG['ROOT_DATA_CONVERSION_SUBSYSTEM_FOLDER'] + self.config['RESOURCE_FILEPATH'], 'r') as f:
                indicators_data = yaml.load(f)
            indicators = []
            for i in indicators_data['INDICATOR_DETAILS']:
                try:
                    code = i
                    name = indicators_data['INDICATOR_DETAILS'][i]['name']
                    description = indicators_data['INDICATOR_DETAILS'][i]['sourceNote']
                    units = indicators_data['INDICATOR_DETAILS'][i]['units']
                    type = indicators_data['INDICATOR_DETAILS'][i]['type']
                    attributions = indicators_data['INDICATOR_DETAILS'][i]['sourceOrganization']
                    indicators.append(IndicatorDetails(code=code, name=name, description=description, units=units,
                            type=type, attributions=attributions))
                except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                    _id = indicators_data['INDICATOR_DETAILS'][i].get('name', 'Unknown name')
                    self.logger.exception('An error occurred while parsing data. IndicatorDetails "%s" will not be '
                            'created. Therefore, Indicators with such IndicatorDetails would not be created, either. '
                            'Data conversion will stop now.' % _id)
                    self.advisedly_no_data_converted = True
                    return
            indicators_count = len(IndicatorDetails.objects.bulk_create(indicators))
            self.state['created_indicators'] = True
            self.logger.info('Successfully created %d IndicatorDetails.' % indicators_count)
        for value in self.elements_to_convert:
            try:
                indicator = value['indicator']
                country = value['country_id']
                # Excluding empty country IDs FIXES [BUG-036].
                if country is None or country == '':
                    raise ValueError('Country ID is not present. Inserting this indicator would violate a foreign key '
                                     'restriction.')
                year = parse_int(value['year'], nullable=False)
                value = parse_float(value['value'])
                self.data.append(CountryIndicator(indicator_id=indicator, country_id=country, year=year, value=value))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. CountryIndicator with ID "%s" will not be '
                        'converted.' % _id)

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            self.state['inserted_elements'] = len(CountryIndicator.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
