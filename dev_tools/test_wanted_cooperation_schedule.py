"""Accepted invitations queue one run without preempting the active task."""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from dev_tools import test_manual_schedule as manual_tests
from module.config.config import Config
from module.config.idle import TIMED, IDLE
from module.config.manual import MANUAL, CooperationStore
from module.script.immediate import ImmediateExecution
from tasks.base_task import BaseTask


class CooperationScheduleTests(unittest.TestCase):
    def setUp(self):
        manual_tests.ManualScheduleTest.setUp(self)
        self.config.cooperation_store = CooperationStore(
            'one', Path(self.temp.name) / 'cooperation.sqlite3')

    def test_one_shot_runs_even_when_disabled_or_manual_without_changing_settings(self):
        scheduler = self.config.model.wanted_quests.scheduler
        for enabled, mode in ((False, TIMED), (True, TIMED), (True, MANUAL), (True, IDLE)):
            with self.subTest(enabled=enabled, mode=mode):
                scheduler.enable, scheduler.execution_mode = enabled, mode
                scheduler.next_run = datetime.now() + timedelta(days=10)
                before = scheduler.model_dump()
                self.config.cooperation_store.request('wanted_quests')
                selected = self.config.get_next()
                self.assertEqual(selected.command, 'WantedQuests')
                self.assertLessEqual(selected.next_run, datetime.now())
                self.assertEqual(scheduler.model_dump(), before)
                self.assertEqual(self.config.manual_store.pending(), {})
                self.assertTrue(self.config.consume_cooperation_request(selected))
                self.assertFalse(self.config.consume_cooperation_request(selected))
                self.config.update_scheduler()
                self.assertFalse(self.config.pending_task)

    def test_active_task_is_not_preempted_and_overview_keeps_request_pending(self):
        pets = self.config.model.pets.scheduler
        pets.enable, pets.priority = True, 100
        pets.next_run = datetime.now() - timedelta(days=1)
        parent = self.config.get_next()
        self.config.model.running_task = 'Pets'
        self.config.model.wanted_quests.scheduler.priority = 0
        self.config.cooperation_store.request('wanted_quests')
        task = BaseTask.__new__(BaseTask)
        task.config = self.config
        task._check_first_priority_task()
        self.assertIs(self.config.task, parent)
        data = self.config.get_schedule_data()
        self.assertEqual(data['running']['name'], 'Pets')
        self.assertEqual([t['name'] for t in data['pending']], ['WantedQuests'])
        self.assertNotIn('immediate', data)
        runner = SimpleNamespace(config=self.config)
        # The safe suspension mechanism never services cooperation requests.
        self.assertFalse(ImmediateExecution(runner).checkpoint(task))
        self.config.model.running_task = ''
        self.assertEqual(self.config.get_next().command, 'WantedQuests')

    def test_request_survives_refresh_reload_and_new_config_instance(self):
        store = self.config.cooperation_store
        store.request('wanted_quests')
        token = store.pending()['wanted_quests']
        for _ in range(3):
            self.config.get_schedule_data()
        with patch('module.config.config.ConfigModel', return_value=self.config.model.model_copy(deep=True)):
            self.config.reload(prune_manual=True)
        other = Config('template')
        other.cooperation_store = CooperationStore('one', store.path)
        self.assertEqual(other.cooperation_store.pending(), {'wanted_quests': token})
        self.assertEqual(CooperationStore('two', store.path).pending(), {})

    def test_repeated_requests_coalesce_and_invitation_during_run_gets_new_token(self):
        store = self.config.cooperation_store
        store.request('wanted_quests')
        selected = self.config.get_next()
        store.request('wanted_quests')
        self.assertEqual(store.pending()['wanted_quests'], selected.cooperation_request)
        self.assertTrue(self.config.consume_cooperation_request(selected))
        store.request('wanted_quests')
        self.assertFalse(self.config.consume_cooperation_request(selected))
        self.assertNotEqual(store.pending()['wanted_quests'], selected.cooperation_request)
        # An unrelated selection/recovery cannot consume the queued invitation.
        self.assertFalse(self.config.consume_cooperation_request(SimpleNamespace(command='Restart')))
        self.assertTrue(store.pending())

    def test_manual_requests_keep_precedence_and_normal_schedule_is_not_duplicated(self):
        manual_tests.ManualScheduleTest.enable(self, 'orochi')
        self.config.manual_store.request('orochi')
        wanted = self.config.model.wanted_quests.scheduler
        wanted.enable = True
        wanted.next_run = datetime.now() - timedelta(days=1)
        self.config.cooperation_store.request('wanted_quests')
        self.config.update_scheduler()
        self.assertEqual([t.command for t in self.config.pending_task], ['Orochi', 'WantedQuests'])
        self.assertEqual(self.config.waiting_task, [])

    def test_executor_consumes_only_after_successful_preparation(self):
        from script import Script
        from module.script.runtime_controller import ScriptRuntimeDecision as Decision
        runner = Script.__new__(Script)
        runner.config_name = 'template'
        runner.__dict__['config'] = self.config
        runner.__dict__['device'] = Mock()
        runner.resource_precache_enable = False
        runner.startup_task_order = Mock()
        runner.state_queue = None
        runner.is_first_task = False
        runner._error_restart_pending = False
        runner.failure_record = {}
        runner.publish_schedule = Mock()
        self.config.model.script.device.run_background_only = True
        store = self.config.cooperation_store
        store.request('wanted_quests')
        selections = []

        def select():
            if len(selections) == 3:
                raise KeyboardInterrupt
            runner.__dict__['config'] = self.config
            selections.append(self.config.get_next())
            return selections[-1].command

        decisions = iter([Decision.RESCHEDULE, Decision.FAILED, Decision.READY])

        def prepare(command):
            self.assertEqual(command, 'WantedQuests')
            self.assertTrue(store.pending())
            return next(decisions)

        def run(command):
            self.assertEqual(command, 'WantedQuests')
            self.assertEqual(store.pending(), {})
            store.request('wanted_quests')  # A new invitation during this run.
            return True

        runner.get_next_task = Mock(side_effect=select)
        runner.runtime = SimpleNamespace(prepare_task_execution=Mock(side_effect=prepare))
        runner.run = Mock(side_effect=run)
        with patch('script.logger.set_file_logger'), \
                self.assertRaises(KeyboardInterrupt):
            runner.loop()
        runner.run.assert_called_once_with('WantedQuests')
        self.assertTrue(store.pending())
        self.assertNotEqual(store.pending()['wanted_quests'], selections[-1].cooperation_request)

    def test_automatic_request_obeys_runtime_guard_in_manual_and_idle_modes(self):
        from script import Script
        for mode in (MANUAL, IDLE):
            with self.subTest(mode=mode):
                self.config.model.wanted_quests.scheduler.execution_mode = mode
                self.config.cooperation_store.request('wanted_quests')
                self.config.get_next()
                runner = Script.__new__(Script)
                runner.__dict__['config'] = self.config
                runner.__dict__['device'] = Mock(activity_guard=None)
                runner.__dict__['activity_guard'] = Mock()
                guard = runner.activity_guard
                guard.checkpoint.return_value = False
                runner.__dict__['immediate_execution'] = SimpleNamespace(checkpoint=Mock())
                runner._error_restart_pending = False
                seen = []

                def execute():
                    seen.append(runner.device.activity_guard)
                    self.assertIsNone(self.config.idle_execution)

                task_module = SimpleNamespace(ScriptTask=Mock(return_value=SimpleNamespace(run=execute)))
                with patch('script.set_ocr_logging_enabled'), \
                        patch('script.load_module', return_value=task_module):
                    runner.run('WantedQuests')
                self.assertEqual(seen, [guard])
                guard.checkpoint.assert_called_once_with()
                guard.start.assert_called_once_with()
                guard.finish.assert_called_once_with()
                self.assertIsNone(runner.device.activity_guard)


if __name__ == '__main__':
    unittest.main()
