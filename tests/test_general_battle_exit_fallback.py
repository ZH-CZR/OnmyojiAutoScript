# This Python file uses the following encoding: utf-8
"""通用战斗「强制退出」在裸 ``GeneralBattle`` 兜底对象上的回归测试。

背景
----
``tasks/GameUi/default_pages.py::handle_battle_page`` 在识别到战斗页面时会调用
``run_task_or_default_general_battle(task)``。当触发页面 hook 的任务自身**没有**
``run_general_battle``（例如 ``KekkaiUtilize``）时，该函数会新建一个**裸
``GeneralBattle``** 兜底对象，只通过属性注入 ``navigator`` 与 ``match_page_once``：

    fallback = GeneralBattle(config=task.config, device=task.device)
    fallback.navigator = navigator
    fallback.match_page_once = match_page_once

``GeneralBattle`` 的继承链是 ``GeneralBattle → GeneralBuff → BaseTask``，**不含 ``GameUi``**，
因此该兜底对象并不具备 ``_detect_current_page`` / ``_default_detect_categories`` 等
``GameUi`` 实例方法（``run_general_battle`` 因此统一改用 ``GameUi.detect_page_in(self, ...)``
这种显式传 self 的调用方式）。

缺陷（实例：2026-10-13 16:15:49 少时之约 KekkaiUtilize）
--------------------------------------------------------
``exit_battle()`` 内部曾用 ``GameUi.get_current_page(self)`` 判断「是否已回到结算 / 奖励页」。
``GameUi.get_current_page()`` 会调用 ``self._detect_current_page(...)``；在兜底对象上该方法
不存在 → ``AttributeError: 'GeneralBattle' object has no attribute '_detect_current_page'``，
快速退出（``global_game.battle.on_takeover = exit``）链路整体崩溃。

本测试钉死不变量：**``exit_battle()`` 必须能在只有 ``navigator`` + ``match_page_once`` 的兜底
对象上走完并返回 True**（改用与 ``run_general_battle`` 同款的 ``GameUi.detect_page_in(self, ...)``
显式页面识别），同时不影响既有行为：先点掉「确认退出战斗吗」弹窗、无退出按钮时直接返回 False。

``page_battle`` / ``page_battle_prepare`` 都是 **global 分类**页面且挂有 ``handle_battle_page``
钩子，因此有突发弹窗（断线重连、活动/公告浮层等）、或残留战斗页被**稳定误判**为战斗页时，
**任意任务在任意时刻**都会进入这条兜底链路——它不是某个任务（如 KekkaiUtilize）专有的路径，
而是一张全局安全网。故除手工替身外，此处另加一条直接驱动**生产代码真正造出的**兜底对象的用例。
"""
import unittest
from types import SimpleNamespace

from tasks.Component.GeneralBattle.general_battle import (
    GeneralBattle,
    run_task_or_default_general_battle,
)
from tasks.GameUi.page import page_battle_result, page_reward


class _StubNavigator:
    """最小 ``NavigatorSession`` 替身：仅提供 ``exit_battle`` 识别所需接口。"""

    def __init__(self):
        self.current_page = None

    def resolve_page(self, page):
        return page

    def all_pages(self, categories=None):
        return [page_battle_result, page_reward]


