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


if __name__ == '__main__':
    unittest.main()
