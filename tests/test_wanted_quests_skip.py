# This Python file uses the following encoding: utf-8
"""封印悬赏「神秘任务跳过」修复的回归测试。

背景
----
新版悬赏详情页不再显示追踪蓝勾，也没有「取消追踪」按钮：
右上角是红色叉，执行按钮是「前往」。原 ``open_wq_info`` 用 ``I_TRACE_TRUE``
判断会空转，神秘妖怪悬赏又只有线索没有「前往」按钮，卡死后还会残留面板遮住
左栏列表。上游 ``c3a88af9`` / ``c695e50d`` / ``9a6eb783`` 的做法是：

* 用「前往」按钮判断详情页是否打开（任意一条即可）；
* 打不开（神秘妖怪）时用右上角红色叉关闭，并记录卡位（进度文本 + y）
  避免下一轮重复打开；
* 连续多轮只剩跳过卡时正常退出。
"""
import inspect
import os
import unittest

import numpy as np

from tasks.WantedQuests.assets import WantedQuestsAssets
from tasks.WantedQuests.script_task import ScriptTask


class _Res:
    def __init__(self, text):
        self.ocr_text = text


class _SkipStub:
    is_wq_row_skipped = ScriptTask.is_wq_row_skipped

    def __init__(self, rows):
        self.wq_skipped_rows = rows


class WantedQuestsSkipTests(unittest.TestCase):
    def test_no_skipped_rows(self):
        stub = _SkipStub(set())
        self.assertFalse(stub.is_wq_row_skipped(_Res('0/3'), 200))

    def test_same_text_near_y_is_skipped(self):
        # 同一张卡在连续截图中的 y 会有几像素抖动，允许 20px 误差
        stub = _SkipStub({('0/3', 200)})
        self.assertTrue(stub.is_wq_row_skipped(_Res('0/3'), 215))
        self.assertTrue(stub.is_wq_row_skipped(_Res('0/3'), 185))

    def test_same_text_far_y_is_not_skipped(self):
        stub = _SkipStub({('0/3', 200)})
        self.assertFalse(stub.is_wq_row_skipped(_Res('0/3'), 260))

    def test_different_text_is_not_skipped(self):
        stub = _SkipStub({('0/3', 200)})
        self.assertFalse(stub.is_wq_row_skipped(_Res('0/12'), 200))

    def test_skip_helpers_exist(self):
        for name in ('appear_any_goto', 'is_mystery_wq', 'close_unsupported_wq',
                     'is_wq_row_skipped'):
            self.assertTrue(callable(getattr(ScriptTask, name, None)), name)

    def test_execute_mission_no_longer_uses_old_trace_loop(self):
        # 老写法 ui_click(I_TRACE_TRUE, I_TRACE_FALSE) 没有超时，神秘任务会卡死
        source = inspect.getsource(ScriptTask.execute_mission)
        self.assertNotIn('I_TRACE_TRUE', source)
        self.assertIn('close_unsupported_wq', source)
        self.assertIn('return True', source)

    def test_open_wq_info_uses_goto_and_mystery(self):
        source = inspect.getsource(ScriptTask.open_wq_info)
        self.assertIn('appear_any_goto', source)
        self.assertIn('is_mystery_wq', source)
        self.assertNotIn('I_TRACE_TRUE', source)

    def test_exit_asset_matches_upstream_roi(self):
        rule = WantedQuestsAssets.I_EXIT
        self.assertEqual(tuple(rule.roi_front), (1189, 111, 36, 36))
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'tasks', 'WantedQuests', 'wq', 'wq_exit.png')
        self.assertTrue(os.path.isfile(path))


class _Boxed:
    def __init__(self, text, box):
        self.ocr_text = text
        self.box = np.array(box)


class _OcrStub:
    """模拟 O_WQ_TEXT_ALL：按当前 roi 宽度区分原生 / 2x 放大两路返回值。"""

    def __init__(self, native, upscaled, relaxed=None):
        self.roi = [0, 0, 60, 400]
        self.area = [0, 0, 60, 400]
        self._native = native
        self._upscaled = upscaled
        self._relaxed = relaxed
        self.calls = []

    def detect_and_ocr(self, image, logDisplay=True, **kwargs):
        self.calls.append((list(self.roi), kwargs.get('box_thresh')))
        if self.roi[2] == 60:
            return self._native
        if kwargs.get('box_thresh') is not None and self._relaxed is not None:
            return self._relaxed
        return self._upscaled


class _WqStub:
    find_wq = ScriptTask.find_wq
    _scan_wq_text = ScriptTask._scan_wq_text
    is_wq_row_skipped = ScriptTask.is_wq_row_skipped

    def __init__(self, ocr):
        self.O_WQ_TEXT_ALL = ocr
        self.wq_skipped_rows = set()
        self.wq_skipped_only = False
        self.wq_current_row = None


class WantedQuestsRescanTests(unittest.TestCase):
    def _img(self):
        return np.zeros((30, 30, 3), np.uint8)

    def test_retries_with_2x_when_label_but_no_progress(self):
        native = [_Boxed('封印', [[5, 5], [40, 5], [40, 25], [5, 25]])]
        upscaled = [
            _Boxed('封印', [[5, 5], [40, 5], [40, 25], [5, 25]]),
            _Boxed('4/5', [[40, 300], [100, 300], [100, 330], [40, 330]]),
        ]
        ocr = _OcrStub(native, upscaled)
        stub = _WqStub(ocr)
        self.assertEqual(stub.find_wq(self._img()), (4, 1, 5, [20, 150, 30, 15]))
        # 原生一次 + 2x 一次，且坐标已按 0.5 回算；roi 用完恢复原值
        self.assertEqual([call[0][2] for call in ocr.calls], [60, 120])
        self.assertEqual(ocr.roi, [0, 0, 60, 400])

    def test_no_label_no_rescan(self):
        native = [_Boxed('abc', [[5, 5], [40, 5], [40, 25], [5, 25]])]
        ocr = _OcrStub(native, [])
        stub = _WqStub(ocr)
        self.assertEqual(stub.find_wq(self._img()), (-1, -1, -1, [0, 0, 0, 0]))
        self.assertEqual(len(ocr.calls), 1)

    def test_relaxed_box_threshold_third_pass(self):
        native = [_Boxed('封印', [[5, 5], [40, 5], [40, 25], [5, 25]])]
        upscaled = list(native)
        relaxed = native + [_Boxed('2/5', [[40, 300], [100, 300], [100, 330], [40, 330]])]
        ocr = _OcrStub(native, upscaled, relaxed)
        stub = _WqStub(ocr)
        self.assertEqual(stub.find_wq(self._img()), (2, 1, 5, [20, 150, 30, 15]))
        self.assertEqual(ocr.calls[-1][1], 0.5)


if __name__ == '__main__':
    unittest.main()
