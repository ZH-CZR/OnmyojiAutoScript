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
        for values, expected in [([4, 4], BossType.FOUR_STARS),
                                 ([5, 6, 6], BossType.SIX_STARS),
                                 ([4, 5, 4], None), ([0, 0, 0], None)]:
            with self.subTest(values=values):
                task = self.task()
                frames = iter(self.card_image(value) for value in values)
                task.screenshot = Mock(side_effect=lambda: setattr(task.device, 'image', next(frames)))
                task.is_in_prepare = Mock(return_value=False)
                task.appear = Mock(return_value=True)
                with patch('tasks.MetaDemon.friend_assist.time.sleep'):
                    self.assertEqual(task._detect_friend_boss_star(), expected)

    def test_owner_loss_blocks_star_reading(self):
        task = self.task()
        task.screenshot = Mock()
        task.is_in_prepare = Mock(return_value=False)
        task.appear = Mock(side_effect=lambda t: t is task.I_MD_FIRE)
        task._friend_star_observation = Mock()
        self.assertIsNone(task._detect_friend_boss_star())
        task._friend_star_observation.assert_not_called()

    @staticmethod
    def card_image(count, top=365, colors=None):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        bottom = top + 110
        image[top - 1:top + 2, 40:310] = (255, 200, 40)
        image[bottom - 1:bottom + 2, 40:310] = (255, 200, 40)
        for index in range(6):
            color = (colors[index % len(colors)] if colors else (255, 180, 0)) if index < count else (120, 120, 120)
            image[bottom - 30:bottom - 22, 56 + 11 * index:67 + 11 * index] = color
        # A skill multiplier in the center must have no effect on the count.
        image[428:451, 513:551] = (255, 255, 255)
        return image

    def test_all_star_counts_ignore_yellow_purple_or_mixed_color(self):
        for count in range(1, 7):
            for colors in [[(255, 180, 0)], [(130, 40, 180)],
                           [(255, 180, 0), (130, 40, 180)]]:
                with self.subTest(count=count, colors=colors):
                    result = self.task()._friend_star_observation(self.card_image(count, colors=colors))
                    self.assertEqual(result[0], BossType(count))

    def test_own_boss_counts_yellow_purple_and_mixed_gems_the_same(self):
        for count in range(1, 7):
            for colors in [[(255, 180, 0)], [(130, 40, 180)],
                           [(255, 180, 0), (130, 40, 180)]]:
                task = self.task()
                image = self.card_image(count, colors=colors)
                image[207:215, 56:122] = image[445:453, 56:122]
                task.device.image = image
                task.screenshot = Mock()
                task.appear = Mock(return_value=True)
                with patch('tasks.MetaDemon.script_task.time.sleep'):
                    self.assertEqual(task._detect_current_boss_star(), BossType(count))

    def test_second_row_is_located_instead_of_own_or_first_card(self):
        image = self.card_image(4, top=485)
        image[207:215, 56:124] = (255, 180, 0)
        result = self.task()._friend_star_observation(image)
        self.assertEqual(result, (BossType.FOUR_STARS, 485, 595))

    def test_five_gems_do_not_bleed_into_sixth_slot(self):
        # A ten-pixel spacing incorrectly samples five colored pixels from the
        # fifth gem in the sixth slot. The real eleven-pixel spacing must win.
        image = self.card_image(5)
        self.assertEqual(self.task()._friend_star_observation(image)[0], BossType.FIVE_STARS)

    def test_missing_ambiguous_frame_and_scattered_gems_are_unknown(self):
        images = [np.zeros((720, 1280, 3), dtype=np.uint8)]
        scattered = self.card_image(4)
        scattered[445:453, 66:74] = (120, 120, 120)
        images.append(scattered)
        ambiguous = self.card_image(4)
        second = self.card_image(6, top=485)
        ambiguous[484:600] = second[484:600]
        images.append(ambiguous)
        for image in images:
            self.assertIsNone(self.task()._friend_star_observation(image))

    def test_selection_change_between_frames_is_not_confirmation(self):
        task = self.task()
        frames = iter([self.card_image(4), self.card_image(4, top=485), self.card_image(4)])
        task.screenshot = Mock(side_effect=lambda: setattr(task.device, 'image', next(frames)))
        task.is_in_prepare = Mock(return_value=False)
        task.appear = Mock(return_value=True)
        with patch('tasks.MetaDemon.friend_assist.time.sleep'):
            self.assertIsNone(task._detect_friend_boss_star())

    def test_four_star_uses_normal_attack_when_only_six_star_is_powerful(self):
        task = self.task()
        task._friend_active = True
        task.device.image = self.card_image(4)
        task.screenshot = Mock()
        task.is_in_prepare = Mock(return_value=False)
        task.appear = Mock(return_value=True)
        task._detect_boss_name = Mock(return_value='鬼切')
        task.conf.meta_demon_config.powerful_list = '6'
        task.ui_click = Mock(return_value=True)
        with patch('tasks.MetaDemon.friend_assist.time.sleep'):
            self.assertEqual(task._refresh_current_boss_type(), BossType.FOUR_STARS)
        task._select_attack()
        self.assertFalse(task._active_attack.powerful)
        self.assertTrue(task.check_and_switch_powerful())
        task.ui_click.assert_called_once_with(task.I_MD_ENABLE_POWERFUL_FIRE,
                                             task.I_MD_DISABLE_POWERFUL_FIRE, interval=0.6, timeout=5)

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

    def test_friend_settlement_returns_without_waiting_and_restores_markers(self):
        task = self.task()
        task._friend_active = True
        task.device.detect_record.add('OTHER_WAIT')
        _, clock = self.replay(task, [(1001, {'I_WIN'}),
                                    (1002, {'I_MD_FIRE', 'I_MD_SETTLING'})])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(task.screenshot.call_count, 2)
        self.assertTrue(task._friend_settlement_pending)
        self.assertEqual(task.device.detect_record, {'OTHER_WAIT'})

    def test_friend_still_in_battle_does_not_skip_rewards_for_settlement(self):
        task = self.task()
        task._friend_active = True
        _, clock = self.replay(task, [
            (1001, {'BATTLE', 'I_MD_FIRE', 'I_MD_SETTLING'}),
            (1002, {'I_WIN'}), (1003, {'I_MD_FIRE', 'I_MD_SETTLING'})])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(task.screenshot.call_count, 3)

    def test_friend_settlement_without_challenge_button_can_reenter_detail(self):
        task = self.task()
        task._friend_active = True
        detail = {'I_MD_SETTLING', 'I_MD_FRIEND_OWNER', 'I_MD_FRIEND_REMAINING'}
        _, clock = self.replay(task, [(1001, detail), (1002, detail)])
        with clock:
            self.assertFalse(task.battle_wait(False))
            self.assertTrue(task._enter_boss_page())
        self.assertTrue(task._friend_settlement_pending)
        task.ui_goto_page.assert_not_called()

    def test_next_friend_is_checked_before_existing_settling_fire(self):
        task = self.task()
        task._friend_settlement_pending = True
        task._encounter_attempts = 2
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
        task._refresh_current_boss_type = Mock()
        state, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_SETTLING'})])

        def select(**kwargs):
            self.assertTrue(kwargs['exclude_selected'])
            state['visible'] = {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}
            task._friend_active = True
            task._new_encounter()
            return True

        task._try_friend_boss = Mock(side_effect=select)
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertFalse(task._friend_settlement_pending)
        self.assertEqual(task._encounter_attempts, 0)
        self.assertEqual(state['clicks'], [])

    def test_no_other_friend_returns_self_instead_of_rechallenging_finished_boss(self):
        task = self.task()
        task._friend_settlement_pending = True
        task._try_friend_boss = Mock(return_value=None)
        task._close_boss_popup = Mock()
        state, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_SETTLING'}),
                                        (1002, {'I_MD_GET_BOSS'})])
        task._return_to_self_discovery = Mock(side_effect=lambda: state.update(visible={'I_MD_SWITCH_TICKET'}))
        with clock:
            self.assertFalse(task.check_and_switch_ticket())
        task._try_friend_boss.assert_called_once_with(exclude_selected=True)
        task._return_to_self_discovery.assert_called_once()
        self.assertEqual(state['clicks'], ['I_MD_SWITCH_TICKET'])

    def test_candidate_search_excludes_finished_card_and_finds_other_row(self):
        for other in [False, True]:
            task = self.task()
            image = self.card_image(4)
            template = task.I_MD_FRIEND_REMAINING.image
            h, w = template.shape[:2]
            image[408:408+h, 147:147+w] = template
            if other:
                image[523:523+h, 147:147+w] = template
            task.device.image = image
            state, clock = self.replay(task, [
                (1001, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
                (1002, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
            original_appear = task.appear.side_effect
            task.appear.side_effect = lambda target, **kwargs: (
                target.match(image) if getattr(target, 'name', '') == 'I_MD_FRIEND_REMAINING'
                else original_appear(target, **kwargs))
            with clock:
                self.assertEqual(task._try_friend_boss(exclude_selected=True), True if other else None)
            if other:
                task.click.assert_called_once()
                self.assertGreater(task.click.call_args.args[0].roi_front[1], 475)
            else:
                task.click.assert_not_called()

    def test_selecting_next_friend_does_not_accept_stale_settling_detail(self):
        task = self.task()
        task.device.image = self.card_image(4)
        task._selected_friend_frame = Mock(return_value=(365, 475))
        state, clock = self.replay(task, [
            (1001, {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_OWNER'}),
            (1002, {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_OWNER'}),
            (1003, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
            (1004, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
        state['visible'] = {'I_MD_FRIEND_REMAINING'}
        with clock:
            self.assertTrue(task._try_friend_boss(exclude_selected=True))
        self.assertEqual(task.screenshot.call_count, 4)
        task.click.assert_called_once()


if __name__ == '__main__':
    unittest.main()
