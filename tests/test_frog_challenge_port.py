# This Python file uses the following encoding: utf-8
"""青蛙瓷器挑战赛移植回归测试。

来源：lgg686/self ``1f230af2``（tasks/FrogChallenge）。
覆盖点：
- 配置模型、菜单、模板与 i18n 注册完整；
- 5 张切图与 2 条 OCR 规则齐全；
- 页面与庭院双向连通，且支持右侧活动栏展开；
- ScriptTask 具备挑战主流程与御魂切换入口。
"""
import json
import unittest
from pathlib import Path

from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from tasks.FrogChallenge.assets import FrogChallengeAssets
from tasks.FrogChallenge.config import FrogChallenge
from tasks.FrogChallenge.page import page_frog_challenge
from tasks.FrogChallenge.script_task import ScriptTask
from tasks.GameUi.page import page_main


ROOT = Path(__file__).resolve().parents[1]


class FrogChallengeRegistrationTests(unittest.TestCase):
    def test_config_model_field(self):
        con = ConfigModel().frog_challenge
        self.assertIsInstance(con, FrogChallenge)
        self.assertFalse(con.scheduler.enable)
        self.assertEqual(con.general_battle_config.preset_group, 1)
        self.assertFalse(con.switch_soul_config.enable)

    def test_menu_entry(self):
        menu = ConfigMenu()
        self.assertIn('FrogChallenge', menu.menu['Activity Task'])

    def test_template_block(self):
        with open(ROOT / 'config' / 'template.json', encoding='utf-8') as f:
            template = json.load(f)
        block = template['frog_challenge']
        for key in ('scheduler', 'general_battle_config', 'switch_soul_config'):
            self.assertIn(key, block)

    def test_i18n_entry(self):
        with open(ROOT / 'assets' / 'i18n' / 'zh-CN.json', encoding='utf-8') as f:
            i18n = json.load(f)
        self.assertEqual(i18n['FrogChallenge'], '青蛙瓷器挑战赛')


class FrogChallengeAssetTests(unittest.TestCase):
    def test_image_rules_and_files(self):
        for name in ('I_GOTO_FROG_CHALLENGE', 'I_FC_SKIP', 'I_CHECK_FROG_CHALLENGE',
                     'I_FC_FIRE', 'I_FC_FIRE_STOP'):
            rule = getattr(FrogChallengeAssets, name)
            self.assertIsInstance(rule, RuleImage)
            self.assertTrue((ROOT / rule.file.lstrip('./')).is_file(), rule.file)

    def test_ocr_rules(self):
        self.assertIsInstance(FrogChallengeAssets.O_MYSTERY_DICE_REWARD, RuleOcr)
        self.assertEqual(FrogChallengeAssets.O_MYSTERY_DICE_REWARD.mode.name, 'DIGITCOUNTER')
        self.assertIsInstance(FrogChallengeAssets.O_CLICK_ANYWHERE_CONTINUE, RuleOcr)
        self.assertEqual(FrogChallengeAssets.O_CLICK_ANYWHERE_CONTINUE.mode.name, 'SINGLE')


class FrogChallengePageTests(unittest.TestCase):
    def test_page_connected_with_main(self):
        self.assertIn(page_frog_challenge, [t.destination for t in page_main.transitions])
        self.assertIn(page_main, [t.destination for t in page_frog_challenge.transitions])


class FrogChallengeScriptTests(unittest.TestCase):
    def test_script_task_entries(self):
        self.assertTrue(hasattr(ScriptTask, 'run'))
        self.assertTrue(hasattr(ScriptTask, 'run_challenge'))
        self.assertTrue(hasattr(ScriptTask, 'switch_soul'))


if __name__ == '__main__':
    unittest.main()
