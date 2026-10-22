# This Python file uses the following encoding: utf-8
"""批次 30 上游修复回归测试。

本批落地三项（均来自 kongdr418/mine，经 ``sync/batch30`` cherry-pick）：

1. ``a9eb4843c`` fix(GameUi): 导航交替换路时空转不报错。
   - 路径签名不再重置 ``progress_timer``（等价路径交替失败会无限重置计时器）；
   - ``repeated_failure_count`` 改为跨边累计，避免交替失败时计数器被换边打断。
2. ``51115b4a8`` fix(annotator): 停止连接导致 Web 服务卡死。
   - 截图方式自适应停止超时（网络方式 8s / 本地 2.5s）；
   - ``terminate()`` 后复查存活并升级 ``kill()``，如实上报状态；
   - 队列排空绑定局部变量并捕获 ``ValueError/OSError``；
   - 截图方式常量与远端方式集合。
3. ``9f07623b5`` feat(Server): 新增模拟器画面截取接口
   （``module/server/screen_router.py``，``/screen`` 前缀）。
"""
import inspect
import unittest
from pathlib import Path
from unittest import mock

from tasks.GameUi.navigator import GameUi
from tasks.GameUi.page import Page, Transition

from module.exception import GamePageUnknownError
from module.server import screen_router, tool, tool_capture_worker, tool_router


# ---------------------------------------------------------------- 导航回归用例


class _Stop(Exception):
    """用于在测试中主动跳出导航循环。"""


class _FakeNavigatorSession:
    def __init__(self):
        self.current_page = None

    def resolve_page(self, page):
        return page

    def add_page(self, page):
        return page


def _make_page(key: str) -> Page:
    return Page(lambda: False, key=key, name=key, register=False)


def _make_transition(source: Page, destination: Page, key: str) -> Transition:
    return Transition(source=source, destination=destination, action=lambda: True, key=key)


class _NavigationHarness:
    """用 ``object.__new__`` 构造的 GameUi 替身，只暴露 goto_page 依赖的成员。"""

    def __init__(self, paths, *, current_page, refresh_limit=200, close_unknown=None):
        self.ui = object.__new__(GameUi)
        self.ui.navigator = _FakeNavigatorSession()
        self.current_page = current_page
        self.paths = paths
        self.path_index = 0
        self.refresh_count = 0
        self.refresh_limit = refresh_limit
        self.close_calls = []
        self.timeout_calls = []
        self.close_unknown_result = False if close_unknown is None else close_unknown

        ui = self.ui
        ui._refresh_current_page = self._refresh_current_page
        ui._run_enter_success_hooks_if_needed = lambda page: None
        ui._build_path = self._build_path
        ui._execute_transition = lambda transition: False
        ui.close_unknown_pages = self._close_unknown_pages
        ui._log_navigation_timeout = self._log_navigation_timeout
        ui._finalize_arrival = lambda destination, confirm_wait, start_time: True

    def _refresh_current_page(self, destination, skip_first_screenshot):
        self.refresh_count += 1
        if self.refresh_count > self.refresh_limit:
            raise _Stop('refresh limit reached')
        return self.current_page

    def _build_path(self, current, destination):
        path = self.paths[self.path_index % len(self.paths)]
        self.path_index += 1
        return path

    def _close_unknown_pages(self, skip_first_screenshot=True):
        self.close_calls.append(skip_first_screenshot)
        if self.close_unknown_result is None:
            raise _Stop('close_unknown_pages called')
        return self.close_unknown_result

    def _log_navigation_timeout(self, *args, **kwargs):
        self.timeout_calls.append(kwargs)


