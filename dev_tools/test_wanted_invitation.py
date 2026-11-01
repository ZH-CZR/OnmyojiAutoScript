"""Replay invitation handling with the open-core Device, without ADB or game input."""
import unittest
import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import cv2

from module.base.timer import Timer
from module.device.device import Device
from module.exception import GameStuckError
from tasks.base_task_parent import BaseTaskParent
from tasks.GlobalGame.config_emergency import FriendInvitation
from tasks.GlobalGame.assets import GlobalGameAssets


class WantedInvitationImageTests(unittest.TestCase):
    """用真实新模板回放公共处理入口，只模拟截图和设备输入。"""

    def setUp(self):
        self.task = BaseTaskParent.__new__(BaseTaskParent)
        self.task.interval_timer = {}
        self.task.device = Device.__new__(Device)
        self.device = self.task.device
        self.device.image = np.full((720, 1280, 3), 90, dtype=np.uint8)
        self.device.detect_record = {'BATTLE_STATUS_S'}
        self.device.stuck_timer = Timer(60, count=60).start()
        self.device.stuck_timer_long = Timer(300, count=300).start()
        self.device.screenshot = Mock(side_effect=self.device.stuck_record_check)
        self.device.app_is_running = Mock(return_value=True)
        self.device.click = Mock(side_effect=self.clicked)
        self.task.config = SimpleNamespace(wanted_quests=SimpleNamespace(
            emergency=SimpleNamespace(friend_invitation=FriendInvitation.ACCEPT)),
            cooperation_store=SimpleNamespace(request=Mock()))
        self.task.set_next_run = Mock()
        self.task.push_notify = Mock()
        for name in ('ACCEPT', 'REJECT', 'IGNORE', 'JADE', 'SUSHI', 'CAT_FOOD', 'DOG_FOOD'):
            key = 'I_G_' + name
            setattr(self.task, key, deepcopy(getattr(GlobalGameAssets, key)))

    def clicked(self, x, y, control_name):
        rule = getattr(self.task, control_name)
        rx, ry, w, h = rule.roi_front
        self.assertTrue(rx <= x < rx + w and ry <= y < ry + h)
        self.device.stuck_record_clear()
        self.device.detect_record.add('INVITATION_BUTTON')
        self.device.image.fill(90)

    def paste(self, name, position=None):
        rule = getattr(self.task, name)
        mat = rule.image
        # 在搜索框内偏移，检查真实匹配后的坐标，而非默认坐标点击。
        x, y = position or (rule.roi_back[0] + 3, rule.roi_back[1] + 3)
        self.device.image[y:y + mat.shape[0], x:x + mat.shape[1]] = mat

    def test_new_images_drive_all_invitation_policies(self):
        cases = [
            (FriendInvitation.ACCEPT, None, 'I_G_ACCEPT'),
            (FriendInvitation.REJECT, None, 'I_G_REJECT'),
            (FriendInvitation.IGNORE, None, 'I_G_IGNORE'),
            (FriendInvitation.ONLY_JADE, 'I_G_JADE', 'I_G_ACCEPT'),
            (FriendInvitation.ONLY_JADE, 'I_G_SUSHI', 'I_G_IGNORE'),
            (FriendInvitation.JADE_SUSHI_FOOD, None, 'I_G_IGNORE'),
        ] + [(FriendInvitation.JADE_SUSHI_FOOD, 'I_G_' + reward, 'I_G_ACCEPT')
             for reward in ('JADE', 'SUSHI', 'CAT_FOOD', 'DOG_FOOD')]
        for policy, reward, button in cases:
            with self.subTest(policy=policy, reward=reward):
                self.setUp()
                self.task.config.wanted_quests.emergency.friend_invitation = policy
                for name in ('I_G_ACCEPT', 'I_G_REJECT', 'I_G_IGNORE'):
                    self.paste(name)
                if reward:
                    self.paste(reward)
                self.assertTrue(self.task._burst())
                self.device.click.assert_called_once()
                self.assertEqual(self.device.click.call_args.kwargs['control_name'], button)
                self.assertEqual(self.device.detect_record,
                                 {'BATTLE_STATUS_S', 'INVITATION_BUTTON'})
                self.assertEqual(self.task.config.cooperation_store.request.call_count,
                                 int(button == 'I_G_ACCEPT'))

    def test_images_at_old_positions_or_rewards_alone_do_not_trigger_invitation(self):
        self.paste('I_G_ACCEPT', (830, 407))
        self.assertFalse(self.task._burst())
        self.device.image.fill(90)
        self.paste('I_G_JADE')
        self.assertFalse(self.task._burst())
        self.device.click.assert_not_called()
        self.device.screenshot.assert_not_called()

    def test_reward_outside_its_region_is_ignored(self):
        self.task.config.wanted_quests.emergency.friend_invitation = FriendInvitation.ONLY_JADE
        self.paste('I_G_ACCEPT')
        self.paste('I_G_IGNORE')
        self.paste('I_G_JADE', (500, 300))
        self.assertTrue(self.task._burst())
        self.assertEqual(self.device.click.call_args.kwargs['control_name'], 'I_G_IGNORE')
        self.task.set_next_run.assert_not_called()
        self.task.config.cooperation_store.request.assert_not_called()

    def test_json_generated_rules_and_template_dimensions_agree(self):
        root = Path(__file__).resolve().parents[1]
        items = json.loads((root / 'tasks/GlobalGame/gg/image.json').read_text('utf-8'))
        for item in items:
            rule = deepcopy(getattr(GlobalGameAssets, 'I_' + item['itemName'].upper()))
            front = tuple(map(int, item['roiFront'].split(',')))
            self.assertEqual(tuple(rule.roi_front), front)
            self.assertEqual(tuple(rule.roi_back), tuple(map(int, item['roiBack'].split(','))))
            self.assertEqual((rule.image.shape[1], rule.image.shape[0]), front[2:])
            self.assertEqual(tuple(rule.roi_front), front)
            self.assertEqual(rule.threshold, item['threshold'])
            self.assertEqual(rule.method, item['method'])


