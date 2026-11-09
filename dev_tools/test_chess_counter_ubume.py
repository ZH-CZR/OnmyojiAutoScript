"""反击姑获鸟：真实入口及纯策略的离线回归，不操作游戏。"""
import unittest
from unittest.mock import Mock, patch

from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit
from tasks.Chess.script_task import ScriptTask
from tasks.Chess.strategy import counter_ubume as plan
from tasks.Chess.strategy.lineup import LineupBond, resolve_lineup_key
from tasks.Chess.config import ChessConfig


def card(name, star=1, x=100):
    return HandUnit(name, star, (x, 600), (x - 42, 573, 84, 117))


def inventory(hand=(), board=None):
    result = CardInventory()
    result.reconcile(hand, board or {})
    return result


class CounterPlanTest(unittest.TestCase):
    def test_registered_chinese_config_and_slot_layout(self):
        self.assertEqual(resolve_lineup_key('反击姑获鸟'), plan.KEY)
        self.assertEqual(ChessConfig(lineup_bond='反击姑获鸟').lineup_bond, LineupBond.COUNTER_UBUME)
        self.assertEqual([(s['name'], s['position'], s['min_level']) for s in plan.SLOTS], [
            ('miketsu', 1, 1), ('kachou_fuugetsu', 3, 1), ('jinkougyou', 5, 1),
            ('kuro_douji', 7, 1), ('gashadokuro', 9, 8), ('kujira', 4, 7),
            ('kujira', 6, 6), ('ubume', 8, 1)])

    def test_purchases_track_current_inventory_and_ubume_wins_even_at_zero(self):
        stock = CardInventory(totals={'ubume': 0, 'miketsu': 8, 'kachou_fuugetsu': 7}, ready=True)
        names = ['kachou_fuugetsu', 'miketsu', 'ubume']
        self.assertEqual(sorted(names, key=lambda n: plan.purchase_priority(n, stock)),
                         ['ubume', 'miketsu', 'kachou_fuugetsu'])
        stock.totals['kachou_fuugetsu'] = 9
        self.assertFalse(plan.can_buy('kachou_fuugetsu', stock))
        stock.totals['miketsu'] = 2
        self.assertLess(plan.purchase_priority('kachou_fuugetsu', stock),
                        plan.purchase_priority('miketsu', stock))

    def test_kujira_buys_only_six_materials_and_both_two_stars_are_protected(self):
        second = card('kujira', 2)
        stock = inventory((second,), {6: BoardUnit('kujira', 2)})
        self.assertFalse(plan.can_buy('kujira', stock))
        self.assertFalse(stock.excess(second, 2, 2))
        extra = card('kujira', 1, 200)
        stock.reconcile((second, extra), stock.board)
        self.assertTrue(stock.excess(extra, 2, 2))

    def test_substitute_is_one_copy_and_stops_after_primary_is_acquired(self):
        stock = inventory()
        self.assertTrue(plan.can_buy('kappa', stock))
        stock.purchased('kappa')
        self.assertFalse(plan.can_buy('kappa', stock))
        stock.reconcile((card('jinkougyou'),), {})
        self.assertFalse(plan.can_buy('kappa', stock))
        stock.reconcile((), {})
        self.assertFalse(plan.can_buy('kappa', stock, primary_acquired=True))

    def test_stage_gates_require_real_board_stars(self):
        stock = inventory((card('ubume', 3),))
        self.assertEqual(plan.operation(5, stock), 'experience')
        self.assertEqual(plan.operation(6, stock), 'refresh')
        stock.reconcile((), {8: BoardUnit('ubume', 3, star_confirmed=False)})
        self.assertEqual(plan.operation(6, stock), 'refresh')
        stock.reconcile((), {8: BoardUnit('ubume', 3)})
        self.assertEqual(plan.operation(6, stock), 'experience')
        self.assertEqual(plan.operation(7, stock), 'refresh')
        stock.board[1] = BoardUnit('miketsu', 3)
        self.assertEqual(plan.operation(7, stock), 'experience')
        self.assertEqual(plan.operation(8, stock), 'refresh')

    def test_unknown_board_and_unconfirmed_second_star_do_not_upgrade(self):
        stock = inventory((), {8: BoardUnit('ubume', 3), 1: BoardUnit(None, 3)})
        self.assertEqual(plan.operation(7, stock), 'hold')
        stock.reconcile((), {8: BoardUnit('ubume', 3), 1: BoardUnit('miketsu', 3, star_confirmed=False)})
        self.assertEqual(plan.operation(7, stock), 'refresh')

    def test_early_unknowns_allow_fixed_slot_candidate_even_when_population_full(self):
        stock = CardInventory()
        stock.reconcile((card('ubume'),), {11: BoardUnit(None, None)}, allow_unknown_board=True)
        self.assertEqual(plan.missing_deployments(1, stock)[0]['position'], 8)
        self.assertTrue(plan.can_buy('miketsu', stock, level=5))
        self.assertEqual(plan.operation(5, stock), 'experience')
        self.assertFalse(plan.can_buy('miketsu', stock, level=6))
        self.assertEqual(plan.operation(6, stock), 'hold')
        stock.board = {8: BoardUnit(None, None)}
        self.assertEqual(plan.missing_deployments(5, stock)[0]['position'], 8)

    def test_level_six_seven_eight_enable_correct_roles(self):
        stock = inventory((card('kujira', 2), card('gashadokuro', 1, 200)))
        positions = lambda level: {s['position'] for s in plan.missing_deployments(level, stock)}
        self.assertEqual(positions(5), set())
        self.assertEqual(positions(6), {6})
        self.assertEqual(positions(7), {4, 6})
        self.assertEqual(positions(8), {4, 6, 9})

    def test_primary_and_fallback_share_one_role_not_two_population(self):
        stock = inventory((card('kappa'),))
        self.assertEqual(plan.missing_deployments(6, stock)[0]['name'], 'kappa')
        stock.reconcile((card('kappa'), card('jinkougyou', x=200)), {})
        self.assertEqual([s['name'] for s in plan.missing_deployments(6, stock)], ['jinkougyou'])

    def test_completed_eight_level_lineup_does_not_pay_for_useless_refreshes(self):
        stock = CardInventory(ready=True, totals={name: plan.purchase_limit(name)
                                                for name in plan.COUNTER_UBUME['shikigami']})
        self.assertEqual(plan.operation(8, stock), 'hold')
        stock.totals['miketsu'] -= 1
        self.assertEqual(plan.operation(8, stock), 'refresh')

    def test_first_kujira_uses_level_six_role_even_when_acquired_at_level_seven(self):
        stock = inventory((card('kujira', 2),))
        self.assertEqual([s['position'] for s in plan.missing_deployments(7, stock)], [6, 4])

    def test_population_and_key_bond_then_frontline_two_star_precede_near_three(self):
        stock = inventory((card('kuro_douji', 1), card('miketsu', 2, 200), card('miketsu', 2, 300),
                           card('miketsu', 1, 400)),
                          {7: BoardUnit('kuro_douji', 1), 8: BoardUnit('ubume', 2)})
        # 缺花鸟卷，可以立即补人口且激活平安京/追击。
        self.assertLess(plan.purchase_priority('kachou_fuugetsu', stock, 6),
                        plan.purchase_priority('miketsu', stock, 6))
        # 买一张黑童子立刻补二星，优于追已有7张材料的其他单位。
        self.assertLess(plan.purchase_priority('kuro_douji', stock, 6),
                        plan.purchase_priority('miketsu', stock, 6))
        self.assertLess(plan.purchase_priority('ubume', stock, 6),
                        plan.purchase_priority('kachou_fuugetsu', stock, 6))

    def test_future_locked_role_does_not_get_population_priority(self):
        stock = CardInventory(ready=True, totals={'gashadokuro': 0, 'miketsu': 7})
        self.assertGreater(plan.purchase_priority('gashadokuro', stock, 6),
                           plan.purchase_priority('kachou_fuugetsu', stock, 6))

    def test_gashadokuro_one_copy_before_eight_then_releases_full_star_goal(self):
        stock = inventory()
        self.assertTrue(plan.can_buy('gashadokuro', stock, level=7))
        stock.purchased('gashadokuro')
        self.assertFalse(plan.can_buy('gashadokuro', stock, level=7))
        self.assertTrue(plan.can_buy('gashadokuro', stock, level=8))
        self.assertEqual(plan.purchase_limit('gashadokuro', 8), 9)


