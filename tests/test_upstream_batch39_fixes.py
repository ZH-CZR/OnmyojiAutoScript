# This Python file uses the following encoding: utf-8
"""批次 39 上游修复回归测试。

本轮 ``nearaura/dev`` 新增 9 条提交，实际可落地 2 处（其余见同步台账 §3.14）：

1. ``a787a58a``（PR #2）：minitouch 设备上报的 ``max_pressure`` 低于 20 时，
   ``_humanized_pressure`` 里 ``randint(max(20, top // 2), top)`` 会出现 low > high
   抛 ``ValueError``；下限改为 ``max(1, top // 2)``。
2. ``3ede58e1``（部分采纳）：``RuleAnimate.stable()`` 帧比较区域固定为构造时的
   ``roi_front``，不再随匹配命中回写的 ``roi_front`` 漂移。上游同一提交里把
   ``roi_pad`` 改为无条件外扩 2px 的部分**不采纳**——本地 ``roi_pad`` 由图像服务
   在桌面模式下发（批次 27），模拟器保持 0 以保证行为逐位不变。
"""
import unittest
from unittest.mock import patch

import numpy as np

try:  # Python 3.12+ 已移除 distutils，adbutils -> pkg_resources 依赖它；导入 setuptools 会补上兼容层
    import setuptools  # noqa: F401
except ImportError:
    pass

from module.atom.animate import RuleAnimate
from module.atom.image import RuleImage
from module.device.method.minitouch import Minitouch
from tasks.SixRealms.assets import SixRealmsAssets


class MinitouchPressureRangeTests(unittest.TestCase):
    @staticmethod
    def _make(max_pressure):
        obj = Minitouch.__new__(Minitouch)
        obj.max_pressure = max_pressure
        return obj

    def test_low_max_pressure_does_not_raise(self):
        # 上游修复前：max(20, 10 // 2) = 20 > 10 -> ValueError
        for top in (1, 5, 10, 19):
            obj = self._make(top)
            for _ in range(50):
                pressure = obj._humanized_pressure()
                self.assertGreaterEqual(pressure, 1, top)
                self.assertLessEqual(pressure, top, top)

    def test_normal_max_pressure_keeps_half_range(self):
        obj = self._make(100)
        for _ in range(50):
            self.assertGreaterEqual(obj._humanized_pressure(), 50)
            self.assertLessEqual(obj._humanized_pressure(), 100)

    def test_zero_max_pressure_falls_back(self):
        obj = self._make(0)
        for _ in range(20):
            pressure = obj._humanized_pressure()
            self.assertGreaterEqual(pressure, 50)
            self.assertLessEqual(pressure, 100)


class _FakeImageClient:
    """模拟图像服务的动态模板匹配，按预设结果回包。"""

    def __init__(self, matched: bool, roi_front=None):
        self.matched = matched
        self.roi_front = roi_front
        self.calls = []

    def match_dynamic_template(self, **kwargs):
        self.calls.append(kwargs)
        if not self.matched:
            return {"matched": False}
        return {"matched": True, "roi_front": list(self.roi_front)}


def _blank_image():
    """构造 1280x720 全黑图，并在两个候选区域写入可区分的内容。"""
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    image[20:60, 10:40] = 64      # roi_front（固定裁剪区）
    image[60:100, 50:80] = 200    # 命中后 roi_front 漂移到的位置
    return image


def _make_rule():
    return RuleImage(
        roi_front=(10, 20, 30, 40),
        roi_back=(0, 0, 200, 200),
        method="Template matching",
        threshold=0.8,
        file="./tasks/Exploration/res/res_swipe_end.png",
    )


class RuleAnimateCropRegionTests(unittest.TestCase):
    def test_crop_roi_is_initial_roi_front(self):
        rule = _make_rule()
        animate = RuleAnimate(rule)
        self.assertEqual(animate._crop_roi, (10, 20, 30, 40))
        self.assertEqual(tuple(animate.roi_back), (0, 0, 200, 200))

    def test_crop_roi_follows_rule_click(self):
        animate = RuleAnimate(SixRealmsAssets.C_MAIN_ANIMATE_KEEP)
        self.assertEqual(animate._crop_roi, tuple(SixRealmsAssets.C_MAIN_ANIMATE_KEEP.roi_front))

    def test_first_frame_crops_initial_region(self):
        animate = RuleAnimate(_make_rule())
        image = _blank_image()
        self.assertFalse(animate.stable(image))
        self.assertEqual(animate._last_image.shape, (40, 30, 3))
        self.assertTrue(np.array_equal(animate._last_image, image[20:60, 10:40]))

    def test_crop_does_not_drift_after_match(self):
        animate = RuleAnimate(_make_rule())
        image = _blank_image()
        animate.stable(image)

        # 服务回包把 roi_front 改到 (50,60)，修复前下一帧会裁剪到这里
        client = _FakeImageClient(matched=True, roi_front=[50, 60, 30, 40])
        with patch("module.atom.animate.get_image_client", return_value=client):
            stable = animate.stable(image)

        self.assertTrue(stable)
        self.assertEqual(animate.roi_front, [50, 60, 30, 40])
        self.assertEqual(animate._crop_roi, (10, 20, 30, 40))
        self.assertTrue(np.array_equal(animate._last_image, image[20:60, 10:40]))
        self.assertFalse(np.array_equal(animate._last_image, image[60:100, 50:80]))

    def test_service_call_uses_search_roi(self):
        animate = RuleAnimate(_make_rule())
        image = _blank_image()
        animate.stable(image)

        client = _FakeImageClient(matched=False)
        with patch("module.atom.animate.get_image_client", return_value=client):
            animate.stable(image, frame_id="frame-1")

        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(tuple(call["roi_back"]), (0, 0, 200, 200))
        self.assertEqual(call["frame_id"], "frame-1")
        self.assertTrue(np.array_equal(call["template"], image[20:60, 10:40]))


if __name__ == "__main__":
    unittest.main()
