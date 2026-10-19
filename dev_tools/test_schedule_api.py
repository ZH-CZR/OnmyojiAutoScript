"""验证任务开关与空总览的 HTTP/WebSocket 更新，不启动服务或设备。"""
import importlib.util
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import WebSocketDisconnect

from dev_tools import test_task_schedule as schedule_tests


class ScheduleApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = schedule_tests.TaskScheduleTest().make_config()
        self.process = SimpleNamespace(
            state='inactive', connect=AsyncMock(), disconnect=AsyncMock(),
            send_json=AsyncMock(), broadcast_state=AsyncMock(),
        )
        self.manager = SimpleNamespace(
            config_cache=Mock(return_value=self.config),
            script_process={'test': self.process},
        )
        # 独立加载路由并替换管理器，避免全局管理器扫描配置、启动线程。
        path = Path(__file__).resolve().parents[1] / 'module/server/script_router.py'
        spec = importlib.util.spec_from_file_location('_schedule_api_test_router', path)
        self.router = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {
                'module.server.main_manager': SimpleNamespace(mm=self.manager)}):
            spec.loader.exec_module(self.router)

    async def test_explicit_stop_resets_idle_session_only_after_success(self):
        self.process.stop = AsyncMock()
        with patch('module.config.idle.IdleStore') as store:
            await self.router.script_stop('test')
            store.return_value.session.assert_called_once_with(reset=True)
        self.process.stop = AsyncMock(side_effect=RuntimeError('still alive'))
        with patch('module.config.idle.IdleStore') as store:
            with self.assertRaisesRegex(RuntimeError, 'still alive'):
                await self.router.script_stop('test')
            store.assert_not_called()

    async def test_toggle_pushes_overview_including_empty_after_last_disable(self):
        for offset in (-1, 1):
            with self.subTest(days=offset):
                self.config.model.activity_common_2.scheduler.next_run = (
                    datetime.now() + timedelta(days=offset))
                with patch.object(type(self.config.model), 'save') as save:
                    self.assertTrue(await self.router.script_task(
                        'test', 'ActivityCommon2', 'scheduler', 'enable', 'boolean', 'true'))
                    shown = self.process.broadcast_state.call_args.args[0]['schedule']
                    self.assertTrue(shown['running'] or shown['waiting'])
                    self.assertTrue(await self.router.script_task(
                        'test', 'ActivityCommon2', 'scheduler', 'enable', 'boolean', 'false'))
                    self.assertEqual(save.call_count, 2)
                self.process.broadcast_state.assert_awaited_with({
                    'schedule': {'running': {}, 'pending': [], 'waiting': []}})

    async def test_empty_websocket_returns_empty_on_connect_and_refresh(self):
        websocket = SimpleNamespace(receive_text=AsyncMock(
            side_effect=['get_schedule', WebSocketDisconnect()]))
        with patch.object(self.config, 'get_next', side_effect=AssertionError('Must not select task')):
            await self.router.websocket_endpoint(websocket, 'test')
        expected = {'schedule': {'running': {}, 'pending': [], 'waiting': []}}
        self.process.send_json.assert_any_await(websocket, expected)
        self.process.broadcast_state.assert_awaited_once_with(expected)
        self.process.disconnect.assert_awaited_once_with(websocket)

    async def test_failed_save_does_not_push_schedule(self):
        with patch.object(type(self.config.model), 'script_set_arg', return_value=False):
            self.assertFalse(await self.router.script_task(
                'test', 'ActivityCommon', 'scheduler', 'enable', 'boolean', 'false'))
        self.process.broadcast_state.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
