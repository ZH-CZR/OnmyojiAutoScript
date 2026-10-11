# This Python file uses the following encoding: utf-8
"""「退四」机制（``GeneralBattle.run_general_battle_back``）的回归测试。

背景
----
``tasks/RealmRaid/script_task.py`` 的个人突破「退四」在批次 18 由
``run_general_battle(build_quick_exit_config) + fire_again`` 改为移植上游 dev 的
``run_general_battle_back(exit_four=True)``。

旧实现快速退出战斗后会残留「确认退出战斗吗」弹窗（原 ``I_EXIT_ENSURE``，批次 20
起统一为共享资产 ``GlobalGameAssets.I_UI_CONFIRM``），而 ``fire_again`` 开头会
``wait_until_appear(I_FIRE_AGAIN)`` 被该弹窗永久挡住，最终约 55s 后
``GameStuckError``（实例：2026-10-10 18:34:20）。

新实现显式走完「退出 → 退出确认 → 失败确认」整链。本测试钉死该链路：
**点击顺序必须是 I_EXIT → I_UI_CONFIRM → I_FALSE，且必须正常返回 True**，
避免日后改动把某一环漏掉又造成残留弹窗卡死。
"""
import unittest

from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralBattle.general_battle import GeneralBattle


class _ScriptedBack(GeneralBattle):
    """绕过 Config / Device，用状态机模拟一次完整的退出链路。"""

    def __init__(self):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.events = []
        self.exit_clicked = False
        self.ensure_clicked = False
        self.false_clicked = False

    def screenshot(self):
        pass

    def wait_until_appear(self, button, **kwargs):
        return self.appear(button)

    def appear(self, button, **kwargs):
        if button is self.I_UI_CONFIRM:
            # 点了「退出」后，确认弹窗才出现；点掉后又消失。
            return self.exit_clicked and not self.ensure_clicked
        if button is self.I_FALSE:
            # 点了「确认」后，失败确认才出现；点掉后又消失。
            return self.ensure_clicked and not self.false_clicked
        return False

    def appear_then_click(self, button, **kwargs):
        if button is self.I_PREPARE_HIGHLIGHT:
            self.events.append('prepare')
            return False
        if button is self.I_EXIT and not self.exit_clicked:
            self.exit_clicked = True
            self.events.append('exit')
            return True
        if button is self.I_UI_CONFIRM and not self.ensure_clicked:
            self.ensure_clicked = True
            self.events.append('exit_ensure')
            return True
        if button is self.I_FALSE and not self.false_clicked:
            self.false_clicked = True
            self.events.append('false')
            return True
        return False


class ExitFourChainTests(unittest.TestCase):
    def test_exit_four_chain_clicks_in_order_and_finishes(self):
        """exit_four=True 时必须按「退出 → 退出确认 → 失败确认」点完并返回 True。"""
        task = _ScriptedBack()
        result = task.run_general_battle_back(config=GeneralBattleConfig(), exit_four=True)

        self.assertTrue(result)
        self.assertEqual(task.events, ['exit', 'exit_ensure', 'false'])

    def test_exit_four_skips_prepare_highlight(self):
        """exit_four=True 时不应触发准备阶段（不点 I_PREPARE_HIGHLIGHT）。"""
        task = _ScriptedBack()
        task.run_general_battle_back(config=GeneralBattleConfig(lock_team_enable=False), exit_four=True)

        self.assertNotIn('prepare', task.events)
        self.assertEqual(task.events, ['exit', 'exit_ensure', 'false'])


if __name__ == '__main__':
    unittest.main()