import datetime
from copy import deepcopy
from os import environ
from unittest import TestCase, mock
from unittest.mock import Mock

from pytz import UTC
from requests import Timeout

import data_conversion_subsystem.data_converter.data_converter as data_converter
from data_conversion_subsystem.config.config import DCS_CONFIG
from data_conversion_subsystem.data_converter.data_converter import ABORTED, CONFIG, CREATED, DATA_CONVERTED, \
    DATA_SAVED, EXECUTION_CHECKED, FINISHED, INITIALIZED, PENDING_WORK_CHECKED, STATE_RESTORED, STATE_SAVED
from data_conversion_subsystem.supervisor.supervisor import DataConverterSupervisor

ENVIRON = deepcopy(environ)
ENVIRON['API_IP'] = 'test_ip'
ENVIRON['POSTGRES_IP'] = 'test_ip'
PAGE_SIZE = 100
MIN_UPDATE_FREQUENCY = {'value': 30, 'units': 'min'}
MAX_UPDATE_FREQUENCY = {'value': 1, 'units': 'day'}
DEPENDENCIES_UNSATISFIED_UPDATE_FREQUENCY = {'value': 10, 'units': 'min'}
DATA_COLLECTION_MIN_UPDATE_FREQUENCY = {'value': 1, 'units': 'min'}
DCS_CONFIG['MAX_DATA_CALLS_PER_MODULE_AND_EXECUTION'] = 4
_CONFIG = deepcopy(data_converter.CONFIG)
_CONFIG['STATE_STRUCT']['last_request'] = None
_CONFIG['PAGE_SIZE'] = PAGE_SIZE
_CONFIG['MAX_UPDATE_FREQUENCY'] = MAX_UPDATE_FREQUENCY
_CONFIG['MIN_UPDATE_FREQUENCY'] = MIN_UPDATE_FREQUENCY
_CONFIG['DATA_COLLECTION_MIN_UPDATE_FREQUENCY'] = DATA_COLLECTION_MIN_UPDATE_FREQUENCY
_CONFIG['DEPENDENCIES_UNSATISFIED_UPDATE_FREQUENCY'] = DEPENDENCIES_UNSATISFIED_UPDATE_FREQUENCY


def _get_config(*args, **kwargs):
    return deepcopy(_CONFIG)


class SimpleDataConverter(data_converter.DataConverter):
    """
        This DataConverter does not perform actual work. Failure or success are fully configurable, and so are the
        state variables and inner attributes.
        With this class, all possible scenarios (transitions, failures, etc...) can be tested.
    """

    def __init__(self, fail_on='', pending_work=True, elements_to_convert=None, data_converted=None, data_inserted=None,
                 update_frequency={'value': 0, 'units': 's'}, restart_required=False, backoff_time=None,
                 log_to_file=True, log_to_stdout=False, log_to_telegram=False, dependencies_satisfied=True):
        fake_file_path = DCS_CONFIG['DATA_CONVERTERS_PATH'] + 'test/simple_data_converter/simple_data_converter.py'
        super().__init__(fake_file_path, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)
        self.fail_on = fail_on
        self._elements_to_convert = elements_to_convert
        self._pending_work = pending_work
        self._update_frequency = update_frequency
        self._data_converted = data_converted
        self._data_inserted = data_inserted
        self._restart_required = restart_required
        self._backoff_time = backoff_time
        self._dependencies_satisfied = dependencies_satisfied
        self.method_name = '__init__'

    def _restore_state(self):
        super()._restore_state()
        self.state['update_frequency'] = self._update_frequency
        if self.fail_on == '_restore_state':
            raise Exception('Fail!')
        self.state['restart_required'] = self._restart_required
        if self._backoff_time:
            self._pending_work = False
            self.state['backoff_time']['value'] = self._backoff_time

    def _has_pending_work(self):
        super()._has_pending_work()
        self.pending_work = self._pending_work
        if self.fail_on == '_has_pending_work':
            raise Exception('Fail!')

    def _convert_data(self):
        super()._convert_data()
        if self.fail_on == '_convert_data':
            self.state['elements_to_convert'] = self.elements_to_convert
            self.state['converted_elements'] = None
            self.state['inserted_elements'] = None
            raise Exception('Fail!')
        self.state['elements_to_convert'] = self._elements_to_convert
        self.state['converted_elements'] = self._data_converted
        self.state['last_request'] = datetime.datetime.now(tz=UTC)

    def _perform_data_conversion(self):
        if self.fail_on == '_perform_data_conversion':
            raise Exception('Fail!')
        self.data = []
        for i in range(self._data_converted if self._data_converted is not None else 0):
            self.data.append(i)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = self._dependencies_satisfied
        if self.fail_on == '_check_dependencies_satisfied':
            raise Exception('Fail!')

    def _save_data(self):
        super()._save_data()
        if self.fail_on == '_save_data':
            raise Exception('Fail!')
        self.state['inserted_elements'] = self._data_inserted

    def _check_execution(self):
        super()._check_execution()
        if self.fail_on == '_check_execution':
            raise Exception('Fail!')

    def _save_state(self):
        if self.fail_on == '_save_state':
            raise Exception('Fail!')
        super()._save_state()


