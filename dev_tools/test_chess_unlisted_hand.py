"""缺人物素材的非阵容式神不能堵住库存/商店；纯截图与动作桩，不连设备。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from tasks.Chess.runtime.card_tracking import ChessCardTrackingMixin
from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit
from tasks.Chess.script_task import ScriptTask


class UnlistedHandTest(unittest.TestCase):
    def task(self):
        task = object.__new__(ScriptTask)
        task.select_lineup_strategy('counter_ubume')
        task._card_tracking_active = True
        task._card_inventory = CardInventory()
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        task._current_round_no = 3
        task._read_round_number = Mock(return_value=3)
        task._read_chess_mode = Mock(return_value='备')
        task._read_level = Mock(return_value=3)
        task._read_shop_gold = Mock(return_value=17)
        task._inventory_action_allowed = Mock(return_value=True)
        task._ensure_shop_closed = Mock(return_value=True)
        task._possible_lineup_shikigami = Mock(return_value=None)
        task._soul_match_in_card = Mock(return_value=None)
        task._hakuzosu_protect_match_in_card = Mock(return_value=None)
        task._discover_soul_hand_cards = Mock(return_value=[])
        task._discover_badge_hand_cards = Mock(return_value=[])
        task._find_badge_hand_card = Mock(return_value=None)
        task.unknown = HandUnit(None, 1, (655, 619), (607, 540, 96, 158))
        state = SimpleNamespace(hand=(task.unknown,))
        task._stable_inventory_hand = Mock(side_effect=lambda _, **kwargs: state.hand)
        task._scan_inventory_hand = Mock(side_effect=lambda: state.hand)
        task.sell_hand_card = Mock(side_effect=lambda _: setattr(state, 'hand', ()))
        return task, state

    def test_missing_portrait_is_sold_from_card_center_after_stable_confirmation(self):
        task, _ = self.task()
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertEqual(task._clean_inventory_hand(('备',)), ())
        task.sell_hand_card.assert_called_once_with((655, 619))
        # 重复确认只比较同一卡面，无需每帧重复执行所有装备/OCR保护。
        task._possible_lineup_shikigami.assert_called_once_with((607, 540, 96, 158))
        self.assertEqual(task._inventory_action_allowed.call_count, 4)

    def test_jade_only_detection_produces_full_card_box_and_center(self):
        task, _ = self.task()
        icon = task.board_occupancy_rules[0].image
        task._star_templates = ((1, icon),)
        task.device.image[550:550 + icon.shape[0], 615:615 + icon.shape[1]] = icon
        with patch('tasks.Chess.runtime.card_tracking.match_hand_templates', return_value=[]):
            hand = ChessCardTrackingMixin._scan_inventory_hand(task)
        self.assertEqual(len(hand), 1)
        card = hand[0]
        self.assertIsNone(card.name)
        self.assertGreaterEqual(card.roi[2], 72)
        self.assertEqual(card.position, (card.roi[0] + card.roi[2] // 2, 619))
        self.assertGreater(card.position[1], 600)

    def test_actual_kappa_template_is_protected_even_if_full_classifier_missed_it(self):
        task, _ = self.task()
        del task._possible_lineup_shikigami
        rule = next(rule for name, rule in task.lineup_shikigami_hand_rules if name == 'kappa')
        image = rule.image
        task.device.image[570:570 + image.shape[0], 611:611 + image.shape[1]] = image
        possible = task._possible_lineup_shikigami(task.unknown.roi)
        self.assertIsNotNone(possible)
        self.assertEqual(possible['name'], 'kappa')
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertEqual(task._clean_inventory_hand(('备',)), (task.unknown,))
        task.sell_hand_card.assert_not_called()

    def test_lineup_substitute_soul_protect_and_discovery_are_preserved(self):
        for guard in ('_possible_lineup_shikigami', '_soul_match_in_card',
                      '_hakuzosu_protect_match_in_card', '_discover_soul_hand_cards',
                      '_discover_badge_hand_cards', '_find_badge_hand_card'):
            task, state = self.task()
            value = {'position': (655, 619), 'name': 'protected'}
            getattr(task, guard).return_value = [value] if guard.startswith('_discover') else value
            with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
                self.assertEqual(task._clean_inventory_hand(('备',)), state.hand)
            task.sell_hand_card.assert_not_called()

    def test_uncertain_star_or_incomplete_card_box_cannot_authorize_sale(self):
        for card in (HandUnit(None, None, (655, 619), (607, 540, 96, 158)),
                     HandUnit(None, 1, (623, 553), (623, 540, 1, 1))):
            task, state = self.task()
            state.hand = (card,)
            with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
                task._clean_inventory_hand(('备',))
            task.sell_hand_card.assert_not_called()

    def test_phase_or_round_change_at_final_guard_never_sells(self):
        task, _ = self.task()
        task._inventory_action_allowed.side_effect = [True, True, True, False]
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertIsNone(task._clean_inventory_hand(('备',)))
        task.sell_hand_card.assert_not_called()

    def test_same_star_different_image_or_moved_card_cannot_continue_sale(self):
        for moved in (False, True):
            task, state = self.task()
            if moved:
                state.hand = (HandUnit(None, 1, (700, 619), (652, 540, 96, 158)),)
                task._stable_inventory_hand.side_effect = lambda _: (task.unknown,)
            else:
                task._inventory_card_fingerprint = Mock(side_effect=[
                    np.zeros((48, 32, 3), dtype=np.uint8),
                    np.full((48, 32, 3), 255, dtype=np.uint8)])
            with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
                task._clean_inventory_hand(('备',))
            task.sell_hand_card.assert_not_called()

    def test_unconfirmed_sale_stops_without_repeating_or_marking_ready(self):
        task, _ = self.task()
        task.sell_hand_card.side_effect = None
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertIsNone(task._clean_inventory_hand(('备',)))
        task.sell_hand_card.assert_called_once()
        self.assertFalse(task._card_inventory.ready)

    def test_round_three_cleanup_unblocks_real_kappa_purchase_path(self):
        task, _ = self.task()
        task._inventory_board_frame = Mock(return_value={11: BoardUnit(None, None),
                                                        12: BoardUnit(None, None)})
        task._recall_inventory_unit = Mock()
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(ChessCardTrackingMixin._prepare_card_inventory(task))
        task.sell_hand_card.assert_called_once_with((655, 619))
        task._recall_inventory_unit.assert_not_called()
        self.assertTrue(task._inventory_should_buy('kappa'))
        task._is_purchase_allowed = Mock(return_value=True)
        task._ensure_shop_open = Mock(return_value=True)
        task._shop_slots = Mock(return_value=[(4, 'kappa_slot')])
        task._recognize_shop_slot = Mock(return_value={'name': 'kappa', 'source': 'test', 'score': 1.})
        task.screenshot = Mock()
        task._handle_preparation = Mock(return_value=True)
        def deploy():
            task._counter_deployment_pending = False
        task.deploy_shikigami_from_hand = Mock(side_effect=deploy)
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', return_value=True) as buy, \
                patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertEqual(task.purchase_lineup_cards_once(), ['kappa'])
        buy.assert_called_once_with(4, 'kappa_slot', 'kappa')
        task.deploy_shikigami_from_hand.assert_called_once()
        self.assertEqual(task._card_inventory.totals['kappa'], 1)

    def test_named_non_lineup_card_is_also_sold_before_six(self):
        task, state = self.task()
        state.hand = (HandUnit('ichimoku_ren', 1, (655, 619), (607, 540, 96, 158)),)
        task._inventory_board_frame = Mock(return_value={11: BoardUnit(None, None)})
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(ChessCardTrackingMixin._prepare_card_inventory(task))
        task.sell_hand_card.assert_called_once_with((655, 619))
        self.assertIn(11, task._card_inventory.board)

    def test_recalled_unlisted_unit_is_sold_before_returning_to_caller(self):
        task, state = self.task()
        state.hand = ()
        task._card_inventory.board = {7: BoardUnit(None, 1)}
        task._board_set_has_shikigami = Mock(return_value=False)
        task.screenshot = Mock()
        def recalled(*args, **kwargs):
            state.hand = (task.unknown,)
        with patch('tasks.Chess.runtime.card_tracking.Press_and_Drag', side_effect=recalled) as drag, \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(task._recall_inventory_unit(7))
        drag.assert_called_once()
        task.sell_hand_card.assert_called_once_with((655, 619))
        self.assertNotIn(7, task._card_inventory.board)
        self.assertEqual(task._card_inventory.hand, ())


if __name__ == '__main__':
    unittest.main()
