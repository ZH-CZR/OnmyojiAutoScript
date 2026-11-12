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
from module.exception import GameStuckError, TaskEnd
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

    def test_detail_route_buttons_allow_horizontal_and_vertical_shift(self):
        # 错误截图中按钮实际位置；原 98px 搜索框容不下右移后的完整模板。
        for x, ys in ((1058, (284, 360, 436, 512)),
                      (1072, (282, 360, 437, 515))):
            with self.subTest(x=x):
                self.image.fill(90)
                for slot, y in enumerate(ys, 1):
                    self.paste(getattr(self.task, f'I_GOTO_{slot}'), x, y)
                for slot in range(1, 5):
                    rule = getattr(self.task, f'I_GOTO_{slot}')
                    self.assertTrue(rule.match(self.image))
                    self.assertEqual(rule.threshold, 0.8)
                # 相邻行有按钮不能使空白本行误判为存在。
                self.image[270:334] = 90
                self.assertFalse(self.task.I_GOTO_1.match(self.image))

    def test_all_four_columns_require_red_plus_and_keep_type_filter(self):
        self.paste(self.task.I_WQ_PANEL)
        for slot, reward in enumerate(('GOLD', 'DOG_FOOD', 'SUSHI', 'JADE'), 1):
            self.paste(getattr(self.task, f'I_WQ_INVITE_{slot}'))
            self.paste(getattr(self.task, f'I_WQ_COOPERATION_TYPE_{reward}_{slot}'),
                       252 + 268*(slot-1), 526)
        info = self.task.get_cooperation_info()
        self.assertEqual([item['type'] for item in info], [
            CooperationType.Gold, CooperationType.Food, CooperationType.Sushi, CooperationType.Jade])
        for slot in range(1, 5):
            self.assertEqual(self.task._cooperation_allowed(getattr(self.task, f'I_WQ_INVITE_{slot}')),
                             slot != 4)

    def test_regular_card_with_coins_and_missing_first_button_do_not_confuse_slots(self):
        self.paste(self.task.I_WQ_PANEL)
        self.paste(self.task.I_WQ_COOPERATION_TYPE_GOLD_1, 252, 526)
        self.paste(self.task.I_WQ_INVITE_4)
        self.paste(self.task.I_WQ_COOPERATION_TYPE_CAT_FOOD_4, 1056, 526)
        info = self.task.get_cooperation_info()
        self.assertEqual([(item['type'], item['inviteBtn']) for item in info],
                         [(CooperationType.Food, self.task.I_WQ_INVITE_4)])

    def test_matching_invite_without_wanted_panel_is_rejected(self):
        self.paste(self.task.I_WQ_INVITE_1)
        self.paste(self.task.I_WQ_COOPERATION_TYPE_GOLD_1, 252, 526)
        self.assertEqual(self.task.get_cooperation_info(), [])

    def test_tracking_buttons_are_distinct(self):
        self.paste(self.task.I_TRACE_ENABLE)
        self.assertTrue(self.task.appear(self.task.I_TRACE_ENABLE))
        self.assertFalse(self.task.appear(self.task.I_TARCE_DISENABLE))
        self.paste(self.task.I_TARCE_DISENABLE)
        self.assertTrue(self.task.appear(self.task.I_TARCE_DISENABLE))
        self.assertFalse(self.task.appear(self.task.I_TRACE_ENABLE))

    def test_click_points_stay_inside_red_plus_even_after_template_match(self):
        self.paste(self.task.I_WQ_PANEL)
        for slot in range(1, 5):
            button = getattr(self.task, f'I_WQ_INVITE_{slot}')
            self.paste(button)
            self.assertTrue(self.task.appear(button))
            click = self.task._cooperation_click(button)
            self.assertEqual(tuple(click.roi_front), (121+268*(slot-1), 403, 26, 26))
            self.assertNotEqual(tuple(button.roi_front), tuple(click.roi_front))
            for _ in range(100):
                x, y = click.coord()
                self.assertTrue(117+268*(slot-1) <= x <= 153+268*(slot-1))
                self.assertTrue(397 <= y <= 435)

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

    def test_open_panel_without_both_action_buttons_is_complete(self):
        self.assertFalse(self.task.pre_work())
        self.task.click.assert_not_called()
        self.task.invite_five.assert_not_called()
        self.task.all_cooperation_invite.assert_not_called()
        self.task.ui_goto_page.assert_not_called()

    def test_title_before_delayed_buttons_does_not_finish_the_round(self):
        frames = [0]
        def screenshot():
            frames[0] += 1
            if frames[0] == 4:
                self.visible.add(self.task.I_TRACE_ENABLE.name)
        self.task.screenshot.side_effect = screenshot
        with patch('tasks.WantedQuests.script_task.sleep'):
            self.assertTrue(self.task.pre_work())
        self.assertIs(self.task.ui_current, page_exploration)
        self.task.click.assert_any_call(self.task.I_TRACE_ENABLE, interval=3)

    def test_unconfirmed_panel_or_retry_limit_cannot_advance_next_round(self):
        self.task.play_count = 2
        self.task.next_run = Mock()
        with self.assertRaisesRegex(GameStuckError, '不能确认本轮已完成'):
            self.task.run()
        self.task.next_run.assert_not_called()

    def test_close_button_without_panel_title_is_not_completion(self):
        self.visible = {self.task.I_BACK_RED.name}
        done_timer, prepare_timer = Mock(), Mock()
        done_timer.started.return_value = done_timer.reached.return_value = True
        prepare_timer.start.return_value = prepare_timer
        prepare_timer.reached.return_value = False
        with patch('tasks.WantedQuests.script_task.Timer', side_effect=[done_timer, prepare_timer]):
            with self.assertRaisesRegex(GameStuckError, '面板标题未确认'):
                self.task.pre_work()

    def test_completed_panel_finishes_run_and_schedules_next_round(self):
        self.task.next_run = Mock()
        self.task.play_run = Mock()
        self.task.run_switch_soul = Mock()
        with self.assertRaises(TaskEnd):
            self.task.run()
        self.task.next_run.assert_called_once_with()
        self.task.play_run.assert_not_called()
        self.task.run_switch_soul.assert_not_called()

    def test_one_action_button_or_unconfirmed_panel_does_not_mean_complete(self):
        for visible in ({self.task.I_WQ_PANEL.name, self.task.I_TRACE_ENABLE.name},
                        {self.task.I_WQ_PANEL.name, self.task.I_WQ_GOTO_EXPLORATION.name},
                        set()):
            with self.subTest(visible=visible):
                self.task.play_count = 0
                self.visible = visible.copy()
                self.task.appear_then_click = Mock(return_value=False)
                prepare_timer = Mock()
                prepare_timer.start.return_value = prepare_timer
                prepare_timer.reached.side_effect = [False, True]
                done_timer = Mock()
                done_timer.started.return_value = False
                with patch('tasks.WantedQuests.script_task.Timer', side_effect=[done_timer, prepare_timer]):
                    with self.assertRaisesRegex(GameStuckError, '悬赏面板追踪准备超时'):
                        self.task.pre_work()
                prepare_timer.reset.assert_not_called()

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

    def test_invitation_open_uses_red_plus_and_confirms_dialog(self):
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

    def test_dialog_opening_between_screenshots_does_not_skip_invitation(self):
        panel = {self.task.I_WQ_PANEL.name, self.task.I_WQ_INVITE_1.name,
                 self.task.I_WQ_COOPERATION_TYPE_GOLD_1.name}
        frames = iter((panel, {self.task.I_WQ_INVITE_ENSURE.name}))

        def screenshot():
            self.visible = next(frames)

        self.task.screenshot.side_effect = screenshot
        self.assertTrue(self.task._open_cooperation_invite(self.task.I_WQ_INVITE_1))
        self.assertEqual(self.task.screenshot.call_count, 2)
        self.task.click.assert_called_once_with(self.task.C_WQ_INVITE_1, interval=2.5)

    def test_dialog_transition_waits_without_clicking_hidden_entry(self):
        panel = {self.task.I_WQ_PANEL.name, self.task.I_WQ_INVITE_1.name,
                 self.task.I_WQ_COOPERATION_TYPE_GOLD_1.name}
        # 标题可能仍能从遮罩后识别，入口已消失；也可能整帧都在过渡。
        frames = iter((panel, {self.task.I_WQ_PANEL.name}, set(),
                       {self.task.I_WQ_INVITE_ENSURE.name}))

        def screenshot():
            self.visible = next(frames)

        self.task.screenshot.side_effect = screenshot
        self.assertTrue(self.task._open_cooperation_invite(self.task.I_WQ_INVITE_1))
        self.assertEqual(self.task.screenshot.call_count, 4)
        self.task.click.assert_called_once_with(self.task.C_WQ_INVITE_1, interval=2.5)

    def test_missing_entry_times_out_in_invitation_instead_of_skipping(self):
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = [False, True]
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaisesRegex(GameStuckError, '悬赏邀请好友表单未打开'):
                self.task._open_cooperation_invite(self.task.I_WQ_INVITE_1)
        self.task.click.assert_not_called()
        timer.reset.assert_not_called()

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
