"""棋局无进展超时及经验扣款确认；虚拟时间/截图，不连接设备。"""
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from module.base.timer import Timer
from module.device.device import Device
from module.exception import GameStuckError
from tasks.Chess.script_task import ScriptTask, ROUND_PROGRESS_TIMEOUT


class ChessRuntimeSafetyTest(unittest.TestCase):
    def clock(self):
        clock = SimpleNamespace(now=1000.)
        stack = ExitStack()
        stack.enter_context(patch('module.base.timer.time.time', side_effect=lambda: clock.now))
        stack.enter_context(patch('tasks.Chess.script_task.time.monotonic', side_effect=lambda: clock.now))
        stack.enter_context(patch('tasks.Chess.script_task.time.sleep',
                                  side_effect=lambda seconds: setattr(clock, 'now', clock.now + seconds)))
        self.addCleanup(stack.close)
        return clock

    def round_task(self, clock, frame):
        task = ScriptTask.__new__(ScriptTask)
        device = SimpleNamespace(detect_record=set(), stuck_long_wait_list=Device.stuck_long_wait_list,
                                 stuck_timer=Timer(60).start(), stuck_timer_long=Timer(300).start(),
                                 app_is_running=Mock(return_value=True))
        device.stuck_record_clear = lambda: Device.stuck_record_clear(device)
        task.device = device
        task.SLOW_POLL_INTERVAL = 1.
        task._read_remaining_time = Mock(return_value=60)
        task._read_chess_mode = lambda: frame(clock.now - 1000.)[1]
        task._read_round_number = lambda: frame(clock.now - 1000.)[0]
        task._is_in_chess_game = Mock(return_value=True)
        task._finish_chess_game_after_open_lineup_missing = Mock(return_value=False)
        task._handle_battle_sell_stage = Mock(return_value=True)
        task._run_battle_economy_until_budget_limit = Mock(return_value='complete')
        task._run_game_by_rounds_without_device_stuck_timeout = lambda: task.run_one_round(1)

        def screenshot():
            Device.stuck_record_check(device)
            return False

        task._refresh_round_state_screenshot = screenshot
        return task

    def test_frozen_recognized_wait_stops_and_restores_device_timer(self):
        clock = self.clock()
        task = self.round_task(clock, lambda _: (1, '待'))
        original = task.device.stuck_timer
        with self.assertRaisesRegex(GameStuckError, 'no stage progress'):
            task._run_round_loop()
        self.assertLessEqual(clock.now - 1000., ROUND_PROGRESS_TIMEOUT + 1)
        self.assertIs(task.device.stuck_timer, original)
        self.assertEqual(original.limit, 60)

    def test_long_battle_and_real_stage_progress_allow_next_round(self):
        clock = self.clock()
        task = self.round_task(clock, lambda elapsed: (1, '战') if elapsed < 120 else
                               (1, '待') if elapsed < 230 else (2, '备'))
        task._run_round_loop()
        self.assertGreaterEqual(clock.now - 1000., 230)
        self.assertLess(clock.now - 1000., 240)
        self.assertEqual(task.device.stuck_timer.limit, 60)

    def test_repeated_old_stage_markers_do_not_refresh_progress_forever(self):
        clock = self.clock()
        task = self.round_task(clock, lambda elapsed: (1, '战' if int(elapsed) % 2 else '待'))
        with self.assertRaises(GameStuckError):
            task._run_round_loop()
        self.assertLessEqual(clock.now - 1000., ROUND_PROGRESS_TIMEOUT + 3)

    def test_repeated_device_timer_resets_cannot_hide_frozen_phase(self):
        clock = self.clock()
        task = self.round_task(clock, lambda _: (1, '待'))
        task._handle_passive_stage = lambda _: task.device.stuck_record_clear()
        with self.assertRaisesRegex(GameStuckError, 'no stage progress'):
            task._run_round_loop()
        self.assertLessEqual(clock.now - 1000., ROUND_PROGRESS_TIMEOUT + 1)

    def test_device_stuck_detection_still_runs_and_restores_timer_after_failure(self):
        clock = self.clock()
        task = self.round_task(clock, lambda _: (1, '待'))
        original = task.device.stuck_timer
        original_screenshot = task._refresh_round_state_screenshot

        def stalled_screenshot():
            clock.now += 301
            return original_screenshot()

        task._refresh_round_state_screenshot = stalled_screenshot
        with self.assertRaisesRegex(GameStuckError, 'Wait too long'):
            task._run_round_loop()
        task.device.app_is_running.assert_called_once()
        self.assertIs(task.device.stuck_timer, original)

    def test_activity_guard_rest_is_excluded_from_no_progress_timeout(self):
        clock = self.clock()
        task = self.round_task(clock, lambda _: (1, '待'))
        original_screenshot = task._refresh_round_state_screenshot
        rested = False

        def checkpoint():
            clock.now += 600
            task.device.stuck_record_clear()
            return True

        def screenshot():
            nonlocal rested
            if not rested and clock.now >= 1005:
                rested = True
                self.assertTrue(task.runtime_checkpoint())
            return original_screenshot()

        task._refresh_round_state_screenshot = screenshot
        task._finish_chess_game_after_open_lineup_missing = lambda _: clock.now >= 1610
        with patch('tasks.base_task_parent.BaseTaskParent.runtime_checkpoint', side_effect=checkpoint):
            task._run_round_loop()
        self.assertEqual(task._chess_guard_wait_seconds, 600)
        self.assertGreaterEqual(clock.now, 1610)
        self.assertLessEqual(clock.now, 1613)

    def experience_task(self, frames):
        task = ScriptTask.__new__(ScriptTask)
        task._reset_economy_state()
        task._current_round_no = 1
        state = SimpleNamespace(frame={'mode': '战', 'gold': 40, 'remaining': 20, 'visible': True})
        frames = iter(frames)
        task.screenshot = lambda: setattr(state, 'frame', next(frames, state.frame))
        task._read_chess_mode = lambda: state.frame.get('mode', '战')
        task._read_shop_gold = lambda: state.frame.get('gold', 40)
        task._read_remaining_time = lambda: state.frame.get('remaining', 20)
        task._read_level = lambda: state.frame.get('level', 3)
        task._read_round_number = lambda: state.frame.get('round', 1)
        task._lineup_final_level = Mock(return_value=9)
        task.appear = lambda marker: (state.frame.get('popup', False) if marker is task.I_SELECT_GRIGRI
                                      else state.frame.get('visible', True))
        task._clear_economy_click_history = Mock()
        task.click = Mock(return_value=True)
        return task, state

    def buy_experience(self, task, battle=True):
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            return task._click_economy_button_and_confirm_gold(
                task.I_EXPERIENCE, 4, '购买经验', allow_hidden=battle)

    def test_stage_changes_after_first_click_never_repeat_click(self):
        task, _ = self.experience_task([{'gold': 40}, {'mode': '鬼', 'gold': 40}])
        self.assertEqual(self.buy_experience(task), 'unknown')
        self.assertEqual(self.buy_experience(task), 'no_progress')
        task.click.assert_called_once_with(task.I_EXPERIENCE)

    def test_same_phase_in_next_round_cannot_confirm_or_repeat_experience(self):
        task, _ = self.experience_task([{'gold': 40}, {'round': 2, 'gold': 36}])
        self.assertEqual(self.buy_experience(task), 'unknown')
        self.assertEqual(self.buy_experience(task), 'no_progress')
        task.click.assert_called_once()

    def test_delayed_gold_and_transient_ocr_failure_are_observed_without_reclick(self):
        for delay in [40, None]:
            with self.subTest(delay=delay):
                task, _ = self.experience_task([{'gold': 40}, {'gold': delay}, {'gold': 36}])
                self.assertEqual(self.buy_experience(task), 'success')
                task.click.assert_called_once()
                self.assertIsNone(task._unconfirmed_experience_round)

    def test_unconfirmed_purchase_blocks_current_round_but_new_round_rechecks_budget(self):
        task, state = self.experience_task([{'gold': 40}])
        self.assertEqual(self.buy_experience(task), 'unknown')
        self.assertEqual(self.buy_experience(task), 'no_progress')
        task._current_round_no = 2
        state.frame = {'gold': 36, 'round': 2}
        self.assertEqual(self.buy_experience(task), 'no_progress')
        task.click.assert_called_once()
        state.frame = {'gold': 40, 'round': 2}
        self.assertEqual(self.buy_experience(task), 'unknown')
        self.assertEqual(task.click.call_count, 2)

    def test_current_frame_stage_button_countdown_and_budget_each_gate_click(self):
        for frame in [{'mode': '鬼'}, {'mode': None}, {'visible': False}, {'popup': True},
                      {'remaining': 0}, {'remaining': 1}, {'remaining': 3}, {'remaining': None}, {'gold': 38}, {'gold': None}, {'level': None},
                      {'round': 2}, {'round': None}]:
            with self.subTest(frame=frame):
                task, _ = self.experience_task([frame])
                self.assertEqual(self.buy_experience(task), 'no_progress')
                task.click.assert_not_called()

    def test_experience_uses_full_phase_in_both_modes(self):
        for mode in ('备', '战'):
            for remaining in (15, 5, 4):
                with self.subTest(mode=mode, remaining=remaining):
                    task, _ = self.experience_task([
                        {'mode': mode, 'remaining': remaining, 'gold': 40},
                        {'mode': mode, 'remaining': remaining, 'gold': 36},
                    ])
                    self.assertEqual(self.buy_experience(task, battle=mode == '战'), 'success')
                    task.click.assert_called_once()

    def test_unconfirmed_experience_does_not_advance_atomic_sequence(self):
        task, _ = self.experience_task([{'gold': 40}])
        task._schedule_economy_cycle()
        with patch('tasks.Chess.runtime.economy.time.sleep'):
            self.assertEqual(task._run_economy_atomic_batch(battle_mode=True), 'blocked')
            self.assertEqual(task._run_economy_atomic_batch(battle_mode=True), 'blocked')
        self.assertEqual(task._economy_sequence_index, 0)
        task.click.assert_called_once()

    def test_both_economy_loops_keep_fixed_timeout_and_exclude_activity_rest(self):
        for battle in (False, True):
            clock = SimpleNamespace(now=0., frames=0)
            task = SimpleNamespace(
                _chess_guard_wait_seconds=0., _economy_pending=True,
                _chess_time_available=Mock(return_value=True),
                _is_preparation_mode=Mock(return_value=True),
                _read_chess_mode=Mock(return_value='战'),
                _read_level=Mock(return_value=5), _read_shop_gold=Mock(return_value=100),
                _next_economy_operation=Mock(return_value='experience'),
                _can_execute_economy_operation=Mock(return_value=True),
                purchase_lineup_cards_once=Mock(return_value=[]),
                _handle_battle_sell_stage=Mock(return_value=True),
                _handle_preparation=Mock(return_value=True),
                _schedule_economy_cycle=Mock(),
                _run_economy_atomic_batch=Mock(return_value='pending'),
                appear=Mock(return_value=False), I_SELECT_GRIGRI='grigri',
            )
            def screenshot():
                clock.frames += 1
                if clock.frames == 1:
                    clock.now += 600.
                    task._chess_guard_wait_seconds += 600.
                else:
                    clock.now += 151.
            task.screenshot = screenshot
            run = ScriptTask._run_battle_economy_cycle if battle else ScriptTask._run_preparation_economy_cycle
            with patch('tasks.Chess.script_task.time.monotonic', side_effect=lambda: clock.now):
                with self.assertRaisesRegex(GameStuckError, 'no stage progress'):
                    run(task)
            self.assertEqual(task._run_economy_atomic_batch.call_count, 3)


if __name__ == '__main__':
    unittest.main()
