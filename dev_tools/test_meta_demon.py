"""Replay MetaDemon navigation and runtime boundaries without device input."""
import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.exception import GameStuckError, TaskEnd
from tasks.MetaDemon import inner_page as pages
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemon.config import MetaDemon, BossType
from tasks.MetaDemon.script_task import ScriptTask


class MetaDemonTest(unittest.TestCase):
    def task(self):
        task = ScriptTask.__new__(ScriptTask)
        task.conf = MetaDemon()
        task.O_MD_FATIGUE = Mock()
        task.O_MD_FATIGUE.ocr.return_value = (0, 100, 100)
        task.config = SimpleNamespace(meta_demon=task.conf)
        task.State = SimpleNamespace(done=False, switch_soul_done=False)
        task.cur_boss_type = None
        task.total_count = task.current_count = 0
        task.start_time = datetime.now()
        task.limit_count = 50
        task.limit_time = timedelta(minutes=45)
        task.device = SimpleNamespace(image=None, detect_record=set(), click_record_clear=Mock())
        task.device.stuck_record_add = lambda marker: task.device.detect_record.add(marker)
        task.ui_goto_page = Mock(return_value=True)
        task.ui_reward_appear_click = Mock(return_value=False)
        task.set_next_run = Mock()
        task.click = Mock()
        task.run_general_battle = Mock()
        return task

    def replay(self, task, frames):
        state = {'now': 1000, 'visible': set(), 'clicks': []}
        sequence = iter(frames)

        def screenshot():
            state['now'], state['visible'] = next(sequence)

        def appear(target, **kwargs):
            if isinstance(target, (list, tuple)):
                return any(appear(t) for t in target)
            return target.name in state['visible']

        def click(target, **kwargs):
            if appear(target):
                state['clicks'].append(target.name)
                task.device.detect_record.clear()  # Actual clicks clear wait markers.
                return True
            return False

        task.screenshot = Mock(side_effect=screenshot)
        task.appear = Mock(side_effect=appear)
        task.appear_then_click = Mock(side_effect=click)
        task._visible_summon_tickets = Mock(side_effect=lambda rules: sorted(
            [(star, rule) for star, rule in rules.items() if appear(rule)],
            key=lambda item: item[1].roi_front[0]))
        task.is_in_battle = Mock(side_effect=lambda *_: 'BATTLE' in state['visible'])
        return state, patch('module.base.timer.time.time', side_effect=lambda: state['now'])

    def test_new_entry_reaches_boss_without_global_navigation(self):
        task = self.task()
        state, clock = self.replay(task, [
            (1001, {'I_MD_CURRENT_ENTRY'}), (1002, {'I_MD_CURRENT_ENTER'}),
            (1003, {'I_MD_CURRENT_SUMMON'})])
        with clock:
            self.assertTrue(task._enter_boss_page())
        self.assertEqual(state['clicks'], ['I_MD_CURRENT_ENTRY', 'I_MD_CURRENT_ENTER'])
        self.assertIs(task.ui_current, pages.page_meta_demon_boss)
        task.ui_goto_page.assert_not_called()

    def test_repeated_entry_clicks_do_not_extend_deadline(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_MD_CURRENT_ENTRY'}),
                                     (1030, {'I_MD_CURRENT_ENTRY'}),
                                     (1061, {'I_MD_CURRENT_ENTRY'})])
        with clock, self.assertRaises(GameStuckError):
            task._enter_boss_page()

    def test_existing_battle_uses_model_battle_config_and_counts_once(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'BATTLE'})])
        with clock:
            self.assertFalse(task._enter_boss_page())
        self.assertEqual(task.total_count, 1)
        task.run_general_battle.assert_called_once()

    def test_failed_entry_recovery_raises(self):
        task = self.task()
        task.ui_goto_page.return_value = False
        _, clock = self.replay(task, [(1001, set())])
        with clock, self.assertRaises(GameStuckError):
            task._enter_boss_page()

    def test_summon_uses_highest_at_high_fatigue_and_confirms_selected_ticket(self):
        task = self.task()
        task.conf.meta_demon_config.fire_sequence = '1 3'
        task.O_MD_FATIGUE.ocr.return_value = (71, 29, 100)
        task._classify_selected_ticket = Mock(return_value=BossType.THREE_STARS)
        task._refresh_current_boss_type = Mock(return_value=BossType.THREE_STARS)
        selected = copy.copy(task.I_MD_CHECK_SELECTED)
        selected.roi_front = [560, 280, 40, 20]
        task.I_MD_CHECK_SELECTED = selected
        state, clock = self.replay(task, [
            (1001, {'I_MD_SWITCH_TICKET'}),
            (1002, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR', 'I_MD_THREE_STARS'}),
            (1003, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1004, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1005, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertEqual(task.cur_boss_type, BossType.THREE_STARS)
        self.assertEqual(state['clicks'], [
            'I_MD_SWITCH_TICKET', 'I_MD_THREE_STARS', 'I_MD_GET_BOSS'])

    def test_missing_tickets_finish_without_battle(self):
        task = self.task()
        task._close_boss_popup = Mock()
        _, clock = self.replay(task, [(1001, {'I_MD_GET_BOSS'})])
        with clock:
            self.assertFalse(task.check_and_switch_ticket())
        self.assertTrue(task.State.done)
        task.run_general_battle.assert_not_called()

    def test_summon_wait_has_fixed_deadline(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_MD_CURRENT_SUMMON'}),
                                     (1016, {'I_MD_CURRENT_SUMMON'})])
        with clock, self.assertRaises(GameStuckError):
            task.check_and_switch_ticket()

    def test_ticket_entry_never_alternates_buttons_and_waits_for_response(self):
        task = self.task()
        task._close_boss_popup = Mock()
        all_entries = {'I_MD_SWITCH_TICKET', 'I_MD_CURRENT_SUMMON', 'I_MD_SUMMON_BOSS'}
        state, clock = self.replay(task, [
            (1001, all_entries), (1001.3, all_entries), (1001.9, all_entries),
            (1002, {'I_MD_GET_BOSS'})])
        with clock:
            self.assertFalse(task.check_and_switch_ticket())
        self.assertEqual(state['clicks'], ['I_MD_SWITCH_TICKET'])

    def test_ticket_entry_clicks_at_most_three_times_without_extending_total_deadline(self):
        task = self.task()
        all_entries = {'I_MD_SWITCH_TICKET', 'I_MD_CURRENT_SUMMON', 'I_MD_SUMMON_BOSS'}
        state, clock = self.replay(task, [(1001, all_entries), (1003.1, all_entries),
                                        (1005.2, all_entries), (1008, all_entries),
                                        (1016, all_entries)])
        with clock, self.assertRaises(GameStuckError):
            task.check_and_switch_ticket()
        self.assertEqual(state['clicks'], ['I_MD_SWITCH_TICKET'] * 3)

    def test_fatigue_seventy_boundary_selects_lowest_or_highest_of_all_six_stars(self):
        for fatigue, star, target in [(0, BossType.ONE_STAR, 'I_MD_ONE_STAR'),
                                      (70, BossType.ONE_STAR, 'I_MD_ONE_STAR'),
                                      (71, BossType.SIX_STARS, 'I_MD_SIX_STARS'),
                                      (99, BossType.SIX_STARS, 'I_MD_SIX_STARS')]:
            task = self.task()
            task.conf.meta_demon_config.fire_sequence = '3'  # Dormant legacy filter.
            task.O_MD_FATIGUE.ocr.return_value = (fatigue, 100-fatigue, 100)
            task._refresh_current_boss_type = Mock()
            state, clock = self.replay(task, [
                (1001, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR', 'I_MD_THREE_STARS', 'I_MD_SIX_STARS'}),
                (1002, {target}), (1003, {'I_MD_FIRE'})])
            with self.subTest(fatigue=fatigue), clock:
                self.assertTrue(task.check_and_switch_ticket())
            self.assertEqual(task.cur_boss_type, star)
            self.assertEqual(state['clicks'], [target])

    def test_rechecks_fatigue_at_selection_instead_of_reusing_previous_counter(self):
        task = self.task()
        task.O_MD_FATIGUE.ocr.side_effect = [(10, 90, 100), (85, 15, 100)]
        task.check_fatigue()
        task._refresh_current_boss_type = Mock()
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR', 'I_MD_SIX_STARS'}),
            (1002, {'I_MD_SIX_STARS'}), (1003, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertEqual(state['clicks'], ['I_MD_SIX_STARS'])
        self.assertEqual(task.O_MD_FATIGUE.ocr.call_count, 2)

    def test_other_summon_icons_are_never_used_when_queue_entry_is_missing(self):
        task = self.task()
        icons = {'I_MD_CURRENT_SUMMON', 'I_MD_SUMMON_BOSS'}
        state, clock = self.replay(task, [(1001, icons), (1005, icons), (1016, icons)])
        with clock, self.assertRaises(GameStuckError):
            task.check_and_switch_ticket()
        self.assertEqual(state['clicks'], [])

    def test_unreadable_fatigue_stops_before_selecting_or_summoning(self):
        task = self.task()
        task.O_MD_FATIGUE.ocr.return_value = (0, 0, 0)
        state, clock = self.replay(task, [(1001, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR'})])
        with clock, self.assertRaisesRegex(GameStuckError, '疲劳度识别失败'):
            task.check_and_switch_ticket()
        self.assertEqual(state['clicks'], [])

    def test_legacy_fire_sequence_is_hidden_but_not_deleted(self):
        from module.config.config_model import ConfigModel
        model = ConfigModel()
        fields = model.script_task('MetaDemon')['meta_demon_config']
        self.assertNotIn('fire_sequence', [field['name'] for field in fields])
        self.assertIn('fire_sequence', model.meta_demon.meta_demon_config.model_dump())

    def test_each_round_clicks_summon_only_once_while_waiting_for_result(self):
        task = self.task()
        task._classify_selected_ticket = Mock(return_value=BossType.ONE_STAR)
        task._refresh_current_boss_type = Mock()
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR'}),
            (1002, {'I_MD_ONE_STAR'}),
            (1003, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1004, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1005, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1006, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertEqual(state['clicks'].count('I_MD_GET_BOSS'), 1)
        self.assertEqual(state['clicks'].count('I_MD_ONE_STAR'), 1)

    def test_already_marked_target_summons_without_clicking_the_eye_again(self):
        task = self.task()
        task._classify_selected_ticket = Mock(return_value=BossType.THREE_STARS)
        task._refresh_current_boss_type = Mock()
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS', 'I_MD_CHECK_SELECTED'}),
            (1002, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS', 'I_MD_CHECK_SELECTED'}),
            (1003, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1004, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertEqual(state['clicks'], ['I_MD_GET_BOSS'])

    def test_eye_is_clicked_once_then_only_waits_for_selection_marker(self):
        task = self.task()
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1002, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1003, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1008, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1017, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'})])
        with clock, self.assertRaises(GameStuckError):
            task.check_and_switch_ticket()
        self.assertEqual(state['clicks'], ['I_MD_THREE_STARS'])

    def test_ambiguous_selected_card_does_not_cause_reselection_or_summon(self):
        task = self.task()
        task._classify_selected_ticket = Mock(return_value=None)
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1002, {'I_MD_GET_BOSS', 'I_MD_THREE_STARS'}),
            (1003, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED', 'I_MD_THREE_STARS'}),
            (1008, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED', 'I_MD_THREE_STARS'}),
            (1017, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED', 'I_MD_THREE_STARS'})])
        with clock, self.assertRaises(GameStuckError):
            task.check_and_switch_ticket()
        self.assertEqual(state['clicks'], ['I_MD_THREE_STARS'])

    def test_old_selected_star_after_click_waits_for_target_without_reclick(self):
        task = self.task()
        task._classify_selected_ticket = Mock(side_effect=[
            BossType.SIX_STARS, BossType.SIX_STARS, BossType.TWO_STARS])
        task._refresh_current_boss_type = Mock()
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_TWO_STARS'}),
            (1002, {'I_MD_GET_BOSS', 'I_MD_TWO_STARS', 'I_MD_CHECK_SELECTED'}),
            (1002.03, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1002.5, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1003, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertEqual(state['clicks'], ['I_MD_TWO_STARS', 'I_MD_GET_BOSS'])

    def test_direction_uses_visible_position_instead_of_star_enum(self):
        for fatigue, expected in [(39, BossType.FIVE_STARS), (73, BossType.TWO_STARS)]:
            task = self.task()
            task.O_MD_FATIGUE.ocr.return_value = (fatigue, 100-fatigue, 100)
            task._classify_selected_ticket = Mock(return_value=expected)
            task._refresh_current_boss_type = Mock()
            state, clock = self.replay(task, [
                (1001, {'I_MD_GET_BOSS'}),
                (1002, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
                (1003, {'I_MD_FIRE'})])
            task._visible_summon_tickets = Mock(return_value=[
                (BossType.FIVE_STARS, task.I_MD_FIVE_STARS),
                (BossType.TWO_STARS, task.I_MD_TWO_STARS)])
            with self.subTest(fatigue=fatigue), clock:
                self.assertTrue(task.check_and_switch_ticket())
            self.assertEqual(task.cur_boss_type, expected)
            self.assertEqual(state['clicks'], ['I_MD_GET_BOSS'])

    def test_real_capture_three_four_star_score_gap_is_not_rejected_as_ambiguous(self):
        task = self.task()
        task.appear = Mock(return_value=True)
        # Scores measured under the marker in the reported queue screenshot.
        for scores, expected in [([.4969, .5032, .9620, .9506, .5004, .4870], BossType.THREE_STARS),
                                 ([.4969, .5032, .9620, .9600, .5004, .4870], None),
                                 ([.4969, .5032, .9100, .8500, .5004, .4870], None)]:
            rules = {BossType(i): SimpleNamespace(roi_back=(0, 0, 1, 1), max_val=score,
                                                  match=Mock(return_value=True))
                     for i, score in enumerate(scores, 1)}
            with self.subTest(scores=scores):
                self.assertEqual(task._classify_selected_ticket(rules), expected)

    def test_unplanned_prepare_is_rejected_before_entry_navigation_or_ticket_actions(self):
        for method in ('_enter_boss_page', 'check_and_switch_ticket'):
            task = self.task()
            state, clock = self.replay(task, [(1001, {'I_PRESET', 'I_PREPARE_HIGHLIGHT'})])
            with self.subTest(method=method), clock, self.assertRaisesRegex(GameStuckError, '未确认本轮选票及阵容'):
                getattr(task, method)()
            task.ui_goto_page.assert_not_called()
            task.run_general_battle.assert_not_called()
            self.assertEqual(state['clicks'], [])

    def test_star_refresh_must_recheck_latest_scene_before_returning_ready(self):
        task = self.task()
        state, clock = self.replay(task, [(1001, {'I_MD_FIRE'})])
        def changed_scene(**kwargs):
            state['visible'] = {'I_PRESET', 'I_PREPARE_HIGHLIGHT'}
        task._refresh_current_boss_type = Mock(side_effect=changed_scene)
        with clock, self.assertRaisesRegex(GameStuckError, '星级复核阶段'):
            task.check_and_switch_ticket()
        task.ui_goto_page.assert_not_called()

    def test_powerful_setting_does_not_use_global_navigation_on_wrong_scene(self):
        task = self.task()
        state, clock = self.replay(task, [(1001, {'I_PRESET'})])
        task.screenshot()
        with clock, self.assertRaisesRegex(GameStuckError, '追击设置阶段'):
            task.check_and_switch_powerful()
        task.ui_goto_page.assert_not_called()
        self.assertEqual(state['clicks'], [])

    def test_planned_challenge_transition_accepts_prepare_page_without_waiting_for_active_battle(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_PRESET', 'I_PREPARE_HIGHLIGHT'})])
        with clock:
            task.start_battle()
        self.assertEqual(task.total_count, 1)
        task.run_general_battle.assert_called_once()

    def test_no_battle_count_until_battle_confirmed(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_MD_FIRE'}), (1016, {'I_MD_FIRE'})])
        with clock, self.assertRaises(GameStuckError):
            task.start_battle()
        self.assertEqual(task.total_count, 0)

    def test_fatigue_full_waits_but_bad_ocr_raises(self):
        for counter in ((100, 0, 100), (0, 0, 0), (0, -1, 100)):
            task = self.task()
            task.O_MD_FATIGUE = Mock()
            task.O_MD_FATIGUE.ocr.return_value = counter
            task.finish_task = Mock(side_effect=TaskEnd)
            with self.subTest(counter=counter):
                with self.assertRaises(TaskEnd if counter == (100, 0, 100) else GameStuckError):
                    task.check_fatigue()
                self.assertEqual(task.set_next_run.call_count, int(counter == (100, 0, 100)))

    def test_auto_tea_does_not_schedule_fatigue_wait(self):
        task = self.task()
        task.conf.meta_demon_config.auto_tea = True
        task.O_MD_FATIGUE = Mock()
        task.O_MD_FATIGUE.ocr.return_value = (100, 0, 100)
        self.assertTrue(task.check_fatigue())
        task.set_next_run.assert_not_called()

    def test_disabled_or_unknown_star_does_not_change_souls(self):
        for enabled in (False, True):
            task = self.task()
            task.conf.switch_soul.enable = enabled
            self.assertTrue(task.check_and_switch_soul())
            task.ui_goto_page.assert_not_called()

    def test_failed_soul_switch_is_not_marked_complete(self):
        task = self.task()
        task.conf.switch_soul.enable = True
        task.conf.switch_soul.one_star = '1,2'
        task.cur_boss_type = BossType.ONE_STAR
        task.run_switch_soul = Mock(side_effect=RuntimeError('soul failure'))
        with self.assertRaisesRegex(RuntimeError, 'soul failure'):
            task.check_and_switch_soul()
        self.assertFalse(task.State.switch_soul_done)

    def test_battle_requires_stable_return_and_restores_markers(self):
        task = self.task()
        task.device.detect_record.add('OTHER_WAIT')
        _, clock = self.replay(task, [
            (1001, {'I_WIN'}), (1002, {'I_MD_CURRENT_SUMMON'}),
            (1002.2, set()), (1003, {'I_MD_CURRENT_SUMMON'}),
            (1004.1, {'I_MD_CURRENT_SUMMON'})])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(task.screenshot.call_count, 5)
        self.assertEqual(task.device.detect_record, {'OTHER_WAIT'})

    def test_stuck_settlement_times_out_and_releases_marker(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_MD_SETTLING'}), (1301, {'I_MD_SETTLING'})])
        with clock, self.assertRaises(GameStuckError):
            task.battle_wait(False)
        self.assertEqual(task.device.detect_record, set())

    def test_settling_overlay_is_not_a_completed_battle(self):
        task = self.task()
        _, clock = self.replay(task, [
            (1001, {'I_MD_FIRE', 'I_MD_SETTLING'}),
            (1003, {'I_MD_FIRE', 'I_MD_SETTLING'}),
            (1004, {'I_MD_FIRE'}), (1005.1, {'I_MD_FIRE'})])
        with clock:
            self.assertFalse(task.battle_wait(False))
        self.assertEqual(task.screenshot.call_count, 4)

    def test_battle_error_restores_existing_marker(self):
        task = self.task()
        task.device.detect_record.update({'BATTLE_STATUS_S', 'OTHER_WAIT'})
        task.screenshot = Mock(side_effect=RuntimeError('capture failure'))
        with self.assertRaisesRegex(RuntimeError, 'capture failure'):
            task.battle_wait(False)
        self.assertEqual(task.device.detect_record, {'BATTLE_STATUS_S', 'OTHER_WAIT'})

    def test_tea_disabled_waits_without_drinking(self):
        task = self.task()
        task._close_boss_popup = Mock()
        task.finish_task = Mock(side_effect=TaskEnd)
        _, clock = self.replay(task, [(1001, {'I_MD_DRINK_TEA'})])
        with clock, self.assertRaises(TaskEnd):
            task.start_battle()
        task.click.assert_not_called()
        task.set_next_run.assert_called_once()
        self.assertEqual(task.total_count, 0)

    def test_repeated_runs_reset_only_their_own_runtime_state(self):
        task = self.task()
        other = self.task()
        original_close = task.ui_close
        try:
            task.before_run()
            task.State.done = task.State.switch_soul_done = True
            task.total_count = 12
            task._restore_navigation()
            task.before_run()
            self.assertFalse(task.State.done)
            self.assertFalse(task.State.switch_soul_done)
            self.assertEqual(task.total_count, 0)
            self.assertFalse(other.State.done)
        finally:
            task._restore_navigation()
            task.ui_close = original_close

    def test_unconfirmed_ticket_selection_never_summons(self):
        task = self.task()
        selected = copy.copy(task.I_MD_CHECK_SELECTED)
        selected.roi_front = [850, 280, 40, 20]  # Wrong star column.
        task._classify_selected_ticket = Mock(return_value=BossType.SIX_STARS)
        task.I_MD_CHECK_SELECTED = selected
        state, clock = self.replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR'}),
            (1002, {'I_MD_ONE_STAR'}),
            (1003, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1017, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'})])
        with clock, self.assertRaises(GameStuckError):
            task.check_and_switch_ticket()
        self.assertNotIn('I_MD_GET_BOSS', state['clicks'])

    def test_run_restores_original_navigation_even_on_error(self):
        for error in (RuntimeError('capture failure'), TaskEnd()):
            task = self.task()
            task._enter_boss_page = Mock(side_effect=error)
            originals = [(page, {dest: list(buttons) for dest, buttons in page.links.items()})
                         for page in (pages.page_main, pages.page_shikigami_records, pages.page_meta_demon_boss)]
            original_close = task.ui_close
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)):
                task.run()
            for page, links in originals:
                self.assertEqual(page.links, links)
            self.assertIs(task.ui_close, original_close)

    def test_full_run_uses_existing_config_without_missing_page_attributes(self):
        task = self.task()
        task.conf.meta_demon_config.limit_count = 1
        task._enter_boss_page = Mock(return_value=True)
        task.check_and_prepare_battle = Mock(return_value=True)
        task.start_battle = Mock(side_effect=lambda: setattr(task, 'total_count', 1))
        with self.assertRaises(TaskEnd):
            task.run()
        task.start_battle.assert_called_once()
        task.set_next_run.assert_called_once_with(task='MetaDemon', success=True)

    def test_imported_templates_match_at_actual_position_and_keep_source_hash(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'upstream/meta_demon_port.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256((root / item['target']).read_bytes()).hexdigest(), item['sha256'])
        for name, point in [('I_MD_CURRENT_ENTRY', (100, 100)),
                            ('I_MD_CURRENT_ENTER', (600, 300)),
                            ('I_MD_CURRENT_SUMMON', (1140, 580))]:
            rule = copy.deepcopy(getattr(MetaDemonAssets, name))
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            x, y = point
            h, w = rule.image.shape[:2]
            frame[y:y+h, x:x+w] = rule.image
            self.assertTrue(rule.match(frame), name)
            self.assertEqual(tuple(rule.roi_front[:2]), point)
            cx, cy = rule.coord()
            self.assertTrue(x <= cx <= x+w and y <= cy <= y+h)

    def test_generated_definitions_match_json(self):
        root = Path(__file__).resolve().parents[1]
        for row in json.loads((root / 'tasks/MetaDemon/current/image.json').read_text(encoding='utf-8')):
            asset = getattr(MetaDemonAssets, 'I_' + row['itemName'].upper())
            self.assertEqual(tuple(asset.roi_back), tuple(map(int, row['roiBack'].split(','))))
            self.assertEqual(asset.threshold, row['threshold'])
            self.assertEqual(Path(asset.file).name, row['imageName'])


if __name__ == '__main__':
    unittest.main()
