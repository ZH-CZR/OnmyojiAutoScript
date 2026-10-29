"""Offline cold-start checks, including a loopback ADB protocol stub; no real device."""
from concurrent.futures import Future
import socketserver
from threading import Event, Thread
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from adbutils import AdbClient, AdbTimeout
from module.base.timer import Timer
from module.device.platform2.platform_windows import PlatformWindows, EmulatorStartWatchState


class EmulatorColdStartTest(unittest.TestCase):
    def setUp(self):
        self.platform = PlatformWindows.__new__(PlatformWindows)
        self.platform.adb_client = Mock()
        self.platform.adb_client.connect.return_value = 'connected'
        self.shell = self.platform.adb_client.device.return_value.shell
        self.platform.adb_shell = Mock(side_effect=AssertionError('task-level retry used'))
        self.platform.list_app_packages = Mock(side_effect=AssertionError('task-level package query used'))
        self.platform.adb_reconnect = Mock()
        self.platform.list_device = Mock(side_effect=AssertionError('task-level device query used'))
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
        with patch.object(self.platform, '_emulator_start_adb_request',
                          return_value=f'{self.state.serial}\tunauthorized\n'):
            self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.platform.adb_client.connect.assert_not_called()
        self.platform.adb_client.disconnect.assert_not_called()

    def test_device_enumeration_uses_bounded_raw_request(self):
        connection = MagicMock()
        self.platform.adb_client._connect.return_value = connection
        connection.__enter__.return_value.read_string_block.return_value = f'{self.state.serial}\tdevice\n'
        self.state.timeout.remain.return_value = 0.7
        self.assertTrue(self.platform._ensure_emulator_device_ready(self.state))
        self.platform.adb_client._connect.assert_called_once_with(timeout=0.7)
        connection.__enter__.return_value.send_command.assert_called_once_with('host:devices')
        self.platform.list_device.assert_not_called()

    def test_device_enumeration_timeout_does_not_reconnect(self):
        self.platform.adb_client._connect.side_effect = AdbTimeout('ADB service starting')
        self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.platform.adb_reconnect.assert_not_called()
        self.platform.list_device.assert_not_called()

    def test_connect_uses_background_request_with_remaining_budget(self):
        self.state.timeout.remain.return_value = 0.7
        with patch.object(self.platform, '_emulator_start_adb_request', return_value=''):
            self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.state.adb_connect.result(timeout=1)
        self.platform.adb_client.connect.assert_called_once_with(self.state.serial, timeout=0.7)
        self.platform.adb_reconnect.assert_not_called()

    def test_offline_boot_transport_is_not_disconnected_or_reconnected(self):
        with patch.object(self.platform, '_emulator_start_adb_request',
                          return_value=f'{self.state.serial}\toffline\n') as request:
            for _ in range(5):
                self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.assertEqual([call.args[1] for call in request.call_args_list],
                         ['host:devices'] * 5)
        self.platform.adb_client.connect.assert_not_called()
        self.platform.adb_client.disconnect.assert_not_called()

    def test_failed_connect_retries_only_after_cooldown(self):
        self.state.adb_connect = Future()
        self.state.adb_connect.set_exception(AdbTimeout('transport not ready'))
        self.state.adb_connect_retry = Mock()
        self.state.adb_connect_retry.reached.side_effect = [False, True]
        with patch.object(self.platform, '_emulator_start_adb_request', return_value=''):
            self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
            self.platform.adb_client.connect.assert_not_called()
            self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.state.adb_connect.result(timeout=1)
        self.platform.adb_client.connect.assert_called_once_with(self.state.serial, timeout=120.0)
        self.state.adb_connect_retry.reset.assert_called_once_with()

    def test_repeated_wait_logs_only_on_status_change(self):
        with patch.object(self.platform, '_emulator_start_adb_request',
                          side_effect=[f'{self.state.serial}\toffline\n'] * 3
                          + [f'{self.state.serial}\tunauthorized\n']), \
                patch('module.device.platform2.platform_windows.logger.info') as log:
            for _ in range(4):
                self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.assertEqual(log.call_count, 2)

    def test_real_adb_client_delayed_connect_does_not_restart_or_block_readiness(self):
        # 独立回环服务模拟 ADB 协议，不访问真实 ADB/模拟器。连接响应超过旧 3 秒超时，
        # 但设备可独立上线；必须复用同一请求，且不用等 host:connect 返回才识别就绪。
        started, release = Event(), Event()
        online = Event()
        connects = []
        serial = self.state.serial

        class Handler(socketserver.BaseRequestHandler):
            def receive(self, size):
                result = b''
                while len(result) < size:
                    chunk = self.request.recv(size - len(result))
                    if not chunk:
                        raise EOFError('client closed')
                    result += chunk
                return result

            def handle(self):
                command = self.receive(int(self.receive(4), 16)).decode()
                if command == f'host:connect:{serial}':
                    connects.append(command)
                    started.set()
                    release.wait(10)
                    output = f'connected to {serial}'.encode()
                elif command == 'host:devices':
                    output = f'{serial}\tdevice\n'.encode() if online.is_set() else b''
                else:
                    raise AssertionError(command)
                self.request.sendall(b'OKAY' + f'{len(output):04x}'.encode() + output)

        with socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler) as server:
            worker = Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
            worker.start()
            self.platform.adb_client = AdbClient(host='127.0.0.1', port=server.server_address[1])
            try:
                self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
                self.assertTrue(started.wait(1))
                self.assertFalse(release.wait(3.2))
                for _ in range(4):
                    self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
                self.assertEqual(len(connects), 1)
                self.assertFalse(self.state.adb_connect.done())
                online.set()
                self.assertTrue(self.platform._ensure_emulator_device_ready(self.state))
                self.assertFalse(self.state.adb_connect.done())
            finally:
                release.set()
                if self.state.adb_connect is not None:
                    self.state.adb_connect.result(timeout=2)
                server.shutdown()
                worker.join(timeout=1)
        self.platform.adb_reconnect.assert_not_called()
        self.platform.list_device.assert_not_called()

    def test_expired_budget_skips_device_probe_and_connect(self):
        self.state.timeout.remain.return_value = 0
        self.assertFalse(self.platform._ensure_emulator_device_ready(self.state))
        self.platform.adb_client._connect.assert_not_called()
        self.platform.adb_client.connect.assert_not_called()

    def test_window_with_children_is_ready_on_first_check(self):
        self.state.struct_window = Timer(10)
        self.state.new_window = 123
        with patch('module.device.platform2.platform_windows.Handle.handle_has_children', return_value=True):
            self.assertTrue(self.platform._is_emulator_window_ready(self.state))

    def test_window_fallback_wait_overlaps_android_boot(self):
        with patch.object(self.platform, '_get_handler', return_value=None), \
                patch('module.device.platform2.platform_windows.get_focused_window', return_value=0), \
                patch('module.base.timer.time.time', return_value=1000):
            state = self.platform._build_emulator_watch_state(SimpleNamespace(serial=self.state.serial))
        with patch('module.base.timer.time.time', return_value=1005):
            self.assertFalse(self.platform._is_emulator_window_ready(state))
        with patch('module.base.timer.time.time', return_value=1011):
            self.assertTrue(self.platform._is_emulator_window_ready(state))

    def test_minimizing_ready_window_does_not_add_fixed_sleep(self):
        self.platform.config = SimpleNamespace(script=SimpleNamespace(device=SimpleNamespace(
            emulator_window_minimize=True, run_background_only=False, handle='MuMu')))
        with patch('module.device.platform2.platform_windows.minimize_by_name') as minimize, \
                patch.object(Timer, 'wait') as wait:
            self.platform._finalize_emulator_window(self.state)
        minimize.assert_called_once_with('MuMu')
        wait.assert_not_called()

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
        self.state.adb_connect = Future()
        instance = SimpleNamespace(serial=self.state.serial)
        with patch.object(self.platform, '_build_emulator_watch_state', return_value=self.state), \
                patch.object(self.platform, '_wait_emulator_watch_tick', return_value=False):
            self.assertFalse(self.platform.emulator_start_watch(instance))
        self.shell.assert_not_called()
        self.assertFalse(self.state.adb_connect.done())
        self.platform.adb_client.connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
