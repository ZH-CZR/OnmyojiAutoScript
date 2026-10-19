"""Chess idle goals and weekly coin block; temporary runtime DB, simulated games."""
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.idle import DAILY, WEEKLY, SESSION, IDLE, TIMED, IdleExecution, IdleStore, IdleYield, limits_for
from module.exception import GameStuckError, TaskEnd
from tasks.Chess.script_task import ScriptTask
from tasks.GameUi.page import page_main


class ChessIdleTest(unittest.TestCase):
    def setUp(self):
        saving = patch.object(ConfigModel, 'save')
        saving.start()
        self.addCleanup(saving.stop)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Config('template')
        for key in ConfigModel.model_fields:
            scheduler = getattr(getattr(self.config.model, key), 'scheduler', None)
            if scheduler is not None:
                scheduler.enable = False
        self.config.idle_store = IdleStore('chess-test', Path(self.temp.name) / 'idle.sqlite3')
        self.scheduler = self.config.chess.scheduler
        self.scheduler.enable, self.scheduler.execution_mode = True, IDLE
        self.settings = self.config.chess.chess_config
        self.settings.run_count = 2
        self.clock = SimpleNamespace(now=datetime(2026, 10, 19, 12), mono=0.)
        clock = self.clock

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls):
                return clock.now

        dates = patch('module.config.config.datetime', FrozenDateTime)
        dates.start()
        self.addCleanup(dates.stop)
        stored_dates = patch('module.config.idle.datetime', FrozenDateTime)
        stored_dates.start()
        self.addCleanup(stored_dates.stop)
        task_dates = patch('tasks.Chess.runtime.idle.datetime', FrozenDateTime)
        task_dates.start()
        self.addCleanup(task_dates.stop)

    def task(self):
        task = ScriptTask(self.config, device=SimpleNamespace())
        task.select_lineup_strategy = Mock(return_value={'key': 'test', 'display_name': 'test'})
        task._recover_interrupted_chess_game = Mock()
        task.ui_goto_page = Mock(return_value=True)
        task._confirm_chess_idle_lobby = Mock()
        task.idle_return_to_main = Mock()
        task.set_next_run = Mock()
        task._chess_coin_full = Mock(return_value=False)
        execution = IdleExecution(self.config, 'chess', now=lambda: self.clock.now,
                                  monotonic=lambda: self.clock.mono)
        self.config.idle_execution = execution
        return task, execution

    def games(self, task, values, *, after=None):
        values = iter(values)

        def one():
            rank = next(values)
            self.clock.mono += 30
            if task._rank_protection_exit_requested:
                task._rank_protection_exit_succeeded = True
            else:
                task._idle_chess_game_settled = True
            if after is not None:
                after()
            return rank

        task.run_one_game = Mock(side_effect=one)

    def test_daily_and_session_use_count_and_coin_option_is_optional(self):
        for scope in (DAILY, SESSION):
            self.scheduler.idle_goal = scope
            task, execution = self.task()
            self.games(task, [7, None])
            with self.assertRaisesRegex(IdleYield, '目标完成'):
                task.run()
            self.assertEqual(execution.progress['count'], 2)
            self.assertTrue(execution.progress['done'])
            task._chess_coin_full.assert_not_called()
            task.set_next_run.assert_not_called()

    def test_weekly_ignores_run_count_and_coin_checkbox(self):
        self.scheduler.idle_goal = WEEKLY
        self.settings.run_count, self.settings.coin_full_exit = 1, False
        self.assertEqual(limits_for('chess', self.config.chess), (0, 0))
        task, execution = self.task()
        task._chess_coin_full.side_effect = [False, False, False, True]
        self.games(task, [7, 7, 7])
        with self.assertRaisesRegex(IdleYield, '鼬乐币已满'):
            task.run()
        self.assertEqual(execution.progress['count'], 3)
        self.assertTrue(execution.progress['done'])
        self.assertEqual(self.config.idle_store.blocked('chess', self.clock.now)['until'], datetime(2026, 10, 26))

    def test_all_goals_coin_full_can_finish_before_count_with_weekly_block(self):
        for scope in (DAILY, WEEKLY, SESSION):
            with self.subTest(scope=scope):
                self.config.idle_store = IdleStore(str(scope), Path(self.temp.name) / 'idle.sqlite3')
                self.scheduler.idle_goal = scope
                self.settings.coin_full_exit = True
                task, execution = self.task()
                task._chess_coin_full.side_effect = [False, True]
                self.games(task, [7])
                with self.assertRaises(IdleYield):
                    task.run()
                self.assertEqual(execution.progress['count'], 1)
                self.assertTrue(execution.progress['done'])
                self.assertIsNotNone(execution.store.blocked('chess', self.clock.now))

    def test_already_full_starts_no_game_and_blocks_daily_session_and_timed(self):
        self.settings.coin_full_exit = True
        task, execution = self.task()
        task._chess_coin_full.return_value = True
        self.games(task, [])
        with self.assertRaises(IdleYield):
            task.run()
        task.run_one_game.assert_not_called()
        execution.finish()
        store_path = execution.store.path
        self.clock.now += timedelta(days=1)
        self.config.idle_store = IdleStore('chess-test', store_path)
        self.config.idle_store.session(reset=True)
        self.settings.coin_full_exit = False
        for scope in (DAILY, WEEKLY, SESSION):
            self.scheduler.idle_goal = scope
            self.config.update_scheduler()
            self.assertFalse(self.config.pending_task)
            self.assertEqual(self.config.idle_status[0]['status'], '本周鼬乐币已满')
        self.scheduler.execution_mode = TIMED
        self.scheduler.next_run = self.clock.now - timedelta(days=1)
        self.config.update_scheduler()
        self.assertFalse(self.config.pending_task)
        self.assertEqual(self.config.waiting_task[0].next_run, datetime(2026, 10, 26))
        task.run_timed = Mock()
        with self.assertRaises(TaskEnd):
            task.run()
        task.run_timed.assert_not_called()
        self.clock.now = datetime(2026, 10, 26)
        self.config.update_scheduler()
        self.assertEqual(self.config.pending_task[0].command, 'Chess')

    def test_block_isolated_by_config_and_does_not_block_other_task(self):
        self.config.idle_store.block('chess', datetime(2026, 10, 26), '本周鼬乐币已满')
        self.assertIsNone(IdleStore('other', self.config.idle_store.path).blocked('chess', self.clock.now))
        pets = self.config.pets.scheduler
        pets.enable, pets.next_run = True, self.clock.now - timedelta(seconds=1)
        self.config.update_scheduler()
        self.assertEqual([item.command for item in self.config.pending_task], ['Pets'])

    def test_yield_and_resume_keep_protection_debt_and_exits_are_not_counted(self):
        self.settings.rank_protection = True
        task, execution = self.task()
        pets = self.config.pets.scheduler
        pets.enable, pets.next_run = True, self.clock.now + timedelta(minutes=20)
        calls = 0

        def make_due():
            nonlocal calls
            calls += 1
            if calls == 2:
                pets.next_run = self.clock.now + timedelta(minutes=5)

        self.games(task, [1, None], after=make_due)
        with self.assertRaises(IdleYield):
            task.run()
        self.assertEqual(execution.progress['count'], 1)
        self.assertEqual(execution.store.read_task_state('chess')['rank_exits'], 2)
        pets.enable = False
        task, execution = self.task()
        self.games(task, [None, None, 8])
        with self.assertRaisesRegex(IdleYield, '目标完成'):
            task.run()
        self.assertEqual(task.run_one_game.call_count, 3)
        self.assertEqual(execution.progress['count'], 2)
        self.assertEqual(execution.store.read_task_state('chess')['rank_exits'], 0)

    def test_target_completion_does_not_force_three_more_exits(self):
        self.settings.run_count, self.settings.rank_protection = 1, True
        task, execution = self.task()
        self.games(task, [1])
        with self.assertRaises(IdleYield):
            task.run()
        self.assertEqual(task.run_one_game.call_count, 1)
        self.assertEqual(execution.store.read_task_state('chess')['rank_exits'], 3)

    def test_unknown_coins_yield_to_courtyard_keep_count_and_cooldown_after_finish(self):
        self.settings.coin_full_exit = True
        task, execution = self.task()
        task._chess_coin_full.side_effect = [False, None]
        self.games(task, [7])
        with self.assertRaisesRegex(IdleYield, '识别失败'):
            task.run()
        execution.finish()
        self.assertEqual(execution.progress['count'], 1)
        self.assertFalse(execution.progress['done'])
        self.assertEqual(execution.progress['retry'], self.clock.now + timedelta(seconds=60))
        self.assertIsNone(execution.store.blocked('chess', self.clock.now))
        task.idle_return_to_main.assert_called_once()

    def test_unconfirmed_game_cannot_increase_count(self):
        task, execution = self.task()
        task.run_one_game = Mock(return_value=7)
        with self.assertRaises(GameStuckError):
            task.run()
        self.assertEqual(execution.progress['count'], 0)

    def test_natural_only_goal_valid_but_no_limit_and_no_coin_is_invalid(self):
        self.settings.run_count = -1
        self.assertIsNone(limits_for('chess', self.config.chess))
        self.settings.coin_full_exit = True
        self.assertEqual(limits_for('chess', self.config.chess), (0, 0))
        self.settings.coin_full_exit = False
        self.scheduler.idle_goal = WEEKLY
        self.assertEqual(limits_for('chess', self.config.chess), (0, 0))

    def test_fresh_coin_confirmation_rejects_single_or_invalid_full_frame(self):
        task, _ = self.task()
        task.screenshot = Mock()
        task.appear = Mock(return_value=True)
        full = dict(current=600, total=600)
        partial = dict(current=599, total=600)
        for readings, expected in (([full, full], True), ([full, partial], False),
                                   ([None, None, None], None), ([full, None, full], None)):
            task._read_coin = Mock(side_effect=readings)
            with patch('tasks.Chess.runtime.idle.time.sleep'):
                self.assertIs(ScriptTask._chess_coin_full(task, strict=True), expected)

    def test_return_main_requires_fresh_confirmation(self):
        task, _ = self.task()
        task.screenshot = Mock()
        task.ui_page_appear = Mock(return_value=True)
        ScriptTask.idle_return_to_main(task)
        task.ui_page_appear.assert_called_once_with(page_main)
        task.ui_page_appear.return_value = False
        with self.assertRaises(GameStuckError):
            ScriptTask.idle_return_to_main(task)

    def test_timed_count_and_protection_exits_preserve_original_semantics(self):
        self.settings.run_count, self.settings.rank_protection = 1, True
        task, _ = self.task()
        self.config.__dict__.pop('idle_execution')
        self.scheduler.execution_mode = TIMED
        task.screenshot = Mock()
        self.games(task, [1, None, None, None])
        with self.assertRaises(TaskEnd):
            task.run()
        self.assertEqual(task.run_one_game.call_count, 4)
        task.set_next_run.assert_called_once_with(task='Chess', success=True, finish=True)
        task._chess_coin_full.assert_not_called()

    def test_timed_full_coin_also_records_weekly_inhibition(self):
        self.settings.coin_full_exit = True
        task, _ = self.task()
        self.config.__dict__.pop('idle_execution')
        self.scheduler.execution_mode = TIMED
        task.screenshot = Mock()
        task._chess_coin_full.return_value = True
        self.games(task, [])
        with self.assertRaises(TaskEnd):
            task.run()
        task.run_one_game.assert_not_called()
        self.assertEqual(self.config.idle_store.blocked('chess', self.clock.now)['until'], datetime(2026, 10, 26))

    def test_switching_to_timed_mode_resumes_and_clears_outstanding_protection(self):
        self.settings.run_count, self.settings.rank_protection = 1, True
        self.config.idle_store.update_task_state('chess', rank_exits=2)
        task, _ = self.task()
        self.config.__dict__.pop('idle_execution')
        self.scheduler.execution_mode = TIMED
        task.screenshot = Mock()
        self.games(task, [None, None, 8])
        with self.assertRaises(TaskEnd):
            task.run()
        self.assertEqual(task.run_one_game.call_count, 3)
        self.assertEqual(self.config.idle_store.read_task_state('chess')['rank_exits'], 0)

    def test_late_reward_resets_lobby_confirmation_and_unknown_lobby_times_out(self):
        task, _ = self.task()
        frames = iter(('lobby', 'lobby', 'reward', 'lobby', 'lobby', 'lobby', 'lobby', 'lobby'))
        task.screenshot = Mock(side_effect=lambda: setattr(task, 'frame', next(frames)))
        task.ui_reward_appear_click = Mock()
        task.appear = lambda marker, **kwargs: (
            marker is task.I_CHECK_CHESS if task.frame == 'lobby' else marker is task.I_UI_REWARD)
        with patch('tasks.Chess.runtime.idle.time.monotonic', side_effect=lambda: self.clock.mono), \
                patch('tasks.Chess.runtime.idle.time.sleep', side_effect=lambda s: setattr(self.clock, 'mono', self.clock.mono + s)):
            ScriptTask._confirm_chess_idle_lobby(task)
        task.ui_reward_appear_click.assert_called_once()
        self.assertGreaterEqual(self.clock.mono, 2.)
        task.screenshot, task.appear = Mock(), Mock(return_value=False)
        with patch('tasks.Chess.runtime.idle.time.monotonic', side_effect=lambda: self.clock.mono), \
                patch('tasks.Chess.runtime.idle.time.sleep', side_effect=lambda s: setattr(self.clock, 'mono', self.clock.mono + s)):
            with self.assertRaises(GameStuckError):
                ScriptTask._confirm_chess_idle_lobby(task)


if __name__ == '__main__':
    unittest.main()
