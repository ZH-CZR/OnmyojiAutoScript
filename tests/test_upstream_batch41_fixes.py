# This Python file uses the following encoding: utf-8
"""批次 41 上游修复回归测试。

本轮同步 3 条上游提交（判定明细见 ``dev_tools/upstream_sync_log.md`` §3.18）：

1. ``f99d75c2``（kongdr418/mine）：配置导入导出时 ``ConfigManager._is_model_type``
   对 ``list[Model]`` / ``dict[str, Model]`` 这类泛型注解误判 —— Python 3.9+ 下
   ``isinstance(list[X], type)`` 为 True，但 ``issubclass`` 会抛 ``TypeError``，
   导致导入含列表模型的配置时整体崩溃。
2. ``bf71e3a5``（lgg686/self）：悬赏封印「协斗」协作类型模板重做、好友邀请筛选
   放宽，并顺带调整契灵球数 OCR 区域；``assets.py`` 与 ``image.json`` 必须同步，
   模板图片文件必须存在。
3. ``844d3bec``（lgg686/self）：交换身份（handoff1/handoff2）应在**单次任务内**
   先跑一半队长再跑一半队员（反之亦然），两段合计 ``limit_count``；
   队员段与抓捕循环都必须受次数上限约束。
"""
import json
import os
import re
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from pydantic import BaseModel

from module.exception import TaskEnd
from module.server.config_manager import ConfigManager
from tasks.BondlingFairyland.config import BondlingClass, BondlingMode, UserStatus
from tasks.BondlingFairyland.script_task import ScriptTask

