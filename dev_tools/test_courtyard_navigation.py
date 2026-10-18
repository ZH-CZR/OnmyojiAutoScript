"""庭院交叉定位的离线图像与导航验证，不连接设备。"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.atom.image import RuleImage
from tasks.GameUi.courtyard import CourtyardEntrances
from tasks.GameUi.game_ui import GameUi
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
                model = CourtyardEntrances({kind: [a], 'I_MAIN_GOTO_SUMMON': [b]})
                self.image[:] = 0
                self.paste(b)
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

    def run_fallback(self, attempts=None):
        return self.ui._try_courtyard_fallback(page_main, page_exploration, self.timer,
                                               {} if attempts is None else attempts)

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
