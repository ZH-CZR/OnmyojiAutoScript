"""御魂名称切换离线回归，不连接设备或 OCR 服务。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.exception import GameStuckError
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul


MODULE = 'tasks.Component.SwitchSoul.switch_soul'


class SwitchSoulTest(unittest.TestCase):
    def setUp(self):
        self.original_cache = SwitchSoul._current_switch_soul
        self.addCleanup(setattr, SwitchSoul, '_current_switch_soul', self.original_cache)
        self.now = 0
        self.sleep_patch = patch(MODULE + '.sleep', self.advance)
        self.clock_patch = patch(MODULE + '.monotonic', lambda: self.now)
        self.sleep_patch.start()
        self.clock_patch.start()
        self.addCleanup(self.sleep_patch.stop)
        self.addCleanup(self.clock_patch.stop)

    def advance(self, seconds):
        self.now += seconds

    def task(self):
        task = SwitchSoul.__new__(SwitchSoul)
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3)))
        task.screenshot = Mock(side_effect=lambda: self.advance(0.1))
        task.swipe = Mock()
        task.click = Mock()
        task.appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=False)
        task.ui_goto_page = Mock()
        return task

    def test_rows_use_full_screen_and_box_offsets(self):
        task = self.task()
        box = np.array([[10, 20], [80, 22], [78, 44], [8, 42]])
        good = SimpleNamespace(ocr_text='通用', box=box)
        clipped = SimpleNamespace(ocr_text='通', box=box-50)
        rule = SimpleNamespace(roi=(573, 140, 277, 481),
                               detect_and_ocr=Mock(return_value=[good, clipped]))
        self.assertEqual(task._soul_name_rows(rule), [('通用', (581, 160, 72, 24))])
        self.assertIs(rule.detect_and_ocr.call_args.args[0], task.device.image)

    def test_target_disappears_then_is_found_again(self):
        task = self.task()
        first = [('通用', (600, 300, 50, 25))]
        final = [('通用', (600, 200, 50, 25))]
        task._soul_name_rows = Mock(side_effect=[first, [], final, final])
        forward, backward = object(), object()
        self.assertEqual(task._find_soul_name(None, '通用', forward, backward, '阵容'), final[0][1])
        task.swipe.assert_called_once_with(forward, 0.3)
        self.assertEqual(task.screenshot.call_count, 4)

    def test_partial_or_duplicate_name_never_selected_and_search_times_out(self):
        for rows in ([('通', (600, 200, 30, 25))],
                     [('通用', (600, 200, 50, 25)), ('通用', (600, 350, 50, 25))], []):
            with self.subTest(rows=rows):
                task = self.task()
                task._soul_name_rows = Mock(return_value=rows)
                with self.assertRaisesRegex(GameStuckError, '阵容查找超时：通用'):
                    task._find_soul_name(None, '通用', object(), object(), '阵容')
                task.click.assert_not_called()

    def test_apply_uses_latest_row_and_does_not_mutate_shared_rules(self):
        task = self.task()
        task._soul_list_top = Mock()
        task._find_soul_name = Mock(side_effect=[(1130, 440, 60, 25), (590, 360, 70, 26)])
        task._confirm_soul_switch = Mock()
        old_keyword = task.O_SS_TEAM_NAME.keyword
        old_roi = tuple(task.I_SOU_CLICK_PRESENT.roi_front)
        task.switch_soul_by_name('逢魔', '通用')
        button = task.click.call_args.args[0]
        self.assertEqual(button.roi_front, (old_roi[0], 360, old_roi[2], 26))
        self.assertEqual(task.O_SS_TEAM_NAME.keyword, old_keyword)
        self.assertEqual(tuple(task.I_SOU_CLICK_PRESENT.roi_front), old_roi)
        task._confirm_soul_switch.assert_called_once_with('逢魔,通用')

    def test_no_confirmation_or_stuck_dialog_never_succeeds(self):
        for dialog in (False, True):
            task = self.task()
            task.appear = Mock(return_value=dialog)
            task.appear_then_click = Mock(return_value=dialog)
            with self.assertRaisesRegex(GameStuckError, '未确认成功'):
                task._confirm_soul_switch('逢魔,通用')

    def test_confirmation_requires_dialog_then_stable_preset(self):
        task = self.task()
        frames = iter([True, True, False, False, False, False, False])
        dialog = [False]
        def screenshot():
            self.advance(0.1)
            dialog[0] = next(frames, False)
        task.screenshot.side_effect = screenshot
        task.appear.side_effect = lambda target: dialog[0] if target is task.I_UI_SURE else target is task.I_SOU_TEAM_PRESENT
        task.appear_then_click.return_value = True
        task._confirm_soul_switch('逢魔,通用')
        self.assertGreaterEqual(task.screenshot.call_count, 5)

    def test_secondary_confirmation_is_handled_before_success(self):
        task = self.task()
        state = [0]
        def screenshot():
            self.advance(0.2)
            state[0] += 1
        task.screenshot.side_effect = screenshot
        def appear(target):
            if target is task.I_UI_SURE:
                return state[0] == 1
            if target is task.I_CHECK_BLOCK:
                return state[0] == 2
            return target is task.I_SOU_TEAM_PRESENT
        task.appear.side_effect = appear
        task.appear_then_click.return_value = True
        task._confirm_soul_switch('6,1')
        self.assertEqual([call.args[0] for call in task.appear_then_click.call_args_list],
                         [task.I_UI_SURE, task.I_CHECK_BLOCK])

    def test_failed_name_switch_invalidates_cache_and_retry_runs(self):
        task = self.task()
        task.click_preset = Mock()
        task.switch_soul_by_name = Mock(side_effect=[GameStuckError('fail'), None])
        SwitchSoul._current_switch_soul = '6,1'
        with self.assertRaises(GameStuckError):
            task.run_switch_soul_by_name('逢魔', '通用')
        self.assertEqual(SwitchSoul._current_switch_soul, '-')
        task.run_switch_soul_by_name('逢魔', '通用')
        self.assertEqual(task.switch_soul_by_name.call_count, 2)
        self.assertEqual(SwitchSoul._current_switch_soul, '逢魔,通用')

    def test_failed_numeric_switch_also_invalidates_cache(self):
        task = self.task()
        task.switch_parser = Mock(return_value=(6, 1))
        task.click_preset = Mock()
        task.switch_souls = Mock(side_effect=GameStuckError('fail'))
        SwitchSoul._current_switch_soul = '逢魔,通用'
        with self.assertRaises(GameStuckError):
            task.run_switch_soul('6,1')
        self.assertEqual(SwitchSoul._current_switch_soul, '-')

    def test_open_and_scroll_top_have_fixed_deadlines(self):
        task = self.task()
        with self.assertRaisesRegex(GameStuckError, '打开御魂预设超时'):
            task.click_preset()
        task._soul_name_rows = Mock(return_value=[])
        with self.assertRaisesRegex(GameStuckError, '回到顶部超时'):
            task._soul_list_top(None, object(), '阵容')

    def test_scroll_top_accepts_small_ocr_jitter_but_not_empty_results(self):
        task = self.task()
        task._soul_name_rows = Mock(side_effect=[[], [('通用', (600, 200, 50, 25))],
                                                  [('通用', (601, 201, 50, 25))]])
        task._soul_list_top(None, object(), '阵容')
        self.assertEqual(task.swipe.call_count, 2)

    def test_unstable_target_keeps_waiting_without_clicking(self):
        task = self.task()
        def rows(rule):
            y = 200 if task.screenshot.call_count % 2 else 300
            return [('通用', (600, y, 50, 25))]
        task._soul_name_rows = rows
        with self.assertRaisesRegex(GameStuckError, '查找超时'):
            task._find_soul_name(None, '通用', object(), object(), '阵容')
        task.click.assert_not_called()

    def test_boundary_reverses_search_direction(self):
        task = self.task()
        row = [('歌姬', (600, 200, 50, 25))]
        target = [('通用', (600, 200, 50, 25))]
        task._soul_name_rows = Mock(side_effect=[row, row, target, target])
        forward, backward = object(), object()
        task._find_soul_name(None, '通用', forward, backward, '阵容')
        self.assertIs(task.swipe.call_args_list[0].args[0], forward)
        self.assertIs(task.swipe.call_args_list[1].args[0], backward)

    def test_successful_numeric_switch_is_cached_only_after_confirmation(self):
        task = self.task()
        task.switch_parser = Mock(return_value=(6, 1))
        task.click_preset = Mock()
        SwitchSoul._current_switch_soul = 'old'
        def switch(target):
            self.assertEqual(SwitchSoul._current_switch_soul, '-')
        task.switch_souls = Mock(side_effect=switch)
        task.run_switch_soul('6,1')
        self.assertEqual(SwitchSoul._current_switch_soul, '6,1')
        task.run_switch_soul('6,1')
        task.switch_souls.assert_called_once_with((6, 1))

    def test_numeric_entry_requires_confirmation(self):
        task = self.task()
        task.O_SS_GROUP_NAME = SimpleNamespace(detect_and_ocr=Mock(
            return_value=[SimpleNamespace(ocr_text='逢魔')]))
        task.appear_then_click.return_value = True
        task._confirm_soul_switch = Mock(side_effect=GameStuckError('not confirmed'))
        with self.assertRaisesRegex(GameStuckError, 'not confirmed'):
            task.switch_soul_one(6, 1)
        task._confirm_soul_switch.assert_called_once_with('6,1')


if __name__ == '__main__':
    unittest.main()
