"""Residency must not alter ordinary queues or consume their request tokens."""
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.idle import IdleStore, TIMED, IDLE
from module.config.manual import ManualStore, CooperationStore, MANUAL
from module.exception import TaskEnd
from dev_tools import test_meta_demon_resident as resident
from tasks.Component.config_scheduler import ExecutionMode
from tasks.Script.config_optimization import ScheduleRule
from tasks.GameUi.page import PageRegistry
from tasks.GameUi.game_ui import GameUi


class ScheduleIsolationTest(unittest.TestCase):
    def setUp(self):
        self.saving = patch.object(ConfigModel, 'save')
        self.save = self.saving.start()
        self.addCleanup(self.saving.stop)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner = resident.ResidentTest().runner()
        self.config = self.runner.config
        root = Path(self.temp.name)
        self.config.manual_store = ManualStore('isolation', root / 'manual.sqlite3')
        self.config.cooperation_store = CooperationStore('isolation', root / 'cooperation.sqlite3')
        self.config.idle_store = IdleStore('isolation', root / 'idle.sqlite3')
        for key in ConfigModel.model_fields:
            scheduler = getattr(getattr(self.config.model, key), 'scheduler', None)
            if scheduler is not None:
                scheduler.enable = False
        reloading = patch.object(self.config, 'reload')
        self.reload = reloading.start()
        self.addCleanup(reloading.stop)

    def enable(self, key, mode=TIMED, future=False):
        scheduler = getattr(self.config.model, key).scheduler
        scheduler.enable, scheduler.execution_mode = True, ExecutionMode(mode)
        scheduler.next_run = datetime.now() + timedelta(days=1) if future else datetime.now() - timedelta(minutes=1)

    def test_future_meta_demon_does_not_reorder_or_rewrite_other_due_tasks(self):
        for key in ('wanted_quests', 'pets', 'orochi'):
            self.enable(key)
        before = self.config.model.model_dump()
        for rule in ScheduleRule:
            with self.subTest(rule=rule):
                self.config.script.optimization.schedule_rule = rule
                self.config.meta_demon.scheduler.enable = False
                self.config.update_scheduler()
                expected = [task.command for task in self.config.pending_task]
                self.enable('meta_demon', future=True)
                self.config.update_scheduler()
                self.assertEqual([task.command for task in self.config.pending_task], expected)
                self.runner.run_meta_demon_resident = Mock(side_effect=AssertionError('ready work must run'))
                self.assertEqual(self.runner.get_next_task(), expected[0])
        for key in ('wanted_quests', 'pets', 'orochi'):
            self.assertEqual(self.config.model.model_dump()[key], before[key])
        self.save.assert_not_called()

    def test_real_manual_cooperation_and_idle_queues_all_end_residency_without_consumption(self):
        for kind in ('timed', 'manual', 'cooperation', 'idle'):
            with self.subTest(kind=kind):
                for key in ('pets', 'orochi', 'six_realms', 'wanted_quests'):
                    getattr(self.config.model, key).scheduler.enable = False
                self.enable('meta_demon', future=True)
                self.config.manual_store.clear('orochi')
                if kind == 'timed':
                    self.enable('pets')
                elif kind == 'manual':
                    self.enable('orochi', MANUAL)
                    self.config.manual_store.request('orochi')
                elif kind == 'cooperation':
                    self.config.cooperation_store.request('wanted_quests')
                else:
                    self.enable('six_realms', IDLE)
                    # SixRealms has the real idle adapter and a finite count.
                    self.config.six_realms.six_realms_gate.limit_count = 1
                manual = self.config.manual_store.pending()
                cooperation = self.config.cooperation_store.pending()
                self.config.update_scheduler()
                self.assertTrue(self.config.pending_task)
                task = resident.ResidentTest().task()
                task.config = self.config
                with self.assertRaises(TaskEnd):
                    task._resident_loop()
                task._try_friend_boss.assert_not_called()
                self.assertEqual(self.config.manual_store.pending(), manual)
                self.assertEqual(self.config.cooperation_store.pending(), cooperation)
                if kind == 'cooperation':
                    token = cooperation['wanted_quests']
                    self.config.cooperation_store.consume('wanted_quests', token)
        self.save.assert_not_called()

    def test_real_resident_handoff_restores_navigation_config_and_device_guard(self):
        self.enable('meta_demon', future=True)
        self.enable('wanted_quests')
        # Importing the resident task has already registered its exit pages.
        before = {page: {dest: list(buttons) for dest, buttons in page.links.items()}
                  for page in PageRegistry.all()}
        model = self.config.model.model_dump()
        previous_task = self.config.task
        close = GameUi.ui_close
        with patch('script.Device', side_effect=AssertionError('must not create device')):
            self.runner.run_meta_demon_resident()
        self.assertEqual({page: page.links for page in PageRegistry.all()}, before)
        self.assertEqual(self.config.model.model_dump(), model)
        self.assertIs(self.config.task, previous_task)
        self.assertIs(GameUi.ui_close, close)
        self.assertIsNone(self.runner.device.activity_guard)
        self.assertNotIn('meta_demon_resident_activity', self.config.__dict__)
        self.save.assert_not_called()

    def test_disable_during_observation_restores_navigation_and_stops_reentry(self):
        self.enable('meta_demon', future=True)
        before = {page: {dest: list(buttons) for dest, buttons in page.links.items()}
                  for page in PageRegistry.all()}
        self.reload.side_effect = lambda: setattr(self.config.meta_demon.scheduler, 'enable', False)
        self.runner.run_meta_demon_resident()
        self.assertFalse(self.config.meta_demon.scheduler.enable)
        self.assertEqual({page: page.links for page in PageRegistry.all()}, before)
        self.assertEqual(self.config.model.running_task, '')
        self.assertIsNone(self.runner.device.activity_guard)
        with patch.object(self.runner, 'run') as run:
            self.runner.run_meta_demon_resident()
        run.assert_not_called()
        self.save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
