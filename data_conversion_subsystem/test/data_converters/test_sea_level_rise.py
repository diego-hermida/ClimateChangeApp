from copy import deepcopy
from unittest import TestCase, mock
from unittest.mock import Mock

# This is necessary to patch the @transaction.atomic decorator
mock.patch('django.db.transaction.atomic', lambda x: x).start()

import data_conversion_subsystem.data_converters.sea_level_rise.sea_level_rise as sea_level_rise


DATA = {"_id": "5a92aba6dd571bdf0ff20cee", "time_utc": 726209883936, "_execution_id": 1,
        "altimeter": "single_frequency",
        "measures": {"variation": "-37.24", "deviation": "92.66", "smoothed_variation": "-37.02",
                     "variation_GIA": "-37.24", "deviation_GIA": "92.66", "smoothed_variation_GIA": "-37.02",
                     "smoothed_variation_GIA_annual_&_semi_annual_removed": "-37.52"}, "observations": "466462",
        "units": "mm", "weighted_observations": "337277.00"}

DATA_UNEXPECTED = {"_id": "5a92aba6dd571bdf0ff20cee", "time_utc": 726209883936, "_execution_id": 1,
                   "altimeter": "dual_frequency",
                   "measures": {"variation": "", "deviation": "", "smoothed_variation": "-37.02",
                                "variation_GIA": "-37.24", "deviation_GIA": "92.66", "smoothed_variation_GIA": "-37.02",
                                "smoothed_variation_GIA_annual_&_semi_annual_removed": None},
                   "observations": "466462", "units": "mm", "weighted_observations": "337277.00"}


class TestSeaLevelRise(TestCase):

    @classmethod
    def setUpClass(cls):
        sea_level_rise.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def setUp(self):
        self.data_converter = sea_level_rise.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        self.data_converter.state = deepcopy(self.data_converter.config['STATE_STRUCT'])

    def tearDown(self):
        if hasattr(self, 'data_converter'):
            self.data_converter.remove_files()

    def test_instance(self):
        self.assertIs(sea_level_rise.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      sea_level_rise.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = sea_level_rise.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, sea_level_rise.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    def test_perform_data_conversion_with_all_values_set(self):
        self.data_converter.elements_to_convert = [DATA, DATA, DATA]
        self.data_converter._perform_data_conversion()
        self.assertEqual(3, len(self.data_converter.data))
        self.assertTrue(all([x for x in self.data_converter.data if isinstance(x, sea_level_rise.SeaLevelRiseMeasure)]))

    def test_perform_data_conversion_with_unexpected_data(self):
        self.data_converter.elements_to_convert = [DATA_UNEXPECTED]
        self.data_converter._perform_data_conversion()
        self.assertListEqual([], self.data_converter.data)

    @mock.patch('data_conversion_subsystem.data_converters.sea_level_rise.sea_level_rise.SeaLevelRiseMeasure.objects.'
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
