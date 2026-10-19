"""Guard against shipping a pre-port template with the current task models."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from module.config.config import Config
from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from module.server.config_manager import ConfigManager


class ConfigTemplateTest(unittest.TestCase):
    def test_runtime_queries_and_reload_never_write_configuration(self):
        with patch.object(ConfigModel, 'read_json', return_value={'running_task': 'Dokan'}), \
                patch.object(ConfigModel, 'write_json') as write:
            config = Config('offline-memory')
            self.assertEqual(config.model.running_task, '')
            config.model.running_task = 'Pets'
            config.reload()
            self.assertEqual(config.model.running_task, 'Pets')
            self.assertNotIn('running_task', config.model.model_dump())
            write.assert_not_called()
            with patch('threading.Thread.start'), \
                    patch.object(ConfigManager, 'all_script_files', return_value=[]):
                from module.server.main_manager import MainManager, mm
            with patch.object(mm, 'script_process', {}):
                for _ in range(3):
                    self.assertEqual(MainManager.config_cache('offline-memory').model.running_task, '')
            write.assert_not_called()
            # Ordinary configuration changes must still persist normally.
            self.assertTrue(config.model.script_set_arg('Orochi', 'scheduler', 'enable', True))
            write.assert_called_once()
            self.assertNotIn('running_task', write.call_args.args[1])

    def test_shipped_template_matches_current_models_and_menu(self):
        path = Path(__file__).resolve().parents[1] / 'config' / 'template.json'
        model = ConfigModel(**json.loads(path.read_text(encoding='utf-8')))
        for tasks in ConfigMenu().gui_menu_list.values():
            for task in tasks:
                with self.subTest(task=task):
                    self.assertTrue(model.script_task(task))