class _FallbackLikeBattle(GeneralBattle):
    """复刻 ``run_task_or_default_general_battle`` 构造的裸兜底对象。

    只注入 ``navigator`` + ``match_page_once``（与生产一致），且**故意不**提供
    ``_detect_current_page`` / ``_default_detect_categories``，用于复现缺陷。
    ``exit_clicks_before_result``: 点退出若干次后「结算页」才出现。
    ``confirm_required``: 循环开始前「确认退出战斗吗」弹窗先出现并被点掉的次数。
    ``initial_current``: 进入时的当前页面（非 None 表示当前不在战斗页）。
    """

    def __init__(self, *, exit_clicks_before_result=1, confirm_required=0, initial_current=None):
        # 故意不调用 BaseTask.__init__：这里不需要真实 Config / Device。
        self.events = []
        self.queried = []
        self.exit_clicks = 0
        self.confirm_clicks = 0
        self.exit_clicks_before_result = exit_clicks_before_result
        self.confirm_required = confirm_required
        self.current = initial_current
        self.navigator = _StubNavigator()
        self.match_page_once = self._match_page_once

    # --- 页面识别替身 ---
    def _match_page_once(self, page):
        return self.current is not None and page.key == self.current.key

    # --- BaseTask 热路径替身（避免真实截图 / 缓存 / 设备）---
    def screenshot(self):
        pass

    def maybe_screenshot(self, soft_skip=False):
        pass

    def prepare_appear_cache(self, targets):
        pass

    def ui_click_until_disappear(self, click, interval=1):
        return False

    # --- 点击 / 识别替身 ---
    def appear(self, button, **kwargs):
        self.queried.append(button)
        if button is self.I_EXIT:
            return self.current is None
        return False

    def appear_then_click(self, button, **kwargs):
        if button is self.I_UI_CONFIRM:
            if self.confirm_clicks < self.confirm_required:
                self.confirm_clicks += 1
                self.events.append('confirm')
                return True
            return False
        if button is self.I_EXIT:
            self.exit_clicks += 1
            self.events.append('exit')
            if self.exit_clicks >= self.exit_clicks_before_result:
                self.current = page_battle_result
            return True
        return False


def _fake_task(on_takeover='finish', *, handler=None, navigator=None, match_page_once=None):
    """构造一个仅有 config / device（及可选注入项）的假任务。"""
    battle = SimpleNamespace(on_takeover=on_takeover)
    config = SimpleNamespace(global_game=SimpleNamespace(battle=battle, costume_config=None))
    task = SimpleNamespace(config=config, device=object(), current_count=0)
    if handler is not None:
        task.run_general_battle = handler
    if navigator is not None:
        task.navigator = navigator
    if match_page_once is not None:
        task.match_page_once = match_page_once
    return task


class FallbackObjectShapeTests(unittest.TestCase):
    """钉死根因前提：裸兜底对象没有 GameUi 的页面检测方法。"""

    def test_bare_general_battle_lacks_gameui_detection_helpers(self):
        self.assertFalse(hasattr(GeneralBattle, '_detect_current_page'))
        self.assertFalse(hasattr(GeneralBattle, '_default_detect_categories'))
        self.assertFalse(hasattr(GeneralBattle, 'get_current_page'))

    def test_fallback_object_only_exposes_injected_navigation(self):
        task = _FallbackLikeBattle()
        self.assertIsInstance(task.navigator, _StubNavigator)
        self.assertTrue(callable(task.match_page_once))
        self.assertFalse(hasattr(task, '_detect_current_page'))
        self.assertFalse(hasattr(task, '_default_detect_categories'))


class ExitBattleOnFallbackTests(unittest.TestCase):
    """``exit_battle`` 必须在裸兜底对象上正常工作（复现并修复 AttributeError）。"""

    def test_exit_battle_completes_on_bare_fallback_object(self):
        """回归：兜底对象上退出必须走完并返回 True，不得抛 AttributeError。"""
        task = _FallbackLikeBattle(exit_clicks_before_result=1)
        result = task.exit_battle()

        self.assertTrue(result)
        self.assertEqual(task.events, ['exit'])
        # 结算页被识别后应记录为当前页面（detect_page_in -> _detect_pages 的副作用）。
        self.assertEqual(task.navigator.current_page, page_battle_result)

    def test_exit_battle_consumes_confirm_dialog_first(self):
        """旧行为：先点掉「确认退出战斗吗」弹窗，再退出（确认资产为共享 I_UI_CONFIRM）。"""
        task = _FallbackLikeBattle(exit_clicks_before_result=1, confirm_required=2)
        result = task.exit_battle()

        self.assertTrue(result)
        self.assertEqual(task.events, ['confirm', 'confirm', 'exit'])

    def test_exit_battle_handles_delayed_result_page(self):
        """结果页延迟出现（需连点退出多次）时链路仍应走完。"""
        task = _FallbackLikeBattle(exit_clicks_before_result=3)
        result = task.exit_battle()

        self.assertTrue(result)
        self.assertEqual(task.events, ['exit', 'exit', 'exit'])

    def test_exit_battle_returns_false_without_exit_button(self):
        """旧行为：不在战斗页（无退出按钮）时直接返回 False，不做任何点击。"""
        task = _FallbackLikeBattle(initial_current=page_reward)
        result = task.exit_battle()

        self.assertFalse(result)
        self.assertEqual(task.events, [])


