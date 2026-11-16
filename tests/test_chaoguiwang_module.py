# This Python file uses the following encoding: utf-8
"""超鬼王（ChaoGuiWang / ChaoGuiWangAssist）新代际模块回归测试。

2026-11-16 从上游 `Carol-official/OnmyojiAutoScript-backup` 的 `chaoguiwang`
分支移植了两个新任务，旧的 `tasks/MetaDemon` 保留不动。这里锁定：

1. 资产可加载：`assets.py` 引用的每张 png 都在，且与 `cgw/image.json` /
   `cgwa/image.json` 的 ROI、阈值一致；
2. 配置模型：默认值、旧星级开关的迁移、互斥模式；
3. 脚本入口与继承链没有被后续同步误删；
4. 任务已登记到配置模型、菜单、调度优先级与中文翻译。
"""
import json
import unittest
from pathlib import Path

from module.atom.image import RuleImage
from tasks.ChaoGuiWang.assets import ChaoGuiWangAssets
from tasks.ChaoGuiWang.config import ChaoGuiWang, ChaoGuiWangConfig, ChaoGuiWangTarget
from tasks.ChaoGuiWang.script_task import ScriptTask as ChaoGuiWangTask
from tasks.ChaoGuiWangAssist.assets import ChaoGuiWangAssistAssets
from tasks.ChaoGuiWangAssist.config import ChaoGuiWangAssist, ChaoGuiWangAssistConfig, ChaoGuiWangAssistMode
from tasks.ChaoGuiWangAssist.script_task import ScriptTask as ChaoGuiWangAssistTask

CGW_DIR = Path('tasks/ChaoGuiWang/cgw')
CGWA_DIR = Path('tasks/ChaoGuiWangAssist/cgwa')


def _image_rules(assets):
    return {
        name: value
        for name, value in vars(assets).items()
        if isinstance(value, RuleImage)
    }


def _json_entries(directory):
    entries = {}
    for entry in json.loads((directory / 'image.json').read_text(encoding='utf-8')):
        entries[entry['imageName']] = entry
    return entries


class ChaoGuiWangAssetTests(unittest.TestCase):
    def test_every_rule_image_exists(self):
        for assets, count in ((ChaoGuiWangAssets, 13), (ChaoGuiWangAssistAssets, 7)):
            rules = _image_rules(assets)
            self.assertGreaterEqual(len(rules), count)
            for name, rule in rules.items():
                self.assertTrue(Path(rule.file).is_file(), f'{name} -> {rule.file}')

    def test_rule_matches_image_json(self):
        for assets, directory in ((ChaoGuiWangAssets, CGW_DIR), (ChaoGuiWangAssistAssets, CGWA_DIR)):
            entries = _json_entries(directory)
            for name, rule in _image_rules(assets).items():
                image_name = Path(rule.file).name
                self.assertIn(image_name, entries, name)
                entry = entries[image_name]
                self.assertEqual(entry['roiFront'], ','.join(map(str, rule.roi_front)), name)
                self.assertEqual(entry['threshold'], rule.threshold, name)

    def test_entry_rules_cover_activity_column(self):
        # 2026-11-16 上游重裁：庭院入口模板的搜索区覆盖右侧活动列全部槽位
        self.assertGreater(ChaoGuiWangAssets.I_CGW_ENTRY.roi_back[3], 400)
        self.assertEqual(
            tuple(ChaoGuiWangAssets.I_CGW_ENTRY.roi_back),
            tuple(ChaoGuiWangAssets.I_CGW_ENTRY_ALT.roi_back),
        )


class ChaoGuiWangConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = ChaoGuiWang()
        self.assertEqual(config.chao_gui_wang_config.target_mode, ChaoGuiWangTarget.COUNT)
        self.assertEqual(config.chao_gui_wang_config.kill_count, 30)
        self.assertTrue(config.chao_gui_wang_config.cgw_fight_star_1)
        self.assertFalse(config.chao_gui_wang_config.cgw_pursuit_star_1)
        self.assertFalse(config.chao_gui_wang_config.cgw_fight_star_6)
        self.assertFalse(config.chao_gui_wang_config.red_mark_boss)
        # 疲劳满后等待恢复而不是结束任务：阈值为满值，恢复到 50 再继续
        self.assertEqual(config.chao_gui_wang_config.fatigue_limit, 100)
        self.assertEqual(config.chao_gui_wang_config.resume_fatigue, 50)
        self.assertEqual(config.chao_gui_wang_config.fatigue_wait_timeout, 0)

    def test_migrate_disabled_fatigue_resume(self):
        # 旧配置用 101 表示「不启用等待」，新默认 50 且 le=100，必须能平滑迁移
        config = ChaoGuiWang(chao_gui_wang_config={'resume_fatigue': 101})
        self.assertEqual(config.chao_gui_wang_config.resume_fatigue, 50)

    def test_migrate_three_switch_generation(self):
        config = ChaoGuiWang(chao_gui_wang_config={'star_rank_1_4': False, 'star_rank_5': True})
        values = [getattr(config.chao_gui_wang_config, f'cgw_fight_star_{rank}') for rank in range(1, 7)]
        self.assertEqual(values, [False, False, False, False, True, False])
        self.assertNotIn('star_rank_1_4', config.chao_gui_wang_config.model_dump())

    def test_assist_defaults_and_migration(self):
        config = ChaoGuiWangAssist()
        self.assertEqual(config.chao_gui_wang_assist_config.mode, ChaoGuiWangAssistMode.INVITE)
        self.assertEqual(config.chao_gui_wang_assist_config.share_friend_name, '')
        migrated = ChaoGuiWangAssist(
            chao_gui_wang_assist_config={
                'invite_star_1': True, 'invite_star_2': False, 'invite_star_3': False,
                'invite_star_4': False, 'invite_star_5': True,
            }
        ).chao_gui_wang_assist_config
        self.assertEqual(
            [getattr(migrated, f'cgwa_invite_star_{rank}') for rank in range(1, 7)],
            [True, False, False, False, True, False],
        )
        self.assertEqual(
            [getattr(migrated, f'cgwa_fight_star_{rank}') for rank in range(1, 7)],
            [True, False, False, False, True, False],
        )


class ChaoGuiWangTaskTests(unittest.TestCase):
    def test_star_order_by_fatigue(self):
        # 疲劳 50~60 时优先 5/6 星；其余区间先 4/5/6，打完再退到 1/2/3
        task = object.__new__(ChaoGuiWangTask)
        task.high_star_warned = False
        cfg = ChaoGuiWangConfig()
        cfg.cgw_fight_star_5 = True
        cfg.cgw_fight_star_6 = True
        self.assertEqual(task.star_order_by_fatigue(cfg, 55), [6, 5, 4, 3, 2, 1])
        self.assertEqual(task.star_order_by_fatigue(cfg, 40), [4, 5, 6, 3, 2, 1])
        # 自定义顺位仍然生效，疲劳窗口只做前置提升
        cfg.ticket_order = '321'
        self.assertEqual(task.star_order_by_fatigue(cfg, 55), [3, 2, 1])

    def test_inheritance(self):
        self.assertTrue(issubclass(ChaoGuiWangTask, ChaoGuiWangAssets))
        self.assertTrue(issubclass(ChaoGuiWangAssistTask, ChaoGuiWangTask))
        self.assertTrue(issubclass(ChaoGuiWangAssistTask, ChaoGuiWangAssistAssets))

    def test_entrypoints(self):
        for name in ('run', 'ensure_ticket_order', 'click_stage', 'diagnose_and_recover'):
            self.assertTrue(callable(getattr(ChaoGuiWangTask, name, None)), name)
        for name in ('run', 'run_invite', 'run_assist', 'click', 'appear_then_click'):
            self.assertTrue(callable(getattr(ChaoGuiWangAssistTask, name, None)), name)


class ChaoGuiWangRegistrationTests(unittest.TestCase):
    """配置模型 / 菜单 / 调度优先级里漏登记会让任务在 GUI 里消失或被 FILTER 静默丢弃。"""

    def test_registered(self):
        model = Path('module/config/config_model.py').read_text(encoding='utf-8')
        menu = Path('module/config/config_menu.py').read_text(encoding='utf-8')
        manual = Path('module/config/config_manual.py').read_text(encoding='utf-8')
        self.assertIn('from tasks.ChaoGuiWang.config import ChaoGuiWang', model)
        self.assertIn('from tasks.ChaoGuiWangAssist.config import ChaoGuiWangAssist', model)
        self.assertIn('chao_gui_wang: ChaoGuiWang', model)
        self.assertIn('chao_gui_wang_assist: ChaoGuiWangAssist', model)
        self.assertIn("'ChaoGuiWang', 'ChaoGuiWangAssist'", menu)
        self.assertIn('ChaoGuiWang > ChaoGuiWangAssist', manual)


class ChaoGuiWangI18nTests(unittest.TestCase):
    def setUp(self):
        self.zh = json.loads(Path('assets/i18n/zh-CN.json').read_text(encoding='utf-8'))

    def test_labels_translated(self):
        keys = {'ChaoGuiWang', 'chao_gui_wang_config',
                'ChaoGuiWangAssist', 'chao_gui_wang_assist_config',
                'ticket_order', 'share_friend_name'}
        for model in (ChaoGuiWangConfig, ChaoGuiWangAssistConfig):
            keys.update(model.model_fields)
        missing = sorted(key for key in keys if key not in self.zh)
        self.assertEqual(missing, [], f'缺少中文翻译: {missing}')


if __name__ == '__main__':
    unittest.main()
