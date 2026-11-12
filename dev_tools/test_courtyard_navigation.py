"""庭院交叉定位的离线图像与导航验证，不连接设备。"""

import unittest
from pathlib import Path
import cv2
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.atom.image import RuleImage
from tasks.GameUi.courtyard import CourtyardEntrances
from tasks.GameUi.game_ui import GameUi
from module.exception import GameStuckError
from tasks.GameUi.page import (courtyard_entrances, page_main, page_exploration,
                               page_town, page_pet)

EXP = 'I_MAIN_GOTO_EXPLORATION'
TOWN = 'I_MAIN_GOTO_TOWN'
PET = 'I_PET_HOUSE'


def template(kind, suffix, roi, seed):
    item = RuleImage(roi, (0, 0, 1280, 720), 'Template matching', 0.7, '')
    item.variable_name = kind + suffix
    item._image = np.random.default_rng(seed).integers(0, 255, (roi[3], roi[2], 3), dtype=np.uint8)
    return item


class InferenceTest(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.target = template(EXP, '_1', (100, 100, 20, 30), 1)
        self.town = template(TOWN, '_1', (300, 300, 20, 30), 2)
        self.pet = template(PET, '_1', (600, 400, 20, 30), 3)
        self.model = CourtyardEntrances({EXP: [self.target], TOWN: [self.town], PET: [self.pet]})

    def paste(self, item, x=None, y=None):
        px, py, w, h = item.roi_front
        x, y = (px if x is None else x), (py if y is None else y)
        self.image[y:y+h, x:x+w] = item.image

    def test_other_entrance_locates_missing_target_without_mutating_assets(self):
        self.paste(self.town)
        self.target.roi_front[:] = [900, 600, 20, 30]
        self.assertEqual(self.model.infer(self.image, EXP), ('1', (100, 100, 20, 30)))
        self.assertEqual(self.town.roi_front, [300, 300, 20, 30])

    def test_same_icon_at_another_location_does_not_identify_skin(self):
        self.paste(self.town, 800, 300)
        self.assertIsNone(self.model.infer(self.image, EXP))

    def test_ambiguity_requires_another_independent_entrance(self):
        other = template(TOWN, '_2', (300, 300, 20, 30), 2)
        variant = template(TOWN, '_1_1', (300, 300, 20, 30), 2)
        model = CourtyardEntrances({EXP: [self.target], TOWN: [self.town, other, variant], PET: [self.pet]})
        self.paste(self.town)
        self.assertIsNone(model.infer(self.image, EXP))
        self.paste(self.pet)
        self.assertEqual(model.infer(self.image, EXP)[0], '1')

    def test_no_match_wrong_resolution_and_missing_target(self):
        self.assertIsNone(self.model.infer(self.image, EXP))
        self.paste(self.town)
        self.assertIsNone(self.model.infer(self.image[:600], EXP))
        self.assertIsNone(self.model.infer(self.image, 'missing'))

    def test_default_skin_and_each_target_kind(self):
        for kind in (EXP, TOWN, PET):
            with self.subTest(kind=kind):
                a = template(kind, '', (100, 100, 20, 30), 7)
                b = template('I_MAIN_GOTO_SUMMON', '', (300, 300, 20, 30), 8)
                c = template(TOWN if kind != TOWN else PET, '', (400, 300, 20, 30), 9)
                model = CourtyardEntrances({kind: [a], 'I_MAIN_GOTO_SUMMON': [b], c.name: [c]})
                self.image[:] = 0
                self.paste(b)
                self.paste(c)
                if kind == PET:
                    self.paste(a)
                self.assertEqual(model.infer(self.image, kind), ('default', (100, 100, 20, 30)))

    def test_large_original_roi_is_valid_and_absent_pet_remains_excluded(self):
        self.paste(self.town)
        self.assertTrue(CourtyardEntrances.safe_roi((464, 160, 324, 75)))
        for entry in self.model.entries:
            if entry.kind == EXP:
                entry.template.roi_front[:] = [0, 0, 324, 75]
        # 不受内部匹配副本的可变坐标影响。
        self.assertEqual(self.model.infer(self.image, EXP)[1], (100, 100, 20, 30))
        a = template(PET, '_5', (100, 100, 20, 30), 4)
        b = template(TOWN, '_5', (300, 300, 20, 30), 2)
        self.assertIsNone(CourtyardEntrances({PET: [a], TOWN: [b]}).infer(self.image, PET))

    def test_large_target_is_preserved_but_invalid_or_conflicting_coordinates_are_rejected(self):
        self.paste(self.town)
        wide = template(EXP, '_1', (100, 100, 324, 75), 9)
        self.assertEqual(CourtyardEntrances({EXP: [wide], TOWN: [self.town]}).infer(self.image, EXP),
                         ('1', (100, 100, 324, 75)))
        for roi in ((-1, 10, 20, 30), (1270, 10, 20, 30), (10, 700, 20, 30), (10, 10, 0, 30)):
            self.assertFalse(CourtyardEntrances.safe_roi(roi))
        variant = template(EXP, '_1_1', (150, 100, 20, 30), 10)
        self.assertIsNone(CourtyardEntrances({EXP: [self.target, variant], TOWN: [self.town]}).infer(self.image, EXP))

    def test_target_itself_is_not_skin_evidence(self):
        self.paste(self.target)
        self.assertIsNone(self.model.infer(self.image, EXP))

    def test_real_asset_catalog_is_complete_and_original(self):
        from tasks.GameUi.page import main_goto_exploration_list
        self.assertEqual(len([e for e in courtyard_entrances.entries if e.kind == EXP]),
                         len(main_goto_exploration_list))
        self.assertEqual({e.skin for e in courtyard_entrances.entries},
                         {'default', '14', '16'} | {str(i) for i in range(1, 14)})
        for entry in courtyard_entrances.entries:
            self.assertEqual(len(entry.template.image.shape), 3)

    def test_real_templates_locate_exploration_when_exploration_is_absent(self):
        for skin in {e.skin for e in courtyard_entrances.entries}:
            with self.subTest(skin=skin):
                image = np.zeros((720, 1280, 3), dtype=np.uint8)
                for entry in courtyard_entrances.entries:
                    if entry.skin != skin or entry.kind == EXP or not courtyard_entrances.safe_roi(entry.roi):
                        continue
                    x, y, _, _ = entry.roi
                    mat = entry.template.image
                    h, w = mat.shape[:2]
                    image[y:y+h, x:x+w] = mat
                self.assertEqual(courtyard_entrances.infer(image, EXP)[0], skin)

    def test_missing_pet_uses_other_entrance_skin_and_original_range(self):
        self.paste(self.town)
        self.assertIsNone(self.model.match_pet(self.image))
        self.assertEqual(self.model.infer(self.image, PET), ('1', (600, 400, 20, 30)))
        self.paste(self.target)
        self.assertEqual(self.model.infer(self.image, PET), ('1', (600, 400, 20, 30)))
        self.paste(self.pet)
        self.assertEqual(self.model.infer(self.image, PET), ('1', (600, 400, 20, 30)))

    def test_pet_direct_match_uses_current_position_without_mutating_catalog(self):
        self.paste(self.pet, 630, 420)
        skin, button = self.model.match_pet(self.image)
        self.assertEqual((skin, tuple(button.roi_front)), ('1', (630, 420, 20, 30)))
        self.assertEqual(self.pet.roi_front, [600, 400, 20, 30])
        self.assertEqual(self.model.entries[-1].roi, (600, 400, 20, 30))

    def test_shifted_courtyard_does_not_allow_fixed_pet_coordinates(self):
        self.paste(self.town, 380, 300)
        self.paste(self.target, 180, 100)
        self.assertIsNone(self.model.infer(self.image, PET))

    def test_pet_rejects_weak_match_and_ambiguous_skin(self):
        self.paste(self.pet)
        # 混入噪声使旧 0.6 阈值会误命中，而安全匹配应拒绝。
        noise = np.random.default_rng(20).integers(0, 255, self.pet.image.shape, dtype=np.uint8)
        self.image[400:430, 600:620] = (self.pet.image * 0.6 + noise * 0.4).astype(np.uint8)
        self.assertTrue(self.pet.match(self.image, threshold=0.6))
        self.assertIsNone(self.model.match_pet(self.image))
        self.paste(self.pet)
        other = template(PET, '_2', (700, 500, 20, 30), 8)
        self.paste(other)
        self.assertIsNone(CourtyardEntrances({PET: [self.pet, other]}).match_pet(self.image))

    def test_multiple_skins_same_location_use_common_click_region(self):
        self.paste(self.pet)
        other = template(PET, '_2', (600, 400, 20, 30), 3)
        model = CourtyardEntrances({PET: [self.pet, other]})
        key, button = model.match_pet(self.image)
        self.assertEqual(key, 'overlap:1,2')
        self.assertEqual(tuple(button.roi_front), (600, 400, 20, 30))
        self.assertEqual(model.entries[0].roi, (600, 400, 20, 30))

    def test_multiple_skins_with_edge_overlap_are_rejected(self):
        self.paste(self.pet)
        other = template(PET, '_2', (615, 400, 20, 30), 8)
        # 另一个独立图案只覆盖原图案右边 5 像素。
        self.paste(other)
        self.pet.threshold = 0.65
        # 各自素材取当前帧，确保拒绝原因是位置而非分数不足。
        self.pet._image = self.image[400:430, 600:620].copy()
        self.assertIsNone(CourtyardEntrances({PET: [self.pet, other]}).match_pet(self.image))


class NavigationTest(unittest.TestCase):
    def setUp(self):
        self.ui = GameUi.__new__(GameUi)
        self.ui.__dict__['device'] = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8),
                                                    screenshot=Mock(), click=Mock())
        self.ui.ui_page_appear = Mock(return_value=True)
        self.ui.appear = Mock(return_value=False)
        self.ui.ui_wait_until_appear = Mock(return_value=True)
        self.timer = Mock(reached=Mock(return_value=False))
        self.selection = ('1', (100, 100, 20, 30))

    def test_pet_click_requires_fresh_stable_position(self):
        for change in ('stable', 'position', 'skin', 'missing', 'popup', 'page', 'timeout'):
            with self.subTest(change=change):
                self.setUp()
                first = template(PET, '_12', (700, 270, 31, 25), 3)
                second = template(PET, '_12' if change != 'skin' else '_7',
                                  (720 if change == 'position' else 700, 270, 31, 25), 3)
                if change == 'popup':
                    self.ui.appear.return_value = True
                if change == 'page':
                    self.ui.ui_page_appear.side_effect = [True, False]
                if change == 'timeout':
                    self.timer.reached.side_effect = [False, False, True]
                with patch.object(courtyard_entrances, 'match_pet', side_effect=[
                        ('12', first), None if change == 'missing' else (('7' if change == 'skin' else '12'), second)]), \
                        patch('tasks.GameUi.game_ui.sleep'):
                    self.assertEqual(self.ui._try_pet_entrance(self.timer), change == 'stable')
                if change == 'stable':
                    self.assertEqual(self.ui.device.screenshot.call_count, 2)
                    x, y = self.ui.device.click.call_args.args
                    self.assertTrue(700 <= x < 731 and 270 <= y < 295)
                else:
                    self.ui.device.click.assert_not_called()

    def test_pet_path_uses_guard_instead_of_low_threshold_generic_click(self):
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui.appear_then_operate = Mock()
        self.ui._try_pet_entrance = Mock(return_value=True)
        self.ui._prepare_pet_entrance = Mock(return_value=True)
        self.ui._try_courtyard_fallback = Mock()
        self.assertTrue(self.ui._execute_path([page_main, page_pet], self.timer, {}))
        self.ui._try_pet_entrance.assert_called_once_with(self.timer)
        self.ui.appear_then_operate.assert_not_called()
        self.ui._try_courtyard_fallback.assert_not_called()

    def test_pet_real_entrance_frames_match_and_click_actual_position(self):
        for state in ('open', 'closed'):
            with self.subTest(state=state):
                self.setUp()
                path = Path(__file__).parent / 'fixtures' / 'courtyard_pet' / (state + '.png')
                crop = cv2.cvtColor(cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), 1),
                                    cv2.COLOR_BGR2RGB)
                self.ui.device.image[330:450, 920:1100] = crop
                with patch('tasks.GameUi.game_ui.sleep'):
                    self.assertTrue(self.ui._try_pet_entrance(self.timer))
                x, y = self.ui.device.click.call_args.args
                self.assertTrue(1000 <= x < 1032 and 380 <= y < 410)

    def test_shared_12_13_error_screenshot_completes_outer_navigation(self):
        # 使用真实错误截图的建筑局部及收起动画局部，运行外层导航，
        # 不替换展开识别、入口匹配、点击位置或等待目标页逻辑。
        self.ui.device.image = self.lantern_frame('collapsed_animated')
        path = Path(__file__).parent / 'fixtures' / 'courtyard_pet' / 'shared_12_13.png'
        crop = cv2.cvtColor(cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), 1), cv2.COLOR_BGR2RGB)
        self.ui.device.image[240:330, 780:900] = crop
        diagnostics = []
        key, button = courtyard_entrances.match_pet(self.ui.device.image, diagnostics)
        self.assertEqual(key, 'overlap:12,13')
        self.assertTrue(any(name == 'I_PET_HOUSE_13' and score > 0.95 for name, score, _ in diagnostics))
        self.assertEqual(tuple(button.roi_front), (832, 275, 31, 25))
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui.build_reverse_path_dict = Mock(return_value={page_main: [page_main, page_pet]})
        arrived = [False]
        self.ui.device.click.side_effect = lambda *args, **kwargs: arrived.__setitem__(0, True)
        self.ui.ui_page_appear.side_effect = lambda page, *args, **kwargs: page == (
            page_pet if arrived[0] else page_main)
        # 使用真实等待逻辑，仅模拟点击后的目标页出现。
        self.ui.ui_wait_until_appear = GameUi.ui_wait_until_appear.__get__(self.ui)
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertTrue(self.ui.ui_goto(page_pet))
        self.ui.device.click.assert_called_once()
        x, y = self.ui.device.click.call_args.args
        self.assertTrue(832 <= x < 863 and 275 <= y < 300)
        self.assertIs(self.ui.ui_current, page_pet)

    def test_missing_pet_real_town_identifies_skin_and_clicks_original_range(self):
        path = Path(__file__).parent / 'fixtures' / 'courtyard_pet' / 'town.png'
        crop = cv2.cvtColor(cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), 1), cv2.COLOR_BGR2RGB)
        self.ui.device.image[337:367, 842:855] = crop
        self.assertIsNone(courtyard_entrances.match_pet(self.ui.device.image))
        self.assertEqual(courtyard_entrances.infer(self.ui.device.image, PET),
                         ('14', (841, 356, 299, 59)))
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui._prepare_pet_entrance = Mock(return_value=True)
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertTrue(self.ui._execute_path([page_main, page_pet], self.timer, {}))
        x, y = self.ui.device.click.call_args.args
        self.assertTrue(841 <= x < 1140 and 356 <= y < 415)
        self.assertEqual(self.ui.device.click.call_count, 1)
        self.assertIs(self.ui.ui_current, page_pet)

    def test_pet_fallback_requires_arrival_and_stops_after_three_failures(self):
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui._prepare_pet_entrance = Mock(return_value=True)
        self.ui._try_pet_entrance = Mock(return_value=False)
        self.ui.ui_wait_until_appear.return_value = False
        attempts = {}
        with patch.object(courtyard_entrances, 'infer', return_value=('14', (841, 356, 299, 59))), \
                patch('tasks.GameUi.game_ui.sleep'):
            for _ in range(2):
                self.assertFalse(self.ui._execute_path([page_main, page_pet], self.timer, attempts))
            with self.assertRaisesRegex(GameStuckError, '三次入口'):
                self.ui._execute_path([page_main, page_pet], self.timer, attempts)
        self.assertEqual(self.ui.device.click.call_count, 3)
        self.assertIs(self.ui.ui_current, page_main)

    def test_pet_navigation_budget_includes_missing_entrance_and_failed_arrival(self):
        for clicked in (False, True):
            with self.subTest(clicked=clicked):
                self.setUp()
                self.ui.ui_current = page_main
                self.ui.run_additional = Mock()
                self.ui._prepare_pet_entrance = Mock(return_value=True)
                self.ui._try_pet_entrance = Mock(return_value=clicked)
                self.ui._try_courtyard_fallback = Mock(return_value=False)
                # 等待目标页超时；不使用真实时钟在测试中等待。
                elapsed = Mock()
                elapsed.start.return_value = elapsed
                elapsed.reached.return_value = True
                attempts = {}
                with patch('tasks.GameUi.game_ui.Timer', return_value=elapsed):
                    for _ in range(2):
                        self.assertFalse(self.ui._execute_path([page_main, page_pet], self.timer, attempts))
                    with self.assertRaisesRegex(GameStuckError, '三次入口'):
                        self.ui._execute_path([page_main, page_pet], self.timer, attempts)
                    with self.assertRaisesRegex(GameStuckError, '三次入口'):
                        self.ui._execute_path([page_main, page_pet], self.timer, attempts)
                self.assertEqual(self.ui._prepare_pet_entrance.call_count, 3)
                self.assertEqual(self.ui._try_pet_entrance.call_count, 3)
                self.assertIs(self.ui.ui_current, page_main)

    def test_ui_goto_outer_loop_stops_after_three_missing_pet_attempts(self):
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui._prepare_pet_entrance = Mock(return_value=True)
        self.ui._try_pet_entrance = Mock(return_value=False)
        self.ui._try_courtyard_fallback = Mock(return_value=False)
        self.ui.build_reverse_path_dict = Mock(return_value={page_main: [page_main, page_pet]})
        with self.assertRaisesRegex(GameStuckError, '三次入口'):
            self.ui.ui_goto(page_pet)
        self.assertEqual(self.ui._prepare_pet_entrance.call_count, 3)
        self.assertEqual(self.ui._try_pet_entrance.call_count, 3)

    def run_fallback(self, attempts=None):
        return self.ui._try_courtyard_fallback(page_main, page_exploration, self.timer,
                                               {} if attempts is None else attempts)

    def lantern_frame(self, name):
        path = Path(__file__).parent / 'fixtures' / 'courtyard_lanterns' / (name + '.png')
        crop = cv2.cvtColor(cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), 1), cv2.COLOR_BGR2RGB)
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[80:560, 1180:1280] = crop
        return frame

    def test_lantern_screenshot_states_are_distinct(self):
        from copy import copy
        for state in ('expanded', 'collapsed'):
            frame = self.lantern_frame(state)
            self.assertEqual(copy(self.ui.I_PAPER_DOLL_EXPANDED).match(frame), state == 'expanded')
            self.assertEqual(copy(self.ui.I_PAPER_DOLL_CLOSE).match(frame), state == 'collapsed')

    def test_lantern_collapses_once_and_waits_for_two_fresh_frames(self):
        frames = iter([self.lantern_frame(state) for state in
                       ('expanded', 'expanded', 'collapsed', 'collapsed')])
        self.ui.device.screenshot.side_effect = lambda: setattr(self.ui.device, 'image', next(frames))
        with patch('tasks.GameUi.game_ui.sleep') as wait:
            self.assertTrue(self.ui._prepare_pet_entrance(self.timer))
        self.assertEqual(self.ui.device.screenshot.call_count, 4)
        self.assertEqual(wait.call_count, 3)
        self.ui.device.click.assert_called_once()
        x, y = self.ui.device.click.call_args.args
        self.assertTrue(1257 <= x < 1271 and 103 <= y < 117)

    def test_already_collapsed_does_not_toggle_lanterns(self):
        self.ui.device.image = self.lantern_frame('collapsed')
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertTrue(self.ui._prepare_pet_entrance(self.timer))
        self.ui.device.click.assert_not_called()
        self.assertEqual(self.ui.device.screenshot.call_count, 2)

    def test_no_expanded_match_is_collapsed_without_positive_closed_match(self):
        from copy import copy
        frame = self.ui.device.image
        self.assertFalse(copy(self.ui.I_PAPER_DOLL_EXPANDED).match(frame))
        self.assertFalse(copy(self.ui.I_PAPER_DOLL_CLOSE).match(frame))
        with patch('tasks.GameUi.game_ui.sleep') as wait:
            self.assertTrue(self.ui._prepare_pet_entrance(self.timer))
        self.assertEqual(self.ui.device.screenshot.call_count, 2)
        wait.assert_called_once_with(0.35)
        self.ui.device.click.assert_not_called()

    def test_closed_match_flicker_after_click_does_not_block_confirmation(self):
        # 第一帧收起命中、第二帧不命中；两帧均无展开即可继续。
        frames = iter([self.lantern_frame('expanded'), self.lantern_frame('expanded'),
                       self.lantern_frame('collapsed_animated'), self.ui.device.image])
        self.ui.device.screenshot.side_effect = lambda: setattr(self.ui.device, 'image', next(frames))
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertTrue(self.ui._prepare_pet_entrance(self.timer))
        self.assertEqual(self.ui.device.screenshot.call_count, 4)
        self.ui.device.click.assert_called_once()

    def test_expanded_frame_resets_absence_confirmation(self):
        absent = self.ui.device.image
        frames = iter([absent, self.lantern_frame('expanded'), absent, absent])
        self.ui.device.screenshot.side_effect = lambda: setattr(self.ui.device, 'image', next(frames))
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertTrue(self.ui._prepare_pet_entrance(self.timer))
        self.assertEqual(self.ui.device.screenshot.call_count, 4)
        self.ui.device.click.assert_not_called()

    def test_popup_page_and_expired_navigation_never_toggle(self):
        for case in ('popup', 'page', 'timeout'):
            with self.subTest(case=case):
                self.setUp()
                self.ui.device.image = self.lantern_frame('expanded')
                if case == 'popup':
                    self.ui.appear.return_value = True
                if case == 'page':
                    self.ui.ui_page_appear.return_value = False
                if case == 'timeout':
                    self.timer.reached.return_value = True
                with patch('tasks.GameUi.game_ui.sleep'):
                    self.assertFalse(self.ui._prepare_pet_entrance(self.timer))
                self.ui.device.click.assert_not_called()

    def test_collapse_failure_blocks_direct_and_fixed_pet_clicks(self):
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui._prepare_pet_entrance = Mock(return_value=False)
        self.ui._try_pet_entrance = Mock()
        self.ui._try_courtyard_fallback = Mock()
        with self.assertRaisesRegex(GameStuckError, '未确认右侧灯笼收起'):
            self.ui._execute_path([page_main, page_pet], self.timer, {})
        self.ui._try_pet_entrance.assert_not_called()
        self.ui._try_courtyard_fallback.assert_not_called()

    def test_collapse_timeout_does_not_repeat_toggle(self):
        self.ui.device.image = self.lantern_frame('expanded')
        wait = Mock(reached=Mock(side_effect=[False, False, True]))
        wait.start.return_value = wait
        with patch('tasks.GameUi.game_ui.Timer', return_value=wait), \
                patch('tasks.GameUi.game_ui.sleep'):
            self.assertFalse(self.ui._prepare_pet_entrance(self.timer))
        self.ui.device.click.assert_called_once()

    def test_lantern_must_be_stable_before_head_click(self):
        self.ui.device.image = self.lantern_frame('expanded')
        self.ui.ui_page_appear.side_effect = [True, False]
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertFalse(self.ui._prepare_pet_entrance(self.timer))
        self.ui.device.click.assert_not_called()

    def test_missed_click_error_screenshot_is_still_expanded(self):
        from copy import copy
        frame = self.lantern_frame('missed_click')
        self.assertTrue(copy(self.ui.I_PAPER_DOLL_EXPANDED).match(frame))
        self.assertFalse(copy(self.ui.I_PAPER_DOLL_CLOSE).match(frame))

    def test_animated_expanded_head_collapses_without_lowering_threshold(self):
        from copy import copy
        frame = self.lantern_frame('expanded_animated')
        expanded = copy(self.ui.I_PAPER_DOLL_EXPANDED)
        self.assertGreaterEqual(expanded.threshold, 0.85)
        self.assertTrue(expanded.match(frame))
        self.assertGreater(expanded.max_val, 0.95)
        self.assertFalse(copy(self.ui.I_PAPER_DOLL_CLOSE).match(frame))
        # 第二帧再平移两像素，模拟轻微晃动；点击应跟随新匹配位置。
        shifted = np.zeros_like(frame)
        shifted[2:, 2:] = frame[:-2, :-2]
        self.assertTrue(expanded.match(shifted))
        frames = iter([frame, shifted, self.lantern_frame('collapsed'),
                       self.lantern_frame('collapsed')])
        self.ui.device.screenshot.side_effect = lambda: setattr(self.ui.device, 'image', next(frames))
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertTrue(self.ui._prepare_pet_entrance(self.timer))
        self.assertEqual(self.ui.device.screenshot.call_count, 4)
        self.ui.device.click.assert_called_once()
        x, y = self.ui.device.click.call_args.args
        self.assertTrue(expanded.roi_front[0] + 7 <= x < expanded.roi_front[0] + 21)
        self.assertTrue(expanded.roi_front[1] + 3 <= y < expanded.roi_front[1] + 17)

    def test_page_loss_after_head_click_fails_without_retry(self):
        self.ui.device.image = self.lantern_frame('expanded')
        self.ui.ui_page_appear.side_effect = [True, True, False]
        with patch('tasks.GameUi.game_ui.sleep'):
            self.assertFalse(self.ui._prepare_pet_entrance(self.timer))
        self.ui.device.click.assert_called_once()

    def test_weak_pet_match_reports_score_without_stale_position(self):
        item = template(PET, '_12', (600, 400, 20, 30), 3)
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        noise = np.random.default_rng(20).integers(0, 255, item.image.shape, dtype=np.uint8)
        image[400:430, 600:620] = (item.image * 0.6 + noise * 0.4).astype(np.uint8)
        diagnostics = []
        self.assertIsNone(CourtyardEntrances({PET: [item]}).match_pet(image, diagnostics))
        self.assertEqual(diagnostics[0][0], 'I_PET_HOUSE_12')
        self.assertGreater(diagnostics[0][1], 0.6)
        self.assertIsNone(diagnostics[0][2])

    def test_two_fresh_frames_click_target_then_verify(self):
        with patch.object(courtyard_entrances, 'infer', return_value=self.selection), \
                patch('tasks.GameUi.game_ui.sleep') as wait:
            self.assertTrue(self.run_fallback())
        wait.assert_called_once_with(0.35)
        self.assertEqual(self.ui.device.screenshot.call_count, 2)
        self.ui.device.click.assert_called_once()
        x, y = self.ui.device.click.call_args.args
        self.assertTrue(100 <= x < 120 and 100 <= y < 130)
        self.assertEqual(self.ui.device.click.call_args.kwargs, {'control_name': 'Courtyard_' + EXP})
        self.ui.ui_wait_until_appear.assert_called_once_with(page_exploration, timeout=6,
                                                           skip_first_screenshot=False)

    def test_random_click_uses_original_large_target_area(self):
        for skin, roi in (('14', (464, 160, 324, 75)), ('6', (1105, 466, 174, 134))):
            with self.subTest(skin=skin):
                points = set()
                for _ in range(20):
                    with patch.object(courtyard_entrances, 'infer', return_value=(skin, roi)), \
                            patch('tasks.GameUi.game_ui.sleep'):
                        destination = page_pet if skin == '6' else page_exploration
                        self.assertTrue(self.ui._try_courtyard_fallback(
                            page_main, destination, self.timer, {}))
                    x, y = self.ui.device.click.call_args.args
                    self.assertTrue(roi[0] <= x < roi[0] + roi[2])
                    self.assertTrue(roi[1] <= y < roi[1] + roi[3])
                    points.add((x, y))
                self.assertGreater(len(points), 1)

    def test_changed_skin_page_or_popup_prevents_click(self):
        for case in ('skin', 'page', 'popup'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'page':
                    self.ui.ui_page_appear.side_effect = [True, False]
                if case == 'popup':
                    self.ui.appear.return_value = True
                with patch.object(courtyard_entrances, 'infer', side_effect=[self.selection, None]), \
                        patch('tasks.GameUi.game_ui.sleep'):
                    self.assertFalse(self.run_fallback())
                self.ui.device.click.assert_not_called()

    def test_failure_keeps_state_and_three_attempt_budget(self):
        self.ui.ui_current = page_main
        self.ui.ui_wait_until_appear.return_value = False
        attempts = {}
        with patch.object(courtyard_entrances, 'infer', return_value=self.selection), \
                patch('tasks.GameUi.game_ui.sleep'):
            for _ in range(4):
                self.assertFalse(self.run_fallback(attempts))
        self.assertEqual(self.ui.device.click.call_count, 3)
        self.assertEqual(attempts[EXP], 3)
        self.assertIs(self.ui.ui_current, page_main)

    def test_other_pages_and_timeout_never_click(self):
        self.assertFalse(self.ui._try_courtyard_fallback(page_town, page_exploration, self.timer, {}))
        self.timer.reached.return_value = True
        self.assertFalse(self.run_fallback())
        self.ui.device.click.assert_not_called()

    def test_timeout_after_confirmation_prevents_click(self):
        self.timer.reached.side_effect = [False, False, True]
        with patch.object(courtyard_entrances, 'infer', return_value=self.selection), \
                patch('tasks.GameUi.game_ui.sleep'):
            self.assertFalse(self.run_fallback())
        self.ui.device.click.assert_not_called()

    def test_path_uses_fallback_only_after_all_direct_actions_fail(self):
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui.appear_then_operate = Mock(return_value=False)
        self.ui._try_courtyard_fallback = Mock(return_value=True)
        self.assertTrue(self.ui._execute_path([page_main, page_exploration], self.timer, {}))
        self.assertIs(self.ui.ui_current, page_exploration)
        self.assertEqual(self.ui.appear_then_operate.call_count, len(page_main.links[page_exploration]))
        self.ui.ui_current = page_main
        self.ui.appear_then_operate.return_value = True
        self.ui._try_courtyard_fallback.reset_mock()
        self.assertTrue(self.ui._execute_path([page_main, page_exploration], self.timer, {}))
        self.ui._try_courtyard_fallback.assert_not_called()

    def test_path_does_not_report_arrival_on_failed_fallback(self):
        self.ui.ui_current = page_main
        self.ui.run_additional = Mock()
        self.ui.appear_then_operate = Mock(return_value=False)
        self.ui._try_courtyard_fallback = Mock(return_value=False)
        self.assertFalse(self.ui._execute_path([page_main, page_exploration], self.timer, {}))
        self.assertIs(self.ui.ui_current, page_main)


if __name__ == '__main__':
    unittest.main()
