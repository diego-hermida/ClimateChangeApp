from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.future_emissions.future_emissions as future_emissions


DATA_2005 = {"_id": "5a92ab9f454cd95abb16ce08", "year": "1765", "scenario": "PRE_2005",
             "measures": [{"measure": "CO2_EQ", "value": "0.27701467E+03", "units": "ppm"},
                          {"measure": "KYOTO_CO2_EQ", "value": "0.27701467E+03", "units": "ppm"},
                          {"measure": "CO2", "value": "0.27805158E+03", "units": "ppm"},
                          {"measure": "CH4", "value": "0.72189411E+03", "units": "ppb"},
                          {"measure": "N2O", "value": "0.27295961E+03", "units": "ppb"},
                          {"measure": "KYOTO_FLOURINATED_HFC134A_EQ", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "MONTREAL_FLOURINATED_CFC-12_EQ", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CF4", "value": "0.35000000E+02", "units": "ppt"},
                          {"measure": "C2F6", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "C6F14", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC23", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC32", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC43_10", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC125", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC134a", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC143a", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC227ea", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HFC245fa", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "SF6", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CFC_11", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CFC_12", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CFC_113", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CFC_114", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CFC_115", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CARB_TET", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "MFC", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HCFC_22", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HCFC_141B", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HCFC_142B", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HALON1211", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HALON1202", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HALON1301", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "HALON2402", "value": "0.00000000E+00", "units": "ppt"},
                          {"measure": "CH3BR", "value": "0.58000000E+01", "units": "ppt"},
                          {"measure": "CH3CL", "value": "0.48000000E+03", "units": "ppt"}], "_execution_id": 1}

DATA_UNEXPECTED = {"_id": "5a92ab9f454cd95abb16ce08", "year": "1765", "scenario": "PRE_2005",
                   "measures": [{"measure": "CO2_EQ", "value": None, "units": "ppm"}]}

DATA_RPC26 = deepcopy(DATA_2005)
DATA_RPC26['scenario'] = 'RPC_2.6'
DATA_RPC45 = deepcopy(DATA_2005)
DATA_RPC45['scenario'] = 'RPC_4.5'
DATA_RPC60 = deepcopy(DATA_2005)
DATA_RPC60['scenario'] = 'RPC_6.0'
DATA_RPC85 = deepcopy(DATA_2005)
DATA_RPC85['scenario'] = 'RPC_8.5'


class TestFutureEmissions(TestCase):

    @classmethod
    def setUpClass(cls):
        future_emissions.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = future_emissions.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(future_emissions.instance(), future_emissions.instance())
        i1 = future_emissions.instance()
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, future_emissions.instance())

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA_2005, DATA_RPC26, DATA_RPC45, DATA_RPC60, DATA_RPC85]
        self.data_converter._perform_data_conversion()
        self.assertEqual(5, len(self.data_converter.data))
        self.assertTrue(
                all([x for x in self.data_converter.data if isinstance(x, future_emissions.RpcDatabaseEmission)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    def test_perform_data_conversion_with_unexpected_data_incorrect_scenario(self):
        self.data_converter.elements_to_convert = [DATA_2005, {'_id': 'foo', "year": "2053", 'scenario': 'baz'},
                                                   DATA_RPC45]
        self.data_converter._perform_data_conversion()
        self.assertEqual(2, len(self.data_converter.data))
        self.assertTrue(
                all([x for x in self.data_converter.data if isinstance(x, future_emissions.RpcDatabaseEmission)]))

    @mock.patch('data_conversion_subsystem.data_converters.future_emissions.future_emissions.RpcDatabaseEmission.'
            'objects.bulk_create', Mock(return_value=[1, 2, 3]))
    def test_save_data(self):
        self.data_converter.data = [1, 2, 3]
        self.data_converter._save_data()
        self.assertEqual(3, self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)

    def test_save_data_with_no_data(self):
        self.data_converter.data = None
        self.data_converter._save_data()
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertIsNone(self.data_converter.data)
