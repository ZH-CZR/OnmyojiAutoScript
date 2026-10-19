"""狭间暗域开放日调度离线回归。"""
import unittest
from datetime import datetime, time, timedelta
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.exception import TaskEnd
from tasks.AbyssShadows.config import AbyssShadows, AbyssShadowsScheduler
from tasks.AbyssShadows.script_task import ScriptTask
from dev_tools import test_task_schedule as schedule_tests


class AbyssShadowsScheduleTests(unittest.TestCase):
    def schedule(self, now, settings=None, **kwargs):
        scheduler = AbyssShadowsScheduler(**(settings or {}))
        config = SimpleNamespace(model=SimpleNamespace(abyss_shadows=AbyssShadows(scheduler=scheduler)),
                                 reload=Mock(), save=Mock(), lock_config=Lock())
        with patch('module.config.config.datetime') as clock:
            clock.now.return_value = now
            Config.task_delay(config, 'AbyssShadows', start_time=now, **kwargs)
        config.save.assert_called_once()
        return scheduler.next_run

    def test_all_day_boundaries_and_weekdays(self):
        scheduler = AbyssShadowsScheduler()
        for day in range(19, 26):
            for hour, minute, second in ((0, 0, 0), (23, 59, 59)):
                self.assertEqual(scheduler.is_open(datetime(2026, 10, day, hour, minute, second)), day >= 23)

    def test_daily_success_and_sunday_to_friday(self):
        for day, target_day in ((23, 24), (24, 25), (25, 30)):
            for execution in ('09:00:00', '21:30:00'):
                expected = datetime.combine(datetime(2026, 10, target_day), time.fromisoformat(execution))
                self.assertEqual(self.schedule(datetime(2026, 10, day, 22),
                                 settings={'server_update': execution}, success=True), expected)

    def test_failure_keeps_retry_interval_and_skips_closed_days(self):
        settings = {'server_update': '20:00:00', 'failure_interval': timedelta(minutes=10)}
        self.assertEqual(self.schedule(datetime(2026, 10, 23, 13), settings, success=False),
                         datetime(2026, 10, 23, 13, 10))
        self.assertEqual(self.schedule(datetime(2026, 10, 25, 23, 55), settings, success=False),
                         datetime(2026, 10, 30, 20))

    def test_explicit_target_preserved_and_no_random(self):
        now = datetime(2026, 10, 23, 13)
        with patch('tasks.AbyssShadows.config.random.randint') as draw:
            self.assertEqual(self.schedule(now, {'float_time': '01:00:00'}, success=True,
                             target=datetime(2026, 10, 23, 16)), datetime(2026, 10, 23, 16))
            self.assertEqual(self.schedule(now, success=True, target=datetime(2026, 10, 26, 16)),
                             datetime(2026, 10, 30, 9))
            draw.assert_not_called()

    def test_random_delay_once_and_capped_before_midnight(self):
        with patch('tasks.AbyssShadows.config.random.randint', side_effect=lambda a, b: b) as draw:
            self.assertEqual(self.schedule(datetime(2026, 10, 25, 13),
                             {'server_update': '23:59:00', 'float_time': '01:00:00'}, success=True),
                             datetime(2026, 10, 30, 23, 59, 59))
            draw.assert_called_once_with(0, 59)
        with patch('tasks.AbyssShadows.config.random.randint', return_value=120):
            self.assertEqual(self.schedule(datetime(2026, 10, 23, 13),
                             {'float_time': '00:05:00'}, success=True), datetime(2026, 10, 24, 9, 2))

    def test_interval_without_fixed_time_still_respects_open_days(self):
        self.assertEqual(self.schedule(datetime(2026, 10, 23, 13), server=False, success=True),
                         datetime(2026, 10, 24, 13))
        self.assertEqual(self.schedule(datetime(2026, 10, 25, 13), server=False, success=True),
                         datetime(2026, 10, 30, 9))

    def test_closed_day_entry_does_not_operate_game(self):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(abyss_shadows=AbyssShadows())
        task.set_next_run = Mock()
        task.get_attack_sequence = Mock(side_effect=AssertionError('must not enter game'))
        for day in range(19, 23):
            with patch('tasks.AbyssShadows.script_task.datetime') as clock:
                clock.now.return_value = datetime(2026, 10, day, 12)
                with self.assertRaises(TaskEnd):
                    task.run()
                task.set_next_run.assert_called_with(task='AbyssShadows', target=datetime(2026, 10, 23, 9))

    def test_legacy_settings_and_frontend_fields(self):
        settings = {'server_update': '20:30:00', 'float_time': '00:05:00'}
        task = AbyssShadows(scheduler=settings)
        reloaded = AbyssShadows.model_validate_json(task.model_dump_json())
        self.assertEqual(reloaded.scheduler.server_update, time(20, 30))
        self.assertEqual(reloaded.scheduler.float_time, time(0, 5))
        fields = {item['name'] for item in ConfigModel().script_task('AbyssShadows')['scheduler']}
        self.assertTrue({'server_update', 'float_time', 'failure_interval'} <= fields)

    def test_overview_skips_closed_days_without_saving_or_redrawing(self):
        config = schedule_tests.TaskScheduleTest().make_config()
        scheduler = config.model.abyss_shadows.scheduler
        scheduler.enable = True
        scheduler.next_run = datetime(2023, 1, 1)
        class ClockMeta(type):
            def __instancecheck__(cls, value):
                return isinstance(value, datetime)
        class Clock(datetime, metaclass=ClockMeta):
            @classmethod
            def now(cls):
                return cls(2026, 10, 19, 12)
        with patch('module.config.config.datetime', Clock), patch.object(config, 'save') as save, \
                patch('tasks.AbyssShadows.config.random.randint') as draw:
            shown = config.get_schedule_data()
            self.assertEqual(shown['running'], {})
            self.assertEqual(shown['waiting'], [{'name': 'AbyssShadows', 'next_run': '2026-10-23 09:00:00'}])
            save.assert_not_called()
            draw.assert_not_called()


if __name__ == '__main__':
    unittest.main()
