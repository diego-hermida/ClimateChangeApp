from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import SeaLevelRiseMeasure
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_date_utc
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _SeaLevelRiseDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                log_to_telegram=log_to_telegram)
    return _singleton


class _SeaLevelRiseDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from SeaLevelRiseDataCollector) and the SeaLevelRiseMeasure
            Django model.
        """
        self.data = []
        for value in self.elements_to_convert:
            try:
                timestamp_epoch = value['time_utc']
                year = parse_date_utc(timestamp_epoch).year
                value = parse_float(value['measures'][
                        'smoothed_variation_GIA_annual_&_semi_annual_removed'], nullable=False)
                self.data.append(SeaLevelRiseMeasure(timestamp_epoch=timestamp_epoch, year=year, value=value))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. SeaLevelRiseMeasure with ID "%s" will not '
                                    'be converted.' % _id)
        if self.data:
            # Ensuring that all values are greater than or equal to 0
            min_value = abs(self.data[0].value)
            for value in self.data:
                value.value += min_value

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            self.state['inserted_elements'] = len(SeaLevelRiseMeasure.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