@unittest.skipUnless(os.environ.get('WANTED_INVITATION_REPLAY_IMAGE'),
                     'Set WANTED_INVITATION_REPLAY_IMAGE to a local jade invitation screenshot')
class WantedInvitationScreenshotTests(unittest.TestCase):
    """用户原图只从本地显式传入，不将截图或昵称提交到仓库。"""

    def test_jade_invitation_through_public_screenshot_entry(self):
        path = os.environ['WANTED_INVITATION_REPLAY_IMAGE']
        image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(image)
        self.assertEqual(image.shape[:2], (720, 1280))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        expected = {
            FriendInvitation.ACCEPT: 'I_G_ACCEPT',
            FriendInvitation.REJECT: 'I_G_REJECT',
            FriendInvitation.IGNORE: 'I_G_IGNORE',
            FriendInvitation.ONLY_JADE: 'I_G_ACCEPT',
            FriendInvitation.JADE_SUSHI_FOOD: 'I_G_ACCEPT',
        }
        for policy, button in expected.items():
            with self.subTest(policy=policy):
                replay = WantedInvitationImageTests()
                replay.setUp()
                replay.device.image = image.copy()
                replay.task.config.config_reload_event = None
                replay.task.config.wanted_quests.emergency.friend_invitation = policy
                self.assertTrue(replay.task.appear(replay.task.I_G_JADE))
                replay.task.screenshot()
                replay.device.click.assert_called_once()
                self.assertEqual(replay.device.click.call_args.kwargs['control_name'], button)
                self.assertEqual(replay.task.config.cooperation_store.request.call_count, int(button == 'I_G_ACCEPT'))
                self.assertIn('BATTLE_STATUS_S', replay.device.detect_record)
                self.assertFalse(replay.task.appear(replay.task.I_G_ACCEPT))
                self.assertFalse(replay.task.appear(replay.task.I_G_REJECT))


