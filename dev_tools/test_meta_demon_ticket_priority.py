"""Ticket priority and interrupted friend encounter replay without game input."""
import unittest
from unittest.mock import Mock

import numpy as np

from dev_tools import test_meta_demon as base
from dev_tools import test_meta_demon_lineups as lineups
from module.exception import GameStuckError
from module.exception import TaskEnd
from types import SimpleNamespace
from tasks.MetaDemon.config import BossType


class TicketPriorityTest(unittest.TestCase):
    def task(self, fatigue=71):
        task = base.MetaDemonTest().task()
        task._friend_active = True
        task.cur_boss_type = BossType.FIVE_STARS
        task.cur_boss_name = '白藏主'
        task._encounter_attempts = 1
        task._read_fatigue = Mock(return_value=(fatigue, 100))
        task.device.image = np.random.default_rng(42).integers(0, 256, (720, 1280, 3), dtype=np.uint8)
        task._selected_friend_frame = Mock(return_value=(365, 475))
        task._return_to_self_discovery = Mock()
        task.check_and_switch_ticket = Mock(return_value=True)
        task._resume_ticket_friend = Mock(return_value=True)
        task._select_attack = Mock(return_value=True)
        task._prepare_lineup = Mock(return_value=True)
        task.check_and_switch_powerful = Mock(return_value=True)
        task.start_battle = Mock()
        task.screenshot = Mock()
        task.is_in_prepare = Mock(return_value=False)
        task.appear = Mock(return_value=False)
        return task

    def test_boundary_and_no_ticket_do_not_switch(self):
        for fatigue, checked, has_ticket in [(70, False, False), (0, True, True), (71, True, False)]:
            task = self.task(fatigue)
            task._tickets_checked, task.has_summon_ticket = checked, has_ticket
            self.assertTrue(task._prioritize_ticket_boss())
            task._return_to_self_discovery.assert_not_called()

    def test_no_friend_does_not_probe(self):
        task = self.task()
        task._friend_active = False
        self.assertTrue(task._prioritize_ticket_boss())
        task._read_fatigue.assert_not_called()

    def test_first_attack_then_high_summon_then_resume_original_count(self):
        task = self.task()
        def summon(**kwargs):
            task._encounter_attempts = 0
            task.cur_boss_type = BossType.SIX_STARS
            return True
        task.check_and_switch_ticket.side_effect = summon
        self.assertTrue(task._prioritize_ticket_boss())
        task.start_battle.assert_called_once()
        snapshot = task._resume_ticket_friend.call_args.args[0]
        self.assertEqual(snapshot[1:], (BossType.FIVE_STARS, '白藏主', 1))
        self.assertEqual(task.check_and_switch_ticket.call_args_list[0].kwargs, {'_summon_only': True})
        self.assertEqual(task.check_and_switch_ticket.call_args_list[1].kwargs,
                         {'_summon_only': True, '_probe_only': True})

    def test_no_ticket_probe_resumes_without_battle_or_marking_done(self):
        task = self.task()
        task.check_and_switch_ticket.return_value = False
        self.assertTrue(task._prioritize_ticket_boss())
        task.start_battle.assert_not_called()
        self.assertFalse(task.State.done)
        task._resume_ticket_friend.assert_called_once()

    def test_unknown_card_blocks_switch(self):
        task = self.task()
        task._selected_friend_frame.return_value = None
        with self.assertRaises(GameStuckError):
            task._prioritize_ticket_boss()
        task._return_to_self_discovery.assert_not_called()

    def test_attack_cap_keeps_current_boss(self):
        task = self.task()
        task._select_attack.return_value = False
        self.assertFalse(task._prioritize_ticket_boss())
        task.start_battle.assert_not_called()
        task._resume_ticket_friend.assert_not_called()

    def test_resident_full_fatigue_does_not_write_schedule(self):
        task = self.task()
        task._resident_mode = True
        task._read_fatigue.side_effect = [(71, 100), (101, 100)]
        self.assertFalse(task._prioritize_ticket_boss())
        task.set_next_run.assert_not_called()
        task.start_battle.assert_not_called()

    def test_resident_inserted_summon_yields_before_another_attack(self):
        task = self.task()
        task._resident_mode = True
        task.conf.scheduler.enable = True
        task.config.reload = Mock()
        task.config.update_scheduler = Mock()
        task.config.normal_pending_task = task.config.pending_task = []
        task.appear.side_effect = lambda rule: rule is task.I_MD_FIRE
        task._refresh_current_boss_type = Mock()
        task.start_battle.side_effect = lambda: setattr(
            task.config, 'normal_pending_task', [SimpleNamespace(command='WantedQuests')])
        with self.assertRaises(TaskEnd):
            task._prioritize_ticket_boss()
        task.start_battle.assert_called_once()
        task._resume_ticket_friend.assert_not_called()
        task.set_next_run.assert_not_called()

    def test_old_total_limit_does_not_interrupt_summon_or_friend_restore(self):
        task = self.task()
        task.total_count = task.limit_count
        self.assertTrue(task._prioritize_ticket_boss())
        task.start_battle.assert_called_once()
        task._resume_ticket_friend.assert_called_once()

    def test_resume_tracks_shifted_card_and_second_attack_plan(self):
        task = self.task()
        task.__dict__.pop('_resume_ticket_friend')
        portrait = task.device.image[373:435, 48:300].copy()
        image = np.zeros_like(task.device.image)
        image[493:555, 48:300] = portrait
        task.device.image = image
        task._selected_friend_frame.return_value = (485, 595)
        task.cur_boss_type, task.cur_boss_name = BossType.SIX_STARS, '其他'
        def refresh(**kwargs):
            task.cur_boss_type, task.cur_boss_name = BossType.FIVE_STARS, '白藏主'
        task._refresh_current_boss_type = Mock(side_effect=refresh)
        state, clock = base.MetaDemonTest().replay(task, [
            (1001, set()), (1002, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
            (1003, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
        with clock:
            self.assertTrue(task._resume_ticket_friend((portrait, BossType.FIVE_STARS, '白藏主', 1)))
        self.assertEqual(task._encounter_attempts, 1)
        self.assertTrue(task._friend_active)
        task.click.assert_called_once()
        # The original plan must choose attack two, rather than restarting one.
        configured = lineups.MetaDemonLineupTest().task()
        task.conf.lineup_config = configured.conf.lineup_config
        task.__dict__.pop('_select_attack')
        self.assertTrue(task._select_attack())
        self.assertEqual(task._active_attack.lineup, '活动,第二队')

    def test_missing_and_duplicate_cards_never_guess(self):
        task = self.task()
        portrait = task.device.image[373:435, 48:300].copy()
        empty = np.zeros_like(task.device.image)
        self.assertIsNone(task._locate_ticket_friend(empty, portrait))
        empty[373:435, 48:300] = portrait
        empty[493:555, 48:300] = portrait
        with self.assertRaises(GameStuckError):
            task._locate_ticket_friend(empty, portrait)

    def test_ticket_flag_and_probe_do_not_summon(self):
        for visible, expected in [({'I_MD_GET_BOSS'}, False),
                                  ({'I_MD_GET_BOSS', 'I_MD_SIX_STARS'}, True)]:
            task = base.MetaDemonTest().task()
            task._close_boss_popup = Mock()
            _, clock = base.MetaDemonTest().replay(task, [(1001, visible)])
            with clock:
                self.assertEqual(task.check_and_switch_ticket(_summon_only=True, _probe_only=True), expected)
            self.assertIs(task.has_summon_ticket, expected)
            self.assertFalse(task.State.done)
            task.click.assert_not_called()

    def test_priority_still_chooses_highest_if_fatigue_recovers_during_navigation(self):
        task = base.MetaDemonTest().task()
        task.O_MD_FATIGUE.ocr.return_value = (70, 30, 100)
        task._classify_selected_ticket = Mock(return_value=BossType.SIX_STARS)
        task._refresh_current_boss_type = Mock(return_value=BossType.SIX_STARS)
        state, clock = base.MetaDemonTest().replay(task, [
            (1001, {'I_MD_GET_BOSS', 'I_MD_ONE_STAR', 'I_MD_SIX_STARS'}),
            (1002, {'I_MD_GET_BOSS', 'I_MD_CHECK_SELECTED'}),
            (1003, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket(_summon_only=True))
        self.assertEqual(task.cur_boss_type, BossType.SIX_STARS)
        self.assertEqual(state['clicks'], ['I_MD_GET_BOSS'])
        self.assertTrue(task.has_summon_ticket)

    def test_existing_own_boss_is_not_counted_as_new_summon(self):
        task = base.MetaDemonTest().task()
        task._refresh_current_boss_type = Mock()
        state, clock = base.MetaDemonTest().replay(task, [(1001, {'I_MD_FIRE'})])
        with clock:
            self.assertFalse(task.check_and_switch_ticket(_summon_only=True))
        task._refresh_current_boss_type.assert_not_called()
        self.assertEqual(state['clicks'], [])

    def test_same_portrait_different_name_is_not_original_friend(self):
        task = self.task()
        portrait = task.device.image[373:435, 48:300].copy()
        image = np.zeros_like(task.device.image)
        image[493:555, 48:300] = portrait
        image[493:513, 132:300] = 255 - portrait[:20, 84:]
        self.assertIsNone(task._locate_ticket_friend(image, portrait))

    def test_restore_identity_mismatch_does_not_restore_attempts(self):
        task = self.task()
        task.__dict__.pop('_resume_ticket_friend')
        portrait = task.device.image[373:435, 48:300].copy()
        task.cur_boss_name = '其他'
        task._encounter_attempts = 0
        task._refresh_current_boss_type = Mock()
        _, clock = base.MetaDemonTest().replay(task, [
            (1001, set()), (1002, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
            (1003, {'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
        with clock, self.assertRaises(GameStuckError):
            task._resume_ticket_friend((portrait, BossType.FIVE_STARS, '白藏主', 1))
        self.assertEqual(task._encounter_attempts, 0)


if __name__ == '__main__':
    unittest.main()
