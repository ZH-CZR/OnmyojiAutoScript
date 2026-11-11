"""Own-boss settlement can hand off to validated friend assistance."""
import unittest
from unittest.mock import Mock

from dev_tools import test_meta_demon as base
from dev_tools import test_meta_demon_ticket_priority as tickets
from module.exception import GameStuckError
from tasks.MetaDemon.config import BossType


class OwnSettlementTest(unittest.TestCase):
    def task(self):
        task = base.MetaDemonTest().task()
        task._friend_active = False
        task._try_friend_boss = Mock(return_value=True)
        task._return_to_self_discovery = Mock()
        return task

    def replay(self, task, frames):
        return base.MetaDemonTest().replay(task, frames)

    def test_own_settlement_checks_friends_immediately_and_restores_markers(self):
        task = self.task()
        task.device.detect_record.add('OTHER_WAIT')
        _, clock = self.replay(task, [(1001, {'I_WIN'}),
                                    (1002, {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'})])
        with clock:
            self.assertTrue(task.battle_wait(False))
        task._try_friend_boss.assert_called_once_with(skip_settling=True)
        self.assertTrue(task._battle_switched_to_friend)
        self.assertEqual(task.screenshot.call_count, 2)
        self.assertEqual(task.device.detect_record, {'OTHER_WAIT'})

    def test_hidden_challenge_uses_own_selected_card_to_confirm_detail(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_MD_SELF_SELECTED', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'})])
        with clock:
            self.assertFalse(task.battle_wait(False))
        task._try_friend_boss.assert_called_once_with(skip_settling=True)

    def test_battle_and_rewards_are_not_skipped(self):
        task = self.task()
        detail = {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'}
        _, clock = self.replay(task, [(1001, detail | {'BATTLE'}), (1002, {'I_WIN'}), (1003, detail)])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(task.screenshot.call_count, 3)
        task._try_friend_boss.assert_called_once()

    def test_no_friend_keeps_original_settlement_wait(self):
        task = self.task()
        _, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_SETTLING'}),
                                    (1003, {'I_MD_FIRE', 'I_MD_SETTLING'}),
                                    (1004, {'I_MD_FIRE'}), (1005.1, {'I_MD_FIRE'})])
        with clock:
            self.assertFalse(task.battle_wait(False))
        task._try_friend_boss.assert_not_called()
        self.assertEqual(task.screenshot.call_count, 4)

    def test_rejected_or_finished_friends_return_to_same_settlement_once(self):
        for result in [None, False]:
            task = self.task()
            task._try_friend_boss.return_value = result
            detail = {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'}
            _, clock = self.replay(task, [(1001, detail), (1002, detail),
                                        (1003, {'I_MD_FIRE'}), (1004.1, {'I_MD_FIRE'})])
            with clock:
                self.assertFalse(task.battle_wait(False))
            task._try_friend_boss.assert_called_once()
            task._return_to_self_discovery.assert_called_once()
            self.assertFalse(getattr(task, '_battle_switched_to_friend', False))

    def test_opening_friend_does_not_charge_old_attack_to_new_encounter(self):
        task = self.task()
        task._encounter_attempts = 2
        task.run_general_battle = Mock(side_effect=lambda *_: task.battle_wait(False))

        def select(**kwargs):
            task._friend_active = True
            task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
            task._new_encounter()
            return True

        task._try_friend_boss.side_effect = select
        _, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'})])
        with clock:
            task._fight_current_boss()
        self.assertEqual(task.total_count, 1)
        self.assertEqual(task._encounter_attempts, 0)
        self.assertTrue(task._friend_active)

    def test_invalid_friend_scan_preserves_timeout_and_markers(self):
        task = self.task()
        task.device.detect_record.add('OTHER_WAIT')
        task._try_friend_boss.side_effect = GameStuckError('unconfirmed selection')
        _, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'})])
        with clock, self.assertRaises(GameStuckError):
            task.battle_wait(False)
        self.assertEqual(task.device.detect_record, {'OTHER_WAIT'})

    def test_no_eligible_friend_keeps_original_total_deadline(self):
        task = self.task()
        task._try_friend_boss.return_value = None
        detail = {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'}
        _, clock = self.replay(task, [(1001, detail), (1301, detail)])
        with clock, self.assertRaises(GameStuckError):
            task.battle_wait(False)
        task._try_friend_boss.assert_called_once()

    def test_temporary_summon_flag_is_restored_on_battle_error(self):
        task = tickets.TicketPriorityTest().task()
        task.start_battle.side_effect = GameStuckError('battle failed')
        with self.assertRaises(GameStuckError):
            task._prioritize_ticket_boss()
        self.assertFalse(task._ticket_priority_own_battle)
        task._resume_ticket_friend.assert_not_called()

    def test_occupied_own_card_is_clickable_without_empty_icon(self):
        task = base.MetaDemonTest().task()
        state, clock = self.replay(task, [(1001, {'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'}),
                                        (1002, {'I_MD_SELF_SELECTED', 'I_MD_FRIEND_OWNER'})])
        with clock:
            task._return_to_self_discovery()
        task.click.assert_called_once()
        target = task.click.call_args.args[0]
        self.assertEqual(target.name, 'MD_SELF_CARD')
        self.assertFalse(task._friend_active)

    def test_priority_summon_restores_original_friend_without_extra_scan(self):
        task = tickets.TicketPriorityTest().task()

        def battle():
            self.assertTrue(task._ticket_priority_own_battle)

        task.start_battle.side_effect = battle
        task.appear = Mock(side_effect=lambda target, **_: target is task.I_MD_SETTLING)
        self.assertTrue(task._prioritize_ticket_boss())
        self.assertFalse(task._ticket_priority_own_battle)
        task._resume_ticket_friend.assert_called_once()
        task.check_and_switch_ticket.assert_called_once_with(_summon_only=True)
        self.assertFalse(task._tickets_checked)

    def test_temporary_summon_settlement_does_not_replace_saved_friend(self):
        task = self.task()
        task._ticket_priority_own_battle = True
        _, clock = self.replay(task, [(1001, {'I_MD_FIRE', 'I_MD_SETTLING', 'I_MD_FRIEND_REMAINING'})])
        with clock:
            self.assertFalse(task.battle_wait(False))
        task._try_friend_boss.assert_not_called()
        self.assertFalse(getattr(task, '_battle_switched_to_friend', False))


if __name__ == '__main__':
    unittest.main()
