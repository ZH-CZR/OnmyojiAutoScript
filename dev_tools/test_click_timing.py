"""Offline checks for bounded settlement bursts, timing and raid delay wiring."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from module.atom.click import RuleClick
from tasks.base_task_parent import BaseTaskParent
from tasks.Script.config import Script as ScriptConfig


class ClickTimingTest(unittest.TestCase):
    def task(self):
        task = BaseTaskParent.__new__(BaseTaskParent)
        task.config = SimpleNamespace(script=ScriptConfig())
        task.device = SimpleNamespace(click=Mock(), long_click=Mock())
        task._is_click_interval_ready = Mock(return_value=True)
        task._settlement_markers = Mock(return_value=['reward'])
        task.screenshot = Mock()
        task.appear = Mock(return_value=True)
        return task

    def action(self, count=3):
        action = RuleClick((10, 10, 30, 30), (10, 10, 30, 30), name='SETTLEMENT_RANDOM_CLICK')
        action.burst_count = count
        action.burst_interval = (.1, .2)
        return action

    def test_settlement_burst_rechecks_and_resamples_each_extra_click(self):
        task = self.task()
        action = self.action()
        action.coord = Mock(side_effect=[(10, 10), (11, 11), (12, 12)])
        with patch('tasks.base_task_parent.sleep') as sleep:
            task.click(action)
        self.assertEqual(task.device.click.call_count, 3)
        self.assertEqual(task.screenshot.call_count, 2)
        self.assertEqual(action.coord.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        for call in sleep.call_args_list:
            self.assertTrue(.1 <= call.args[0] <= .2)

    def test_burst_stops_when_original_settlement_disappears(self):
        task = self.task()
        task.appear.side_effect = [True, False]
        with patch('tasks.base_task_parent.sleep'):
            task.click(self.action())
        self.assertEqual(task.device.click.call_count, 2)

    def test_unknown_page_cannot_burst(self):
        task = self.task()
        task._settlement_markers.return_value = []
        task.click(self.action())
        self.assertEqual(task.device.click.call_count, 1)

    def test_switch_off_and_unmarked_action_never_burst(self):
        for enabled, name in ((False, 'SETTLEMENT_RANDOM_CLICK'), (True, 'normal')):
            task = self.task()
            task.config.script.anti_ban.settlement_burst_enable = enabled
            action = self.action()
            action.name = name
            task.click(action)
            self.assertEqual(task.device.click.call_count, 1)
            task._settlement_markers.assert_not_called()

    def test_burst_has_hard_cap_and_respects_interval_gate(self):
        task = self.task()
        with patch('tasks.base_task_parent.sleep'):
            task.click(self.action(99))
        self.assertEqual(task.device.click.call_count, 3)
        task.device.click.reset_mock()
        task._is_click_interval_ready.return_value = False
        task.click(self.action())
        task.device.click.assert_not_called()

    def test_screenshot_pauses_only_on_known_settlement_and_returns_fresh_frame(self):
        task = self.task()
        del task.screenshot
        task.config.config_reload_event = None
        task.device.activity_guard = SimpleNamespace(pending=True)
        frames = iter(['old', 'fresh'])
        def shot():
            task.device.image = next(frames)
        task.device.screenshot = Mock(side_effect=shot)
        task._burst = Mock()
        task.runtime_checkpoint = Mock(return_value=True)
        self.assertEqual(task.screenshot(), 'fresh')
        task.runtime_checkpoint.assert_called_once()
        task.device.screenshot.assert_has_calls([unittest.mock.call(), unittest.mock.call()])
        task.device.screenshot.reset_mock()
        task.device.screenshot.side_effect = None
        task._settlement_markers.return_value = []
        task.runtime_checkpoint.reset_mock()
        task.screenshot()
        task.runtime_checkpoint.assert_not_called()

    def test_public_click_timing_can_be_disabled(self):
        from module.device.control import Control
        cfg = SimpleNamespace(script=ScriptConfig())
        tap = Mock()
        device = SimpleNamespace(config=cfg, handle_control_check=Mock(),
                                 _invalidate_image_batch_cache=Mock(), click_methods={'minitouch': tap},
                                 click_adb=Mock(), _format_action_duration=lambda x: '')
        for enabled in (True, False):
            cfg.script.anti_ban.click_timing_enable = enabled
            with patch('module.device.control.time.sleep') as wait:
                Control.click(device, 20, 30)
                self.assertEqual(wait.call_count, int(enabled))
                if enabled:
                    self.assertTrue(.06 <= wait.call_args.args[0] <= .18)
        self.assertEqual(tap.call_count, 2)

    def test_minitouch_press_duration_is_explicit_and_bounded(self):
        from module.device.method.minitouch import Minitouch
        cfg = SimpleNamespace(script=ScriptConfig())
        builder = Mock()
        builder.down.return_value = builder
        builder.up.return_value = builder
        builder.commit.return_value = builder
        device = SimpleNamespace(config=cfg, minitouch_builder=builder, minitouch_send=Mock())
        Minitouch.click_minitouch.__wrapped__(device, 10, 20)
        self.assertTrue(40 <= builder.wait.call_args.args[0] <= 110)
        cfg.script.anti_ban.click_timing_enable = False
        builder.reset_mock()
        Minitouch.click_minitouch.__wrapped__(device, 10, 20)
        builder.wait.assert_not_called()

    def test_raid_delay_switch_rechecks_area_after_wait(self):
        from tasks.RyouToppa.script_task import ScriptTask
        from tasks.RyouToppa.config import RaidConfig
        for interval, bounds in (('2,10', (2, 10)), ('12,20', (12, 20)), ('7,7', (7, 7)), ('0,0', (0, 0))):
            with self.subTest(interval=interval):
                task = ScriptTask.__new__(ScriptTask)
                task.config = SimpleNamespace(ryou_toppa=SimpleNamespace(
                    raid_config=RaidConfig(random_delay=True, random_delay_interval=interval)))
                task.check_area = Mock(side_effect=[True, False])
                task.screenshot = Mock()
                with patch('tasks.RyouToppa.script_task.time.sleep') as sleep:
                    self.assertFalse(task.attack_area(0))
                seconds = sleep.call_args.args[0]
                self.assertIsInstance(seconds, int)
                self.assertTrue(bounds[0] <= seconds <= bounds[1])
                self.assertEqual(task.check_area.call_count, 2)
                task.screenshot.assert_called_once()

    def test_raid_delay_interval_validation_and_legacy_defaults(self):
        from pydantic import ValidationError
        from tasks.RyouToppa.config import RaidConfig
        self.assertEqual(RaidConfig(random_delay=True).random_delay_interval, '2,10')
        self.assertEqual(RaidConfig(random_delay_interval=' 3， 15 ').random_delay_interval, '3,15')
        for invalid in ('10,2', '-1,2', '1.5,3', '', '2', '1,2,3'):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                RaidConfig(random_delay_interval=invalid)

    def test_disabled_raid_delay_does_not_wait(self):
        from tasks.RyouToppa.script_task import ScriptTask
        from tasks.RyouToppa.config import RaidConfig
        task = ScriptTask.__new__(ScriptTask)
        task.config = SimpleNamespace(ryou_toppa=SimpleNamespace(raid_config=RaidConfig(random_delay=False)))
        task.check_area = Mock(return_value=True)
        task.screenshot = Mock(side_effect=RuntimeError('stop before device input'))
        with patch('tasks.RyouToppa.script_task.time.sleep') as sleep, self.assertRaises(RuntimeError):
            task.attack_area(0)
        sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
