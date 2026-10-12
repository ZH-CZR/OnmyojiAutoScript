# This Python file uses the following encoding: utf-8
"""批次 22「掩码模板匹配」的回归测试。

背景
----
上游 self 源 ``8753481b``（LGG686）为匹配框架新增 ``Masked template matching``：
掩码按约定取模板同目录的 ``xxx_mask.png``，非零参与匹配、零忽略，用于滤掉会变化
的背景与镂空；掩码缺失或尺寸不符时自动回退普通匹配。同批还带来两处加固：
``TM_CCOEFF_NORMED`` 在同色窗口下算出的 nan/inf 统一压成 -1.0（nan 静默漏检、
inf 会把命中指到随机坐标），以及按「参与区域」而非整张模板判断是否退化为常量。

本地与 runhey 的落点不同：匹配统一由图像服务（``module/image/runtime.py``）分派，
``RuleImage`` 只把 method 原样透传给 RPC。因此本测试直接驱动服务端公开接口
``ImageRuntime.match_rule``，钉死三件事：

1. **新功能有效**：掩码忽略区的背景变化时，掩码匹配仍能命中，普通匹配不行；
   掩码方法同样支持 ``match_all``；
2. **新功能安全**：掩码缺失/尺寸不符自动回退普通匹配且结果与普通匹配逐位一致；
   参与区域同色的退化模板、同色窗口算出的 nan/inf 都不产生假阳性；改掩码后
   模板缓存必须失效重载；
3. **旧功能不回归**：普通模板匹配分数与位置不变，多尺度 / SIFT 分派原样可用，
   未知 method 仍 ``raise ValueError``，全仓 ``image.json`` 声明的 method 都在
   服务端可分派集合内，且标注器下拉选项与分派集合一致。
"""
import json
import pickle
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from module.atom.image import RuleImage
from module.image.runtime import ImageRuntime
from module.server.annotator_rule_schema import RULE_TYPE_SCHEMAS

REPO_ROOT = Path(__file__).resolve().parents[1]

# 服务端 ``_match_rule`` / ``_match_all_template`` 能分派的 method 全集。
SUPPORTED_METHODS = {
    "Template matching",
    "Masked template matching",
    "Multi-scale template matching",
    "Sift Flann",
}


class _MaskedFixture:
    """构造「模板 + 掩码 + 场景」：掩码只保留模板右半的特征区。

    模板左半是一块纯色（会被掩码忽略、允许在实机里随背景变化），右半是棋盘特征；
    场景把特征区放在 ``TRUE_LOCATION``，左半按需填成不同背景。
    """

    WIDTH = 40
    HEIGHT = 40
    FEATURE_WIDTH = 20
    TRUE_LOCATION = (60, 70)
    SCENE_SIZE = 200

    def __init__(self, workdir):
        self.workdir = Path(workdir)
        self.template_path = self.workdir / "tp_fixture.png"
        self.mask_path = self.workdir / "tp_fixture_mask.png"

        checker = np.indices((self.HEIGHT, self.FEATURE_WIDTH)).sum(axis=0) % 8 < 4
        template = np.zeros((self.HEIGHT, self.WIDTH, 3), np.uint8)
        template[:, : self.FEATURE_WIDTH] = 12
        template[:, self.FEATURE_WIDTH:] = np.where(checker[:, :, None], 240, 20).astype(np.uint8)
        self.template = template
        # 服务端按 BGR 解码后转 RGB，落盘时反序写入才能与场景（RGB）同序
        cv2.imwrite(str(self.template_path), template[:, :, ::-1])

    def write_mask(self, *, keep_right=True):
        """写入 40x40 掩码；``keep_right=False`` 时换一块内容等尺寸的掩码。"""
        mask = np.zeros((self.HEIGHT, self.WIDTH), np.uint8)
        mask[:, self.FEATURE_WIDTH if keep_right else 0: self.WIDTH if keep_right else self.FEATURE_WIDTH] = 255
        cv2.imwrite(str(self.mask_path), mask)

    def write_wrong_size_mask(self):
        cv2.imwrite(str(self.mask_path), np.zeros((11, 11), np.uint8))

    def remove_mask(self):
        self.mask_path.unlink(missing_ok=True)

    def scene(self, *, background_matches=False, seed=0):
        """构造场景；``background_matches=True`` 时左半背景与模板一致（普通匹配也命中）。"""
        rng = np.random.default_rng(seed)
        x, y = self.TRUE_LOCATION
        scene = np.full((self.SCENE_SIZE, self.SCENE_SIZE, 3), 200, np.uint8)
        scene[y:y + self.HEIGHT, x + self.FEATURE_WIDTH:x + self.WIDTH] = self.template[:, self.FEATURE_WIDTH:]
        left = (
            self.template[:, : self.FEATURE_WIDTH]
            if background_matches
            else rng.integers(0, 255, (self.HEIGHT, self.FEATURE_WIDTH, 3), dtype=np.uint8)
        )
        scene[y:y + self.HEIGHT, x:x + self.FEATURE_WIDTH] = left
        return scene

    def rule(self, method="Template matching", threshold=0.8):
        return {
            "name": "tp_fixture",
            "file": str(self.template_path),
            "method": method,
            "threshold": threshold,
            "roi_front": [0, 0, self.WIDTH, self.HEIGHT],
            "roi_back": [0, 0, self.SCENE_SIZE, self.SCENE_SIZE],
        }

    def payload(self, **kwargs):
        return pickle.dumps(self.scene(**kwargs))