class WantedInvitationTests(unittest.TestCase):
    def setUp(self):
        self.task = BaseTaskParent.__new__(BaseTaskParent)
        self.device = Device.__new__(Device)
        self.task.device = self.device
        self.device.detect_record = {'BATTLE_STATUS_S'}
        self.device.stuck_timer = Timer(60, count=60).start()
        self.device.stuck_timer_long = Timer(300, count=300).start()
        self.device.screenshot = Mock(side_effect=self.device.stuck_record_check)
        self.device.app_is_running = Mock(return_value=True)
        self.task.config = SimpleNamespace(wanted_quests=SimpleNamespace(
            emergency=SimpleNamespace(friend_invitation=FriendInvitation.ONLY_JADE)),
            cooperation_store=SimpleNamespace(request=Mock()))
        self.visible = {self.task.I_G_ACCEPT.name}
        self.task.appear = Mock(side_effect=lambda target: target.name in self.visible)
        self.task.appear_then_click = Mock(side_effect=self.click_invitation)
        self.task.set_next_run = Mock()
        self.task.push_notify = Mock()

    def click_invitation(self, target, **kwargs):
        # Real input clears both waiting records and timers.
        self.device.stuck_record_clear()
        self.device.detect_record.add('INVITATION_BUTTON')
        self.visible.clear()
        return True

    def test_all_invitation_policies_use_current_device_interface(self):
        cases = [
            (FriendInvitation.ACCEPT, None, 'I_G_ACCEPT'),
            (FriendInvitation.REJECT, None, 'I_G_REJECT'),
            (FriendInvitation.IGNORE, None, 'I_G_IGNORE'),
            (FriendInvitation.ONLY_JADE, 'I_G_JADE', 'I_G_ACCEPT'),
            (FriendInvitation.ONLY_JADE, None, 'I_G_IGNORE'),
            (FriendInvitation.JADE_SUSHI_FOOD, None, 'I_G_IGNORE'),
        ] + [(FriendInvitation.JADE_SUSHI_FOOD, reward, 'I_G_ACCEPT') for reward in (
            'I_G_JADE', 'I_G_CAT_FOOD', 'I_G_DOG_FOOD', 'I_G_SUSHI')]
        for policy, reward, button_name in cases:
            with self.subTest(policy=policy, reward=reward):
                self.task.config.wanted_quests.emergency.friend_invitation = policy
                button = getattr(self.task, button_name)
                self.visible = {self.task.I_G_ACCEPT.name, button.name}
                if reward:
                    self.visible.add(getattr(self.task, reward).name)
                self.task.appear_then_click.reset_mock()
                self.task.config.cooperation_store.request.reset_mock()
                self.assertTrue(self.task._burst())
                self.task.appear_then_click.assert_called_once_with(button, interval=0.8)
                self.assertIn('BATTLE_STATUS_S', self.device.detect_record)
                self.assertIn('INVITATION_BUTTON', self.device.detect_record)
                self.assertNotIn('stuck_timeout', self.device.__dict__)
                self.task.set_next_run.assert_not_called()
                if button_name == 'I_G_ACCEPT':
                    self.task.config.cooperation_store.request.assert_called_once_with('wanted_quests')
                else:
                    self.task.config.cooperation_store.request.assert_not_called()

    def test_no_invitation_does_not_change_wait_state(self):
        self.visible.clear()
        timers = (self.device.stuck_timer._current, self.device.stuck_timer_long._current)
        self.assertFalse(self.task._burst())
        self.assertEqual(self.device.detect_record, {'BATTLE_STATUS_S'})
        self.assertEqual(timers, (self.device.stuck_timer._current,
                                  self.device.stuck_timer_long._current))
        self.device.screenshot.assert_not_called()
        self.task.set_next_run.assert_not_called()
        self.task.config.cooperation_store.request.assert_not_called()

    def test_wait_marker_restored_when_invitation_processing_raises(self):
        def fail_click(*args, **kwargs):
            self.device.stuck_record_clear()
            raise RuntimeError('input failed')

        self.visible.add(self.task.I_G_IGNORE.name)
        self.task.appear_then_click.side_effect = fail_click
        with self.assertRaisesRegex(RuntimeError, 'input failed'):
            self.task._burst()
        self.assertIn('BATTLE_STATUS_S', self.device.detect_record)
        self.task.set_next_run.assert_not_called()
        self.task.config.cooperation_store.request.assert_not_called()

    def test_long_battle_still_waits_after_invitation_click(self):
        self.visible.add(self.task.I_G_IGNORE.name)
        with patch('module.base.timer.time.time', return_value=1000):
            self.assertTrue(self.task._burst())
        self.device.stuck_timer._reach_count = 61
        with patch('module.base.timer.time.time', return_value=1061):
            self.assertFalse(self.device.stuck_record_check())
        self.device.app_is_running.assert_not_called()
        self.device.stuck_timer_long._reach_count = 301
        with patch('module.base.timer.time.time', return_value=1301):
            with self.assertRaises(GameStuckError):
                self.device.stuck_record_check()

    def test_invitation_loop_keeps_stuck_detection_enabled(self):
        self.device.detect_record.clear()
        self.device.stuck_timer._current = 1000
        self.device.stuck_timer._reach_count = 61
        self.device.stuck_timer_long._current = 1000
        with patch('module.base.timer.time.time', return_value=1061):
            with self.assertRaises(GameStuckError):
                self.task._burst()
        self.task.appear_then_click.assert_not_called()
        self.task.set_next_run.assert_not_called()
        self.task.config.cooperation_store.request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
