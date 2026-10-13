# This Python file uses the following encoding: utf-8
"""批次 23「共享 UI 资产统一化 · 收尾」(#1881) 的回归测试。

背景
----
批次 20 已把「确认 / 取消 / 勾选」收敛到 ``GlobalGameAssets`` 的共享资产，
但上游在两个后续 PR 里补完了新 UI 下的勾选框与登录弹窗资产：

* ``916e6eb8`` (#1931)：更新 ``ui_ui_check.png`` / ``ui_ui_uncheck.png``
  为**新版 UI** 的勾选框素材（旧素材在新 UI 下识别不到，导致组队「默认邀请」
  勾选框状态判断失效 —— issue #1881）；
* ``e8df3ae0`` (#1930)：``check_and_invite`` 里 ``I_UI_UNCHECK`` /
  ``I_UI_CONFIRM`` 的重复点击间隔由 ``1`` 放宽到 ``3``（点太快时新素材
  还没渲染完，会被判为「未勾选」而反复点击）；
* ``5b556e92``：登录 / 邮件相关私有资产改用共享资产，并删除一批同义私有资产：
  - ``RestartAssets.I_CANCEL_BATTLE`` / ``I_WATCH_VIDEO_CANCEL`` /
    ``I_LOGIN_LOGIN_CANCEL_BIND_PHONE`` → ``GlobalGameAssets.I_UI_CANCEL_SAMLL``；
  - 同时把 ``I_UI_CONFIRM`` / ``I_UI_CANCEL`` 的 ``roi_back`` 放大、把
    ``I_UI_UNCHECK`` 的 ``roi_front`` 左移到新素材位置。

本地架构与上游不同：登录实现在 ``tasks/Component/Login/service.py``
（上游仍在 ``tasks/Restart/login.py``），因此登录侧的替换是**手工移植**。

本测试钉死不变量：私有资产确已删除、调用点确实改用共享资产、ROI 与
``image.json`` 同步、勾选框素材为新版。若有人回退任一项，用例立刻变红。
"""
import ast
import hashlib
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GG_ASSETS = REPO / "tasks" / "GlobalGame" / "assets.py"
GG_IMAGE_JSON = REPO / "tasks" / "GlobalGame" / "ui" / "image.json"
GG_CHECK_PNG = REPO / "tasks" / "GlobalGame" / "ui" / "ui_ui_check.png"
GG_UNCHECK_PNG = REPO / "tasks" / "GlobalGame" / "ui" / "ui_ui_uncheck.png"
RESTART_ASSETS = REPO / "tasks" / "Restart" / "assets.py"
LOGIN_JSON = REPO / "tasks" / "Restart" / "login" / "image.json"
HARVEST_JSON = REPO / "tasks" / "Restart" / "harvest" / "image.json"
LOGIN_SERVICE = REPO / "tasks" / "Component" / "Login" / "service.py"
DEFAULT_PAGES = REPO / "tasks" / "GameUi" / "default_pages.py"
GENERAL_INVITE = REPO / "tasks" / "Component" / "GeneralInvite" / "general_invite.py"

# 新版 UI 勾选框素材（git blob hash，等价于上游 916e6eb8 的产物）。
NEW_CHECK_BLOB = "0a21262c6916152bfe7e33ab35d83aeb1cfc0e63"
NEW_UNCHECK_BLOB = "eb41e476a943dec85903abf49d25b1ff2502654a"

