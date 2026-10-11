# This Python file uses the following encoding: utf-8
"""重连守卫（``BaseTask._wait_if_reconnecting``）的回归测试。

背景
----
提交 ``f5a0891a feat(GameUi): 重连弹窗等待与未知页强制重启兜底`` 在
``BaseTask.screenshot()`` 收口处加了「正在连接……」重连等待，判据是 OCR 规则
``GlobalGameAssets.O_UI_CONNECTING``（``keyword="连接"`` + ``mode="Full"``，
roi 为屏幕中央一带）。

缺陷
----
``RuleOcr.filter()`` 在「完整关键词」匹配不到时会退化成**单字兜底**：keyword 里
任意一个「单字」出现在 OCR 文本里就算命中（见 ``module/ocr/base_ocr.py`` 中
``filter`` 的单字分支及其 TODO）。于是 ``O_UI_CONNECTING`` 只要碰到含「连」或
「接」的文字就会误报：

* 吉闻「一键祝福」弹窗的输入框文字「欧运连连」→ 命中「连」；
* 任意「接受 / 直接 / 连接中……」弹窗 → 命中「接」。

一旦误报，守卫就会原地等待、不再点击，设备层约 74s 后抛 ``GameStuckError``。

实例：2026-10-11 08:11:53 ``少时之约`` DailyTrifles 卡死。

本测试钉死不变量：守卫判据必须能区分「真正的重连弹窗」与「仅含单个关键词字的
普通弹窗」。若某天把 ``O_UI_CONNECTING`` 改回宽松匹配，这些用例会立刻变红。
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from module.ocr.base_ocr import OcrMode
from tasks.GlobalGame.assets import GlobalGameAssets
from tasks.base_task import BaseTask


def _boxes(*texts):
    """构造 ``filter()`` 需要的 BoxedResult 形状（只需要 ``ocr_text`` 字段）。"""
    return [SimpleNamespace(ocr_text=t) for t in texts]


def guard_detects(rule, texts) -> bool:
    """按 ``BaseTask.ocr_appear`` 的语义，判断这些 OCR 文本是否会被判为「重连中」。

    仅覆盖守卫用到的两种模式（FULL / SINGLE），其余模式与本守卫无关。
    """
    if not rule.keyword:
        return False
    if rule.mode == OcrMode.FULL:
        return rule.filter(_boxes(*texts)) is not None
    if rule.mode == OcrMode.SINGLE:
        return ''.join(texts) == rule.keyword
    return False


class ReconnectRuleMatchingTests(unittest.TestCase):
    """``O_UI_CONNECTING`` 的匹配判据。"""

    def setUp(self):
        self.rule = GlobalGameAssets.O_UI_CONNECTING

    def test_real_reconnect_banner_is_detected(self):
        """真正的重连弹窗（「正在连接」）必须命中。"""
        self.assertTrue(guard_detects(self.rule, ['正在连接']))

    def test_luck_msg_input_is_not_detected(self):
        """吉闻「一键祝福」输入框文字「欧运连连」不得被判为断线重连。"""
        self.assertFalse(guard_detects(self.rule, ['欧运连连']))

    def test_generic_accept_dialog_is_not_detected(self):
        """只含单个关键词字（如「接受」）的普通弹窗不得被判为断线重连。"""
        self.assertFalse(guard_detects(self.rule, ['接受好友请求']))

    def test_lone_keyword_char_is_not_detected(self):
        """孤立的关键词单字本身不构成重连证据。"""
        self.assertFalse(guard_detects(self.rule, ['连']))
        self.assertFalse(guard_detects(self.rule, ['接']))


class _GuardProbe(BaseTask):
    """绕过真实 Config / Device 的守卫探针。"""

    RECONNECT_CHECK_INTERVAL = 0.0
    RECONNECT_MAX_WAIT = 30.0

    def __init__(self, connecting: bool):
        self.connecting = connecting
        self._reconnect_last_check = 0.0
        self.screenshots = 0
        self.cleared = 0
        self.device = SimpleNamespace(
            click_record_clear=self._clear,
            stuck_record_clear=self._clear,
            screenshot=self._shot,
        )

    def _clear(self):
        self.cleared += 1

    def _shot(self):
        self.screenshots += 1

    def ocr_appear(self, target, interval=None):
        return self.connecting


class ReconnectGuardBehaviorTests(unittest.TestCase):
    """守卫在「非重连」帧上必须零副作用；在「重连」帧上要先清理点击/卡死记录。"""

    def _run(self, probe):
        # 让计时器立刻到达，避免真实等待。
        with patch('tasks.base_task.Timer') as timer_cls:
            timer_cls.return_value.start.return_value.reached.return_value = True
            probe._wait_if_reconnecting()

    def test_no_side_effect_when_not_connecting(self):
        """未命中重连时，守卫直接返回，不截图、不清理记录。"""
        probe = _GuardProbe(connecting=False)
        self._run(probe)
        self.assertEqual(probe.cleared, 0)
        self.assertEqual(probe.screenshots, 0)

    def test_clears_records_when_connecting(self):
        """命中重连时，守卫先清理点击/卡死记录，避免重连期间无效点击累积。"""
        probe = _GuardProbe(connecting=True)
        self._run(probe)
        self.assertGreaterEqual(probe.cleared, 2)  # click_record_clear + stuck_record_clear


if __name__ == '__main__':
    unittest.main()