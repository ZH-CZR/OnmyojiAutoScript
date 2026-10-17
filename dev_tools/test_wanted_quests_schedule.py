"""Exercise WantedQuests scheduling through the real task/config interfaces offline."""
import unittest
from datetime import datetime, time, timedelta
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from tasks.WantedQuests.config import WantedQuests, WantedQuestsScheduler
from tasks.WantedQuests.script_task import ScriptTask


class WantedQuestsScheduleTest(unittest.TestCase):
    def test_interval_fields_are_hidden_only_for_wanted_quests(self):
        model = ConfigModel()
        for task, hidden in (('WantedQuests', True), ('Restart', False)):
            names = {field['name'] for field in model.script_task(task)['scheduler']}
            for name in ('success_interval', 'failure_interval', 'delay_date', 'server_update'):
                self.assertEqual(name not in names, hidden)
            if hidden:
                self.assertIn('server_update_am', names)
                self.assertIn('float_time', names)
        scheduler = WantedQuestsScheduler(success_interval='03 00:00:00',
                                          failure_interval='02 00:00:00')
        restored = WantedQuestsScheduler.model_validate_json(scheduler.model_dump_json())
        self.assertEqual(restored.success_interval, timedelta(days=3))
        self.assertEqual(restored.failure_interval, timedelta(days=2))

    def test_success_and_failure_ignore_legacy_intervals_without_target(self):
        for success in (True, False):
            for now, expected in ((datetime(2026, 10, 17, 10), datetime(2026, 10, 17, 20)),
                                  (datetime(2026, 10, 17, 21), datetime(2026, 10, 18, 7))):
                with self.subTest(success=success, now=now):
                    scheduler = WantedQuestsScheduler(
                        server_update='07:00:00', server_update_pm='20:00:00',
                        success_interval=timedelta(minutes=1), failure_interval=timedelta(days=5))
                    config = SimpleNamespace(
                        model=SimpleNamespace(wanted_quests=WantedQuests(scheduler=scheduler)),
                        reload=Mock(), save=Mock(), lock_config=Lock())
                    with patch('module.config.config.datetime') as clock:
                        clock.now.return_value = now
                        Config.task_delay(config, task='WantedQuests', success=success)
                    self.assertEqual(scheduler.next_run, expected)

    def schedule(self, now, am='09:00:00', pm='18:00:00', **settings):
        scheduler = WantedQuestsScheduler(server_update=am, server_update_pm=pm, **settings)
        config = SimpleNamespace(
            model=SimpleNamespace(wanted_quests=WantedQuests(scheduler=scheduler)),
            wanted_quests=SimpleNamespace(scheduler=scheduler),
            reload=Mock(), save=Mock(), lock_config=Lock(),
        )
        config.task_delay = lambda *args, **kwargs: Config.task_delay(config, *args, **kwargs)
        task = object.__new__(ScriptTask)
        task.config = config
        task.start_time = now - timedelta(minutes=30)
        with patch('tasks.WantedQuests.script_task.datetime') as clock:
            clock.now.return_value = now
            clock.combine.side_effect = datetime.combine
            ScriptTask.next_run(task)
        config.save.assert_called_once_with()
        return scheduler.next_run

    def test_refresh_boundaries_and_midnight(self):
        cases = [
            ('2026-10-17 00:00:00', '2026-10-17 09:00:00'),
            ('2026-10-17 05:00:00', '2026-10-17 09:00:00'),
            ('2026-10-17 05:59:59', '2026-10-17 09:00:00'),
            ('2026-10-17 06:00:00', '2026-10-17 18:00:00'),
            ('2026-10-17 09:30:00', '2026-10-17 18:00:00'),
            ('2026-10-17 17:59:59', '2026-10-17 18:00:00'),
            ('2026-10-17 18:00:00', '2026-10-18 09:00:00'),
            ('2026-10-17 23:59:59', '2026-10-18 09:00:00'),
            ('2026-12-31 23:59:59', '2027-01-01 09:00:00'),
        ]
        for now, expected in cases:
            with self.subTest(now=now):
                self.assertEqual(self.schedule(datetime.fromisoformat(now)),
                                 datetime.fromisoformat(expected))

    def test_custom_morning_time_does_not_overwrite_afternoon(self):
        self.assertEqual(self.schedule(datetime(2026, 10, 17, 10),
                                       am='06:30:00', pm='19:15:00'),
                         datetime(2026, 10, 17, 19, 15))

    def test_delayed_evening_time_does_not_change_refresh_boundary(self):
        self.assertEqual(self.schedule(datetime(2026, 10, 17, 18, 30),
                                       am='07:15:00', pm='20:00:00'),
                         datetime(2026, 10, 18, 7, 15))

    def test_exact_refresh_times_can_be_configured(self):
        for now, expected in ((datetime(2026, 10, 17, 5, 59), datetime(2026, 10, 17, 6)),
                              (datetime(2026, 10, 17, 6), datetime(2026, 10, 17, 18)),
                              (datetime(2026, 10, 17, 18), datetime(2026, 10, 18, 6))):
            with self.subTest(now=now):
                self.assertEqual(self.schedule(now, am='06:00:00'), expected)

    def test_intervals_and_common_server_settings_do_not_override_target(self):
        with patch('tasks.WantedQuests.config.random.randint', return_value=300) as draw:
            actual = self.schedule(datetime(2026, 10, 17, 10),
                                       am='07:00:00', pm='20:00:00',
                                       success_interval=timedelta(minutes=1),
                                       delay_date=3, float_time=time(2))
        self.assertEqual(actual, datetime(2026, 10, 17, 20, 5))
        draw.assert_called_once_with(0, 7200)

    def test_random_delay_applies_once_to_both_rounds(self):
        for now, expected in ((datetime(2026, 10, 17, 10), datetime(2026, 10, 17, 18, 10)),
                              (datetime(2026, 10, 17, 21), datetime(2026, 10, 18, 9, 10))):
            with self.subTest(now=now), patch('tasks.WantedQuests.config.random.randint', return_value=600) as draw:
                self.assertEqual(self.schedule(now, float_time=time(0, 10)), expected)
                draw.assert_called_once_with(0, 600)
        with patch('tasks.WantedQuests.config.random.randint') as draw:
            self.schedule(datetime(2026, 10, 17, 10))
            draw.assert_not_called()

    def test_morning_migration_preserves_new_setting_and_roundtrip(self):
        old = WantedQuestsScheduler(server_update='07:30:00')
        self.assertEqual(old.server_update_am, time(7, 30))
        new = WantedQuestsScheduler(server_update='07:30:00', server_update_am='08:15:00')
        restored = WantedQuestsScheduler.model_validate_json(new.model_dump_json())
        self.assertEqual(restored.server_update_am, time(8, 15))

    def test_automatic_fallback_also_adds_random_delay_once(self):
        scheduler = WantedQuestsScheduler(float_time='00:10:00')
        config = SimpleNamespace(
            model=SimpleNamespace(wanted_quests=WantedQuests(scheduler=scheduler)),
            reload=Mock(), save=Mock(), lock_config=Lock())
        with patch('module.config.config.datetime') as clock, \
                patch('tasks.WantedQuests.config.random.randint', return_value=600) as draw:
            clock.now.return_value = datetime(2026, 10, 17, 10)
            Config.task_delay(config, task='WantedQuests', success=False)
        self.assertEqual(scheduler.next_run, datetime(2026, 10, 17, 18, 10))
        draw.assert_called_once_with(0, 600)

    def test_common_rule_is_blocked_even_when_caller_leaves_server_enabled(self):
        scheduler = WantedQuestsScheduler(server_update='07:00:00', float_time='02:00:00')
        config = SimpleNamespace(
            model=SimpleNamespace(wanted_quests=WantedQuests(scheduler=scheduler)),
            reload=Mock(), save=Mock(), lock_config=Lock(),
        )
        now = datetime(2026, 10, 17, 10)
        target = datetime(2026, 10, 17, 18)
        with patch('module.config.config.parse_tomorrow_server') as force_next_day:
            Config.task_delay(config, task='WantedQuests', start_time=now,
                              success=True, target=target)
        force_next_day.assert_not_called()
        self.assertEqual(scheduler.next_run, target)
        config.save.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
