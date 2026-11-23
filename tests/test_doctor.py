# This Python file uses the following encoding: utf-8
"""体检辅助解析函数的回归测试。"""
from module.server.doctor import parse_adb_devices, parse_packages, parse_wm_size


def test_parse_adb_devices_only_online():
    output = """List of devices attached
16416\tdevice
emulator-5554\toffline
10.0.0.2:5555\tdevice
"""
    assert parse_adb_devices(output) == ["16416", "10.0.0.2:5555"]


def test_parse_wm_size_prefers_last():
    output = """Physical size: 1280x720
Override size: 1920x1080
"""
    assert parse_wm_size(output) == [(1280, 720), (1920, 1080)]


def test_parse_packages():
    output = """package:com.netease.onmyoji
package:com.android.settings
"""
    assert parse_packages(output) == ["com.netease.onmyoji", "com.android.settings"]