class _RuntimeTestCase(unittest.TestCase):
    """公共夹具：临时目录 + 低线程数运行时 + 背景会变化的场景。"""

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.fixture = _MaskedFixture(tmpdir.name)
        self.fixture.write_mask()
        # worker_count=1：测试不需要并发，减少线程开销
        self.runtime = ImageRuntime({"worker_count": 1})

    def match(self, method, **kwargs):
        return self.runtime.match_rule(self.fixture.rule(method), image_bytes=self.fixture.payload(**kwargs))


class MaskedTemplateMatchTests(_RuntimeTestCase):
    """新功能：掩码匹配生效、可回退、可缓存。"""

    def test_masked_match_ignores_changing_background(self):
        plain = self.match("Template matching")
        masked = self.match("Masked template matching")

        # 背景被掩码忽略：普通匹配被拉低到阈值以下，掩码匹配仍稳稳命中
        self.assertFalse(plain["matched"])
        self.assertTrue(masked["matched"])
        self.assertGreater(masked["score"], plain["score"])
        self.assertEqual(masked["roi_front"], [60, 70, 40, 40])

    def test_missing_mask_falls_back_to_plain_matching(self):
        self.fixture.remove_mask()
        plain = self.match("Template matching")
        masked = self.match("Masked template matching")

        # 缺掩码 = 普通匹配，分数与命中与否都必须逐位一致（不得抛错）
        self.assertEqual(masked["score"], plain["score"])
        self.assertEqual(masked["matched"], plain["matched"])
        self.assertIsNone(
            self.runtime._get_template_entry(str(self.fixture.template_path), with_mask=True).mask
        )

    def test_wrong_size_mask_falls_back_to_plain_matching(self):
        self.fixture.write_wrong_size_mask()
        plain = self.match("Template matching")
        masked = self.match("Masked template matching")

        self.assertEqual(masked["score"], plain["score"])
        self.assertEqual(masked["matched"], plain["matched"])

    def test_masked_match_supports_match_all(self):
        rule = self.fixture.rule("Masked template matching")
        matches = self.runtime._match_all_template(image=self.fixture.scene(), rule=rule)

        self.assertTrue(matches, "掩码方法必须支持全量匹配")
        best = max(matches)
        self.assertEqual(best[1:], (60, 70, 40, 40))

    def test_mask_path_convention_is_same_directory(self):
        derived = Path(ImageRuntime._resolve_mask_path(str(self.fixture.template_path)))

        self.assertEqual(derived, self.fixture.mask_path)

    def test_changing_mask_invalidates_template_cache(self):
        entry = self.runtime._get_template_entry(str(self.fixture.template_path), with_mask=True)
        self.assertIsNotNone(entry.mask)
        # 未改动时复用同一条缓存
        self.assertIs(entry, self.runtime._get_template_entry(str(self.fixture.template_path), with_mask=True))

        self.fixture.write_mask(keep_right=False)
        reloaded = self.runtime._get_template_entry(str(self.fixture.template_path), with_mask=True)

        # 指纹含掩码 mtime:size，改掩码后必须重新加载
        self.assertIsNot(reloaded, entry)


