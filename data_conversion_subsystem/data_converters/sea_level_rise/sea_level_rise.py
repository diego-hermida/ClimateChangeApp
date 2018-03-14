import datetime
from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import SeaLevelRiseMeasure
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_int, parse_float
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
                timestamp = datetime.datetime.utcfromtimestamp(parse_int(value['time_utc'], nullable=False) / 1000)
                altimeter = SeaLevelRiseMeasure.DUAL_FREQUENCY if value['altimeter'] == 'dual_frequency' else \
                        SeaLevelRiseMeasure.SINGLE_FREQUENCY
                variation = parse_float(value['measures']['variation'], nullable=False)
                deviation = parse_float(value['measures']['deviation'], nullable=False)
                smoothed_variation = parse_float(value['measures']['smoothed_variation'], nullable=False)
                variation_gia = parse_float(value['measures']['variation_GIA'], nullable=False)
                deviation_gia = parse_float(value['measures']['deviation_GIA'], False)
                smoothed_variation_gia = parse_float(value['measures']['smoothed_variation_GIA'], nullable=False)
                smoothed_variation_gia_annual_semi_annual_removed = parse_float(value['measures'][
                        'smoothed_variation_GIA_annual_&_semi_annual_removed'], nullable=False)
                self.data.append(SeaLevelRiseMeasure(timestamp=timestamp, altimeter=altimeter, variation=variation,
                        deviation=deviation, smoothed_variation=smoothed_variation, variation_GIA=variation_gia,
                        deviation_GIA=deviation_gia, smoothed_variation_GIA=smoothed_variation_gia,
                        smoothed_variation_GIA_annual_semi_annual_removed=smoothed_variation_gia_annual_semi_annual_removed))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. SeaLevelRiseMeasure with ID "%s" will not '
                                    'be converted.' % _id)

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
