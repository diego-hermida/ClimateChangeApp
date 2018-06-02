from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.energy_sources.energy_sources as energy_sources


DATA = {"_id": "5a92ac02dd571bdf0ff2456c", "country_id": "AR", "time_utc": 1516896000000,
        "data": {"carbonIntensity": 342.9892587951837, "fossilFuelPercentage": 66.77125906707224},
        "units": {"carbonIntensity": "gCO2eq/kWh"}}

DATA_UNEXPECTED = {"_id": "5a92ac02dd571bdf0ff2456c", "country_id": "AR", "time_utc": None,
                   "data": {"carbonIntensity": 342.9892587951837, "fossilFuelPercentage": 66.77125906707224},
                   "units": {"carbonIntensity": "gCO2eq/kWh"}}


class TestEnergySources(TestCase):

    @classmethod
    def setUpClass(cls):
        energy_sources.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, energy_sources.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_conversion_subsystem.data_converters.energy_sources.energy_sources.Country.objects.exists',
                Mock(return_value=True))
    def test_dependencies_satisfied_ok(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertTrue(self.data_converter.dependencies_satisfied)

    @mock.patch('data_conversion_subsystem.data_converters.energy_sources.energy_sources.Country.objects.exists',
                Mock(return_value=False))
    def test_dependencies_satisfied_missing(self):
        self.data_converter._check_dependencies_satisfied()
        self.assertFalse(self.data_converter.dependencies_satisfied)

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(
            all([x for x in self.data_converter.data if isinstance(x, energy_sources.EnergySourcesMeasure)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.energy_sources.energy_sources.EnergySourcesMeasure.objects.'
                'bulk_create', Mock(return_value=[1, 2, 3]))
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
