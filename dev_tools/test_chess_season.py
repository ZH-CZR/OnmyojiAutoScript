"""赛季目录、旧编号和实际OCR调用链；不连接OCR服务或游戏。"""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np

from tasks.Chess.script_task import ScriptTask
from tasks.Chess.strategy.shikigami_catalog import (
    SHIKIGAMI_ENTRIES, SHIKIGAMI_BY_ROMAJI, STORE_SHIKIGAMI_BY_SIGNATURE,
    LEGACY_SHIKIGAMI_KEYS, bond_key, resolve_shikigami, build_lineup_shikigami,
)


class ChessSeasonTest(unittest.TestCase):
    def test_legacy_import_uses_the_same_current_catalog(self):
        from tasks.Chess import shikigami_catalog as legacy
        self.assertIs(legacy.SHIKIGAMI_ENTRIES, SHIKIGAMI_ENTRIES)
        self.assertIs(legacy.resolve_shikigami('3-10'), SHIKIGAMI_BY_ROMAJI['kujira'])

    def test_season_costs_and_bonds(self):
        expected = {
            'yamawaro': (1, ('大江山', '强体')), 'yasha': (2, ('平安京', '强体')),
            'yamakaze': (2, ('七角山', '追击')), 'kujira': (2, ('海国', '回响', '护佑')),
            'miketsu': (2, ('狐妖', '遗念')), 'kappa': (1, ('荒川', '回响')),
            'hakurou': (1, ('七角山', '追击')), 'korouka': (1, ('流火', '遗念')),
            'kuda_gitsune': (1, ('狐妖', '甲胄')), 'komatsumaru': (2, ('七角山', '分裂')),
            'yume_san_byakuzou': (4, ('狐妖', '鬼火', '遗念')),
            'kumon_fuken_gaku': (4, ('流火', '遗念')),
            'arakawa_no_nushi': (5, ('荒川', '回响', '荒川之主')),
            'taira_no_masakado': (5, ('流火', '常世', '狩日将军')),
        }
        for name, (cost, bonds) in expected.items():
            entry = SHIKIGAMI_BY_ROMAJI[name]
            self.assertEqual((entry.cost, entry.bonds), (cost, bonds), name)
            self.assertEqual(STORE_SHIKIGAMI_BY_SIGNATURE[(cost, bond_key(bonds))], name)

    def test_old_numeric_lineup_identifiers_resolve_to_current_entries(self):
        for key, name in LEGACY_SHIKIGAMI_KEYS.items():
            self.assertIs(resolve_shikigami(key), SHIKIGAMI_BY_ROMAJI[name])
            built = build_lineup_shikigami({key: 1})
            self.assertEqual(set(built), {name})
            self.assertEqual(built[name]['catalog_key'], SHIKIGAMI_BY_ROMAJI[name].key)

    def test_menu_matches_the_current_catalog(self):
        path = Path(__file__).resolve().parents[1] / 'tasks/Chess/shikigami/shikigami_menu.txt'
        lines = set(path.read_text(encoding='utf8').splitlines())
        for entry in SHIKIGAMI_ENTRIES:
            self.assertIn(f'{entry.key}:{entry.romaji}:{entry.chinese_name}.', lines)

    def test_updated_bond_ocr_identifies_current_cards_and_prices(self):
        task = object.__new__(ScriptTask)
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        task.O_SHIKIGAMI_SKILL_1 = SimpleNamespace(ocr=Mock())
        for name in ('yamawaro', 'kappa', 'korouka', 'kujira', 'miketsu', 'hakurou', 'yamakaze'):
            entry = SHIKIGAMI_BY_ROMAJI[name]
            task.O_SHIKIGAMI_SKILL_1.ocr.return_value = '\n'.join(entry.bonds)
            task._read_shop_slot_price = Mock(return_value=(entry.cost, str(entry.cost)))
            result = task._recognize_shop_shikigami_by_ocr(1, task.C_SHIKIGAMI_1)
            self.assertIsNotNone(result, name)
            self.assertEqual((result['name'], result['price']), (name, entry.cost))

    def test_ambiguous_shared_bonds_require_price_or_avatar_fallback(self):
        task = object.__new__(ScriptTask)
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
        task.O_SHIKIGAMI_SKILL_1 = SimpleNamespace(ocr=Mock(return_value='七角山\n追击'))
        task._read_shop_slot_price = Mock(return_value=(None, ''))
        self.assertIsNone(task._recognize_shop_shikigami_by_ocr(1, task.C_SHIKIGAMI_1))


if __name__ == '__main__':
    unittest.main()