class CounterRuntimeTest(unittest.TestCase):
    def task(self, level=6, hand=(), board=None):
        task = object.__new__(ScriptTask)
        task.select_lineup_strategy(plan.KEY)
        task._card_inventory = inventory(hand, board)
        task._card_tracking_active = True
        task._counter_deployment_pending = False
        task._counter_primary_acquired = False
        task._counter_deploy_target = None
        task._counter_bought_names = set()
        task._board_shikigami_attributes = {}
        task._current_round_no = 1
        task._read_level = Mock(return_value=level)
        task._read_chess_mode = Mock(return_value='备')
        task._read_round_number = Mock(return_value=1)
        task._read_shop_gold = Mock(return_value=100)
        task._inventory_action_allowed = Mock(return_value=True)
        task._handle_preparation = Mock(return_value=True)
        return task

    def simulate_deployment(self, task):
        task._counter_refresh_inventory = Mock(return_value=True)
        task._sell_excess_inventory_cards = Mock()
        def deploy(name, source):
            unit = next(u for u in task._card_inventory.hand if u.name == name and u.position == source)
            position = task.shikigami_deploy_positions[name]
            board = {**task._card_inventory.board, position: BoardUnit(name, unit.star)}
            task._card_inventory.reconcile(tuple(u for u in task._card_inventory.hand if u is not unit), board)
            return True
        task.deploy_shikigami_hand_card = Mock(side_effect=deploy)

    def test_strict_gold_boundaries_and_early_no_refresh(self):
        task = self.task(level=5)
        self.assertEqual(task._next_economy_operation(5), 'experience')
        self.assertFalse(task._can_execute_economy_operation(5, 54, 'experience'))
        self.assertTrue(task._can_execute_economy_operation(5, 55, 'experience'))
        self.assertFalse(task._can_execute_economy_operation(5, 100, 'refresh'))
        task._read_level.return_value = 6
        self.assertFalse(task._can_execute_economy_operation(6, 32, 'refresh'))
        self.assertTrue(task._can_execute_economy_operation(6, 33, 'refresh'))
        self.assertFalse(task._can_execute_economy_operation(6, 100, 'experience'))
        task._card_inventory.board[8] = BoardUnit('ubume', 3)
        self.assertFalse(task._can_execute_economy_operation(6, 34, 'experience'))
        self.assertTrue(task._can_execute_economy_operation(6, 35, 'experience'))
        self.assertFalse(task._can_execute_economy_operation(8, 1, 'refresh'))
        self.assertTrue(task._can_execute_economy_operation(8, 2, 'refresh'))

    def test_card_purchase_reserves_thirty_at_six_and_seven_but_not_at_eight(self):
        task = self.task()
        for level, gold, expected in ((5, 4, True), (6, 34, False), (6, 35, True),
                                      (7, 34, False), (8, 4, True)):
            task._read_level.return_value = level
            task._read_shop_gold.return_value = gold
            self.assertEqual(task._can_afford_shop_shikigami(1, known_price=4), expected)

    def test_stale_gold_after_purchase_cannot_cross_reserve_on_next_card(self):
        task = self.task()
        task._read_shop_gold.return_value = 33
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', return_value=True) as buy:
            self.assertTrue(task._buy_shop_slot(1, 'slot', 'ubume'))
            self.assertFalse(task._buy_shop_slot(2, 'slot', 'ubume'))
        buy.assert_called_once()
        self.assertEqual(task._counter_gold_ceiling, 31)
        task._current_round_no = 2
        task._read_round_number.return_value = 2
        self.assertTrue(task._can_afford_shop_shikigami(1, 2))

    def test_confirmed_experience_and_refresh_each_consume_budget_once(self):
        task = self.task(level=5)
        task._read_shop_gold.return_value = 55
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._click_economy_button_and_confirm_gold',
                   return_value='success'):
            self.assertEqual(task._click_economy_button_and_confirm_gold('exp', 4, 'exp', False), 'success')
        self.assertFalse(task._can_execute_economy_operation(5, 55, 'experience'))
        task._read_level.return_value = 6
        task._counter_gold_ceiling = 33
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._click_shop_refresh_and_confirm_slots',
                   return_value='success'):
            task._click_shop_refresh_and_confirm_slots(False)
        self.assertEqual(task._counter_gold_ceiling, 31)
        self.assertFalse(task._can_execute_economy_operation(6, 55, 'refresh'))

    def test_uncertain_refresh_retries_do_not_reserve_cost_repeatedly(self):
        task = self.task()
        task._read_shop_gold.return_value = 40
        def uncertain(allow_hidden):
            task._unconfirmed_shop_refresh = True
            return 'no_progress'
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._click_shop_refresh_and_confirm_slots',
                   side_effect=uncertain):
            task._click_shop_refresh_and_confirm_slots(False)
            task._click_shop_refresh_and_confirm_slots(False)
        self.assertEqual(task._counter_gold_ceiling, 38)

    def test_real_shop_reorders_after_each_purchase_and_deploys_before_next_purchase(self):
        task = self.task(board={8: BoardUnit('ubume', 2)})
        task._card_inventory.totals.update(ubume=8, miketsu=1, kachou_fuugetsu=2)
        task._refresh_inventory_hand = Mock(return_value=True)
        task._is_purchase_allowed = Mock(return_value=True)
        task._ensure_shop_open = Mock(return_value=True)
        task._shop_slots = Mock(return_value=[(1, 'miketsu'), (2, 'kachou_fuugetsu'), (3, 'ubume')])
        task._recognize_shop_slot = Mock(side_effect=lambda i, click: {'name': click, 'source': 'test', 'score': 1.})
        task.screenshot = Mock()
        actions = []
        shop_open = [True]
        task._ensure_shop_open.side_effect = lambda: shop_open.__setitem__(0, True) or True
        task._handle_preparation.side_effect = lambda: shop_open.__setitem__(0, False) or True
        def buy(slot_index, click_rule, matched_name):
            self.assertTrue(shop_open[0], '补阵/装备关闭商店后，下一张购买必须重新开店')
            actions.append(('buy', matched_name))
            return True
        def deploy():
            actions.append(('deploy',))
            task._counter_deployment_pending = False
            return []
        task.deploy_shikigami_from_hand = Mock(side_effect=deploy)
        task._counter_confirm_board_stars = Mock(return_value=True)
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', side_effect=buy), \
                patch('tasks.Chess.runtime.economy.time.sleep'):
            task.purchase_lineup_cards_once()
        self.assertEqual(actions, [('buy', 'ubume'), ('buy', 'kachou_fuugetsu'), ('deploy',),
                                   ('buy', 'miketsu'), ('deploy',)])

    def test_first_purchase_in_battle_defers_deployment_without_blocking_economy(self):
        task = self.task(hand=(card('miketsu'),))
        task._read_chess_mode.return_value = '战'
        self.assertTrue(task._after_lineup_purchase('miketsu'))
        self.assertTrue(task._counter_deployment_pending)
        self.assertTrue(task._can_execute_economy_operation(6, 100, 'refresh'))
        with patch('tasks.Chess.runtime.card_tracking.ChessCardTrackingMixin.buy_lineup_shikigami_from_shop',
                   return_value=[]) as buy:
            self.assertEqual(task.purchase_lineup_cards_once(), [])
        buy.assert_called_once()
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._run_economy_atomic_batch',
                   return_value='pending') as operate:
            self.assertEqual(task._run_economy_atomic_batch(battle_mode=True), 'pending')
        operate.assert_called_once()

    def test_pending_battle_purchase_is_deployed_before_preparation_economy_resumes(self):
        task = self.task(hand=(card('miketsu'),))
        task._counter_deployment_pending = True
        self.simulate_deployment(task)
        with patch('tasks.Chess.runtime.card_tracking.ChessCardTrackingMixin._prepare_card_inventory', return_value=True):
            self.assertTrue(task._prepare_card_inventory())
        self.assertEqual(task._card_inventory.board[1], BoardUnit('miketsu', 1))
        self.assertFalse(task._counter_deployment_pending)

    def test_level_upgrade_deploys_newly_unlocked_second_kujira_before_more_economy(self):
        task = self.task(level=6, hand=(card('kujira', 2),), board={6: BoardUnit('kujira', 2)})
        self.simulate_deployment(task)
        def upgrade(*args):
            task._read_level.return_value = 7
            return 'pending'
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._run_economy_atomic_batch', side_effect=upgrade):
            self.assertEqual(task._run_economy_atomic_batch(), 'pending')
        self.assertEqual(task._card_inventory.board[4], BoardUnit('kujira', 2))

    def test_two_kujira_deploy_to_distinct_slots_and_count_as_two_population(self):
        task = self.task(level=7, hand=(card('kujira', 2), card('kujira', 2, 200)))
        self.simulate_deployment(task)
        task.deploy_shikigami_from_hand()
        self.assertEqual({p: u.name for p, u in task._card_inventory.board.items()}, {4: 'kujira', 6: 'kujira'})
        self.assertEqual(task._read_lineup_capacity_status()['current'], 2)
        self.assertIsNone(task._counter_deploy_target)

    def test_second_kujira_and_gashadokuro_stay_in_hand_until_correct_level(self):
        task = self.task(level=6, hand=(card('kujira', 2), card('gashadokuro', 1, 200)),
                         board={6: BoardUnit('kujira', 2)})
        self.simulate_deployment(task)
        task.deploy_shikigami_from_hand()
        task.deploy_shikigami_hand_card.assert_not_called()
        task._read_level.return_value = 7
        task.deploy_shikigami_from_hand()
        self.assertEqual(task._card_inventory.board[4], BoardUnit('kujira', 2))
        self.assertNotIn(9, task._card_inventory.board)
        task._read_level.return_value = 8
        task.deploy_shikigami_from_hand()
        self.assertEqual(task._card_inventory.board[9], BoardUnit('gashadokuro', 1))

    def test_replacement_is_recall_then_deploy_and_only_then_substitute_can_be_sold(self):
        task = self.task(hand=(card('jinkougyou'),), board={5: BoardUnit('kappa', 1)})
        self.simulate_deployment(task)
        held_kappa = card('kappa', x=200)
        self.assertFalse(task._inventory_card_excess(held_kappa))
        actions = []
        def recall(position):
            actions.append(('recall', position))
            board = dict(task._card_inventory.board)
            board.pop(position)
            task._card_inventory.reconcile((*task._card_inventory.hand, held_kappa), board)
            return True
        task._recall_inventory_unit = Mock(side_effect=recall)
        task.deploy_shikigami_from_hand()
        self.assertEqual(actions, [('recall', 5)])
        self.assertEqual(task._card_inventory.board[5], BoardUnit('jinkougyou', 1))
        self.assertTrue(task._inventory_card_excess(held_kappa))
        self.assertFalse(task._inventory_should_buy('kappa'))

    def test_failed_substitute_recall_does_not_deploy_or_sell_it(self):
        task = self.task(hand=(card('jinkougyou'),), board={5: BoardUnit('kappa', 1)})
        self.simulate_deployment(task)
        task._recall_inventory_unit = Mock(return_value=False)
        task.deploy_shikigami_from_hand()
        task.deploy_shikigami_hand_card.assert_not_called()
        task._sell_excess_inventory_cards.assert_not_called()
        self.assertTrue(task._counter_deployment_pending)

    def test_dual_kujira_have_independent_equipment_slots(self):
        task = self.task(level=7, board={4: BoardUnit('kujira', 2), 6: BoardUnit('kujira', 2)})
        task._set_shikigami_attributes('kujira@4', (None, 'poshi', 'zhaocaimao'))
        self.assertEqual(task._shikigami_name_at_set(4), 'kujira@4')
        self.assertEqual([p for p, _ in task._soul_targets('poshi', 'attack', {'kujira'})], [6])
        self.assertEqual(task._shikigami_attributes('kujira@6'), (None, None, None))

    def test_unwanted_three_star_kujira_is_not_a_goal_or_upgrade_candidate(self):
        task = self.task(level=7, hand=(card('kujira', 3),), board={6: BoardUnit('kujira', 2),
                                                                                8: BoardUnit('ubume', 3)})
        self.assertTrue(task._inventory_card_excess(task._card_inventory.hand[0]))
        self.assertFalse(task._inventory_needs_upgrade(BoardUnit('kujira', 2), task._card_inventory.hand))
        task._card_inventory.board[4] = BoardUnit('kujira', 3)
        self.assertEqual(task._next_economy_operation(7), 'refresh')

    def test_failed_deployment_does_not_leave_temporary_position_override(self):
        task = self.task(level=7, hand=(card('kujira', 2),))
        task._counter_refresh_inventory = Mock(return_value=True)
        task.deploy_shikigami_hand_card = Mock(return_value=False)
        task.deploy_shikigami_from_hand()
        self.assertIsNone(task._counter_deploy_target)
        self.assertTrue(task._counter_deployment_pending)

    def test_missing_stable_star_frame_cannot_authorize_an_upgrade(self):
        task = self.task(level=7, board={8: BoardUnit('ubume', 2)})
        task._read_card_star = Mock(side_effect=[3, None, 3])
        with patch('tasks.Chess.runtime.counter_ubume.time.sleep'):
            self.assertFalse(task._counter_confirm_board_stars())
        self.assertEqual(task._card_inventory.board[8], BoardUnit('ubume', 2))
        self.assertFalse(task._card_inventory.ready)

    def test_inferred_third_star_does_not_change_upgrade_threshold(self):
        task = self.task(level=7, board={8: BoardUnit('ubume', 3),
                                       1: BoardUnit('miketsu', 3, star_confirmed=False)})
        self.assertEqual(task._next_economy_operation(7), 'refresh')
        task._card_inventory.board[1] = BoardUnit('miketsu', 3)
        self.assertEqual(task._next_economy_operation(7), 'experience')

    def test_legacy_lineup_keeps_old_economy(self):
        task = self.task()
        task.select_lineup_strategy('qijiaoshan')
        self.assertEqual(task._economy_sequence_for_level(6), ('experience', 'experience', 'refresh'))
        self.assertEqual(task._economy_reserve_for_level(6), 23)

    def equipped_task(self):
        board = {s['position']: BoardUnit(s['name'], 2) for s in plan.SLOTS}
        task = self.task(level=8, board=board)
        task._soul_hand_cards = Mock(return_value=[])
        return task

    def targets(self, task, soul, category):
        names = {u.name for u in task._card_inventory.board.values()}
        return [p for p, _ in task._soul_targets(soul, category, names)]

    def test_attack_defense_and_remaining_functional_orders(self):
        task = self.equipped_task()
        self.assertEqual(self.targets(task, 'poshi', 'attack'), [8, 4, 6])
        self.assertEqual(self.targets(task, 'beifu', 'functional'), [7, 3, 1, 5, 9])
        self.assertEqual(self.targets(task, 'diaopinghuo', 'functional'), [1, 3, 5, 7, 9])
        self.assertEqual(self.targets(task, 'wangliangzhixia', 'functional'), [1, 3, 5, 7, 9])

    def test_core_reserves_survive_other_souls_and_emblems(self):
        task = self.equipped_task()
        task._set_shikigami_attributes('ubume@8', (None, 'poshi', None))
        task._set_shikigami_attributes('kuro_douji@7', (None, 'beifu', None))
        self.assertNotIn(8, self.targets(task, 'wangqie', 'attack'))
        self.assertNotIn(7, self.targets(task, 'jingji', 'functional'))
        self.assertEqual(self.targets(task, 'yingshengchong', 'attack')[0], 8)
        self.assertEqual(self.targets(task, 'zheng', 'functional')[0], 7)
        targets = task._emblem_targets('回响纹章', {u.name for u in task._card_inventory.board.values()})
        self.assertNotIn(('ubume@8', 8), targets)
        self.assertNotIn(('kuro_douji@7', 7), targets)

    def test_uncertain_board_cannot_receive_souls_or_emblems(self):
        task = self.equipped_task()
        task._card_inventory.ready = False
        self.assertEqual(self.targets(task, 'yingshengchong', 'attack'), [])
        self.assertEqual(task._emblem_targets('回响纹章', {u.name for u in task._card_inventory.board.values()}), [])

    def test_extra_zheng_goes_to_other_frontline_after_black_has_it(self):
        task = self.equipped_task()
        task._set_shikigami_attributes('kuro_douji@7', (None, 'zheng', None))
        self.assertEqual(self.targets(task, 'zheng', 'functional'), [3, 1, 5, 9])

    def test_last_core_soul_waits_for_owner_but_extra_can_be_used(self):
        task = self.equipped_task()
        task._card_inventory.board.pop(7)
        task._soul_hand_cards.return_value = [{'name': 'zheng'}]
        self.assertEqual(self.targets(task, 'zheng', 'functional'), [])
        task._soul_hand_cards.return_value = [{'name': 'zheng'}, {'name': 'zheng'}]
        self.assertEqual(self.targets(task, 'zheng', 'functional'), [3, 1, 5, 9])

    def test_huoling_and_zhaocai_prefer_both_kujira(self):
        task = self.equipped_task()
        for name in plan.KUJIRA_SOULS:
            self.assertEqual(self.targets(task, name, 'functional')[:2], [4, 6])
        task._set_shikigami_attributes('kujira@4', (None, 'huoling', None))
        self.assertEqual(self.targets(task, 'huoling', 'functional')[0], 6)

    def test_kujira_reserves_fire_and_fortune_across_two_units(self):
        task = self.equipped_task()
        task._set_shikigami_attributes('kujira@4', (None, 'poshi', 'wangqie'))
        # 另一只的最后两格要留给火灵和招财猫。
        self.assertNotIn(6, self.targets(task, 'kuanggu', 'attack'))
        self.assertEqual(self.targets(task, 'huoling', 'functional')[0], 6)
        task._set_shikigami_attributes('kujira@6', (None, 'huoling', None))
        self.assertNotIn(6, self.targets(task, 'kuanggu', 'attack'))
        self.assertEqual(self.targets(task, 'zhaocaimao', 'functional')[0], 6)

    def test_single_kujira_preserves_both_utility_slots_until_second_is_deployed(self):
        task = self.equipped_task()
        task._card_inventory.board.pop(4)
        self.assertNotIn(6, self.targets(task, 'poshi', 'attack'))
        self.assertEqual(self.targets(task, 'zhaocaimao', 'functional')[0], 6)

    def test_surplus_gashadokuro_cleanup_changes_at_level_eight(self):
        extra = card('gashadokuro', 1, 200)
        task = self.task(level=7, hand=(card('gashadokuro', 1), extra))
        self.assertTrue(task._inventory_card_excess(extra))
        self.assertFalse(task._inventory_should_buy('gashadokuro'))
        task._read_level.return_value = 8
        self.assertFalse(task._inventory_card_excess(extra))
        self.assertTrue(task._inventory_should_buy('gashadokuro'))

    def test_current_two_cost_kujira_uses_two_coin_budget(self):
        task = self.task(level=6)
        task._read_shop_gold.return_value = 33
        with patch('tasks.Chess.runtime.economy.ChessEconomyMixin._buy_shop_slot', return_value=True):
            self.assertTrue(task._buy_shop_slot(1, 'slot', 'kujira'))
        self.assertEqual(task._counter_gold_ceiling, 31)

    def test_real_equipment_loop_handles_core_souls_before_generic_souls(self):
        task = self.equipped_task()
        remaining = [dict(name=n, position=(x, 600), category=c, text=n)
                     for n, x, c in [('poshi', 100, 'attack'), ('beifu', 200, 'functional'),
                                     ('zheng', 300, 'functional'), ('yingshengchong', 400, 'attack')]]
        task._soul_hand_cards = Mock(side_effect=lambda: list(remaining))
        task._is_preparation_mode = Mock(return_value=True)
        task.discover_souls_from_hand = Mock(return_value=0)
        task.equip_emblems_from_hand = Mock(return_value=[])
        task.equip_hakuzosu_protect_after_deploy = Mock(return_value=False)
        task.screenshot = Mock()
        actions = []
        def equip(source, set_index, operation_name):
            unit = next(c for c in remaining if c['position'] == source)
            actions.append((unit['name'], set_index))
            remaining.remove(unit)
            return True
        task._equip_soul_card = Mock(side_effect=equip)
        with patch('tasks.Chess.runtime.hand_operations.time.sleep'):
            task.equip_souls_from_hand({u.name for u in task._card_inventory.board.values()})
        self.assertEqual(actions, [('yingshengchong', 8), ('zheng', 7), ('poshi', 8), ('beifu', 7)])
        self.assertEqual(task._shikigami_attributes('ubume@8'), (None, 'yingshengchong', 'poshi'))
        self.assertEqual(task._shikigami_attributes('kuro_douji@7'), (None, 'zheng', 'beifu'))


if __name__ == '__main__':
    unittest.main()
