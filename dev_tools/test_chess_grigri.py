"""银色以伞为剑：OCR、最高优先级、主动刷新及停止边界。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from tasks.Chess.script_task import ScriptTask
from tasks.Chess.strategy.counter_ubume import COUNTER_UBUME
from tasks.Chess.strategy.grigri import (
    grigri_file, grigri_keep_names, grigri_names_for_quality,
    grigri_selection_key, resolve_grigri_name,
)


class ChessGrigriTest(unittest.TestCase):
    def task(self, names, quality='silver', enabled=True, lineup='counter_ubume'):
        task = object.__new__(ScriptTask)
        task.select_lineup_strategy(lineup)
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        task.config = SimpleNamespace(chess=SimpleNamespace(chess_config=SimpleNamespace(
            continue_grigri_refresh_below_nine=enabled)))
        task._detect_grigri_quality = Mock(return_value=quality)
        task._match_grigri_icon = Mock(return_value=(None, 0.))
        for index, name in enumerate(names, 1):
            setattr(task, f'O_GRIGRI_OPTION_NAME_{index}', SimpleNamespace(ocr=Mock(return_value=name)))
        task._grigri_refresh_remaining = [1, 1, 1]
        task.screenshot = Mock()
        return task

    def test_name_is_silver_and_resolves_without_an_icon(self):
        self.assertIn('以伞为剑', grigri_names_for_quality('silver'))
        self.assertNotIn('以伞为剑', grigri_names_for_quality('gold'))
        self.assertNotIn('以伞为剑', grigri_names_for_quality('copper'))
        self.assertEqual(resolve_grigri_name(' 以伞 为剑 ', 'silver'), ('以伞为剑', 1.))
        self.assertEqual(resolve_grigri_name('以伞为剑', None), ('以伞为剑', 1.))
        self.assertIsNone(grigri_file('以伞为剑'))
        task = object.__new__(ScriptTask)
        self.assertNotIn('以伞为剑', task.grigri_icon_templates)

    def test_explicit_lineup_priority_beats_every_registered_alternative(self):
        best = grigri_selection_key('以伞为剑', COUNTER_UBUME)
        for name in grigri_names_for_quality(None):
            if name != '以伞为剑':
                self.assertGreater(best, grigri_selection_key(name, COUNTER_UBUME), name)
        self.assertIn('以伞为剑', grigri_keep_names('silver', COUNTER_UBUME))
        self.assertLess(grigri_selection_key('以伞为剑', '七角山'), grigri_selection_key('返金符咒', '七角山'))

    def test_real_recognition_keeps_ocr_only_target_and_selects_it(self):
        task = self.task(['返金符咒', '以伞为剑', '鬼神助力·贰'])
        options = task._recognize_grigri_options()
        self.assertEqual(options[1]['name'], '以伞为剑')
        self.assertEqual(options[1]['quality'], 'silver')
        self.assertEqual(options[1]['priority'], 1)
        self.assertEqual(task._best_grigri_option(options)['index'], 2)
        self.assertIsNone(task._next_refreshable_grigri_option(options))

    def test_silver_search_refreshes_lowest_even_when_all_three_are_top_forty_percent(self):
        task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'])
        options = task._recognize_grigri_options()
        keep = grigri_keep_names('silver', COUNTER_UBUME)
        self.assertTrue(all(o['name'] in keep for o in options))
        self.assertEqual(task._next_refreshable_grigri_option(options)['index'], 3)

    def test_general_toggle_and_other_lineups_keep_existing_refresh_behavior(self):
        for enabled, lineup in ((False, 'counter_ubume'), (True, 'qijiaoshan')):
            task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'], enabled=enabled, lineup=lineup)
            self.assertIsNone(task._next_refreshable_grigri_option(task._recognize_grigri_options()))

    def test_gold_and_unknown_quality_do_not_start_silver_hunt(self):
        task = self.task(['折上加折', '轮入之道·叁', '金运·大吉'], quality='gold')
        self.assertIsNone(task._next_refreshable_grigri_option(task._recognize_grigri_options()))
        task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'], quality=None)
        self.assertIsNone(task._next_refreshable_grigri_option(task._recognize_grigri_options()))

    def run_selection(self, task, spawn_target=False):
        state = SimpleNamespace(panel=True)
        task.appear = Mock(side_effect=lambda rule: state.panel if rule is task.I_SELECT_GRIGRI else False)
        task.click = Mock(side_effect=lambda rule: setattr(state, 'panel', False))
        refreshed = []
        def refresh(option):
            index = option['index']
            refreshed.append(index)
            task._grigri_refresh_remaining[index - 1] -= 1
            if spawn_target:
                getattr(task, f'O_GRIGRI_OPTION_NAME_{index}').ocr.return_value = '以伞为剑'
            return True
        task._refresh_grigri_option = Mock(side_effect=refresh)
        with patch('tasks.Chess.runtime.round_state.time.sleep'):
            self.assertTrue(task.select_grigri())
        return refreshed

    def test_target_already_present_is_selected_without_any_refresh(self):
        task = self.task(['返金符咒', '以伞为剑', '捷径·贰'])
        self.assertEqual(self.run_selection(task), [])
        task.click.assert_called_once_with(task.C_GRIGRI_OPTION_2)

    def test_first_refresh_finds_target_and_cancels_all_further_refreshes(self):
        task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'])
        self.assertEqual(self.run_selection(task, spawn_target=True), [3])
        task.click.assert_called_once_with(task.C_GRIGRI_OPTION_3)

    def test_search_exhausts_each_slot_once_then_selects_best_existing_option(self):
        task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'])
        self.assertEqual(self.run_selection(task), [3, 2, 1])
        self.assertEqual(task._grigri_refresh_remaining, [0, 0, 0])
        task.click.assert_called_once_with(task.C_GRIGRI_OPTION_1)

    def test_silver_search_clicks_refresh_once_then_observes(self):
        task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'])
        task.device.click = Mock()
        option = task._recognize_grigri_options()[2]
        with patch('tasks.Chess.runtime.round_state.time.sleep') as sleep:
            self.assertTrue(task._refresh_grigri_option(option))
        task.device.click.assert_called_once()
        task.screenshot.assert_called_once()
        self.assertEqual(task._grigri_refresh_remaining, [1, 1, 0])
        sleep.assert_any_call(task.ACTION_SETTLE_INTERVAL)

    def test_legacy_refresh_click_sequence_is_unchanged(self):
        task = self.task(['返金符咒', '鬼神助力·贰', '捷径·贰'], lineup='qijiaoshan')
        task.device.click = Mock()
        option = task._recognize_grigri_options()[2]
        with patch('tasks.Chess.runtime.round_state.time.sleep'):
            self.assertTrue(task._refresh_grigri_option(option))
        self.assertEqual(task.device.click.call_count, 2)


if __name__ == '__main__':
    unittest.main()
