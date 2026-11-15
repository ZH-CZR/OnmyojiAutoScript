# This Python file uses the following encoding: utf-8
"""批次 46 上游修复回归测试。

覆盖 nearaura/dev 窗口内两条超鬼王提交：

1. ``f449cb35`` feat(MetaDemon) 疲劳≥61 优先召唤鬼王：新增配置开关
   ``md_fatigue_summon_first``（默认开），判定插在「自己的鬼王」分支之前。
2. ``b615ec97`` fix(MetaDemon) 更新 ``I_ENTER2`` 识别模板：本地只取新模板图与
   ``roi_front``，保留本地更宽的 ``roi_back`` 搜索区。

kongdr418/mine 的 ``838d4b7c`` 与 lgg686/self 的 ``761614dc`` / ``0ca19ebc`` 依赖
本地不存在的 ``I_MD_CHECK_MAIN_PAGE`` / ``tasks/MetaDemon/assistance.py`` /
``module/cooperation.py``，判定不适用，不在本文件范围内。
"""
import json
import struct
import unittest
from pathlib import Path

from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemon.config import MetaDemonConfig


ROOT = Path(__file__).resolve().parents[1]


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    width, height = struct.unpack('>II', data[16:24])
    return width, height


class FatigueSummonFirstTests(unittest.TestCase):
    def test_config_default_enabled(self):
        field = MetaDemonConfig.model_fields['md_fatigue_summon_first']
        self.assertTrue(field.default)

    def test_branch_precedes_own_boss_detection(self):
        src = (ROOT / 'tasks' / 'MetaDemon' / 'script_task.py').read_text(encoding='utf-8')
        self.assertIn('md_fatigue_summon_first', src)
        self.assertIn('61 <= fatigue <= 100', src)
        self.assertLess(
            src.index('md_fatigue_summon_first'),
            src.index('先看自己有没有鬼王要打'),
            '疲劳优先召唤判定必须在原有自己的鬼王判定之前',
        )


class Enter2AssetTests(unittest.TestCase):
    def test_template_size_matches_roi_front(self):
        asset = MetaDemonAssets.I_ENTER2
        x, y, w, h = asset.roi_front
        self.assertEqual((w, h), (73, 125))
        self.assertEqual(_png_size(ROOT / asset.file), (w, h))

    def test_roi_back_keeps_local_broader_area(self):
        asset = MetaDemonAssets.I_ENTER2
        self.assertEqual(asset.roi_back, (852, 20, 195, 413))

    def test_image_json_synced(self):
        data = json.loads((ROOT / 'tasks' / 'MetaDemon' / 'md' / 'image_2025.json').read_text(encoding='utf-8'))
        entry = next(item for item in data if item['itemName'] == 'enter2')
        self.assertEqual(entry['roiFront'], '933,150,73,125')
        self.assertEqual(entry['roiBack'], '852,20,195,413')


if __name__ == '__main__':
    unittest.main()
