import datetime
from unittest import TestCase, mock

from copy import deepcopy
from pytz import UTC

import data_gathering_subsystem.data_collector.data_collector as data_collector
from data_gathering_subsystem.data_collector.data_collector import ABORTED, CONFIG, CREATED, DATA_COLLECTED, DATA_SAVED, \
    EXECUTION_CHECKED, FINISHED, INITIALIZED, PENDING_WORK_CHECKED, STATE_RESTORED, STATE_SAVED
from data_gathering_subsystem.config.config import DGS_CONFIG
from data_gathering_subsystem.supervisor.supervisor import DataCollectorSupervisor


class SimpleDataCollector(data_collector.DataCollector):
    """
        This DataCollector does not perform actual work. Failure or success are fully configurable, and so are the
        state variables and inner attributes.
        With this class, all possible scenarios (transitions, failures, etc...) can be tested.
    """

    def __init__(self, fail_on='', pending_work=True, data_collected=None, data_inserted=None,
                 update_frequency={'value': 0, 'units': 's'}, restart_required=False, backoff_time=None,
                 log_to_file=True, log_to_stdout=False, log_to_telegram=False):
        fake_file_path = DGS_CONFIG['DATA_MODULES_PATH'] + 'test/simple_data_collector/simple_data_collector.py'
        super().__init__(fake_file_path, log_to_file=log_to_file, log_to_stdout=log_to_stdout, 
                         log_to_telegram=log_to_telegram)
        self.fail_on = fail_on
        self._pending_work = pending_work
        self._update_frequency = update_frequency
        self._data_collected = data_collected
        self._data_inserted = data_inserted
        self._restart_required = restart_required
        self._backoff_time = backoff_time
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

    def _collect_data(self):
        super()._collect_data()
        if self.fail_on == '_collect_data':
            raise Exception('Fail!')
        self.state['data_elements'] = self._data_collected
        self.state['last_request'] = datetime.datetime.now(tz=UTC)

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


