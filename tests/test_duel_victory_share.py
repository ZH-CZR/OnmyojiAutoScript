# This Python file uses the following encoding: utf-8
"""批次 21「斗技 MVP 分享页识别」的回归测试。

背景
----
上游 ``d638c11f``（PR #1923）发现 ``is_battle_win`` 漏判「胜利 MVP 分享页」
（该页没有 ``I_WIN`` / ``I_D_VICTORY``），于是新增 ``I_D_VICTORY_SHARE``
并在 ``is_battle_win`` 里追加判断。

上游用 ``Masked template matching``（掩码剔除雾化左缘），但本地匹配框架
（图像服务 RPC）只认 ``Template matching`` / ``Multi-scale template matching``
/ ``Sift Flann``，未知 method 会直接 ``raise ValueError``。因此本地落地时
**裁剪掉被掩码的雾化左缘**，改用普通 ``Template matching``。

本测试钉死这些不变量：资产存在且 method 为本地可用的普通模板匹配（防止
回退到会抛错的掩码方法）、模板尺寸与 ``roi_front`` 一致、JSON 元数据同步、
``is_battle_win`` 命中分享页且原有胜利判定不受影响。
"""
import json
import unittest
from pathlib import Path

import cv2
import numpy as np

from tasks.Duel.assets import DuelAssets
from tasks.Duel.script_task import ScriptTask

REPO_ROOT = Path(__file__).resolve().parents[1]


class _ScriptedDuelWin(ScriptTask):
    """绕过 Config / Device，仅用手动声明的可见资产驱动 ``is_battle_win``。"""

    def __init__(self, visible):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.visible = set(visible)

    def appear(self, button, **kwargs):
        return button in self.visible


class DuelVictoryShareAssetTests(unittest.TestCase):
    def test_asset_is_defined(self):
        self.assertTrue(hasattr(DuelAssets, "I_D_VICTORY_SHARE"))

    def test_asset_uses_supported_template_matching(self):
        # 本地框架不支持 "Masked template matching"，否则运行期 raise ValueError。
        rule = DuelAssets.I_D_VICTORY_SHARE
        self.assertEqual(rule.method, "Template matching")

    def test_template_file_matches_roi_front(self):
        rule = DuelAssets.I_D_VICTORY_SHARE
        path = REPO_ROOT / rule.file.lstrip("./")
        self.assertTrue(path.exists(), f"模板文件缺失: {path}")

        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        self.assertIsNotNone(image, "模板图无法解码")
        height, width = image.shape[:2]
        self.assertEqual((width, height), (rule.roi_front[2], rule.roi_front[3]))

    def test_image_json_entry_uses_supported_method(self):
        with (REPO_ROOT / "tasks/Duel/duel/image.json").open(encoding="utf-8") as fp:
            entries = {entry["itemName"]: entry for entry in json.load(fp)}

        self.assertIn("d_victory_share", entries)
        self.assertEqual(entries["d_victory_share"]["method"], "Template matching")


class DuelBattleWinTests(unittest.TestCase):
    def test_share_page_counts_as_win(self):
        task = _ScriptedDuelWin({ScriptTask.I_D_VICTORY_SHARE})
        self.assertTrue(task.is_battle_win())

    def test_plain_victory_still_counts_as_win(self):
        task = _ScriptedDuelWin({ScriptTask.I_D_VICTORY})
        self.assertTrue(task.is_battle_win())

    def test_no_win_assets_is_not_a_win(self):
        task = _ScriptedDuelWin(set())
        self.assertFalse(task.is_battle_win())


if __name__ == '__main__':
    unittest.main()