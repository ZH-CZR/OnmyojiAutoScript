"""Shop visibility regressions; simulated frames, no device or user config."""
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tasks.Chess.runtime.economy import ChessEconomyMixin
from tasks.Chess.runtime.settings import ChessRuntimeSettings
from tasks.Chess.script_task import ScriptTask
from tasks.Chess.assets import ChessAssets
from tasks.GameUi.assets import GameUiAssets


class ShopProbe(ChessEconomyMixin, ChessRuntimeSettings):
    I_CHESS_SHOP_REFRESH = 'refresh'
    I_REFRESH_NOT_GOLD = 'no_gold'
    I_CHECK_MARKET = 'market_marker'
    I_MARKET = 'market'
    I_SELECT_GRIGRI = 'grigri'

    def __init__(self, frames):
        self.frames = iter(frames)
        self.frame = next(self.frames)
        self._shop_assumed_open = True
        self._economy_battle_mode = True
        self.device = SimpleNamespace(click_record_remove=Mock())
        self.click = Mock()
        self._shop_slot_refresh_snapshot = Mock()
        self._clear_economy_click_history = Mock()
        self._read_shop_gold = Mock(return_value=100)
        self._read_remaining_time = Mock(return_value=60)
        self._read_round_number = Mock(return_value=12)

    def appear(self, marker):
        return marker in self.frame

    def screenshot(self):
        self.frame = next(self.frames, self.frame)

    def _read_chess_mode(self):
        return '鬼' if 'ghost' in self.frame else '战'