class TestDataCollector(TestCase):

    def create_run(self, fail_on='', pending_work=True, data_collected=0, data_inserted=0,
                   update_frequency={'value': 0, 'units': 's'}, log_to_file=False, log_to_stdout=False, 
                   log_to_telegram=False):
        with mock.patch('data_gathering_subsystem.data_collector.data_collector.get_config') as mock_config:
            mock_config.return_value = deepcopy(CONFIG)
            CONFIG['STATE_STRUCT']['last_request'] = None
            self.data_collector = SimpleDataCollector(fail_on=fail_on, pending_work=pending_work,
                    data_collected=data_collected, data_inserted=data_inserted, update_frequency=update_frequency,
                    log_to_file=log_to_file, log_to_stdout=log_to_stdout, log_to_telegram=log_to_telegram)
            self.data_collector.run()

    @classmethod
    def setUpClass(cls):
        SimpleDataCollector().remove_files()

    def setUp(self):
        self.data_collector = None

    def tearDown(self):
        if self.data_collector:
            self.data_collector.remove_files()

    def test_create_fails(self):
        # Since '.config' file hasn't been defined, DataCollector isn't runnable.
        self.data_collector = SimpleDataCollector()
        self.assertFalse(self.data_collector.is_runnable())

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.get_config')
    def test_invalid_state_struct(self, mock):
        # Since 'STATE_STRUCT' has less fields than expected, DataCollector isn't runnable.
        mock.return_value = {'STATE_STRUCT': {'update_frequency': {'value': 1, 'units': 's'}}, 'last_request': None}
        self.data_collector = SimpleDataCollector()
        self.assertFalse(self.data_collector.is_runnable())

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.get_config')
    def test_correct_creation(self, mock):
        mock.return_value = CONFIG
        self.data_collector = SimpleDataCollector()
        self.assertTrue(self.data_collector.is_runnable())

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.get_config')
    def test_expose_inner_data(self, mock):
        class Thief:  # isinstance(o, Supervisor) is False
            pass

        class FakeSupervisor(DataCollectorSupervisor):  # isinstance(o, Supervisor) is True
            pass

        # Negative cases
        mock.return_value = CONFIG
        self.data_collector = SimpleDataCollector()
        thief = Thief()
        elegant_thief = FakeSupervisor(None, None)
        self.assertIsNone(self.data_collector.expose_transition_states(who=thief))
        self.assertIsNone(self.data_collector.expose_transition_states(who=elegant_thief))
        self.assertFalse(self.data_collector.execute_actions(CREATED, who=thief))
        self.assertFalse(self.data_collector.execute_actions(CREATED, who=elegant_thief))

        # Positive case
        supervisor = DataCollectorSupervisor(None, None)
        expected = [CREATED, INITIALIZED]
        result = self.data_collector.expose_transition_states(who=supervisor)
        self.assertIsNotNone(result)
        self.assertEqual(expected, result)
        self.assertTrue(self.data_collector.execute_actions(CREATED, who=supervisor))

    def test_remove_files(self):
        from os.path import exists
        from global_config.config import GLOBAL_CONFIG
        from utilities.util import map_data_collector_path_to_state_file_path

        mock.return_value = CONFIG
        self.create_run(data_collected=1000, data_inserted=1000)
        self.data_collector.remove_files()
        self.assertFalse(exists(map_data_collector_path_to_state_file_path(__file__,
                GLOBAL_CONFIG['ROOT_PROJECT_FOLDER'])))
        self.assertFalse(exists(GLOBAL_CONFIG['ROOT_LOG_FOLDER'] +
                'test/simple_data_collector/simple_data_collector.py'))

    def test_positive_execution_with_pending_work(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(data_collected=1000, data_inserted=1000)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertTrue(self.data_collector.check_result)
        self.assertIsNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.state['data_elements'], self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_normal_execution_with_no_pending_work(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(pending_work=False)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, EXECUTION_CHECKED, STATE_SAVED,
                    FINISHED]
        self.assertFalse(self.data_collector.pending_work)
        self.assertTrue(self.data_collector.check_result)
        self.assertIsNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_pending_work_less_saved_than_collected(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(data_collected=1000, data_inserted=987)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertFalse(self.data_collector.check_result)
        self.assertIsNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertGreater(self.data_collector.state['data_elements'], self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_pending_work_less_collected_than_saved(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(data_collected=987, data_inserted=1000)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertFalse(self.data_collector.check_result)
        self.assertIsNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertLess(self.data_collector.state['data_elements'], self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_pending_work_collected_not_saved(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(data_collected=1000, data_inserted=0)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertFalse(self.data_collector.check_result)
        self.assertIsNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1000, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)


    def test_abnormal_execution_failure_INITIALIZED(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(fail_on='_restore_state')
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, ABORTED]
        self.assertIsNone(self.data_collector.pending_work)
        self.assertIsNone(self.data_collector.check_result)
        self.assertIsNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_STATE_RESTORED(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(fail_on='_has_pending_work')
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, ABORTED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertIsNone(self.data_collector.check_result)
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_PENDING_WORK_CHECKED(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(fail_on='_collect_data')
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, ABORTED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertIsNone(self.data_collector.check_result)
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNone(self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_DATA_COLLECTED(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(fail_on='_save_data', data_collected=1000)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, ABORTED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertIsNone(self.data_collector.check_result)
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertEqual(1000, self.data_collector.state['data_elements'])
        self.assertIsNone(self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_DATA_SAVED(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(fail_on='_check_execution', data_collected=1000, data_inserted=1000)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED, ABORTED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertTrue(self.data_collector.check_result)
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1000, self.data_collector.state['data_elements'])
        self.assertEqual(1000, self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    def test_abnormal_execution_failure_EXECUTION_CHECKED(self):
        supervisor = DataCollectorSupervisor(None, None)
        self.create_run(fail_on='_save_state', data_collected=1000, data_inserted=1000)
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED,
                    EXECUTION_CHECKED, ABORTED]
        self.assertTrue(self.data_collector.pending_work)
        self.assertTrue(self.data_collector.check_result)
        self.assertIsNotNone(self.data_collector.state['error'])
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1000, self.data_collector.state['data_elements'])
        self.assertEqual(1000, self.data_collector.state['inserted_elements'])
        self.assertListEqual(expected, transitions)

    @mock.patch('data_gathering_subsystem.data_collector.data_collector.get_config')
    def test_exponential_backoff_mechanism(self, mock_config):
        mock_config.return_value = CONFIG
        supervisor = DataCollectorSupervisor(None, None)
        dc = SimpleDataCollector(fail_on='_restore_state')
        dc.run()
        # Checking exponential backoff update, and error saving
        self.assertIsNone(dc.state['error'])
        dc = SimpleDataCollector(fail_on='_collect_data')
        dc.run()
        self.assertIsNotNone(dc.state['error'])
        dc.execute_actions(EXECUTION_CHECKED, supervisor)
        self.assertEqual('Exception', dc.state['error'])
        self.assertDictEqual({'Exception': 1}, dc.state['errors'])
        exponential_backoff_value = dc.state['backoff_time']['value']
        config = dc.config
        dc2 = SimpleDataCollector(fail_on='_save_data')
        dc2.run()
        dc2.config = config
        dc2.execute_actions(EXECUTION_CHECKED, supervisor)
        self.assertGreater(dc2.state['backoff_time']['value'], exponential_backoff_value)  # Next exponential backoff
        self.assertEqual('Exception', dc2.state['error'])
        self.assertDictEqual({'Exception': 2}, dc2.state['errors'])
        exponential_backoff_value = dc2.state['backoff_time']['value']
        config = dc2.config
        dc3 = SimpleDataCollector(fail_on='_save_data')
        dc3.run()
        dc3.config = config
        dc3.state['error'] = {'class': 'ValueError', 'message': 'Fail!'}
        dc3.execute_actions(EXECUTION_CHECKED, supervisor)
        self.assertLess(dc3.state['backoff_time']['value'], exponential_backoff_value)  # Exponential backoff restarted
        self.assertEqual('ValueError', dc3.state['error'])
        self.assertDictEqual({'Exception': 2, 'ValueError': 1}, dc3.state['errors'])

        # Checking a module with restart_required and big exponential_backoff won't work
        self.data_collector = SimpleDataCollector(pending_work=True, restart_required=True, backoff_time=2000)
        self.data_collector.run()
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, EXECUTION_CHECKED, STATE_SAVED,
                    FINISHED]
        self.assertListEqual(expected, transitions)

        # Checking a module with restart_required and short exponential_backoff will work as usual
        self.data_collector = SimpleDataCollector(pending_work=True, restart_required=True, backoff_time=0,
                                                  data_collected=1, data_inserted=1)
        self.data_collector.run()
        transitions = self.data_collector.expose_transition_states(supervisor)
        expected = [CREATED, INITIALIZED, STATE_RESTORED, PENDING_WORK_CHECKED, DATA_COLLECTED, DATA_SAVED,
                    EXECUTION_CHECKED, STATE_SAVED, FINISHED]
        self.assertListEqual(expected, transitions)

        # Checking a module with big exponential backoff and successful execution restarts backoff.
        self.data_collector = SimpleDataCollector(pending_work=True, restart_required=False, backoff_time=2000,
                                                  data_collected=1, data_inserted=1)
        self.data_collector.run()
        self.assertTrue(self.data_collector.successful_execution())
        self.assertDictEqual(data_collector.MIN_BACKOFF, self.data_collector.state['backoff_time'])

    def test_reader(self):
        r = data_collector.Reader()
        data = ['HDR Foo Baz Bar\n', 'HDR\n', 'Actual data']
        for line in data:
            r(line)
        self.assertEqual(['Actual data'], r.get_data())
