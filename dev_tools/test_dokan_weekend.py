"""道馆五六七狭间选项离线验证，不操作游戏或访问群消息。"""
import unittest
from datetime import datetime
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.exception import TaskEnd
from tasks.Dokan.config import Dokan
from tasks.Dokan.script_task import ScriptTask


class DokanWeekendTests(unittest.TestCase):
    def make_task(self, enabled=False, abyss_enabled=False):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(dokan=Dokan(dokan_config={'weekend_abyss_enable': enabled},
                                                  scheduler={'server_update': '20:30:00'}),
                                      abyss_shadows=SimpleNamespace(scheduler=SimpleNamespace(enable=abyss_enabled)))
        task.set_next_run = Mock()
        task.finish_task = Mock(side_effect=TaskEnd)
        task._run_dokan = Mock()
        return task

    def test_default_and_frontend_boolean(self):
        self.assertFalse(Dokan().dokan_config.weekend_abyss_enable)
        field = next(item for item in ConfigModel().script_task('Dokan')['dokan_config']
                     if item['name'] == 'weekend_abyss_enable')
        self.assertEqual(field['type'], 'boolean')
        saved = Dokan(dokan_config={'weekend_abyss_enable': True})
        self.assertTrue(Dokan.model_validate_json(saved.model_dump_json()).dokan_config.weekend_abyss_enable)

    def test_enabled_skips_friday_saturday_sunday_independent_of_abyss_task(self):
        for abyss_enabled in (False, True):
            for day in (23, 24, 25):
                task = self.make_task(True, abyss_enabled)
                with patch('tasks.Dokan.script_task.datetime') as clock:
                    clock.today.return_value = datetime(2026, 10, day, 13)
                    clock.combine.side_effect = datetime.combine
                    with self.assertRaises(TaskEnd):
                        task.check_current_weekday()
                task.set_next_run.assert_called_once_with(task='Dokan', target=datetime(2026, 10, 26, 20, 30), success=None, server=False)

    def test_disabled_keeps_every_day_even_when_abyss_task_enabled(self):
        for day in range(19, 26):
            task = self.make_task(False, True)
            with patch('tasks.Dokan.script_task.datetime') as clock:
                clock.today.return_value = datetime(2026, 10, day, 13)
                task.check_current_weekday(success=True)
            task.set_next_run.assert_not_called()
            task.finish_task.assert_not_called()

    def test_weekday_work_and_thursday_completion(self):
        for day in range(19, 23):
            task = self.make_task(True)
            with patch('tasks.Dokan.script_task.datetime') as clock:
                clock.today.return_value = datetime(2026, 10, day, 13)
                task.check_current_weekday()
                task.set_next_run.assert_not_called()
                if day == 22:
                    clock.combine.side_effect = datetime.combine
                    with self.assertRaises(TaskEnd):
                        task.check_current_weekday(success=True)
                    task.set_next_run.assert_called_once_with(task='Dokan', target=datetime(2026, 10, 26, 20, 30), success=None, server=False)

    def test_monday_target_is_saved_without_success_interval_or_server_override(self):
        task = self.make_task(True)
        config = SimpleNamespace(model=SimpleNamespace(dokan=task.config.dokan),
                                 reload=Mock(), save=Mock(), lock_config=Lock())
        now = datetime(2026, 10, 23, 13)
        def save_target(**kwargs):
            Config.task_delay(config, start_time=now, **kwargs)
        task.set_next_run.side_effect = save_target
        with patch('tasks.Dokan.script_task.datetime') as clock:
            clock.today.return_value = now
            clock.combine.side_effect = datetime.combine
            with self.assertRaises(TaskEnd):
                task.check_current_weekday()
        self.assertEqual(config.model.dokan.scheduler.next_run, datetime(2026, 10, 26, 20, 30))
        config.save.assert_called_once()

    def test_skip_precedes_qq_queries_and_game_flow(self):
        task = self.make_task(True)
        task.config.dokan.welfare_config.welfare_enable = True
        task.config.dokan.qq_message_config.enable = True
        with patch('tasks.Dokan.script_task.datetime') as clock, patch('tasks.Dokan.script_task.QQListener') as listener:
            clock.today.return_value = datetime(2026, 10, 24, 13)
            clock.combine.side_effect = datetime.combine
            with self.assertRaises(TaskEnd):
                task.run()
            listener.assert_not_called()
            task._run_dokan.assert_not_called()


if __name__ == '__main__':
    unittest.main()
