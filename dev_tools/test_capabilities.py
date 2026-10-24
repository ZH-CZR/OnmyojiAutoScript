"""Unavailable tasks cannot import opaque implementations or enter any queue."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from module.config.capabilities import unavailable_reason
from module.config.config import Config
from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from module.config.idle import IdleStore, IDLE
from module.config.manual import ManualStore, MANUAL


class CapabilityBoundaryTest(unittest.TestCase):
    def test_hidden_task_retains_compatible_data_but_rejects_edit_and_call(self):
        self.assertTrue(unavailable_reason('Hyakkiyakou'))
        self.assertFalse(any('Hyakkiyakou' in tasks for tasks in ConfigMenu().menu.values()))
        with patch.object(ConfigModel, 'read_json', return_value={}):
            config = Config('offline')
        self.assertIsNotNone(config.model.hyakkiyakou)
        with patch.object(ConfigModel, 'save') as save:
            self.assertFalse(config.model.script_set_arg('Hyakkiyakou', 'scheduler', 'enable', True))
            self.assertFalse(config.task_call('Hyakkiyakou'))
            save.assert_not_called()

    def test_old_enabled_task_and_manual_request_stay_out_of_overview(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(ConfigModel, 'read_json', return_value={}):
            config = Config('offline')
            config.manual_store = ManualStore('offline', Path(directory) / 'manual.sqlite3')
            config.idle_store = IdleStore('offline', Path(directory) / 'idle.sqlite3')
            for key in config.model.model_fields:
                item = getattr(getattr(config.model, key), 'scheduler', None)
                if item is not None:
                    item.enable = False
            scheduler = config.hyakkiyakou.scheduler
            scheduler.enable = True
            scheduler.next_run = datetime.now() - timedelta(days=1)
            for mode in ('定时执行', MANUAL, IDLE):
                with self.subTest(mode=mode):
                    scheduler.execution_mode = mode
                    config.manual_store.request('hyakkiyakou')
                    data = config.get_schedule_data()
                    self.assertEqual(data['running'], {})
                    self.assertEqual(data['pending'], [])
                    self.assertEqual(data['waiting'], [])
                    self.assertEqual(data.get('manual', []), [])
                    self.assertEqual(data.get('idle', []), [])
                    # An overview query still never destructively prunes tokens.
                    self.assertIn('hyakkiyakou', config.manual_store.pending())

    def test_direct_execution_rejects_before_loading_config_device_or_module(self):
        from script import Script
        runner = Script.__new__(Script)
        with patch('script.load_module') as load:
            self.assertFalse(runner.run('Hyakkiyakou'))
            load.assert_not_called()
        self.assertNotIn('config', runner.__dict__)
        self.assertNotIn('device', runner.__dict__)


if __name__ == '__main__':
    unittest.main()