REGEX_RULE = re.compile(
    r"^\s*(\w+) = RuleImage\(roi_front=\(([^)]*)\), roi_back=\(([^)]*)\), "
    r"threshold=([0-9.]+), method=\"([^\"]*)\"(?:, profile=\"[^\"]*\")?, file=\"([^\"]*)\"\)\s*$"
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _DemoModel(BaseModel):
    value: int = 0


class ConfigAnnotationTests(unittest.TestCase):
    """``f99d75c2``：泛型注解不能再让配置导入抛 TypeError。"""

    def test_model_type_is_recognized(self):
        self.assertTrue(ConfigManager._is_model_type(_DemoModel))

    def test_generic_annotations_are_not_treated_as_model(self):
        for annotation in (List[_DemoModel], Dict[str, _DemoModel], Optional[_DemoModel], Any):
            with self.subTest(annotation=annotation):
                self.assertFalse(ConfigManager._is_model_type(annotation))

    def test_plain_types_are_not_treated_as_model(self):
        for annotation in (str, int, list, None):
            with self.subTest(annotation=annotation):
                self.assertFalse(ConfigManager._is_model_type(annotation))

    def test_list_item_model_still_resolves(self):
        self.assertIs(ConfigManager._list_item_model(List[_DemoModel]), _DemoModel)
        self.assertIsNone(ConfigManager._list_item_model(_DemoModel))


class BondlingHandoffTests(unittest.TestCase):
    """``844d3bec``：交换身份半量切换与终止流程。"""

    @staticmethod
    def _make_task(user_status: UserStatus, limit_count: int = 10):
        task = ScriptTask.__new__(ScriptTask)
        task.config = SimpleNamespace(
            bondling_fairyland=SimpleNamespace(
                battle_config=SimpleNamespace(),
                bondling_config=SimpleNamespace(
                    check_enable=False,
                    bondling_mode=BondlingMode.MODE2,
                    user_status=user_status,
                    limit_count=limit_count,
                    bondling_stone_class=BondlingClass.TOMB_GUARD,
                ),
            )
        )
        task.calls = []

        def record(name, *extra):
            task.calls.append((name, task.limit_count, task.current_count, *extra))

        task.switch_soul = lambda: record('switch_soul')
        task.goto_page = lambda page, **kwargs: record('goto_page', page)
        task.goto_ball_area = lambda index: record('goto_ball_area', index)
        task.switch_ball = lambda: record('switch_ball')
        task.run_member = lambda: record('run_member')
        task.run_search = lambda *a, **k: record('run_search')
        task.set_next_run = lambda **kwargs: record('set_next_run', kwargs)
        return task

    def test_handoff1_runs_leader_then_member_with_half_limit(self):
        task = self._make_task(UserStatus.handoff1)
        with patch.object(BondlingClass, 'get_index', return_value=1):
            with self.assertRaises(TaskEnd):
                task.run()

        names = [c[0] for c in task.calls]
        self.assertIn('switch_ball', names)
        self.assertIn('run_member', names)
        self.assertLess(names.index('switch_ball'), names.index('run_member'))

        switch_ball = next(c for c in task.calls if c[0] == 'switch_ball')
        run_member = next(c for c in task.calls if c[0] == 'run_member')
        # 队长段限次 5，队员段限次 5（合计 10），两段之间计数清零
        self.assertEqual(switch_ball[1], 5)
        self.assertEqual(switch_ball[2], 0)
        self.assertEqual(run_member[1], 5)
        self.assertEqual(run_member[2], 0)

        finish = task.calls[-1]
        self.assertEqual(finish[0], 'set_next_run')
        self.assertTrue(finish[3]['finish'])
        self.assertTrue(finish[3]['success'])

    def test_handoff2_runs_member_then_leader_with_half_limit(self):
        task = self._make_task(UserStatus.handoff2)
        with patch.object(BondlingClass, 'get_index', return_value=1):
            with self.assertRaises(TaskEnd):
                task.run()

        names = [c[0] for c in task.calls]
        self.assertLess(names.index('run_member'), names.index('switch_ball'))
        switch_ball = next(c for c in task.calls if c[0] == 'switch_ball')
        run_member = next(c for c in task.calls if c[0] == 'run_member')
        self.assertEqual(switch_ball[1], 5)
        self.assertEqual(run_member[1], 5)
        self.assertEqual(switch_ball[2], 0)

    def test_single_status_keeps_full_limit(self):
        for status, expected in ((UserStatus.ALONE, 'switch_ball'), (UserStatus.LEADER, 'switch_ball'),
                                 (UserStatus.MEMBER, 'run_member')):
            with self.subTest(status=status):
                task = self._make_task(status)
                with patch.object(BondlingClass, 'get_index', return_value=1):
                    with self.assertRaises(TaskEnd):
                        task.run()
                call = next(c for c in task.calls if c[0] == expected)
                self.assertEqual(call[1], 10)

    def test_switch_ball_exits_immediately_when_count_reached(self):
        # 不复用 _make_task：这里要跑真实的 switch_ball，验证循环入口的次数上限判断
        task = ScriptTask.__new__(ScriptTask)
        task.config = SimpleNamespace(
            bondling_fairyland=SimpleNamespace(
                battle_config=SimpleNamespace(),
                bondling_config=SimpleNamespace(bondling_stone_class=BondlingClass.TOMB_GUARD),
            )
        )
        task.current_count = 10
        task.limit_count = 10
        task.calls = []
        task.in_search_ui = lambda **kwargs: self.fail('次数已满仍继续搜索契灵')
        with patch.object(BondlingClass, 'get_index', return_value=1):
            task.switch_ball()


class AssetConsistencyTests(unittest.TestCase):
    """``bf71e3a5``：模板、ROI 与 JSON 导出必须一致。"""

    PAIRS = [
        ('tasks/GlobalGame/assets.py', 'tasks/GlobalGame/gg/image.json'),
        ('tasks/WantedQuests/assets.py', 'tasks/WantedQuests/invite/image.json'),
    ]

    @staticmethod
    def _read_rules(py_path):
        rules = {}
        with open(os.path.join(ROOT, py_path), encoding='utf-8') as f:
            for line in f:
                m = REGEX_RULE.match(line)
                if m:
                    rules[m.group(1).lower().removeprefix('i_')] = {
                        'roi_front': m.group(2),
                        'roi_back': m.group(3),
                        'threshold': float(m.group(4)),
                        'file': m.group(6),
                    }
        return rules

    def test_assets_py_matches_image_json(self):
        for py_path, json_path in self.PAIRS:
            rules = self._read_rules(py_path)
            with open(os.path.join(ROOT, json_path), encoding='utf-8') as f:
                items = {item['itemName']: item for item in json.load(f)}
            checked = 0
            for name, rule in rules.items():
                item = items.get(name)
                if item is None:
                    continue
                checked += 1
                with self.subTest(source=py_path, rule=name):
                    self.assertEqual(item['roiFront'], rule['roi_front'])
                    self.assertEqual(item['roiBack'], rule['roi_back'])
                    self.assertAlmostEqual(item['threshold'], rule['threshold'], places=6)
            self.assertGreater(checked, 0, f'{py_path} 与 JSON 没有可比对的条目')

    # 仅校验本批次改动过的资源：其它规则存在历史遗留（点击用 ROI 不依赖模板图片）
    TOUCHED = {
        'tasks/GlobalGame/assets.py': {'g_jade', 'g_cat_food', 'g_dog_food'},
        'tasks/WantedQuests/assets.py': {'wq_invite_1', 'wq_invite_2', 'wq_invite_3'} | {
            f'wq_cooperation_type_{kind}_{idx}'
            for kind in ('gold', 'jade', 'sushi', 'cat_food', 'dog_food') for idx in (1, 2, 3)
        },
    }

    def test_template_files_exist(self):
        for py_path, names in self.TOUCHED.items():
            rules = self._read_rules(py_path)
            for name in names:
                self.assertIn(name, rules, f'{py_path} 缺少 {name}')
                path = os.path.join(ROOT, rules[name]['file'].lstrip('./').replace('/', os.sep))
                with self.subTest(source=py_path, rule=name):
                    self.assertTrue(os.path.isfile(path), path)
                    self.assertGreater(os.path.getsize(path), 0, path)

    def test_cooperation_templates_use_body_crop(self):
        # 协斗协作类型图标改为整卡识别：roi_back 必须比 roi_front 大
        rules = self._read_rules('tasks/WantedQuests/assets.py')
        for name in sorted(n for n in self.TOUCHED['tasks/WantedQuests/assets.py']
                           if n.startswith('wq_cooperation_type_')):
            rule = rules[name]
            with self.subTest(rule=name):
                front = [int(v) for v in rule['roi_front'].split(',')]
                back = [int(v) for v in rule['roi_back'].split(',')]
                self.assertGreater(back[2], front[2])
                self.assertGreater(back[3], front[3])

    def test_bondling_ball_number_ocr_matches_json(self):
        rules = self._read_rules('tasks/BondlingFairyland/assets.py')
        self.assertNotIn('b_ball_number', rules)  # RuleOcr 不在 RuleImage 正则范围内
        with open(os.path.join(ROOT, 'tasks/BondlingFairyland/bf/ocr.json'), encoding='utf-8') as f:
            items = {item['itemName']: item for item in json.load(f)}
        self.assertEqual(items['b_ball_number']['roiFront'], '1183,666,68,27')
        self.assertEqual(items['b_ball_number']['roiBack'], '1183,666,68,27')


if __name__ == '__main__':
    unittest.main()
