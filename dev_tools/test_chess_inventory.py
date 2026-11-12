"""星级、持有目标和棋盘身份恢复；不连接游戏、不读取用户配置。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from tasks.Chess.runtime.card_tracking import ChessCardTrackingMixin
from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit, copies_for_star
from tasks.Chess.script_task import ScriptTask
from tasks.Chess.strategy.shikigami_catalog import build_lineup_shikigami
from tasks.Chess.strategy.lineup import LINEUP_REGISTRY


def hand(star=1, x=100, name='kaoru'):
    return HandUnit(name, star, (x, 600), (x - 42, 550, 84, 118))


class InventoryTest(unittest.TestCase):
    def test_board_star_is_weighted_but_each_hand_card_counts_once(self):
        inventory = CardInventory()
        inventory.reconcile((hand(2, 100), hand(2, 200)), {4: BoardUnit('kaoru', 2)})
        self.assertEqual(inventory.totals['kaoru'], 5)
        self.assertTrue(inventory.can_buy('kaoru', 3))
        inventory.reconcile((hand(3),), {})
        self.assertEqual(inventory.totals['kaoru'], 1)
        self.assertFalse(inventory.can_buy('kaoru', 3))
        inventory.reconcile((), {4: BoardUnit('kaoru', 3)})
        self.assertEqual(inventory.totals['kaoru'], 9)

    def test_eight_copies_buy_one_then_stop_even_with_more_shop_duplicates(self):
        inventory = CardInventory(totals={'kaoru': 8}, ready=True)
        self.assertTrue(inventory.can_buy('kaoru', 3))
        inventory.purchased('kaoru')
        self.assertFalse(inventory.can_buy('kaoru', 3))

    def test_unknown_is_not_an_empty_slot_or_one_star(self):
        inventory = CardInventory()
        inventory.reconcile((), {1: BoardUnit('kaoru', None)})
        self.assertFalse(inventory.can_buy('kaoru', 3))
        inventory.reconcile((hand(3),), {1: BoardUnit(None, 1)})
        self.assertFalse(inventory.can_buy('kaoru', 3))
        self.assertFalse(inventory.excess(inventory.hand[0], 3))

    def test_external_gain_is_counted_and_only_surplus_can_be_sold(self):
        inventory = CardInventory()
        extra = hand(1)
        inventory.reconcile((extra,), {2: BoardUnit('kaoru', 3)})
        self.assertEqual(inventory.totals['kaoru'], 10)
        self.assertTrue(inventory.excess(extra, 3))
        self.assertFalse(inventory.can_buy('kaoru', 3))
        inventory.reconcile((hand(3),), {})
        self.assertFalse(inventory.excess(inventory.hand[0], 3))

    def test_target_two_keeps_strongest_and_preserves_unmerged_materials(self):
        inventory = CardInventory()
        cards = (hand(1, 100), hand(2, 200), hand(2, 300))
        inventory.reconcile(cards, {})
        self.assertTrue(inventory.excess(cards[0], 2))
        self.assertFalse(inventory.excess(cards[1], 2))
        self.assertTrue(inventory.excess(cards[2], 2))
        inventory.reconcile((hand(1, 100), hand(1, 200), hand(1, 300)), {})
        self.assertTrue(all(not inventory.excess(c, 2) for c in inventory.hand))

    def test_inferred_board_upgrade_alone_cannot_authorize_sale(self):
        inventory = CardInventory()
        extra = hand(1)
        inventory.reconcile((extra,), {2: BoardUnit('kaoru', 3, star_confirmed=False)})
        self.assertFalse(inventory.excess(extra, 3))

    def test_summon_is_not_inventory_or_population_material(self):
        inventory = CardInventory()
        inventory.reconcile((), {12: BoardUnit('arakawa_goldfish', None, True)})
        self.assertTrue(inventory.ready)
        self.assertEqual(inventory.totals, {})
        self.assertEqual(len(inventory.snapshot()['board']), 12)

    def test_every_existing_lineup_defaults_to_three_and_new_lineup_can_override(self):
        for entry in LINEUP_REGISTRY.values():
            if entry['strategy']['key'] == 'counter_ubume':
                continue  # 新阵容明确将久次良设为两张二星，旧阵容仍默认三星。
            self.assertTrue(all(u['target_star'] == 3 for u in entry['strategy']['shikigami'].values()))
        units = build_lineup_shikigami({'薰': {'position': 2, 'target_star': 2}})
        self.assertEqual(units['kaoru']['target_star'], 2)
        for value in (0, 4, True, 1.0, '2'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_lineup_shikigami({'薰': {'position': 2, 'target_star': value}})


class TrackingTest(unittest.TestCase):
    def task(self):
        task = object.__new__(ScriptTask)
        task._card_tracking_active = True
        task._card_inventory = CardInventory()
        task.select_lineup_strategy('qijiaoshan')
        task.screenshot = Mock()
        task.appear = Mock(side_effect=lambda rule: rule is task.I_EXPERIENCE)
        task._read_chess_mode = Mock(return_value='备')
        task._read_level = Mock(return_value=6)
        task._read_remaining_time = Mock(return_value=30)
        task._current_round_no = 4
        task._read_round_number = Mock(return_value=4)
        task._ensure_shop_closed = Mock(return_value=True)
        task._handle_preparation = Mock(return_value=True)
        task._board_set_has_shikigami = Mock(return_value=False)
        task._scan_inventory_hand = Mock(return_value=())
        task.sell_hand_card = Mock()
        return task

    def test_real_entry_uses_tracking_and_stars_reuse_existing_templates(self):
        task = self.task()
        for star in (1, 2, 3):
            for scale in (.8, 1.):
                icon = cv2.resize(task.board_occupancy_rules[star - 1].image,
                                  None, fx=scale, fy=scale)
                canvas = np.zeros((80, 80, 3), dtype=np.uint8)
                canvas[20:20 + icon.shape[0], 20:20 + icon.shape[1]] = icon
                task.device = SimpleNamespace(image=canvas)
                self.assertEqual(task._read_card_star((10, 10, 45, 45)), star)
        task.device = SimpleNamespace(image=np.zeros((80, 80, 3), dtype=np.uint8))
        self.assertIsNone(task._read_card_star((10, 10, 45, 45)))
        self.assertIn(ChessCardTrackingMixin, ScriptTask.__mro__)
        self.assertEqual(ScriptTask._buy_shop_slot.__module__, 'tasks.Chess.runtime.counter_ubume')

    def test_confirmed_purchase_increments_once_and_failed_purchase_does_not(self):
        task = self.task()
        task._card_inventory.reconcile((hand(2),), {})
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', return_value=True) as buy:
            self.assertTrue(task._buy_shop_slot(1, 'slot', 'kaoru'))
            self.assertEqual(task._card_inventory.totals['kaoru'], 2)
            buy.assert_called_once()
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', return_value=False):
            self.assertFalse(task._buy_shop_slot(1, 'slot', 'kaoru'))
            self.assertTrue(task._inventory_should_buy('kaoru'))
        def unconfirmed_purchase(*args):
            task._shop_purchase_clicked = True
            return False
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', side_effect=unconfirmed_purchase):
            self.assertFalse(task._buy_shop_slot(1, 'slot', 'kaoru'))
            self.assertEqual(task._card_inventory.totals['kaoru'], 2)
        task._stable_inventory_hand = Mock(return_value=(hand(2),))
        task._refresh_inventory_hand(('备',))
        self.assertFalse(task._inventory_should_buy('kaoru'))

    def test_real_shop_loop_stops_mid_shop_at_ninth_copy(self):
        task = self.task()
        task._card_inventory = CardInventory(totals={'kaoru': 8}, ready=True)
        task._refresh_inventory_hand = Mock(return_value=True)
        task._is_purchase_allowed = Mock(return_value=True)
        task._ensure_shop_open = Mock(return_value=True)
        task._shop_slots = Mock(return_value=[(i, f'slot{i}') for i in range(1, 6)])
        task._recognize_shop_slot = Mock(return_value={'name': 'kaoru', 'source': 'test', 'score': 1.})
        task._can_afford_shop_shikigami = Mock(return_value=True)
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', return_value=True) as buy, \
                patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertEqual(task.purchase_lineup_cards_once(), ['kaoru'])
        buy.assert_called_once()
        self.assertEqual(task._card_inventory.totals['kaoru'], 9)

    def test_purchase_updates_only_the_matching_board_star_from_image(self):
        task = self.task()
        task._card_inventory.reconcile((hand(1),), {2: BoardUnit('kaoru', 1), 6: BoardUnit('other', 2)})
        task._read_card_star = Mock(return_value=2)
        task._stable_inventory_hand = Mock(return_value=())
        task._read_chess_mode.return_value = '战'
        self.assertTrue(task._after_lineup_purchase('kaoru'))
        task._read_card_star.assert_called_once_with(task._set_jade_area(2))
        self.assertEqual(task._card_inventory.board[2], BoardUnit('kaoru', 2))
        self.assertEqual(task._card_inventory.totals['kaoru'], 3)

    def test_surplus_sale_requires_exact_reduction_and_does_not_repeat_on_ambiguity(self):
        for confirmed in (False, True):
            task = self.task()
            extra = hand(1)
            task._card_inventory.reconcile((extra,), {2: BoardUnit('kaoru', 3)})
            task._stable_inventory_hand = Mock(side_effect=[(extra,), () if confirmed else (extra,), ()])
            task._scan_inventory_hand.return_value = (extra,)
            with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
                task._sell_excess_inventory_cards(('备',))
            task.sell_hand_card.assert_called_once_with(extra.position)
            self.assertEqual(task._card_inventory.totals['kaoru'], 9 if confirmed else 10)
            self.assertEqual(task._card_inventory.ready, confirmed)

    def test_target_card_and_unknown_stars_are_never_sold(self):
        for cards in ((hand(3),), (hand(None), hand(3, 200))):
            task = self.task()
            task._card_inventory.reconcile(cards, {})
            task._stable_inventory_hand = Mock(return_value=cards)
            task._sell_excess_inventory_cards(('备',))
            task.sell_hand_card.assert_not_called()

    def test_late_phase_never_starts_recall_or_sale(self):
        task = self.task()
        task._read_remaining_time.return_value = 3
        task._card_inventory.reconcile((hand(1),), {2: BoardUnit('kaoru', 3)})
        with patch('tasks.Chess.runtime.card_tracking.Press_and_Drag') as drag:
            self.assertFalse(task._recall_inventory_unit(7))
            task._sell_excess_inventory_cards(('备',))
        drag.assert_not_called()
        task.sell_hand_card.assert_not_called()

    def test_same_mode_in_next_round_cannot_resume_old_recall(self):
        task = self.task()
        task._read_round_number.return_value = 5
        with patch('tasks.Chess.runtime.card_tracking.Press_and_Drag') as drag:
            self.assertFalse(task._recall_inventory_unit(3))
        drag.assert_not_called()

    def test_drag_ui_without_experience_button_cannot_be_a_stable_inventory_frame(self):
        task = self.task()
        task.appear = Mock(return_value=False)
        task._scan_inventory_hand = Mock()
        self.assertIsNone(task._stable_inventory_hand(('备',)))
        task._scan_inventory_hand.assert_not_called()

    def test_recall_confirms_empty_slot_and_increased_hand_mass(self):
        task = self.task()
        task._card_inventory.board = {7: BoardUnit(None, 2)}
        task._stable_inventory_hand = Mock(side_effect=[(), (hand(2),)])
        task._board_set_has_shikigami = Mock(return_value=False)
        with patch('tasks.Chess.runtime.card_tracking.Press_and_Drag') as drag, \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(task._recall_inventory_unit(7))
        drag.assert_called_once()
        self.assertNotIn(7, task._card_inventory.board)

    def test_recall_without_hand_evidence_is_not_recorded(self):
        task = self.task()
        task._card_inventory.board = {7: BoardUnit(None, 2)}
        task._stable_inventory_hand = Mock(return_value=())
        task._board_set_has_shikigami = Mock(return_value=False)
        with patch('tasks.Chess.runtime.card_tracking.Press_and_Drag'), \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertFalse(task._recall_inventory_unit(7))
        self.assertIn(7, task._card_inventory.board)
        self.assertFalse(task._card_inventory.ready)

    def test_board_scan_requires_preparation_and_closed_shop_once_per_round(self):
        task = self.task()
        board = {3: BoardUnit(None, 1), 2: BoardUnit('kaoru', 3)}
        task._inventory_board_frame = Mock(return_value=board)
        task._stable_inventory_hand = Mock(return_value=())
        task._recall_inventory_unit = Mock()
        task._ensure_shop_closed.return_value = False
        self.assertFalse(task._prepare_card_inventory())
        task._ensure_shop_closed.return_value = True
        task._read_chess_mode.return_value = '战'
        self.assertFalse(task._prepare_card_inventory())
        task._read_chess_mode.return_value = '备'
        task._read_round_number.return_value = 5
        self.assertFalse(task._prepare_card_inventory())
        task._inventory_board_frame.assert_not_called()
        task._read_round_number.return_value = 4
        self.assertTrue(task._prepare_card_inventory())
        self.assertTrue(task._prepare_card_inventory())
        task._inventory_board_frame.assert_called_once()
        task._recall_inventory_unit.assert_not_called()
        self.assertEqual(task._card_inventory.board, board)
        self.assertFalse(task._inventory_should_buy('kaoru'))
        task._current_round_no = 5
        task._read_round_number.return_value = 5
        self.assertTrue(task._prepare_card_inventory())
        self.assertEqual(task._inventory_board_frame.call_count, 2)

    def test_manual_deployment_records_identity_and_star_only_after_confirmation(self):
        for success in (False, True):
            task = self.task()
            task._stable_inventory_hand = Mock(return_value=(hand(2),))
            with patch('tasks.Chess.runtime.hand_operations.ChessHandOperationsMixin.deploy_shikigami_hand_card',
                       return_value=success):
                self.assertEqual(task.deploy_shikigami_hand_card('kaoru', (100, 600)), success)
            self.assertEqual(task._card_inventory.board.get(2), BoardUnit('kaoru', 2) if success else None)

    def test_goldfish_exchange_preserves_displaced_unit_identity(self):
        task = self.task()
        task._card_inventory.board = {11: BoardUnit('arakawa_goldfish', None, True),
                                      12: BoardUnit('kaoru', 2)}
        task._arakawa_goldfish_current_position = 11
        task._record_arakawa_goldfish_position(12)
        self.assertEqual(task._card_inventory.board[11], BoardUnit('kaoru', 2))
        self.assertEqual(task._board_actual_positions['kaoru'], 11)
        self.assertTrue(task._card_inventory.board[12].special)

    def test_new_game_does_not_reuse_old_inventory(self):
        task = self.task()
        task._card_inventory.totals['kaoru'] = 9
        task._reset_economy_state = Mock()
        task._wait_until_in_chess_game = Mock()
        task._start_chess_game()
        self.assertEqual(task._card_inventory.totals, {})
        self.assertFalse(task._card_inventory.ready)

    def test_unknown_board_does_not_prevent_normal_shop_at_any_level(self):
        task = self.task()
        task._card_inventory.board = {11: BoardUnit(None, 2)}
        task._stable_inventory_hand = Mock(return_value=(hand(1),))
        for level in (5, 6):
            task._read_level.return_value = level
            self.assertTrue(task._refresh_inventory_hand(('备',)))
            self.assertTrue(task._inventory_should_buy('kaoru'))
        self.assertTrue(task._card_inventory.deferred_board)

    def test_deferred_board_does_not_hide_unknown_hand(self):
        stock = CardInventory()
        stock.reconcile((hand(1, name=None),), {11: BoardUnit(None, None)}, allow_unknown_board=True)
        self.assertTrue(stock.deferred_board)
        self.assertFalse(stock.ready)

    def test_recovery_can_sell_known_non_lineup_with_other_board_identities_pending(self):
        task = self.task()
        bad = hand(1, name='non_lineup')
        task._card_inventory.board = {11: BoardUnit(None, 1)}
        task._stable_inventory_hand = Mock(side_effect=[(bad,), (), ()])
        task._scan_inventory_hand.return_value = (bad,)
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            task._sell_excess_inventory_cards(('备',), include_non_lineup=True, non_lineup_only=True)
        task.sell_hand_card.assert_called_once_with(bad.position)
        self.assertFalse(task._card_inventory.ready)
        self.assertIn(11, task._card_inventory.board)

    def test_recall_only_when_target_blocked_or_population_full(self):
        for full, blocked in ((False, False), (True, False), (False, True)):
            task = self.task()
            task._read_level.return_value = 2 if full else 5
            unknown_position = 2 if blocked else 11
            task._card_inventory.board = {unknown_position: BoardUnit(None, None),
                                           1: BoardUnit('known', 1)}
            task._inspect_blocking_board_unit = Mock(side_effect=lambda p: bool(task._card_inventory.board.pop(p)))
            self.assertTrue(task._free_inventory_deploy_slot(2))
            if full or blocked:
                task._inspect_blocking_board_unit.assert_called_once_with(unknown_position)
            else:
                task._inspect_blocking_board_unit.assert_not_called()

    def test_known_and_special_units_cannot_be_evicted_for_deployment(self):
        for unit in (BoardUnit('known', 1), BoardUnit('arakawa_goldfish', None, True)):
            task = self.task()
            task._card_inventory.board = {2: unit}
            task._recall_inventory_unit = Mock()
            self.assertFalse(task._free_inventory_deploy_slot(2))
            task._recall_inventory_unit.assert_not_called()

    def test_recall_relocates_hand_before_deploying_to_fixed_position(self):
        task = self.task()
        task._read_level.return_value = 1
        task._card_inventory.board = {11: BoardUnit(None, None)}
        task._stable_inventory_hand = Mock(side_effect=[(hand(1, 100),), (hand(1, 400),)])
        task._inspect_blocking_board_unit = Mock(side_effect=lambda p: bool(task._card_inventory.board.pop(p)))
        with patch('tasks.Chess.runtime.hand_operations.ChessHandOperationsMixin.deploy_shikigami_hand_card',
                   return_value=True) as deploy:
            self.assertTrue(task.deploy_shikigami_hand_card('kaoru', (100, 600)))
        deploy.assert_called_once_with('kaoru', (400, 600))
        self.assertEqual(task._card_inventory.board, {2: BoardUnit('kaoru', 1)})

    def test_board_detail_name_ignores_player_text_behind_panel(self):
        task = self.task()
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        name = SimpleNamespace(score=.99, ocr_text='白狼', box=((0, 0), (59, 0), (59, 32), (0, 32)))
        player = SimpleNamespace(score=.99, ocr_text='玩家名', box=((128, 10), (193, 10), (193, 36), (128, 36)))
        with patch.object(task.O_SHIKIGAMI_SPECIFICS_NAME, 'detect_and_ocr', return_value=[player, name]):
            self.assertEqual(task._read_board_detail_name(), '白狼')

    def test_round_three_keeps_confirmed_non_lineup_board_unit(self):
        task = self.task()
        task._current_round_no = 3
        task._read_round_number.return_value = 3
        task._card_inventory.board = {2: BoardUnit(None, 1)}
        task._board_set_has_shikigami.return_value = True
        task.click = Mock()
        task.appear.side_effect = lambda rule: (rule is task.I_EXPERIENCE
                                               or rule is task.I_SHIKIGAMI_SPECIFICS and task.click.called)
        with patch.object(task, '_read_board_detail_name', return_value='山兔'), \
                patch('tasks.Chess.runtime.card_tracking.RuleOcr.detect_and_ocr') as sale, \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertFalse(task._inspect_blocking_board_unit(2))
        sale.assert_not_called()
        self.assertEqual(task._card_inventory.board[2].name, 'yamausagi')
        self.assertFalse(any(call.args[0].name.startswith('CHESS_SELL') for call in task.click.call_args_list))

    def test_unlisted_unit_sells_from_detail_button_without_dragging(self):
        task = self.task()
        task._card_inventory.board = {2: BoardUnit(None, 1)}
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        state = {'panel': False, 'selling': False}
        occupancy_after_click = iter((True, False, True, False, False))
        task.appear.side_effect = lambda rule: (rule is task.I_EXPERIENCE
                                               or rule is task.I_SHIKIGAMI_SPECIFICS and state['panel'])
        task._board_set_has_shikigami.side_effect = lambda _: (
            next(occupancy_after_click) if state['selling'] else True
        )
        def click(rule):
            if rule.name == 'CHESS_INSPECT_2':
                state['panel'] = True
            elif rule.name == 'CHESS_SELL_SET_2':
                state.update(panel=False, selling=True)
        task.click = Mock(side_effect=click)
        result = SimpleNamespace(score=.95, ocr_text='+3 出售', box=((54, 57), (145, 54), (146, 85), (55, 87)))
        with patch.object(task, '_read_board_detail_name', return_value='未收录式神'), \
                patch('tasks.Chess.runtime.card_tracking.RuleOcr.detect_and_ocr', return_value=[result]), \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'), \
                patch('tasks.Chess.runtime.card_tracking.Press_and_Drag') as drag:
            self.assertTrue(task._free_inventory_deploy_slot(2))
        self.assertEqual([call.args[0].name for call in task.click.call_args_list],
                         ['CHESS_INSPECT_2', 'CHESS_SELL_SET_2'])
        _, y, _, height = task.click.call_args.args[0].roi_back
        self.assertLessEqual(y, 588)
        self.assertGreater(y + height, 588)
        drag.assert_not_called()
        self.assertNotIn(2, task._card_inventory.board)
        self.assertFalse(task._inventory_pending_board_sales)
        self.assertIsNone(next(occupancy_after_click, None))

    def test_next_preparation_scan_releases_empty_slot_after_unconfirmed_sale(self):
        task = self.task()
        task._card_inventory.board = {2: BoardUnit('yamausagi', 1), 3: BoardUnit('ichimoku_ren', 2)}
        task._inventory_pending_board_sales = {2}
        task._stable_inventory_hand = Mock(return_value=())
        self.assertTrue(task._prepare_card_inventory())
        self.assertNotIn(2, task._card_inventory.board)
        self.assertIn(3, task._card_inventory.board)
        self.assertFalse(task._inventory_pending_board_sales)
        self.assertTrue(task._free_inventory_deploy_slot(2))

    def test_unreadable_board_detail_is_not_reopened_in_same_round(self):
        task = self.task()
        task._card_inventory.board = {2: BoardUnit(None, 1)}
        panel = False

        def click(rule):
            nonlocal panel
            panel = rule.name == 'CHESS_INSPECT_2'

        task.click = Mock(side_effect=click)
        task.appear.side_effect = lambda rule: (rule is task.I_EXPERIENCE
                                               or rule is task.I_SHIKIGAMI_SPECIFICS and panel)
        task._board_set_has_shikigami.return_value = True
        with patch.object(task, '_read_board_detail_name', return_value=None), \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertFalse(task._free_inventory_deploy_slot(2))
            self.assertFalse(task._free_inventory_deploy_slot(2))
        self.assertEqual([c.args[0].name for c in task.click.call_args_list],
                         ['CHESS_INSPECT_2', task.C_CLICK_CLOSE_SPECIFICS_AREA.name])

    def test_recall_known_unit_with_other_unrecognized_hand_card(self):
        task = self.task()
        task._card_inventory.board = {7: BoardUnit('kaoru', 2)}
        other = hand(star=None, x=200, name=None)
        task._stable_inventory_hand = Mock(side_effect=[(other,), (other, hand(2))])
        with patch('tasks.Chess.runtime.card_tracking.Press_and_Drag') as drag, \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(task._recall_inventory_unit(7))
        drag.assert_called_once()
        self.assertNotIn(7, task._card_inventory.board)

    def test_lineup_blocker_is_recalled_and_never_sold(self):
        task = self.task()
        task._card_inventory.board = {2: BoardUnit(None, 1)}
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        state = {'panel': False, 'occupied': True}
        task.appear.side_effect = lambda rule: (rule is task.I_EXPERIENCE
                                               or rule is task.I_SHIKIGAMI_SPECIFICS and state['panel'])
        task._board_set_has_shikigami.side_effect = lambda position: position == 2 and state['occupied']
        task.click = Mock(side_effect=lambda rule: state.update(panel=rule.name == 'CHESS_INSPECT_2'))
        def recall(position):
            self.assertEqual(task._card_inventory.board[position].name, 'ichimoku_ren')
            state['occupied'] = False
            task._card_inventory.board.pop(position)
            task._card_inventory.hand = (hand(name='ichimoku_ren'),)
            return True
        task._recall_inventory_unit = Mock(side_effect=recall)
        def deploy(name, source):
            task._card_inventory.board[3] = BoardUnit(name, 1)
            return True
        task.deploy_shikigami_hand_card = Mock(side_effect=deploy)
        with patch.object(task, '_read_board_detail_name', return_value='一目连'), \
                patch('tasks.Chess.runtime.card_tracking.RuleOcr.detect_and_ocr') as sale, \
                patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(task._free_inventory_deploy_slot(2))
        task._recall_inventory_unit.assert_called_once_with(2)
        task.deploy_shikigami_hand_card.assert_called_once_with('ichimoku_ren', (100, 600))
        self.assertEqual(task._card_inventory.board[3].name, 'ichimoku_ren')
        sale.assert_not_called()


if __name__ == '__main__':
    unittest.main()
