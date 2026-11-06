# This Python file uses the following encoding: utf-8
"""批次 33 上游修复回归测试。

本轮可落地 7 条（零冲突直接 cherry-pick）：
1. ``bf889f02d`` + ``c08fe24f9`` 花合战先识别「任务」页签再收奖励（新增
   ``tp_task_tab.png``，ROI 在后续提交中调整为 1198,328,36,73）；
2. ``4944b3df8`` 结界卡收获奖励识别区在所有庭院皮肤下统一扩大为 750,90,250,230；
3. ``1cc1707bf`` 桌面版「激活」按钮误判防护（黄色命中还需灰色同时命中且分数更高）；
4. ``8d499033c`` 协作邀请（接受/拒绝/勾玉/忽略）重截素材并调整 ROI；
5. ``4b823fdeb`` 重新邀请时勾选框点击间隔 1→3（与 ``check_and_invite`` 对齐）；
6. ``cf9fe93ca`` 标注器上传支持选择文件夹（前端分批上传 + 去重）。

判退：``8b4dc669b`` 已覆盖（本地 ``FindJade`` 已在调度优先级表）、
``ce0e78d64`` 已覆盖（本地已按命中框动态点击「完成」下方区域）、
``940ba61b3`` 不适用（限制更新源为 xylolit-mu 官方仓库，会拒绝本 fork 的 origin）。
"""
import inspect
import json
import struct
import unittest
from pathlib import Path

from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.GlobalGame.assets import GlobalGameAssets
from tasks.KekkaiActivation.assets import KekkaiActivationAssets
from tasks.KekkaiActivation.script_task import ScriptTask as KekkaiActivationTask
from tasks.TalismanPass.script_task import ScriptTask as TalismanPassTask


def png_size(path: str) -> tuple:
    """只读 PNG 头取宽高，避免测试环境引入 Pillow 依赖。"""
    with open(path, 'rb') as f:
        header = f.read(24)
    return struct.unpack('>II', header[16:24])


class TalismanPassTaskTabTests(unittest.TestCase):
    def test_run_recognizes_task_tab_before_claiming(self):
        source = inspect.getsource(TalismanPassTask.run)
        self.assertIn('tp/tp_task_tab.png', source)
        self.assertIn('(1198, 328, 36, 73)', source)
        self.assertIn('(1185, 307, 64, 117)', source)
        self.assertIn('self.appear_then_click(task_tab)', source)

    def test_task_tab_template_size_matches_roi_front(self):
        self.assertEqual(png_size('tasks/TalismanPass/tp/tp_task_tab.png'), (36, 73))


class KekkaiHarvestRoiTests(unittest.TestCase):
    ITEMS = {
        'a_harvest_fish4': 'I_A_HARVEST_FISH4',
        'a_harvest_exp': 'I_A_HARVEST_EXP',
        'a_harvest_kaiko_4': 'I_A_HARVEST_KAIKO_4',
        'a_harvest_kaiko_3': 'I_A_HARVEST_KAIKO_3',
        'a_harvest_kaiko_6': 'I_A_HARVEST_KAIKO_6',
        'a_harvest_fish_6': 'I_A_HARVEST_FISH_6',
        'a_harvest_moon_3': 'I_A_HARVEST_MOON_3',
        'a_harvest_fish_3': 'I_A_HARVEST_FISH_3',
    }

    def test_harvest_roi_back_is_shared_expanded_region(self):
        expected = (750, 90, 250, 230)
        for attr in self.ITEMS.values():
            rule = getattr(KekkaiActivationAssets, attr)
            self.assertEqual(tuple(rule.roi_back), expected, attr)

    def test_image_json_matches_assets(self):
        data = json.loads(Path('tasks/KekkaiActivation/a/image.json').read_text(encoding='utf-8'))
        by_name = {entry['itemName']: entry for entry in data}
        for item_name, attr_name in self.ITEMS.items():
            rule = getattr(KekkaiActivationAssets, attr_name)
            entry = by_name[item_name]
            self.assertEqual(entry['roiFront'], ','.join(map(str, rule.roi_front)), item_name)
            self.assertEqual(entry['roiBack'], ','.join(map(str, rule.roi_back)), item_name)


class KekkaiActivateGuardTests(unittest.TestCase):
    def test_desktop_false_positive_guard(self):
        source = inspect.getsource(KekkaiActivationTask)
        self.assertIn('I_A_ACTIVATE_GRAY', source)
        self.assertIn('I_A_ACTIVATE_YELLOW.last_score > self.I_A_ACTIVATE_GRAY.last_score', source)


class GlobalGameInviteAssetTests(unittest.TestCase):
    EXPECTED = {
        'I_G_ACCEPT': (852, 472, 42, 50),
        'I_G_REJECT': (848, 560, 48, 50),
        'I_G_JADE': (682, 518, 32, 38),
        'I_G_IGNORE': (794, 88, 14, 16),
    }
    ITEMS = {
        'I_G_ACCEPT': 'g_accept',
        'I_G_REJECT': 'g_reject',
        'I_G_JADE': 'g_jade',
        'I_G_IGNORE': 'g_ignore',
    }

    def test_roi_front_values(self):
        for attr, expected in self.EXPECTED.items():
            self.assertEqual(tuple(getattr(GlobalGameAssets, attr).roi_front), expected, attr)

    def test_image_json_matches_assets(self):
        data = json.loads(Path('tasks/GlobalGame/gg/image.json').read_text(encoding='utf-8'))
        by_name = {entry['itemName']: entry for entry in data}
        for attr, item_name in self.ITEMS.items():
            rule = getattr(GlobalGameAssets, attr)
            entry = by_name[item_name]
            self.assertEqual(entry['roiFront'], ','.join(map(str, rule.roi_front)), item_name)
            self.assertEqual(entry['roiBack'], ','.join(map(str, rule.roi_back)), item_name)

    def test_templates_match_roi_front(self):
        for attr, expected in self.EXPECTED.items():
            rule = getattr(GlobalGameAssets, attr)
            self.assertEqual(png_size(rule.file.replace('./', '')), (expected[2], expected[3]), attr)


class GeneralInviteAgainTests(unittest.TestCase):
    def test_reinvite_uses_interval_three(self):
        source = inspect.getsource(GeneralInvite.invite_again)
        self.assertIn('self.appear_then_click(self.I_UI_UNCHECK, interval=3)', source)


if __name__ == '__main__':
    unittest.main()
