"""Friend assistance replay; no device or game is created."""
import copy
import unittest
from unittest.mock import Mock, patch

import numpy as np

from dev_tools import test_meta_demon as base
from module.exception import GameStuckError
from tasks.MetaDemon.config import BossType


class FriendAssistTest(unittest.TestCase):
    def task(self):
        return base.MetaDemonTest().task()

    def replay(self, task, frames):
        return base.MetaDemonTest().replay(task, frames)

    def test_no_friend_does_not_click(self):
        task = self.task()
        task.appear = Mock(return_value=False)
        self.assertIsNone(task._try_friend_boss())
        task.click.assert_not_called()

    def test_matching_owner_selects_once_and_starts_encounter(self):
        task = self.task()
        task._encounter_attempts = 3
        state, clock = self.replay(task, [
            (1001, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
            (1002, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
        state['visible'] = {'I_MD_FRIEND_REMAINING'}
        with clock:
            self.assertTrue(task._try_friend_boss())
        self.assertTrue(task._friend_active)
        self.assertEqual(task._encounter_attempts, 0)
        task.click.assert_called_once()
        self.assertEqual(state['clicks'], [])

    def test_mismatch_returns_to_self_without_challenging(self):
        task = self.task()
        task._return_to_self_discovery = Mock()
        state, clock = self.replay(task, [
            (1001, {'I_MD_FIRE'}), (1002, {'I_MD_FIRE'})])
        state['visible'] = {'I_MD_FRIEND_REMAINING'}
        with clock:
            self.assertFalse(task._try_friend_boss())
        task._return_to_self_discovery.assert_called_once()
        task.run_general_battle.assert_not_called()
        self.assertFalse(getattr(task, '_friend_active', False))

    def test_missing_detail_times_out_without_reclick(self):
        task = self.task()
        state, clock = self.replay(task, [(1001, set()), (1016, set())])
        state['visible'] = {'I_MD_FRIEND_REMAINING'}
        with clock, self.assertRaises(GameStuckError):
            task._try_friend_boss()
        task.click.assert_called_once()

    def test_return_requires_selected_self_and_clears_friend_state(self):
        task = self.task()
        task._friend_active = True
        state, clock = self.replay(task, [
            (1001, {'I_MD_SELF_DISCOVERY'}),
            (1002, {'I_MD_SELF_SELECTED'})])
        with clock:
            task._return_to_self_discovery()
        self.assertEqual(state['clicks'], ['I_MD_SELF_DISCOVERY'])
        self.assertFalse(task._friend_active)

    def test_return_failure_has_three_click_limit_and_no_navigation(self):
        task = self.task()
        state, clock = self.replay(task, [
            (1000 + i, {'I_MD_SELF_DISCOVERY'}) for i in range(1, 17)])
        click_times = []
        original_click = task.appear_then_click.side_effect

        def click(*args, **kwargs):
            click_times.append(state['now'])
            return original_click(*args, **kwargs)

        task.appear_then_click.side_effect = click
        with clock, self.assertRaises(GameStuckError):
            task._return_to_self_discovery()
        self.assertEqual(state['clicks'], ['I_MD_SELF_DISCOVERY'] * 3)
        self.assertTrue(all(b - a >= 2 for a, b in zip(click_times, click_times[1:])))
        task.ui_goto_page.assert_not_called()

    def test_friend_star_requires_two_equal_strict_readings(self):
        for values, expected in [(['×6', '×6'], BossType.SIX_STARS),
                                 (['x5', 'x6', 'x6'], BossType.SIX_STARS),
                                 (['16', '16', '16'], None),
                                 (['x0', 'x7', ''], None)]:
            with self.subTest(values=values):
                task = self.task()
                task.screenshot = Mock()
                task.is_in_prepare = Mock(return_value=False)
                task.appear = Mock(return_value=True)
                task.O_MD_FRIEND_STAR = Mock()
                task.O_MD_FRIEND_STAR.ocr.side_effect = values
                with patch('tasks.MetaDemon.friend_assist.time.sleep'):
                    self.assertEqual(task._detect_friend_boss_star(), expected)

    def test_owner_loss_blocks_star_reading(self):
        task = self.task()
        task.screenshot = Mock()
        task.is_in_prepare = Mock(return_value=False)
        task.appear = Mock(side_effect=lambda t: t is task.I_MD_FIRE)
        task.O_MD_FRIEND_STAR = Mock()
        self.assertIsNone(task._detect_friend_boss_star())
        task.O_MD_FRIEND_STAR.ocr.assert_not_called()

    def test_surviving_friend_keeps_attempts_and_revalidates_identity(self):
        task = self.task()
        task._friend_active = True
        task._encounter_attempts = 1
        task.cur_boss_name = '夜刀神'
        task.cur_boss_type = BossType.SIX_STARS
        task._refresh_current_boss_type = Mock()
        state, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertEqual(task._encounter_attempts, 1)
        task._refresh_current_boss_type.assert_called_once()

    def test_new_friend_enters_existing_plan_without_opening_queue(self):
        task = self.task()
        state, clock = self.replay(task, [(1001, {'I_MD_SWITCH_TICKET'})])

        def select_friend():
            state['visible'] = {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}
            task._friend_active = True
            return True

        task._try_friend_boss = Mock(side_effect=select_friend)
        task.cur_boss_type, task.cur_boss_name = BossType.SIX_STARS, '夜刀神'
        task._refresh_current_boss_type = Mock()
        task._select_attack = Mock(return_value=True)
        task._prepare_lineup = Mock(return_value=True)
        task.check_and_switch_powerful = Mock(return_value=True)
        with clock:
            self.assertTrue(task.check_and_prepare_battle())
        task._select_attack.assert_called_once()
        task._prepare_lineup.assert_called_once()
        self.assertEqual(state['clicks'], [])

    def test_mismatched_friend_returns_then_opens_original_summon_queue(self):
        task = self.task()
        task._try_friend_boss = Mock(return_value=False)
        task._close_boss_popup = Mock()
        state, clock = self.replay(task, [
            (1001, {'I_MD_SWITCH_TICKET'}), (1002, {'I_MD_GET_BOSS'})])
        with clock:
            self.assertFalse(task.check_and_switch_ticket())
        self.assertEqual(state['clicks'], ['I_MD_SWITCH_TICKET'])

    def test_unplanned_prepare_during_friend_selection_is_rejected(self):
        task = self.task()
        state, clock = self.replay(task, [(1001, set())])
        state['visible'] = {'I_MD_FRIEND_REMAINING'}
        task.is_in_prepare = Mock(return_value=True)
        with clock, self.assertRaises(GameStuckError):
            task._try_friend_boss()
        task.run_general_battle.assert_not_called()

    def test_unknown_friend_star_or_name_blocks_lineup_and_battle(self):
        for star, name in [(None, '夜刀神'), (BossType.SIX_STARS, '')]:
            task = self.task()
            task._friend_active = True
            task.cur_boss_type, task.cur_boss_name = star, name
            task._refresh_current_boss_type = Mock()
            task._select_attack = Mock()
            _, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
            with clock, self.assertRaises(GameStuckError):
                task.check_and_prepare_battle()
            task._select_attack.assert_not_called()
            task.run_general_battle.assert_not_called()

    def test_templates_are_local_and_owner_is_required_in_fixed_region(self):
        task = self.task()
        owner = copy.copy(task.I_MD_FRIEND_OWNER)
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertFalse(owner.match(image))
        image[103:140, 515:548] = owner.image
        self.assertTrue(owner.match(image))
        image[103:140, 515:548] = 0
        image[300:337, 515:548] = owner.image
        self.assertFalse(owner.match(image))


if __name__ == '__main__':
    unittest.main()
