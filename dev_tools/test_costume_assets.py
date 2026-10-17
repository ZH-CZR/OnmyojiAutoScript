"""Validate generated skin resources and switching preloaded templates."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from module.atom.image import RuleImage
from tasks.Component.Costume.costume_base import CostumeBase
from tasks.Component.CostumeShikigami.assets import CostumeShikigamiAssets


class CostumeAssetsTest(unittest.TestCase):
    def test_all_skin_image_definitions_are_generated(self):
        root = Path(__file__).resolve().parents[1] / 'tasks/Component/CostumeShikigami'
        for definition in root.glob('*/image.json'):
            for item in json.loads(definition.read_text(encoding='utf-8')):
                name = 'I_' + item['itemName'].upper()
                with self.subTest(skin=definition.parent.name, asset=name):
                    asset = getattr(CostumeShikigamiAssets, name)
                    self.assertIsInstance(asset, RuleImage)
                    expected = definition.parent / item['imageName']
                    self.assertTrue(expected.is_file())
                    self.assertEqual(Path(asset.file).resolve(), expected.resolve())

    def test_skin_switch_invalidates_loaded_template_and_method_flags(self):
        old = RuleImage((0, 0, 10, 10), (0, 0, 10, 10), 'Sift Flann', 0.8, 'old.png')
        old._image = np.zeros((10, 10, 3), dtype=np.uint8)
        old._kp = object()
        old._des = object()
        self.assertFalse(old.is_template_match)
        new = CostumeShikigamiAssets.I_SOUL_PRESET_11
        holder = SimpleNamespace(I_PRESET=old)
        CostumeBase.replace_img(holder, 'I_PRESET', new)
        self.assertEqual(old.file, new.file)
        self.assertIsNone(old._image)
        self.assertIsNone(old._kp)
        self.assertIsNone(old._des)
        self.assertTrue(old.is_template_match)
        self.assertIsNot(old.roi_front, new.roi_front)
        np.testing.assert_array_equal(old.image, new.image)

    def test_post_diagnostic_uses_available_confirm_asset(self):
        from unittest.mock import Mock
        from tasks.Utils.post_diagnotor import AnalyzeType, PostDiagnotor

        confirm, overflow = Mock(), Mock()
        confirm.match.return_value = False
        holder = SimpleNamespace(I_UI_CONFIRM=confirm, I_ST_SOUL_OVERFLOW=overflow)
        self.assertEqual(PostDiagnotor.handle(holder, RuntimeError(), 'RyouToppa', np.zeros((1, 1, 3))), AnalyzeType.NONE)
        overflow.match.assert_not_called()
