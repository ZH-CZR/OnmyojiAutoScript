"""单人结契挂饼离线回放；不创建或连接游戏设备。"""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image
from pydantic import ValidationError

from module.base.timer import Timer
from module.exception import GameStuckError, TaskEnd
from module.device.device import Device
from module.config.config_model import ConfigModel
from tasks.BondlingFairyland.config import BondlingConfig, UserStatus
from tasks.BondlingFairyland.script_task import ScriptTask
from tasks.BondlingFairyland.sakura import BondlingSakura


ROOT = Path(__file__).resolve().parents[1]


class BondlingSakuraTests(unittest.TestCase):
    def test_count_range_normalization_and_old_config(self):
        for value, expected in [(30, '30,30'), ('8', '8,8'), (' 2， 5 ', '2,5'),
                                ('0,0', '0,0'), ('3,3', '3,3')]:
            with self.subTest(value=value):
                self.assertEqual(BondlingConfig(limit_count=value).limit_count, expected)
        for value in ['5,2', '-1,3', '2.5,3', '1,2,3', '', 'a,b', True, 3.0, None]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                BondlingConfig(limit_count=value)

    def test_fixed_count_does_not_roll_and_range_rolls_once(self):
        task = ScriptTask.__new__(ScriptTask)
        with patch('tasks.BondlingFairyland.script_task.random.randint') as roll:
            task.select_bondling_count_limit(BondlingConfig(limit_count='4,4'))
            self.assertEqual(task.limit_count, 4)
            roll.assert_not_called()
        for selected in [3, 6]:
            cfg = BondlingConfig(limit_count='3,6')
            with patch('tasks.BondlingFairyland.script_task.random.randint', return_value=selected) as roll:
                task.select_bondling_count_limit(cfg)
                task.current_count = selected
                task.lock_team = Mock()
                task.in_search_ui = Mock(return_value=True)
                # Runtime checks use the selected integer, never compare the
                # configured text or roll again during a checkpoint/reload.
                cfg.limit_count = '10,20'
                self.assertFalse(task.run_search(cfg))
                self.assertEqual(task.limit_count, selected)
                roll.assert_called_once_with(3, 6)

    def test_count_range_api_is_text_and_rejects_invalid_save(self):
        model = ConfigModel()
        fields = model.script_task('BondlingFairyland')['bondling_config']
        count = next(field for field in fields if field['name'] == 'limit_count')
        self.assertEqual(count['type'], 'string')
        with patch.object(ConfigModel, 'save') as save:
            self.assertTrue(model.script_set_arg('BondlingFairyland', 'bondling_config', 'limit_count', '2,5'))
            self.assertEqual(model.bondling_fairyland.bondling_config.limit_count, '2,5')
            save.assert_called_once()
            save.reset_mock()
            self.assertFalse(model.script_set_arg('BondlingFairyland', 'bondling_config', 'limit_count', '5,2'))
            self.assertEqual(model.bondling_fairyland.bondling_config.limit_count, '2,5')
            save.assert_not_called()

    def test_supplied_circle_samples_and_animation_rotation(self):
        task = BondlingSakura()
        for filename, expected in [('auto_off.png', False), ('auto_off_stopped_sample.png', False),
                                   ('auto_on_sample.png', True)]:
            circle = np.array(Image.open(ROOT / 'tasks/BondlingFairyland/sakura' / filename))
            for rotation in range(4):
                image = np.zeros((720, 1280, 3), dtype=np.uint8)
                image[638:670, 786:818] = np.rot90(circle, rotation)
                task.device = SimpleNamespace(image=image)
                self.assertIs(task.bondling_sakura_state(), expected)
        task.device.image[:] = 0
        self.assertIsNone(task.bondling_sakura_state())

    def test_real_stopped_circle_and_minor_color_noise(self):
        task = BondlingSakura()
        circle = np.array(Image.open(ROOT / 'tasks/BondlingFairyland/sakura/auto_off_stopped_sample.png'))
        for delta in [-6, 0, 6]:
            image = np.zeros((720, 1280, 3), dtype=np.uint8)
            image[638:670, 786:818] = np.clip(circle.astype(int) + delta, 0, 255)
            task.device = SimpleNamespace(image=image)
            self.assertIs(task.bondling_sakura_state(), False)

    def test_real_stopped_circle_finishes_at_limit_without_another_toggle(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (1, 'battle', None), (2, 'result', None),
            (3, 'catch', True), (4, 'catch', False), (5.1, 'catch', False),
        ], limit=1)
        on = np.array(Image.open(ROOT / 'tasks/BondlingFairyland/sakura/auto_on_sample.png'))
        off = np.array(Image.open(ROOT / 'tasks/BondlingFairyland/sakura/auto_off_stopped_sample.png'))
        original_screenshot = task.screenshot

        def screenshot():
            original_screenshot()
            task.device.image = np.zeros((720, 1280, 3), dtype=np.uint8)
            task.device.image[638:670, 786:818] = on if state['auto'] else off

        task.screenshot = screenshot
        task.bondling_sakura_state = BondlingSakura.bondling_sakura_state.__get__(task, ScriptTask)
        with clock, dates:
            self.assertFalse(task.run_bondling_sakura())
        self.assertEqual(task.current_count, 1)
        self.assertEqual(state['clicks'], [(3, True)])
        task.device.image = np.zeros((1280, 720, 3), dtype=np.uint8)
        self.assertIsNone(task.bondling_sakura_state())

    def replay(self, frames, *, limit=2, seconds=300, count=0, guard=None):
        task = ScriptTask.__new__(ScriptTask)
        task.current_count = count
        task.limit_count = limit
        task.__dict__['limit_time'] = timedelta(seconds=seconds)
        task.start_time = datetime(2026, 10, 19)
        task.device = SimpleNamespace(
            detect_record={'existing'}, stuck_timer=Timer(60), stuck_timer_long=Timer(300),
            screenshot_interval_set=Mock(), activity_guard=guard)
        task.device.stuck_record_add = lambda name: task.device.detect_record.add(name)
        state = dict(time=1000, page=None, auto=None, clicks=[])
        sequence = iter(frames)

        def screenshot():
            try:
                elapsed, state['page'], state['auto'] = next(sequence)
            except StopIteration:
                self.fail('回放耗尽，任务没有按预期结束')
            state['time'] = 1000 + elapsed

        def click(button, interval):
            if button is task.I_BACK_YELLOW:
                self.assertEqual(state['page'], 'catch')
                self.assertIs(state['auto'], False)
                self.assertEqual(interval, 1)
                state['clicks'].append((round(state['time'] - 1000, 3), 'back'))
                return True
            if state['page'] in ('confirm', 'sure'):
                self.assertIs(button, task.I_UI_CONFIRM if state['page'] == 'confirm' else task.I_UI_SURE)
                self.assertEqual(interval, 1)
                state['clicks'].append((round(state['time'] - 1000, 3), state['page']))
                return True
            if state['page'] == 'warning':
                self.assertIs(button, task.I_BONDLING_PLATE_LIMIT_CONFIRM)
                self.assertEqual(interval, 1)
                state['clicks'].append((round(state['time'] - 1000, 3), 'confirm'))
                return True
            self.assertEqual(state['page'], 'catch')
            self.assertIs(button, task.C_BONDLING_SAKURA)
            self.assertEqual(interval, 0.8)
            state['clicks'].append((round(state['time'] - 1000, 3), state['auto']))
            return True

        class Clock:
            @staticmethod
            def now():
                return task.start_time + timedelta(seconds=state['time'] - 1000)

        task.screenshot = screenshot
        task.click = click
        task.in_catch_ui = lambda: state['page'] in ('catch', 'confirm', 'sure')
        task.in_search_ui = lambda: state['page'] == 'search'
        task.bondling_sakura_state = lambda: state['auto']
        def appear(marker, **kwargs):
            if marker is task.I_UI_CONFIRM:
                return state['page'] == 'confirm'
            if marker is task.I_UI_SURE:
                return state['page'] == 'sure'
            if marker is task.I_BACK_YELLOW:
                return state['page'] == 'catch'
            if marker is task.I_BONDLING_PLATE_LIMIT or marker is task.I_BONDLING_PLATE_LIMIT_CONFIRM:
                return state['page'] == 'warning'
            return (state['page'] == 'result'
                    or (state['page'] == 'capture' and isinstance(marker, list)))

        task.appear = appear
        task.is_in_prepare = lambda *args: state['page'] == 'prepare'
        task.is_in_battle = lambda *args: state['page'] == 'battle'
        task.run_general_battle = Mock(side_effect=AssertionError('挂机不接管战斗点击'))
        task.ui_goto_page = Mock(return_value=True)
        task.ui_page_appear = Mock(return_value=True)
        task.set_next_run = Mock()
        clock = patch('module.base.timer.time.time', side_effect=lambda: state['time'])
        dates = patch('tasks.BondlingFairyland.sakura.datetime', Clock)
        return task, state, clock, dates

    def test_count_once_per_round_then_stop_at_task_page(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', False), (0.5, 'catch', True),
            (1, 'prepare', None), (2, 'battle', None), (3, 'battle', None),
            (4, 'result', None), (5, 'result', None), (6, 'catch', True),
            (7, 'prepare', None), (8, 'battle', None), (9, 'result', None),
            (10, 'catch', True), (10.5, 'catch', True),
            (11, 'catch', False), (11.5, 'catch', False), (12.1, 'catch', False),
        ])
        with clock, dates:
            self.assertFalse(task.run_bondling_sakura())
        self.assertEqual(task.current_count, 2)
        self.assertEqual(state['clicks'], [(0, False), (10, True)])
        self.assertEqual(task.device.detect_record, {'existing'})
        task.run_general_battle.assert_not_called()

    def test_switch_uses_current_task_click_interface(self):
        task, _, clock, dates = self.replay([
            (0, 'catch', False), (0.5, 'catch', True), (1, 'battle', None),
            (2, 'result', None), (3, 'catch', True),
            (4, 'catch', False), (5.1, 'catch', False),
        ], limit=1)
        task.interval_timer = {}
        task.click = ScriptTask.click.__get__(task, ScriptTask)
        task.device.click = Mock()
        with clock, dates:
            task.run_bondling_sakura()
        self.assertEqual(task.device.click.call_count, 2)
        for call in task.device.click.call_args_list:
            self.assertEqual(call.kwargs['control_name'], 'bondling_sakura')
            self.assertTrue(795 <= call.kwargs['x'] < 809)
            self.assertTrue(647 <= call.kwargs['y'] < 661)

    def test_daily_plate_warning_is_confirmed_without_counting_or_toggling(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', False), (1, 'warning', None),
            (1.5, 'catch', True), (2, 'catch', True),
            (3, 'battle', None), (4, 'result', None),
            (5, 'catch', True), (6, 'catch', False), (7.1, 'catch', False),
        ], limit=1)
        with clock, dates:
            self.assertFalse(task.run_bondling_sakura())
        self.assertEqual(task.current_count, 1)
        self.assertEqual(state['clicks'], [(0, False), (1, 'confirm'), (5, True)])

    def test_unresponsive_plate_warning_has_bounded_clicks_and_timeout(self):
        task, state, clock, dates = self.replay([
            (0, 'warning', None), (1, 'warning', None), (2, 'warning', None),
            (3, 'warning', None), (4, 'warning', None), (5.1, 'warning', None),
        ])
        with clock, dates, self.assertRaisesRegex(GameStuckError, '式盘上限提示'):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(0, 'confirm'), (1, 'confirm'), (2, 'confirm')])
        self.assertFalse(task._bondling_sakura_observing)

    def test_normal_single_challenge_confirms_the_same_warning(self):
        task, state, clock, dates = self.replay([
            (0, 'warning', None), (1, 'battle', None), (2, 'battle', None),
        ])
        with clock, dates:
            task.run_alone()
        self.assertEqual(state['clicks'], [(0, 'confirm')])
        self.assertEqual(task.current_count, 0)

    def test_plate_warning_assets_match_only_their_own_regions(self):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        for asset in [BondlingSakura.I_BONDLING_PLATE_LIMIT,
                      BondlingSakura.I_BONDLING_PLATE_LIMIT_CONFIRM]:
            x, y, w, h = asset.roi_front
            image[y:y+h, x:x+w] = asset.image
            self.assertTrue(asset.match(image))
            image[y:y+h, x:x+w] = 0
            self.assertFalse(asset.match(image))

    def test_time_limit_during_battle_waits_for_return(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (1, 'battle', None),
            (20, 'battle', None), (21, 'result', None), (22, 'catch', True),
            (23, 'catch', False), (24.1, 'catch', False),
        ], limit=100, seconds=5)
        with clock, dates:
            self.assertFalse(task.run_bondling_sakura())
        self.assertEqual(task.current_count, 1)
        self.assertEqual(state['clicks'], [(22, True)])

    def test_limits_already_reached_and_resource_exhaustion_do_not_start(self):
        for auto in [False, True]:
            for reason in ['count', 'time', 'resource']:
                with self.subTest(auto=auto, reason=reason):
                    task, state, clock, dates = self.replay([
                        (1, 'catch', auto), (2, 'catch', False), (3.1, 'catch', False)
                    ], count=2 if reason == 'count' else 0,
                        seconds=0 if reason == 'time' else 300)
                    with clock, dates:
                        self.assertFalse(task.run_bondling_sakura(can_start=reason != 'resource'))
                    self.assertEqual(len(state['clicks']), int(auto))

    def test_natural_stop_does_not_restart_and_search_return_preserves_count(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (1, 'battle', None),
            (2, 'result', None), (3, 'search', False), (4.1, 'search', False),
        ], limit=100, count=4)
        with clock, dates:
            self.assertTrue(task.run_bondling_sakura())
        self.assertEqual(task.current_count, 5)
        self.assertEqual(state['clicks'], [])

    def test_exhausted_auto_on_or_off_returns_to_courtyard_after_ten_seconds(self):
        from tasks.GameUi.page import page_main
        for auto in [True, False]:
            task, state, clock, dates = self.replay([
                (0, 'catch', True), (1, 'battle', None), (2, 'result', None),
                (3, 'catch', auto), (12.9, 'catch', auto),
                (13, 'catch', auto), (14, 'catch', False),
                (15.1, 'catch', False), (16, 'search', None),
                (17.1, 'search', None), (18, 'courtyard', None),
            ], limit=100, count=4)
            with clock, dates, self.assertRaises(TaskEnd):
                task.run_bondling_sakura()
            self.assertEqual(task.current_count, 5)
            self.assertEqual(state['clicks'], ([(13, True)] if auto else []) + [(15.1, 'back')])
            task.ui_goto_page.assert_called_once_with(page_main, skip_first_screenshot=False)
            task.ui_page_appear.assert_called_once_with(page_main)
            task.set_next_run.assert_called_once_with(task='BondlingFairyland', finish=True, success=True)
            self.assertFalse(task._bondling_sakura_observing)
            self.assertEqual(task.device.detect_record, {'existing'})

    def test_next_battle_resets_exhaustion_wait_and_long_battle_is_allowed(self):
        task, _, clock, dates = self.replay([
            (0, 'catch', True), (9.9, 'catch', True),
            (10, 'battle', None), (35, 'battle', None), (36, 'result', None),
            (37, 'catch', True), (46.9, 'catch', True),
            (47, 'catch', True), (48, 'catch', False), (49.1, 'catch', False),
            (50, 'search', None), (51.1, 'search', None), (52, 'courtyard', None),
        ], limit=100)
        with clock, dates, self.assertRaises(TaskEnd):
            task.run_bondling_sakura()
        self.assertEqual(task.current_count, 1)
        task.ui_goto_page.assert_called_once()

    def test_exhaustion_does_not_finish_if_courtyard_navigation_fails(self):
        for navigation_ok in [False, True]:
            task, _, clock, dates = self.replay([
                (0, 'catch', True), (10, 'catch', True), (11, 'catch', False),
                (12.1, 'catch', False), (13, 'search', None),
                (14.1, 'search', None), (15, 'unknown', None),
            ], limit=100)
            task.ui_goto_page.return_value = navigation_ok
            task.ui_page_appear.return_value = False
            with clock, dates, self.assertRaises(GameStuckError):
                task.run_bondling_sakura()
            task.set_next_run.assert_not_called()

    def test_start_confirmation_does_not_trigger_exhaustion_or_count_as_battle(self):
        for prompt in ('confirm', 'sure'):
            with self.subTest(prompt=prompt):
                task, state, clock, dates = self.replay([
                    (0, 'catch', False), (9.9, prompt, None),
                    (10.5, 'battle', None), (11, 'battle', None),
                    (12, 'result', None), (13, 'catch', True),
                    (14, 'catch', False), (15.1, 'catch', False),
                ], limit=1)
                with clock, dates:
                    self.assertFalse(task.run_bondling_sakura())
                self.assertEqual(task.current_count, 1)
                self.assertEqual(state['clicks'], [(0, False), (9.9, prompt), (13, True)])
                task.ui_goto_page.assert_not_called()

    def test_unresponsive_start_confirmation_is_bounded(self):
        task, state, clock, dates = self.replay([
            (0, 'confirm', None), (1, 'confirm', None), (2, 'confirm', None),
            (3, 'confirm', None), (5.1, 'confirm', None),
        ])
        with clock, dates, self.assertRaisesRegex(GameStuckError, '开战确认'):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(0, 'confirm'), (1, 'confirm'), (2, 'confirm')])
        self.assertEqual(task.current_count, 0)
        task.ui_goto_page.assert_not_called()

    def test_late_battle_during_exhaustion_waits_for_settlement_before_navigation(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (10, 'catch', True),
            (10.5, 'battle', None), (35, 'battle', None), (36, 'result', None),
            (37, 'catch', True), (38, 'catch', False), (39.1, 'catch', False),
            (40, 'search', None), (41.1, 'search', None), (42, 'courtyard', None),
        ], limit=100)
        def navigate(*args, **kwargs):
            self.assertEqual(state['page'], 'search')
            self.assertEqual(task.current_count, 1)
            return True
        task.ui_goto_page.side_effect = navigate
        with clock, dates, self.assertRaises(TaskEnd):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(10, True), (37, True), (39.1, 'back')])

    def test_exhaustion_switch_failure_never_enters_navigation(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (10, 'catch', True),
            (11, 'catch', True), (15.1, 'catch', True),
        ], limit=100)
        with clock, dates, self.assertRaisesRegex(GameStuckError, '切换未生效'):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(10, True)])
        task.ui_goto_page.assert_not_called()

    def test_exhaustion_back_failure_has_bounded_clicks_and_timeout(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (10, 'catch', True), (11, 'catch', False),
            (12.1, 'catch', False), (13.2, 'catch', False), (14.3, 'catch', False),
            (15.4, 'catch', False), (22.2, 'catch', False),
        ], limit=100)
        with clock, dates, self.assertRaisesRegex(GameStuckError, '退出结契页'):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(10, True), (12.1, 'back'), (13.2, 'back'), (14.3, 'back')])
        task.ui_goto_page.assert_not_called()
        task.set_next_run.assert_not_called()

    def test_exhaustion_unknown_page_after_back_is_bounded(self):
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (10, 'catch', True), (11, 'catch', False),
            (12.1, 'catch', False), (13, 'unknown', None), (22.2, 'unknown', None),
        ], limit=100)
        with clock, dates, self.assertRaisesRegex(GameStuckError, '退出结契页'):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(10, True), (12.1, 'back')])
        task.ui_goto_page.assert_not_called()

    def test_start_confirmation_is_not_clicked_without_catch_background(self):
        task = ScriptTask.__new__(ScriptTask)
        task.in_catch_ui = Mock(return_value=False)
        task.appear = Mock(return_value=True)
        task.click = Mock()
        self.assertFalse(task.confirm_bondling_start_prompt())
        task.appear.assert_not_called()
        task.click.assert_not_called()

    def test_missed_prepare_and_task_page_do_not_lose_next_round(self):
        task, _, clock, dates = self.replay([
            (0, 'catch', True), (1, 'result', None), (2, 'result', None),
            (3, 'battle', None), (4, 'result', None), (5, 'catch', True),
            (6, 'catch', False), (7.1, 'catch', False),
        ])
        with clock, dates:
            task.run_bondling_sakura()
        self.assertEqual(task.current_count, 2)

    def test_capture_flash_then_same_battle_is_not_a_new_round(self):
        task, _, clock, dates = self.replay([
            (0, 'catch', True), (1, 'battle', None), (2, 'capture', None),
            (3, 'battle', None), (4, 'result', None), (5, 'catch', False),
            (6.1, 'catch', False),
        ], limit=1)
        with clock, dates:
            task.run_bondling_sakura()
        self.assertEqual(task.current_count, 1)

    def test_unknown_or_failed_switch_raises_without_repeated_toggle(self):
        for auto in [None, False]:
            task, state, clock, dates = self.replay([
                (0, 'catch', auto), (1, 'catch', auto), (6, 'catch', auto)
            ])
            task.device.detect_record.add('BATTLE_STATUS_S')
            with clock, dates, self.assertRaises(GameStuckError):
                task.run_bondling_sakura()
            self.assertEqual(len(state['clicks']), int(auto is False))
            self.assertIn('BATTLE_STATUS_S', task.device.detect_record)
            self.assertFalse(task._bondling_sakura_observing)
            task.device.screenshot_interval_set.assert_called_with()

    def test_stuck_battle_still_uses_device_timeout(self):
        task, _, clock, dates = self.replay([
            (0, 'catch', True), (1, 'battle', None), (302, 'battle', None),
        ], limit=100, seconds=1000)
        device = task.device
        device.stuck_long_wait_list = Device.stuck_long_wait_list
        device.app_is_running = Mock(return_value=True)

        def clear():
            device.detect_record.clear()
            device.stuck_timer.reset()
            device.stuck_timer_long.reset()

        device.stuck_record_clear = clear
        original_screenshot = task.screenshot

        def screenshot():
            original_screenshot()
            device.stuck_timer._reach_count = device.stuck_timer_long._reach_count = 1000
            Device.stuck_record_check(device)

        task.screenshot = screenshot
        with clock, dates:
            device.stuck_timer.start()
            device.stuck_timer_long.start()
            with self.assertRaises(GameStuckError):
                task.run_bondling_sakura()
        device.app_is_running.assert_called_once()
        self.assertFalse(task._bondling_sakura_observing)

    def test_rest_stops_auto_before_checkpoint_and_resumes_same_count(self):
        guard = SimpleNamespace(pending=False)
        task, state, clock, dates = self.replay([
            (0, 'catch', True), (1, 'battle', None), (2, 'result', None),
            (3, 'catch', True), (4, 'catch', False), (5.1, 'catch', False),
            (6, 'catch', False), (7, 'catch', True), (8, 'battle', None),
            (9, 'result', None), (10, 'catch', True),
            (11, 'catch', False), (12.1, 'catch', False),
        ], guard=guard)
        original_screenshot = task.screenshot

        def screenshot():
            original_screenshot()
            if state['time'] == 1002:
                guard.pending = True

        def checkpoint():
            self.assertFalse(state['auto'])
            self.assertEqual(task.current_count, 1)
            guard.pending = False
            return True

        task.screenshot = screenshot
        with clock, dates, patch('tasks.base_task.BaseTask.runtime_checkpoint', side_effect=checkpoint) as rest:
            task.run_bondling_sakura()
        rest.assert_called_once()
        self.assertEqual(task.current_count, 2)
        self.assertEqual(state['clicks'], [(3, True), (6, False), (10, True)])

    def test_config_defaults_and_only_single_catch_dispatches(self):
        self.assertFalse(BondlingConfig().bondling_sakura_enable)
        for enabled, status in [(True, UserStatus.ALONE), (False, UserStatus.ALONE),
                                (True, UserStatus.LEADER), (True, UserStatus.MEMBER)]:
            task = ScriptTask.__new__(ScriptTask)
            cfg = BondlingConfig(bondling_sakura_enable=enabled, user_status=status)
            task.lock_team = Mock()
            task.screenshot = Mock()
            task.device = SimpleNamespace(image=None)
            # No plates: both branches finish immediately, but only the enabled
            # single-player branch must inspect/disable an already active switch.
            task.O_B_LOW_NUMBER = SimpleNamespace(ocr=Mock(return_value=(0, 200, 200)))
            task.run_bondling_sakura = Mock(return_value=False)
            self.assertFalse(task.run_catch(cfg))
            self.assertEqual(task.run_bondling_sakura.call_count, int(enabled and status == UserStatus.ALONE))

    def test_pending_rest_before_activation_waits_then_starts(self):
        guard = SimpleNamespace(pending=True)
        task, state, clock, dates = self.replay([
            (0, 'catch', False), (1.1, 'catch', False),
            (2, 'catch', False), (3, 'catch', True), (4, 'battle', None),
            (5, 'result', None), (6, 'catch', True),
            (7, 'catch', False), (8.1, 'catch', False),
        ], limit=1, guard=guard)

        def checkpoint():
            self.assertEqual(state['clicks'], [])
            guard.pending = False
            return True

        with clock, dates, patch('tasks.base_task.BaseTask.runtime_checkpoint', side_effect=checkpoint):
            task.run_bondling_sakura()
        self.assertEqual(state['clicks'], [(2, False), (6, True)])


if __name__ == '__main__':
    unittest.main()
