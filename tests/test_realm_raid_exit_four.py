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

实机卡死复盘（2026-10-11 17:20）
-------------------------------
实测日志显示 ``fire(RES_FIRE)`` 后直接进入 ``run_general_battle_back``（无
``page_battle_prepare``/``GENERAL BATTLE START``），随后 ``GB_EXIT`` 被连点 9 次
（约 12s）后无任何后续操作，约 60s 后 ``GameStuckError``；卡死截图正是
「确认退出战斗吗?」弹窗。
根因：当时部署的构建仍使用**旧的「确认」样式资产** ``I_EXIT_ENSURE``
(``gb/gb_exit_ensure.png``)，而该弹窗右侧按钮实际为「确定」样式，模板永不命中，
退出循环永远等不到确认弹窗 → 卡死。批次 20 (``97c5f0ce``) 已将其替换为共享的
``GlobalGameAssets.I_UI_CONFIRM`` (``ui/ui_ui_confirm.png``，即「确定」样式)。

因此本测试额外钉死两点：
1. **退出确认必须使用共享的「确定」资产**（``I_UI_CONFIRM``），防止回归到
   不匹配的旧「确认」资产；
2. **退出确认弹窗延迟出现**（连点退出若干次后才弹出）时链路仍应走完；
3. **旧功能（非退四）不受影响**：``lock_team_enable`` / 准备阶段行为保持原样。
"""
import unittest

from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.GlobalGame.assets import GlobalGameAssets


class _ScriptedBattle(GeneralBattle):
    """绕过 Config / Device，用状态机模拟一次完整的退出链路。

    ``enable_prepare``: 是否模拟「未锁定队伍」时先点准备按钮。
    ``confirm_after_exit_clicks``: 点退出若干次后「确认退出战斗吗」弹窗才出现
    （模拟实机中该弹窗延迟弹出的行为）。
    """

    def __init__(self, *, enable_prepare: bool = False, confirm_after_exit_clicks: int = 1):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.events = []
        self.queried = []
        self.exit_clicks = 0
        self.prepare_clicks = 0
        self.confirm_clicks = 0
        self.false_clicks = 0
        self.prepare_done = not enable_prepare
        self.confirm_after_exit_clicks = confirm_after_exit_clicks

    def screenshot(self):
        pass

    def wait_until_appear(self, button, **kwargs):
        return self.appear(button)

    def appear(self, button, **kwargs):
        self.queried.append(button)
        if button is self.I_PREPARE_HIGHLIGHT:
            return not self.prepare_done
        if button is self.I_PRESET or button is self.I_PRESET_WIT_NUMBER:
            return False
        if button is self.I_EXIT:
            # 退出确认弹窗弹出前，退出按钮一直可见
            return self.exit_clicks < self.confirm_after_exit_clicks
        if button is self.I_UI_CONFIRM:
            return self.exit_clicks >= self.confirm_after_exit_clicks and self.confirm_clicks == 0
        if button is self.I_FALSE:
            return self.confirm_clicks >= 1 and self.false_clicks == 0
        return False

    def appear_then_click(self, button, **kwargs):
        if not self.appear(button):
            return False
        if button is self.I_PREPARE_HIGHLIGHT:
            self.prepare_clicks += 1
            self.prepare_done = True
            self.events.append('prepare')
        elif button is self.I_EXIT:
            self.exit_clicks += 1
            self.events.append('exit')
        elif button is self.I_UI_CONFIRM:
            self.confirm_clicks += 1
            self.events.append('exit_ensure')
        elif button is self.I_FALSE:
            self.false_clicks += 1
            self.events.append('false')
        return True


class ExitFourChainTests(unittest.TestCase):
    def test_exit_four_chain_clicks_in_order_and_finishes(self):
        """exit_four=True 时必须按「退出 → 退出确认 → 失败确认」点完并返回 True。"""
        task = _ScriptedBattle(confirm_after_exit_clicks=1)
        result = task.run_general_battle_back(config=GeneralBattleConfig(), exit_four=True)

        self.assertTrue(result)
        self.assertEqual(task.events, ['exit', 'exit_ensure', 'false'])

    def test_exit_four_skips_prepare_highlight(self):
        """exit_four=True 时不应触发准备阶段（不点 I_PREPARE_HIGHLIGHT）。"""
        task = _ScriptedBattle(confirm_after_exit_clicks=1)
        task.run_general_battle_back(config=GeneralBattleConfig(lock_team_enable=False), exit_four=True)

        self.assertNotIn('prepare', task.events)
        self.assertEqual(task.events, ['exit', 'exit_ensure', 'false'])

    def test_exit_four_handles_delayed_confirm_dialog(self):
        """退出确认弹窗延迟出现时，链路仍应按序走完（对应 2026-10-11 实机延迟弹窗）。"""
        task = _ScriptedBattle(confirm_after_exit_clicks=3)
        result = task.run_general_battle_back(config=GeneralBattleConfig(), exit_four=True)

        self.assertTrue(result)
        self.assertEqual(task.events, ['exit', 'exit', 'exit', 'exit_ensure', 'false'])


class NonExitFourRegressionTests(unittest.TestCase):
    """旧功能（非退四）回归：准备阶段 / lock_team_enable 行为不得被破坏。"""

    def test_unlocked_team_clicks_prepare_before_exit(self):
        """未锁定队伍时，必须先点准备按钮，再走「退出 → 确认 → 失败确认」。"""
        task = _ScriptedBattle(enable_prepare=True, confirm_after_exit_clicks=1)
        result = task.run_general_battle_back(
            config=GeneralBattleConfig(lock_team_enable=False), exit_four=False)

        self.assertTrue(result)
        self.assertEqual(task.events, ['prepare', 'exit', 'exit_ensure', 'false'])

    def test_locked_team_skips_prepare(self):
        """锁定队伍时，不点准备按钮，直接走退出整链。"""
        task = _ScriptedBattle(enable_prepare=True, confirm_after_exit_clicks=1)
        result = task.run_general_battle_back(
            config=GeneralBattleConfig(lock_team_enable=True), exit_four=False)

        self.assertTrue(result)
        self.assertNotIn('prepare', task.events)
        self.assertEqual(task.events, ['exit', 'exit_ensure', 'false'])


class ExitConfirmAssetTests(unittest.TestCase):
    """钉死：战斗退出确认使用共享的 GlobalGame「确定」资产。

    实机卡死根因是旧构建用了「确认」样式的 ``I_EXIT_ENSURE``，与弹窗的
    「确定」按钮不匹配。此测试断言退出整链**实际查询/点击的**确认资产就是共享的
    ``GlobalGameAssets.I_UI_CONFIRM``，防止日后回退到不匹配的任务级资产。
    """

    def test_exit_confirm_uses_shared_ui_confirm_asset(self):
        task = _ScriptedBattle(confirm_after_exit_clicks=1)
        task.run_general_battle_back(config=GeneralBattleConfig(), exit_four=True)

        self.assertIs(GeneralBattle.I_UI_CONFIRM, GlobalGameAssets.I_UI_CONFIRM)
        self.assertIn(GlobalGameAssets.I_UI_CONFIRM, task.queried)


if __name__ == '__main__':
    unittest.main()