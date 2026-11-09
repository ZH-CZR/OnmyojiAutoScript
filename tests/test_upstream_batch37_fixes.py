# This Python file uses the following encoding: utf-8
"""批次 37 上游修复回归测试。

本轮从 ``xylolit-mu/self`` 手工移植 4 组小修（不 cherry-pick）：
1. ``dd96057e``：御魂自选活动弹窗遮挡战斗结算 -> 新增 ``I_GB_CLOSE_RED``，
   ``Orochi`` 在结算/奖励/未知页三处先关弹窗；
2. ``38a8f00d``：庭院右侧活动栏目最多轮换 8 次找活动入口（寄养开关部分本地已有
   ``utilize_harvest``，不重复引入）；
3. ``904686c1``：逢魔 boss 页 3 轮重进仍打不开时不再 ``GameStuckError``，改为
   记录失败并结束本轮；
4. ``18ededee``：pass/boss 门票 OCR 为 0 时先进一次战复核，确认真的没票才结束。
"""
import inspect
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from module.exception import GamePageUnknownError
from tasks.ActivityShikigami import page as act_page
from tasks.ActivityShikigami.base_act import BaseAct, TicketsNotEnough
from tasks.Component.BaseActivity.base_activity import BaseActivity
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.DemonEncounter.script_task import ScriptTask as DemonEncounterTask
from tasks.Orochi.script_task import ScriptTask as OrochiTask


class OrochiSoulChoicePopupTests(unittest.TestCase):
    def test_asset_defined(self):
        rule = GeneralBattleAssets.I_GB_CLOSE_RED
        self.assertEqual(tuple(rule.roi_front), (1108, 128, 45, 41))
        self.assertEqual(tuple(rule.roi_back), (1108, 128, 45, 41))
        self.assertEqual(rule.threshold, 0.8)

    def test_image_json_matches(self):
        data = json.loads(
            Path('tasks/Component/GeneralBattle/gb/image.json').read_text(encoding='utf-8')
        )
        entry = {item['itemName']: item for item in data}['gb_close_red']
        rule = GeneralBattleAssets.I_GB_CLOSE_RED
        self.assertEqual(entry['imageName'], 'gb_gb_close_red.png')
        self.assertEqual(entry['roiFront'], ','.join(map(str, rule.roi_front)))
        self.assertEqual(entry['roiBack'], ','.join(map(str, rule.roi_back)))
        self.assertEqual(entry['threshold'], rule.threshold)

    def test_image_file_exists(self):
        self.assertTrue(
            Path('tasks/Component/GeneralBattle/gb/gb_gb_close_red.png').is_file()
        )

    def test_close_helper(self):
        source = inspect.getsource(OrochiTask._close_orochi_soul_choice_popup)
        self.assertIn('self.I_GB_CLOSE_RED', source)
        self.assertIn('appear_then_click', source)

    def test_handlers_close_popup_first(self):
        for handler in (
            OrochiTask._handle_result,
            OrochiTask._handle_reward,
            OrochiTask._handle_missing_battle_page,
        ):
            source = inspect.getsource(handler)
            self.assertIn('_close_orochi_soul_choice_popup', source, handler.__name__)
            self.assertIn('context.reward_no_battle_ts = None', source, handler.__name__)