@mock.patch('os.environ', ENVIRON)
@mock.patch('data_conversion_subsystem.data_converter.data_converter.DCS_CONFIG', DCS_CONFIG)
class TestDataConverter(TestCase):

    def create_run(self, fail_on='', pending_work=True, data_converted=None, data_inserted=None,
                   elements_to_convert=None, update_frequency={'value': 0, 'units': 's'}, dependencies_satisfied=True):
        with mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config') as mock_config:
            mock_config.side_effect = _get_config
            self.data_converter = SimpleDataConverter(fail_on=fail_on, pending_work=pending_work,
                    elements_to_convert=elements_to_convert, data_converted=data_converted, data_inserted=data_inserted,
                    update_frequency=update_frequency, dependencies_satisfied=dependencies_satisfied, log_to_stdout=False)
            self.data_converter.run()

    @classmethod
    def setUpClass(cls):
        SimpleDataConverter().remove_files()

    def setUp(self):
        self.data_converter = None

    def tearDown(self):
        if self.data_converter:
            self.data_converter.remove_files()

    def test_create_fails(self):
        # Since '.config' file hasn't been defined, DataConverter isn't runnable.
        self.data_converter = SimpleDataConverter()
        self.assertFalse(self.data_converter.is_runnable())

    @mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config')
    def test_invalid_state_struct(self, mock):
        config = deepcopy(CONFIG)
        config['STATE_STRUCT'] = {'update_frequency': {'value': 1, 'units': 's'}, 'last_request': None}
        # Since 'STATE_STRUCT' has less fields than expected, DataConverter isn't runnable.
        mock.return_value = config
        self.data_converter = SimpleDataConverter()
        self.assertFalse(self.data_converter.is_runnable())

    @mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config')
    def test_invalid_config(self, mock):
        # Since 'STATE_STRUCT' has less fields than expected, DataConverter isn't runnable.
        mock.return_value = {}
        self.data_converter = SimpleDataConverter()
        self.assertFalse(self.data_converter.is_runnable())

    @mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config')
    def test_correct_creation(self, mock):
        mock.return_value = CONFIG
        self.data_converter = SimpleDataConverter()
        self.assertTrue(self.data_converter.is_runnable())

    @mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config')
    def test_expose_inner_data(self, mock):
        class Thief:  # isinstance(o, Supervisor) is False
            pass

        class FakeSupervisor(DataConverterSupervisor):  # isinstance(o, Supervisor) is True
            pass

        # Negative cases
        mock.return_value = CONFIG
        self.data_converter = SimpleDataConverter()
        thief = Thief()
        elegant_thief = FakeSupervisor(None, None)
        self.assertIsNone(self.data_converter.expose_transition_states(who=thief))
        self.assertIsNone(self.data_converter.expose_transition_states(who=elegant_thief))
        self.assertFalse(self.data_converter.execute_actions(CREATED, who=thief))
        self.assertFalse(self.data_converter.execute_actions(CREATED, who=elegant_thief))

        # Positive case
        supervisor = DataConverterSupervisor(None, None)
        expected = [CREATED, INITIALIZED]
        result = self.data_converter.expose_transition_states(who=supervisor)
        self.assertIsNotNone(result)
        self.assertEqual(expected, result)
        self.assertTrue(self.data_converter.execute_actions(CREATED, who=supervisor))

    @mock.patch('requests.get')
    def test_remove_files(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        from os.path import exists
        from global_config.config import GLOBAL_CONFIG
        from utilities.util import map_data_collector_path_to_state_file_path

        mock.return_value = CONFIG
        self.create_run(data_converted=1000, data_inserted=1000)
        self.data_converter.remove_files()
        self.assertFalse(
                exists(map_data_collector_path_to_state_file_path(__file__, GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'])))
        self.assertFalse(
                exists(GLOBAL_CONFIG['ROOT_LOG_FOLDER'] + 'test/simple__data_converter/simple__data_converter.py'))

    @mock.patch('requests.get')
    def test_positive_execution_with_pending_work(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(elements_to_convert=2, data_converted=2, data_inserted=2)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertTrue(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertEqual(2, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_normal_execution_with_no_pending_work(self):
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(pending_work=False)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, EXECUTION_CHECKED, STATE_SAVED,
                    FINISHED]
        self.assertFalse(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertTrue(self.data_converter.successful_execution())
        self.assertIsNone(self.data_converter.state['elements_to_convert'])
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_pending_work_less_saved_than_converted(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(elements_to_convert=2, data_converted=2, data_inserted=1)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertFalse(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertEqual(1, self.data_converter.state['inserted_elements'])
        self.assertGreater(self.data_converter.state['converted_elements'],
                           self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_pending_work_less_converted_than_saved(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(elements_to_convert=2, data_converted=1, data_inserted=2)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertFalse(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(1, self.data_converter.state['converted_elements'])
        self.assertEqual(2, self.data_converter.state['inserted_elements'])
        self.assertLess(self.data_converter.state['converted_elements'], self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_pending_work_not_converted(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(elements_to_convert=2, data_converted=0, data_inserted=0)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertFalse(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(0, self.data_converter.state['converted_elements'])
        self.assertEqual(0, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_pending_work_converted_not_saved(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(elements_to_convert=2, data_converted=2, data_inserted=0)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertFalse(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertEqual(0, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_INITIALIZED(self):
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(fail_on='_restore_state')
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, ABORTED]
        self.assertIsNone(self.data_converter.pending_work)
        self.assertIsNone(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_STATE_RESTORED(self):
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(fail_on='_has_pending_work')
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertIsNone(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_failure_PENDING_WORK_CHECKED(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(fail_on='_convert_data')
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertIsNone(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_failure_DATA_COLLECTED(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(fail_on='_save_data', elements_to_convert=2, data_converted=2)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertIsNone(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_failure_DATA_SAVED(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(fail_on='_check_execution', elements_to_convert=2, data_converted=2, data_inserted=2)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertEqual(2, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_abnormal_execution_failure_EXECUTION_CHECKED(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(fail_on='_save_state', elements_to_convert=2, data_converted=2, data_inserted=2)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertEqual(2, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_dependencies_unsatisfied(self):
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=False)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertTrue(self.data_converter.successful_execution())
        self.assertFalse(self.data_converter.dependencies_satisfied)
        self.assertIsNone(self.data_converter.state['elements_to_convert'])
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)
        self.assertDictEqual(DEPENDENCIES_UNSATISFIED_UPDATE_FREQUENCY, self.data_converter.state['update_frequency'])

    @mock.patch('requests.get', Mock(side_effect=Timeout('Test error to verify requests timeout. This is OK.')))
    def test_requests_timed_out(self):
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=True)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertTrue(self.data_converter.dependencies_satisfied)
        self.assertIsNone(self.data_converter.state['elements_to_convert'])
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_API_responses_unparseable_json_content_error_code(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 500
        response.content = '<html><h1>Internal Error</h1></html>'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=True)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertFalse(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertTrue(self.data_converter.dependencies_satisfied)
        self.assertIsNone(self.data_converter.state['elements_to_convert'])
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_API_responses_unparseable_content_at_all_error_code(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 500
        response.content = '\xf9291\x32'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=True)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, ABORTED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertFalse(self.data_converter.check_result)
        self.assertIsNotNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertFalse(self.data_converter.successful_execution())
        self.assertTrue(self.data_converter.dependencies_satisfied)
        self.assertIsNone(self.data_converter.state['elements_to_convert'])
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('requests.get')
    def test_correct_data_conversion_no_data_to_convert(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": []}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=True)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertTrue(self.data_converter.successful_execution())
        self.assertTrue(self.data_converter.advisedly_no_data_converted)
        self.assertIsNone(self.data_converter.state['elements_to_convert'])
        self.assertIsNone(self.data_converter.state['converted_elements'])
        self.assertIsNone(self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)
        self.assertDictEqual(MIN_UPDATE_FREQUENCY, self.data_converter.state['update_frequency'])

    @mock.patch('requests.get')
    def test_correct_data_conversion_data_to_convert_last_data(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=True, elements_to_convert=2, data_converted=2, data_inserted=2)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertTrue(self.data_converter.successful_execution())
        self.assertEqual(2, self.data_converter.state['start_index'])
        self.assertEqual(2, self.data_converter.state['elements_to_convert'])
        self.assertEqual(2, self.data_converter.state['converted_elements'])
        self.assertEqual(2, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)
        self.assertDictEqual(MAX_UPDATE_FREQUENCY, self.data_converter.state['update_frequency'])

    @mock.patch('requests.get')
    def test_correct_data_conversion_data_to_convert_more_data(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content.decode = Mock(side_effect=['{"data": [{"foo": true}, {"baz": false}], "next_start_index": 2}',
                                                    '{"data": [{"foo": true}, {"baz": false}], "next_start_index": 4}',
                                                    '{"data": [{"foo": true}, {"baz": false}], "next_start_index": 6}',
                                                    '{"data": [{"foo": true}, {"baz": false}], "next_start_index": 8}'])
        supervisor = DataConverterSupervisor(None, None)
        self.create_run(dependencies_satisfied=True, elements_to_convert=8, data_converted=8, data_inserted=8)
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_converter.pending_work)
        self.assertTrue(self.data_converter.check_result)
        self.assertIsNone(self.data_converter.state['error'])
        self.assertTrue(self.data_converter.finished_execution())
        self.assertTrue(self.data_converter.successful_execution())
        self.assertEqual(8, self.data_converter.state['start_index'])
        self.assertEqual(8, self.data_converter.state['elements_to_convert'])
        self.assertEqual(8, self.data_converter.state['converted_elements'])
        self.assertEqual(8, self.data_converter.state['inserted_elements'])
        self.assertListEqual(expected, transitions)
        self.assertDictEqual(DATA_COLLECTION_MIN_UPDATE_FREQUENCY, self.data_converter.state['update_frequency'])

    @mock.patch('requests.get')
    @mock.patch('data_conversion_subsystem.data_converter.data_converter.get_config', Mock(return_value=CONFIG))
    def test_exponential_backoff_mechanism(self, mock_requests):
        mock_requests.return_value = response = Mock()
        response.status_code = 200
        response.content = '{"data": [{"foo": true}, {"baz": false}]}'.encode()
        supervisor = DataConverterSupervisor(None, None)
        dc = SimpleDataConverter(fail_on='_restore_state')
        dc.run()
        # Checking exponential backoff update, and error saving
        self.assertIsNone(dc.state['error'])
        dc = SimpleDataConverter(fail_on='_convert_data')
        dc.run()
        self.assertIsNotNone(dc.state['error'])
        dc.execute_actions(EXECUTION_CHECKED, supervisor)
        self.assertEqual('Exception', dc.state['error'])
        self.assertDictEqual({'Exception': 1}, dc.state['errors'])
        exponential_backoff_value = dc.state['backoff_time']['value']
        config = dc.config
        dc2 = SimpleDataConverter(fail_on='_save_data')
        dc2.run()
        dc2.config = config
        dc2.execute_actions(EXECUTION_CHECKED, supervisor)
        self.assertGreater(dc2.state['backoff_time']['value'], exponential_backoff_value)  # Next exponential backoff
        self.assertEqual('Exception', dc2.state['error'])
        self.assertDictEqual({'Exception': 2}, dc2.state['errors'])
        exponential_backoff_value = dc2.state['backoff_time']['value']
        config = dc2.config
        dc3 = SimpleDataConverter(fail_on='_save_data')
        dc3.run()
        dc3.config = config
        dc3.state['error'] = {'class': 'ValueError', 'message': 'Fail!'}
        dc3.execute_actions(EXECUTION_CHECKED, supervisor)
        self.assertLess(dc3.state['backoff_time']['value'], exponential_backoff_value)  # Exponential backoff restarted
        self.assertEqual('ValueError', dc3.state['error'])
        self.assertDictEqual({'Exception': 2, 'ValueError': 1}, dc3.state['errors'])

        # Checking a module with restart_required and big exponential_backoff won't work
        self.data_converter = SimpleDataConverter(pending_work=True, restart_required=True, backoff_time=2000)
        self.data_converter.run()
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, EXECUTION_CHECKED, STATE_SAVED,
                    FINISHED]
        self.assertListEqual(expected, transitions)

        # Checking a module with restart_required and short exponential_backoff will work as usual
        self.data_converter = SimpleDataConverter(pending_work=True, restart_required=True, backoff_time=0,
                                                  data_converted=1, data_inserted=1)
        self.data_converter.run()
        transitions = self.data_converter.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_CONVERTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertListEqual(expected, transitions)

        # Checking a module with big exponential backoff and successful execution restarts backoff.
        self.data_converter = SimpleDataConverter(pending_work=True, restart_required=False, backoff_time=2000,
                                                  data_converted=1, data_inserted=1)
        self.data_converter.run()
        self.assertTrue(self.data_converter.successful_execution())
        self.assertDictEqual(data_converter.MIN_BACKOFF, self.data_converter.state['backoff_time'])
