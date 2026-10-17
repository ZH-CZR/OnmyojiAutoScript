"""验证启用任务进入调度与总览，不连接设备或写入用户配置。"""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from module.base.filter import Filter
from module.config.config import Config
from module.config.config_manual import ConfigManual
from module.config.config_model import ConfigModel
from module.config.scheduler import TaskScheduler
from tasks.Script.config_optimization import ScheduleRule


AFFECTED_TASKS = (
    'activity_common', 'activity_common_2', 'activity_simple', 'nian_true',
    'netherworld', 'auto_cake', 'main_story',
)


class TaskScheduleTest(unittest.TestCase):
    def make_config(self):
        config = Config('template')
        for field in ConfigModel.model_fields:
            scheduler = getattr(getattr(config.model, field), 'scheduler', None)
            if scheduler is not None:
                scheduler.enable = False
        return config

    def enable(self, config, key, when):
        scheduler = getattr(config.model, key).scheduler
        scheduler.enable = True
        scheduler.next_run = when

    def overview_names(self, config):
        data = config.get_schedule_data()
        names = [item['name'] for item in data['pending'] + data['waiting']]
        if data['running']:
            names.append(data['running']['name'])
        return names

    def test_each_reported_task_can_be_selected_and_shown(self):
        for key in AFFECTED_TASKS:
            with self.subTest(task=key):
                config = self.make_config()
                self.enable(config, key, datetime.now() - timedelta(days=1))
                self.assertEqual(config.get_next().command, ConfigModel.type(key))
                self.assertEqual(self.overview_names(config), [ConfigModel.type(key)])

    def test_all_reported_tasks_survive_together(self):
        config = self.make_config()
        for key in AFFECTED_TASKS:
            self.enable(config, key, datetime.now() - timedelta(days=1))
        config.get_next()
        self.assertCountEqual(self.overview_names(config),
                              [ConfigModel.type(key) for key in AFFECTED_TASKS])

    def test_default_order_covers_every_schedulable_model(self):
        declared = [name.strip() for name in ConfigManual.SCHEDULER_PRIORITY.split('>')]
        config = self.make_config()
        for key in ConfigModel.model_fields:
            if hasattr(getattr(config.model, key), 'scheduler'):
                with self.subTest(task=key):
                    self.assertEqual(declared.count(ConfigModel.type(key)), 1)

    def test_filter_preserves_unlisted_tasks_after_known_tasks(self):
        order = Filter(regex=r'(.*)', attr=['command'])
        order.load('Restart > Orochi')
        now = datetime.now()
        first = SimpleNamespace(command='FutureTask', next_run=now)
        second = SimpleNamespace(command='AnotherTask', next_run=now + timedelta(seconds=1))
        restart = SimpleNamespace(command='Restart', next_run=now)
        orochi = SimpleNamespace(command='Orochi', next_run=now)
        pending = [second, orochi, first, restart]
        with patch.object(TaskScheduler, 'filter', order):
            result = TaskScheduler.schedule(ScheduleRule.FILTER, pending)
        self.assertEqual(result, [restart, orochi, first, second])
        self.assertEqual(pending, [second, orochi, first, restart])

    def test_future_and_disabled_tasks_keep_their_semantics(self):
        config = self.make_config()
        target = datetime.now().replace(microsecond=0) + timedelta(days=1)
        self.enable(config, 'activity_common_2', target)
        config.get_next()
        self.assertEqual(config.pending_task, [])
        self.assertEqual(config.get_schedule_data()['waiting'],
                         [{'name': 'ActivityCommon2', 'next_run': str(target)}])
        config.model.activity_common_2.scheduler.enable = False
        config.update_scheduler()
        self.assertEqual(config.pending_task, [])
        self.assertEqual(config.waiting_task, [])

    def test_all_rules_keep_enabled_tasks_and_running_task_first(self):
        for rule in ScheduleRule:
            with self.subTest(rule=rule):
                config = self.make_config()
                config.model.script.optimization.schedule_rule = rule
                for key in AFFECTED_TASKS:
                    self.enable(config, key, datetime.now() - timedelta(days=1))
                # 绕过 ConfigModel 顶层赋值自动保存，仅模拟运行状态。
                config.model.__dict__['running_task'] = 'MainStory'
                self.assertEqual(config.get_next().command, 'MainStory')
                self.assertCountEqual(self.overview_names(config),
                                      [ConfigModel.type(key) for key in AFFECTED_TASKS])

    def test_disabling_last_due_task_clears_overview_without_selecting(self):
        for key in AFFECTED_TASKS:
            with self.subTest(task=key):
                config = self.make_config()
                self.enable(config, key, datetime.now() - timedelta(days=1))
                selected = config.get_next()
                getattr(config.model, key).scheduler.enable = False
                self.assertEqual(config.get_schedule_data(),
                                 {'running': {}, 'pending': [], 'waiting': []})
                # 总览刷新不干预执行器持有的任务对象。
                self.assertIs(config.task, selected)

    def test_disabling_selected_task_keeps_remaining_due_and_future_tasks(self):
        config = self.make_config()
        past = datetime.now() - timedelta(days=1)
        self.enable(config, 'activity_common', past)
        self.enable(config, 'activity_common_2', past)
        self.enable(config, 'main_story', datetime.now() + timedelta(days=1))
        self.assertEqual(config.get_next().command, 'ActivityCommon')
        config.model.activity_common.scheduler.enable = False
        data = config.get_schedule_data()
        self.assertEqual(data['running']['name'], 'ActivityCommon2')
        self.assertEqual(data['pending'], [])
        self.assertEqual([item['name'] for item in data['waiting']], ['MainStory'])

    def test_postponing_selected_task_removes_stale_running_entry(self):
        config = self.make_config()
        self.enable(config, 'activity_common', datetime.now() - timedelta(days=1))
        config.get_next()
        config.model.activity_common.scheduler.next_run = datetime.now() + timedelta(days=1)
        data = config.get_schedule_data()
        self.assertEqual(data['running'], {})
        self.assertEqual(data['pending'], [])
        self.assertEqual([item['name'] for item in data['waiting']], ['ActivityCommon'])


if __name__ == '__main__':
    unittest.main()
