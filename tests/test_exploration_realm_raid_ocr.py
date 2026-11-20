# This Python file uses the following encoding: utf-8
"""探索「突破券」OCR 识别区修正的回归测试。

背景
----
``tasks/Exploration/base.py`` 在「点出困难 28」时会用
``O_REALM_RAID_NUMBER1`` 读取右上角突破券数量（``ocr(...)`` 返回
``cu, res, total``）。历史修正：

* 上游 ``92578cd0``（PR #1926）：``(936,10,82,36)`` → ``(920,12,78,30)``；
* nearaura/dev ``bb6f2103``：困难 28 入口仍会多识别一位前导数字，
  上游收窄为 ``(923,16,74,25)``；本地实机验证该值仍包含突破券图标右缘，
  会读成 ``18/30``（实际 ``8/30``），故左边再右移 5px 并按本地实测取
  ``(928,16,69,25)``，``roi`` 与 ``area`` 一致；
* 常规态的 ``O_REALM_RAID_NUMBER`` ``(739,11,78,37)`` **不受影响**。

本测试钉死 ROI 数值与 ``res/ocr.json`` 的同步，防止有人只改一侧或改回旧值。
"""
import ast
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "tasks" / "Exploration" / "assets.py"
OCR_JSON = REPO / "tasks" / "Exploration" / "res" / "ocr.json"


def _ocr_rules(source: str) -> dict:
    """解析类体里 ``Foo = RuleOcr(...)`` 的赋值，返回 {名字: {kwarg: 值}}。"""
    rules = {}
    tree = ast.parse(source)
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            call = node.value
            if not (isinstance(target, ast.Name) and isinstance(call, ast.Call)):
                continue
            if not (isinstance(call.func, ast.Name) and call.func.id == "RuleOcr"):
                continue
            rules[target.id] = {
                kw.arg: ast.literal_eval(kw.value)
                for kw in call.keywords
                if kw.arg in ("roi", "area", "mode", "name")
            }
    return rules


class RealmRaidTicketOcrTests(unittest.TestCase):
    def setUp(self):
        self.rules = _ocr_rules(ASSETS.read_text(encoding="utf-8"))
        self.entries = {
            entry["itemName"]: entry
            for entry in json.loads(OCR_JSON.read_text(encoding="utf-8"))
        }

    def test_hard_mode_roi_is_corrected(self):
        rule = self.rules["O_REALM_RAID_NUMBER1"]
        self.assertEqual(tuple(rule["roi"]), (928, 16, 69, 25))
        self.assertEqual(tuple(rule["area"]), (928, 16, 69, 25))

    def test_normal_mode_roi_unchanged(self):
        """常规态突破券 ROI 不得被误改。"""
        rule = self.rules["O_REALM_RAID_NUMBER"]
        self.assertEqual(tuple(rule["roi"]), (739, 11, 78, 37))

    def test_mode_is_still_digit_counter(self):
        for name in ("O_REALM_RAID_NUMBER", "O_REALM_RAID_NUMBER1"):
            self.assertEqual(self.rules[name]["mode"], "DigitCounter")

    def test_ocr_json_is_synced(self):
        entry = self.entries["realm_raid_number1"]
        self.assertEqual(entry["roiFront"], "928,16,69,25")
        self.assertEqual(entry["roiBack"], "928,16,69,25")
        self.assertEqual(entry["mode"], "DigitCounter")


if __name__ == "__main__":
    unittest.main()
