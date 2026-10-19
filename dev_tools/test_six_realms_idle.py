"""Six Realms idle contract: simulated whole runs and screenshots, no game input."""
from datetime import datetime, timedelta, time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.idle import DAILY, WEEKLY, SESSION, IDLE, TIMED, IdleExecution, IdleStore, IdleYield, limits_for
from module.exception import GameStuckError, TaskEnd
from tasks.GameUi.page import page_main
from tasks.SixRealms.config import SixRealmsType
from tasks.SixRealms.script_task import ScriptTask
from tasks.SixRealms.settlement import RoundResult, SixRealmsSettlement
from tasks.SixRealms.moon_sea.moon_sea import MoonSea as Jiaotu
from tasks.SixRealms_jue.moon_sea.moon_sea import MoonSea as Jue


class SixRealmsIdleTest(unittest.TestCase):
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
        self.config.idle_store = IdleStore('six-test', Path(self.temp.name) / 'idle.sqlite3')
        self.scheduler = self.config.model.six_realms.scheduler
        self.scheduler.enable, self.scheduler.execution_mode = True, IDLE
        self.settings = self.config.model.six_realms.six_realms_gate
        self.settings.limit_count, self.settings.limit_time = 3, time(hour=1)
        self.settings.saved_count = 7
        self.clock = SimpleNamespace(now=datetime(2026, 10, 19, 12), mono=0.)
        clock = self.clock

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls):
                return clock.now

        dates = patch('module.config.config.datetime', FrozenDateTime)
        dates.start()
        self.addCleanup(dates.stop)

    def task(self, kind=SixRealmsType.JIAOTU):
        self.settings.six_realms_type = kind
        task = ScriptTask(self.config, device=SimpleNamespace())
        task.ui_goto_page = Mock(return_value=True)
        task.idle_return_to_main = Mock()
        task.run_switch_soul = Mock()
        task.push_notify = Mock()
        task.next_run_week = Mock()
        task._check_first_priority_task = Mock(side_effect=AssertionError('legacy priority path'))
        execution = IdleExecution(self.config, 'six_realms', now=lambda: self.clock.now,
                                  monotonic=lambda: self.clock.mono)
        self.config.idle_execution = execution
        return task, execution

    def rounds(self, task, results, *, seconds=10, after=None):
        values = iter(results)

        def one():
            result = next(values)
            self.clock.mono += seconds
            task._moon_sea.round_result = result
            if after is not None:
                after()
            return result in (RoundResult.FINISHED, RoundResult.FAILED)

        task._moon_sea.one = Mock(side_effect=one)

    def test_registry_uses_original_limits_and_both_types_share_device(self):
        self.assertEqual(limits_for('six_realms', self.config.model.six_realms), (3, 3600))
        for kind, cls in ((SixRealmsType.JIAOTU, Jiaotu), (SixRealmsType.JUE, Jue)):
            task, _ = self.task(kind)
            self.assertIsInstance(task._moon_sea, cls)
            self.assertIs(task.device, task._moon_sea.device)

    def test_both_types_count_whole_settlements_and_keep_timed_progress(self):
        for kind, scope in ((SixRealmsType.JIAOTU, DAILY), (SixRealmsType.JUE, WEEKLY)):
            self.scheduler.idle_goal = scope
            task, execution = self.task(kind)
            original_time = self.scheduler.next_run
            self.rounds(task, [RoundResult.FINISHED, RoundResult.FAILED, RoundResult.FINISHED])
            with self.assertRaisesRegex(IdleYield, '目标完成'):
                task.run()
            self.assertEqual(execution.progress['count'], 3)
            self.assertTrue(execution.progress['done'])
            self.assertEqual(task._moon_sea.one.call_count, 3)
            self.assertEqual(self.settings.saved_count, 7)
            self.assertEqual(self.scheduler.next_run, original_time)
            task.next_run_week.assert_not_called()
            task._check_first_priority_task.assert_not_called()
            task.idle_return_to_main.assert_called_once()

    def test_yield_and_resume_accumulate_until_original_goal(self):
        task, execution = self.task()
        pets = self.config.model.pets.scheduler
        pets.enable = True
        pets.next_run = self.clock.now + timedelta(minutes=20)
        self.rounds(task, [RoundResult.FINISHED],
                    after=lambda: setattr(pets, 'next_run', self.clock.now + timedelta(minutes=5)))
        with self.assertRaisesRegex(IdleYield, '让位余量'):
            task.run()
        execution.finish()
        self.assertEqual(execution.progress['count'], 1)
        self.assertFalse(execution.progress['done'])
        pets.enable = False
        task, execution = self.task()
        self.rounds(task, [RoundResult.FINISHED, RoundResult.FINISHED])
        with self.assertRaisesRegex(IdleYield, '目标完成'):
            task.run()
        self.assertEqual(task._moon_sea.one.call_count, 2)
        self.assertEqual(execution.progress['count'], 3)

    def test_runtime_goal_waits_for_whole_run_and_zero_count_is_unlimited(self):
        self.settings.limit_count, self.settings.limit_time = 0, time(minute=1)
        task, execution = self.task()
        self.rounds(task, [RoundResult.FINISHED, RoundResult.FINISHED], seconds=40)
        with self.assertRaisesRegex(IdleYield, '目标完成'):
            task.run()
        self.assertEqual(execution.progress['count'], 2)
        self.assertEqual(execution.progress['seconds'], 80)

    def test_all_goal_scopes_block_until_their_reset(self):
        self.settings.limit_count = 1
        for scope in (DAILY, WEEKLY, SESSION):
            self.scheduler.idle_goal = scope
            task, execution = self.task()
            self.rounds(task, [RoundResult.FINISHED])
            with self.assertRaises(IdleYield):
                task.run()
            self.config.update_scheduler()
            self.assertFalse(self.config.pending_task)
            self.assertEqual(self.config.idle_status[0]['status'], '目标完成')
        session = execution.period
        self.config.idle_store.session(reset=True)
        self.config.update_scheduler()
        self.assertNotEqual(session, self.config.idle_store.period(SESSION, self.clock.now))
        self.assertEqual(self.config.pending_task[0].command, 'SixRealms')

    def test_no_tickets_complete_each_goal_without_fabricating_a_run(self):
        for scope in (DAILY, WEEKLY, SESSION):
            self.scheduler.idle_goal = scope
            task, execution = self.task()
            self.rounds(task, [RoundResult.NO_TICKETS])
            with self.assertRaisesRegex(IdleYield, '目标完成'):
                task.run()
            execution.finish()
            self.assertEqual(execution.progress['count'], 0)
            self.assertTrue(execution.progress['done'])
            self.assertIsNone(execution.progress['retry'])
            task.idle_return_to_main.assert_called_once()
            task.next_run_week.assert_not_called()
            self.config.idle_store = IdleStore('six-test', self.config.idle_store.path)
            self.config.update_scheduler()
            self.assertFalse(self.config.pending_task)
            self.assertEqual(self.config.idle_status[0]['status'], '目标完成')
        self.config.idle_store.session(reset=True)
        self.config.update_scheduler()
        self.assertEqual(self.config.pending_task[0].command, 'SixRealms')

    def test_no_limits_does_not_enter_idle_queue(self):
        self.settings.limit_count, self.settings.limit_time = 0, time()
        self.config.update_scheduler()
        self.assertFalse(self.config.pending_task)
        self.assertEqual(self.config.idle_status[0]['status'], '未设置有效目标限制')

    def test_ticket_shortage_keeps_previous_completed_runs(self):
        task, execution = self.task()
        self.rounds(task, [RoundResult.FINISHED, RoundResult.NO_TICKETS])
        with self.assertRaisesRegex(IdleYield, '目标完成'):
            task.run()
        self.assertEqual(execution.progress['count'], 1)
        self.assertTrue(execution.progress['done'])
        self.assertEqual(self.settings.saved_count, 7)

    def test_unconfirmed_exit_does_not_count(self):
        task, execution = self.task()
        self.rounds(task, [RoundResult.NOT_STARTED])
        with self.assertRaises(GameStuckError):
            task.run()
        self.assertEqual(execution.progress['count'], 0)
        self.assertFalse(execution.progress['done'])
        task.idle_return_to_main.assert_not_called()

    def test_ready_before_first_run_yields_to_new_due_task(self):
        task, execution = self.task()
        pets = self.config.model.pets.scheduler
        pets.enable, pets.next_run = True, self.clock.now - timedelta(seconds=1)
        self.rounds(task, [])
        with self.assertRaisesRegex(IdleYield, '普通任务已到期'):
            task.run()
        task._moon_sea.one.assert_not_called()
        self.assertEqual(execution.progress['count'], 0)

    def test_return_main_requires_navigation_and_fresh_confirmation(self):
        task, _ = self.task()
        task.screenshot = Mock()
        task.ui_page_appear = Mock(return_value=True)
        ScriptTask.idle_return_to_main(task)
        task.screenshot.assert_called_once()
        task.ui_page_appear.assert_called_once_with(page_main)
        task.ui_goto_page.return_value = False
        with self.assertRaises(GameStuckError):
            ScriptTask.idle_return_to_main(task)
        task.ui_goto_page.return_value = True
        task.ui_page_appear.return_value = False
        with self.assertRaises(GameStuckError):
            ScriptTask.idle_return_to_main(task)

    def test_timed_path_preserves_old_saved_count_and_week_schedule(self):
        task, _ = self.task()
        self.config.__dict__.pop('idle_execution')
        self.scheduler.execution_mode = TIMED
        self.settings.saved_count = 2
        task._check_first_priority_task = Mock()
        self.rounds(task, [RoundResult.FINISHED])
        with patch.object(self.config, 'reload') as reload, \
                patch.object(self.config, 'save') as save, self.assertRaises(TaskEnd):
            task.run()
        self.assertEqual(reload.call_count, 2)
        self.assertEqual(save.call_count, 2)
        self.assertEqual(task.current_count, 1)
        self.assertEqual(self.settings.saved_count, 0)
        task.next_run_week.assert_called_once_with(1)
        task.idle_return_to_main.assert_not_called()


