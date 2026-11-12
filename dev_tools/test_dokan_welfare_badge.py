"""鑫字寮徽截图回放及目标隔离；不连接设备或 OCR 服务。"""
from pathlib import Path
from types import SimpleNamespace
import json
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from tasks.Dokan.script_task import ScriptTask
from dev_tools import test_dokan_challenge


FIXTURES = Path(__file__).parent / 'fixtures'


class DokanWelfareBadgeTests(unittest.TestCase):
    def make_task(self, number=1):
        task = object.__new__(ScriptTask)
        task.device = SimpleNamespace(image=np.array(Image.open(
            FIXTURES / f'dokan_welfare_{number}.png').convert('RGB')))
        task.welfare_names = []
        task.open_welfare = False
        task.screenshot = Mock()
        return task

    def test_supplied_list_screenshots_and_other_guilds(self):
        for number, y in ((1, 320), (2, 250)):
            task = self.make_task(number)
            with self.subTest(screenshot=number):
                self.assertTrue(task.has_welfare_badge((1125, y, 25, 25)))
                for other_y in (y - 145, y + 145):
                    self.assertFalse(task.has_welfare_badge((1125, other_y, 25, 25)))

    def test_badge_follows_scrolled_row(self):
        task = self.make_task()
        source = task.device.image.copy()
        for shift in (-180, -80, 80, 180):
            image = source.copy()
            image[28:602, 1075:1255] = 0
            image[245 + shift:318 + shift, 1125:1200] = source[245:318, 1125:1200]
            task.device.image = image
            with self.subTest(shift=shift):
                self.assertTrue(task.has_welfare_badge((1125, 320 + shift, 25, 25)))
                self.assertFalse(task.has_welfare_badge((1125, 320, 25, 25)))

    def test_name_and_other_nodes_cannot_supply_badge(self):
        task = self.make_task()
        source = task.device.image.copy()
        image = np.zeros_like(source)
        # Even an exact copy of the template in the name area must be excluded.
        image[350:400, 1136:1180] = source[263:313, 1136:1180]
        task.device.image = image
        self.assertFalse(task.has_welfare_badge((1125, 320, 25, 25)))
        task = self.make_task(3)
        self.assertFalse(task.has_welfare_badge((353, 304, 66, 28), joined=True))

    def test_clipped_or_invalid_rows_are_ignored(self):
        task = self.make_task()
        for box in ((1125, 80, 25, 25), (1125, 610, 25, 25),
                    (1000, 320, 25, 25), (1240, 320, 25, 25),
                    (1125, 320, 0, 25)):
            self.assertFalse(task.has_welfare_badge(box), box)

    def test_unknown_name_can_be_confirmed_by_two_badge_frames(self):
        task = self.make_task()
        with patch('tasks.Dokan.script_task.time.sleep') as sleep:
            self.assertTrue(task.is_welfare_candidate('天邪鬼', (1125, 320, 25, 25)))
        sleep.assert_called_once_with(0.35)
        task.screenshot.assert_called_once()

    def test_transient_badge_is_not_confirmed(self):
        task = self.make_task()
        task.screenshot.side_effect = lambda: setattr(task.device, 'image', np.zeros((720, 1280, 3), np.uint8))
        with patch('tasks.Dokan.script_task.time.sleep'):
            self.assertFalse(task.is_welfare_candidate('天邪鬼', (1125, 320, 25, 25)))

    def test_name_alone_is_sufficient_and_badge_is_also_checked(self):
        task = self.make_task()
        task.welfare_names = ['已知福利寮']
        task.has_welfare_badge = Mock(return_value=False)
        self.assertTrue(task.is_welfare_candidate('已知福利寮', (1125, 320, 25, 25)))
        task.has_welfare_badge.assert_called_once_with((1125, 320, 25, 25))
        task.screenshot.assert_not_called()

    def test_neither_name_nor_badge_is_not_welfare(self):
        task = self.make_task()
        self.assertFalse(task.is_welfare_candidate('普通鑫字寮名', (1125, 175, 25, 25)))

    def test_empty_name_does_not_skip_badge_candidate(self):
        harness = test_dokan_challenge.DokanChallengeTests()
        task = harness.make_task([''])
        task.has_welfare_badge.return_value = True
        with patch('tasks.Dokan.script_task.time.sleep'):
            task.is_welfare_candidate = lambda name, box: ScriptTask.is_welfare_candidate(task, name, box)
            self.assertTrue(task.find_dokan(harness.con, welfare_flag=True))
        self.assertTrue(task.open_welfare)

    def test_joined_unknown_name_uses_map_badge(self):
        task = self.make_task(3)
        with patch('tasks.Dokan.script_task.RuleOcr') as rule, \
                patch('tasks.Dokan.script_task.time.sleep'):
            rule.return_value.ocr.return_value = '豆豆小屋'
            task.identify_joined_welfare((610, 304, 66, 28))
        self.assertTrue(task.open_welfare)
        task.screenshot.assert_called_once()

    def test_joined_transient_badge_is_not_confirmed(self):
        task = self.make_task(3)
        task.screenshot.side_effect = lambda: setattr(task.device, 'image', np.zeros((720, 1280, 3), np.uint8))
        with patch('tasks.Dokan.script_task.RuleOcr') as rule, \
                patch('tasks.Dokan.script_task.time.sleep'):
            rule.return_value.ocr.return_value = '豆豆小屋'
            task.identify_joined_welfare((610, 304, 66, 28))
        self.assertFalse(task.open_welfare)

    def test_icon_only_candidate_enters_welfare_search(self):
        harness = test_dokan_challenge.DokanChallengeTests()
        task = harness.make_task(['未收录的福利寮'])
        task.has_welfare_badge.return_value = True
        with patch('tasks.Dokan.script_task.time.sleep'):
            # The AST harness supplies its own virtual clock.
            task.is_welfare_candidate = lambda name, box: ScriptTask.is_welfare_candidate(task, name, box)
            self.assertTrue(task.find_dokan(harness.con, welfare_flag=True))
        self.assertTrue(task.open_welfare)

    def test_asset_definitions_match_json(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / 'tasks/Dokan/res/image.json').read_text(encoding='utf-8'))
        task = self.make_task()
        for kind in ('list', 'map'):
            entry = next(item for item in data if item['itemName'] == f'dokan_welfare_badge_{kind}')
            rule = getattr(task, f'I_DOKAN_WELFARE_BADGE_{kind.upper()}')
            self.assertEqual(rule.threshold, entry['threshold'])
            self.assertEqual(tuple(rule.roi_back), tuple(map(int, entry['roiBack'].split(','))))
            self.assertEqual(rule.image.shape[:2], (50, 44))


if __name__ == '__main__':
    unittest.main()