class DegenerateAndNanGuardTests(_RuntimeTestCase):
    """新功能的安全边界：退化模板与同色窗口不得产生假阳性。"""

    def test_degenerate_judgement_follows_masked_region(self):
        mask = np.zeros((self.fixture.HEIGHT, self.fixture.WIDTH), np.uint8)
        mask[:, self.fixture.FEATURE_WIDTH:] = 255

        # 参与区域有起伏 → 不是退化模板（不能误杀）
        self.assertFalse(ImageRuntime._template_is_degenerate(self.fixture.template, mask))

        # 整图同色 → 退化
        flat = np.full((self.fixture.HEIGHT, self.fixture.WIDTH, 3), 30, np.uint8)
        self.assertTrue(ImageRuntime._template_is_degenerate(flat))

        # 忽略区有起伏但参与区域同色 → 同样退化（判据只看参与区域）
        flat_with_noisy_ignored = flat.copy()
        flat_with_noisy_ignored[:, : self.fixture.FEATURE_WIDTH] = np.random.default_rng(1).integers(
            0, 255, (self.fixture.HEIGHT, self.fixture.FEATURE_WIDTH, 3), dtype=np.uint8
        )
        self.assertTrue(ImageRuntime._template_is_degenerate(flat_with_noisy_ignored, mask))

    def test_flat_template_is_not_matched(self):
        flat_path = self.fixture.workdir / "tp_flat.png"
        cv2.imwrite(str(flat_path), np.full((self.fixture.HEIGHT, self.fixture.WIDTH, 3), 30, np.uint8))

        for method in ("Template matching", "Masked template matching"):
            rule = self.fixture.rule(method)
            rule["file"] = str(flat_path)
            result = self.runtime.match_rule(rule, image_bytes=self.fixture.payload(background_matches=True))
            # 常量模板会被 OpenCV 特判成整张 1.0（假阳性），必须被提前拦掉
            self.assertFalse(result["matched"], method)

    def test_solid_source_window_produces_no_false_positive(self):
        solid = np.full((self.fixture.SCENE_SIZE, self.fixture.SCENE_SIZE, 3), 128, np.uint8)
        result = self.runtime.match_rule(
            self.fixture.rule("Masked template matching"), image_bytes=pickle.dumps(solid)
        )

        # 同色窗口在掩码下的结果是全 nan；清洗后按不匹配处理，而不是漏检或乱指坐标
        self.assertFalse(result["matched"])
        self.assertTrue(np.isfinite(result["score"]))
        self.assertIsNone(result["roi_front"])

    def test_sanitize_replaces_non_finite_values(self):
        raw = np.array([[np.nan, np.inf, -np.inf, 0.5]], dtype=np.float32)
        cleaned = ImageRuntime._sanitize_match_result(raw, "tp_fixture")

        self.assertTrue(np.isfinite(cleaned).all())
        self.assertEqual(float(cleaned.max()), 0.5)


class ExistingMatchRegressionTests(_RuntimeTestCase):
    """旧功能：普通 / 多尺度 / SIFT 分派与未知方法的行为保持原样。"""

    def test_plain_match_score_and_location_unchanged(self):
        scene = self.fixture.scene(background_matches=True)
        result = self.runtime.match_rule(
            self.fixture.rule("Template matching"), image_bytes=pickle.dumps(scene)
        )

        expected = cv2.matchTemplate(scene, self.fixture.template, cv2.TM_CCOEFF_NORMED)
        self.assertTrue(result["matched"])
        self.assertEqual(result["roi_front"], [60, 70, 40, 40])
        self.assertAlmostEqual(result["score"], float(expected.max()), places=5)

    def test_multi_scale_dispatch_intact(self):
        result = self.match("Multi-scale template matching", background_matches=True)

        # 默认缩放范围 (0.6, 1.2) 覆盖原尺寸档，原尺寸命中必须仍能取到
        self.assertTrue(result["matched"])
        self.assertEqual(result["roi_front"], [60, 70, 40, 40])

    def test_sift_dispatch_still_available(self):
        entry = self.runtime._ensure_template_sift(
            self.runtime._get_template_entry(str(self.fixture.template_path))
        )

        self.assertIsNotNone(entry.sift_des)

    def test_unknown_method_still_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.runtime.match_rule(self.fixture.rule("Bogus matching"), image_bytes=self.fixture.payload())
        with self.assertRaises(ValueError):
            self.runtime._match_all_template(
                image=self.fixture.scene(), rule=self.fixture.rule("Bogus matching")
            )


