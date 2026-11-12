"""阶段末尾停止及纯目标图像商店识别；只使用模拟帧和操作记录。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from dev_tools import test_chess_action_priority as priority_tests
from dev_tools import test_chess_shop as shop_tests
from tasks.Chess.script_task import ScriptTask
from tasks.Chess.runtime.card_tracking import ChessCardTrackingMixin
from tasks.Chess.runtime.inventory import BoardUnit, HandUnit


class PhaseControlsTest(unittest.TestCase):
    def image_task(self):
        task = object.__new__(ScriptTask)
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8), image_frame_id=1)
        task.shikigami_shop_rules = [('kappa', object()), ('ubume', object())]
        task._recognize_shop_shikigami_by_name = Mock(side_effect=AssertionError('禁止名称OCR'))
        task._recognize_shop_shikigami_by_ocr = Mock(side_effect=AssertionError('禁止羁绊OCR'))
        task.all_shikigami_shop_rules = [('unwanted', object())]
        task._match_shop_shikigami_avatar = Mock(return_value={
            'name': 'kappa', 'score': .99, 'position': (100, 100)})
        return task

    def test_shop_only_matches_targets_including_miss_and_expected_mismatch(self):
        task = self.image_task()
        result = task._recognize_shop_slot(1, task.C_SHIKIGAMI_1,
                                           fallback_rules=task.all_shikigami_shop_rules)
        self.assertEqual(result['name'], 'kappa')
        self.assertEqual(result['source'], 'target_image')
        task._match_shop_shikigami_avatar.assert_called_once_with(
            task.C_SHIKIGAMI_1, rules=task.shikigami_shop_rules)
        self.assertIsNone(task._recognize_shop_slot(1, task.C_SHIKIGAMI_1, 'ubume'))
        task.device.image_frame_id += 1
        task._match_shop_shikigami_avatar.return_value = None
        self.assertIsNone(task._recognize_shop_slot(1, task.C_SHIKIGAMI_1))
        self.assertIsNone(task._recognize_shop_slot(0, task.C_SHIKIGAMI_1))
        task._recognize_shop_shikigami_by_name.assert_not_called()
        task._recognize_shop_shikigami_by_ocr.assert_not_called()

    def test_summary_and_refresh_share_images_only_within_same_frame(self):
        task = self.image_task()
        self.assertEqual(task._shop_shikigami_summary(), ['河童'] * 5)
        snapshot = task._shop_slot_refresh_snapshot()
        self.assertTrue(all(slot['name'] == 'kappa' for slot in snapshot.values()))
        self.assertEqual(task._match_shop_shikigami_avatar.call_count, 5)
        task.device.image_frame_id += 1
        task._shop_slot_refresh_snapshot()
        self.assertEqual(task._match_shop_shikigami_avatar.call_count, 10)
        task.device.image = task.device.image.copy()
        task._shop_slot_refresh_snapshot()
        self.assertEqual(task._match_shop_shikigami_avatar.call_count, 15)

    def test_counter_lineup_loads_all_eight_target_templates(self):
        task = object.__new__(ScriptTask)
        task._active_lineup_key = 'counter_ubume'
        names = {name for name, rule in task.shikigami_shop_rules if rule.image is not None}
        self.assertEqual(names, {'ubume', 'kujira', 'jinkougyou', 'kappa',
                                 'gashadokuro', 'miketsu', 'kachou_fuugetsu', 'kuro_douji'})

    def test_missing_image_without_debit_never_confirms_or_reclicks(self):
        task = shop_tests.ShopProbe([{'refresh'}])
        task._recognize_shop_slot = Mock(side_effect=lambda *a, **k:
                                        {'name': 'yamausagi'} if not task.click.called else None)
        task._can_afford_shop_shikigami = Mock(return_value=True)
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertFalse(task._buy_shop_slot(1, 'card', 'yamausagi'))
        task.click.assert_called_once()

    def test_purchase_already_clicked_can_finish_confirmation_at_three(self):
        task = shop_tests.ShopProbe([{'refresh'}])
        task._read_remaining_time.side_effect = lambda: 3 if task.click.called else 4
        task._read_shop_gold.side_effect = lambda: 99 if task.click.called else 100
        task._recognize_shop_slot = Mock(side_effect=lambda *a, **k:
                                        None if task.click.called else {'name': 'yamausagi'})
        task._can_afford_shop_shikigami = Mock(return_value=True)
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertTrue(task._buy_shop_slot(1, 'card', 'yamausagi'))
        task.click.assert_called_once()

    def test_three_or_less_stops_battle_and_wait_before_cleanup_or_shop(self):
        for mode in ('战', '待'):
            for remaining in (None, 0, 1, 2, 3):
                task, events = shop_tests.ChessShopTest().battle_task()
                task._read_chess_mode.return_value = mode
                task._read_remaining_time.return_value = remaining
                self.assertEqual(task._run_battle_economy_cycle(), 'blocked')
                self.assertEqual(events, [])

    def test_three_stops_sale_equipment_and_inventory_actions(self):
        task = priority_tests.ActionPriorityTest().task()
        task._read_remaining_time.return_value = 3
        task._chess_equipment_ready = Mock(return_value=True)
        with patch('tasks.Chess.runtime.hand_operations.Press_and_Drag') as drag:
            task.sell_hand_card((655, 619))
            self.assertFalse(task._equip_soul_card((655, 619), 8, 'test'))
        drag.assert_not_called()
        self.assertFalse(task._inventory_action_allowed(('备',), reserve=2))

    def test_three_stops_market_toggle(self):
        task = shop_tests.ShopProbe([{'refresh'}])
        task._read_remaining_time.return_value = 3
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertFalse(task._ensure_shop_closed(allowed_modes=('战',)))
        task.click.assert_not_called()

    def test_preparation_observation_pass_does_not_recall_or_sell_unknowns(self):
        task = priority_tests.ActionPriorityTest().task()
        task._inventory_board_round = task._current_round_no
        task._inventory_board_frame = Mock(return_value={1: BoardUnit(None, 1)})
        task._stable_inventory_hand = Mock(return_value=(
            HandUnit('ubume', 1, (655, 619), (607, 540, 96, 158)),
            HandUnit(None, 1, (755, 619), (707, 540, 96, 158))))
        task._clean_inventory_hand = Mock(side_effect=AssertionError('补阵/装备前不清杂卡'))
        task._recall_inventory_unit = Mock(side_effect=AssertionError('补阵/装备前不批量回收'))
        task._identify_inventory_specials = Mock(side_effect=AssertionError('延后检查未知单位'))
        task._sell_excess_inventory_cards = Mock(side_effect=AssertionError('临时账本不能卖阵容材料'))
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertTrue(ChessCardTrackingMixin._prepare_card_inventory(task))
        self.assertEqual(task._card_inventory.totals['ubume'], 1)
        task._inventory_board_frame.assert_not_called()
        self.assertFalse(task._card_inventory.ready)


if __name__ == '__main__':
    unittest.main()
