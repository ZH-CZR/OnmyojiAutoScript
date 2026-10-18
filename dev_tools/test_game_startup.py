"""Initial game launch and subsequent recovery, without operating a device."""
from datetime import datetime, timedelta
import unittest
from unittest.mock import Mock, patch

from module.config.config import Config
from module.script import ScriptRuntimeController, ScriptRuntimeDecision
from script import Script


class GameStartupTest(unittest.TestCase):
    def make_runner(self):
        runner = Script.__new__(Script)
        runner.config_name = 'game-startup-regression'
        config = Config('template')
        config.model.restart.scheduler.enable = False
        runner.__dict__['config'] = config
        runner.__dict__['device'] = Mock(activity_guard=None)
        runner.__dict__['activity_guard'] = Mock()
        runner.activity_guard.checkpoint.return_value = False
        runner._emulator_down = False
        runner._error_restart_pending = False
        runner._error_restart_count = 0
        runner.last_task_runtime_outcome = None
        runner.runtime = ScriptRuntimeController(runner)
        return runner

    def test_cold_emulator_launches_game_and_continues_with_restart_disabled(self):
        runner = self.make_runner()
        runner._emulator_down = True
        device = runner.device
        device.app_is_running.side_effect = [False, True, True]
        with patch('module.script.runtime_controller.Device', return_value=device) as connect, \
                patch('tasks.Restart.login.LoginHandler') as login, \
                patch.object(runner, '_delay_tasks_for_server_update', return_value=False), \
                patch('script.load_module') as load:
            login.return_value.app_handle_login.return_value = True
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.RESCHEDULE)
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.READY)
        connect.assert_called_once_with(runner.config)
        self.assertFalse(runner._emulator_down)
        device.app_start.assert_called_once_with()
        device.app_stop.assert_not_called()
        login.assert_called_once_with(config=runner.config, device=device)
        login.return_value.app_handle_login.assert_called_once_with()
        load.assert_not_called()
        runner.activity_guard.start.assert_called_once_with()
        runner.activity_guard.finish.assert_called_once_with()
        self.assertIsNone(device.activity_guard)
        self.assertFalse(runner.config.model.restart.scheduler.enable)
        self.assertEqual(runner._error_restart_count, 0)

    def test_config_reload_does_not_grant_another_initial_launch(self):
        runner = self.make_runner()
        runner.device.app_is_running.side_effect = [True, False]
        self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                         ScriptRuntimeDecision.READY)
        runner.__dict__['config'] = Config('template')
        with patch.object(runner, 'run', return_value=False) as run:
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.FAILED)
        run.assert_called_once_with('Restart')

    def test_running_game_does_not_launch_and_later_loss_respects_restart_switch(self):
        runner = self.make_runner()
        runner.device.app_is_running.side_effect = [True, False]
        self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                         ScriptRuntimeDecision.READY)
        with patch.object(runner.config.notifier, 'push'), self.assertRaises(SystemExit):
            runner.runtime.prepare_task_execution('AbyssShadows')
        runner.device.app_start.assert_not_called()

    def test_failed_startup_does_not_repeat_initial_launch(self):
        runner = self.make_runner()
        runner.device.app_is_running.return_value = False
        with patch.object(runner, 'run', return_value=False) as run:
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.FAILED)
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.FAILED)
        self.assertEqual([c.args for c in run.call_args_list], [('GameStartup',), ('Restart',)])

    def test_startup_success_requires_game_to_be_running(self):
        runner = self.make_runner()
        runner.device.app_is_running.return_value = False
        with patch.object(runner, 'run', return_value=True):
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.FAILED)
        self.assertFalse(runner.runtime.game_startup_pending)

    def test_idle_game_preparation_uses_initial_launch(self):
        runner = self.make_runner()
        runner.device.app_is_running.side_effect = [False, True]
        with patch.object(runner, 'run', return_value=True) as run:
            self.assertEqual(runner.runtime._ensure_game_running(),
                             ScriptRuntimeDecision.RESCHEDULE)
        run.assert_called_once_with('GameStartup')

    def test_maintenance_wait_preserves_startup_allowance_without_opening_game(self):
        runner = self.make_runner()
        runner.device.app_is_running.return_value = False
        until = datetime.now() + timedelta(hours=1)

        def delay(*args):
            runner._set_task_runtime_outcome('GameStartup', 'server_update_delayed', until)
            return True

        with patch.object(runner, '_delay_tasks_for_server_update', side_effect=delay):
            self.assertEqual(runner.runtime.prepare_task_execution('AbyssShadows'),
                             ScriptRuntimeDecision.RESCHEDULE)
        self.assertEqual(runner.runtime.server_update_wait_until, until)
        self.assertTrue(runner.runtime.game_startup_pending)
        runner.device.app_start.assert_not_called()
        runner.activity_guard.finish.assert_called_once_with()

    def test_launch_error_uses_existing_error_handler_and_finishes_guard(self):
        runner = self.make_runner()
        error = RuntimeError('launch failed')
        runner.device.app_start.side_effect = error
        with patch.object(runner, '_delay_tasks_for_server_update', return_value=False), \
                patch.object(runner, '_handle_task_exception', return_value=False) as handler:
            self.assertFalse(runner.run('GameStartup'))
        handler.assert_called_once_with(error, 'GameStartup')
        runner.activity_guard.finish.assert_called_once_with()
        self.assertIsNone(runner.device.activity_guard)

    def test_scheduled_restart_keeps_existing_switch_check(self):
        runner = self.make_runner()
        self.assertEqual(runner.runtime.prepare_task_execution('Restart'), ScriptRuntimeDecision.READY)
        with patch.object(runner.config.notifier, 'push'), self.assertRaises(SystemExit):
            runner.run('Restart')
        runner.device.app_start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
