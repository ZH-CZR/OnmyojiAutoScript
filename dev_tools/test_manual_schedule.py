"""Manual requests must never become automatic schedules; no game/device IO."""
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.manual import MANUAL, ManualStore
from module.config.idle import IDLE, TIME_FIELDS, IDLE_FIELDS, IdleStore
from dev_tools import test_schedule_api as api_tests


class ManualScheduleTest(unittest.TestCase):
    def setUp(self):
        saving = patch.object(ConfigModel, 'save')
        saving.start()
        self.addCleanup(saving.stop)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Config('template')
        self.config.manual_store = ManualStore('one', Path(self.temp.name) / 'manual.sqlite3')
        self.config.idle_store = IdleStore('one', Path(self.temp.name) / 'idle.sqlite3')
        for key in self.config.model.model_fields:
            scheduler = getattr(getattr(self.config.model, key), 'scheduler', None)
            if scheduler:
                scheduler.enable = False

    def enable(self, key='orochi'):
        s = getattr(self.config.model, key).scheduler
        s.enable, s.execution_mode = True, MANUAL
        s.next_run = datetime.now() - timedelta(days=10)
        return s

    def test_saved_running_task_never_marks_unstarted_manual_task_as_active(self):
        self.enable('dokan')
        saved = self.config.model.model_copy(deep=True)
        saved.running_task = 'Dokan'
        with patch('module.config.config.ConfigModel', return_value=saved):
            fresh = Config('template')
        fresh.manual_store = self.config.manual_store
        fresh.idle_store = self.config.idle_store
        self.assertEqual(fresh.model.running_task, '')
        data = fresh.get_schedule_data()
        self.assertEqual(data['running'], {})
        self.assertEqual(data['manual'][0]['status'], '等待手动执行')
        # Reloading a live child preserves its actual task, not the disk value.
        fresh.model.running_task = 'Pets'
        disk = saved.model_copy(deep=True)
        disk.running_task = 'Dokan'
        with patch('module.config.config.ConfigModel', return_value=disk):
            fresh.reload()
        self.assertEqual(fresh.model.running_task, 'Pets')

    def test_only_frontend_request_can_make_manual_task_due(self):
        s = self.enable()
        before = s.next_run
        for _ in range(2):
            data = self.config.get_schedule_data()
            self.assertEqual(data['running'], {})
            self.assertEqual(data['waiting'], [])
            self.assertEqual(data['manual'][0]['status'], '等待手动执行')
            self.assertGreater(self.config.get_next().next_run, datetime.now())
        self.assertFalse(self.config.task_call('Orochi'))
        with patch.object(self.config, 'reload'), patch.object(self.config, 'save') as save:
            for success in (True, False, None):
                self.config.task_delay('Orochi', success=success, target=datetime.now())
            save.assert_not_called()
        self.assertEqual(s.next_run, before)
        self.config.manual_store.request('orochi')
        selected = self.config.get_next()
        self.assertEqual(selected.command, 'Orochi')
        self.assertLessEqual(selected.next_run, datetime.now())
        self.assertTrue(self.config.manual_store.consume('orochi', selected.manual_request))
        self.assertFalse(self.config.manual_store.consume('orochi', selected.manual_request))
        self.assertEqual(self.config.get_schedule_data()['running'], {})

    def test_queue_coalesces_and_isolates_configs_and_new_requests(self):
        self.enable()
        store = self.config.manual_store
        store.request('orochi')
        token = store.pending()['orochi']
        store.request('orochi')
        self.assertEqual(store.pending()['orochi'], token)
        self.assertEqual(ManualStore('one', store.path).pending()['orochi'], token)
        self.assertEqual(ManualStore('two', store.path).pending(), {})
        self.assertTrue(store.consume('orochi', token))
        store.request('orochi')
        self.assertFalse(store.consume('orochi', token))
        self.assertTrue(store.pending())

    def test_manual_bypasses_weekly_projection_and_has_precedence(self):
        for key in ('demon_retreat', 'abyss_shadows'):
            self.enable(key).next_run = datetime.now() + timedelta(days=60)
            self.config.manual_store.request(key)
        self.config.model.pets.scheduler.enable = True
        self.config.model.pets.scheduler.next_run = datetime.now() - timedelta(days=1)
        self.config.update_scheduler()
        self.assertEqual([t.command for t in self.config.pending_task], ['DemonRetreat', 'AbyssShadows', 'Pets'])
        self.assertEqual(len(self.config.normal_pending_task), 3)

    def test_manual_poll_does_not_delay_earlier_timed_task(self):
        self.enable()
        pets = self.config.model.pets.scheduler
        pets.enable = True
        pets.next_run = datetime.now() + timedelta(seconds=2)
        self.assertEqual(self.config.get_next().command, 'Pets')

    def test_immediate_request_does_not_interrupt_current_task_priority_checkpoint(self):
        from tasks.base_task import BaseTask
        pets = self.config.model.pets.scheduler
        pets.enable, pets.priority = True, 100
        pets.next_run = datetime.now() - timedelta(days=1)
        self.config.get_next()
        self.enable().priority = 0
        self.config.manual_store.request('orochi')
        current = BaseTask.__new__(BaseTask)
        current.config = self.config
        current._check_first_priority_task()
        self.assertEqual([task.command for task in self.config.pending_task], ['Orochi', 'Pets'])

    def test_timed_mode_never_uses_immediate_queue(self):
        from module.config.idle import TIMED
        s = self.enable()
        s.execution_mode = TIMED
        s.next_run = datetime.now() + timedelta(days=1)
        self.config.manual_store.request('orochi')
        self.assertGreater(self.config.get_next().next_run, datetime.now())
        self.assertEqual(self.config.manual_store.pending(), {})
        self.assertEqual(s.execution_mode, TIMED)

    def test_disable_or_mode_change_discards_pending_request(self):
        s = self.enable()
        self.config.manual_store.request('orochi')
        s.enable = False
        self.config.update_scheduler()
        self.assertEqual(self.config.manual_store.pending(), {})
        s.enable = True
        self.config.manual_store.request('orochi')
        s.execution_mode = IDLE
        self.config.update_scheduler()
        self.assertEqual(self.config.manual_store.pending(), {})

    def test_all_models_expose_manual_mode_and_hide_dormant_fields(self):
        for key in self.config.model.model_fields:
            model = getattr(self.config.model, key)
            if getattr(model, 'scheduler', None) is None:
                continue
            with self.subTest(task=key):
                payload = self.config.model.script_task(key)['scheduler']
                mode = next(item for item in payload if item['name'] == 'execution_mode')
                self.assertIn(MANUAL, mode['enumEnum'])
                for item in payload:
                    if item['name'] in TIME_FIELDS | IDLE_FIELDS | {'priority'}:
                        self.assertNotIn(MANUAL, item['execution_modes'])
        banquet = self.config.model.script_task('GuildBanquet')['guild_banquet_time']
        self.assertNotIn('execution_modes', next(item for item in banquet if item['name'] == 'enable'))

    def test_manual_chess_ignores_block_without_clearing_it(self):
        from tasks.Chess.script_task import ScriptTask
        from module.exception import TaskEnd
        self.enable('chess')
        until = datetime.now() + timedelta(days=7)
        self.config.idle_store.block('chess', until, 'full')
        task = ScriptTask.__new__(ScriptTask)
        task.config = self.config
        task.run_timed = Mock()
        task.run()
        task.run_timed.assert_called_once()
        self.assertIsNotNone(self.config.idle_store.blocked('chess', datetime.now()))
        self.config.model.chess.scheduler.execution_mode = IDLE
        with self.assertRaises(TaskEnd):
            task.run()

    def test_scheduler_consumes_once_before_success_or_failure(self):
        from dev_tools.test_restart_compatibility import RestartCompatibilityTest, SchedulerBoundary
        for success in (True, False):
            with self.subTest(success=success):
                self.enable()
                self.config.model.script.error.handle_error = False
                self.config.model.script.device.run_background_only = True
                self.config.manual_store.request('orochi')
                self.config.get_next()
                runner, _ = RestartCompatibilityTest().make_runner()
                runner.__dict__['config'] = self.config
                runner.get_next_task = Mock(side_effect=['Orochi', SchedulerBoundary()])
                def run(command):
                    self.assertEqual(self.config.manual_store.pending(), {})
                    return success
                runner.run = Mock(side_effect=run)
                with patch('script.logger'), patch('script.RuleScatter'), \
                        patch('script.del_cached_property'), patch.object(self.config, 'reload'):
                    if success:
                        with self.assertRaises(SchedulerBoundary):
                            runner.loop()
                    else:
                        runner.loop()
                runner.run.assert_called_once_with('Orochi')
                self.assertEqual(self.config.get_schedule_data()['running'], {})

    def test_dynamic_loader_and_manual_run_skip_guard_but_keep_accounting(self):
        from script import Script
        from tasks.base_task_parent import BaseTaskParent
        self.enable()
        self.config.manual_store.request('orochi')
        self.config.get_next()
        dynamic = type('ScriptTask', (BaseTaskParent,), {'__module__': 'script_task'})
        task = dynamic.__new__(dynamic)
        task.config = self.config
        self.assertTrue(task.manual_execution)
        runner = Script.__new__(Script)
        runner.__dict__['config'] = self.config
        runner.__dict__['device'] = SimpleNamespace(screenshot=Mock(), activity_guard='previous')
        guard = Mock()
        guard.checkpoint.side_effect = AssertionError('Manual must not rest')
        runner.__dict__['activity_guard'] = guard
        def execute():
            self.assertIsNone(runner.device.activity_guard)
        module = SimpleNamespace(ScriptTask=lambda **kwargs: SimpleNamespace(run=execute))
        with patch('script.load_module', return_value=module):
            runner.run('Orochi')
        guard.checkpoint.assert_not_called()
        guard.start.assert_called_once()
        guard.finish.assert_called_once()
        self.assertEqual(runner.device.activity_guard, 'previous')

    def test_manual_hunt_and_dokan_ignore_entry_clock(self):
        from tasks.Hunt.script_task import ScriptTask as HuntTask
        from tasks.Dokan.script_task import ScriptTask as DokanTask
        from tasks.DemonEncounter.script_task import ScriptTask as DemonTask
        for task_type, key, method in ((HuntTask, 'hunt', 'check_datetime'),
                                      (DokanTask, 'dokan', 'check_current_weekday'),
                                      (DemonTask, 'demon_encounter', 'check_time')):
            self.enable(key)
            task = task_type.__new__(task_type)
            task.config = self.config
            task.set_next_run = Mock(side_effect=AssertionError('Must not defer'))
            with patch('tasks.Hunt.script_task.datetime') as clock:
                clock.now.return_value = datetime(2026, 10, 19, 1)
                getattr(task, method)()
            task.set_next_run.assert_not_called()


