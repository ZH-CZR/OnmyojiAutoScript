# This Python file uses the following encoding: utf-8
"""批次 26「寮突（RyouToppa）挑战进入失败判定」回归测试。

背景
----
上游两条提交改了同一个循环（``tasks/RyouToppa/script_task.py::attack_area``）：

* ``3f45805b7``（2026-08-28）把「浮窗点击上限 + 挑战点击上限」两个独立计数器
  收敛成单一 ``TOPPA_CLICK_FAILURE_LIMIT = 4``；
* ``3ee4e53db``（2026-08-29）进一步指出**「发出点击」不等于「失败」**：只有
  「点击结界卡片后浮窗在 ``TOPPA_POPUP_WAIT_TIMEOUT`` 内未出现」或「点击挑战
  按钮后 ``TOPPA_BATTLE_WAIT_TIMEOUT`` 内未进入战斗」才算一次真实失败，并把
  两者合并计数到 4 后跳过当前区域。

本地旧实现是 ``click_failure_count`` **每次成功点击就 +1**（上限 5），于是设备
慢一帧／动画多几帧时会被误判成「Click failure, check your click position」并
提前 ``return False``（该区域被当成打不动而跳过）。

本地架构差异（务必保留）
------------------------
上游用 ``is_in_battle(False)`` 判「已进入战斗」；本地用 ``I_TOPPA_RECORD``
**消失**作为同一判据，且有 ``sleep(1)`` 二次确认。本批次只移植失败计数语义，
战斗判据保持本地实现。

不变量（本测试钉死）
--------------------
1. 只发出点击（等待窗口未超时）**不累计**失败，循环继续；
2. 等待超时会累计，且 popup / battle 两个来源合并计数到 4 即返回 ``False``；
3. 战斗判据未被破坏：``I_TOPPA_RECORD`` 消失（二次确认后仍消失）时照旧调用
   ``run_general_battle`` 并返回其结果。
"""
import unittest
from types import SimpleNamespace
from unittest import mock

import tasks.RyouToppa.script_task as rt
from tasks.RealmRaid.assets import RealmRaidAssets
from tasks.RyouToppa.script_task import ScriptTask


class _ImmediateTimer(object):
    """``reached()`` 立即为真：模拟等待窗口马上超时。"""

    def __init__(self, seconds=0):
        self.seconds = seconds

    def start(self):
        return self

    def reset(self):
        return self

    def reached(self):
        return True

    def remain(self):
        return 0


class _NeverTimer(_ImmediateTimer):
    """``reached()`` 永不为真：模拟等待窗口一直没超时。"""

    def reached(self):
        return False


class _ScriptedToppa(ScriptTask):
    """绕过 Config / Device，脚本化驱动 ``attack_area`` 的挑战循环。"""

    def __init__(self, record_iterations=10 ** 9, fire_appears=True,
                 fire_clicked=True, click_rcl=True):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.record_iterations = record_iterations
        self.record_appear_count = 0
        self.fire_appears = fire_appears
        self.fire_clicked = fire_clicked
        self.click_rcl = click_rcl
        self.fire_click_calls = 0
        self.rcl_click_calls = 0
        self.battle_result = SimpleNamespace(name='GENERAL_BATTLE')
        self.config = SimpleNamespace(
            ryou_toppa=SimpleNamespace(
                raid_config=SimpleNamespace(random_delay=False),
                general_battle_config='gb-config',
            )
        )

    # ---- 被驱动的方法用到的替身 ----
    def check_area(self, index):
        return True

    def screenshot(self):
        pass

    def appear(self, rule, **kwargs):
        if rule is ScriptTask.I_TOPPA_RECORD:
            self.record_appear_count += 1
            return self.record_appear_count <= self.record_iterations
        if rule is RealmRaidAssets.I_FIRE:
            return self.fire_appears
        return False

    def appear_then_click(self, rule, **kwargs):
        if rule is RealmRaidAssets.I_FIRE and self.fire_clicked:
            self.fire_click_calls += 1
            return True
        return False

    def click(self, rule, **kwargs):
        self.rcl_click_calls += 1
        return self.click_rcl

    def run_general_battle(self, config=None):
        return self.battle_result


def _failure_warnings(mock_logger):
    return [str(c) for c in mock_logger.warning.call_args_list]


class RyouToppaClickFailureTests(unittest.TestCase):
    def _run(self, stub, timer_cls):
        with mock.patch.object(rt, 'Timer', timer_cls), \
                mock.patch.object(rt, 'logger') as mock_logger, \
                mock.patch.object(rt.time, 'sleep'):
            result = stub.attack_area(0)
        return result, mock_logger

    def test_clicks_alone_do_not_count_as_failure(self):
        # 等待窗口永不超时 -> 只有「发出点击」，不应产生任何失败。
        # 第 6 次之后 I_TOPPA_RECORD 消失 -> 走战斗判据并返回 run_general_battle 结果。
        stub = _ScriptedToppa(record_iterations=6)
        result, mock_logger = self._run(stub, _NeverTimer)

        self.assertIs(result, stub.battle_result)
        self.assertEqual(stub.battle_result.name, 'GENERAL_BATTLE')
        self.assertGreaterEqual(stub.fire_click_calls, 1, '未发出挑战按钮点击')
        self.assertEqual(
            [w for w in _failure_warnings(mock_logger) if '失败' in w or '未出现' in w],
            [], '仅发出点击不应被计为挑战进入失败',
        )

    def test_battle_wait_timeout_stops_after_limit(self):
        stub = _ScriptedToppa()  # I_TOPPA_RECORD 恒在：始终未进入战斗
        result, mock_logger = self._run(stub, _ImmediateTimer)

        self.assertIs(result, False)
        warnings = _failure_warnings(mock_logger)
        self.assertEqual(
            len([w for w in warnings if '未进入战斗' in w]), 4,
            '每次战斗等待超时应各记一次失败，共 4 次',
        )
        self.assertEqual(
            len([w for w in warnings if '跳过当前区域' in w]), 1,
            '达到上限时应只警告一次并返回 False',
        )
        self.assertIn('battle=4', warnings[-1])
        self.assertIn('popup=0', warnings[-1])

    def test_popup_wait_timeout_stops_after_limit(self):
        stub = _ScriptedToppa(fire_appears=False)  # 浮窗一直不出现
        result, mock_logger = self._run(stub, _ImmediateTimer)

        self.assertIs(result, False)
        warnings = _failure_warnings(mock_logger)
        self.assertEqual(
            len([w for w in warnings if '挑战浮窗未出现' in w]), 4,
            '每次浮窗等待超时应各记一次失败，共 4 次',
        )
        self.assertEqual(len([w for w in warnings if '跳过当前区域' in w]), 1)
        self.assertIn('popup=4', warnings[-1])
        self.assertIn('battle=0', warnings[-1])

    def test_limit_constant_is_four(self):
        self.assertEqual(rt.TOPPA_CLICK_FAILURE_LIMIT, 4)
        self.assertEqual(rt.TOPPA_POPUP_WAIT_TIMEOUT, 3.0)
        self.assertEqual(rt.TOPPA_BATTLE_WAIT_TIMEOUT, 5.0)


if __name__ == '__main__':
    unittest.main()
