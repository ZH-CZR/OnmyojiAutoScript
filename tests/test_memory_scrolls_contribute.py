# This Python file uses the following encoding: utf-8
"""批次 21「绘卷捐献用最大按钮 + 限制轮数」的回归测试。

背景
----
上游 ``4f0a4856``（PR #1910）把 ``contribute_memoryscrolls`` 的旧实现
（``while 1`` 无限循环 + 三次 ``swipe`` 拉满数量条）改为：

* 每行改用「最大」按钮 ``C_MS_MAX_S`` / ``C_MS_MAX_M`` / ``C_MS_MAX_L``
  各点两次（等价拉满），不再依赖滑动；
* 外层捐献轮数上限 ``max_rounds = 10``，避免素材识别异常时无限循环；
* 内层等待捐献动画同样限制次数，超限告警而非死等。

本测试用状态机驱动 ``contribute_memoryscrolls``，钉死这些不变量：
不再调用 ``swipe``、每轮按序点满 6 次「最大」按钮、轮数上限为 10、
素材已满（无需捐献）时立即返回且不点击。
"""
import unittest
from unittest.mock import patch

from tasks.MemoryScrolls.script_task import ScriptTask

MAX_ROUNDS = 10


class _ScriptedContribute(ScriptTask):
    """绕过 Config / Device，用状态机模拟一次绘卷捐献流程。"""

    def __init__(self, *, already_full: bool = False):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.already_full = already_full
        self.swipes = 0
        self.max_clicks = []
        self.contribute_clicks = 0
        self.contributed_clicks = 0
        self.warnings = []

    def screenshot(self):
        pass

    def appear(self, button, **kwargs):
        if button in (self.I_MS_ZERO_S, self.I_MS_ZERO_M, self.I_MS_ZERO_L):
            return self.already_full
        return False

    def click(self, button, **kwargs):
        if button in (self.C_MS_MAX_S, self.C_MS_MAX_M, self.C_MS_MAX_L):
            self.max_clicks.append(button)
        elif button is self.C_MS_CONTRIBUTED:
            self.contributed_clicks += 1
        return True

    def appear_then_click(self, button, **kwargs):
        if button is self.I_MS_CONTRIBUTE:
            self.contribute_clicks += 1
            return True
        return False

    def wait_until_appear(self, button, **kwargs):
        return False

    def swipe(self, button, **kwargs):
        self.swipes += 1


class MemoryScrollsContributeTests(unittest.TestCase):
    def setUp(self):
        logger_patch = patch('tasks.MemoryScrolls.script_task.logger')
        self.logger = logger_patch.start()
        self.addCleanup(logger_patch.stop)
        sleep_patch = patch('tasks.MemoryScrolls.script_task.sleep')
        sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def test_no_longer_uses_swipe(self):
        """捐献不再依赖滑动，一次 swipe 都不应发生。"""
        task = _ScriptedContribute()
        task.contribute_memoryscrolls()
        self.assertEqual(task.swipes, 0)

    def test_max_buttons_clicked_twice_each_per_round(self):
        """每轮小/中/大「最大」按钮各点两次。"""
        task = _ScriptedContribute()
        task.contribute_memoryscrolls()

        expected_per_round = [(task.C_MS_MAX_S, 2), (task.C_MS_MAX_M, 2), (task.C_MS_MAX_L, 2)]
        self.assertEqual(len(task.max_clicks), MAX_ROUNDS * 6)
        # 每轮按 S → M → L 顺序，各出现两次
        for round_index in range(MAX_ROUNDS):
            chunk = task.max_clicks[round_index * 6:(round_index + 1) * 6]
            self.assertEqual(chunk, [b for b, n in expected_per_round for _ in range(n)])

    def test_contribution_rounds_capped(self):
        """无「已满」信号时，捐献轮数被限制在 10 轮内（不再无限循环）。"""
        task = _ScriptedContribute()
        task.contribute_memoryscrolls()

        self.assertEqual(task.contribute_clicks, MAX_ROUNDS)
        self.logger.warning.assert_called()

    def test_already_full_returns_immediately_without_clicking(self):
        """三卷都提示「不足/已满」时立即返回，且不点击任何按钮。"""
        task = _ScriptedContribute(already_full=True)
        task.contribute_memoryscrolls()

        self.assertEqual(task.max_clicks, [])
        self.assertEqual(task.contribute_clicks, 0)


if __name__ == '__main__':
    unittest.main()