class ChessShopTest(unittest.TestCase):
    def test_real_task_resolves_shop_refresh_independently_of_navigation(self):
        self.assertIs(ScriptTask.I_CHESS_SHOP_REFRESH, ChessAssets.I_CHESS_SHOP_REFRESH)
        self.assertIs(ScriptTask.I_REFRESH, GameUiAssets.I_REFRESH)
        self.assertIsNot(ScriptTask.I_CHESS_SHOP_REFRESH, ScriptTask.I_REFRESH)
        self.assertEqual(ScriptTask.I_CHESS_SHOP_REFRESH.roi_back, (1169, 419, 65, 64))
        # 覆盖完整任务类的解析路径，禁止把公共刷新素材带入商店检查。
        task = object.__new__(ScriptTask)
        task.appear = Mock(side_effect=lambda rule: rule is ChessAssets.I_CHESS_SHOP_REFRESH)
        self.assertTrue(task._shop_refresh_marker_visible())
        task.appear.assert_called_once_with(ChessAssets.I_CHESS_SHOP_REFRESH)

    def test_refresh_waits_out_brief_occlusion(self):
        task = ShopProbe([set(), set(), {'refresh'}])
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertTrue(task._wait_for_shop_refresh_button())
        task.click.assert_not_called()

    def test_ghost_phase_is_not_reported_as_missing_button(self):
        task = ShopProbe([{'ghost', 'refresh'}])
        with patch('tasks.Chess.runtime.economy.logger') as log:
            self.assertFalse(task._wait_for_shop_refresh_button())
        log.warning.assert_not_called()
        log.info.assert_called_once_with('停止棋局商店刷新: 检测到鬼阶段')
        task.click.assert_not_called()

    def test_closed_shop_reports_failed_confirmation_after_new_frames(self):
        task = ShopProbe([set()])
        task.screenshot = Mock()
        with patch('tasks.Chess.runtime.economy.time.sleep'), \
                patch('tasks.Chess.runtime.economy.logger') as log:
            self.assertFalse(task._wait_for_shop_refresh_button())
        self.assertEqual(task.screenshot.call_count, 2)
        self.assertFalse(task._shop_assumed_open)
        log.warning.assert_called_once()
        task.click.assert_not_called()

    def test_battle_retries_blocked_economy_after_cooldown_then_stops_on_complete(self):
        clock = SimpleNamespace(now=0.)
        calls = []
        def economy():
            calls.append(clock.now)
            return 'blocked' if len(calls) == 1 else 'complete'
        task = SimpleNamespace(
            device=SimpleNamespace(stuck_record_clear=Mock()),
            _refresh_round_state_screenshot=Mock(return_value=False),
            _finish_chess_game_after_open_lineup_missing=Mock(side_effect=[False] * 6 + [True]),
            _read_round_number=Mock(return_value=21),
            _read_chess_mode=Mock(return_value='战'),
            _handle_battle_sell_stage=Mock(return_value=True),
            _run_battle_economy_until_budget_limit=economy,
            _handle_passive_stage=Mock(), SLOW_POLL_INTERVAL=1.,
        )
        def sleep(seconds):
            clock.now += seconds
        with patch('tasks.Chess.script_task.time.sleep', side_effect=sleep), \
                patch('tasks.Chess.script_task.time.monotonic', side_effect=lambda: clock.now):
            ScriptTask.run_one_round(task, 21)
        self.assertEqual(calls, [0., 3.])
        task._handle_battle_sell_stage.assert_called_once()

    def test_battle_open_failure_remains_retryable_and_restores_context(self):
        task = SimpleNamespace(
            _economy_battle_mode=False,
            _read_chess_mode=Mock(return_value='战'),
            _read_remaining_time=Mock(return_value=6),
            _schedule_economy_cycle=Mock(),
        )
        contexts = []
        def purchase():
            contexts.append(task._economy_battle_mode)
            return None
        task.purchase_lineup_cards_once = purchase
        task._run_battle_economy_cycle = MethodType(ScriptTask._run_battle_economy_cycle, task)
        self.assertEqual(ScriptTask._run_battle_economy_until_budget_limit(task), 'blocked')
        self.assertEqual(contexts, [True])
        self.assertFalse(task._economy_battle_mode)
        task._schedule_economy_cycle.assert_not_called()

    def test_battle_successfully_continues_after_open_and_restores_context(self):
        task = SimpleNamespace(
            _economy_battle_mode=False, _economy_pending=True,
            _read_chess_mode=Mock(return_value='战'),
            _read_remaining_time=Mock(return_value=72),
            purchase_lineup_cards_once=Mock(return_value=[]),
            _schedule_economy_cycle=Mock(),
            _run_economy_atomic_batch=Mock(return_value='complete'),
        )
        task._run_battle_economy_cycle = MethodType(ScriptTask._run_battle_economy_cycle, task)
        self.assertEqual(ScriptTask._run_battle_economy_until_budget_limit(task), 'complete')
        task._run_economy_atomic_batch.assert_called_once_with(battle_mode=True)
        self.assertFalse(task._economy_battle_mode)

    def test_battle_time_limit_does_not_reopen_shop(self):
        for remaining in (5, 4, 0):
            with self.subTest(remaining=remaining):
                task = SimpleNamespace(
                    _read_chess_mode=Mock(return_value='战'),
                    _read_remaining_time=Mock(return_value=remaining),
                    purchase_lineup_cards_once=Mock(),
                )
                self.assertEqual(ScriptTask._run_battle_economy_cycle(task), 'complete')
                task.purchase_lineup_cards_once.assert_not_called()

    def test_battle_countdown_stops_next_action_at_five_seconds(self):
        task = SimpleNamespace(
            _economy_pending=True, _read_chess_mode=Mock(return_value='战'),
            _read_remaining_time=Mock(side_effect=[10, 6, 5]),
            purchase_lineup_cards_once=Mock(return_value=[]),
            _schedule_economy_cycle=Mock(),
            _run_economy_atomic_batch=Mock(return_value='pending'), screenshot=Mock(),
        )
        self.assertEqual(ScriptTask._run_battle_economy_cycle(task), 'complete')
        task._run_economy_atomic_batch.assert_called_once_with(battle_mode=True)

    def preparation_round(self, *, prepared=True, modes=None, times=None):
        events = []
        task = SimpleNamespace(
            device=SimpleNamespace(stuck_record_clear=Mock()),
            _refresh_round_state_screenshot=Mock(return_value=False),
            _finish_chess_game_after_open_lineup_missing=Mock(side_effect=[False, True]),
            _read_round_number=Mock(return_value=19),
            _read_chess_mode=Mock(return_value='备'),
            appear=Mock(return_value=False), I_SELECT_GRIGRI='grigri',
            SLOW_POLL_INTERVAL=1.,
            purchase_lineup_cards_once=Mock(side_effect=lambda: events.append('buy')),
            _is_preparation_mode=Mock(side_effect=modes) if modes else Mock(return_value=True),
            _read_remaining_time=Mock(side_effect=times or [10, 10, 3]),
            _handle_preparation_stage=Mock(side_effect=lambda _: events.append('formation') or prepared),
            _run_economy_atomic_batch=Mock(side_effect=lambda **_: events.append('economy') or 'pending'),
            screenshot=Mock(),
        )
        task._schedule_economy_cycle = lambda: setattr(task, '_economy_pending', True)
        task._run_preparation_economy_until_time_limit = MethodType(
            ScriptTask._run_preparation_economy_until_time_limit, task,
        )
        with patch('tasks.Chess.script_task.time.sleep'):
            ScriptTask.run_one_round(task, 19)
        return task, events

    def test_preparation_uses_idle_time_after_formation_until_three_seconds(self):
        task, events = self.preparation_round()
        self.assertEqual(events, ['buy', 'formation', 'economy'])
        self.assertEqual(task._read_remaining_time.call_count, 3)
        task._handle_preparation_stage.assert_called_once()

    def test_failed_formation_does_not_start_idle_economy(self):
        task, events = self.preparation_round(prepared=False)
        self.assertEqual(events, ['buy', 'formation'])
        task._run_economy_atomic_batch.assert_not_called()

    def test_phase_change_after_formation_cancels_idle_economy(self):
        task, events = self.preparation_round(modes=[True, True, True, False])
        self.assertEqual(events, ['buy', 'formation'])
        task._run_economy_atomic_batch.assert_not_called()

    def test_three_seconds_does_not_start_another_economy_action(self):
        task, events = self.preparation_round(times=[10, 3])
        self.assertEqual(events, ['buy', 'formation'])
        task._run_economy_atomic_batch.assert_not_called()

    def economy_task(self, gold):
        task = ShopProbe([{'refresh'}])
        task._reset_economy_state()
        task._schedule_economy_cycle()
        task._lineup_final_level = Mock(return_value=9)
        task._read_level = Mock(return_value=3)
        task._read_shop_gold = Mock(side_effect=lambda: gold[0])
        def buy(*args, **kwargs):
            gold[0] -= task.EXPERIENCE_COST
            return 'success'
        task.I_EXPERIENCE = 'experience'
        task._click_economy_button_and_confirm_gold = Mock(side_effect=buy)
        return task

    def test_two_experience_purchases_before_refresh(self):
        task = self.economy_task([50])
        self.assertEqual(task._run_economy_atomic_batch(True), 'pending')
        self.assertEqual(task._run_economy_atomic_batch(True), 'pending')
        self.assertEqual(task._click_economy_button_and_confirm_gold.call_count, 2)
        self.assertEqual(task._next_economy_operation(3), 'refresh')
        task.click.assert_not_called()

    def test_second_experience_cannot_spend_reserved_gold(self):
        task = self.economy_task([40])
        self.assertEqual(task._run_economy_atomic_batch(True), 'complete')
        self.assertEqual(task._run_economy_atomic_batch(True), 'complete')
        task._click_economy_button_and_confirm_gold.assert_called_once()
        self.assertEqual(task._read_shop_gold(), 36)

    def open_shop(self, frames):
        task = ShopProbe(frames)
        clock = SimpleNamespace(now=0.)
        def sleep(seconds):
            clock.now += seconds
        with patch('tasks.Chess.runtime.economy.time.sleep', side_effect=sleep), \
                patch('tasks.Chess.runtime.economy.time.monotonic', side_effect=lambda: clock.now):
            result = task._ensure_shop_open()
        return task, result

    def test_stale_cache_does_not_prove_shop_open(self):
        task = ShopProbe([set()])
        self.assertFalse(task._is_shop_open())
        self.assertFalse(task._shop_assumed_open)

    def test_closed_shop_auxiliary_marker_does_not_confirm_open(self):
        task, result = self.open_shop([{'market_marker'}])
        self.assertFalse(result)
        self.assertFalse(task._shop_assumed_open)
        task.click.assert_called_once_with(task.I_MARKET)

    def test_open_click_requires_visible_confirmation(self):
        task, result = self.open_shop([set(), set(), {'refresh'}])
        self.assertTrue(result)
        task.click.assert_called_once_with(task.I_MARKET)

    def test_temporary_occlusion_does_not_toggle_visible_shop(self):
        task, result = self.open_shop([set(), {'refresh'}])
        self.assertTrue(result)
        task.click.assert_not_called()

    def test_phase_change_during_open_cancels_scan(self):
        task, result = self.open_shop([set(), set(), {'ghost'}])
        self.assertFalse(result)
        self.assertFalse(task._shop_assumed_open)

    def test_hidden_refresh_never_clicks_or_scans_closed_shop(self):
        task = ShopProbe([set()])
        self.assertEqual(task._click_shop_refresh_and_confirm_slots(True), 'no_progress')
        task.click.assert_not_called()
        task._shop_slot_refresh_snapshot.assert_not_called()
        task._recognize_shop_slot = Mock()
        with patch.object(task, '_ensure_shop_open', return_value=False):
            self.assertIsNone(task.purchase_lineup_cards_once())
        task._recognize_shop_slot.assert_not_called()

    def test_shop_closes_after_refresh_without_scanning_board(self):
        task = ShopProbe([{'refresh'}, {'refresh'}, set()])
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertEqual(task._click_shop_refresh_and_confirm_slots(True), 'no_progress')
        task.click.assert_called_once_with(task.I_CHESS_SHOP_REFRESH)
        task._shop_slot_refresh_snapshot.assert_called_once()

    def test_shop_closure_does_not_count_as_purchase_success(self):
        task = ShopProbe([{'refresh'}, set()])
        task._recognize_shop_slot = Mock(return_value={'source': 'test', 'score': 1.})
        task._can_afford_shop_shikigami = Mock(return_value=True)
        task._shikigami_display_name = Mock(return_value='山兔')
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertFalse(task._buy_shop_slot(1, 'card', 'yamausagi'))
        task._recognize_shop_slot.assert_called_once()


if __name__ == '__main__':
    unittest.main()
