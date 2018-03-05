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
                co2_eq = parse_float(value['measures'][0]['value'], nullable=False)
                kyoto_co2_eq = parse_float(value['measures'][1]['value'], nullable=False)
                co2 = parse_float(value['measures'][2]['value'], nullable=False)
                ch4 = parse_float(value['measures'][3]['value'], nullable=False)
                n2o = parse_float(value['measures'][4]['value'], nullable=False)
                kyoto_flourinated_hfc134a_eq = parse_float(value['measures'][5]['value'], nullable=False)
                montreal_flourinated_cfc_13_eq = parse_float(value['measures'][6]['value'], nullable=False)
                cf4 = parse_float(value['measures'][7]['value'], nullable=False)
                c2f6 = parse_float(value['measures'][8]['value'], nullable=False)
                c6f14 = parse_float(value['measures'][9]['value'], nullable=False)
                hfc23 = parse_float(value['measures'][10]['value'], nullable=False)
                hfc32 = parse_float(value['measures'][11]['value'], nullable=False)
                hfc43_10 = parse_float(value['measures'][12]['value'], nullable=False)
                hfc125 = parse_float(value['measures'][13]['value'], nullable=False)
                hfc134a = parse_float(value['measures'][14]['value'], nullable=False)
                hfc143a = parse_float(value['measures'][15]['value'], nullable=False)
                hfc227ea = parse_float(value['measures'][16]['value'], nullable=False)
                hfc245fa = parse_float(value['measures'][17]['value'], nullable=False)
                sf6 = parse_float(value['measures'][18]['value'], nullable=False)
                cfc_11 = parse_float(value['measures'][19]['value'], nullable=False)
                cfc_12 = parse_float(value['measures'][20]['value'], nullable=False)
                cfc_113 = parse_float(value['measures'][21]['value'], nullable=False)
                cfc_114 = parse_float(value['measures'][22]['value'], nullable=False)
                cfc_115 = parse_float(value['measures'][23]['value'], nullable=False)
                carb_tet = parse_float(value['measures'][24]['value'], nullable=False)
                mfc = parse_float(value['measures'][25]['value'], nullable=False)
                hcfc_22 = parse_float(value['measures'][26]['value'], nullable=False)
                hcfc_141b = parse_float(value['measures'][27]['value'], nullable=False)
                hcfc_142b = parse_float(value['measures'][28]['value'], nullable=False)
                halon_1211 = parse_float(value['measures'][29]['value'], nullable=False)
                halon_1202 = parse_float(value['measures'][30]['value'], nullable=False)
                halon_1301 = parse_float(value['measures'][31]['value'], nullable=False)
                halon_2402 = parse_float(value['measures'][32]['value'], nullable=False)
                ch3br = parse_float(value['measures'][33]['value'], nullable=False)
                ch3cl = parse_float(value['measures'][34]['value'], nullable=False)
                self.data.append(RpcDatabaseEmission(year=year, scenario=scenario, co2_eq=co2_eq,
                        kyoto_co2_eq=kyoto_co2_eq, co2=co2, ch4=ch4, n2o=n2o, kyoto_flourinated_hfc134a_eq=
                        kyoto_flourinated_hfc134a_eq, montreal_flourinated_cfc_13_eq=montreal_flourinated_cfc_13_eq,
                        cf4=cf4, c2f6=c2f6, c6f14=c6f14, hfc23=hfc23, hfc32=hfc32, hfc43_10=hfc43_10, hfc125=hfc125,
                        hfc134a=hfc134a, hfc143a=hfc143a, hfc227ea=hfc227ea, hfc245fa=hfc245fa, sf6=sf6, cfc_11=cfc_11,
                        cfc_12=cfc_12, cfc_113=cfc_113, cfc_114=cfc_114, cfc_115=cfc_115, carb_tet=carb_tet, mfc=mfc,
                        hcfc_22=hcfc_22, hcfc_141b=hcfc_141b, hcfc_142b=hcfc_142b, halon_1211=halon_1211, halon_1202=
                        halon_1202, halon_1301=halon_1301, halon_2402=halon_2402, ch3br=ch3br, ch3cl=ch3cl))
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