class SettlementTest(unittest.TestCase):
    def test_jiaotu_ticket_shortage_only_when_ticket_option_enabled(self):
        for idle in (False, True):
            task = Jiaotu.__new__(Jiaotu)
            task.config = SimpleNamespace(
                six_realms=SimpleNamespace(six_realms_gate=SimpleNamespace(number_enable=True)))
            if idle:
                task.config.idle_execution = SimpleNamespace(key='six_realms')
            task.device = SimpleNamespace(image=None)
            task.screenshot, task.push_notify = Mock(), Mock()
            task.appear = lambda marker, **kwargs: marker is task.I_MSTART
            task.O_SIXREALMS_NUMBER = SimpleNamespace(ocr=Mock(return_value=0))
            self.assertFalse(task.one())
            self.assertEqual(task.round_result, RoundResult.NO_TICKETS)
            self.assertEqual(task.push_notify.call_count, 0 if idle else 1)
        task.config.six_realms.six_realms_gate.number_enable = False
        task.appear = lambda marker, **kwargs: any(marker is item for item in (
            task.I_MSTART, task.I_MSHOUZU, task.I_PREPARE_BATTLE, task.I_M_STORE))
        task.O_SIXREALMS_NUMBER.ocr.reset_mock()
        self.assertTrue(task._start())
        task.O_SIXREALMS_NUMBER.ocr.assert_not_called()

    def test_finish_reports_result_only_after_confirmed_ready(self):
        for cls in (Jiaotu, Jue):
            task = cls.__new__(cls)
            task.config = SimpleNamespace(idle_execution=SimpleNamespace(key='six_realms'))
            task.ui_click = Mock(return_value=True)
            task.confirm_idle_ready = Mock()
            self.assertTrue(task.finish_round('close', RoundResult.FAILED))
            self.assertEqual(task.round_result, RoundResult.FAILED)
            task.ui_click.assert_called_once_with('close', stop=task.I_MSTART, timeout=15)
            task.confirm_idle_ready.assert_called_once()
            task.round_result = RoundResult.NOT_STARTED
            task.ui_click.return_value = False
            with self.assertRaises(GameStuckError):
                task.finish_round('close', RoundResult.FINISHED)
            self.assertEqual(task.round_result, RoundResult.NOT_STARTED)

    def test_timed_settlement_keeps_legacy_click_contract(self):
        task = Jiaotu.__new__(Jiaotu)
        task.config = SimpleNamespace()
        task.ui_click, task.confirm_idle_ready = Mock(), Mock()
        self.assertTrue(task.finish_round('close', RoundResult.FINISHED))
        task.ui_click.assert_called_once_with('close', stop=task.I_MSTART)
        task.confirm_idle_ready.assert_not_called()

    def test_late_rewards_reset_stable_confirmation_and_timeout_is_an_error(self):
        clock = SimpleNamespace(mono=0.)
        task = SimpleNamespace(I_UI_REWARD='reward', I_MSTART='ready',
                               screenshot=Mock(), ui_reward_appear_click=Mock())
        frames = iter(('ready', 'ready', 'reward', 'ready', 'ready', 'ready', 'ready', 'ready'))
        task.screenshot.side_effect = lambda: setattr(task, 'frame', next(frames))
        task.appear = lambda marker, **kwargs: task.frame == marker
        with patch('tasks.SixRealms.settlement.monotonic', side_effect=lambda: clock.mono), \
                patch('tasks.SixRealms.settlement.sleep', side_effect=lambda s: setattr(clock, 'mono', clock.mono + s)):
            self.assertTrue(SixRealmsSettlement.confirm_idle_ready(task))
        task.ui_reward_appear_click.assert_called_once()
        self.assertGreaterEqual(clock.mono, 2.)
        task.screenshot = Mock()
        task.appear = lambda *args, **kwargs: False
        with patch('tasks.SixRealms.settlement.monotonic', side_effect=lambda: clock.mono), \
                patch('tasks.SixRealms.settlement.sleep', side_effect=lambda s: setattr(clock, 'mono', clock.mono + s)):
            with self.assertRaises(GameStuckError):
                SixRealmsSettlement.confirm_idle_ready(task)


if __name__ == '__main__':
    unittest.main()
