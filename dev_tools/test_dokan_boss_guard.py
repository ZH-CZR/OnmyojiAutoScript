"""福利寮馆主保护：不连接游戏、设备或OCR服务。"""
import unittest
import json
from pathlib import Path

import numpy as np
from PIL import Image
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import GameStuckError, TaskEnd
from tasks.Dokan.config import Dokan
from tasks.Dokan.script_task import DokanScene, ScriptTask


class DokanBossGuardTests(unittest.TestCase):
    def make_task(self, welfare=True):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(dokan=Dokan())
        task.open_welfare = welfare
        task.device = Mock(image=object())
        task.screenshot = Mock()
        task.appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=False)
        task.ui_click_until_disappear = Mock()
        task.switch_preset_team = Mock()
        task.last_scene = None
        return task

    def test_offline_return_skips_challenge_even_without_boss_marker(self):
        task = self.make_task()
        task._welfare_no_more_battles = True
        task.appear.side_effect = lambda target, *args, **kwargs: target in (
            task.I_RYOU_DOKAN_CHECK, task.I_RYOU_DOKAN_START_CHALLENGE,
            task.I_RYOU_DOKAN_GATHERING)
        self.assertEqual(task.get_current_scene(),
                         (True, DokanScene.RYOU_DOKAN_SCENE_BOSS_WAITING))
        task.appear_then_click.assert_not_called()

    def test_normal_guild_keeps_challenge_without_boss_marker(self):
        task = self.make_task(False)
        task._welfare_no_more_battles = True
        task.appear.side_effect = lambda target, *args, **kwargs: target in (
            task.I_RYOU_DOKAN_CHECK, task.I_RYOU_DOKAN_START_CHALLENGE)
        task.appear_rgb = Mock(return_value=True)
        with patch('tasks.Dokan.script_task.time.sleep'), \
                patch.object(task.O_DOKAN_BOSS_WAITING, 'ocr') as ocr:
            self.assertEqual(task.get_current_scene(),
                             (True, DokanScene.RYOU_DOKAN_SCENE_START_CHALLENGE))
        ocr.assert_not_called()

    def test_direct_quit_never_asks_for_boss_phase(self):
        task = self.make_task()
        task.config.dokan.dokan_config.dokan_enable = True
        task._welfare_no_more_battles = True
        state = ['lobby']
        events = []
        task.get_current_scene = Mock(side_effect=AssertionError('不应识别馆主阶段'))
        task.appear.side_effect = lambda target, **kwargs: (
            target is task.I_RYOU_DOKAN_CHECK
            or target is task.I_CONTINUE_DOKAN and state[0] == 'vote')

        def click(target, **kwargs):
            if target is task.I_QUIT_DOKAN and state[0] == 'lobby':
                state[0] = 'confirm'
                events.append('quit')
                return True
            if target is task.I_DOKAN_QUIT_CONFIRM and state[0] == 'confirm':
                state[0] = 'vote'
                events.append('confirm')
                return True
            return False

        task.appear_then_click.side_effect = click
        task.quit_dokan(task.config.dokan)
        self.assertEqual(events, ['quit', 'confirm'])
        task.get_current_scene.assert_not_called()
        checked = [call.args[0] for call in task.appear.call_args_list]
        self.assertNotIn(task.I_DOKAN_BOSS_WAITING, checked)
        task.ui_click_until_disappear.assert_not_called()

    def test_delayed_confirmation_never_reclicks_quit(self):
        task = self.make_task()
        task.config.dokan.dokan_config.dokan_enable = True
        task._welfare_no_more_battles = True
        task.appear.side_effect = lambda target, **kwargs: target is task.I_RYOU_DOKAN_CHECK
        events = []

        def click(target, **kwargs):
            if target is task.I_QUIT_DOKAN:
                events.append('quit')
                return True  # 按钮一直可识别，仍只能点击一次。
            if target is task.I_DOKAN_QUIT_CONFIRM and task.screenshot.call_count >= 4:
                events.append('confirm')
                return True
            return False

        task.appear_then_click.side_effect = click
        task.quit_dokan(task.config.dokan)
        for _ in range(5):
            task.quit_dokan(task.config.dokan)
        self.assertEqual(events, ['quit', 'confirm'])
        self.assertEqual(task.screenshot.call_count, 5)
        self.assertTrue(task._dokan_quit_clicked)
        self.assertTrue(task._dokan_quit_confirmed)

    def test_reported_confirmation_popup_must_disappear_before_retry(self):
        task = self.make_task()
        task.config.dokan.dokan_config.dokan_enable = True
        task._welfare_no_more_battles = True
        root = Path(__file__).resolve().parents[1]
        popup = np.zeros((720, 1280, 3), dtype=np.uint8)
        popup[215:505, 420:860] = np.array(Image.open(
            root / 'dev_tools/fixtures/dokan_quit_confirmation.png').convert('RGB'))
        blank = np.zeros_like(popup)
        marker = task.I_DOKAN_QUIT_CONFIRM
        self.assertTrue(marker.match(popup))
        self.assertFalse(marker.match(blank))
        entries = json.loads((root / 'tasks/Dokan/res/image.json').read_text(encoding='utf-8'))
        entry = next(item for item in entries if item['itemName'] == 'dokan_quit_confirm')
        self.assertEqual(tuple(map(int, entry['roiBack'].split(','))), tuple(marker.roi_back))
        frames = iter([blank, popup, popup, blank])
        events = []

        def screenshot():
            task.device.image = next(frames)
            # 确认后仍有一帧弹窗，不能提前标记为完成。
            if task.screenshot.call_count == 3:
                self.assertFalse(task._dokan_quit_confirmed)

        def appear(target, **kwargs):
            if target is marker:
                return marker.match(task.device.image)
            return target is task.I_RYOU_DOKAN_CHECK

        def click(target, **kwargs):
            if target is task.I_QUIT_DOKAN:
                events.append('quit')
                return True
            if target is marker and marker.match(task.device.image):
                events.append('confirm')
                return True
            return False

        task.screenshot.side_effect = screenshot
        task.appear.side_effect = appear
        task.appear_then_click.side_effect = click
        task.quit_dokan(task.config.dokan)
        self.assertEqual(events, ['quit', 'confirm'])
        self.assertEqual(task.screenshot.call_count, 4)
        self.assertTrue(task._dokan_quit_confirmed)
        task.get_current_scene = Mock(side_effect=[
            (True, DokanScene.RYOU_DOKAN_SCENE_FAILED_VOTE_NO),
            (True, DokanScene.RYOU_DOKAN_SCENE_BOSS_WAITING),
            (True, DokanScene.RYOU_DOKAN_SCENE_FAILED_VOTE_NO),
            (False, DokanScene.RYOU_DOKAN_SCENE_FINDING_DOKAN)])
        task.first_open_dokan_time = None
        task.goto_dokan = Mock(side_effect=TaskEnd)

        def retry(target, **kwargs):
            if target is task.I_CONTINUE_DOKAN:
                events.append('retry')
                return True
            self.assertIs(target, task.I_UI_CONFIRM)
            return False

        task.appear_then_click.side_effect = retry
        with patch('tasks.Dokan.script_task.time.sleep'):
            with self.assertRaises(TaskEnd):
                task.dokan_process(task.config.dokan)
        self.assertEqual(events, ['quit', 'confirm', 'retry'])
        task.goto_dokan.assert_called_once_with()

    def test_missing_quit_confirmation_times_out_without_repeating_quit(self):
        task = self.make_task()
        task.config.dokan.dokan_config.dokan_enable = True
        task._dokan_quit_clicked = True
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=[0, 1, 16]):
            with self.assertRaises(GameStuckError):
                task.quit_dokan(task.config.dokan)
        task.appear_then_click.assert_called_once_with(task.I_DOKAN_QUIT_CONFIRM, interval=1)
        self.assertFalse(task._dokan_quit_confirmed)

    def test_retry_transition_does_not_repeat_quit_confirm_or_retry(self):
        task = self.make_task()
        task.config.dokan.dokan_config.dokan_enable = True
        task._welfare_no_more_battles = True
        task._dokan_quit_clicked = True
        task._dokan_quit_confirmed = True
        task.first_open_dokan_time = None
        task.goto_dokan = Mock(side_effect=TaskEnd)
        task.get_current_scene = Mock(side_effect=[
            (True, DokanScene.RYOU_DOKAN_SCENE_FAILED_VOTE_NO),
            (True, DokanScene.RYOU_DOKAN_SCENE_BOSS_WAITING),
            (True, DokanScene.RYOU_DOKAN_SCENE_FAILED_VOTE_NO),
            (True, DokanScene.RYOU_DOKAN_SCENE_BOSS_WAITING),
            (False, DokanScene.RYOU_DOKAN_SCENE_FINDING_DOKAN)])
        task.appear_then_click.side_effect = lambda target, **kwargs: target is task.I_CONTINUE_DOKAN
        with patch('tasks.Dokan.script_task.time.sleep'):
            with self.assertRaises(TaskEnd):
                task.dokan_process(task.config.dokan)
        checked = [call.args[0] for call in task.appear_then_click.call_args_list]
        self.assertEqual(checked, [task.I_UI_CONFIRM, task.I_CONTINUE_DOKAN])
        self.assertTrue(task._dokan_retry_clicked)
        # 离馆刷新不能让旧馆的放弃状态失效；新选馆入口才重置。
        self.assertTrue(task._dokan_quit_confirmed)
        task.goto_dokan.assert_called_once_with()

    def test_same_frame_boss_and_prepare_never_clicks_prepare(self):
        task = self.make_task()
        task.team_switched = True
        task.appear.side_effect = lambda target, **kwargs: target in (
            task.I_DOKAN_BOSS_WAITING, task.I_RYOU_DOKAN_IN_FIELD)
        task.dokan_battle(task.config.dokan)
        task.ui_click_until_disappear.assert_not_called()
        self.assertTrue(task._welfare_no_more_battles)

    def test_blocked_prepare_does_not_switch_team_or_start_battle(self):
        task = self.make_task()
        task._welfare_no_more_battles = True
        task.leave_welfare_prepare = Mock()
        task.dokan_battle(task.config.dokan)
        task.leave_welfare_prepare.assert_called_once_with()
        task.ui_click_until_disappear.assert_not_called()
        task.switch_preset_team.assert_not_called()

    def test_prepare_exit_confirms_lobby_before_returning(self):
        task = self.make_task()
        state = ['prepare']
        events = []
        task.appear.side_effect = lambda target, **kwargs: (
            target is task.I_RYOU_DOKAN_CHECK and state[0] == 'lobby'
            or target is task.I_RYOU_DOKAN_IN_FIELD and state[0] == 'prepare')

        def click(target, **kwargs):
            self.assertIs(target, task.C_DOKAN_BATTLE_QUIT_AREA)
            events.append('exit')
            state[0] = 'confirm'
            return True

        def confirm(target, **kwargs):
            self.assertIs(target, task.I_UI_CONFIRM)
            self.assertEqual(state[0], 'confirm')
            events.append('confirm')
            state[0] = 'lobby'
            return True

        task.click = Mock(side_effect=click)
        task.appear_then_click.side_effect = confirm
        task.leave_welfare_prepare()
        self.assertEqual(events, ['exit', 'confirm'])
        self.assertEqual(task.screenshot.call_count, 3)
        task.ui_click_until_disappear.assert_not_called()

    def test_unknown_prepare_exit_times_out_without_starting_battle(self):
        task = self.make_task()
        task.click = Mock()
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=[0, 16]):
            with self.assertRaises(GameStuckError):
                task.leave_welfare_prepare()
        task.click.assert_not_called()
        task.appear_then_click.assert_not_called()

    def test_blocked_prepare_in_outer_process_returns_without_battle(self):
        task = self.make_task()
        task._welfare_no_more_battles = True
        task.get_current_scene = Mock(side_effect=[
            (True, DokanScene.RYOU_DOKAN_SCENE_IN_FIELD), TaskEnd])
        task.leave_welfare_prepare = Mock()
        task.dokan_battle = Mock()
        with self.assertRaises(TaskEnd):
            task.dokan_process(task.config.dokan)
        task.leave_welfare_prepare.assert_called_once_with()
        task.dokan_battle.assert_not_called()


if __name__ == '__main__':
    unittest.main()
