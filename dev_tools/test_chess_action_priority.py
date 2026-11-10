"""装备解锁、同帧复用及回收即清理；不创建设备、不操作游戏。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit
from tasks.Chess.script_task import ScriptTask
from tasks.Chess.strategy import counter_ubume as plan


class ActionPriorityTest(unittest.TestCase):
    def task(self, level=6):
        task = object.__new__(ScriptTask)
        task.select_lineup_strategy('counter_ubume')
        task._card_tracking_active = True
        task._card_inventory = CardInventory(ready=True)
        task._inventory_board_dirty = False
        task._read_level = Mock(return_value=level)
        task._current_round_no = 8
        task._read_round_number = Mock(return_value=8)
        task._read_chess_mode = Mock(return_value='备')
        task._read_remaining_time = Mock(return_value=20)
        task.appear = Mock(side_effect=lambda rule: rule is task.I_EXPERIENCE)
        task.device = SimpleNamespace(image_frame_id=0, image=np.zeros((720, 1280, 3), dtype=np.uint8))
        task.screenshot = Mock(side_effect=lambda: setattr(task.device, 'image_frame_id', task.device.image_frame_id + 1))
        task._ensure_shop_closed = Mock(return_value=True)
        task.close_shikigami_specifics_if_open = Mock(return_value=False)
        task._scan_inventory_hand = Mock(return_value=())
        return task

    def fill_six_roles(self, task, fallback=False):
        task._card_inventory.reconcile((), {
            slot['position']: BoardUnit('kappa' if fallback and slot['name'] == plan.JINKOUGYOU
                                        else slot['name'], 1)
            for slot in plan.SLOTS if slot['min_level'] <= 6})

    def test_equipment_waits_for_six_and_each_current_role(self):
        task = self.task(5)
        self.fill_six_roles(task)
        self.assertFalse(task._chess_equipment_ready())
        task._read_level.return_value = 6
        task._card_inventory.board.pop(7)
        self.assertFalse(task._chess_equipment_ready())
        task._card_inventory.hand = (HandUnit('kuro_douji', 1, (655, 619), (607, 540, 96, 158)),)
        self.assertTrue(task._chess_equipment_ready())

    def test_generic_lineup_also_requires_each_owned_role(self):
        task = self.task()
        task.select_lineup_strategy('qijiaoshan')
        names = list(task.get_lineup_strategy()['shikigami'])
        cards = tuple(HandUnit(name, 1, (200 + i * 90, 619), (160 + i * 90, 540, 83, 158))
                      for i, name in enumerate(names))
        task._card_inventory.reconcile(cards[:-1], {})
        self.assertFalse(task._chess_equipment_ready())
        task._card_inventory.reconcile(cards, {})
        self.assertTrue(task._chess_equipment_ready())

    def test_kappa_counts_as_current_role_and_gashadokuro_is_not_required_at_six(self):
        task = self.task()
        self.fill_six_roles(task, fallback=True)
        self.assertNotIn('gashadokuro', task._card_inventory.totals)
        self.assertTrue(task._chess_equipment_ready())
        task._read_level.return_value = 8
        self.assertTrue(task._chess_equipment_ready(), '一次解锁后不反复冻结装备')
        task.select_lineup_strategy('counter_ubume')
        self.assertFalse(task._chess_equipment_ready(), '换阵容必须重新判断当前所需角色')

    def test_all_equipment_entrypoints_hold_cards_before_unlock(self):
        task = self.task(5)
        self.fill_six_roles(task)
        task._soul_hand_cards = Mock()
        task._recognized_emblem_hand_cards = Mock()
        with patch('tasks.Chess.runtime.hand_operations.Press_and_Drag') as drag:
            self.assertEqual(task.equip_souls_from_hand({'ubume'}), [])
            self.assertEqual(task.equip_emblems_from_hand({'ubume'}), [])
            self.assertEqual(task.discover_souls_from_hand(), 0)
            self.assertFalse(task.equip_hakuzosu_protect_after_deploy())
            self.assertFalse(task._equip_soul_card((655, 619), 8, 'test'))
        drag.assert_not_called()
        task._soul_hand_cards.assert_not_called()
        task._recognized_emblem_hand_cards.assert_not_called()

    def test_stable_hand_same_frame_is_reused_but_sale_invalidates_it(self):
        task = self.task()
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertEqual(task._stable_inventory_hand(('备',)), ())
            self.assertEqual(task.screenshot.call_count, 2)
            self.assertEqual(task._stable_inventory_hand(('备',)), ())
            self.assertEqual(task.screenshot.call_count, 2)
            with patch('tasks.Chess.runtime.hand_operations.Press_and_Drag'):
                task.sell_hand_card((655, 619))
            self.assertIsNone(task._current_inventory_hand())
            task._stable_inventory_hand(('备',))
            self.assertEqual(task.screenshot.call_count, 4)

    def test_observation_expires_and_does_not_allow_cross_mode_reuse(self):
        task = self.task()
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            task._stable_inventory_hand(('备',))
        observed = task._current_inventory_hand()
        with patch('tasks.Chess.runtime.card_tracking.time.monotonic', return_value=observed['time'] + 1):
            self.assertIsNone(task._current_inventory_hand())
        task._read_chess_mode.return_value = '战'
        self.assertIsNone(task._stable_inventory_hand(('备',)))

    def test_empty_snapshot_does_not_rescan_board_or_hand_before_next_action(self):
        task = self.task()
        task._counter_confirm_board_stars = Mock(side_effect=AssertionError('不应重复整盘核对'))
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            task._stable_inventory_hand(('备',))
        captures = task.screenshot.call_count
        task._sell_excess_inventory_cards(('备',))
        self.assertEqual(task.deploy_shikigami_from_hand(), [])
        self.assertEqual(task.screenshot.call_count, captures)
        self.assertFalse(task._counter_deployment_pending)

    def test_recall_empty_slot_is_verified_inside_two_stable_hand_frames(self):
        task = self.task()
        task._board_set_has_shikigami = Mock(side_effect=[True, False, False])
        with patch('tasks.Chess.runtime.card_tracking.time.sleep'):
            self.assertEqual(task._stable_inventory_hand(('备',), empty_position=7), ())
        self.assertEqual(task.screenshot.call_count, 3)
        self.assertIn(7, task._current_inventory_hand()['empty_positions'])

    def test_plain_unit_jade_skips_equipment_and_ocr_but_lineup_stays_protected(self):
        task = self.task()
        icon = task.board_occupancy_rules[0].image
        task.device.image[550:550 + icon.shape[0], 615:615 + icon.shape[1]] = icon
        card = HandUnit(None, 1, (655, 619), (607, 540, 96, 158))
        task._possible_lineup_shikigami = Mock(return_value=None)
        task._soul_match_in_card = Mock(side_effect=AssertionError('普通式神不应扫描全御魂'))
        task._discover_soul_hand_cards = Mock(side_effect=AssertionError('普通式神不应OCR'))
        self.assertFalse(task._unidentified_inventory_card_protected(card))
        task._possible_lineup_shikigami.return_value = {'name': 'kappa'}
        self.assertTrue(task._unidentified_inventory_card_protected(card))

    def test_preparation_orders_deployment_equipment_before_bulk_recovery(self):
        task = self.task()
        events = []
        def inventory():
            events.append('observe' if task._preparation_priority_pass else 'recover')
            task._card_inventory.ready = True
            return True
        task._prepare_card_inventory = Mock(side_effect=inventory)
        task._handle_preparation_stage = Mock(side_effect=lambda _: events.extend(['deploy', 'equip']) or True)
        self.assertTrue(task._handle_preparation_priorities())
        self.assertEqual(events, ['observe', 'deploy', 'equip', 'recover', 'deploy', 'equip'])
        self.assertFalse(task._preparation_priority_pass)

    def test_partial_inventory_never_allows_purchase_and_is_invalidated_on_failure(self):
        task = self.task()
        def fail():
            self.assertFalse(task._is_purchase_allowed())
            task._reconcile_inventory((HandUnit(None, 1, (655, 619), (607, 540, 96, 158)),),
                                      {1: BoardUnit(None, 1)})
            self.assertTrue(task._card_inventory.ready)
            return False
        task._prepare_card_inventory = Mock(side_effect=fail)
        self.assertFalse(task._handle_preparation_priorities())
        self.assertFalse(task._preparation_priority_pass)
        self.assertFalse(task._card_inventory.ready)


if __name__ == '__main__':
    unittest.main()
