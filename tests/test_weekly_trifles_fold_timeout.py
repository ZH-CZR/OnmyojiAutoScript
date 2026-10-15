# This Python file uses the following encoding: utf-8
"""批次 26「每周琐事·摸鱼行动入口折叠超时」回归测试。

背景
----
上游 ``28e8f060b``（xylolit-mu/self，2026-09-20）在 ``_save_touch_fish`` 的开头
给「等待公会入口折叠窗口展开」的 ``while 1`` 循环加了 15 秒超时兜底：

    fold_timer = Timer(15).start()
    while 1:
        if fold_timer.reached():
            logger.warning('Touch fish guild entry timeout')
            self.goto_page(page_main)
            return
        ...

本地该循环**没有**任何超时（只有外层任务框架的卡死检测兜底）：若公会页面的
``I_WT_FOLD_WINDOW`` / ``I_WT_OPEN_FOLD_WINDOW`` 都匹配不到（例如入口被改版、
页面未加载完成），这里会一直空转 ``sleep(1)`` 而不返回，直到全局卡死检测把
任务判失败。

不变量（本测试钉死）
--------------------
1. 折叠窗口 15 秒内没出现时，方法**返回**并回到庭院（``page_main``），不再空转；
2. 正常路径（折叠窗口出现）不受影响：照旧进入 ``page_touch_fish`` 并收尾回庭院。
"""
import unittest
from unittest import mock

import tasks.WeeklyTrifles.script_task as wt
from tasks.GameUi.page import page_main
from tasks.WeeklyTrifles.page import page_touch_fish
from tasks.WeeklyTrifles.script_task import ScriptTask


class _TimerFactory(object):
    """可控 Timer 替身工厂：按 ``mode`` 决定 ``reached()`` 行为。"""

    def __init__(self, mode):
        self.mode = mode
        self.created = []

    def __call__(self, seconds):
        timer = _TimerInstance(seconds, self.mode)
        self.created.append(timer)
        return timer


class _TimerInstance(object):
    def __init__(self, seconds, mode):
        self.seconds = seconds
        self.mode = mode

    def start(self):
        return self

    def reset(self):
        return self

    def reached(self):
        return self.mode == 'immediate'

    def remain(self):
        return 0


class _ScriptedTrifles(ScriptTask):
    """绕过 Config / Device，只驱动 ``_save_touch_fish`` 的入口等待段。"""

    def __init__(self, fold_window_appears):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.fold_window_appears = fold_window_appears
        self.visited = []
        self.rule_appear = []

    def goto_page(self, page, **kwargs):
        self.visited.append(page)

    def screenshot(self):
        pass

    def appear(self, rule, **kwargs):
        self.rule_appear.append(rule)
        if rule is ScriptTask.I_WT_FOLD_WINDOW:
            return self.fold_window_appears
        return False

    def appear_then_click(self, rule, **kwargs):
        # 折叠按钮一直点不到（触发超时分支） / 正常分支无需点击
        return False


class TouchFishEntryTimeoutTests(unittest.TestCase):
    def _run(self, stub, timer_factory):
        with mock.patch.object(wt, 'Timer', timer_factory), \
                mock.patch.object(wt, 'sleep'), \
                mock.patch.object(wt, 'logger') as mock_logger:
            stub._save_touch_fish()
        return mock_logger

    def test_timeout_returns_to_main_without_hanging(self):
        stub = _ScriptedTrifles(fold_window_appears=False)
        factory = _TimerFactory('immediate')
        mock_logger = self._run(stub, factory)

        self.assertIn(page_main, stub.visited, '超时后应回到庭院')
        self.assertNotIn(page_touch_fish, stub.visited, '超时后不应再进入摸鱼页面')
        self.assertEqual(
            len([c for c in mock_logger.warning.call_args_list
                 if '入场超时' in str(c) or 'entry timeout' in str(c)]), 1,
            '超时应恰好告警一次',
        )
        self.assertTrue(factory.created, '入口等待循环应使用 Timer 兜底')
        self.assertEqual(factory.created[0].seconds, 15, '超时窗口应为 15 秒')

    def test_normal_path_still_enters_touch_fish_page(self):
        stub = _ScriptedTrifles(fold_window_appears=True)
        factory = _TimerFactory('never')
        mock_logger = self._run(stub, factory)

        self.assertIn(page_touch_fish, stub.visited, '折叠窗口出现后应进入摸鱼页面')
        self.assertIn(page_main, stub.visited, '收尾应回到庭院')
        self.assertEqual(
            [c for c in mock_logger.warning.call_args_list
             if 'entry timeout' in str(c)], [],
            '正常路径不应告警入口超时',
        )


if __name__ == '__main__':
    unittest.main()