class RunTaskOrDefaultBattleTests(unittest.TestCase):
    """``run_task_or_default_general_battle`` 的分支与兜底守卫。"""

    def test_uses_task_handler_with_quick_exit_config_on_takeover_exit(self):
        calls = []

        def handler(config=None):
            calls.append(config)
            return True

        task = _fake_task('exit', handler=handler)
        self.assertTrue(run_task_or_default_general_battle(task))

        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(calls[0])
        self.assertTrue(calls[0].quick_exit)

    def test_uses_task_handler_without_config_on_takeover_finish(self):
        calls = []

        def handler(config=None):
            calls.append(config)
            return True

        task = _fake_task('finish', handler=handler)
        self.assertTrue(run_task_or_default_general_battle(task))

        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0])

    def test_returns_false_when_no_handler_and_no_navigation(self):
        task = _fake_task('exit')
        self.assertFalse(run_task_or_default_general_battle(task))


class GenericFallbackPathTests(unittest.TestCase):
    """任意任务（无 ``run_general_battle``）随时可能因突发页面/弹窗进入兜底战斗链路。

    这里直接驱动 ``run_task_or_default_general_battle`` **在生产中真正造出的**那个
    ``GeneralBattle`` 兜底对象（而非手工替身），验证其 ``exit_battle`` 能走完。
    """

    def test_production_fallback_object_survives_exit_battle(self):
        captured = []
        original_run_general_battle = GeneralBattle.run_general_battle
        original_check_costume = GeneralBattle.check_costume

        def capture(self, *args, **kwargs):
            captured.append(self)
            return True

        # 兜底对象需真实构造（BaseTask.__init__ 会调用 check_costume 做皮肤切换），
        # 单元测试里把该设备相关副作用替换掉。
        GeneralBattle.run_general_battle = capture
        GeneralBattle.check_costume = lambda self, *args, **kwargs: None
        try:
            task = _fake_task(
                'exit',
                navigator=_StubNavigator(),
                match_page_once=lambda page: False,
            )
            self.assertTrue(run_task_or_default_general_battle(task))
        finally:
            GeneralBattle.run_general_battle = original_run_general_battle
            GeneralBattle.check_costume = original_check_costume

        self.assertEqual(len(captured), 1)
        fallback = captured[0]
        self.assertIsInstance(fallback, GeneralBattle)
        # 生产兜底对象的关键特征：不具备 GameUi 的页面检测方法。
        self.assertFalse(hasattr(fallback, '_detect_current_page'))
        self.assertFalse(hasattr(fallback, '_default_detect_categories'))

        # 用脚本化替身驱动这个**真实兜底对象**的 exit_battle。
        fallback.current = None
        fallback.match_page_once = lambda page: fallback.current is not None and page.key == fallback.current.key
        fallback.screenshot = lambda: None
        fallback.maybe_screenshot = lambda soft_skip=False: None
        fallback.prepare_appear_cache = lambda targets: None
        fallback.ui_click_until_disappear = lambda click, interval=1: False
        fallback.appear = lambda button, **kwargs: button is fallback.I_EXIT and fallback.current is None

        def appear_then_click(button, **kwargs):
            if button is fallback.I_EXIT:
                fallback.current = page_battle_result
                return True
            return False

        fallback.appear_then_click = appear_then_click

        self.assertTrue(fallback.exit_battle())
        self.assertEqual(fallback.navigator.current_page, page_battle_result)


if __name__ == '__main__':
    unittest.main()
