"""福利寮离线战斗回归：虚拟时间和设备，不启动游戏。"""
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.atom.image import RuleImage
from module.config.config_model import ConfigModel
from module.exception import GameStuckError, TaskEnd
from tasks.Dokan.config import Dokan
from tasks.Dokan.script_task import ScriptTask


class DokanOfflineTests(unittest.TestCase):
    def make_task(self, welfare=True, enabled=True):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(dokan=Dokan(welfare_config={'offline_battle_enable': enabled}))
        task.device = Mock()
        task.open_welfare = welfare
        task.team_switched = True
        task.current_count = 0
        task.ui_click_until_disappear = Mock()
        task.dokan_green_mark = Mock()
        task.welfare_offline_wait = Mock()
        task.switch_preset_team = Mock()
        task.leave_welfare_prepare = Mock()
        return task

    def battle(self, task, frames):
        frame = None
        iterator = iter(frames)

        def screenshot():
            nonlocal frame
            frame = next(iterator)

        def appear(target, **kwargs):
            return ((target is task.I_RYOU_DOKAN_IN_FIELD and frame == 'prepare')
                    or (target is task.I_BATTLE_INFO and frame in ('prepare', 'battle'))
                    or (target is task.I_RYOU_DOKAN_FIGHTING and frame in ('prepare', 'dokan_battle'))
                    or (target is task.I_DOKAN_BOSS_WAITING and frame == 'boss'))

        task.screenshot = Mock(side_effect=screenshot)
        task.appear = Mock(side_effect=appear)
        task.dokan_battle(task.config.dokan)

    def test_default_interface_and_saved_value(self):
        self.assertFalse(Dokan().welfare_config.offline_battle_enable)
        field = next(field for field in ConfigModel().script_task('Dokan')['welfare_config']
                     if field['name'] == 'offline_battle_enable')
        self.assertEqual(field['type'], 'boolean')
        saved = Dokan(welfare_config={'offline_battle_enable': True})
        self.assertTrue(Dokan.model_validate_json(saved.model_dump_json()).welfare_config.offline_battle_enable)

    def test_disabled_or_unconfirmed_guild_keeps_online_battle(self):
        for welfare, enabled in ((True, False), (False, True), (False, False)):
            task = self.make_task(welfare, enabled)
            self.battle(task, ['prepare', 'battle', 'boss'])
            task.welfare_offline_wait.assert_not_called()

    def test_closes_immediately_after_prepare_disappears_without_battle_icons(self):
        task = self.make_task()
        events = []
        task.ui_click_until_disappear.side_effect = lambda target: events.append('prepare_disappeared')
        task.welfare_offline_wait.side_effect = lambda: events.append('offline')
        self.battle(task, ['prepare'])
        self.assertEqual(events, ['prepare_disappeared', 'offline'])
        task.welfare_offline_wait.assert_called_once_with()
        self.assertEqual(task.screenshot.call_count, 1)
        task.ui_click_until_disappear.assert_called_once_with(task.I_RYOU_DOKAN_IN_FIELD)
        task.dokan_green_mark.assert_not_called()
        checked = [call.args[0] for call in task.appear.call_args_list]
        self.assertNotIn(task.I_RYOU_DOKAN_FIGHTING, checked)
        self.assertNotIn(task.I_BATTLE_INFO, checked)
        self.battle(task, ['prepare', 'boss'])
        task.welfare_offline_wait.assert_called_once_with()
        task.dokan_green_mark.assert_called_once()

    def test_waits_until_prepare_really_disappears(self):
        task = self.make_task()
        task.ui_click_until_disappear = ScriptTask.ui_click_until_disappear.__get__(task)
        task.appear_then_click = Mock(return_value=True)
        self.battle(task, ['prepare', 'prepare', 'prepare', 'unknown'])
        self.assertEqual(task.screenshot.call_count, 4)
        self.assertEqual(task.appear_then_click.call_count, 2)
        task.welfare_offline_wait.assert_called_once_with()

    def test_real_dokan_battle_asset_matches_without_opencv_size_error(self):
        task = self.make_task()
        asset = task.I_RYOU_DOKAN_FIGHTING
        marker = RuleImage(roi_front=tuple(asset.roi_front), roi_back=asset.roi_back,
                           method=asset.method, threshold=asset.threshold, file=asset.file)
        template = marker.image
        height, width = template.shape[:2]
        self.assertGreaterEqual(marker.roi_back[2], width)
        self.assertGreaterEqual(marker.roi_back[3], height)
        metadata = json.loads((Path(__file__).resolve().parents[1]
                               / 'tasks/Dokan/res/image.json').read_text(encoding='utf-8'))
        entry = next(item for item in metadata if item['itemName'] == 'ryou_dokan_fighting')
        for key, roi in (('roiFront', marker.roi_front), ('roiBack', marker.roi_back)):
            self.assertEqual(tuple(map(int, entry[key].split(','))), tuple(roi))

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertFalse(marker.match(frame))
        x, y = marker.roi_back[:2]
        frame[y:y + height, x:x + width] = template
        self.assertTrue(marker.match(frame))

    def test_dokan_marker_alone_does_not_bypass_disabled_or_normal_guild(self):
        for welfare, enabled in ((True, False), (False, True)):
            task = self.make_task(welfare, enabled)
            self.battle(task, ['prepare', 'dokan_battle', 'boss'])
            task.welfare_offline_wait.assert_not_called()

    def test_missed_member_battle_does_not_close_during_boss_battle(self):
        task = self.make_task()
        self.battle(task, ['boss'])
        self.battle(task, ['prepare', 'battle', 'boss'])
        task.welfare_offline_wait.assert_not_called()

    def test_new_selected_guild_resets_consumed_flag(self):
        task = self.make_task()
        task._welfare_offline_consumed = True
        task._welfare_no_more_battles = True
        task._dokan_quit_clicked = True
        task._dokan_quit_confirm_clicked = True
        task._dokan_quit_confirmed = True
        task._welfare_offline_returns = 1
        task._dokan_retry_clicked = True
        task.screenshot = Mock()
        task.appear_then_click = Mock(return_value=False)
        task.appear_rgb = Mock(return_value=True)
        task.find_dokan = Mock(return_value=True)
        task.find_dokan_list = []
        task.dokan_switch_soul = Mock()
        task.open_dokan()
        self.assertFalse(task._welfare_offline_consumed)
        self.assertFalse(task._welfare_no_more_battles)
        self.assertFalse(task._dokan_quit_clicked)
        self.assertFalse(task._dokan_quit_confirm_clicked)
        self.assertEqual(task._welfare_offline_returns, 1)
        self.assertFalse(task._dokan_quit_confirmed)
        self.assertFalse(task._dokan_retry_clicked)

    def test_random_wait_then_shared_device_login_and_return(self):
        for duration in (530, 540.5, 550):
            task = self.make_task()
            task.device.app_is_running.return_value = False
            task.goto_dokan = Mock()
            events = []
            now = [0.0]

            def sleep(seconds):
                self.assertLessEqual(seconds, 30)
                now[0] += seconds

            task.device.app_stop.side_effect = lambda: events.append('stop')
            task.device.app_start.side_effect = lambda: events.append(('start', now[0]))
            task.goto_dokan.side_effect = lambda: events.append('return')
            task.quit_dokan = Mock(side_effect=lambda cfg: events.append('quit'))
            with patch('tasks.Dokan.script_task.random.uniform', return_value=duration) as draw, \
                    patch('tasks.Dokan.script_task.time.monotonic', side_effect=lambda: now[0]), \
                    patch('tasks.Dokan.script_task.time.sleep', side_effect=sleep), \
                    patch('tasks.Restart.login.LoginHandler') as login:
                login.return_value._app_handle_login.side_effect = lambda: events.append('login')
                ScriptTask.welfare_offline_wait(task)
            draw.assert_called_once_with(530, 550)
            self.assertEqual(events, ['stop', ('start', duration), 'login', 'return', 'quit'])
            login.assert_called_once_with(config=task.config, device=task.device)
            login.return_value.app_handle_login.assert_not_called()
            task.device.stuck_record_clear.assert_called_once()
            task.device.click_record_clear.assert_called_once()
            self.assertFalse(task.team_switched)
            self.assertIsNone(task.ui_current)
            self.assertTrue(task.open_welfare)
            self.assertTrue(task._welfare_no_more_battles)
            task.quit_dokan.assert_called_once_with(task.config.dokan)

    def test_second_successful_login_finishes_without_entering_dokan(self):
        for explicit_time in (None, 'next-custom-time'):
            task = self.make_task()
            task._welfare_offline_returns = 1
            task.device.app_is_running.return_value = False
            task.goto_dokan = Mock()
            task.quit_dokan = Mock()
            task.check_current_weekday = Mock()
            task.create_doukan_time = explicit_time
            task.set_next_run = Mock()
            task.finish_task = Mock(side_effect=TaskEnd)
            with patch('tasks.Dokan.script_task.time.monotonic', side_effect=[0, 551]), \
                    patch('tasks.Restart.login.LoginHandler') as login:
                with self.assertRaises(TaskEnd):
                    ScriptTask.welfare_offline_wait(task)
            login.return_value._app_handle_login.assert_called_once_with()
            task.goto_dokan.assert_not_called()
            task.quit_dokan.assert_not_called()
            task.finish_task.assert_called_once_with()
            self.assertEqual(task._welfare_offline_returns, 2)
            task.check_current_weekday.assert_called_once_with(True)
            if explicit_time:
                task.set_next_run.assert_called_once_with(target=explicit_time)
            else:
                task.set_next_run.assert_called_once_with(
                    task='Dokan', finish=True, server=True, success=True)

    def test_failed_second_login_does_not_mark_task_complete(self):
        task = self.make_task()
        task._welfare_offline_returns = 1
        task.device.app_is_running.return_value = False
        task.goto_dokan = Mock()
        task.finish_task = Mock()
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=[0, 551]), \
                patch('tasks.Restart.login.LoginHandler') as login:
            login.return_value._app_handle_login.side_effect = GameStuckError('login failed')
            with self.assertRaises(GameStuckError):
                ScriptTask.welfare_offline_wait(task)
        self.assertEqual(task._welfare_offline_returns, 1)
        task.finish_task.assert_not_called()
        task.goto_dokan.assert_not_called()

    def test_stop_and_login_errors_propagate_without_return(self):
        task = self.make_task()
        task.goto_dokan = Mock()
        task.device.app_is_running.return_value = True
        with patch('tasks.Dokan.script_task.time.sleep') as sleep, self.assertRaises(GameStuckError):
            ScriptTask.welfare_offline_wait(task)
        sleep.assert_not_called()
        task.device.app_start.assert_not_called()
        task.goto_dokan.assert_not_called()

        task.device.app_is_running.return_value = False
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=[0, 551]), \
                patch('tasks.Restart.login.LoginHandler') as login:
            login.return_value._app_handle_login.side_effect = GameStuckError('login failed')
            with self.assertRaises(GameStuckError):
                ScriptTask.welfare_offline_wait(task)
        task.goto_dokan.assert_not_called()


if __name__ == '__main__':
    unittest.main()
