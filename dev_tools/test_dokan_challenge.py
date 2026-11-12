"""离线重现道馆被其他玩家击破后的选馆、确认和后续搜索，不操作游戏。"""

import ast
from collections import Counter, deque
from pathlib import Path
import re
import unicodedata
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class Rule:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class DokanChallengeTests(unittest.TestCase):
    def make_task(self, names, unavailable=(), welfare=(), bounties=None, toast=True, entry_delay=0):
        source = Path(__file__).resolve().parents[1] / 'tasks/Dokan/script_task.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ScriptTask')
        methods = [node for node in original.body if isinstance(node, ast.FunctionDef)
                   and node.name in ('challenge_selected_dokan', 'find_dokan', 'position_offset', 'open_dokan',
                                     'is_welfare_name', 'is_welfare_candidate')]
        module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(
            name='Task', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[]))
        self.clock = 0

        def sleep(seconds):
            self.clock += seconds

        scene = SimpleNamespace(RYOU_DOKAN_SCENE_FINDING_DOKAN='finding')
        namespace = dict(time=SimpleNamespace(monotonic=lambda: self.clock), sleep=sleep,
                         re=re, unicodedata=unicodedata, logger=Mock(), DokanScene=scene)
        exec(compile(module, str(source), 'exec'), namespace)
        task = namespace['Task']()
        task.find_dokan_list = []
        task.welfare_names = list(welfare)
        task.dokan_quit = False
        task.open_welfare = False
        task.has_welfare_badge = Mock(return_value=False)
        task.get_current_scene = Mock(return_value=(False, 'finding'))
        task.push_notify = Mock()
        task.save_image = Mock()
        task.swipe = Mock()
        task.ui_click = Mock()
        task.ui_click_until_disappear = Mock()
        task.wait_animate_stable = Mock()
        task.finish_task = Mock()
        task.dokan_switch_soul = Mock()
        self.selected = None
        self.card = False
        self.dialog = False
        self.entered = False
        self.pending_at = None
        self.message = ''
        self.message_at = 0
        self.events = []
        self.history = deque(maxlen=15)

        def record(button):
            self.events.append((self.selected, button))
            self.history.append(button)
            counts = sorted(Counter(self.history).values())
            if counts[0] >= 12 or len(counts) >= 2 and counts[0] >= 6 and counts[1] >= 6:
                raise AssertionError('触发全局点击次数保护')

        task.device = SimpleNamespace(image=object(), click_record_clear=self.history.clear)
        buttons = ('I_RYOU_DOKAN_CHECK', 'I_UI_SURE', 'I_CENTER_CHALLENGE',
                   'I_CENTER_GUANZHU_XIUXI', 'C_DOKAN_CANCEL_SELECT_DOKAN',
                   'C_DOKAN_CANCEL_SELECT_DOKAN_CHECK_ANIMATE', 'S_DOKAN_LIST_UP',
                   'C_DOKAN_REFRESH', 'I_UI_CONFIRM', 'I_RED_CLOSE',
                   'I_CREATE_DAOGUAN_SURE', 'I_CREATE_DAOGUAN_OK', 'I_CREATE_DAOGUAN')
        for button in buttons:
            setattr(task, button, button)
        matches = [(1, 1129, 100 + i * 146, 30, 30) for i in range(len(names))]
        task.I_RIGHTPAD_POINT_BOUNTY = Rule(roi_back=(0, 0, 1280, 720),
                                          match_all_any=Mock(return_value=matches))
        task.I_CENTER_POINT_PEOPLE_NUMBER = Rule(roi_back=(0, 0, 1280, 720), roi_front=(400, 400, 80, 30))
        task.O_DOKAN_RIGHTPAD_NAME = Rule(roi=None)
        task.O_DOKAN_RIGHTPAD_NAME.ocr = lambda image: names[(task.O_DOKAN_RIGHTPAD_NAME.roi[1] - 129) // 146]
        task.O_DOKAN_CENTER_PEOPLE_NUMBER = Rule(roi=None, detect_text=lambda image: '防守人数150人')
        bounties = bounties or {name: 400 for name in names}
        task.O_DOKAN_RIGHTPAD_BOUNTY = Rule(roi=None, ocr=lambda image: str(bounties[self.selected]))
        task.O_DOKAN_CHALLENGE_MESSAGE = Rule(ocr=lambda image:
            self.message if self.clock - self.message_at < 1.5 else '')

        def screenshot():
            self.clock += 0.1
            if self.pending_at is not None and self.clock >= self.pending_at:
                self.entered = True

        task.screenshot = screenshot

        def appear(button, **kwargs):
            if button == task.I_RYOU_DOKAN_CHECK:
                return self.entered
            if button == task.I_UI_SURE:
                return self.dialog
            if button == task.I_CENTER_CHALLENGE:
                return self.card and not self.dialog and not self.entered
            return button is task.I_CENTER_POINT_PEOPLE_NUMBER or button == task.I_CENTER_GUANZHU_XIUXI

        task.appear = appear

        def appear_then_click(button, **kwargs):
            if not appear(button):
                return False
            record(button)
            if button == task.I_CENTER_CHALLENGE:
                self.dialog = True
            elif button == task.I_UI_SURE:
                self.dialog = False
                if self.selected in unavailable:
                    if toast:
                        self.message = '您选择的道馆已经被他人击破，请尝试挑战其他道馆。'
                        self.message_at = self.clock
                elif self.pending_at is None:
                    self.pending_at = self.clock + entry_delay
            return True

        task.appear_then_click = appear_then_click

        def click(button, **kwargs):
            record(button)
            self.card = False

        task.click = click

        def select(click, stop, **kwargs):
            index = (task.I_RIGHTPAD_POINT_BOUNTY.roi_back[1] - 90) // 146
            self.selected = names[index]
            self.card = True
            return True

        task.ui_click_until_appear_or_timeout = Mock(side_effect=select)
        self.con = SimpleNamespace(fresh_num=1, min_people_num=-1, find_dokan_score=4.6, min_bounty=0)
        task.config = SimpleNamespace(dokan=SimpleNamespace(
            welfare_config=SimpleNamespace(welfare_enable=True, fresh_num_less_people=20),
            dokan_config=self.con))
        return task

    def challenge_names(self):
        return [name for name, button in self.events if button == 'I_CENTER_CHALLENGE']

    def test_defeated_welfare_guild_is_skipped_and_next_guild_opens(self):
        task = self.make_task(['樱途', '可挑战福利寮'], unavailable=['樱途'], welfare=['樱途', '可挑战福利寮'])
        self.assertTrue(task.find_dokan(self.con, welfare_flag=True))
        self.assertEqual(self.challenge_names(), ['樱途', '可挑战福利寮'])
        task.push_notify.assert_called_once()
        self.assertIn('可挑战福利寮', task.push_notify.call_args.kwargs['content'])
        self.assertTrue(task.open_welfare)
        self.assertTrue(task.dokan_quit)
        self.assertEqual(task.I_RIGHTPAD_POINT_BOUNTY.roi_back, (0, 0, 1280, 720))

    def test_reported_welfare_name_is_selected_after_loading_shipped_list(self):
        from tasks.Dokan.script_task import ScriptTask
        names = object.__new__(ScriptTask).welfare_name_str()
        task = self.make_task(['普通寮', '破晓'], welfare=names)
        self.assertTrue(task.find_dokan(self.con, welfare_flag=True))
        self.assertEqual(self.challenge_names(), ['破晓'])
        self.assertTrue(task.open_welfare)

    def test_normal_guild_search_continues_after_server_rejection(self):
        task = self.make_task(['失效普通寮', '可挑战普通寮'], unavailable=['失效普通寮'])
        self.assertTrue(task.find_dokan(self.con, welfare_flag=False))
        self.assertEqual(self.challenge_names(), ['失效普通寮', '可挑战普通寮'])
        self.assertFalse(task.open_welfare)
        self.assertFalse(task.dokan_quit)

    def test_failed_welfare_does_not_leak_flags_to_normal_guild(self):
        task = self.make_task(['樱途', '普通寮'], unavailable=['樱途'], welfare=['樱途'])
        self.assertTrue(task.find_dokan(self.con, welfare_flag=False))
        self.assertFalse(task.open_welfare)
        self.assertFalse(task.dokan_quit)

    def test_missed_toast_has_bounded_retries_and_continues_search(self):
        task = self.make_task(['失效寮', '可挑战寮'], unavailable=['失效寮'], toast=False)
        self.assertTrue(task.find_dokan(self.con, welfare_flag=False))
        self.assertEqual(self.challenge_names(), ['失效寮'] * 3 + ['可挑战寮'])
        self.assertEqual(sum(name == '失效寮' and button == 'I_UI_SURE' for name, button in self.events), 3)

    def test_delayed_success_waits_for_actual_entry(self):
        task = self.make_task(['普通寮'], entry_delay=8)
        self.assertTrue(task.find_dokan(self.con, welfare_flag=False))
        self.assertTrue(self.entered)
        self.assertGreaterEqual(self.clock, self.pending_at)
        task.push_notify.assert_called_once()

    def test_fallback_tries_next_lowest_score_after_rejection(self):
        task = self.make_task(['最低系数寮', '次低系数寮'], unavailable=['最低系数寮'],
                              bounties={'最低系数寮': 600, '次低系数寮': 750})
        self.con.fresh_num = 0
        self.con.find_dokan_score = 3
        self.assertTrue(task.find_dokan(self.con, welfare_flag=False))
        self.assertEqual(self.challenge_names(), ['最低系数寮', '次低系数寮'])
        self.assertIn('次低系数寮', task.push_notify.call_args.kwargs['content'])

    def test_unavailable_guild_is_not_retried_after_swiping_or_refresh(self):
        task = self.make_task(['樱途'], unavailable=['樱途'], welfare=['樱途'])
        self.con.fresh_num = 2
        self.assertFalse(task.find_dokan(self.con, welfare_flag=True))
        self.assertEqual(self.challenge_names(), ['樱途'])
        task.push_notify.assert_called_once_with(content='未找到福利寮')
        self.assertFalse(task.open_welfare)
        self.assertFalse(task.dokan_quit)

    def test_empty_fallback_has_no_invalid_index_or_click(self):
        task = self.make_task([])
        self.con.fresh_num = 0
        self.assertFalse(task.find_dokan(self.con, welfare_flag=False))
        self.assertEqual(self.events, [])
        task.push_notify.assert_not_called()

    def test_no_available_guild_ends_without_success_timestamp_or_soul_switch(self):
        task = self.make_task(['失效寮'], unavailable=['失效寮'])
        task.config.dokan.welfare_config.welfare_enable = False
        self.con.fresh_num = 0
        task.appear_rgb = Mock(return_value=True)
        task.open_dokan()
        task.finish_task.assert_called_once()
        task.dokan_switch_soul.assert_not_called()
        self.assertFalse(hasattr(task, 'first_open_dokan_time'))
        task.push_notify.assert_not_called()

    def test_stuck_detail_card_is_bounded_and_never_selects_next_guild(self):
        task = self.make_task(['普通寮'])
        self.con.fresh_num = 0
        self.card = True
        task.click = Mock()  # 收起点击没有生效。
        self.assertFalse(task.find_dokan(self.con, welfare_flag=False))
        self.assertEqual(task.click.call_count, 3)
        task.ui_click_until_appear_or_timeout.assert_not_called()
        task.push_notify.assert_not_called()

    def test_each_candidate_gets_its_own_three_detail_close_attempts(self):
        task = self.make_task(['普通寮一', '普通寮二'])
        self.con.fresh_num = 0
        self.card = True
        task.click = Mock()
        self.assertFalse(task.find_dokan(self.con, welfare_flag=False))
        self.assertEqual(task.click.call_count, 6)
        task.ui_click_until_appear_or_timeout.assert_not_called()

    def test_persistent_confirmation_clicks_only_three_times(self):
        task = self.make_task(['普通寮'])
        self.dialog = True
        clicks = []
        def click(button, **kwargs):
            clicks.append(button)
            return True
        task.appear_then_click = click
        self.assertFalse(task.challenge_selected_dokan())
        self.assertEqual(clicks, ['I_UI_SURE'] * 3)
        self.assertGreaterEqual(self.clock, 15)
        self.assertLess(self.clock, 16)

    def test_no_buttons_times_out_without_clicking(self):
        task = self.make_task(['普通寮'])
        self.assertFalse(task.challenge_selected_dokan())
        self.assertEqual(self.events, [])
        self.assertGreaterEqual(self.clock, 15)

    def test_unknown_scene_is_not_reported_as_success(self):
        task = self.make_task(['普通寮'])
        task.get_current_scene.return_value = (False, 'unknown')
        self.assertFalse(task.find_dokan(self.con, welfare_flag=False))
        task.push_notify.assert_not_called()

    def test_default_quit_flag_survives_rejected_welfare_candidate(self):
        task = self.make_task(['福利寮', '普通寮'], unavailable=['福利寮'], welfare=['福利寮'])
        task.dokan_quit = True
        self.assertTrue(task.find_dokan(self.con, welfare_flag=False))
        self.assertFalse(task.open_welfare)
        self.assertTrue(task.dokan_quit)

    def test_real_import_and_ocr_resource_definition_agree(self):
        import json
        from tasks.Dokan.script_task import ScriptTask
        self.assertTrue(callable(ScriptTask.challenge_selected_dokan))
        resource = Path(__file__).resolve().parents[1] / 'tasks/Dokan/res/ocr.json'
        entry, = [item for item in json.loads(resource.read_text(encoding='utf-8'))
                  if item['itemName'] == 'dokan_challenge_message']
        rule = ScriptTask.O_DOKAN_CHALLENGE_MESSAGE
        self.assertEqual(tuple(rule.roi), tuple(map(int, entry['roiFront'].split(','))))
        self.assertEqual(entry['mode'], 'Single')


if __name__ == '__main__':
    unittest.main()
