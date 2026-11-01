"""Idle interface regression: temporary database, no device or game input."""
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from types import SimpleNamespace
import unittest
import sqlite3
from unittest.mock import Mock, patch

from pydantic import ValidationError
from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.manual import ManualStore, CooperationStore
from module.config.idle import (ADAPTERS, DAILY, WEEKLY, SESSION, IDLE, TIMED,
                                TIME_FIELDS, IDLE_FIELDS, IdleStore, IdleExecution,
                                IdleYield, reached, select_idle)
from tasks.Component.config_scheduler import Scheduler
from tasks.base_task_parent import BaseTaskParent


NOW = datetime(2026, 10, 19, 12)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls):
        return NOW


class IdleScheduleTest(unittest.TestCase):
    def setUp(self):
        saving = patch.object(ConfigModel, 'save')
        saving.start()
        self.addCleanup(saving.stop)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Config('template')
        self.config.idle_store = IdleStore('test', Path(self.temp.name) / 'idle.sqlite3')
        self.config.manual_store = ManualStore('test', Path(self.temp.name) / 'manual.sqlite3')
        self.config.cooperation_store = CooperationStore('test', Path(self.temp.name) / 'cooperation.sqlite3')
        for key in ConfigModel.model_fields:
            scheduler = getattr(getattr(self.config.model, key), 'scheduler', None)
            if scheduler is not None:
                scheduler.enable = False
        self.clock = patch('module.config.config.datetime', FrozenDateTime)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.adapters = patch.dict(ADAPTERS, {'orochi': lambda model: (3, 100)}, clear=True)
        self.adapters.start()
        self.addCleanup(self.adapters.stop)

    def enable(self, key='orochi', mode=IDLE, when=None):
        s = getattr(self.config.model, key).scheduler
        s.enable, s.execution_mode = True, mode
        s.next_run = when or NOW + timedelta(days=10)
        return s

    def select(self):
        self.config.update_scheduler()
        return [item.command for item in self.config.pending_task]

    def test_all_task_models_have_default_mode_and_visibility_contract(self):
        for key in ConfigModel.model_fields:
            model = getattr(self.config.model, key)
            if getattr(model, 'scheduler', None) is None:
                continue
            with self.subTest(task=key):
                self.assertEqual(model.scheduler.execution_mode, TIMED)
                fields = {item['name']: item for item in self.config.model.script_task(key)['scheduler']}
                self.assertTrue(IDLE_FIELDS <= fields.keys())
                for name in TIME_FIELDS & fields.keys():
                    self.assertEqual(fields[name]['execution_modes'], [TIMED])
                for name in IDLE_FIELDS:
                    self.assertEqual(fields[name]['execution_modes'], [IDLE])

    def test_window_validation_and_save_preserves_old_times(self):
        with self.assertRaises(ValidationError):
            Scheduler.model_validate(dict(idle_start_minutes=5, idle_stop_minutes=5))
        s = self.config.model.orochi.scheduler
        before = s.next_run
        with patch.object(ConfigModel, 'save') as save:
            self.assertFalse(self.config.model.script_set_arg('Orochi', 'scheduler', 'idle_start_minutes', 5))
            self.assertEqual(s.idle_start_minutes, 15)
            self.assertTrue(self.config.model.script_set_arg('Orochi', 'scheduler', 'execution_mode', IDLE))
            self.assertEqual(s.next_run, before)
            save.assert_called_once()

    def test_idle_ignores_old_schedule_but_never_due_normal_tasks(self):
        self.enable()
        self.assertEqual(self.select(), ['Orochi'])
        self.enable('pets', TIMED, NOW - timedelta(seconds=1))
        self.assertEqual(self.select(), ['Pets'])

    def test_start_boundary_and_disabled_normal_task(self):
        self.enable()
        self.enable('pets', TIMED, NOW + timedelta(minutes=15))
        self.assertEqual(self.select(), [])
        self.config.model.pets.scheduler.next_run += timedelta(seconds=1)
        self.assertEqual(self.select(), ['Orochi'])
        self.config.model.pets.scheduler.enable = False
        self.assertEqual(self.select(), ['Orochi'])

    def test_unadapted_and_invalid_limits_never_execute_or_show_old_time(self):
        self.enable('pets')
        self.assertEqual(self.select(), [])
        data = self.config.get_schedule_data()
        self.assertEqual(data['waiting'], [])
        self.assertEqual(data['idle'][0]['status'], '待适配')
        self.assertGreater(self.config.get_next().next_run, NOW)
        ADAPTERS['pets'] = lambda model: (0, 0)
        self.assertEqual(self.select(), [])
        self.assertEqual(self.config.idle_status[0]['status'], '未设置有效目标限制')

    def test_either_limit_completes_goal_and_survives_config_reconstruction(self):
        s = self.enable()
        store = self.config.idle_store
        period = store.period(s.idle_goal, NOW)
        store.add('orochi', s.idle_goal, period, count=3)
        self.assertEqual(self.select(), [])
        self.assertEqual(self.config.idle_status[0]['status'], '目标完成')
        other = IdleStore('test', store.path)
        self.assertTrue(reached(other.read('orochi', s.idle_goal, period), (3, 100)))
        self.assertTrue(reached(dict(done=False, count=0, seconds=100), (3, 100)))
        self.assertFalse(reached(dict(done=False, count=2, seconds=99), (3, 100)))
        self.assertEqual(IdleStore('other', store.path).read('orochi', s.idle_goal, period)['count'], 0)

    def test_daily_weekly_and_session_periods(self):
        store = self.config.idle_store
        self.assertNotEqual(store.period(DAILY, NOW), store.period(DAILY, NOW + timedelta(days=1)))
        self.assertEqual(store.period(WEEKLY, NOW), store.period(WEEKLY, NOW + timedelta(days=6)))
        self.assertNotEqual(store.period(WEEKLY, NOW), store.period(WEEKLY, NOW + timedelta(days=7)))
        token = store.period(SESSION, NOW)
        self.assertEqual(token, IdleStore('test', store.path).period(SESSION, NOW + timedelta(days=30)))
        self.assertNotEqual(token, store.session(reset=True))

    def execution(self):
        self.enable()
        self.mono = 0
        return IdleExecution(self.config, 'orochi', now=lambda: NOW, monotonic=lambda: self.mono)

    def test_checkpoint_cumulates_deltas_excludes_rest_and_exposes_remaining(self):
        execution = self.execution()
        task = SimpleNamespace(config=self.config, idle_return_to_main=Mock())
        self.config.idle_execution = execution
        self.mono = 40
        execution.exclude_wait(25)
        self.assertFalse(execution.checkpoint(task, completed=1))
        self.assertEqual(execution.progress['seconds'], 15)
        self.assertEqual(BaseTaskParent.idle_remaining_limits(task), (2, 85))
        self.mono = 50
        self.assertFalse(execution.checkpoint(task, completed=1))
        self.assertEqual(execution.progress['count'], 2)
        task.idle_return_to_main.assert_not_called()

    def test_yield_after_reward_with_exact_x_preserves_progress_and_no_failure(self):
        execution = self.execution()
        self.enable('pets', TIMED, NOW + timedelta(minutes=5))
        task = SimpleNamespace(idle_return_to_main=Mock())
        with self.assertRaises(IdleYield):
            execution.checkpoint(task, completed=1)
        task.idle_return_to_main.assert_called_once()
        execution.finish()
        self.assertEqual(execution.progress['count'], 1)
        self.assertFalse(execution.progress['done'])
        self.assertIsNone(execution.progress['retry'])
        self.assertEqual(self.config.task_runtime_outcome['status'], 'idle_yield')

    def test_due_task_forces_safe_yield_and_exit_failure_is_not_swallowed(self):
        execution = self.execution()
        self.enable('pets', TIMED, NOW - timedelta(seconds=1))
        task = SimpleNamespace(idle_return_to_main=Mock(side_effect=RuntimeError('cannot exit')))
        with self.assertRaisesRegex(RuntimeError, 'cannot exit'):
            execution.checkpoint(task, completed=1)
        self.assertEqual(execution.progress['count'], 1)
        self.assertFalse(execution.progress['done'])

    def test_goal_completion_and_failed_fragment_cooldown(self):
        execution = self.execution()
        task = SimpleNamespace(idle_return_to_main=Mock())
        with self.assertRaises(IdleYield):
            execution.checkpoint(task, completed=3)
        self.assertTrue(execution.progress['done'])
        self.assertEqual(self.select(), [])

    def test_failed_fragment_keeps_runtime_without_fabricating_count(self):
        execution = self.execution()
        self.mono = 10
        execution.finish()
        self.assertEqual(execution.progress['count'], 0)
        self.assertEqual(execution.progress['seconds'], 10)
        self.assertFalse(execution.progress['done'])
        self.assertEqual(self.select(), [])
        self.assertEqual(self.config.idle_status[0]['status'], '失败冷却')

    def test_old_delays_do_not_mutate_idle_schedule_or_mark_success(self):
        s = self.enable()
        previous = s.next_run
        with patch.object(self.config, 'reload'):
            self.config.task_delay('Orochi', success=True)
            self.config.task_delay('Orochi', success=False)
        self.assertEqual(s.next_run, previous)
        self.assertFalse(self.config.task_call('Orochi'))
        self.assertEqual(s.next_run, previous)
        self.assertEqual(self.select(), ['Orochi'])

    def test_overview_preserves_running_idle_and_new_normal_pending(self):
        self.enable()
        self.enable('pets', TIMED, NOW - timedelta(seconds=1))
        self.config.model.running_task = 'Orochi'
        data = self.config.get_schedule_data()
        self.assertEqual(data['running']['name'], 'Orochi')
        self.assertEqual([item['name'] for item in data['pending']], ['Pets'])
        self.assertEqual(data['idle'][0]['status'], '闲时执行中')

    def test_two_session_goals_share_one_connection_and_warm_reads_do_not_write(self):
        for key in ('six_realms', 'chess'):
            self.enable(key).idle_goal = SESSION
        statements, connections = [], []
        real_connect = sqlite3.connect

        def traced(*args, **kwargs):
            db = real_connect(*args, **kwargs)
            db.set_trace_callback(statements.append)
            connections.append(db)
            return db

        store = self.config.idle_store
        with patch('module.config.idle.sqlite3.connect', side_effect=traced):
            self.config.get_schedule_data()
            self.assertEqual(len(connections), 1)
            self.assertEqual(sum(sql.startswith('CREATE TABLE') for sql in statements), 4)
            self.assertEqual(sum(sql.startswith('INSERT') for sql in statements), 1)
            # Reconstructing Config's store must not repeat schema migration
            # or session INSERTs, and still opens only one connection.
            self.config.idle_store = IdleStore('test', store.path)
            statements.clear()
            connections.clear()
            self.config.get_schedule_data()
            self.assertEqual(len(connections), 1)
            self.assertTrue(statements)
            self.assertTrue(all(sql.startswith('SELECT') for sql in statements), statements)

        other = IdleStore('test', store.path)
        token = other.session()
        other.add('six_realms', SESSION, token, count=2, retry=NOW + timedelta(seconds=60))
        other.block('chess', NOW + timedelta(days=1), 'weekly block')
        data = {item['name']: item for item in self.config.get_schedule_data()['idle']}
        self.assertEqual(data['SixRealms']['count'], 2)
        self.assertEqual(data['Chess']['status'], 'weekly block')
        # Session reset by another store is visible immediately; task blocks
        # survive it and no progress/session tokens are cached in memory.
        other.session(reset=True)
        data = {item['name']: item for item in self.config.get_schedule_data()['idle']}
        self.assertEqual(data['SixRealms']['count'], 0)
        self.assertEqual(data['Chess']['status'], 'weekly block')

    def test_bulk_snapshot_isolates_scope_period_and_configuration(self):
        store = self.config.idle_store
        scopes = {'orochi': DAILY, 'chess': WEEKLY}
        day, week = store.period(DAILY, NOW), store.period(WEEKLY, NOW)
        store.add('orochi', DAILY, day, count=2, seconds=12)
        store.add('orochi', DAILY, store.period(DAILY, NOW - timedelta(days=1)), count=99)
        store.add('chess', WEEKLY, week, done=True, retry=NOW + timedelta(seconds=60))
        states, _ = store.snapshot(scopes, NOW)
        self.assertEqual(states['orochi']['count'], 2)
        self.assertEqual(states['orochi']['seconds'], 12)
        self.assertTrue(states['chess']['done'])
        self.assertEqual(states['chess']['retry'], NOW + timedelta(seconds=60))
        states, blocks = IdleStore('other', store.path).snapshot(scopes, NOW)
        self.assertEqual(states['orochi']['count'], 0)
        self.assertFalse(states['chess']['done'])
        self.assertEqual(blocks, {})
        states, _ = store.snapshot(scopes, NOW + timedelta(days=7))
        self.assertEqual(states['orochi']['count'], 0)
        self.assertFalse(states['chess']['done'])

    def test_old_database_is_migrated_without_erasing_goals_and_recreated_file_works(self):
        store = self.config.idle_store
        with closing(sqlite3.connect(store.path)) as db, db:
            db.execute('CREATE TABLE goals (name TEXT, task TEXT, scope TEXT, period TEXT, '
                       'count INTEGER, seconds REAL, done INTEGER, retry TEXT, '
                       'PRIMARY KEY(name, task, scope, period))')
            db.execute('INSERT INTO goals VALUES (?, ?, ?, ?, 2, 3, 0, NULL)',
                       ('test', 'orochi', DAILY, store.period(DAILY, NOW)))
        states, _ = store.snapshot({'orochi': DAILY}, NOW)
        self.assertEqual(states['orochi']['count'], 2)
        self.assertTrue(store.session())
        store.path.unlink()
        states, _ = IdleStore('test', store.path).snapshot({'orochi': DAILY}, NOW)
        self.assertEqual(states['orochi']['count'], 0)


if __name__ == '__main__':
    unittest.main()
