# This Python file uses the following encoding: utf-8
"""斗技「增益道具兑换」弹窗阻塞导航的回归测试。

背景
----
进入斗技主界面时会弹出「可兑换增益道具」提示（按钮为“开心收下”）。该弹窗是
模态的，但不会遮挡 ``I_CHECK_DUEL`` 等页面识别元素，因此导航器仍判定当前页为
``page_duel``，随后反复点击左上角返回键；点击次数达到上限后抛出
``GameTooManyClickError``，任务在“离开斗技页”时卡死。

上游 ``7114d0cf3`` 只处理了另一种「斗技入口附属消息页」（模板与本弹窗实测匹配
分仅 0.47），不能覆盖此界面，故本地补一条 OCR 识别 + 关闭逻辑。

本测试钉死：
1. OCR 资产与 ``ocr.json`` 元数据一致，且用 ``Full`` 子串匹配（不依赖全等）；
2. ``dismiss_duel_gain_popup`` 命中时点击“开心收下”，未命中时不做任何点击；
3. ``page_duel`` 的进入成功与离开失败 hook 都挂载了该关闭动作。
"""
import json
import unittest
from pathlib import Path

from module.ocr.base_ocr import OcrMode
from tasks.Duel.assets import DuelAssets
from tasks.Duel.script_task import ScriptTask
from tasks.GameUi.page import page_duel

REPO_ROOT = Path(__file__).resolve().parents[1]


class DuelGainPopupAssetTests(unittest.TestCase):
    def test_asset_is_defined(self):
        self.assertTrue(hasattr(DuelAssets, "O_D_GAIN_POPUP_CLOSE"))

    def test_asset_uses_full_substring_match(self):
        rule = DuelAssets.O_D_GAIN_POPUP_CLOSE
        self.assertEqual(rule.mode, OcrMode.FULL)
        self.assertEqual(rule.keyword, "开心收下")
        self.assertEqual(rule.roi, [735, 490, 220, 60])

    def test_ocr_json_entry_matches_asset(self):
        with (REPO_ROOT / "tasks/Duel/duel/ocr.json").open(encoding="utf-8") as fp:
            entries = {entry["itemName"]: entry for entry in json.load(fp)}

        self.assertIn("d_gain_popup_close", entries)
        entry = entries["d_gain_popup_close"]
        self.assertEqual(entry["mode"], "Full")
        self.assertEqual(entry["keyword"], "开心收下")
        self.assertEqual(entry["roiFront"], "735,490,220,60")


class _ScriptedDuelPopup(ScriptTask):
    """绕过 Config / Device，仅驱动弹窗关闭分支。"""

    def __init__(self, visible):
        self.visible = visible
        self.clicked = []

    def appear(self, rule, **kwargs):
        return rule in self.visible

    def click(self, rule, **kwargs):
        self.clicked.append(rule)
        return True


class DuelGainPopupDismissTests(unittest.TestCase):
    def test_click_close_button_when_popup_visible(self):
        task = _ScriptedDuelPopup({ScriptTask.O_D_GAIN_POPUP_CLOSE})
        self.assertTrue(task.dismiss_duel_gain_popup())
        self.assertEqual(task.clicked, [ScriptTask.O_D_GAIN_POPUP_CLOSE])

    def test_no_click_when_popup_absent(self):
        task = _ScriptedDuelPopup(set())
        self.assertFalse(task.dismiss_duel_gain_popup())
        self.assertEqual(task.clicked, [])


class PageDuelHookTests(unittest.TestCase):
    def test_enter_and_leave_failure_hooks_installed(self):
        rule = DuelAssets.O_D_GAIN_POPUP_CLOSE
        self.assertIn(rule, page_duel.on_enter_success)
        self.assertIn(rule, page_duel.on_leave_failure)


if __name__ == '__main__':
    unittest.main()
