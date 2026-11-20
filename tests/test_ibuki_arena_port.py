# This Python file uses the following encoding: utf-8
"""狭间幻境（伊吹之擂）移植回归测试。

来源：lgg686/self ``5bc76c7e`` + ``c2390c2a``（最终资产名为 ``1f230af2`` 重命名后）。
覆盖点：
- 配置模型、菜单、模板与 i18n 注册完整；
- 8 张切图与挑战次数 OCR 规则齐全；
- 庭院/伊吹之擂/狭间幻境三页导航连通；
- ScriptTask 提供循环挑战、次数保护与锁定/御魂切换入口。
"""
import json
import unittest
from pathlib import Path

from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from tasks.GameUi.page import page_main
from tasks.IbukiArena.assets import IbukiArenaAssets
from tasks.IbukiArena.config import IbukiArena
from tasks.IbukiArena.page import page_ibuki, page_ibuki_arena
from tasks.IbukiArena.script_task import ScriptTask


ROOT = Path(__file__).resolve().parents[1]

IMAGE_RULES = (
    'I_MAIN_TO_IBUKI',
    'I_CHECK_IBUKI',
    'I_GOTO_ARENA',
    'I_CHECK_ARENA',
    'I_CHALLENGE',
    'I_SKIP',
    'I_IBUKI_UNLOCK',
    'I_IBUKI_LOCK',
)


class IbukiArenaRegistrationTests(unittest.TestCase):
    def test_config_model_field(self):
        con = ConfigModel().ibuki_arena
        self.assertIsInstance(con, IbukiArena)
        self.assertFalse(con.scheduler.enable)
        self.assertFalse(con.switch_soul_config.enable)
        self.assertFalse(con.general_battle_config.lock_team_enable)

    def test_menu_entry(self):
        menu = ConfigMenu()
        self.assertIn('IbukiArena', menu.menu['Activity Task'])

    def test_template_block(self):
        with open(ROOT / 'config' / 'template.json', encoding='utf-8') as f:
            template = json.load(f)
        block = template['ibuki_arena']
        for key in ('scheduler', 'general_battle_config', 'switch_soul_config'):
            self.assertIn(key, block)
        self.assertFalse(block['scheduler']['enable'])

    def test_i18n_entry(self):
        with open(ROOT / 'assets' / 'i18n' / 'zh-CN.json', encoding='utf-8') as f:
            i18n = json.load(f)
        self.assertEqual(i18n['IbukiArena'], '狭间幻境')


class IbukiArenaAssetTests(unittest.TestCase):
    def test_image_rules_and_files(self):
        for name in IMAGE_RULES:
            rule = getattr(IbukiArenaAssets, name)
            self.assertIsInstance(rule, RuleImage)
            self.assertTrue((ROOT / rule.file.lstrip('./')).is_file(), rule.file)

    def test_ocr_rule(self):
        rule = IbukiArenaAssets.O_CHALLENGE_TIMES
        self.assertIsInstance(rule, RuleOcr)
        self.assertEqual(rule.mode.name, 'DIGITCOUNTER')


class IbukiArenaPageTests(unittest.TestCase):
    def test_main_connects_ibuki(self):
        self.assertIn(page_ibuki, [t.destination for t in page_main.transitions])

    def test_ibuki_arena_chain(self):
        self.assertIn(page_ibuki_arena, [t.destination for t in page_ibuki.transitions])
        self.assertIn(page_main, [t.destination for t in page_ibuki.transitions])
        self.assertIn(page_ibuki, [t.destination for t in page_ibuki_arena.transitions])


class IbukiArenaScriptTests(unittest.TestCase):
    def test_script_task_entries(self):
        for name in ('run', 'run_arena', 'switch_lock', 'switch_soul'):
            self.assertTrue(hasattr(ScriptTask, name), name)

    def test_ocr_fail_protection(self):
        self.assertEqual(ScriptTask.ocr_fail_limit, 3)


if __name__ == '__main__':
    unittest.main()
