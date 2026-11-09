"""待阶段经济及六阶前经验边界；虚拟金币、截图和点击，不操作游戏。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tasks.Chess.runtime.inventory import CardInventory
from tasks.Chess.script_task import ScriptTask


class WaitEconomyTest(unittest.TestCase):
    def task(self, gold=64):
        task = object.__new__(ScriptTask)
        task.select_lineup_strategy('counter_ubume')
        task._reset_economy_state()
        task._current_round_no = 8
        task._card_inventory = CardInventory()
        task._card_tracking_active = True
        state = SimpleNamespace(gold=gold, mode='待', level=3)
        task._read_chess_mode = Mock(side_effect=lambda: state.mode)
        task._read_round_number = Mock(return_value=8)
        task._read_remaining_time = Mock(return_value=90)
        task._read_level = Mock(side_effect=lambda: state.level)
        task._read_shop_gold = Mock(side_effect=lambda: state.gold)
        task.appear = Mock(side_effect=lambda rule: rule is task.I_EXPERIENCE)
        task.screenshot = Mock()
        task._priority_cleanup_inventory_hand = Mock(return_value=False)
        task._clear_economy_click_history = Mock()
        task._handle_battle_sell_stage = Mock(return_value=True)
        task.purchase_lineup_cards_once = Mock(return_value=[])
        task._click_shop_refresh_and_confirm_slots = Mock()
        def click(rule):
            self.assertIs(rule, task.I_EXPERIENCE)
            state.gold -= 4
        task.click = Mock(side_effect=click)
        return task, state

    def run_wait(self, task):
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            return task._run_battle_economy_until_budget_limit()

    def test_screenshot_case_64_gold_buys_three_experience_and_never_refreshes(self):
        task, state = self.task(64)
        self.assertEqual(self.run_wait(task), 'complete')
        self.assertEqual(state.gold, 52)
        self.assertEqual(task.click.call_count, 3)
        task._click_shop_refresh_and_confirm_slots.assert_not_called()
        task.purchase_lineup_cards_once.assert_called_once()
        self.assertFalse(task._economy_battle_mode)
        self.assertIsNone(task._economy_expected_mode)

    def test_pre_six_experience_keeps_at_least_fifty_after_payment(self):
        for gold, expected, clicks in ((54, 50, 1), (55, 51, 1), (53, 53, 0),
                                       (50, 50, 0), (49, 49, 0), (2, 2, 0)):
            task, state = self.task(gold)
            self.assertEqual(self.run_wait(task), 'complete')
            self.assertEqual((state.gold, task.click.call_count), (expected, clicks))
            task._click_shop_refresh_and_confirm_slots.assert_not_called()
            task.purchase_lineup_cards_once.assert_called_once()
            if gold == 2:
                self.assertTrue(task._can_afford_shop_shikigami(4, known_price=1))

    def test_wait_stage_change_cannot_confirm_or_repeat_experience(self):
        task, state = self.task()
        def change_mode(_):
            state.mode = '备'
        task.click.side_effect = change_mode
        self.assertEqual(self.run_wait(task), 'blocked')
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertEqual(task._click_economy_button_and_confirm_gold(
                task.I_EXPERIENCE, 4, '经验', False), 'no_progress')
        task.click.assert_called_once()

    def test_wait_requires_visible_experience_button(self):
        task, _ = self.task()
        task.appear.return_value = False
        task.appear.side_effect = None
        self.assertEqual(self.run_wait(task), 'blocked')
        task.click.assert_not_called()

    def test_confirmed_previous_phase_budget_does_not_hide_wait_income(self):
        for uncertain in (False, True):
            task, state = self.task()
            state.mode = '战'
            task._counter_record_spend(55, 4)
            if uncertain:
                task._unconfirmed_experience_round = 8
            state.mode = '待'
            self.assertEqual(task._counter_effective_gold(64), 51 if uncertain else 64)

    def test_completed_battle_rechecks_economy_on_entering_wait(self):
        clock = SimpleNamespace(now=0.)
        modes = []
        task = SimpleNamespace(
            device=SimpleNamespace(stuck_record_clear=Mock()),
            _refresh_round_state_screenshot=Mock(return_value=False),
            _finish_chess_game_after_open_lineup_missing=lambda _: clock.now >= 4,
            _read_round_number=Mock(return_value=8),
            _read_chess_mode=lambda: '战' if clock.now < 1 else '待',
            _handle_passive_stage=Mock(), SLOW_POLL_INTERVAL=1.,
        )
        task._run_battle_economy_until_budget_limit = lambda: modes.append(task._read_chess_mode()) or 'complete'
        with patch('tasks.Chess.script_task.time.monotonic', side_effect=lambda: clock.now), \
                patch('tasks.Chess.script_task.time.sleep',
                      side_effect=lambda seconds: setattr(clock, 'now', clock.now + seconds)):
            ScriptTask.run_one_round(task, 8)
        self.assertEqual(modes, ['战', '待'])


if __name__ == '__main__':
    unittest.main()
