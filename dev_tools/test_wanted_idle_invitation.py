"""Idle invitation polling, with real matching and simulated device IO only."""
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import unittest
import os

import cv2
import numpy as np

from dev_tools import test_wanted_invitation as invitation_tests
from module.config.config import Config
from module.config.manual import CooperationStore, ManualStore
from module.exception import GameStuckError
from module.script import ScriptRuntimeController
from script import Script
from tasks.GlobalGame.config_emergency import FriendInvitation


class IdleInvitationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner = Script.__new__(Script)
        self.runner.config_name = 'template'
        config = Config('template')
        config.cooperation_store = CooperationStore('idle', Path(self.temp.name) / 'cooperation.sqlite3')
        config.manual_store = ManualStore('idle', Path(self.temp.name) / 'manual.sqlite3')
        config.wanted_quests.emergency.friend_invitation = FriendInvitation.ACCEPT
        self.runner.__dict__['config'] = config
        self.runner._emulator_down = False
        self.runtime = ScriptRuntimeController(self.runner)
        self.runner.runtime = self.runtime
        self.runtime.idle_waiting = True
        replay = invitation_tests.WantedInvitationImageTests()
        replay.setUp()
        self.replay = replay
        self.runner.__dict__['device'] = replay.device
        replay.device.release_during_wait = Mock()
        replay.device.app_is_running.return_value = True
        # Keep the real _burst, appear and input path; only image/input are fake.
        self.runtime._idle_invitation_handler = replay.task
        for name in ('I_G_ACCEPT', 'I_G_REJECT', 'I_G_IGNORE', 'I_G_JADE'):
            replay.paste(name)

    def test_idle_wait_accepts_then_wakes_scheduler_without_navigation(self):
        original_next_run = self.runner.config.wanted_quests.scheduler.next_run
        self.runner.prepare_main_page = Mock()
        self.assertFalse(self.runner.wait_until(datetime.now() + timedelta(minutes=5)))
        self.replay.device.click.assert_called_once()
        self.assertEqual(self.replay.device.click.call_args.kwargs['control_name'], 'I_G_ACCEPT')
        self.assertIn('wanted_quests', self.runner.config.cooperation_store.pending())
        self.assertEqual(self.runner.config.wanted_quests.scheduler.next_run, original_next_run)
        self.runner.prepare_main_page.assert_not_called()
        self.replay.device.release_during_wait.assert_called_once()
        self.runner.config.get_next()
        self.assertEqual(self.runner.config.task.command, 'WantedQuests')

    @unittest.skipUnless(os.environ.get('WANTED_INVITATION_REPLAY_IMAGE'), 'No local invitation screenshot')
    def test_original_screenshot_through_idle_wait(self):
        image = cv2.imdecode(np.fromfile(os.environ['WANTED_INVITATION_REPLAY_IMAGE'], dtype=np.uint8),
                             cv2.IMREAD_COLOR)
        self.assertIsNotNone(image)
        self.replay.device.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.test_idle_wait_accepts_then_wakes_scheduler_without_navigation()

    def test_reject_and_ignore_do_not_schedule(self):
        for policy, button in ((FriendInvitation.REJECT, 'I_G_REJECT'),
                               (FriendInvitation.IGNORE, 'I_G_IGNORE')):
            with self.subTest(policy=policy):
                self.runner.config.wanted_quests.emergency.friend_invitation = policy
                for name in ('I_G_ACCEPT', 'I_G_REJECT', 'I_G_IGNORE'):
                    self.replay.paste(name)
                self.replay.device.click.reset_mock()
                self.assertTrue(self.runtime.poll_idle_invitation())
                self.assertEqual(self.replay.device.click.call_args.kwargs['control_name'], button)
                self.assertEqual(self.runner.config.cooperation_store.pending(), {})

    def test_closed_emulator_maintenance_and_non_idle_wait_never_capture(self):
        for condition in ('emulator', 'maintenance', 'non_idle'):
            with self.subTest(condition=condition):
                self.runner._emulator_down = condition == 'emulator'
                self.runtime.idle_waiting = condition != 'non_idle'
                self.runtime.server_update_wait_until = (
                    datetime.now() + timedelta(minutes=10) if condition == 'maintenance' else None)
                self.assertFalse(self.runtime.poll_idle_invitation())
                self.replay.device.app_is_running.assert_not_called()
                self.replay.device.screenshot.assert_not_called()

    def test_missing_device_or_closed_game_never_launches(self):
        device = self.runner.__dict__.pop('device')
        with patch('module.script.runtime_controller.Device') as create:
            self.assertFalse(self.runtime.poll_idle_invitation())
            create.assert_not_called()
        self.runner.__dict__['device'] = device
        device.app_is_running.return_value = False
        self.assertFalse(self.runtime.poll_idle_invitation())
        device.screenshot.assert_not_called()
        device.click.assert_not_called()

    def test_idle_staleness_does_not_trigger_false_stuck_but_handling_failure_propagates(self):
        device = self.replay.device
        device.stuck_timer._current = 0
        device.stuck_timer._reach_count = 61
        device.stuck_timer_long._current = 0
        device.stuck_timer_long._reach_count = 301
        self.assertTrue(self.runtime.poll_idle_invitation())
        device.screenshot.side_effect = GameStuckError('screenshot failure')
        with self.assertRaises(GameStuckError):
            self.runtime.poll_idle_invitation()
        self.assertEqual(device.release_during_wait.call_count, 2)

    def test_wait_polls_at_five_second_intervals_and_rebinds_latest_config(self):
        self.replay.device.image.fill(90)
        elapsed = [0]
        start = datetime.now()
        def advance(seconds):
            elapsed[0] += seconds
        with ExitStack() as stack:
            clock = stack.enter_context(patch('script.datetime'))
            clock.now.side_effect = lambda: start + timedelta(seconds=elapsed[0])
            stack.enter_context(patch('script.time.sleep', side_effect=advance))
            stack.enter_context(patch('script.time.monotonic', side_effect=lambda: elapsed[0]))
            self.assertTrue(self.runner.wait_until(start + timedelta(seconds=14)))
        self.assertEqual(self.replay.device.screenshot.call_count, 4)  # 0, 5, 10, 15
        self.replay.device.click.assert_not_called()
        self.assertIs(self.runtime._idle_invitation_handler.config, self.runner.config)

    def test_pending_cooperation_does_not_spin_during_maintenance(self):
        self.runner.config.cooperation_store.request('wanted_quests')
        start = datetime.now()
        self.runtime.server_update_wait_until = start + timedelta(hours=1)
        with patch('script.datetime') as clock, patch('script.time.sleep') as sleep:
            clock.now.side_effect = [start, start + timedelta(seconds=3)]
            self.assertTrue(self.runner.wait_until(start + timedelta(seconds=1)))
        sleep.assert_called_once_with(1)
        self.replay.device.app_is_running.assert_not_called()
        self.assertTrue(self.runner.config.cooperation_store.pending())

    def test_idle_flag_is_cleared_even_if_waiting_fails(self):
        self.runtime.idle_waiting = False
        self.runner.config.script.optimization.when_task_queue_empty = 'goto_main'
        with patch.object(self.runtime, '_wait_goto_main', side_effect=GameStuckError('failed')):
            with self.assertRaises(GameStuckError):
                self.runtime.handle_wait_during_idle(datetime.now() + timedelta(minutes=1))
        self.assertFalse(self.runtime.idle_waiting)


if __name__ == '__main__':
    unittest.main()
