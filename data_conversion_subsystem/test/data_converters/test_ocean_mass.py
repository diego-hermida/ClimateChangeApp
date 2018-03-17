from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.ocean_mass.ocean_mass as ocean_mass


DATA_ANTARCTICA = {"_id": "5a92aba8dd571bdf0ff2108a", "time_utc": 1018988639999, "type": "antarctica",
                   "_execution_id": 1,
                   "measures": [{"mass": "0.00", "units": "Gt"}, {"uncertainty": "164.18", "units": "Gt"}]}
DATA_GREENLAND = {"_id": "5a92aba8dd571bdf0ff2118a", "time_utc": 1018988639999, "type": "greenland", "_execution_id": 1,
                  "measures": [{"mass": "0.00", "units": "Gt"}, {"uncertainty": "164.18", "units": "Gt"}]}
DATA_OCEAN = {"_id": "5a92aba8dd571bdf0ff211c8", "time_utc": 1018988639999, "type": "ocean", "_execution_id": 1,
              "measures": [{"height": "0.00", "units": "mm"}, {"uncertainty": "0.94", "units": "mm"},
                           {"height_deseasoned": "0.00", "units": "mm"}]}

DATA_ANTARCTICA_UNEXPECTED = {"_id": "5a92aba8dd571bdf0ff2108a", "time_utc": 1018988639999, "type": "antarctica",
                              "_execution_id": 1,
                              "measures": [{"mass": "", "units": "Gt"}, {"uncertainty": None, "units": "Gt"}]}


class TestOceanMass(TestCase):

    @classmethod
    def setUpClass(cls):
        ocean_mass.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = ocean_mass.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(ocean_mass.instance(), ocean_mass.instance())
        i1 = ocean_mass.instance()
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, ocean_mass.instance())

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA_ANTARCTICA, DATA_GREENLAND, DATA_OCEAN]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, ocean_mass.OceanMassMeasure)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_ANTARCTICA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    def test_perform_data_conversion_with_unexpected_data_incorrect_type(self):
        self.data_converter.elements_to_convert = [DATA_ANTARCTICA,
                                                   {'_id': 'foo', "time_utc": 1018988639999, 'type': 'baz'}, DATA_OCEAN]
        self.data_converter._perform_data_conversion()
        self.assertEqual(2, len(self.data_converter.data))
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, ocean_mass.OceanMassMeasure)]))

    @mock.patch('data_conversion_subsystem.data_converters.ocean_mass.ocean_mass.OceanMassMeasure.objects.bulk_create',
                Mock(return_value=[1, 2, 3]))
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
