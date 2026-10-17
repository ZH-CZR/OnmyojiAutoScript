"""Guard against shipping a pre-port template with the current task models."""
import json
import unittest
from pathlib import Path

from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel


class ConfigTemplateTest(unittest.TestCase):
    def test_shipped_template_matches_current_models_and_menu(self):
        path = Path(__file__).resolve().parents[1] / 'config' / 'template.json'
        model = ConfigModel(**json.loads(path.read_text(encoding='utf-8')))
        for tasks in ConfigMenu().gui_menu_list.values():
            for task in tasks:
                with self.subTest(task=task):
                    self.assertTrue(model.script_task(task))
