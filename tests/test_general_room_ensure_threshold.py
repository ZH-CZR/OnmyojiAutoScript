# This Python file uses the following encoding: utf-8
"""批次 26「GeneralRoom 建房勾选框阈值入资产」回归测试。

背景
----
上游 ``7c850c3ca``（xylolit-mu/self，2026-09-27）的语义是：把
``ensure_private`` / ``ensure_public`` 里**内联**的 ``threshold=0.7`` 挪进资产，
让 ``assets.py`` 与 ``gr/image.json`` 自身带 0.7。上游注释解释了原因：

    降阈值适配渲染偏差设备；小图标 0.8 太严

本地 ``general_room.py`` 的调用点**没有**内联覆盖（直接 ``self.appear(规则)``），
但 ``assets.py`` / ``image.json`` 仍是 **0.8** → 小勾选框在渲染偏差设备上仍然
过严，会走到「弹窗开关匹配不到」的分支（本地虽有 ``room_mark`` 兜底，但那要求
房间已建成）。本批次把 8 条勾选框规则统一为 0.7，与上游终态一致。

不变量（本测试钉死）
--------------------
1. 8 条勾选框规则（``I_ENSURE_*``）的 ``threshold`` 均为 0.7；
2. ``gr/image.json`` 中同 ROI 的条目阈值同为 0.7（资产单一真源）；
3. ``ensure_private`` / ``ensure_public`` 不再内联传 ``threshold=``（阈值只在资产里）；
4. 未被本提交涉及的规则（``I_CREATE_ENSURE`` / ``I_GR_REFRESH`` 等）阈值保持 0.8。
"""
import json
import re
import unittest
from pathlib import Path

from tasks.Component.GeneralRoom.assets import GeneralRoomAssets

CHECKBOX_RULES = [
    'I_ENSURE_PRIVATE',
    'I_ENSURE_PRIVATE_FALSE',
    'I_ENSURE_PRIVATE_2',
    'I_ENSURE_PRIVATE_FALSE_2',
    'I_ENSURE_PUBLIC',
    'I_ENSURE_PUBLIC_FALSE',
    'I_ENSURE_PUBLIC_2',
    'I_ENSURE_PUBLIC_FALSE_2',
]
UNTOUCHED_RULES = ['I_CREATE_ENSURE', 'I_GR_REFRESH']

IMAGE_JSON = Path('tasks/Component/GeneralRoom/gr/image.json')
SOURCE = Path('tasks/Component/GeneralRoom/general_room.py')


def _roi_key(rule):
    return ','.join(str(v) for v in rule.roi_front)


def _image_json_items():
    with IMAGE_JSON.open(encoding='utf-8') as f:
        return json.load(f)


class GeneralRoomEnsureThresholdTests(unittest.TestCase):
    def test_checkbox_rules_use_asset_threshold_07(self):
        for name in CHECKBOX_RULES:
            rule = getattr(GeneralRoomAssets, name)
            self.assertEqual(
                rule.threshold, 0.7,
                '%s.threshold 应为 0.7（上游 7c850c3ca：小图标 0.8 太严）' % name,
            )

    def test_image_json_matches_assets(self):
        items = {item['roiFront']: item for item in _image_json_items()}
        for name in CHECKBOX_RULES:
            rule = getattr(GeneralRoomAssets, name)
            item = items.get(_roi_key(rule))
            self.assertIsNotNone(item, 'image.json 缺少 %s（ROI %s）' % (name, _roi_key(rule)))
            self.assertEqual(
                item['threshold'], 0.7,
                'image.json 中 %s 的阈值应与 assets.py 一致（0.7）' % name,
            )

    def test_ensure_methods_do_not_override_threshold_inline(self):
        text = SOURCE.read_text(encoding='utf-8')
        start = text.index('def ensure_private')
        end = text.index('def create_ensure')
        body = text[start:end]
        self.assertEqual(
            re.findall(r'threshold\s*=', body), [],
            '阈值应只由资产提供，ensure_private/ensure_public 不应内联 threshold=',
        )
        # 两个方法都还在用这批规则（防止误删调用点）
        for name in CHECKBOX_RULES:
            self.assertIn(name, body, '%s 未被 ensure_private/ensure_public 引用' % name)

    def test_unrelated_rules_keep_default_threshold(self):
        for name in UNTOUCHED_RULES:
            rule = getattr(GeneralRoomAssets, name)
            self.assertEqual(
                rule.threshold, 0.8,
                '%s 不属于本次阈值调整范围，应保持 0.8' % name,
            )


if __name__ == '__main__':
    unittest.main()
