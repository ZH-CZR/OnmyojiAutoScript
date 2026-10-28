"""New four-card WantedQuests layout; no device, RPC server or game input."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import numpy as np

from module.atom.click import RuleClick
from module.atom.image import RuleImage
from module.exception import GameStuckError
from tasks.GameUi.page import page_exploration
from tasks.WantedQuests.assets import WantedQuestsAssets
from tasks.WantedQuests.config import CooperationType, WantedQuestsConfig
from tasks.WantedQuests.script_task import ScriptTask


def make_task():
    task = ScriptTask.__new__(ScriptTask)
    task.config = SimpleNamespace(wanted_quests=SimpleNamespace(
        wanted_quests_config=WantedQuestsConfig(cooperation_type='GoldAndFoodAndSushi')))
    task.screenshot = Mock()
    task.click = Mock()
    for name, rule in vars(WantedQuestsAssets).items():
        if isinstance(rule, (RuleClick, RuleImage)):
            setattr(task, name, copy.deepcopy(rule))
    return task


class WantedUiAssetTest(unittest.TestCase):
    def setUp(self):
        self.task = make_task()
        self.image = np.full((720, 1280, 3), 90, dtype=np.uint8)
        self.task.appear = Mock(side_effect=lambda rule: rule.match(self.image))

    def paste(self, rule, x=None, y=None):
        template = rule.image
        px, py = rule.roi_front[:2]
        x, y = px if x is None else x, py if y is None else y
        self.image[y:y+template.shape[0], x:x+template.shape[1]] = template

    def test_all_four_columns_require_invite_text_and_keep_type_filter(self):
        self.paste(self.task.I_WQ_PANEL)
        for slot, reward in enumerate(('GOLD', 'DOG_FOOD', 'SUSHI', 'JADE'), 1):
            self.paste(getattr(self.task, f'I_WQ_INVITE_{slot}'))
            self.paste(getattr(self.task, f'I_WQ_COOPERATION_TYPE_{reward}_{slot}'),
                       232 + 282*(slot-1), 540)
        info = self.task.get_cooperation_info()
        self.assertEqual([item['type'] for item in info], [
            CooperationType.Gold, CooperationType.Food, CooperationType.Sushi, CooperationType.Jade])
        for slot in range(1, 5):
            self.assertEqual(self.task._cooperation_allowed(getattr(self.task, f'I_WQ_INVITE_{slot}')),
                             slot != 4)

    def test_regular_card_with_coins_and_missing_first_button_do_not_confuse_slots(self):
        self.paste(self.task.I_WQ_PANEL)
        self.paste(self.task.I_WQ_COOPERATION_TYPE_GOLD_1, 232, 540)
        self.paste(self.task.I_WQ_INVITE_4)
        self.paste(self.task.I_WQ_COOPERATION_TYPE_CAT_FOOD_4, 1078, 540)
        info = self.task.get_cooperation_info()
        self.assertEqual([(item['type'], item['inviteBtn']) for item in info],
                         [(CooperationType.Food, self.task.I_WQ_INVITE_4)])

    def test_matching_invite_without_wanted_panel_is_rejected(self):
        self.paste(self.task.I_WQ_INVITE_1)
        self.paste(self.task.I_WQ_COOPERATION_TYPE_GOLD_1, 232, 540)
        self.assertEqual(self.task.get_cooperation_info(), [])

    def test_tracking_buttons_are_distinct(self):
        self.paste(self.task.I_TRACE_ENABLE)
        self.assertTrue(self.task.appear(self.task.I_TRACE_ENABLE))
        self.assertFalse(self.task.appear(self.task.I_TARCE_DISENABLE))
        self.paste(self.task.I_TARCE_DISENABLE)
        self.assertTrue(self.task.appear(self.task.I_TARCE_DISENABLE))
        self.assertFalse(self.task.appear(self.task.I_TRACE_ENABLE))

    def test_click_points_stay_in_user_bar_even_after_template_match(self):
        self.paste(self.task.I_WQ_PANEL)
        for slot in range(1, 5):
            button = getattr(self.task, f'I_WQ_INVITE_{slot}')
            self.paste(button)
            self.assertTrue(self.task.appear(button))
            click = self.task._cooperation_click(button)
            self.assertEqual(tuple(click.roi_front), (98+282*(slot-1), 405, 248, 25))
            self.assertNotEqual(tuple(button.roi_front), tuple(click.roi_front))
            for _ in range(100):
                x, y = click.coord()
                self.assertTrue(96+282*(slot-1) < x < 348+282*(slot-1))
                self.assertTrue(403 < y < 432)

    def test_json_and_generated_assets_agree(self):
        root = Path(__file__).resolve().parents[1] / 'tasks/WantedQuests'
        for relative, prefix in (('invite/image.json', 'I_'), ('invite/click.json', 'C_'),
                                 ('wq/image.json', 'I_')):
            for item in json.loads((root / relative).read_text('utf-8')):
                rule = getattr(self.task, prefix + item['itemName'].upper())
                self.assertEqual(tuple(rule.roi_back), tuple(map(int, item['roiBack'].split(','))))
                self.assertEqual(tuple(rule.roi_front), tuple(map(int, item['roiFront'].split(','))))
                # 原好友槽位仅用作点击坐标，从未用于图像匹配。
                if prefix == 'I_' and not item['itemName'].startswith('wq_friend_'):
                    self.assertTrue(Path(rule.file).is_file())


class WantedUiFlowTest(unittest.TestCase):
    def setUp(self):
        self.task = make_task()
        self.visible = {self.task.I_WQ_PANEL.name}
        self.task.appear = Mock(side_effect=lambda rule: rule.name in self.visible)
        self.task.appear_then_click = Mock(side_effect=self.click_if_visible)
        self.task.click.side_effect = self.click
        self.task.ui_goto_page = Mock()
        self.task.invite_five = Mock()
        self.task.all_cooperation_invite = Mock()
        self.task.play_count = 0

    def click_if_visible(self, rule, **kwargs):
        if rule.name not in self.visible:
            return False
        self.task.click(rule, **kwargs)
        return True

    def click(self, rule, **kwargs):
        if rule is self.task.I_TRACE_ENABLE:
            self.visible.discard(rule.name)
            self.visible.update((self.task.I_TARCE_DISENABLE.name,
                                 self.task.I_WQ_GOTO_EXPLORATION.name))
        elif rule is self.task.I_WQ_GOTO_EXPLORATION:
            self.visible = {page_exploration.check_button.name}
        return True

    def test_prepare_tracks_and_goes_straight_to_exploration(self):
        self.visible.add(self.task.I_TRACE_ENABLE.name)
        self.assertTrue(self.task.pre_work())
        self.assertEqual(self.task.click.call_args_list, [
            call(self.task.I_TRACE_ENABLE, interval=3),
            call(self.task.I_WQ_GOTO_EXPLORATION, interval=1)])
        self.task.ui_goto_page.assert_not_called()
        self.assertIs(self.task.ui_current, page_exploration)

    def test_fourth_slot_triggers_named_or_default_invitation(self):
        for name in ('', '测试好友'):
            with self.subTest(name=name):
                self.visible = {self.task.I_WQ_PANEL.name, self.task.I_TARCE_DISENABLE.name,
                                self.task.I_WQ_GOTO_EXPLORATION.name, self.task.I_WQ_INVITE_4.name}
                self.task.config.wanted_quests.wanted_quests_config.invite_friend_name = name
                self.task.play_count = 0
                self.assertTrue(self.task.pre_work())
        self.task.invite_five.assert_called_once_with()
        self.task.all_cooperation_invite.assert_called_once_with('测试好友')

    def test_exploration_background_does_not_count_until_panel_is_gone(self):
        self.visible.update((page_exploration.check_button.name, self.task.I_TARCE_DISENABLE.name,
                             self.task.I_WQ_GOTO_EXPLORATION.name))
        self.task._goto_wanted_exploration()
        self.task.click.assert_called_once_with(self.task.I_WQ_GOTO_EXPLORATION, interval=1)

    def test_direct_navigation_timeout_does_not_fall_back_to_courtyard(self):
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = [False, True]
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaises(GameStuckError):
                self.task._goto_wanted_exploration()
        self.task.ui_goto_page.assert_not_called()
        self.task.click.assert_not_called()
        timer.reset.assert_not_called()

    def test_invitation_open_uses_click_bar_and_confirms_dialog(self):
        self.visible.update((self.task.I_WQ_INVITE_4.name,
                             self.task.I_WQ_COOPERATION_TYPE_GOLD_4.name))

        def open_dialog(rule, **kwargs):
            self.visible = {self.task.I_WQ_INVITE_ENSURE.name}
            return True

        self.task.click.side_effect = open_dialog
        self.assertTrue(self.task._open_cooperation_invite(self.task.I_WQ_INVITE_4))
        self.task.click.assert_called_once_with(self.task.C_WQ_INVITE_4, interval=2.5)

    def test_type_change_stops_invitation_retries(self):
        self.visible.update((self.task.I_WQ_INVITE_1.name,
                             self.task.I_WQ_COOPERATION_TYPE_GOLD_1.name))

        def shift(rule, **kwargs):
            self.visible.discard(self.task.I_WQ_COOPERATION_TYPE_GOLD_1.name)
            self.visible.add(self.task.I_WQ_COOPERATION_TYPE_JADE_1.name)
            return True

        self.task.click.side_effect = shift
        self.assertFalse(self.task._open_cooperation_invite(self.task.I_WQ_INVITE_1))
        self.task.click.assert_called_once_with(self.task.C_WQ_INVITE_1, interval=2.5)

    def test_invitation_total_timeout_is_not_reset_by_clicks(self):
        self.visible.update((self.task.I_WQ_INVITE_1.name,
                             self.task.I_WQ_COOPERATION_TYPE_GOLD_1.name))
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = [False, True]
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaises(GameStuckError):
                self.task._open_cooperation_invite(self.task.I_WQ_INVITE_1)
        self.task.click.assert_called_once_with(self.task.C_WQ_INVITE_1, interval=2.5)
        timer.reset.assert_not_called()


if __name__ == '__main__':
    unittest.main()
