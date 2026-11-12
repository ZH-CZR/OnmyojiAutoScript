"""Wanted monster detail routes and skip list, without devices or OCR services."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import numpy as np
import cv2

from module.config.config_model import ConfigModel
from module.exception import GameStuckError
from tasks.GameUi.page import page_exploration
from tasks.WantedQuests.assets import WantedQuestsAssets as Assets
from tasks.WantedQuests.config import WantedQuestsConfig
from tasks.WantedQuests.script_task import ScriptTask


class WantedDetailTest(unittest.TestCase):
    def test_cooperation_error_frame_is_already_open_without_extra_sidebar_clicks(self):
        patch_image = cv2.cvtColor(cv2.imread(str(Path(__file__).parent /
            'fixtures/wanted_detail/cooperation_header.png')), cv2.COLOR_BGR2RGB)
        image = self.task.device.image
        image[160:234, 637:1146] = patch_image
        normal = copy.deepcopy(Assets.I_WQ_DETAIL)
        cooperation = copy.deepcopy(Assets.I_WQ_DETAIL_COOPERATION)
        self.assertFalse(normal.match(image))
        self.assertTrue(cooperation.match(image))
        self.task.I_WQ_DETAIL = normal
        self.task.I_WQ_DETAIL_COOPERATION = cooperation
        self.task.appear.side_effect = lambda rule: rule.match(image)
        self.assertTrue(self.task._open_wanted_detail(self.task.O_WQ_TEXT_1))
        self.task.click.assert_not_called()

    def test_cooperation_title_uses_target_name_and_actual_progress(self):
        self.visible.discard(self.task.I_WQ_DETAIL.name)
        self.visible.add(self.task.I_WQ_DETAIL_COOPERATION.name)
        self.settings.unwanted_boss_names = '灯笼鬼'
        self.task.O_WQ_DETAIL_TARGET.ocr.return_value = '自己击败提灯小僧'
        self.task.O_WQ_DETAIL_PROGRESS.ocr.return_value = (0, 8, 8)
        self.task.O_WQ_NUMBER.ocr.return_value = 3851
        self.routes(('式神碎片', '片第二章(数量:14)'))
        self.task.execute_mission(None, 999, 0)
        self.task.challenge.assert_called_once_with(self.task.I_GOTO_1, 1)
        self.assertEqual(self.task._wanted_monster_name('自己击败提灯小僧'), '提灯小僧')
        self.assertIsNone(self.task._wanted_monster_name('好友击败灯笼鬼'))

    def test_cooperation_blacklist_cancels_and_confirms_before_close(self):
        self.visible.discard(self.task.I_WQ_DETAIL.name)
        self.visible.add(self.task.I_WQ_DETAIL_COOPERATION.name)
        self.visible.add(self.task.I_WQ_DETAIL_CANCEL_TRACK.name)
        self.settings.unwanted_boss_names = '提灯小僧'
        self.task.O_WQ_DETAIL_TARGET.ocr.return_value = '自己击败提灯小僧'

        def transition(rule, **kwargs):
            if rule is self.task.I_WQ_DETAIL_CANCEL_TRACK:
                self.visible.remove(rule.name)
                self.visible.add(self.task.I_WQ_DETAIL_TRACK.name)
            elif rule is self.task.I_WQ_DETAIL_CLOSE:
                self.visible = {page_exploration.check_button.name}
            else:
                self.fail(f'Unexpected action: {rule}')

        self.task.click.side_effect = transition
        self.task.execute_mission(None, 0, 0)
        self.assertEqual(self.task.click.call_args_list, [
            call(self.task.I_WQ_DETAIL_CANCEL_TRACK, interval=1),
            call(self.task.I_WQ_DETAIL_CLOSE, interval=1)])
        self.task.challenge.assert_not_called()
        self.task.secret.assert_not_called()

    def setUp(self):
        self.task = ScriptTask.__new__(ScriptTask)
        self.settings = WantedQuestsConfig()
        self.task.config = SimpleNamespace(wanted_quests=SimpleNamespace(wanted_quests_config=self.settings))
        self.task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        self.task.screenshot = Mock()
        self.task.click = Mock()
        self.task.challenge = Mock()
        self.task.secret = Mock()
        self.task.ui_goto_page = Mock()
        self.visible = {self.task.I_WQ_DETAIL.name, self.task.I_WQ_DETAIL_CLOSE.name}
        self.task.appear = Mock(side_effect=lambda rule: rule.name in self.visible)
        self.task.appear_then_click = Mock(side_effect=self.click_visible)
        for name in vars(Assets):
            if name.startswith('O_'):
                setattr(self.task, name, SimpleNamespace(ocr=Mock(return_value='')))
        self.task.O_WQ_NUMBER.ocr.return_value = 2
        self.task.O_WQ_DETAIL_PROGRESS.ocr.return_value = (0, 6, 6)
        self.task.O_WQ_DETAIL_TARGET.ocr.return_value = '悬赏目标：击败6个唐纸伞妖'

    def click_visible(self, rule, **kwargs):
        if rule.name not in self.visible:
            return False
        self.task.click(rule, **kwargs)
        return True

    def routes(self, *rows):
        for slot, (kind, info) in enumerate(rows, 1):
            self.visible.add(getattr(self.task, f'I_GOTO_{slot}').name)
            getattr(self.task, f'O_WQ_TYPE_{slot}').ocr.return_value = kind
            getattr(self.task, f'O_WQ_INFO_{slot}').ocr.return_value = info

    def test_frog_skip_happens_before_progress_route_or_battle(self):
        self.settings.unwanted_boss_names = '青蛙瓷器'
        self.task.O_WQ_DETAIL_TARGET.ocr.return_value = '悬赏目标: 击败 1 个 青蛙瓷器'
        self.visible.add(self.task.I_WQ_DETAIL_CANCEL_TRACK.name)

        def transition(rule, **kwargs):
            if rule is self.task.I_WQ_DETAIL_CANCEL_TRACK:
                self.visible.remove(rule.name)
                self.visible.add(self.task.I_WQ_DETAIL_TRACK.name)
            elif rule is self.task.I_WQ_DETAIL_CLOSE:
                self.visible = {page_exploration.check_button.name}
            else:
                self.fail(f'Unexpected action: {rule}')

        self.task.click.side_effect = transition
        self.task.execute_mission(None, 99, 99)
        self.assertEqual(self.task.click.call_args_list, [
            call(self.task.I_WQ_DETAIL_CANCEL_TRACK, interval=1),
            call(self.task.I_WQ_DETAIL_CLOSE, interval=1)])
        self.task.challenge.assert_not_called()
        self.task.secret.assert_not_called()
        self.task.O_WQ_DETAIL_PROGRESS.ocr.assert_not_called()
        self.task.O_WQ_NUMBER.ocr.assert_not_called()
        self.task.ui_goto_page.assert_not_called()

    def test_skip_names_support_separators_and_exact_matching(self):
        self.settings.unwanted_boss_names = ' 青蛙瓷器，山兔、唐纸伞妖;酒吞童子；阎魔\n 山兔\r\n'
        self.assertEqual(self.task._wanted_blacklist(),
                         {'青蛙瓷器', '山兔', '唐纸伞妖', '酒吞童子', '阎魔'})
        self.assertNotIn('山童', self.task._wanted_blacklist())
        self.assertNotIn('青蛙', self.task._wanted_blacklist())
        self.assertIsNone(self.task._wanted_monster_name('青蛙瓷器(数量:3)'))

    def test_nonmatching_monster_uses_actual_progress_and_low_ticket_count(self):
        self.settings.unwanted_boss_names = '青蛙瓷器'
        self.routes(('式神碎片', '片第八章(数量:14)'),
                    ('秘闻意志', '意志的觉醒·壹(数量:3)'))
        self.task.execute_mission(None, 999, 999)
        self.task.secret.assert_called_once_with(self.task.I_GOTO_2, 2)
        self.task.challenge.assert_not_called()
        self.task.click.assert_not_called()

    def test_unreadable_name_with_skip_list_never_attacks_or_cancels(self):
        self.settings.unwanted_boss_names = '青蛙瓷器'
        self.task.O_WQ_DETAIL_TARGET.ocr.return_value = ''
        with self.assertRaises(GameStuckError):
            self.task.execute_mission(None, 1, 30)
        self.task.click.assert_not_called()
        self.task.secret.assert_not_called()
        self.task.challenge.assert_not_called()

    def test_empty_skip_list_does_not_need_name_ocr(self):
        self.routes(('秘闻', '意志的觉醒·壹(数量:3)'))
        self.task.execute_mission(None, 999, 999)
        self.task.O_WQ_DETAIL_TARGET.ocr.assert_not_called()
        self.task.secret.assert_called_once_with(self.task.I_GOTO_1, 2)

    def test_partial_name_does_not_cancel_a_different_full_name(self):
        self.settings.unwanted_boss_names = '青蛙'
        self.task.O_WQ_DETAIL_TARGET.ocr.return_value = '悬赏目标:击败1个青蛙瓷器'
        self.routes(('秘闻', '雨女的等候·拾(数量:5)'))
        self.task.execute_mission(None, 1, 30)
        self.task.secret.assert_called_once()
        self.task.click.assert_not_called()

    def test_sidebar_is_rescanned_from_first_item_after_cancel_or_battle(self):
        handled = []
        self.task.current_count = 0
        self.task.O_WQ_TEXT_1.detect_text = Mock(side_effect=lambda image:
            '悬赏封印' if len(handled) < 2 else '')
        self.task.O_WQ_NUM_1.ocr.return_value = (0, 1, 1)
        for slot in (2, 3):
            getattr(self.task, f'O_WQ_TEXT_{slot}').detect_text = Mock(return_value='')
        self.task.execute_mission = Mock(side_effect=lambda *args: handled.append(args))
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = lambda: len(handled) == 2
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            self.task.play_run()
        self.assertEqual(self.task.execute_mission.call_args_list, [
            call(self.task.O_WQ_TEXT_1, 1, 2), call(self.task.O_WQ_TEXT_1, 1, 2)])

    def test_left_challenge_tickets_allow_challenge_despite_low_breakthrough_tickets(self):
        self.task.O_WQ_NUMBER.ocr.return_value = 3876
        self.routes(('式神碎片', '片第八章(数量:14)'),
                    ('秘闻', '意志的觉醒·壹(数量:3)'))
        self.task.execute_mission(None, 999, 2)
        self.task.challenge.assert_called_once_with(self.task.I_GOTO_1, 1)
        self.task.secret.assert_not_called()

    def test_challenge_label_and_threshold(self):
        self.routes(('式神碎片', '片第九章(数量:14)'), ('秘闻', '山兔大暴走·拾(数量:6)'))
        for tickets, expected in ((9, 'SECRET'), (10, 'CHALLENGE')):
            with self.subTest(tickets=tickets):
                route = self.task._select_wanted_route(12, tickets)
                self.assertEqual(route[:2], (expected, 2 if tickets == 9 else 1))

    def test_fourth_row_secret_after_exploration_rows(self):
        self.routes(('式神碎片', '片第九章(数量:14)'), ('探索第二', '第二十三章(数量:9)'),
                    ('探索第九', '第九章(数量:7)'), ('秘闻山兔', '山兔大暴走·拾(数量:6)'))
        self.assertEqual(self.task._select_wanted_route(12, 2), ('SECRET', 2, self.task.I_GOTO_4))

    def test_high_layers_use_layer_not_monster_quantity(self):
        self.settings.enable_secret_layer_h = True
        self.routes(('秘闻', '雨女的等候·拾(数量:5)'), ('秘闻', '河畔童谣·玖(数量:3)'),
                    ('秘闻', '意志的觉醒·壹(数量:14)'))
        self.assertEqual(self.task._select_wanted_route(20, 2), ('SECRET', 2, self.task.I_GOTO_3))
        for layer in ('柒', '捌', '玖', '拾', '番外', '7', '8', '9', '10', '七', '八', '九', '十'):
            with self.subTest(layer=layer):
                self.routes(('秘闻', f'雨女的等候·{layer}(数量:5)'))
                self.visible.discard(self.task.I_GOTO_2.name)
                self.visible.discard(self.task.I_GOTO_3.name)
                self.assertIsNone(self.task._select_wanted_route(1, 2))

    def test_count_requires_explicit_quantity_never_guesses_chapter_number(self):
        for text in ('第二十三章', '第九章(数量:0)', '第九章(数量:?)'):
            with self.subTest(info=text):
                self.routes(('秘闻', text))
                with self.assertRaises(GameStuckError):
                    self.task._select_wanted_route(12, 2)
        self.routes(('秘闻', '第23章·壹（数量：9）'))
        self.assertEqual(self.task._select_wanted_route(100, 2)[1], 5)

    def test_invalid_progress_does_not_guess_or_start_fight(self):
        for progress in ((0, 0, 0), (7, -1, 6), (0, 2, 6)):
            self.task.O_WQ_DETAIL_PROGRESS.ocr.return_value = progress
            with self.assertRaises(GameStuckError):
                self.task.execute_mission(None, 99, 99)
        self.task.secret.assert_not_called()
        self.task.challenge.assert_not_called()

    def test_cancel_must_see_track_button_before_closing(self):
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = [False, False, True]
        self.visible.add(self.task.I_WQ_DETAIL_CANCEL_TRACK.name)
        self.task.click.side_effect = lambda *args, **kwargs: self.visible.discard(
            self.task.I_WQ_DETAIL_CANCEL_TRACK.name)
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaises(GameStuckError):
                self.task._close_wanted_detail(cancel_tracking=True)
        self.task.click.assert_called_once_with(self.task.I_WQ_DETAIL_CANCEL_TRACK, interval=1)
        timer.reset.assert_not_called()

    def test_already_untracked_never_toggles_tracking_back_on(self):
        self.visible.add(self.task.I_WQ_DETAIL_TRACK.name)
        self.task.click.side_effect = lambda *args, **kwargs: setattr(
            self, 'visible', {page_exploration.check_button.name})
        self.task._close_wanted_detail(cancel_tracking=True)
        self.task.click.assert_called_once_with(self.task.I_WQ_DETAIL_CLOSE, interval=1)

    def test_open_detail_has_fixed_timeout_and_at_most_five_clicks(self):
        self.visible.clear()
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = [False]*7 + [True]
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaises(GameStuckError):
                self.task._open_wanted_detail('side-entry')
        self.assertEqual(self.task.click.call_count, 5)
        timer.reset.assert_not_called()

    def test_original_blacklist_is_the_only_field_and_keeps_existing_values(self):
        self.assertEqual(WantedQuestsConfig().unwanted_boss_names, '')
        model = ConfigModel()
        fields = model.script_task('WantedQuests')['wanted_quests_config']
        field = next(item for item in fields if item['name'] == 'unwanted_boss_names')
        self.assertEqual((field['type'], field['value']), ('string', ''))
        self.assertEqual(field['title'], '悬赏黑名单')
        self.assertEqual(field['description'], 'unwanted_boss_name_help')
        self.assertEqual([item['name'] for item in fields].count('unwanted_boss_names'), 1)
        self.assertFalse(any('skip_monster' in item['name'] for item in fields))
        with patch.object(ConfigModel, 'save') as save:
            self.assertTrue(model.script_set_arg('WantedQuests', 'wanted_quests_config',
                                                 'unwanted_boss_names', '青蛙瓷器，山兔'))
        save.assert_called_once()
        restored = ConfigModel.model_validate_json(model.model_dump_json())
        self.assertEqual(restored.wanted_quests.wanted_quests_config.unwanted_boss_names, '青蛙瓷器，山兔')
        self.assertEqual(restored.wanted_quests.wanted_quests_config.model_dump()['unwanted_boss_names'],
                         '青蛙瓷器，山兔')

    def test_detail_ocr_rois_and_generated_json_agree(self):
        root = Path(__file__).resolve().parents[1] / 'tasks/WantedQuests'
        for item in json.loads((root/'wq/ocr.json').read_text('utf-8')):
            rule = getattr(Assets, 'O_' + item['itemName'].upper())
            self.assertEqual(tuple(rule.roi), tuple(map(int, item['roiFront'].split(','))))
        rule = copy.deepcopy(Assets.O_WQ_DETAIL_PROGRESS)
        rule.__dict__['model'] = Mock()
        rule.model.ocr_single_line.return_value = ('2/30', 0.99)
        self.assertEqual(rule.ocr(self.task.device.image), (2, 28, 30))

    def test_ticket_ocr_crops_left_balance_and_excludes_breakthrough_counter(self):
        rule = copy.deepcopy(Assets.O_WQ_NUMBER)
        rule.__dict__['model'] = Mock()
        image = self.task.device.image
        # 左侧余额与右侧突破券区域使用不同像素，验证实际裁剪传入 OCR 的内容。
        image[12:46, 548:654] = 37
        image[12:46, 761:844] = 230

        def recognize(cropped):
            self.assertEqual(cropped.shape, (34, 106, 3))
            self.assertTrue(np.all(cropped == 37))
            return '3876', 0.99

        rule.model.ocr_single_line.side_effect = recognize
        self.assertEqual(rule.ocr(image), 3876)
        rule.model.ocr_single_line.side_effect = None
        rule.model.ocr_single_line.return_value = ('', 0.99)
        rule.model.detect_and_ocr.return_value = []
        self.assertEqual(rule.ocr(image), 0)


if __name__ == '__main__':
    unittest.main()
