from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import RpcDatabaseEmission
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from django.db import transaction
from utilities.util import parse_float, parse_int

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _FutureEmissionsDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                   log_to_telegram=log_to_telegram)
    return _singleton


class _FutureEmissionsDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from OceanMassDataCollector) and the RpcDatabaseEmission
            Django model.
        """
        self.data = []
        for value in self.elements_to_convert:
            try:
                year = parse_int(value['year'], nullable=False)
                if value['scenario'] == 'PRE_2005':
                    scenario = RpcDatabaseEmission.PRE_2005
                elif value['scenario'] == 'RPC_2.6':
                    scenario = RpcDatabaseEmission.RPC_26
                elif value['scenario'] == 'RPC_4.5':
                    scenario = RpcDatabaseEmission.RPC_45
                elif value['scenario'] == 'RPC_6.0':
                    scenario = RpcDatabaseEmission.RPC_60
                elif value['scenario'] == 'RPC_8.5':
                    scenario = RpcDatabaseEmission.RPC_85
                else:
                    self.logger.warning('ScenarioType "%s" is unrecognized. Measure with ID: "%s" will not be '
                                        'converted.' % (value['scenario'], value['_id']))
                    continue
                co2 = parse_float(value['measures'][2]['value'], nullable=False)
                self.data.append(RpcDatabaseEmission(year=year, scenario=scenario, co2=co2))
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
            self.state['inserted_elements'] = len(RpcDatabaseEmission.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
