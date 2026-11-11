"""The final friend settlement must not block the next own summon."""
import unittest
from unittest.mock import Mock

from dev_tools import test_meta_demon as base
from dev_tools import test_meta_demon_resident as resident
from module.exception import GameStuckError, TaskEnd
from tasks.MetaDemon.config import BossType


class FriendSettlementTicketsTest(unittest.TestCase):
    def test_last_card_can_disappear_before_settlement_handoff(self):
        for marker in ['I_MD_FRIEND_OWNER', 'I_CHECK_BOSS_PAGE']:
            task = base.MetaDemonTest().task()
            task._friend_active = True
            task._try_friend_boss = Mock(return_value=None)
            task._close_boss_popup = Mock()
            detail = {'I_MD_SETTLING', marker}
            state, clock = base.MetaDemonTest().replay(task, [
                (1001, detail), (1002, detail), (1003, detail), (1004, {'I_MD_GET_BOSS'})])
            task._return_to_self_discovery = Mock(side_effect=lambda: state.update(visible={'I_MD_SWITCH_TICKET'}))
            with clock:
                self.assertFalse(task.battle_wait(False))
                self.assertTrue(task._enter_boss_page())
                self.assertFalse(task.check_and_switch_ticket())
            task._try_friend_boss.assert_called_once_with(exclude_selected=True)
            task._return_to_self_discovery.assert_called_once()
            self.assertEqual(state['clicks'], ['I_MD_SWITCH_TICKET'])

    def test_battle_not_ended_cannot_use_hidden_card_shortcut(self):
        task = base.MetaDemonTest().task()
        task._friend_active = True
        detail = {'I_MD_SETTLING', 'I_MD_FRIEND_OWNER'}
        _, clock = base.MetaDemonTest().replay(task, [
            (1001, detail | {'BATTLE'}), (1002, {'I_WIN'}), (1003, detail)])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(task.screenshot.call_count, 3)

    def test_occupied_own_card_can_be_selected_after_last_friend_card_disappears(self):
        for marker in ['I_MD_FRIEND_OWNER', 'I_CHECK_BOSS_PAGE']:
            task = base.MetaDemonTest().task()
            _, clock = base.MetaDemonTest().replay(task, [
                (1001, {'I_MD_SETTLING', marker}), (1002, {'I_MD_SELF_SELECTED'})])
            with clock:
                task._return_to_self_discovery()
            task.click.assert_called_once()
            self.assertEqual(task.click.call_args.args[0].name, 'MD_SELF_CARD')

    def task(self, ticket=True):
        task = resident.ResidentTest().task(pending=True)
        task._friend_active = True
        task._friend_settlement_pending = True
        state = {'view': 'settling'}

        def appear(rule, **kwargs):
            if rule is task.I_MD_SETTLING:
                return state['view'] == 'settling'
            if rule is task.I_MD_FIRE:
                return state['view'] in ('own', 'friend')
            if rule is task.I_MD_FRIEND_OWNER:
                return state['view'] in ('settling', 'friend')
            if rule is task.I_MD_SELF_SELECTED:
                return state['view'] in ('self', 'own')
            return False

        def return_self():
            task._friend_active = False
            state['view'] = 'self'

        def summon(**kwargs):
            self.assertEqual(kwargs, {'_summon_only': True})
            task._tickets_checked = True
            task.has_summon_ticket = ticket
            if ticket:
                state['view'] = 'own'
                task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, ''
                task._new_encounter()
            return ticket

        task.appear = Mock(side_effect=appear)
        task._return_to_self_discovery = Mock(side_effect=return_self)
        task.check_and_switch_ticket = Mock(side_effect=summon)
        task._refresh_current_boss_type = Mock()
        task._prioritize_ticket_boss = Mock(return_value=True)
        task._select_attack = Mock(return_value=True)
        task._prepare_lineup = Mock(return_value=True)
        task.check_and_switch_powerful = Mock(return_value=True)
        task.start_battle = Mock(side_effect=TaskEnd)
        return task, state

    def test_resident_last_friend_returns_self_and_summons_without_wait(self):
        task, _ = self.task()
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._return_to_self_discovery.assert_called_once()
        task.check_and_switch_ticket.assert_called_once_with(_summon_only=True)
        task.start_battle.assert_called_once()
        task.ui_goto_page.assert_not_called()
        self.assertTrue(task._resident_summoned_boss)
        self.assertFalse(task._friend_settlement_pending)
        self.assertEqual(task._encounter_attempts, 0)
        task.set_next_run.assert_not_called()

    def test_resident_no_ticket_yields_to_due_task_instead_of_waiting_settlement(self):
        task, _ = self.task(ticket=False)
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.check_and_switch_ticket.assert_called_once_with(_summon_only=True)
        task.start_battle.assert_not_called()
        task.ui_goto_page.assert_called_once()
        self.assertFalse(task.State.done)

    def test_known_empty_ticket_state_does_not_reopen_queue_each_poll(self):
        task, _ = self.task(ticket=False)
        task._tickets_checked, task.has_summon_ticket = True, False
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.check_and_switch_ticket.assert_not_called()
        task._return_to_self_discovery.assert_called_once()

    def test_other_eligible_friend_is_still_preferred(self):
        task, state = self.task()

        def select(**kwargs):
            state['view'] = 'friend'
            task.cur_boss_type, task.cur_boss_name = BossType.FIVE_STARS, '夜刀神'
            return True

        task._try_friend_boss.side_effect = select
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.check_and_switch_ticket.assert_not_called()
        task._return_to_self_discovery.assert_not_called()
        task.start_battle.assert_called_once()

    def test_full_fatigue_does_not_bypass_wait_or_summon_policy(self):
        task, _ = self.task()
        task._read_fatigue.return_value = (112, 100)
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.check_and_switch_ticket.assert_not_called()
        task.start_battle.assert_not_called()

    def test_surviving_own_summon_continues_without_resetting_attempts(self):
        task, state = self.task()
        state['view'] = 'own'
        task._friend_active, task._resident_summoned_boss = False, True
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, ''
        task._encounter_attempts = 1
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._try_friend_boss.assert_not_called()
        task.check_and_switch_ticket.assert_not_called()
        task.start_battle.assert_called_once()
        self.assertEqual(task._encounter_attempts, 1)

    def test_failed_summon_restores_guard_and_actual_running_status(self):
        task, _ = self.task()
        task.device.activity_guard = Mock()
        activity = Mock()
        task.config.meta_demon_resident_activity = activity
        task.check_and_switch_ticket.side_effect = GameStuckError('not confirmed')
        with self.assertRaises(GameStuckError):
            task._resident_loop()
        self.assertEqual([call.args[0] for call in activity.call_args_list], [False, True, False])
        task.device.activity_guard.start.assert_called_once()
        self.assertEqual(task.device.activity_guard.finish.call_count, 2)


if __name__ == '__main__':
    unittest.main()
