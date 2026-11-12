"""P0 交易与阵容保护；模拟画面，不连接游戏或写用户配置。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from dev_tools.test_chess_shop import ShopProbe
from tasks.Chess.runtime.hand_operations import ChessHandOperationsMixin
from tasks.Chess.strategy.lineup import LINEUP_REGISTRY
from tasks.Chess.strategy.lineup_strategy import build_lineup_strategy


def slots(names):
    return {i: {'name': name, 'image': np.zeros((4, 4), dtype=np.uint8)}
            for i, name in enumerate(names, 1)}


class ChessP0Test(unittest.TestCase):
    def test_registered_lineups_have_unique_positions(self):
        for entry in LINEUP_REGISTRY.values():
            positions = [u['position'] for u in entry['strategy']['shikigami'].values()]
            self.assertEqual(len(positions), len(set(positions)), entry['display_name'])

    def test_conflict_reports_lineup_position_and_units(self):
        with self.assertRaisesRegex(ValueError, '测试.*7.*雪女.*觉'):
            build_lineup_strategy(dict(key='test', display_name='测试',
                                       shikigami_positions={'雪女': 7, '觉': 7}))

    def refresh_task(self, snapshots, gold=None):
        task = ShopProbe([{'refresh'}])
        task._shop_slot_refresh_snapshot = Mock(side_effect=snapshots)
        if gold is not None:
            task._read_shop_gold = Mock(side_effect=gold)
        return task

    def refresh(self, task):
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            return task._click_shop_refresh_and_confirm_slots(True)

    def test_same_shop_with_confirmed_payment_needs_two_stable_frames(self):
        same = slots('abcde')
        task = self.refresh_task([same] * 3, [100, 98, 98])
        self.assertEqual(self.refresh(task), 'success')
        task.click.assert_called_once_with('refresh')
        self.assertEqual(task._shop_slot_refresh_snapshot.call_count, 3)

    def test_one_or_two_changed_slots_can_confirm_without_gold_ocr(self):
        for names in ('xbcde', 'xycde'):
            with self.subTest(names=names):
                task = self.refresh_task([slots('abcde'), slots(names), slots(names)],
                                         [None, None, None])
                self.assertEqual(self.refresh(task), 'success')
                task.click.assert_called_once()

    def test_delayed_payment_and_animation_do_not_reclick(self):
        task = self.refresh_task([slots(n) for n in ('abcde', 'xbcde', 'xycde', 'xycde')],
                                 [100, 100, None, 98])
        self.assertEqual(self.refresh(task), 'success')
        task.click.assert_called_once()

    def test_unknown_refresh_blocks_same_round_but_next_confirmed_round_can_refresh(self):
        task = self.refresh_task([slots('abcde')] * 5)
        task._current_round_no = 12
        self.assertEqual(self.refresh(task), 'no_progress')
        self.assertEqual(self.refresh(task), 'no_progress')
        task.click.assert_called_once()
        task._current_round_no = 13
        task._read_round_number = Mock(return_value=13)
        task._shop_slot_refresh_snapshot = Mock(side_effect=[slots(n) for n in ('abcde', 'xbcde', 'xbcde')])
        self.assertEqual(self.refresh(task), 'success')
        self.assertEqual(task.click.call_count, 2)
        self.assertFalse(task._unconfirmed_shop_refresh)

    def test_round_change_cannot_confirm_natural_shop_refresh(self):
        task = self.refresh_task([slots('abcde')])
        task._read_round_number = Mock(side_effect=[12, 12, 13])
        self.assertEqual(self.refresh(task), 'no_progress')
        self.assertTrue(task._unconfirmed_shop_refresh)
        task._shop_slot_refresh_snapshot.assert_called_once()

    def test_phase_change_during_slow_scan_never_clicks(self):
        task = self.refresh_task([slots('abcde')])
        task._read_chess_mode = Mock(side_effect=['战', '战', '鬼'])
        self.assertEqual(self.refresh(task), 'no_progress')
        task.click.assert_not_called()

    def test_unstable_shop_does_not_confirm_even_with_payment(self):
        task = self.refresh_task([slots(n) for n in ('abcde', 'xbcde', 'xycde', 'xyzde', 'xyzwe')],
                                 [100, 98, 98, 98, 98])
        self.assertEqual(self.refresh(task), 'no_progress')
        task.click.assert_called_once()

    def test_near_deadline_and_unknown_round_never_click(self):
        for remaining, round_no in ((0, 12), (None, 12), (60, None)):
            task = self.refresh_task([])
            task._read_remaining_time = Mock(return_value=remaining)
            task._read_round_number = Mock(return_value=round_no)
            self.assertEqual(self.refresh(task), 'no_progress')
            task.click.assert_not_called()

    def test_refresh_remains_available_below_old_cutoffs_in_both_phases(self):
        for mode in ('备', '战'):
            for remaining in (15, 5, 4):
                task = self.refresh_task([slots('abcde'), slots('xbcde'), slots('xbcde')])
                task._read_chess_mode = Mock(return_value=mode)
                task._read_remaining_time = Mock(return_value=remaining)
                with patch('tasks.Chess.runtime.economy.time.sleep'):
                    self.assertEqual(task._click_shop_refresh_and_confirm_slots(mode == '战'), 'success')
                task.click.assert_called_once()

    def test_ambiguous_purchase_does_not_retry_or_sell_lineup(self):
        task = ShopProbe([{'refresh'}])
        task._recognize_shop_slot = Mock(return_value={'source': 'test', 'score': 1.})
        task._can_afford_shop_shikigami = Mock(return_value=True)
        task._shikigami_display_name = Mock(return_value='山兔')
        task._free_one_hand_slot_for_purchase = Mock(return_value={'sold_non_lineup': []})
        task.sell_one_lineup_hand_card = Mock()
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertFalse(task._buy_shop_slot(1, 'card', 'yamausagi'))
        task._free_one_hand_slot_for_purchase.assert_not_called()
        task.click.assert_called_once()
        task.sell_one_lineup_hand_card.assert_not_called()

    def test_delayed_purchase_confirmation_does_not_sell_any_card(self):
        task = ShopProbe([{'refresh'}])
        task._read_shop_gold = Mock(side_effect=[100, 100, 99])
        task._recognize_shop_slot = Mock(side_effect=[{'source': 'test', 'score': 1.},
                                                     {'source': 'test', 'score': 1.}, None])
        task._can_afford_shop_shikigami = Mock(return_value=True)
        task._shikigami_display_name = Mock(return_value='山兔')
        task._free_one_hand_slot_for_purchase = Mock()
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertTrue(task._buy_shop_slot(1, 'card', 'yamausagi'))
        task._free_one_hand_slot_for_purchase.assert_not_called()

    def test_legacy_sale_entry_cannot_bypass_material_protection(self):
        task = SimpleNamespace(sell_hand_card=Mock(), emergency_cleanup_hand=Mock())
        self.assertIsNone(ChessHandOperationsMixin.sell_one_lineup_hand_card(task))
        self.assertIsNone(ChessHandOperationsMixin._free_one_hand_slot_for_purchase(task, True))
        task.sell_hand_card.assert_not_called()
        task.emergency_cleanup_hand.assert_not_called()

    def test_battle_cleanup_closes_shop_in_battle_but_never_equips(self):
        task = SimpleNamespace(
            _read_chess_mode=Mock(return_value='战'),
            _ensure_shop_closed=Mock(return_value=True), screenshot=Mock(),
            _soul_hand_cards=Mock(return_value=[{'name': 'soul'}]),
            equip_souls_from_hand=Mock(),
            cleanup_non_lineup_hand_cards=Mock(return_value=[(1, 2)]),
        )
        result = ChessHandOperationsMixin.emergency_cleanup_hand(task)
        self.assertEqual(result['sold_non_lineup'], [(1, 2)])
        task._ensure_shop_closed.assert_called_once_with(allowed_modes=('战',))
        task.equip_souls_from_hand.assert_not_called()

    def test_occupied_deploy_target_cannot_implicitly_swap_unit(self):
        task = SimpleNamespace(
            shikigami_deploy_positions={'unit': 7},
            _ensure_shop_closed=Mock(return_value=True),
            _read_shikigami_count=Mock(return_value={'current': 2}),
            _lineup_hand_card_match_count=Mock(return_value=1),
            _board_set_has_shikigami=Mock(return_value=True),
        )
        with patch('tasks.Chess.runtime.hand_operations.Press_and_Drag') as drag:
            self.assertFalse(ChessHandOperationsMixin.deploy_shikigami_hand_card(task, 'unit', (1, 2)))
        drag.assert_not_called()

    def test_hand_disappearance_alone_does_not_confirm_deployment(self):
        task = SimpleNamespace(
            shikigami_deploy_positions={'unit': 7}, device=Mock(),
            _ensure_shop_closed=Mock(return_value=True),
            _read_shikigami_count=Mock(return_value={'current': 2}),
            _lineup_hand_card_match_count=Mock(side_effect=[1, 0]),
            _chess_drag_hold_duration=Mock(return_value=.25),
            _chess_time_available=Mock(return_value=True),
            _invalidate_inventory_hand_observation=Mock(),
            _board_set_has_shikigami=Mock(return_value=False),
            _set_position=Mock(return_value=(1, 2)),
            close_shikigami_specifics_if_open=Mock(), screenshot=Mock(),
            ACTION_SETTLE_INTERVAL=.6,
        )
        with patch('tasks.Chess.runtime.hand_operations.Press_and_Drag'), \
                patch('tasks.Chess.runtime.hand_operations.time.sleep'):
            self.assertFalse(ChessHandOperationsMixin.deploy_shikigami_hand_card(task, 'unit', (3, 4)))

    def test_emergency_unknown_card_is_preserved_without_sale(self):
        task = SimpleNamespace(
            get_lineup_strategy=Mock(return_value={'key': 'test', 'shikigami': {}}),
            HAND_CLEANUP_SAFETY_LIMIT=2, HAND_CLEANUP_CLEAN_CONFIRM_FRAMES=1,
            _chess_sale_allowed=Mock(return_value=True),
            close_shikigami_specifics_if_open=Mock(),
            _read_chess_mode=Mock(return_value='战'),
            _is_hand_cleanup_allowed=Mock(return_value=True),
            _find_badge_hand_card=Mock(return_value=None),
            _soul_hand_cards=Mock(return_value=[]),
            _discover_soul_hand_cards=Mock(return_value=[]),
            _discover_badge_hand_cards=Mock(return_value=[]),
            _hand_card_rois=Mock(return_value=[(1, 2, 3, 4)]),
            _soul_match_in_card=Mock(return_value=None),
            _hakuzosu_protect_match_in_card=Mock(return_value=None),
            classify_hand_card=Mock(return_value={'type': 'unknown'}),
            _possible_lineup_shikigami=Mock(return_value=None),
            _confirm_unknown_hand_card=Mock(), sell_hand_card=Mock(),
        )
        self.assertEqual(ChessHandOperationsMixin.cleanup_non_lineup_hand_cards(task, emergency=True), [])
        task._confirm_unknown_hand_card.assert_not_called()
        task.sell_hand_card.assert_not_called()


if __name__ == '__main__':
    unittest.main()