class RuleImageClientTests(unittest.TestCase):
    """客户端只透传 method：掩码方法不得落进旧分支，旧分支判定不得被改写。"""

    @staticmethod
    def _rule(method):
        return RuleImage(
            roi_front=(0, 0, 40, 40),
            roi_back=(0, 0, 200, 200),
            method=method,
            threshold=0.8,
            file="./tasks/Duel/duel/duel_d_victory_share.png",
        )

    def test_masked_method_is_exposed_and_passed_through(self):
        rule = self._rule(RuleImage.METHOD_MASKED_TEMPLATE_MATCH)

        self.assertTrue(rule.is_masked_template_match)
        self.assertFalse(rule.is_template_match)
        self.assertFalse(rule.is_multi_scale_template_match)
        self.assertFalse(rule.is_sift_flann)
        # 服务端按 method 分派，客户端必须原样透传
        self.assertEqual(rule.to_service_payload()["method"], "Masked template matching")

    def test_test_match_routes_masked_method_to_service(self):
        rule = self._rule(RuleImage.METHOD_MASKED_TEMPLATE_MATCH)
        rule.debug_mode = True

        with patch.object(RuleImage, "match", return_value=True) as mocked:
            self.assertTrue(rule.test_match(np.zeros((10, 10, 3), np.uint8)))

        self.assertEqual(mocked.call_count, 1)

    def test_existing_method_branches_unchanged(self):
        cases = (
            (RuleImage.METHOD_TEMPLATE_MATCH, "is_template_match"),
            (RuleImage.METHOD_MULTI_SCALE_TEMPLATE_MATCH, "is_multi_scale_template_match"),
            (RuleImage.METHOD_SIFT_FLANN, "is_sift_flann"),
        )
        for method, attribute in cases:
            rule = self._rule(method)
            self.assertTrue(getattr(rule, attribute), method)
            self.assertFalse(rule.is_masked_template_match, method)


class RuleMethodWhitelistTests(unittest.TestCase):
    """全仓规则声明必须落在服务端可分派集合内，避免运行期 ``ValueError``。"""

    def test_all_declared_image_rule_methods_are_dispatchable(self):
        methods = set()
        for path in (REPO_ROOT / "tasks").rglob("image.json"):
            for entry in json.loads(path.read_text(encoding="utf-8")):
                method = entry.get("method")
                if method:
                    methods.add(method)

        self.assertTrue(methods, "未扫描到任何 image.json 规则声明")
        self.assertLessEqual(methods, SUPPORTED_METHODS, f"存在未支持的 method: {methods - SUPPORTED_METHODS}")

    def test_generated_assets_declare_dispatchable_methods(self):
        declared = set()
        for path in (REPO_ROOT / "tasks").rglob("assets.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "RuleImage(" not in line:
                    continue
                declared.update(re.findall(r"method\s*=\s*[\"']([^\"']+)[\"']", line))

        self.assertTrue(declared, "未扫描到任何 RuleImage 的 method 声明")
        self.assertLessEqual(declared, SUPPORTED_METHODS, f"存在未支持的 method: {declared - SUPPORTED_METHODS}")

    def test_annotator_options_match_service_dispatch(self):
        fields = RULE_TYPE_SCHEMAS["image"]["fields"]
        options = next(field["options"] for field in fields if field["key"] == "method")

        self.assertEqual(set(options), SUPPORTED_METHODS)


if __name__ == "__main__":
    unittest.main()