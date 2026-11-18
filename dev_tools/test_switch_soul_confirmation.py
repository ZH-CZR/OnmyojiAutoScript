import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import numpy as np

from module.config.config import Config
from module.exception import GameStuckError
from tasks.Component.Costume.config import ShikigamiType
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.Hunt.script_task import ScriptTask as Hunt


class SwitchSoulConfirmationTest(unittest.TestCase):
    def setUp(self):
        self.task = SwitchSoul(Config('template'), device=SimpleNamespace(image=None))
        self.now = 100.0
        self.frame = 0
        self.addCleanup(setattr, SwitchSoul, '_current_switch_soul', SwitchSoul._current_switch_soul)
        patches = ExitStack()
        self.addCleanup(patches.close)
        patches.enter_context(patch('module.base.timer.time', SimpleNamespace(time=lambda: self.now)))
        patches.enter_context(patch('tasks.Component.SwitchSoul.switch_soul.sleep'))
        patches.enter_context(patch.object(self.task.O_SS_GROUP_NAME, 'detect_and_ocr',
                                           return_value=[SimpleNamespace(ocr_text='寮活动')]))
        self.task.screenshot = Mock(side_effect=self.screenshot)
        self.task.swipe = Mock()
        self.task.click = Mock()

    def screenshot(self):
        self.now += 0.4
        self.frame += 1

    def simulate(self, *, group_selected=True, popup_frame=6, popup_gone_frame=9):
        task = self.task

        def appear(rule):
            if rule is task.I_SOU_CHECK_GROUP_3:
                return group_selected
            if rule in (task.I_UI_SURE, task.I_SOU_SWITCH_SURE):
                return popup_frame <= self.frame < popup_gone_frame
            return rule in (task.I_SOU_SWITCH_1, task.I_SOU_TEAM_PRESENT)

        task.appear = Mock(side_effect=appear)
        task.appear_then_click = Mock(side_effect=lambda rule, **kwargs: appear(rule))

    def test_selected_group_then_one_equip_and_one_confirmation(self):
        self.simulate()
        self.task.switch_soul_one(3, 1)
        self.task.click.assert_called_once_with(self.task.C_SOU_GROUP_3)
        accepted = [args for args in self.task.appear_then_click.call_args_list
                    if args.args[0] is self.task.I_SOU_SWITCH_1]
        self.assertEqual(accepted, [call(self.task.I_SOU_SWITCH_1, interval=None)])
        self.assertEqual(self.task.appear_then_click.call_count, 3)
        self.assertGreaterEqual(self.frame, 10)

    def test_unconfirmed_group_never_clicks_equip(self):
        self.simulate(group_selected=False)
        with self.assertRaisesRegex(GameStuckError, '未确认选中第 3 组'):
            self.task.switch_soul_one(3, 1)
        self.task.appear_then_click.assert_not_called()

    def test_missing_or_stuck_confirmation_fails_without_retrying_equip(self):
        for popup_frame in (6, 1000):
            with self.subTest(popup_frame=popup_frame):
                self.frame = 0
                self.simulate(popup_frame=popup_frame, popup_gone_frame=1000)
                with self.assertRaisesRegex(GameStuckError, '装配未确认'):
                    self.task.switch_soul_one(3, 1)
                attempts = [args for args in self.task.appear_then_click.call_args_list
                            if args.args[0] is self.task.I_SOU_SWITCH_1]
                self.assertEqual(len(attempts), 1)

    def test_skin_11_uses_blue_selected_border_for_the_target_row(self):
        task = self.task
        task.config.model.global_game.costume_config.costume_shikigami_type = ShikigamiType.COSTUME_SHIKIGAMI_11
        image = np.full((720, 1280, 3), (67, 123, 207), dtype=np.uint8)
        image[315:337, 1088:1093] = (76, 155, 224)
        image[315:337, 1236:1241] = (75, 151, 221)
        task.device.image = image
        self.assertFalse(task._soul_group_selected(3, task.C_SOU_GROUP_3))
        self.assertTrue(task._soul_group_selected(4, task.C_SOU_GROUP_4))

    def test_kirin_bypasses_old_cache_and_does_not_challenge_after_failed_equip(self):
        task = Hunt(Config('template'), device=SimpleNamespace(image=None))
        task.config.hunt.kirin_config.enable = True
        task.config.hunt.kirin_config.switch_group_team = '3,1'
        task.check_datetime = Mock(return_value=True)
        task.ui_goto_page = Mock(return_value=True)
        task.click_preset = Mock()
        task.switch_souls = Mock(side_effect=GameStuckError('装配未确认'))
        task.kirin = Mock()
        task.run_general_battle = Mock()
        SwitchSoul._current_switch_soul = '3,1'

        with self.assertRaisesRegex(GameStuckError, '装配未确认'):
            task.run()

        task.switch_souls.assert_called_once_with((3, 1))
        task.kirin.assert_not_called()
        task.run_general_battle.assert_not_called()
        self.assertEqual(SwitchSoul._current_switch_soul, '-')
