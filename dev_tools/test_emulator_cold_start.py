"""Cold-start readiness probes without launching an emulator or connecting ADB."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from adbutils import AdbTimeout
from module.device.platform2.platform_windows import PlatformWindows, EmulatorStartWatchState


class EmulatorColdStartTest(unittest.TestCase):
    def setUp(self):
        self.platform = PlatformWindows.__new__(PlatformWindows)
        self.platform.adb_client = Mock()
        self.shell = self.platform.adb_client.device.return_value.shell
        self.platform.adb_shell = Mock(side_effect=AssertionError('task-level retry used'))
        self.platform.list_app_packages = Mock(side_effect=AssertionError('task-level package query used'))
        self.platform.adb_reconnect = Mock()
        self.state = EmulatorStartWatchState(
            serial='127.0.0.1:16384', current_window=0, interval=Mock(),
            timeout=Mock(), struct_window=Mock(), launch_confirm=None)
        self.state.timeout.remain.return_value = 120.0

    def test_shell_available_before_android_boot_is_not_ready(self):
        for output in ('', '0\n', 'pong'):
            self.shell.return_value = output
            self.assertFalse(self.platform._ensure_emulator_command_ready(self.state))
        self.shell.return_value = '1\r\n'
        self.assertTrue(self.platform._ensure_emulator_command_ready(self.state))
        self.shell.assert_called_with(['getprop', 'sys.boot_completed'], timeout=3.0)
        self.platform.adb_shell.assert_not_called()

    def test_package_timeout_waits_then_succeeds_without_reconnect(self):
        self.shell.side_effect = [AdbTimeout('boot in progress'),
                                 'package:app.lawnchair\n',
                                 'package:com.netease.onmyoji.wyzymnqsd_cps\n']
        self.assertFalse(self.platform._ensure_emulator_package_ready(self.state))
        self.assertFalse(self.platform._ensure_emulator_package_ready(self.state))
        self.assertTrue(self.platform._ensure_emulator_package_ready(self.state))
        self.platform.adb_reconnect.assert_not_called()
        self.platform.list_app_packages.assert_not_called()
        self.platform.adb_client.device.assert_called_with(self.state.serial)

    def test_probe_respects_remaining_startup_budget(self):
        self.state.timeout.remain.return_value = 0.7
        self.shell.return_value = '1'
        self.assertTrue(self.platform._ensure_emulator_command_ready(self.state))
        self.shell.assert_called_once_with(['getprop', 'sys.boot_completed'], timeout=0.7)
        self.shell.reset_mock()
        self.state.timeout.remain.return_value = 0
        self.assertFalse(self.platform._ensure_emulator_command_ready(self.state))
        self.assertFalse(self.platform._ensure_emulator_package_ready(self.state))
        self.shell.assert_not_called()

    def test_boot_connection_reset_is_transient(self):
        self.shell.side_effect = ConnectionResetError('boot transport reset')
        self.assertFalse(self.platform._ensure_emulator_command_ready(self.state))
        self.platform.adb_reconnect.assert_not_called()

    def test_unauthorized_device_is_not_ready(self):
        device = SimpleNamespace(status='unauthorized')
        self.platform.list_device = Mock()
        self.platform.list_device.return_value.select.return_value.first_or_none.return_value = device
        self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.platform.adb_client.disconnect.assert_not_called()

    def test_watch_waits_through_boot_and_package_timeout_then_finishes(self):
        self.shell.side_effect = ['0', '1', AdbTimeout('package service starting'),
                                 '1', 'package:com.netease.onmyoji.test\n']
        instance = SimpleNamespace(serial=self.state.serial)
        with patch.object(self.platform, '_build_emulator_watch_state', return_value=self.state), \
                patch.object(self.platform, '_wait_emulator_watch_tick', side_effect=[True] * 3), \
                patch.object(self.platform, '_check_handler_launch_state', return_value=('ready', {})), \
                patch.object(self.platform, '_hide_emulator_window_if_needed'), \
                patch.object(self.platform, '_track_emulator_focus_window'), \
                patch.object(self.platform, '_ensure_emulator_device_ready', return_value=True), \
                patch.object(self.platform, '_is_emulator_window_ready', return_value=True), \
                patch.object(self.platform, '_finalize_emulator_window') as finalize:
            self.assertTrue(self.platform.emulator_start_watch(instance))
        finalize.assert_called_once_with(self.state)
        self.platform.adb_reconnect.assert_not_called()
        self.platform.adb_shell.assert_not_called()
        self.platform.list_app_packages.assert_not_called()

    def test_watch_returns_failure_when_overall_startup_budget_expires(self):
        instance = SimpleNamespace(serial=self.state.serial)
        with patch.object(self.platform, '_build_emulator_watch_state', return_value=self.state), \
                patch.object(self.platform, '_wait_emulator_watch_tick', return_value=False):
            self.assertFalse(self.platform.emulator_start_watch(instance))
        self.shell.assert_not_called()


if __name__ == '__main__':
    unittest.main()
