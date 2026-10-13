# This Python file uses the following encoding: utf-8
"""断线守卫（``BaseTask._wait_if_disconnected``）的回归测试。

背景
----
2026-10-13 08:01 KekkaiUtilize（结界突破）任务卡死：游戏弹出模态弹窗
「已断开游戏服务器，需要重新连接」，该弹窗吞掉全部点击并阻塞页面导航。框架既未
识别也未关闭它，导航 ``page_main -> page_guild`` 连续失败 5 次、penalty 从 1.0 累加
到 5.0，最终抛 ``GamePageUnknownError``（日志 ``Game page unknown``）导致任务失败。

上游（runhey/OnmyojiAutoScript，dev/master/self 各分支）在 ``BaseTask.screenshot``
中仅留有被注释掉的兜底::

    # if self.appear(self.I_NETWORK_ERROR):
    #     logger.warning(f"Network error")
    #     raise GameStuckError

即上游并没有启用任何处理方案；本地 ``tasks/GlobalGame/gg/gg_network_error.png``
（``I_NETWORK_ERROR``）与 ``gg_network_abnormal.png``（``I_NETWORK_ABNORMAL``）长期
处于「有资产、无引用」的悬挂状态。查证结论：本问题在上游无现成可移植方案，故本地
自行补齐。

修复
----
在 ``screenshot`` 收口处新增 ``_wait_if_disconnected``：用 ``I_NETWORK_ERROR`` 模板
命中该弹窗后，反复点击弹窗内的「确定」按钮（``C_NETWORK_ERROR_CONFIRM``）并等待弹窗
消失，从而触发游戏自带的重连；期间清理点击/卡死记录，避免点击守卫误伤。与「正在
连接……」的 ``_wait_if_reconnecting`` 互为补充。

本测试钉死不变量：
1. 「确定」按钮落点必须位于弹窗识别 roi 内部（否则识别到了却点不中）；
2. 未出现弹窗时守卫零副作用；
3. 出现弹窗时会点击确定并清理记录，弹窗消失后立即返回；
4. ``screenshot`` 收口确实接入了该守卫。
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from module.atom.click import RuleClick
from module.atom.image import RuleImage
from tasks.GlobalGame.assets import GlobalGameAssets
from tasks.base_task import BaseTask


class DisconnectAssetTests(unittest.TestCase):
    """断线弹窗的检测/点击资产必须存在且几何自洽。"""

    def test_assets_exist(self):
        self.assertIsInstance(GlobalGameAssets.I_NETWORK_ERROR, RuleImage)
        self.assertIsInstance(GlobalGameAssets.C_NETWORK_ERROR_CONFIRM, RuleClick)

    def test_network_error_template_file_exists(self):
        path = GlobalGameAssets.I_NETWORK_ERROR.file
        self.assertTrue(os.path.exists(path), f'missing template {path}')

    def test_confirm_point_inside_popup(self):
        """「确定」落点必须落在弹窗识别 roi 内部, 否则识别到了也点不中。"""
        x, y, w, h = GlobalGameAssets.I_NETWORK_ERROR.roi_front
        cx, cy = GlobalGameAssets.C_NETWORK_ERROR_CONFIRM.center
        self.assertTrue(x <= cx <= x + w, f'confirm x {cx} outside popup [{x}, {x + w}]')
        self.assertTrue(y <= cy <= y + h, f'confirm y {cy} outside popup [{y}, {y + h}]')


class _DisconnectProbe(BaseTask):
    """绕过真实 Config / Device 的守卫探针。"""

    DISCONNECT_CHECK_INTERVAL = 0.0
    DISCONNECT_MAX_WAIT = 30.0

    def __init__(self, appear_sequence):
        # appear() 依次消费的返回值; 用尽后一律返回 False, 避免测试死循环。
        self._appear_sequence = list(appear_sequence)
        self._disconnect_last_check = 0.0
        self.clicks = []
        self.cleared = 0
        self.screenshots = 0
        self.device = SimpleNamespace(
            image=None,
            click_record_clear=self._clear,
            stuck_record_clear=self._clear,
            screenshot=self._shot,
            click=self._click,
        )

    def _clear(self):
        self.cleared += 1

    def _shot(self):
        self.screenshots += 1

    def _click(self, x, y, **kwargs):
        self.clicks.append((x, y))

    def appear(self, target, interval=None, threshold=None):
        if not self._appear_sequence:
            return False
        return self._appear_sequence.pop(0)


class DisconnectGuardBehaviorTests(unittest.TestCase):
    """守卫在「非断线」帧上必须零副作用; 在「断线」帧上要点击确定并清理记录。"""

    def _run(self, probe):
        # 屏蔽真实等待, 保持测试快速。
        with patch('tasks.base_task.sleep'):
            probe._wait_if_disconnected()

    def test_no_side_effect_without_popup(self):
        """未命中断线弹窗时, 守卫直接返回, 不点击、不截图、不清理记录。"""
        probe = _DisconnectProbe([False])
        self._run(probe)
        self.assertEqual(probe.clicks, [])
        self.assertEqual(probe.cleared, 0)
        self.assertEqual(probe.screenshots, 0)

    def test_clicks_confirm_and_clears_records(self):
        """命中后点击确定, 并清理点击/卡死记录, 弹窗消失即返回。"""
        probe = _DisconnectProbe([True, True, False])
        self._run(probe)
        self.assertEqual(len(probe.clicks), 1)
        # click_record_clear + stuck_record_clear + 恢复后的 click_record_clear
        self.assertGreaterEqual(probe.cleared, 3)
        self.assertEqual(probe.screenshots, 1)

    def test_click_point_inside_popup_roi(self):
        """实际点击点仍应落在弹窗识别 roi 内。"""
        probe = _DisconnectProbe([True, True, False])
        self._run(probe)
        x, y, w, h = GlobalGameAssets.I_NETWORK_ERROR.roi_front
        cx, cy = probe.clicks[0]
        self.assertTrue(x <= cx <= x + w)
        self.assertTrue(y <= cy <= y + h)

    def test_reclicks_while_popup_persists(self):
        """弹窗未消失（网络仍未恢复）时会再次点击确认。"""
        # 每次循环消耗两次 appear: appear_then_click 一次 + 截图后复核一次
        probe = _DisconnectProbe([True, True, True, True, False])
        self._run(probe)
        self.assertEqual(len(probe.clicks), 2)

    def test_throttled_between_checks(self):
        """检测节流: 距离上次检测不足间隔时直接返回, 不重复匹配。"""
        probe = _DisconnectProbe([True, True, False])
        probe.DISCONNECT_CHECK_INTERVAL = 1000.0
        self._run(probe)
        self.assertEqual(len(probe.clicks), 1)
        # 第二次调用被节流, 不再产生点击
        probe._appear_sequence = [True, True, False]
        self._run(probe)
        self.assertEqual(len(probe.clicks), 1)


class ScreenshotHookTests(unittest.TestCase):
    """``screenshot`` 收口必须接入断线守卫。"""

    def test_screenshot_invokes_disconnect_guard(self):
        probe = _DisconnectProbe([])
        with patch.object(BaseTask, '_burst', return_value=False), \
                patch.object(BaseTask, '_wait_if_disconnected') as disconnect_guard, \
                patch.object(BaseTask, '_wait_if_reconnecting'):
            probe.screenshot()
        disconnect_guard.assert_called_once()


if __name__ == '__main__':
    unittest.main()
