# This Python file uses the following encoding: utf-8
"""斗技「寻龙逐奕」小白弹窗阻塞导航的回归测试。

背景
----
进入斗技主界面会弹出「可兑换增益道具」的模态弹窗（小白），弹窗会吞掉
左上角 ``UI_UI_BACK_YELLOW`` 与战斗按钮的点击。此前只有
``Duel.switch_all_soul`` 内部会关闭它；任务开始时若正停在斗技页，
``page_duel -> page_town`` 会反复失败（导航 penalty 递增）直到
``GameTooManyClickError``。

修复方式是把关闭动作挂到全局 ``page_duel`` 的进入成功 / 离开失败 hook，
条件为 ``DuelAssets.I_WHITE_DOG``。本测试钉死：资产可用、hook 已挂载且
条件正确、弹窗存在时点左侧空白（与 ``switch_all_soul`` 同一区域）。
"""
import unittest
from pathlib import Path

import cv2
import numpy as np

from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.Duel.assets import DuelAssets
from tasks.GameUi.action import ConditionalAction
from tasks.GameUi.page import page_duel
from tasks.GameUi.default_pages import close_duel_buff_popup

REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeTask:
    """只提供 hook 需要的 ``appear`` / ``click``。"""

    def __init__(self, visible=()):
        self.visible = set(visible)
        self.clicks = []

    def appear(self, button, **kwargs):
        return button in self.visible

    def click(self, click, interval=None, **kwargs):
        self.clicks.append(click)
        return True


class DuelWhiteDogAssetTests(unittest.TestCase):
    def test_asset_is_defined(self):
        self.assertTrue(hasattr(DuelAssets, "I_WHITE_DOG"))

    def test_template_file_matches_roi_front(self):
        rule = DuelAssets.I_WHITE_DOG
        path = REPO_ROOT / rule.file.lstrip("./")
        self.assertTrue(path.exists(), f"模板文件缺失: {path}")

        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        self.assertIsNotNone(image, "模板图无法解码")
        height, width = image.shape[:2]
        self.assertEqual((width, height), (rule.roi_front[2], rule.roi_front[3]))


class DuelWhiteDogHookTests(unittest.TestCase):
    @staticmethod
    def _popup_hooks(stage: str):
        hooks = page_duel.hooks(stage)
        return [
            hook for hook in hooks
            if isinstance(hook, ConditionalAction) and hook.action is close_duel_buff_popup
        ]

    def test_enter_success_hook_installed(self):
        self.assertEqual(len(self._popup_hooks("on_enter_success")), 1)

    def test_leave_failure_hook_installed(self):
        self.assertEqual(len(self._popup_hooks("on_leave_failure")), 1)

    def test_hook_condition_matches_popup_only(self):
        for stage in ("on_enter_success", "on_leave_failure"):
            hook = self._popup_hooks(stage)[0]
            self.assertTrue(hook.condition.evaluate(_FakeTask({DuelAssets.I_WHITE_DOG})))
            self.assertFalse(hook.condition.evaluate(_FakeTask()))

    def test_helper_clicks_left_blank_area(self):
        task = _FakeTask({DuelAssets.I_WHITE_DOG})
        self.assertTrue(close_duel_buff_popup(task))
        self.assertEqual(len(task.clicks), 1)
        self.assertEqual(task.clicks[0].roi_front, GeneralBattleAssets.C_RANDOM_LEFT.roi_front)


if __name__ == '__main__':
    unittest.main()
