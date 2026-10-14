# This Python file uses the following encoding: utf-8
"""批次 25「斗技开战前等待收敛」的回归测试。

背景
----
上游 ``bedff718`` / ``985ac267`` / ``5770f91e``（PR #1934）针对斗技进入战斗后
「开战前操作」的问题做了改动：把原来的 ``ui_click(O_BATTLE_HAND, O_BATTLE_AUTO,
interval=0.8)`` 改成 ``interval=6, timeout=45``——放慢点击频率并加上超时上限，
避免在战斗加载期间对着「手动/自动」按钮连点空转。

上游 ``ui_click`` 在 ``13cf4303``（2026-02-15）新增了 ``timeout`` 参数；本地
``BaseTask.ui_click`` 至今**没有** ``timeout`` 参数，因此直接照搬会 ``TypeError``。

本地有一个语义等价且更成熟的工具 ``ui_click_until_appear_or_timeout``（主体由
``05298287`` 引入），本轮据用户决策「先复用本地的」采用它：

    self.ui_click_until_appear_or_timeout(self.O_BATTLE_HAND, self.O_BATTLE_AUTO,
                                          interval=6, timeout=45)

本测试钉死两条不变量：
1. ``ui_click_until_appear_or_timeout`` 的契约稳定——``stop`` 出现即返回 ``True``，
   否则在 ``timeout`` 到达后返回 ``False``（保证复用的语义可靠）。
2. ``Duel.ScriptTask.wait_battle`` 开战前操作确实走该工具且参数为
   ``(O_BATTLE_HAND, O_BATTLE_AUTO, interval=6, timeout=45)``，并且**不再**回退到
   ``ui_click`` 的旧路径。
"""
import unittest
from types import SimpleNamespace

from tasks.base_task import BaseTask
from tasks.Duel.script_task import ScriptTask


class _StubUi(object):
    """仅用替身驱动真实的 ``BaseTask.ui_click_until_appear_or_timeout``。"""

    # 直接绑定真实实现，验证其契约而非替换逻辑。
    ui_click_until_appear_or_timeout = BaseTask.ui_click_until_appear_or_timeout

    def __init__(self, stop_visible):
        self.stop_visible = stop_visible
        self.screenshot_count = 0

    def screenshot(self):
        self.screenshot_count += 1

    def appear(self, rule, **kwargs):
        return self.stop_visible

    def appear_then_click(self, rule, **kwargs):
        return False

    def click(self, rule, **kwargs):
        return False

    def ocr_appear_click(self, rule, **kwargs):
        return False


class UiClickUntilAppearOrTimeoutContractTests(unittest.TestCase):
    def test_returns_true_when_stop_appears(self):
        stub = _StubUi(stop_visible=True)
        result = stub.ui_click_until_appear_or_timeout(
            ScriptTask.O_BATTLE_HAND, ScriptTask.O_BATTLE_AUTO, interval=0.05, timeout=2
        )
        self.assertTrue(result)

    def test_returns_false_when_timeout_reached(self):
        stub = _StubUi(stop_visible=False)
        result = stub.ui_click_until_appear_or_timeout(
            ScriptTask.O_BATTLE_HAND, ScriptTask.O_BATTLE_AUTO, interval=0.05, timeout=0.3
        )
        self.assertFalse(result)


class _ScriptedDuelWait(ScriptTask):
    """绕过 Config / Device，驱动 ``wait_battle`` 的开战前操作分支。"""

    def __init__(self):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.captured = None
        self.ui_click_calls = []
        # green_mark 入参在调用前求值，故需提供 conf.duel_config 占位。
        self.conf = SimpleNamespace(
            duel_config=SimpleNamespace(green_enable=False, green_mark=None)
        )

    def screenshot(self):
        pass

    def check_and_get_reward(self):
        pass

    def appear(self, button, **kwargs):
        # 捕获到开战前操作后，让斗技主界面判定成立以结束循环。
        if self.captured is not None and button in (ScriptTask.I_CHECK_DUEL, ScriptTask.I_D_HELP):
            return True
        return False

    def appear_then_click(self, button, **kwargs):
        return False

    def is_battle_win(self):
        return False

    def is_battle_lose(self):
        return False

    def ui_click_until_appear_or_timeout(self, click, stop=None, interval=1, timeout=10):
        self.captured = (click, stop, interval, timeout)
        return True

    def ui_click(self, click, stop, interval=1):
        self.ui_click_calls.append((click, stop, interval))
        return None

    def green_mark(self, *args, **kwargs):
        pass

    def reset_device(self, status):
        pass


class DuelSetupWaitTests(unittest.TestCase):
    def test_wait_battle_uses_bounded_ui_click(self):
        task = _ScriptedDuelWait()
        task.wait_battle()

        self.assertIsNotNone(task.captured, 'wait_battle 未走到开战前操作分支')
        click, stop, interval, timeout = task.captured
        self.assertIs(click, ScriptTask.O_BATTLE_HAND)
        self.assertIs(stop, ScriptTask.O_BATTLE_AUTO)
        self.assertEqual(interval, 6)
        self.assertEqual(timeout, 45)

    def test_wait_battle_does_not_fallback_to_ui_click(self):
        task = _ScriptedDuelWait()
        task.wait_battle()
        self.assertEqual(task.ui_click_calls, [])


if __name__ == '__main__':
    unittest.main()
