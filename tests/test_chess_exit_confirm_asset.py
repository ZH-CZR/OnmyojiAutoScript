# This Python file uses the following encoding: utf-8
"""百鬼棋局退出确认弹窗资产回归测试。

背景
----
2026-11-24 实机诊断（`E_CLICK_GUARD_TOO_MANY`）显示：棋局退出确认弹窗已经
出现在屏幕上，但 ``I_CHESS_EXIT_CONFIRM`` / ``I_CHESS_EXIT_CANCEL`` 两个
规则始终命中失败，任务因此反复点击左上角退出按钮，约 19 秒后触发
``GameTooManyClickError: PAGE_CHESS_EXIT``，每轮重启游戏后继续循环。

离线比对错误截图后定位到两个独立问题：

1. ``page_chess_exit_confirm.png`` 是旧版按钮素材，与当前游戏渲染整体
   偏移约 5~7px；旧素材在固化 ROI 内得分 0.155，上游 ``725baa1a0``
   替换后的新素材得分 0.9995。
2. 两条规则的 ``roi_back`` 与 ``roi_front`` 完全相等（搜索区域没有余量），
   而模拟器下 ``ROI_MATCH_PAD`` 为 0，任何相位差都会让匹配直接失败。

本测试钉死不变量：确认按钮素材为上游新版本、两条规则的搜索区域带余量、
``assets.py`` 与 ``image_chess.json`` 保持同步。若有人回退任一项，用例变红。
"""
import hashlib
import json
import unittest
from pathlib import Path

import cv2
import numpy as np

from tasks.GameUi.assets import GameUiAssets

REPO = Path(__file__).resolve().parent.parent
PAGE_DIR = REPO / 'tasks' / 'GameUi' / 'page'
CONFIRM_PNG = PAGE_DIR / 'page_chess_exit_confirm.png'
CANCEL_PNG = PAGE_DIR / 'page_chess_exit_cancel.png'
IMAGE_JSON = PAGE_DIR / 'image_chess.json'

# 上游 oYe486 725baa1a0「fix(chess): replace obsolete quit confirmation asset」
# 的确认按钮素材。
UPSTREAM_CONFIRM_BLOB = 'aeab60fc3a7401f3e6c14f01fff2138af1158ac6'

# 搜索区域相对模板四边最小余量（像素）。
MIN_ROI_PAD = 16


def _git_blob_hash(path: Path) -> str:
    data = path.read_bytes()
    header = f'blob {len(data)}\0'.encode('ascii')
    return hashlib.sha1(header + data).hexdigest()


def _template_size(path: Path) -> tuple[int, int]:
    """读取模板宽高；用 imdecode 兼容含中文的工作区路径。"""
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    height, width = image.shape[:2]
    return width, height


def _json_rules() -> dict:
    entries = json.loads(IMAGE_JSON.read_text(encoding='utf-8'))
    return {entry['imageName']: entry for entry in entries}


class ChessExitConfirmAssetTest(unittest.TestCase):
    def test_confirm_asset_is_upstream_version(self):
        self.assertEqual(_git_blob_hash(CONFIRM_PNG), UPSTREAM_CONFIRM_BLOB)

    def test_exit_dialog_rules_have_search_margin(self):
        for rule, png in (
            (GameUiAssets.I_CHESS_EXIT_CONFIRM, CONFIRM_PNG),
            (GameUiAssets.I_CHESS_EXIT_CANCEL, CANCEL_PNG),
        ):
            width, height = _template_size(png)
            roi_x, roi_y, roi_w, roi_h = rule.roi_back
            self.assertGreaterEqual(
                roi_w - width, MIN_ROI_PAD * 2, f'{rule.name} 横向搜索余量不足'
            )
            self.assertGreaterEqual(
                roi_h - height, MIN_ROI_PAD * 2, f'{rule.name} 纵向搜索余量不足'
            )
            # 搜索区域必须完整覆盖原标定位置，避免改余量时误挪按钮区域。
            front_x, front_y, front_w, front_h = rule.roi_front
            self.assertLessEqual(roi_x, front_x)
            self.assertLessEqual(roi_y, front_y)
            self.assertGreaterEqual(roi_x + roi_w, front_x + front_w)
            self.assertGreaterEqual(roi_y + roi_h, front_y + front_h)

    def test_json_synced_with_assets(self):
        rules = _json_rules()
        for rule, name in (
            (GameUiAssets.I_CHESS_EXIT_CONFIRM, 'page_chess_exit_confirm.png'),
            (GameUiAssets.I_CHESS_EXIT_CANCEL, 'page_chess_exit_cancel.png'),
        ):
            entry = rules[name]
            self.assertEqual(
                entry['roiFront'], ','.join(str(value) for value in rule.roi_front)
            )
            self.assertEqual(
                entry['roiBack'], ','.join(str(value) for value in rule.roi_back)
            )
            self.assertEqual(entry['threshold'], rule.threshold)


if __name__ == '__main__':
    unittest.main()
