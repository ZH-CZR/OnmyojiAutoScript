"""Replay invitation handling with the open-core Device, without ADB or game input."""
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.base.timer import Timer
from module.device.device import Device
from module.exception import GameStuckError
from tasks.base_task_parent import BaseTaskParent
from tasks.GlobalGame.config_emergency import FriendInvitation


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
            emergency=SimpleNamespace(friend_invitation=FriendInvitation.ONLY_JADE)))
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
                self.task.set_next_run.reset_mock()
                self.assertTrue(self.task._burst())
                self.task.appear_then_click.assert_called_once_with(button, interval=0.8)
                self.assertIn('BATTLE_STATUS_S', self.device.detect_record)
                self.assertIn('INVITATION_BUTTON', self.device.detect_record)
                self.assertNotIn('stuck_timeout', self.device.__dict__)
                if button_name == 'I_G_ACCEPT':
                    self.task.set_next_run.assert_called_once()
                    call = self.task.set_next_run.call_args.kwargs
                    self.assertEqual(call['task'], 'WantedQuests')
                    self.assertIsInstance(call['target'], datetime)
                    self.assertEqual(call['target'].microsecond, 0)
                else:
                    self.task.set_next_run.assert_not_called()

    def test_no_invitation_does_not_change_wait_state(self):
        self.visible.clear()
        timers = (self.device.stuck_timer._current, self.device.stuck_timer_long._current)
        self.assertFalse(self.task._burst())
        self.assertEqual(self.device.detect_record, {'BATTLE_STATUS_S'})
        self.assertEqual(timers, (self.device.stuck_timer._current,
                                  self.device.stuck_timer_long._current))
        self.device.screenshot.assert_not_called()
        self.task.set_next_run.assert_not_called()

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


if __name__ == '__main__':
    unittest.main()
