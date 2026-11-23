# This Python file uses the following encoding: utf-8
"""RichMan 鼬乐币商店移植回归测试。

来源：lgg686/self ``05fca68a``（tasks/WeeklyPurchase/itachi_shop.py）。
覆盖点：
- 配置默认关闭，且已挂进 RichMan 配置模型与 config/template.json；
- 素材规则与图片文件齐全；
- 礼盒名称匹配容忍 OCR 把「鼬」读成「融」或丢字，已购买的礼盒会被跳过；
- RichMan ScriptTask 已接入 ItachiCoinShop 执行入口。
"""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from tasks.RichMan.assets import RichManAssets
from tasks.RichMan.config import ItachiCoinShop as ItachiCoinShopConfig
from tasks.RichMan.config import RichMan
from tasks.RichMan.itachi_shop import ItachiCoinShop
from tasks.RichMan.script_task import ScriptTask


ROOT = Path(__file__).resolve().parents[1]


class ItachiConfigTests(unittest.TestCase):
    def test_default_disabled(self):
        con = RichMan().itachi_coin_shop
        self.assertIsInstance(con, ItachiCoinShopConfig)
        self.assertFalse(con.itachi_coin_buy_jade)

    def test_template_has_key(self):
        with open(ROOT / 'config' / 'template.json', encoding='utf-8') as f:
            template = json.load(f)
        self.assertIn('itachi_coin_shop', template['rich_man'])
        self.assertFalse(template['rich_man']['itachi_coin_shop']['itachi_coin_buy_jade'])

    def test_i18n_has_keys(self):
        with open(ROOT / 'assets' / 'i18n' / 'zh-CN.json', encoding='utf-8') as f:
            i18n = json.load(f)
        for key in ('itachi_coin_shop', 'itachi_coin_buy_jade', 'itachi_coin_buy_jade_help'):
            self.assertIn(key, i18n)
            self.assertTrue(i18n[key])


class ItachiAssetTests(unittest.TestCase):
    def test_image_rules(self):
        for name in ('I_ITACHI_SHOP_ENTRY', 'I_ITACHI_SHOP_CHECK'):
            rule = getattr(RichManAssets, name)
            self.assertIsInstance(rule, RuleImage)
            self.assertTrue((ROOT / rule.file.lstrip('./')).is_file(), rule.file)

    def test_ocr_rules(self):
        for name in ('O_ITACHI_COIN', 'O_ITACHI_BUY_COST',
                     'O_ITACHI_MINI', 'O_ITACHI_MEDIUM', 'O_ITACHI_LARGE'):
            self.assertIsInstance(getattr(RichManAssets, name), RuleOcr)
        self.assertEqual(RichManAssets.O_ITACHI_MINI.keyword, '小型鼬乐礼盒')
        self.assertEqual(RichManAssets.O_ITACHI_MEDIUM.keyword, '中型鼬乐礼盒')
        self.assertEqual(RichManAssets.O_ITACHI_LARGE.keyword, '大型鼬乐礼盒')


def _boxed(text: str):
    box = np.array([[10, 20], [110, 20], [110, 60], [10, 60]])
    return SimpleNamespace(ocr_text=text, box=box)


class ItachiGiftMatchTests(unittest.TestCase):
    def _make_instance(self):
        task = ItachiCoinShop.__new__(ItachiCoinShop)
        task.device = SimpleNamespace(image=None)
        task.screenshot = lambda: None
        task.O_ITACHI_MINI = RichManAssets.O_ITACHI_MINI
        task.O_ITACHI_MEDIUM = RichManAssets.O_ITACHI_MEDIUM
        task.O_ITACHI_LARGE = RichManAssets.O_ITACHI_LARGE
        return task

    def test_exact_name_match_returns_area(self):
        task = self._make_instance()
        base = RichManAssets.O_ITACHI_MINI.area
        with patch('module.ocr.base_ocr.BaseCor.detect_and_ocr',
                   return_value=[_boxed('小型鼬乐礼盒')]):
            gift = task._find_itachi_gift(set())
        self.assertIsNotNone(gift)
        name, area = gift
        self.assertEqual(name, '小型鼬乐礼盒')
        self.assertEqual(area, (base[0] + 10, base[1] + 20, 100, 40))

    def test_partial_name_is_rejected(self):
        task = self._make_instance()
        with patch('module.ocr.base_ocr.BaseCor.detect_and_ocr',
                   return_value=[_boxed('小型鼬乐礼')]):
            self.assertIsNone(task._find_itachi_gift(set()))

    def test_purchased_gift_is_skipped(self):
        task = self._make_instance()
        base = RichManAssets.O_ITACHI_MEDIUM.area
        with patch('module.ocr.base_ocr.BaseCor.detect_and_ocr',
                   return_value=[_boxed('小型鼬乐礼盒'), _boxed('中型鼬乐礼盒')]):
            gift = task._find_itachi_gift({'小型鼬乐礼盒'})
        self.assertEqual(gift[0], '中型鼬乐礼盒')
        self.assertEqual(gift[1], (base[0] + 10, base[1] + 20, 100, 40))

    def test_ocr_confused_name_still_matches(self):
        """实机 11-23：OCR 把鼬读成融。"""
        task = self._make_instance()
        with patch('module.ocr.base_ocr.BaseCor.detect_and_ocr',
                   return_value=[_boxed('中型融乐礼盒')]):
            gift = task._find_itachi_gift(set())
        self.assertIsNotNone(gift)
        self.assertEqual(gift[0], '中型鼬乐礼盒')

    def test_ocr_dropped_char_still_matches(self):
        """实机 11-23：OCR 输出「小型乐礼盒」，漏掉鼬字。"""
        task = self._make_instance()
        with patch('module.ocr.base_ocr.BaseCor.detect_and_ocr',
                   return_value=[_boxed('小型乐礼盒')]):
            gift = task._find_itachi_gift(set())
        self.assertIsNotNone(gift)
        self.assertEqual(gift[0], '小型鼬乐礼盒')

    def test_unrelated_item_is_rejected(self):
        task = self._make_instance()
        with patch('module.ocr.base_ocr.BaseCor.detect_and_ocr',
                   return_value=[_boxed('雪平女纹章·初级')]):
            self.assertIsNone(task._find_itachi_gift(set()))


class ItachiCoinVerifyTests(unittest.TestCase):
    def test_plausible_reading(self):
        self.assertTrue(ItachiCoinShop._is_coin_reading_plausible((44, 60000)))
        self.assertTrue(ItachiCoinShop._is_coin_reading_plausible((0, 60000)))

    def test_implausible_reading_skipped(self):
        """实机 11-23 购买后读到 7744/6000，应判定不可信而非报错。"""
        self.assertFalse(ItachiCoinShop._is_coin_reading_plausible((7744, 6000)))
        self.assertFalse(ItachiCoinShop._is_coin_reading_plausible(None))
        self.assertFalse(ItachiCoinShop._is_coin_reading_plausible((1, 0)))


class ItachiScriptTaskTests(unittest.TestCase):
    def test_script_task_has_execute_entry(self):
        self.assertTrue(issubclass(ScriptTask, ItachiCoinShop))
        self.assertTrue(hasattr(ScriptTask, 'execute_itachi_coin_shop'))


if __name__ == '__main__':
    unittest.main()
