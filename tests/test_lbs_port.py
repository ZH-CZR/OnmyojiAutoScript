# This Python file uses the following encoding: utf-8
"""LBS 鬼王移植回归测试。

来源：lgg686/self ``ad15a023``、``188dee7c``、``a1fb24a6``、``f01a83f0``（tasks/LBS）。
覆盖点：
- 配置模型、菜单、模板与 i18n 注册完整；
- 11 张切图与 1 条挑战次数 OCR 规则齐全；
- 活动页、地图中转页与庭院导航连通；
- ScriptTask 具备三种模式主流程入口；
- GeneralRoom 支持任务自定义弹窗资产参数。
"""
import inspect
import json
import unittest
from pathlib import Path

from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.GameUi.page import page_main
from tasks.LBS.assets import LBSAssets
from tasks.LBS.config import LBS, LBSMode
from tasks.LBS.page import page_lbs, page_lbs_map
from tasks.LBS.script_task import ScriptTask


ROOT = Path(__file__).resolve().parents[1]

IMAGE_RULES = (
    'I_LBS_ENTRY',
    'I_LBS_TEAM_CHALLENGE',
    'I_LBS_SETTLE_CONFIRM',
    'I_LBS_ENSURE_PUBLIC',
    'I_LBS_ENSURE_PUBLIC_FALSE',
    'I_LBS_ENSURE_PRIVATE_FALSE',
    'I_LBS_ENSURE_PRIVATE',
    'I_LBS_CREATE_ENSURE',
    'I_LBS_MAP_ENTRY',
    'I_LBS_FIND_TEAM',
    'I_LBS_MATCH_CANCEL',
)


class LBSRegistrationTests(unittest.TestCase):
    def test_config_model_field(self):
        con = ConfigModel().lbs
        self.assertIsInstance(con, LBS)
        self.assertFalse(con.scheduler.enable)
        self.assertEqual(con.lbs_config.mode, LBSMode.SOLO)
        self.assertEqual(con.lbs_config.limit_count, 30)
        self.assertEqual(con.lbs_config.limit_time.strftime('%H:%M:%S'), '00:30:00')
        self.assertFalse(con.switch_soul.enable)

    def test_menu_entry(self):
        menu = ConfigMenu()
        self.assertIn('LBS', menu.menu['Activity Task'])

    def test_template_block(self):
        with open(ROOT / 'config' / 'template.json', encoding='utf-8') as f:
            template = json.load(f)
        block = template['lbs']
        for key in ('scheduler', 'lbs_config', 'switch_soul', 'general_battle_config'):
            self.assertIn(key, block)
        self.assertEqual(block['lbs_config']['mode'], '单人挑战')

    def test_i18n_entry(self):
        with open(ROOT / 'assets' / 'i18n' / 'zh-CN.json', encoding='utf-8') as f:
            i18n = json.load(f)
        self.assertEqual(i18n['LBS'], 'LBS鬼王')
        self.assertEqual(i18n['lbs_config'], 'LBS鬼王配置')
        self.assertEqual(i18n['lbs_mode'], '运行模式')
        self.assertIn('lbs_mode_help', i18n)
        self.assertIn('limit_count', i18n)
        self.assertIn('limit_count_help', i18n)


class LBSAssetTests(unittest.TestCase):
    def test_image_rules_and_files(self):
        for name in IMAGE_RULES:
            rule = getattr(LBSAssets, name)
            self.assertIsInstance(rule, RuleImage)
            self.assertTrue((ROOT / rule.file.lstrip('./')).is_file(), rule.file)

    def test_ocr_rule(self):
        rule = LBSAssets.O_LBS_COUNT
        self.assertIsInstance(rule, RuleOcr)
        self.assertEqual(rule.mode.name, 'DIGITCOUNTER')


class LBSPageTests(unittest.TestCase):
    def test_main_connects_lbs(self):
        self.assertIn(page_lbs, [t.destination for t in page_main.transitions])

    def test_lbs_map_chain(self):
        lbs_destinations = [t.destination for t in page_lbs.transitions]
        self.assertIn(page_lbs_map, lbs_destinations)
        map_destinations = [t.destination for t in page_lbs_map.transitions]
        self.assertIn(page_main, map_destinations)
        self.assertIn(page_lbs, map_destinations)


class LBSScriptTests(unittest.TestCase):
    def test_script_task_entries(self):
        for name in ('run', '_run_solo', '_run_team_match', '_run_drive_mode', '_reach_exit'):
            self.assertTrue(hasattr(ScriptTask, name), name)

    def test_general_room_accepts_custom_rules(self):
        for name in ('create_room', 'ensure_private', 'ensure_public', 'create_ensure'):
            params = inspect.signature(getattr(GeneralRoom, name)).parameters
            self.assertTrue(
                any(key in params for key in ('ensure_rules', 'private_rules', 'public_rules')),
                name,
            )


if __name__ == '__main__':
    unittest.main()