class NavigationAlternatingPathTests(unittest.TestCase):
    """a9eb4843c：交替换路不再无限重置超时、失败计数跨边累计。"""

    def _make_harness(self, timeout_close_unknown=False, close_unknown_value=False):
        current = _make_page('current')
        destination = _make_page('destination')
        first = _make_transition(current, destination, 'edge-a')
        second = _make_transition(current, destination, 'edge-b')
        harness = _NavigationHarness(
            [[first], [second]],
            current_page=current,
            close_unknown=close_unknown_value,
        )
        harness.destination = destination
        return harness

    def test_alternating_path_signatures_do_not_reset_progress_timer(self):
        harness = self._make_harness()
        with self.assertRaises(GamePageUnknownError):
            harness.ui.goto_page(harness.destination, timeout=0.2)
        # 修复前：两种签名交替会一直 reset()，永远走不到超时；这里能超时且循环次数有限。
        self.assertGreater(harness.refresh_count, 1)
        self.assertLess(harness.refresh_count, harness.refresh_limit)
        self.assertTrue(harness.timeout_calls)

    def test_repeated_failure_count_accumulates_across_edges(self):
        harness = self._make_harness()
        # 第 3 次失败（阈值 REPEATED_TRANSITION_FAILURE_THRESHOLD=3）必须触发 close_unknown_pages；
        # 修复前换边会把计数重置为 1，永远不会命中阈值。
        original_close = harness.ui.close_unknown_pages

        def close_unknown(skip_first_screenshot=True):
            original_close(skip_first_screenshot)
            raise _Stop('threshold reached')

        harness.ui.close_unknown_pages = close_unknown
        with self.assertRaises(_Stop):
            harness.ui.goto_page(harness.destination, timeout=30)
        self.assertEqual(harness.close_calls, [False])

    def test_navigator_source_keeps_regression_fix(self):
        source = inspect.getsource(GameUi.goto_page)
        self.assertNotIn('if path_signature != last_progress_signature', source)
        self.assertNotIn('repeated_failure_count = 1', source)
        self.assertIn('repeated_failure_count += 1', source)
        self.assertEqual(GameUi.REPEATED_TRANSITION_FAILURE_THRESHOLD, 3)


# -------------------------------------------------------------- 标注工具回归用例


class _FakeCaptureProcess:
    def __init__(self, dies_on=('terminate',)):
        self.alive = True
        self.dies_on = set(dies_on)
        self.pid = 4321
        self.joins = []
        self.terminated = 0
        self.killed = 0

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        self.joins.append(timeout)

    def terminate(self):
        self.terminated += 1
        if 'terminate' in self.dies_on:
            self.alive = False

    def kill(self):
        self.killed += 1
        if 'kill' in self.dies_on:
            self.alive = False


