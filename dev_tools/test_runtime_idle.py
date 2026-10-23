"""Defer idle courtyard navigation until a task is selected; no device IO."""
from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from module.config.config import Config
from module.script import ScriptRuntimeController, ScriptRuntimeDecision
from script import Script


class RuntimeIdleTest(unittest.TestCase):
    def setUp(self):
        self.runner = Script.__new__(Script)
        self.runner.__dict__['config'] = Config('template')
        self.runner.__dict__['device'] = Mock(activity_guard=None)
        self.runner.__dict__['activity_guard'] = Mock()
        self.runner.activity_guard.checkpoint.return_value = False
        self.runner._emulator_down = False
        self.runner.state_queue = None
        self.runner.last_task_runtime_outcome = None
        self.runner.wait_until = Mock(return_value=True)
        self.runner.prepare_main_page = Mock(return_value=True)
        self.runner.run = Mock(return_value=True)
        self.runtime = ScriptRuntimeController(self.runner)
        self.runner.runtime = self.runtime
        self.until = datetime.now() + timedelta(minutes=10)

    def wait(self, strategy='goto_main'):
        self.runner.config.script.optimization.when_task_queue_empty = strategy
        return self.runtime.handle_wait_during_idle(self.until)

    def test_idle_wait_keeps_current_page_without_querying_or_launching_game(self):
        self.runner.device.app_is_running.return_value = False
        self.assertEqual(self.wait(), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_not_called()
        self.runner.device.app_is_running.assert_not_called()
        self.runner.run.assert_not_called()
        self.runner.device.release_during_wait.assert_called_once_with()
        self.runner.wait_until.assert_called_once_with(self.until)

    def test_repeated_interrupted_waits_do_not_navigate(self):
        self.runner.wait_until.return_value = False
        for _ in range(2):
            self.assertEqual(self.wait(), ScriptRuntimeDecision.RESCHEDULE)
        self.runner.prepare_main_page.assert_not_called()
        self.assertTrue(self.runtime.main_page_pending)

    def test_scheduler_reselects_before_returning_to_courtyard(self):
        waiting = SimpleNamespace(command='Orochi', next_run=self.until)
        due = SimpleNamespace(command='Pets', next_run=datetime.now() - timedelta(seconds=1))
        config = self.runner.config
        with patch.object(config, 'reload'), \
                patch.object(config, 'get_next', side_effect=[waiting, due]):
            self.assertEqual(self.runner.get_next_task(), 'Pets')
        self.runner.prepare_main_page.assert_not_called()
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_called_once_with()
        self.assertFalse(self.runtime.main_page_pending)
        # Consecutive due tasks keep their own scene navigation.
        self.assertEqual(self.runtime.prepare_task_execution('Orochi'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_called_once_with()

    def test_short_close_emulator_wait_also_defers_navigation(self):
        self.assertEqual(self.wait('close_emulator_or_goto_main'), ScriptRuntimeDecision.READY)
        self.runner.device.emulator_stop.assert_not_called()
        self.runner.prepare_main_page.assert_not_called()
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_called_once_with()

    def test_emulator_preheat_does_not_launch_game_or_navigate(self):
        self.runner._emulator_down = True
        current = datetime.now()

        def advance(future):
            nonlocal current
            current = future
            return True

        self.runner.wait_until.side_effect = advance
        with patch('module.script.runtime_controller.datetime') as clock, \
                patch('module.script.runtime_controller.Device', return_value=self.runner.device) as connect:
            clock.now.side_effect = lambda: current
            self.assertEqual(self.wait('close_emulator_or_goto_main'), ScriptRuntimeDecision.READY)
        self.assertEqual(self.runner.wait_until.call_args_list[-1].args, (self.until,))
        self.assertEqual(self.runner.wait_until.call_count, 2)
        connect.assert_called_once_with(self.runner.config)
        self.runner.prepare_main_page.assert_not_called()
        self.runner.device.app_is_running.assert_not_called()
        self.runner.run.assert_not_called()
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_called_once_with()

    def test_game_launch_is_deferred_until_task_and_navigation_survives_reschedule(self):
        self.runner.device.app_is_running.side_effect = [False, True, True]
        self.assertEqual(self.wait(), ScriptRuntimeDecision.READY)
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.RESCHEDULE)
        self.runner.run.assert_called_once_with('GameStartup')
        self.runner.prepare_main_page.assert_not_called()
        self.assertTrue(self.runtime.main_page_pending)
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_called_once_with()

    def test_config_replacement_keeps_deferred_navigation(self):
        self.wait()
        self.runner.__dict__['config'] = Config('template')
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_called_once_with()

    def test_failed_navigation_prevents_task_and_can_retry(self):
        self.wait()
        self.runner.prepare_main_page.side_effect = [False, True]
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.FAILED)
        self.assertTrue(self.runtime.main_page_pending)
        self.runner.run.assert_not_called()
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.assertFalse(self.runtime.main_page_pending)

    def test_maintenance_navigation_failure_reschedules_and_preserves_request(self):
        self.wait()

        def maintenance():
            self.runner.last_task_runtime_outcome = dict(status='server_update_delayed', wait_until=self.until)
            return False

        self.runner.prepare_main_page.side_effect = maintenance
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.RESCHEDULE)
        self.assertEqual(self.runtime.server_update_wait_until, self.until)
        self.assertTrue(self.runtime.main_page_pending)

    def test_maintenance_idle_keeps_existing_close_game_policy(self):
        self.runtime.server_update_wait_until = self.until
        self.assertEqual(self.wait(), ScriptRuntimeDecision.READY)
        self.runner.device.app_stop.assert_called_once_with()
        self.runner.prepare_main_page.assert_not_called()

    def test_restart_bypasses_deferred_navigation(self):
        self.wait()
        self.assertEqual(self.runtime.prepare_task_execution('Restart'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_not_called()
        self.assertTrue(self.runtime.main_page_pending)

    def test_close_game_wait_keeps_its_policy_without_requesting_navigation(self):
        # Default threshold keeps the game running during a short wait.
        self.assertEqual(self.wait('close_game'), ScriptRuntimeDecision.READY)
        self.assertEqual(self.runtime.prepare_task_execution('Pets'), ScriptRuntimeDecision.READY)
        self.runner.prepare_main_page.assert_not_called()
        self.assertFalse(self.runtime.main_page_pending)


if __name__ == '__main__':
    unittest.main()
