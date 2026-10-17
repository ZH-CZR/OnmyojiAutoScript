"""验证狩猎战的工作日、周末调度，不连接游戏或写入用户配置。"""
import unittest
from datetime import datetime, time, timedelta
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pydantic import ValidationError

from module.config.config import Config
from module.config.config_model import ConfigModel
from tasks.Hunt.config import Hunt, HuntScheduler
from tasks.Hunt.script_task import ScriptTask
from module.exception import TaskEnd


class HuntScheduleTests(unittest.TestCase):
    def setUp(self):
        self.scheduler = HuntScheduler(kirin_time='19:05:00', netherworld_time='20:10:00')

    def schedule(self, now, **kwargs):
        config = SimpleNamespace(
            model=SimpleNamespace(hunt=Hunt(scheduler=self.scheduler)),
            reload=Mock(), save=Mock(), lock_config=Lock(), state_queue=None,
        )
        with patch('module.config.config.datetime') as clock:
            clock.now.return_value = now
            clock.combine.side_effect = datetime.combine
            Config.task_delay(config, task='Hunt', start_time=now, **kwargs)
        return config.model.hunt.scheduler.next_run

    def test_all_weekdays_select_the_activity_for_the_next_day(self):
        for day in range(12, 19):
            now = datetime(2026, 10, day, 21)
            target_day = now.date() + timedelta(days=1)
            expected = time(19, 5) if target_day.weekday() < 4 else time(20, 10)
            with self.subTest(day=day):
                self.assertEqual(self.schedule(now, success=True), datetime.combine(target_day, expected))

    def test_multi_day_interval_uses_target_days_activity(self):
        self.scheduler.success_interval = timedelta(days=3)
        self.assertEqual(self.schedule(datetime(2026, 10, 14, 21), success=True),
                         datetime(2026, 10, 17, 20, 10))

    def test_retry_and_explicit_target_keep_their_semantics(self):
        now = datetime(2026, 10, 15, 21)
        self.scheduler.failure_interval = timedelta(minutes=10)
        self.assertEqual(self.schedule(now, success=False), now + timedelta(minutes=10))
        target = datetime(2026, 10, 16, 18)
        self.assertEqual(self.schedule(now, target=target), target)
        self.assertEqual(self.schedule(now, success=True, target=target), target)
        self.assertEqual(self.schedule(now, success=True, server=False), now + timedelta(days=1))

    def test_default_nine_is_a_fixed_time_and_delay_date_is_respected(self):
        self.scheduler = HuntScheduler()
        self.assertEqual(self.schedule(datetime(2026, 10, 18, 21), success=True),
                         datetime(2026, 10, 19, 9))
        self.scheduler.delay_date = 2
        self.assertEqual(self.schedule(datetime(2026, 10, 14, 21), success=True),
                         datetime(2026, 10, 16, 17))

    def test_explicit_target_is_exact_even_with_random_float(self):
        self.scheduler.float_time = time(0, 10)
        now = datetime(2026, 10, 16, 16)
        target = datetime(2026, 10, 16, 17)
        self.assertEqual(self.schedule(now, success=True, target=target), target)
        later_target = datetime(2026, 10, 20, 17)
        self.assertEqual(self.schedule(now, success=True, target=later_target), later_target)

    def test_open_hours_select_only_the_days_activity(self):
        task = object.__new__(ScriptTask)
        for day in range(12, 19):
            with self.subTest(day=day), patch('tasks.Hunt.script_task.datetime') as clock:
                clock.now.return_value = datetime(2026, 10, day, 20)
                self.assertTrue(task.check_datetime())
                self.assertEqual(task.kirin_day, day < 16)

    def test_outside_open_hours_reschedules_using_the_correct_activity(self):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(hunt=Hunt(scheduler=self.scheduler))
        task.set_next_run = Mock()
        task.push_notify = Mock()
        cases = [
            (datetime(2026, 10, 15, 5), datetime(2026, 10, 15, 19, 5)),
            (datetime(2026, 10, 15, 23, 1), datetime(2026, 10, 16, 20, 10)),
            (datetime(2026, 10, 16, 16), datetime(2026, 10, 16, 20, 10)),
            (datetime(2026, 10, 18, 23, 1), datetime(2026, 10, 19, 19, 5)),
        ]
        for now, expected in cases:
            with self.subTest(now=now), patch('tasks.Hunt.script_task.datetime') as clock:
                clock.now.return_value = now
                with self.assertRaises(TaskEnd):
                    task.check_datetime()
                task.set_next_run.assert_called_with(task='Hunt', target=expected)

    def test_legacy_time_migration_and_new_values_survive_reload(self):
        legacy = HuntScheduler(server_update='20:30:00')
        self.assertEqual(legacy.kirin_time, time(20, 30))
        self.assertEqual(legacy.netherworld_time, time(20, 30))
        default_legacy = HuntScheduler(server_update='09:00:00')
        self.assertEqual(default_legacy.netherworld_time, time(17))
        explicit = HuntScheduler(server_update='20:30:00', kirin_time='08:00:00',
                                 netherworld_time='18:00:00')
        self.assertEqual(explicit.kirin_time, time(8))
        self.assertEqual(explicit.netherworld_time, time(18))
        invalid_legacy = HuntScheduler(server_update='01:00:00')
        self.assertEqual(invalid_legacy.kirin_time, time(9))
        self.assertEqual(invalid_legacy.netherworld_time, time(17))
        self.assertEqual(HuntScheduler.model_validate_json(self.scheduler.model_dump_json()).netherworld_time, time(20, 10))

    def test_frontend_exposes_two_independent_time_fields(self):
        args = ConfigModel().script_task('Hunt')['scheduler']
        names = {item['name'] for item in args}
        self.assertIn('kirin_time', names)
        self.assertIn('netherworld_time', names)
        self.assertNotIn('server_update', names)
        for name in ('kirin_time', 'netherworld_time'):
            self.assertEqual(next(item['type'] for item in args if item['name'] == name), 'time')

    def test_times_outside_activity_hours_are_rejected(self):
        for values in ({'kirin_time': '05:59:59'}, {'netherworld_time': '16:59:59'},
                       {'kirin_time': '23:00:01'}, {'netherworld_time': '23:00:01'}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                HuntScheduler(**values)


if __name__ == '__main__':
    unittest.main()