class ManualApiTest(api_tests.ScheduleApiTest):
    async def test_manual_wait_does_not_reload_or_delay_any_other_task(self):
        with TemporaryDirectory() as directory:
            self.config.manual_store = ManualStore('test', Path(directory) / 'requests.sqlite3')
            for key in ('orochi', 'pets'):
                scheduler = getattr(self.config.model, key).scheduler
                scheduler.enable, scheduler.execution_mode = True, MANUAL
                self.config.manual_store.request(key)
            before = self.config.model.model_dump()
            with patch.object(self.config, 'task_delay', side_effect=AssertionError('Must only cancel request')), \
                    patch.object(self.config, 'reload', side_effect=AssertionError('Must not replace configuration')):
                self.assertTrue(await self.router.sync_next_run('test', 'Orochi'))
                self.assertFalse(await self.router.sync_next_run('test', 'NotATask'))
            self.assertEqual(self.config.model.model_dump(), before)
            self.assertEqual(list(self.config.manual_store.pending()), ['pets'])

    async def test_manual_wait_cancels_request_preserving_mode_time_and_active_task(self):
        with TemporaryDirectory() as directory:
            self.config.manual_store = ManualStore('test', Path(directory) / 'requests.sqlite3')
            s = self.config.model.orochi.scheduler
            s.enable, s.execution_mode = True, MANUAL
            before = s.next_run
            self.config.manual_store.request('orochi')
            self.config.model.pets.scheduler.enable = True
            self.process.stop = Mock()
            with patch.object(ConfigModel, 'save') as save, patch.object(self.config, 'reload'):
                self.config.model.running_task = 'Pets'
                save.reset_mock()
                for _ in range(2):
                    self.assertTrue(await self.router.sync_next_run('test', 'Orochi', ''))
                save.assert_not_called()
                self.assertEqual(self.config.model.running_task, 'Pets')
            self.process.stop.assert_not_called()
            self.assertEqual(self.config.manual_store.pending(), {})
            self.assertEqual(s.execution_mode, MANUAL)
            self.assertEqual(s.next_run, before)
            self.assertTrue(s.enable)
            data = self.process.broadcast_state.call_args.args[0]['schedule']
            self.assertEqual(data['running']['name'], 'Pets')
            self.assertEqual(data['manual'], [{'name': 'Orochi', 'status': '等待手动执行'}])

    async def test_request_does_not_change_schedule_and_pushes_overview(self):
        with TemporaryDirectory() as directory:
            self.config.manual_store = ManualStore('test', Path(directory) / 'manual.sqlite3')
            s = self.config.model.orochi.scheduler
            s.enable, s.execution_mode = True, MANUAL
            before = s.next_run
            with patch.object(ConfigModel, 'save') as save:
                self.assertTrue(await self.router.run_now('test', 'Orochi'))
                save.assert_not_called()
            self.assertEqual(s.next_run, before)
            self.assertIn('orochi', self.config.manual_store.pending())
            self.assertEqual(self.process.broadcast_state.call_args.args[0]['schedule']['running']['name'], 'Orochi')
            s.enable = False
            self.assertFalse(await self.router.run_now('test', 'Orochi'))
            self.assertFalse(await self.router.run_now('missing', 'Orochi'))

    async def test_timed_button_keeps_normal_priority_and_only_changes_its_time(self):
        from tasks.Script.config_optimization import ScheduleRule
        with TemporaryDirectory() as directory:
            self.config.manual_store = ManualStore('test', Path(directory) / 'requests.sqlite3')
            self.config.model.script.optimization.schedule_rule = ScheduleRule.PRIORITY
            s = self.config.model.orochi.scheduler
            s.enable, s.priority = True, 100
            s.next_run = datetime.now() + timedelta(days=30)
            normal = self.config.model.pets.scheduler
            normal.enable, normal.priority = True, 1
            normal.next_run = datetime.now() - timedelta(days=1)
            before = normal.next_run
            with patch.object(ConfigModel, 'save') as save:
                self.assertTrue(await self.router.run_now('test', 'Orochi'))
                save.assert_called_once()
            self.assertLess(s.next_run, datetime.now())
            self.assertEqual(normal.next_run, before)
            self.assertEqual(s.priority, 100)
            self.assertEqual(self.config.manual_store.pending(), {})
            self.assertEqual(self.config.get_next().command, 'Pets')

    async def test_active_task_stays_running_and_request_is_first_pending(self):
        with TemporaryDirectory() as directory:
            self.config.manual_store = ManualStore('test', Path(directory) / 'requests.sqlite3')
            pets = self.config.model.pets.scheduler
            pets.enable = True
            # Current task may already have saved its future schedule.
            pets.next_run = datetime.now() + timedelta(days=1)
            requested = self.config.model.orochi.scheduler
            requested.enable, requested.execution_mode = True, MANUAL
            auto = self.config.model.activity_common.scheduler
            auto.enable, auto.priority = True, 0
            auto.next_run = datetime.now() - timedelta(days=1)
            with patch.object(ConfigModel, 'save'):
                self.config.model.running_task = 'Pets'
                self.assertTrue(await self.router.run_now('test', 'Orochi'))
                data = self.process.broadcast_state.call_args.args[0]['schedule']
                self.assertEqual(data['running']['name'], 'Pets')
                self.assertEqual([item['name'] for item in data['pending']], ['Orochi', 'ActivityCommon'])
                self.assertNotIn('Pets', [item['name'] for item in data['waiting']])
                self.assertEqual(data['manual'][0]['name'], 'Orochi')
                self.config.model.running_task = ''
                self.assertEqual(self.config.get_next().command, 'Orochi')

    async def test_mode_switch_keeps_enabled_task_visible_before_any_request(self):
        with TemporaryDirectory() as directory:
            self.config.manual_store = ManualStore('test', Path(directory) / 'requests.sqlite3')
            self.config.model.orochi.scheduler.enable = True
            with patch.object(ConfigModel, 'save'):
                self.assertTrue(await self.router.script_task(
                    'test', 'Orochi', 'scheduler', 'execution_mode', 'enum', MANUAL))
            data = self.process.broadcast_state.call_args.args[0]['schedule']
            self.assertEqual(data['manual'], [{'name': 'Orochi', 'status': '等待手动执行'}])
            self.assertNotEqual(data['running'].get('name'), 'Orochi')


if __name__ == '__main__':
    unittest.main()
