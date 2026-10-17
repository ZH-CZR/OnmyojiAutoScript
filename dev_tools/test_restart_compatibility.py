"""Exercise scheduler completion and recovery without operating a game device."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from script import Script, ScriptRuntimeDecision
from tasks.Restart.config import Restart


class SchedulerBoundary(BaseException):
    """Stop after the scheduler has completed one iteration."""


class RestartCompatibilityTest(unittest.TestCase):
    def make_runner(self, restart=None):
        runner = Script.__new__(Script)
        runner.config_name = 'restart-regression'
        runner.resource_precache_enable = False
        runner.is_first_task = False
        runner._error_restart_pending = False
        runner._error_restart_count = 0
        runner.failure_record = {}
        config = SimpleNamespace(
            model=SimpleNamespace(restart=restart or Restart(), running_task=''),
            script=SimpleNamespace(
                device=SimpleNamespace(run_background_only=True),
                error=SimpleNamespace(handle_error=False, error_repeated=False)),
            notifier=Mock(), task_call=Mock())
        runner.__dict__['config'] = config
        runner.__dict__['device'] = Mock()
        runner.runtime = Mock()
        runner.runtime.prepare_task_execution.return_value = ScriptRuntimeDecision.READY
        runner.get_next_task = Mock(side_effect=['RyouToppa', SchedulerBoundary()])
        return runner, config

    def test_old_config_gets_defaults_and_retains_port_fields(self):
        restart = Restart.model_validate({
            'task_config': {'task_date': '2026-10-16'},
            'harvest_config': {'enable_mail': False}})
        self.assertEqual(restart.restart_config.error_restart_limit, 3)
        self.assertTrue(restart.scheduler.enable)
        self.assertEqual(restart.task_config.task_date, '2026-10-16')
        self.assertFalse(restart.harvest_config.enable_mail)

    def test_success_resets_failures_and_reaches_next_schedule(self):
        runner, config = self.make_runner()
        runner.failure_record['RyouToppa'] = 2
        runner.run = Mock(return_value=True)
        with patch('script.logger'), patch('script.RuleScatter'), \
                self.assertRaises(SchedulerBoundary):
            runner.loop()
        self.assertEqual(runner.failure_record['RyouToppa'], 0)
        self.assertEqual(config.model.running_task, '')
        self.assertEqual(runner.get_next_task.call_count, 2)
        runner.run.assert_called_once_with('RyouToppa')
        config.notifier.push.assert_not_called()
        runner.device.emulator_stop.assert_not_called()

    def test_failure_is_counted_without_missing_attribute(self):
        runner, config = self.make_runner()
        runner.run = Mock(return_value=False)
        with patch('script.logger'), patch('script.RuleScatter'):
            runner.loop()
        self.assertEqual(runner.failure_record['RyouToppa'], 1)
        config.notifier.push.assert_not_called()

    def test_explicit_recovery_budget_and_zero_are_respected(self):
        for limit in (0, 2):
            with self.subTest(limit=limit):
                restart = Restart.model_validate({'restart_config': {'error_restart_limit': limit}})
                runner, config = self.make_runner(restart)
                with patch('script.logger'):
                    for _ in range(limit):
                        runner._request_error_restart('RyouToppa')
                    with self.assertRaises(SystemExit):
                        runner._request_error_restart('RyouToppa')
                self.assertEqual(runner._error_restart_count, limit)
                self.assertEqual(config.task_call.call_count, limit)
                config.notifier.push.assert_called_once()

    def test_disabled_restart_stops_recovery_before_scheduling(self):
        runner, config = self.make_runner(Restart.model_validate({'scheduler': {'enable': False}}))
        with patch('script.logger'), self.assertRaises(SystemExit):
            runner._request_error_restart('RyouToppa')
        config.task_call.assert_not_called()
        self.assertEqual(runner._error_restart_count, 0)
