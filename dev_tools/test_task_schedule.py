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
from module.config.startup_order import StartupTaskOrder
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

    def test_startup_shuffle_is_opt_in_and_overview_never_draws(self):
        config = self.make_config()
        self.assertFalse(config.script.optimization.startup_task_shuffle_enable)
        config.script.optimization.startup_task_shuffle_enable = True
        for key in AFFECTED_TASKS:
            self.enable(config, key, datetime.now() - timedelta(days=1))
        with patch('module.config.startup_order.random.random') as draw:
            config.get_schedule_data()
            config.get_next()
        draw.assert_not_called()

    def test_enabled_shuffle_enforces_priority_for_all_rules_and_draw_outcomes(self):
        for rule in ScheduleRule:
            for chance in (.1, .9):
                with self.subTest(rule=rule, chance=chance):
                    config = self.make_config()
                    config.script.optimization.schedule_rule = rule
                    config.script.optimization.startup_task_shuffle_enable = True
                    past = datetime.now() - timedelta(days=1)
                    priorities = {'activity_common': 15, 'activity_common_2': 1,
                                  'main_story': 1, 'orochi': 5, 'restart': 15}
                    for name, priority in priorities.items():
                        self.enable(config, name, past)
                        getattr(config.model, name).scheduler.priority = priority
                    # Covers server overview before receiving a startup snapshot.
                    config.update_scheduler()
                    baseline = [task.command for task in config.pending_task]
                    self.assertEqual(baseline[0], 'Restart')
                    self.assertEqual([task.priority for task in config.pending_task[1:]], [1, 1, 5, 15])
                    order = StartupTaskOrder()
                    config.startup_task_order = order
                    with patch('module.config.startup_order.random.random', return_value=chance), \
                            patch('module.config.startup_order.random.shuffle', side_effect=lambda items: items.reverse()):
                        order.initialize(config.pending_task, True)
                    for _ in range(2):
                        config.get_schedule_data()
                        self.assertEqual(config.get_next().command, 'Restart')
                        self.assertEqual([task.priority for task in config.pending_task[1:]], [1, 1, 5, 15])
                        self.assertCountEqual([task.command for task in config.pending_task], baseline)
                    if chance < .2:
                        self.assertEqual([task.command for task in config.pending_task[1:3]], baseline[1:3][::-1])
                    else:
                        self.assertEqual([task.command for task in config.pending_task], baseline)
                    config.model.restart.scheduler.enable = False
                    config.model.__dict__['running_task'] = 'ActivityCommon'
                    self.assertEqual(config.get_next().command, 'ActivityCommon')
                    self.assertEqual([task.priority for task in config.pending_task[1:]], [1, 1, 5])

    def test_enabled_shuffle_puts_new_high_priority_task_before_startup_cohort(self):
        config = self.make_config()
        config.script.optimization.startup_task_shuffle_enable = True
        past = datetime.now() - timedelta(days=1)
        for key in ('activity_common', 'activity_common_2'):
            self.enable(config, key, past)
            getattr(config.model, key).scheduler.priority = 10
        config.update_scheduler()
        order = StartupTaskOrder()
        config.startup_task_order = order
        with patch('module.config.startup_order.random.random', return_value=0), \
                patch('module.config.startup_order.random.shuffle', side_effect=lambda items: items.reverse()):
            order.initialize(config.pending_task, True)
        self.enable(config, 'main_story', past)
        config.model.main_story.scheduler.priority = 1
        self.assertEqual(config.get_next().command, 'MainStory')
        self.assertEqual([task.priority for task in config.pending_task], [1, 10, 10])

    def test_disabled_shuffle_retains_original_filter_and_fifo_rules(self):
        for rule in (ScheduleRule.FILTER, ScheduleRule.FIFO):
            config = self.make_config()
            config.script.optimization.schedule_rule = rule
            past = datetime.now() - timedelta(days=1)
            self.enable(config, 'activity_common', past)
            self.enable(config, 'main_story', past + timedelta(seconds=1))
            config.model.activity_common.scheduler.priority = 15
            config.model.main_story.scheduler.priority = 1
            self.assertEqual(config.get_next().command, 'ActivityCommon')

    def test_startup_order_survives_refresh_and_only_changes_equal_priority_slots(self):
        config = self.make_config()
        config.script.optimization.startup_task_shuffle_enable = True
        past = datetime.now() - timedelta(days=1)
        for key, priority in (('activity_common', 5), ('activity_common_2', 1), ('main_story', 5)):
            self.enable(config, key, past)
            getattr(config.model, key).scheduler.priority = priority
        config.update_scheduler()
        original = [t.command for t in config.pending_task]
        order = StartupTaskOrder()
        config.startup_task_order = order
        with patch('module.config.startup_order.random.random', return_value=.1) as draw, \
                patch('module.config.startup_order.random.shuffle', side_effect=lambda items: items.reverse()):
            order.initialize(config.pending_task, enabled=True)
            expected = list(original)
            slots = [i for i, name in enumerate(original) if name in ('ActivityCommon', 'MainStory')]
            expected[slots[0]], expected[slots[1]] = expected[slots[1]], expected[slots[0]]
            for _ in range(3):
                config.get_schedule_data()
                self.assertEqual([t.command for t in config.pending_task], expected)
                order.initialize(config.pending_task, enabled=True)
            draw.assert_called_once()
        config.model.__dict__['running_task'] = 'ActivityCommon'
        self.assertEqual(config.get_next().command, 'ActivityCommon')
        config.model.__dict__['running_task'] = ''
        config.model.main_story.scheduler.next_run = past + timedelta(seconds=1)
        config.update_scheduler()
        self.assertEqual([t.command for t in config.pending_task], original)
        config.script.optimization.startup_task_shuffle_enable = False
        config.update_scheduler()
        self.assertEqual([t.command for t in config.pending_task],
                         ['ActivityCommon', 'ActivityCommon2', 'MainStory'])

    def test_startup_order_probability_boundary_and_restart_protection(self):
        now = datetime.now()
        tasks = [SimpleNamespace(command=name, priority=priority, next_run=now)
                 for name, priority in (('Restart', 5), ('A', 5), ('Other', 1), ('B', 5))]
        for chance, expected in ((.1999, ['Restart', 'B', 'Other', 'A']),
                                 (.2, ['Restart', 'A', 'Other', 'B'])):
            order = StartupTaskOrder()
            with patch('module.config.startup_order.random.random', return_value=chance), \
                    patch('module.config.startup_order.random.shuffle'):  # no-op must still change order
                order.initialize(tasks, True)
            self.assertEqual([t.command for t in order.apply(tasks)], expected)
            self.assertEqual([t.command for t in tasks], ['Restart', 'A', 'Other', 'B'])

    def test_startup_order_does_not_draw_for_disabled_single_or_distinct_priorities(self):
        now = datetime.now()
        a = SimpleNamespace(command='A', priority=1, next_run=now)
        b = SimpleNamespace(command='B', priority=2, next_run=now)
        for enabled, tasks in ((False, [a, a]), (True, []), (True, [a]), (True, [a, b])):
            order = StartupTaskOrder()
            with patch('module.config.startup_order.random.random') as draw:
                order.initialize(tasks, enabled)
            draw.assert_not_called()
            self.assertEqual(order.apply(tasks), tasks)

    def test_startup_order_reused_after_config_object_replacement(self):
        from script import Script
        runner = Script.__new__(Script)
        runner.config_name = 'template'
        runner.startup_task_order = StartupTaskOrder()
        first, second = self.make_config(), self.make_config()
        with patch('module.config.config.Config', side_effect=[first, second]):
            self.assertIs(runner.config.startup_task_order, runner.startup_task_order)
            del runner.__dict__['config']
            self.assertIs(runner.config.startup_task_order, runner.startup_task_order)

    def test_startup_order_keeps_new_tasks_and_surviving_candidates(self):
        now = datetime.now()
        a, b, c, new = [SimpleNamespace(command=name, priority=5, next_run=now)
                        for name in ('A', 'B', 'C', 'New')]
        order = StartupTaskOrder()
        with patch('module.config.startup_order.random.random', return_value=0), \
                patch('module.config.startup_order.random.shuffle', side_effect=lambda items: items.reverse()):
            order.initialize([a, b, c], True)
        self.assertEqual([t.command for t in order.apply([a, new, b])], ['B', 'New', 'A'])
        b.priority = 1
        self.assertEqual(order.apply([a, new, b]), [a, new, b])

    def test_server_accepts_only_current_process_snapshot_and_reuses_it(self):
        from module.config.startup_order import active_startup_orders
        from module.server.script_process import ScriptProcess
        from module.server.main_manager import MainManager
        process = ScriptProcess.__new__(ScriptProcess)
        process.config_name = 'template'
        process._process = SimpleNamespace(pid=123)
        order = StartupTaskOrder()
        try:
            payload = {'_startup_task_order': order, '_startup_pid': 122, 'schedule': {}}
            self.assertFalse(process._consume_startup_order(payload))
            self.assertNotIn('template', active_startup_orders)
            payload = {'_startup_task_order': order, '_startup_pid': 123, 'schedule': {}}
            self.assertTrue(process._consume_startup_order(payload))
            self.assertEqual(payload, {'schedule': {}})
            self.assertIs(MainManager.config_cache('template').startup_task_order, order)
        finally:
            active_startup_orders.pop('template', None)


if __name__ == '__main__':
    unittest.main()