class ActivityEntryRotationTests(unittest.TestCase):
    @staticmethod
    def _make_task(results):
        """results: 每次 appear 的返回值序列，用完后一直 False。"""
        calls = {'toggle': 0}
        state = {'appear': 0}

        def appear(_rule):
            index = state['appear']
            state['appear'] += 1
            return results[index] if index < len(results) else False

        task = SimpleNamespace(
            screenshot=lambda: None,
            appear=appear,
            appear_then_click=lambda _rule, interval=0: calls.__setitem__('toggle', calls['toggle'] + 1) or True,
        )
        return task, calls

    def test_max_tries_is_eight(self):
        self.assertEqual(act_page.ACTIVITY_COLUMN_SWITCH_MAX_TRIES, 8)

    def test_found_after_two_switches(self):
        task, calls = self._make_task([False, False, True])
        with patch('tasks.ActivityShikigami.page.time.sleep'):
            self.assertTrue(act_page.find_activity_entry(task))
        self.assertEqual(calls['toggle'], 2)

    def test_gives_up_after_max_tries(self):
        task, calls = self._make_task([])
        with patch('tasks.ActivityShikigami.page.time.sleep'):
            with self.assertRaises(GamePageUnknownError):
                act_page.find_activity_entry(task)
        self.assertEqual(calls['toggle'], act_page.ACTIVITY_COLUMN_SWITCH_MAX_TRIES)

    def test_page_hook_uses_rotation(self):
        self.assertIn(act_page.find_activity_entry, act_page.page_act.on_enter_failure)
        from tasks.Component.RightActivity.assets import RightActivityAssets

        self.assertNotIn(
            RightActivityAssets.I_TOGGLE_BUTTON, act_page.page_act.on_enter_failure
        )


class _FakeAct(BaseAct):
    """把只读的 ``climb_type`` 固定成 pass，便于直接驱动战斗/门票逻辑。"""

    @property
    def climb_type(self):
        return 'pass'


class DemonEncounterBossFallbackTests(unittest.TestCase):
    def test_boss_page_failure_ends_task(self):
        source = inspect.getsource(DemonEncounterTask.execute_boss)
        self.assertIn('treat boss as already challenged today', source)
        self.assertIn("raise TaskEnd('DemonEncounter')", source)
        # 仅保留「找不到搜索按钮」这一处 GameStuckError，boss 页打不开不再抛卡死
        self.assertEqual(source.count('raise GameStuckError('), 1)


class ActivityTicketVerificationTests(unittest.TestCase):
    @staticmethod
    def _make_task(fire_result=True):
        task = object.__new__(_FakeAct)
        task.screenshot = lambda *a, **k: None
        task.is_in_battle = lambda *a, **k: False
        task.appear = lambda *a, **k: False
        task.appear_then_click = lambda *a, **k: False
        task.ocr_appear_click = lambda *a, **k: fire_result
        task.device = SimpleNamespace(click_record_clear=lambda: None)
        return task

    def test_base_act_inherits_base_activity(self):
        self.assertTrue(issubclass(BaseAct, BaseActivity))
        self.assertTrue(callable(BaseAct.verify_zero_ticket))

    def test_enter_battle_fallback_returns_false(self):
        task = self._make_task(fire_result=True)
        self.assertFalse(task.enter_battle(max_times=1))

    def test_enter_battle_normal_path_still_raises(self):
        task = self._make_task(fire_result=True)
        with patch('tasks.ActivityShikigami.base_act.random.randint', return_value=1):
            with self.assertRaises(TicketsNotEnough):
                task.enter_battle()

    def test_enter_battle_success(self):
        task = self._make_task()
        task.is_in_battle = lambda *a, **k: True
        self.assertTrue(task.enter_battle(max_times=1))

    def test_zero_ticket_marks_verification(self):
        task = object.__new__(_FakeAct)
        task.screenshot = lambda *a, **k: None
        task.device = SimpleNamespace(image=None)
        task.O_REMAIN_PASS = SimpleNamespace(ocr_digit=lambda _image: 0)
        self.assertTrue(task.check_tickets_enough())
        self.assertTrue(task._ticket_needs_verification)

    def test_run_common_uses_verification(self):
        source = inspect.getsource(BaseAct._run_common)
        self.assertIn('self._ticket_needs_verification', source)
        self.assertIn('verify_zero_ticket', source)
        self.assertIn('enter_battle(max_times=1)', source)
        self.assertIn('raise TicketsNotEnough', source)

    def test_check_tickets_resets_flag(self):
        source = inspect.getsource(BaseAct.check_tickets_enough)
        self.assertIn('self._ticket_needs_verification = False', source)
        self.assertIn("self.climb_type in (\"pass\", \"boss\") and remain_times <= 0", source)


if __name__ == '__main__':
    unittest.main()
