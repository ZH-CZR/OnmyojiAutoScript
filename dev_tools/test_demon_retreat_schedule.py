"""首领退治周六开放窗口、迁移与调度回归，不连接游戏。"""
import unittest
from datetime import datetime, time
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError
from module.config.config import Config
from module.config.config_model import ConfigModel
from module.exception import TaskEnd
from tasks.DemonRetreat.config import DemonRetreat, DemonRetreatScheduler
from tasks.DemonRetreat.script_task import ScriptTask
from dev_tools import test_task_schedule as schedule_tests


class DemonRetreatScheduleTests(unittest.TestCase):
    def test_open_boundaries(self):
        for day in range(19, 26):
            for hour in (10, 11, 22, 23):
                now = datetime(2026, 10, day, hour)
                self.assertEqual(DemonRetreatScheduler.is_open(now), day == 24 and 11 <= hour < 23)
        self.assertTrue(DemonRetreatScheduler.is_open(datetime(2026, 10, 24, 22, 59, 59)))

    def test_invalid_time_rejected(self):
        for value in ('10:59:59', '23:00:00', '23:59:59'):
            with self.assertRaises(ValidationError):
                DemonRetreatScheduler(saturday_time=value)

    def test_legacy_migration(self):
        for old, expected in (('10:00:00', time(11)), ('20:30:00', time(20, 30)), ('23:00:00', time(11))):
            task = DemonRetreat(demon_retreat_time={'custom_run_time': old}, scheduler={'server_update': '19:00:00'})
            self.assertEqual(task.scheduler.saturday_time, expected)
        self.assertEqual(DemonRetreat(scheduler={'server_update': '19:00:00'}).scheduler.saturday_time, time(19))
        task = DemonRetreat(demon_retreat_time={'custom_run_time': '20:00:00'}, scheduler={'saturday_time': '12:00:00'})
        self.assertEqual(DemonRetreat.model_validate_json(task.model_dump_json()).scheduler.saturday_time, time(12))

    def test_frontend_has_one_execution_time(self):
        args = ConfigModel().script_task('DemonRetreat')
        self.assertNotIn('demon_retreat_time', args)
        names = {item['name'] for item in args['scheduler']}
        self.assertIn('saturday_time', names)
        self.assertIn('failure_interval', names)
        self.assertFalse(names & {'server_update', 'success_interval', 'delay_date', 'float_time'})

    def schedule(self, now, **kwargs):
        config = SimpleNamespace(model=SimpleNamespace(demon_retreat=DemonRetreat(
            scheduler={'saturday_time': '12:00:00', 'server_update': '18:00:00', 'float_time': '01:00:00'})),
            reload=Mock(), save=Mock(), lock_config=Lock())
        with patch('module.config.config.datetime') as clock:
            clock.now.return_value = now
            Config.task_delay(config, 'DemonRetreat', start_time=now, **kwargs)
        config.save.assert_called_once()
        return config.model.demon_retreat.scheduler.next_run

    def test_success_next_saturday(self):
        self.assertEqual(self.schedule(datetime(2026, 10, 24, 13), success=True), datetime(2026, 10, 31, 12))

    def test_retry_within_window_or_next_week(self):
        self.assertEqual(self.schedule(datetime(2026, 10, 24, 13), success=False), datetime(2026, 10, 24, 13, 10))
        self.assertEqual(self.schedule(datetime(2026, 10, 24, 22, 55), success=False), datetime(2026, 10, 31, 12))
        self.assertEqual(self.schedule(datetime(2026, 10, 19, 13), success=False), datetime(2026, 10, 24, 12))

    def test_explicit_target_preserved_inside_window(self):
        now = datetime(2026, 10, 24, 13)
        target = datetime(2026, 10, 24, 15)
        self.assertEqual(self.schedule(now, success=True, target=target), target)
        self.assertEqual(self.schedule(now, success=True, target=datetime(2026, 10, 25, 15)), datetime(2026, 10, 31, 12))

    def test_outside_window_never_enters_game(self):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(demon_retreat=DemonRetreat())
        task.set_next_run = Mock()
        task.run_switch_soul = Mock(side_effect=AssertionError('must not operate game'))
        for now, expected in ((datetime(2026, 10, 24, 10), datetime(2026, 10, 24, 11)),
                              (datetime(2026, 10, 24, 23), datetime(2026, 10, 31, 11)),
                              (datetime(2026, 10, 25, 12), datetime(2026, 10, 31, 11))):
            with patch('tasks.DemonRetreat.script_task.datetime') as clock:
                clock.now.return_value = now
                with self.assertRaises(TaskEnd):
                    task.run()
                task.set_next_run.assert_called_with(task='DemonRetreat', target=expected)

    def test_overview_normalizes_old_due_time_without_saving(self):
        config = schedule_tests.TaskScheduleTest().make_config()
        config.model.demon_retreat.scheduler.enable = True
        config.model.demon_retreat.scheduler.next_run = datetime(2023, 1, 1)
        class ClockMeta(type):
            def __instancecheck__(cls, value):
                return isinstance(value, datetime)

        class Clock(datetime, metaclass=ClockMeta):
            @classmethod
            def now(cls):
                return cls(2026, 10, 19, 12)
        config.model.demon_retreat.scheduler.next_run = Clock(2023, 1, 1)
        with patch('module.config.config.datetime', Clock), patch.object(config, 'save') as save:
            shown = config.get_schedule_data()
            self.assertEqual(shown['running'], {})
            self.assertEqual(shown['waiting'], [{'name': 'DemonRetreat', 'next_run': '2026-10-24 11:00:00'}])
            save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
