# This Python file uses the following encoding: utf-8
"""批次 27「桌面客户端」新功能与 roi_pad 回归测试。

覆盖三件事：
1. 桌面配置组（``script.desktop``）默认值、开关判定与 ``config/template.json`` 同步；
2. ``DesktopDevice`` 的登录态判定（MPay 弹窗存在即视为掉登录）；
3. 桌面渲染相位差容差 ``roi_pad``：远端模板匹配按外扩后的 ROI 搜索，命中坐标
   仍换算回原图；模拟器默认 0 时行为不变；payload 正确透传 pad 值。
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

import module.atom.image as image_atom
from module.atom.image import (DESKTOP_ROI_MATCH_PAD,
                               ROI_MATCH_PAD,
                               RuleImage,
                               set_roi_match_padding)
from module.config.utils import desktop_mode_enabled
from module.device.desktop_device import DesktopDevice
from module.image.runtime import ImageRuntime
from tasks.Script.config import Script
from tasks.Script.config_desktop import Desktop


class DesktopConfigTests(unittest.TestCase):
    def test_default_config_group(self):
        desktop = Desktop()
        self.assertFalse(desktop.enable)
        self.assertEqual(desktop.game_path, '')
        self.assertEqual(desktop.profile_dir, '')
        self.assertEqual(desktop.window_pos, '')
        self.assertEqual(desktop.window_title, '')
        self.assertFalse(desktop.launch_instance)

    def test_script_model_includes_desktop_group(self):
        script = Script()
        self.assertIsInstance(script.desktop, Desktop)
        self.assertFalse(script.desktop.enable)

    def test_template_json_matches_model_fields(self):
        template = json.loads(Path('config/template.json').read_text(encoding='utf-8'))
        desktop = template['script']['desktop']
        self.assertEqual(set(desktop), {
            'enable', 'game_path', 'profile_dir', 'window_pos',
            'window_title', 'launch_instance',
        })
        self.assertFalse(desktop['enable'])

    def test_desktop_mode_enabled_reads_script_desktop_enable(self):
        on = SimpleNamespace(script=SimpleNamespace(desktop=SimpleNamespace(enable=True)))
        off = SimpleNamespace(script=SimpleNamespace(desktop=SimpleNamespace(enable=False)))
        self.assertTrue(desktop_mode_enabled(on))
        self.assertFalse(desktop_mode_enabled(off))


class _FakeDesktop(DesktopDevice):
    def __init__(self, is_desktop, popup):
        self.is_desktop = is_desktop
        self.popup = popup

    def find_desktop_login_popup(self):
        return self.popup


class DesktopLoginStateTests(unittest.TestCase):
    def test_popup_marks_logged_out(self):
        device = _FakeDesktop(True, True)
        self.assertTrue(device.app_lost_login())
        self.assertFalse(device._desktop_login_done)

    def test_no_popup_keeps_state(self):
        device = _FakeDesktop(True, False)
        self.assertFalse(device.app_lost_login())
        self.assertTrue(device._desktop_login_done)

    def test_emulator_mode_never_reports_lost_login(self):
        device = _FakeDesktop(False, True)
        self.assertFalse(device.app_lost_login())
        self.assertTrue(device._desktop_login_done)

    def test_mark_logged_in_after_login(self):
        device = _FakeDesktop(True, True)
        device.app_lost_login()
        device.desktop_mark_logged_in()
        self.assertTrue(device._desktop_login_done)


class _FakeConfig:
    def __init__(self):
        self.script = SimpleNamespace(
            device=SimpleNamespace(screenshot_method='auto', control_method='minitouch')
        )
        self.saved = False

    def save(self):
        self.saved = True


class DesktopInitTests(unittest.TestCase):
    def tearDown(self):
        set_roi_match_padding(0)

    def test_init_desktop_forces_window_methods_and_sets_pad(self):
        device = object.__new__(DesktopDevice)
        device.config = _FakeConfig()
        device.screenshot_interval_set = lambda: None
        device.desktop_window_set_size = lambda: None

        device._init_desktop()

        self.assertEqual(device.config.script.device.screenshot_method, 'window_background')
        self.assertEqual(device.config.script.device.control_method, 'window_message')
        self.assertTrue(device.config.saved)
        self.assertEqual(image_atom.ROI_MATCH_PAD, DESKTOP_ROI_MATCH_PAD)


class RoiPadTests(unittest.TestCase):
    def setUp(self):
        set_roi_match_padding(0)
        self.tmpdir = tempfile.TemporaryDirectory()
        rng = np.random.default_rng(20261019)
        self.template = rng.integers(0, 255, (10, 10, 3), dtype=np.uint8)
        self.template_path = str(Path(self.tmpdir.name) / 'tpl.png')
        cv2.imwrite(self.template_path, self.template)
        self.image = np.zeros((100, 100, 3), dtype=np.uint8)
        # 模板相对整像素 ROI 偏移 1px，模拟桌面 DPI 重采样的相位差
        # 服务端模板统一转 RGB，这里也按 RGB 贴回截图，保证颜色空间一致
        template_rgb = cv2.cvtColor(self.template, cv2.COLOR_BGR2RGB)
        self.image[61:71, 51:61] = template_rgb

    def tearDown(self):
        set_roi_match_padding(0)
        self.tmpdir.cleanup()

    def _rule(self, pad):
        return {
            'name': 'batch27_tpl',
            'file': self.template_path,
            'method': 'Template matching',
            'threshold': 0.99,
            'roi_front': [50, 60, 10, 10],
            'roi_back': [50, 60, 10, 10],
            'roi_pad': pad,
        }

    def _match(self, pad):
        runtime = ImageRuntime()
        return runtime.match_rule(rule_data=self._rule(pad), image_bytes=self._pickle(self.image))

    @staticmethod
    def _pickle(image):
        import pickle
        return pickle.dumps(image)

    def test_one_pixel_phase_shift_needs_padding(self):
        without = self._match(0)
        with_pad = self._match(2)
        self.assertFalse(without['matched'], '原生渲染不该靠容差，外扩关闭时此例应落榜')
        self.assertTrue(with_pad['matched'], '外扩 2px 后应吸收 1px 相位差')
        self.assertEqual(with_pad['roi_front'], [51, 61, 10, 10], '命中坐标必须换算回原图')

    def test_padding_is_clamped_to_image_edge(self):
        runtime = ImageRuntime()
        rule = self._rule(2)
        rule['roi_back'] = [0, 0, 10, 10]
        normalized = runtime._normalize_rule(rule)
        self.assertEqual(normalized['roi_back'], [0, 0, 12, 12])

    def test_payload_carries_padding(self):
        set_roi_match_padding(2)
        rule = RuleImage(
            roi_front=(50, 60, 10, 10),
            roi_back=(50, 60, 10, 10),
            method=RuleImage.METHOD_TEMPLATE_MATCH,
            threshold=0.9,
            file=self.template_path,
        )
        self.assertEqual(rule.to_service_payload()['roi_pad'], 2)

    def test_default_padding_is_zero(self):
        rule = RuleImage(
            roi_front=(50, 60, 10, 10),
            roi_back=(50, 60, 10, 10),
            method=RuleImage.METHOD_TEMPLATE_MATCH,
            threshold=0.9,
            file=self.template_path,
        )
        self.assertEqual(rule.to_service_payload()['roi_pad'], 0)


if __name__ == '__main__':
    unittest.main()