# 本批认定已删除的私有资产。
DELETED_PRIVATE_ASSETS = (
    "I_CANCEL_BATTLE",
    "I_WATCH_VIDEO_CANCEL",
    "I_LOGIN_LOGIN_CANCEL_BIND_PHONE",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git_blob_hash(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _iter_rule_assignments(source: str):
    """遍历类体里 ``Foo = RuleImage/RuleOcr(...)`` 形式的赋值。"""
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
            if not (isinstance(call.func, ast.Name) and call.func.id in ("RuleImage", "RuleOcr")):
                continue
            yield target.id, call


def _image_rules(source: str) -> dict:
    """解析 ``Foo = RuleImage(...)``，返回 {名字: {kwarg: 值}}。"""
    rules = {}
    for name, call in _iter_rule_assignments(source):
        kwargs = {}
        for kw in call.keywords:
            try:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            except ValueError:
                kwargs[kw.arg] = ast.dump(kw.value)
        rules[name] = kwargs
    return rules


def _json_by_name(path: Path, key: str = "itemName") -> dict:
    return {entry[key]: entry for entry in json.loads(_read(path))}


def _method_source(source: str, name: str) -> str:
    """截取类方法 ``name`` 的源码文本（用于按调用点做断言）。"""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise AssertionError(f"未找到方法 {name}")


class CheckboxAssetTests(unittest.TestCase):
    """新 UI 勾选框素材与 ROI 必须成对更新。"""

    def test_check_png_is_new_ui_asset(self):
        self.assertTrue(GG_CHECK_PNG.exists())
        self.assertEqual(_git_blob_hash(GG_CHECK_PNG), NEW_CHECK_BLOB)

    def test_uncheck_png_is_new_ui_asset(self):
        self.assertTrue(GG_UNCHECK_PNG.exists())
        self.assertEqual(_git_blob_hash(GG_UNCHECK_PNG), NEW_UNCHECK_BLOB)

    def test_uncheck_roi_front_moved_for_new_art(self):
        rules = _image_rules(_read(GG_ASSETS))
        self.assertEqual(tuple(rules["I_UI_UNCHECK"]["roi_front"]), (545, 343, 33, 36))

    def test_confirm_roi_back_widened(self):
        rules = _image_rules(_read(GG_ASSETS))
        self.assertEqual(tuple(rules["I_UI_CONFIRM"]["roi_back"]), (643, 345, 231, 320))

    def test_cancel_roi_back_widened(self):
        rules = _image_rules(_read(GG_ASSETS))
        self.assertEqual(tuple(rules["I_UI_CANCEL"]["roi_back"]), (356, 384, 275, 256))

    def test_image_json_matches_assets_py(self):
        """``assets.py`` 与 ``image.json`` 的 ROI 必须逐项一致（roiFront ↔ roi_front）。"""
        rules = _image_rules(_read(GG_ASSETS))
        entries = _json_by_name(GG_IMAGE_JSON)
        for asset_name, item_name, front, back in (
            ("I_UI_UNCHECK", "ui_uncheck", "roi_front", "roi_back"),
            ("I_UI_CONFIRM", "ui_confirm", "roi_front", "roi_back"),
            ("I_UI_CANCEL", "ui_cancel", "roi_front", "roi_back"),
        ):
            expected_front = ",".join(str(v) for v in rules[asset_name][front])
            expected_back = ",".join(str(v) for v in rules[asset_name][back])
            self.assertEqual(entries[item_name]["roiFront"], expected_front, asset_name)
            self.assertEqual(entries[item_name]["roiBack"], expected_back, asset_name)


class PrivateAssetRemovalTests(unittest.TestCase):
    """登录 / 邮件私有资产必须已被删除，避免又改回旧引用。"""

    def test_restart_assets_drops_private_login_assets(self):
        rules = _image_rules(_read(RESTART_ASSETS))
        for name in DELETED_PRIVATE_ASSETS:
            self.assertNotIn(name, rules, f"RestartAssets 仍定义了 {name}")

    def test_deleted_png_files_are_gone(self):
        for name in (
            "login_cancel_battle.png",
            "login_watch_video_cancel.png",
            "login_login_cancel_bind_phone.png",
        ):
            self.assertFalse((REPO / "tasks" / "Restart" / "login" / name).exists(), name)

    def test_login_image_json_drops_removed_entries(self):
        entries = _json_by_name(LOGIN_JSON)
        for name in ("cancel_battle", "watch_video_cancel", "login_login_cancel_bind_phone"):
            self.assertNotIn(name, entries)

    def test_harvest_image_json_drops_mail_confirm(self):
        entries = _json_by_name(HARVEST_JSON)
        self.assertNotIn("harvest_mail_confirm", entries)


class LoginCallSiteTests(unittest.TestCase):
    """登录流程调用点必须改用共享取消按钮。"""

    def test_login_service_uses_shared_cancel(self):
        source = _read(LOGIN_SERVICE)
        self.assertEqual(source.count("self.I_UI_CANCEL_SAMLL"), 3)
        for name in DELETED_PRIVATE_ASSETS:
            self.assertNotIn(f"self.{name}", source, f"登录服务仍引用 {name}")

    def test_default_pages_main_hook_uses_shared_cancel(self):
        source = _read(DEFAULT_PAGES)
        self.assertNotIn("RestartAssets.I_CANCEL_BATTLE", source)
        self.assertIn(
            "GlobalGameAssets.I_UI_BACK_RED, GlobalGameAssets.I_UI_CANCEL_SAMLL",
            source,
        )


class InviteIntervalTests(unittest.TestCase):
    """``check_and_invite`` 的勾选框 / 确认按钮重复点击间隔必须放宽到 3。"""

    def setUp(self):
        self.method = _method_source(_read(GENERAL_INVITE), "check_and_invite")

    def test_uncheck_uses_interval_3(self):
        self.assertTrue(
            re.search(r"I_UI_UNCHECK,\s*interval=3", self.method),
            "I_UI_UNCHECK 未使用 interval=3",
        )

    def test_confirm_uses_interval_3(self):
        self.assertTrue(
            re.search(r"I_UI_CONFIRM,\s*interval=3", self.method),
            "I_UI_CONFIRM 未使用 interval=3",
        )


if __name__ == "__main__":
    unittest.main()
