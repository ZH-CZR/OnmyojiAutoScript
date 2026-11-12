"""Task completion navigation, without creating a device or starting the game."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.config import Config
from module.exception import GameStuckError, TaskEnd
from script import Script
from tasks.GameUi.page import page_main


class TaskCompletionTest(unittest.TestCase):
    def setUp(self):
        self.runner = Script.__new__(Script)
        self.runner.config_name = 'template'
        self.runner.__dict__['config'] = Config('template')
        self.runner.__dict__['device'] = Mock(activity_guard=None)
        self.runner.__dict__['activity_guard'] = Mock()
        self.runner.activity_guard.checkpoint.return_value = False
        self.runner.__dict__['immediate_execution'] = Mock()
        self.runner.runtime = SimpleNamespace(idle_main_prepared=False)
        self.runner._error_restart_pending = False

    def test_completion_confirms_courtyard_and_reuses_idle_marker(self):
        with patch('tasks.GameUi.game_ui.GameUi') as ui:
            ui.return_value.ui_goto_page.return_value = True
            self.runner._finish_task_page('RealmRaid')
        ui.assert_called_once_with(config=self.runner.config, device=self.runner.device)
        ui.return_value.ui_goto_page.assert_called_once_with(page_main)
        self.runner.device.screenshot.assert_called_once_with()
        self.assertTrue(self.runner.runtime.idle_main_prepared)

    def test_meta_demon_and_environment_tasks_keep_their_own_exit(self):
        with patch('tasks.GameUi.game_ui.GameUi') as ui:
            for command in ('MetaDemon', 'Restart', 'GameStartup'):
                self.runner._finish_task_page(command)
        ui.assert_not_called()
        self.runner.device.screenshot.assert_not_called()

    def test_maintenance_skips_navigation(self):
        self.runner.config.task_runtime_outcome = {'status': 'server_update_delayed'}
        with patch('tasks.GameUi.game_ui.GameUi') as ui:
            self.runner._finish_task_page('RealmRaid')
        ui.assert_not_called()

    def test_navigation_failure_is_not_reported_as_completed(self):
        with patch('tasks.GameUi.game_ui.GameUi') as ui:
            ui.return_value.ui_goto_page.return_value = False
            with self.assertRaises(GameStuckError):
                self.runner._finish_task_page('RealmRaid')
        self.assertFalse(self.runner.runtime.idle_main_prepared)

    def test_run_finishes_both_task_end_and_normal_return_but_not_errors(self):
        for error in (None, TaskEnd(), GameStuckError('battle failed')):
            with self.subTest(error=error):
                task = Mock()
                task.run.side_effect = error
                with patch('script.load_module', return_value=SimpleNamespace(ScriptTask=Mock(return_value=task))), \
                        patch.object(self.runner, '_finish_task_page') as finish, \
                        patch.object(self.runner, '_handle_task_exception', return_value=True):
                    self.assertTrue(self.runner.run('RealmRaid'))
                if error is None or isinstance(error, TaskEnd):
                    finish.assert_called_once_with('RealmRaid')
                else:
                    finish.assert_not_called()

    def test_failed_return_uses_existing_error_recovery(self):
        task = Mock()
        task.run.side_effect = TaskEnd()
        failure = GameStuckError('return failed')
        with patch('script.load_module', return_value=SimpleNamespace(ScriptTask=Mock(return_value=task))), \
                patch.object(self.runner, '_finish_task_page', side_effect=failure), \
                patch.object(self.runner, '_handle_task_exception', return_value=False) as handle:
            self.assertFalse(self.runner.run('RealmRaid'))
        handle.assert_called_once_with(failure, 'RealmRaid')

    def test_disabled_restart_does_not_announce_a_restart_countdown(self):
        self.runner.config.restart.scheduler.enable = False
        self.runner.save_error_log = Mock()
        self.runner.exception_handler = Mock()
        with patch.object(self.runner.config.notifier, 'push'), \
                patch('script.logger.warning') as warning, self.assertRaises(SystemExit):
            self.runner._handle_task_exception(GameStuckError('test'), 'RealmRaid')
        self.assertFalse(any('10' in str(call) for call in warning.call_args_list))
        self.runner.device.sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
