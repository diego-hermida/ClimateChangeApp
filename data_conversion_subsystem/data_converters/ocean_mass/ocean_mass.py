from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import OceanMassMeasure
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_date_utc
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _OceanMassDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                             log_to_telegram=log_to_telegram)
    return _singleton


class _OceanMassDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from OceanMassDataCollector) and the OceanMassMeasure
            Django model.
        """
        self.data = []
        for value in self.elements_to_convert:
            try:
                timestamp_epoch = value['time_utc']
                year = parse_date_utc(timestamp_epoch).year
                if value['type'] == 'antarctica':
                    type = OceanMassMeasure.ANTARCTICA
                elif value['type'] == 'greenland':
                    type = OceanMassMeasure.GREENLAND
                else:
                    self.logger.warning('OceanMassMeasureType "%s" is unrecognized. Measure with ID: "%s" will not be '
                            'converted.' % (value['type'], value['_id']))
                    continue
                mass = parse_float(value['measures'][0]['mass'], nullable=False)
                uncertainty = parse_float(value['measures'][1]['uncertainty'], nullable=False)
                trend = parse_float(value['measures'][2]['trend'], nullable=True)
                self.data.append(OceanMassMeasure(timestamp_epoch=timestamp_epoch, year=year, type=type, mass=mass,
                        uncertainty=uncertainty, trend=trend))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. OceanMassMeasure with ID "%s" will not be '
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
            self.state['inserted_elements'] = len(OceanMassMeasure.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
