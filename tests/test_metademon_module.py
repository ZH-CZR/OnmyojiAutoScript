# This Python file uses the following encoding: utf-8
"""超鬼王（MetaDemon）新代际模块回归测试。

2026-11-11 用上游 `nearaura/dev`（`a86b0e50`）整体替换了本地旧代际的
`tasks/MetaDemon`。这里锁定三件事：

1. 资产与图片可加载：`assets.py` 引用的每张 png 都在，且与
   `md/image.json` / `md/image_2025.json` 的 ROI、阈值一致；
2. 配置模型：默认值、`auto_tea` 强制 False、策略列表的展开/拍平；
3. 脚本入口：新代际依赖的方法与继承链没有被后续同步误删。

旧代际（`md_md_*`、`goto_metademon_list.json`、门票合成/邀请好友）已按
「以最新上游为准」删除，这里同时断言它们不会回来。
"""
import json
import unittest
from pathlib import Path

from module.atom.image import RuleImage
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.RightActivity.right_activity import RightActivity
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemon.config import MetaDemon, Strategy
from tasks.MetaDemon.script_task import ScriptTask

MD_DIR = Path('tasks/MetaDemon/md')


def _image_rules():
    return {
        name: value
        for name, value in vars(MetaDemonAssets).items()
        if isinstance(value, RuleImage)
    }


def _json_entries():
    entries = {}
    for filename in ('image.json', 'image_2025.json'):
        for entry in json.loads((MD_DIR / filename).read_text(encoding='utf-8')):
            entries[entry['imageName']] = entry
    return entries


class MetaDemonAssetTests(unittest.TestCase):
    def test_every_rule_image_exists(self):
        rules = _image_rules()
        self.assertGreater(len(rules), 10)
        for name, rule in rules.items():
            self.assertTrue(Path(rule.file).is_file(), f'{name} -> {rule.file}')

    def test_rule_matches_image_json(self):
        entries = _json_entries()
        for name, rule in _image_rules().items():
            image_name = Path(rule.file).name
            self.assertIn(image_name, entries, name)
            entry = entries[image_name]
            self.assertEqual(entry['roiFront'], ','.join(map(str, rule.roi_front)), name)
            self.assertEqual(entry['threshold'], rule.threshold, name)

    def test_public_boss_rules(self):
        # 11-10 上游新增：先判「已公开」，再判「集结」
        self.assertEqual(MetaDemonAssets.I_BOOS_PUBLIC.threshold, 0.8)
        self.assertEqual(
            tuple(MetaDemonAssets.I_BOOS_PUBLIC.roi_back),
            tuple(MetaDemonAssets.I_BOSS_CONVENE.roi_back),
        )
        for name in ('I_BOSS_EMPTY', 'I_BOSS_EMPTY_1', 'I_BOSS_EMPTY_2', 'O_BOSS_EMPTY_1'):
            self.assertTrue(hasattr(MetaDemonAssets, name), name)

    def test_star56_rules(self):
        for name in ('I_STAR56_POS_1', 'I_STAR56_HP_THRESHOLD_T', 'I_STAR56_HP_THRESHOLD_F'):
            self.assertTrue(hasattr(MetaDemonAssets, name), name)
        self.assertEqual(MetaDemonAssets.O_MD_FULL_NAME.mode.name, 'FULL')
        self.assertEqual(MetaDemonAssets.O_MD_EXHAUSTION.mode.name, 'DIGITCOUNTER')

    def test_old_generation_removed(self):
        for name in ('I_MD_FIRE', 'I_MD_SUMMON_BOSS', 'I_MD_SYNTHESIS', 'I_MD_INVITE_FRIENDS'):
            self.assertFalse(hasattr(MetaDemonAssets, name), name)
        self.assertFalse((MD_DIR / 'goto_metademon_list.json').exists())
        self.assertFalse((MD_DIR / 'md_md_fire.png').exists())


class MetaDemonConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = MetaDemon()
        self.assertTrue(config.meta_demon_config.meta_crafting_card)
        self.assertFalse(config.meta_demon_config.auto_tea)
        self.assertEqual(config.meta_demon_config.md_strategy_count, 0)
        self.assertFalse(config.meta_demon_config.md_use_strategy)
        self.assertEqual(config.md_default_strategy.md_preset_group_team_default_1, '1,1')

    def test_auto_tea_forced_false(self):
        config = MetaDemon(meta_demon_config={'auto_tea': True})
        self.assertFalse(config.meta_demon_config.auto_tea)

    def test_parse_names_and_group_team(self):
        self.assertEqual(Strategy.parse_names('御撰津，千姬 阿修罗'), ['御撰津', '千姬阿修罗'])
        self.assertEqual(Strategy.parse_group_team('2，3'), [2, 3])
        with self.assertRaises(Exception):
            Strategy.parse_group_team('0,1')
        with self.assertRaises(Exception):
            Strategy.parse_group_team('1,6')
        with self.assertRaises(Exception):
            Strategy.parse_group_team('1')

    def test_parse_all(self):
        data = [
            Strategy(md_match_names='御撰津,千姬', md_preset_group_team_1='2,3', md_preset_group_team_2='4,5'),
        ]
        self.assertEqual(
            Strategy.parse_all(data),
            {'御撰津': [2, 3, 4, 5], '千姬': [2, 3, 4, 5]},
        )

    def test_strategies_flatten_and_expand(self):
        config = MetaDemon(
            meta_demon_config={'md_strategy_count': 2},
            md_strategies_1={'md_match_names': 'A'},
            md_strategies_2={'md_match_names': 'B'},
        )
        self.assertEqual([item.md_match_names for item in config.md_strategies], ['A', 'B'])
        dumped = config.model_dump()
        self.assertEqual(dumped['md_strategies_1']['md_match_names'], 'A')
        self.assertEqual(dumped['md_strategies_2']['md_match_names'], 'B')


class MetaDemonTaskTests(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(ScriptTask, GeneralBattle))
        self.assertTrue(issubclass(ScriptTask, RightActivity))
        self.assertTrue(issubclass(ScriptTask, MetaDemonAssets))

    def test_entrypoints(self):
        for name in ('run', 'crafting', 'battle_boss', 'find_demon', 'current_exhaustion', 'battle_wait'):
            self.assertTrue(callable(getattr(ScriptTask, name, None)), name)


if __name__ == '__main__':
    unittest.main()
