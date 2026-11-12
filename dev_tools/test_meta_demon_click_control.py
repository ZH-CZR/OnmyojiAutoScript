"""Real click/recognition methods with a virtual clock; no game or device."""
import unittest
import numpy as np
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.atom.click import RuleClick
from module.exception import GameStuckError
from tasks.base_task_parent import BaseTaskParent
from tasks.MetaDemon.click_control import MetaDemonClickControl
from tasks.MetaDemon.script_task import ScriptTask


class ReplayBackend(BaseTaskParent):
    def screenshot(self):
        self.now += self.tick
        self.events.append(('screenshot', self.now))
        self.device.image = int(self.changed and self.now >= self.changed_at)
        return self.device.image


class ReplayTask(MetaDemonClickControl, ReplayBackend):
    pass


class MetaDemonClickControlTest(unittest.TestCase):
    def task(self, changed=False, cls=ReplayTask):
        task = cls.__new__(cls)
        task.now = 1000
        task.tick = 0
        task.changed_at = 1000.2
        task.events = []
        task.changed = changed
        task.interval_timer = {}
        task.device = SimpleNamespace(image=0, click=Mock(side_effect=lambda *a, **k:
            task.events.append(('click', task.now))))
        return task

    def clock(self, task):
        stack = ExitStack()
        def sleep(seconds):
            task.events.append(('wait', seconds))
            task.now += seconds
        stack.enter_context(patch('tasks.MetaDemon.click_control.time.sleep', side_effect=sleep))
        stack.enter_context(patch('module.base.timer.time.time', side_effect=lambda: task.now))
        stack.enter_context(patch('tasks.MetaDemon.click_control.time.monotonic', side_effect=lambda: task.now))
        return stack

    def button(self, name='button', visible=True):
        return SimpleNamespace(name=name, match=lambda image, **kw: visible and image == 0,
                               coord=lambda: (10, 20))

    def test_unchanged_page_retries_only_after_two_seconds(self):
        task = self.task()
        button = self.button()
        with self.clock(task):
            self.assertTrue(task.appear_then_click(button, interval=None))
            self.assertEqual(task.now, 1000)
            task.now = 1000.2
            self.assertFalse(task.appear_then_click(button, interval=None))
            task.now = 1001.99
            self.assertFalse(task.appear_then_click(button, interval=None))
            task.now = 1002
            self.assertTrue(task.appear_then_click(button, interval=None))
        self.assertEqual([t for event, t in task.events if event == 'click'], [1000, 1002])
        self.assertFalse(any(event == 'wait' for event, _ in task.events))

    def test_changed_page_never_reclicks_old_button_without_waiting_two_seconds(self):
        task = self.task(changed=True)
        button = self.button()
        with self.clock(task):
            self.assertTrue(task.appear_then_click(button, interval=None))
            task.now = 1000.2
            self.assertFalse(task.appear_then_click(button, interval=None))
        task.device.click.assert_called_once()
        self.assertEqual(task.now, 1000.2)
        self.assertFalse(any(event == 'wait' for event, _ in task.events))

    def test_new_page_button_can_click_at_point_two_seconds(self):
        task = self.task(changed=True)
        with self.clock(task):
            task.appear_then_click(self.button('first'), interval=None)
            task.now = 1000.2
            next_button = self.button('next')
            next_button.match = lambda image, **kw: image == 1
            self.assertTrue(task.appear_then_click(next_button, interval=None))
        self.assertEqual([t for event, t in task.events if event == 'click'], [1000, 1000.2])

    def test_other_existing_button_on_unchanged_page_cannot_bypass_interval(self):
        task = self.task()
        with self.clock(task):
            task.appear_then_click(self.button('first'), interval=None)
            task.now = 1000.2
            self.assertFalse(task.appear_then_click(self.button('second'), interval=None))
            task.now = 1002
            self.assertTrue(task.appear_then_click(self.button('second'), interval=None))
        self.assertEqual([t for event, t in task.events if event == 'click'], [1000, 1002])

    def test_failed_recognition_does_not_wait(self):
        task = self.task()
        with self.clock(task):
            self.assertFalse(task.appear_then_click(self.button(visible=False), interval=None))
        self.assertEqual(task.events, [])

    def test_background_noise_does_not_release_repeat_interval(self):
        task = self.task()
        task.device.image = np.zeros((720, 1280, 3), dtype=np.uint8)
        button = self.button()
        button.match = lambda image, **kw: True
        with self.clock(task):
            task.appear_then_click(button, interval=None)
            task._meta_click_needs_screenshot = False
            task.device.image[0:20, 0:100] = 255
            task.now = 1000.2
            self.assertFalse(task.appear_then_click(button, interval=None))
        task.device.click.assert_called_once()

    def test_same_named_button_on_changed_page_can_click_immediately(self):
        task = self.task()
        task.device.image = np.zeros((720, 1280, 3), dtype=np.uint8)
        button = self.button()
        button.match = lambda image, **kw: True
        with self.clock(task):
            task.appear_then_click(button, interval=None)
            task._meta_click_needs_screenshot = False
            task.device.image[:] = 255
            task.now = 1000.2
            self.assertTrue(task.appear_then_click(button, interval=None))
        self.assertEqual([t for event, t in task.events if event == 'click'], [1000, 1000.2])

    def test_coordinate_click_does_not_sleep_and_next_recognition_refreshes(self):
        task = self.task(changed=True)
        with self.clock(task):
            task._meta_click(100, 200, control_name='MD_PRESET_APPLY')
            self.assertEqual(task.now, 1000)
            task.now = 1000.2
            self.assertFalse(task.appear(self.button()))
        self.assertEqual(task.events, [('click', 1000), ('screenshot', 1000.2)])

    def test_repeated_coordinate_click_polls_and_cancels_when_page_changes(self):
        task = self.task(changed=True)
        with self.clock(task):
            task._meta_click(100, 200, control_name='repeat')
            self.assertFalse(task._meta_click(100, 200, control_name='repeat'))
        task.device.click.assert_called_once()
        self.assertLess(task.now, 1002)

    def test_repeated_coordinate_click_waits_remaining_interval_on_same_page(self):
        task = self.task()
        with self.clock(task):
            task._meta_click(100, 200, control_name='repeat')
            self.assertTrue(task._meta_click(100, 200, control_name='repeat'))
        self.assertEqual([t for event, t in task.events if event == 'click'], [1000, 1002])

    def test_explicit_screenshot_prevents_duplicate_refresh(self):
        task = self.task()
        with self.clock(task):
            task._meta_click(100, 200)
            task.screenshot()
            self.assertTrue(task.appear(self.button()))
        self.assertEqual(sum(e[0] == 'screenshot' for e in task.events), 1)

    def test_screenshot_marker_checks_do_not_recurse(self):
        button = self.button()
        class MarkerBackend(ReplayBackend):
            def screenshot(self):
                image = super().screenshot()
                self.appear(button)  # Base screenshot checks settlement markers.
                return image
        class MarkerTask(MetaDemonClickControl, MarkerBackend):
            pass
        task = self.task(cls=MarkerTask)
        with self.clock(task):
            task._meta_click(100, 200)
            self.assertTrue(task.appear(button))
        self.assertEqual(sum(e[0] == 'screenshot' for e in task.events), 1)

    def test_click_without_interval_records_retry_when_base_returns_false(self):
        task = self.task()
        click = RuleClick((10, 20, 5, 5), (10, 20, 5, 5), name='test')
        with self.clock(task):
            self.assertFalse(task.click(click))
        task.device.click.assert_called_once()
        self.assertEqual(task.now, 1000)

    def test_interval_rejection_does_not_click_or_wait(self):
        task = self.task()
        task._is_click_interval_ready = Mock(return_value=False)
        with self.clock(task):
            self.assertFalse(task.click(RuleClick((10, 20, 5, 5), (10, 20, 5, 5)), interval=3))
        self.assertEqual(task.events, [])

    def test_settlement_burst_is_one_click_without_mutating_shared_rule(self):
        task = self.task()
        click = RuleClick((10, 20, 5, 5), (10, 20, 5, 5), name='SETTLEMENT_RANDOM_CLICK')
        click.burst_count = 3
        with self.clock(task):
            task.click(click)
        task.device.click.assert_called_once()
        self.assertEqual(click.burst_count, 3)

    def test_other_tasks_keep_existing_click_behavior(self):
        task = self.task(cls=ReplayBackend)
        with self.clock(task):
            task.appear_then_click(self.button(), interval=None)
            task.appear_then_click(self.button(), interval=None)
        self.assertEqual(task.events, [('click', 1000), ('click', 1000)])

    def test_retry_waits_do_not_extend_start_battle_deadline(self):
        task = self.task()
        task.tick = 0.1
        task.I_MD_FIRE = self.button('fire')
        task.I_MD_DRINK_TEA = self.button('tea', visible=False)
        task.is_in_prepare = Mock(return_value=False)
        task.is_in_battle = Mock(return_value=False)
        with self.clock(task), self.assertRaisesRegex(GameStuckError, '15秒'):
            ScriptTask.start_battle(task)
        clicks = [t for event, t in task.events if event == 'click']
        self.assertGreater(len(clicks), 1)
        self.assertTrue(all(b-a >= 2 for a,b in zip(clicks, clicks[1:])))
        self.assertGreaterEqual(task.now, 1015)
        self.assertLess(task.now, 1016)


if __name__ == '__main__':
    unittest.main()