class AnnotatorStopTests(unittest.TestCase):
    """51115b4a8：停止采集进程超时自适应与逐级升级。"""

    def _session(self, screenshot_method=''):
        session = tool.EmulatorCaptureSession('test-session')
        session.screenshot_method = screenshot_method
        session._process = _FakeCaptureProcess()
        return session

    def test_network_screenshot_method_uses_longer_join_timeout(self):
        self.assertEqual(tool.EMULATOR_CAPTURE_PROCESS_JOIN_TIMEOUT_SECONDS, 2.5)
        self.assertEqual(tool.EMULATOR_CAPTURE_PROCESS_JOIN_TIMEOUT_NETWORK_SECONDS, 8.0)
        session = self._session('ADB')
        self.assertEqual(session._resolve_stop_timeout(), 8.0)
        session.screenshot_method = 'nemu_ipc'
        self.assertEqual(session._resolve_stop_timeout(), 2.5)
        session.screenshot_method = ''
        self.assertEqual(session._resolve_stop_timeout(), 2.5)

    def test_remote_screenshot_methods_constant(self):
        self.assertEqual(
            tool._REMOTE_SCREENSHOT_METHODS,
            {'ADB', 'ADB_nc', 'uiautomator2', 'DroidCast', 'DroidCast_raw', 'scrcpy'},
        )

    def test_stop_escalates_to_kill_and_reports_still_alive(self):
        session = self._session('ADB')
        process = session._process
        process.dies_on = set()  # terminate/kill 都无效
        session.stop(clear_error=True)
        self.assertEqual(process.terminated, 1)
        self.assertEqual(process.killed, 1)
        self.assertEqual(process.joins, [8.0, 1.0, 1.0])
        self.assertIn('无法被终止', session.error)
        self.assertIsNone(session._process)
        self.assertEqual(session.state, 'stopped')

    def test_stop_reports_forced_terminate_when_terminate_works(self):
        session = self._session('nemu_ipc')
        process = session._process
        session.stop(clear_error=True)
        self.assertEqual(process.terminated, 1)
        self.assertEqual(process.killed, 0)
        self.assertEqual(process.joins, [2.5, 1.0])
        self.assertIn('未响应停止命令', session.error)

    def test_stop_without_process_is_clean(self):
        session = self._session()
        session._process = None
        session.stop(clear_error=True)
        self.assertEqual(session.state, 'stopped')
        self.assertEqual(session.error, '')

    def test_drain_status_queue_tolerates_closed_queue(self):
        session = self._session()
        session._state_queue = None
        session._drain_status_queue()  # 不应抛异常

        class ClosedQueue:
            def get_nowait(self):
                raise ValueError('queue is closed')

        session._state_queue = ClosedQueue()
        session._drain_status_queue()  # ValueError 应被吞掉

    def test_release_device_logs_warning_instead_of_silent_pass(self):
        source = inspect.getsource(tool_capture_worker._release_device)
        self.assertIn('logger.warning', source)

    def test_ws_send_timeout_and_disconnect_detection_present(self):
        self.assertEqual(tool_router.ANNOTATOR_WS_SEND_TIMEOUT_SECONDS, 2.0)
        source = inspect.getsource(tool_router._ws_send_frame)
        self.assertIn('asyncio.wait_for', source)
        self.assertIn('_looks_like_client_disconnect', inspect.getsource(tool_router._ws_send_json))


# -------------------------------------------------------------- 画面截取接口用例


class ScreenCaptureApiTests(unittest.TestCase):
    """9f07623b5：新增 /screen 画面截取接口。"""

    def test_screen_name_sanitizes_unsafe_chars(self):
        self.assertEqual(screen_router.screen_name('a/b:c*?'), 'a_b_c__')
        self.assertEqual(screen_router.screen_name('..'), '_')
        self.assertEqual(screen_router.screen_name(''), 'script')
        self.assertEqual(screen_router.screen_name('  '), 'script')
        self.assertEqual(screen_router.screen_name('配置 1'), '配置 1')

    def test_screen_path_layout(self):
        path = screen_router.screen_path('配置 1')
        self.assertEqual(path.parent, Path('./log/screen'))
        self.assertEqual(path.name, '配置 1.png')
        self.assertEqual(screen_router.SCREEN_DIR, Path('./log/screen'))
        self.assertEqual(screen_router.CAPTURE_TIMEOUT_SECONDS, 15)

    def test_screen_info_defaults(self):
        info = screen_router.ScreenInfoResponse(script_name='cfg')
        self.assertFalse(info.has_image)
        self.assertEqual(info.captured_at, '')

    def test_friendly_capture_error_messages(self):
        cases = {
            'Emulator is offline': '模拟器离线',
            'connect failed': '连接不上模拟器',
            'request timeout': '截图超时',
            'RequestHumanTakeover: device init failed': '设备初始化失败',
            'boom': '截图失败：boom',
            '': '截图失败',
        }
        for raw, expected in cases.items():
            self.assertIn(expected, screen_router._friendly_capture_error(raw))

    def test_router_prefix_and_routes(self):
        self.assertEqual(screen_router.screen_app.prefix, '/screen')
        paths = {route.path for route in screen_router.screen_app.routes}
        self.assertIn('/screen/{script_name}', paths)
        self.assertIn('/screen/{script_name}/capture', paths)
        self.assertIn('/screen/{script_name}/image', paths)

    def test_app_registers_screen_router(self):
        source = Path('module/server/app.py').read_text(encoding='utf-8')
        self.assertIn('screen_app', source)
        self.assertIn('include_router(screen_app)', source)


if __name__ == '__main__':
    unittest.main()
