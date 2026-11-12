"""悬赏刷新光圈的真实局部截图回归，不连接设备。"""

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock

import cv2
import numpy as np

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.WantedQuests.assets import WantedQuestsAssets


FIXTURES = Path(__file__).parent / 'fixtures' / 'wanted_seal'


def fixture(name):
    return cv2.cvtColor(cv2.imread(str(FIXTURES / name)), cv2.COLOR_BGR2RGB)


class WantedSealTest(unittest.TestCase):
    def canvas(self, name, x, y):
        image = np.full((720, 1280, 3), 90, dtype=np.uint8)
        patch = fixture(name)
        image[y:y + patch.shape[0], x:x + patch.shape[1]] = patch
        return image

    def test_refresh_effect_recognizes_courtyard_and_clicks_inside_seal(self):
        image = self.canvas('seal_refresh_effect.png', 152, 150)
        ui = GameUi.__new__(GameUi)
        ui.maybe_screenshot = Mock()
        ui.appear = lambda rules, interval=None: any(
            deepcopy(rule).match(image) for rule in rules)
        self.assertTrue(ui.ui_page_appear(page_main))

        seal = deepcopy(WantedQuestsAssets.I_WQ_SEAL)
        self.assertTrue(seal.match(image))
        self.assertGreater(seal.max_val, 0.95)
        # 多尺度匹配后的点击区域应落在实际“封”字内。
        x, y, w, h = seal.roi_front
        self.assertTrue(170 <= x < x + w <= 200)
        self.assertTrue(160 <= y < y + h <= 205)
        for _ in range(100):
            cx, cy = seal.coord()
            self.assertTrue(170 <= cx <= 200 and 160 <= cy <= 205)

    def test_old_full_icon_still_matches_at_different_courtyard_positions(self):
        for x, y in ((244, 181), (166, 162), (500, 300)):
            with self.subTest(position=(x, y)):
                image = self.canvas('seal_before_refresh.png', x, y)
                seal = deepcopy(WantedQuestsAssets.I_WQ_SEAL)
                self.assertTrue(seal.match(image))
                self.assertEqual(seal.roi_front[:2], [x + 10, y + 5])

    def test_outer_effect_changes_do_not_affect_glyph(self):
        patch = fixture('seal_refresh_effect.png')
        for seed in range(4):
            image = np.random.default_rng(seed).integers(
                0, 256, (720, 1280, 3), dtype=np.uint8)
            # 原截图的中央字形位于 (176,169)，保留字形并改变整个外部区域。
            image[169:195, 176:194] = patch[19:45, 24:42]
            self.assertTrue(deepcopy(WantedQuestsAssets.I_WQ_SEAL).match(image))

    def test_blank_done_icon_and_icon_outside_search_region_are_rejected(self):
        seal = deepcopy(WantedQuestsAssets.I_WQ_SEAL)
        image = np.full((720, 1280, 3), 90, dtype=np.uint8)
        self.assertFalse(seal.match(image))
        done = deepcopy(WantedQuestsAssets.I_WQ_DONE)
        mat = done.image
        image[183:183 + mat.shape[0], 248:248 + mat.shape[1]] = mat
        self.assertFalse(seal.match(image))
        image = self.canvas('seal_refresh_effect.png', 1000, 150)
        self.assertFalse(seal.match(image))


if __name__ == '__main__':
    unittest.main()
