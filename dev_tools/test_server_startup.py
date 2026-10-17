"""Run with: python -m unittest dev_tools.test_server_startup"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import server


class ServerStartupTest(unittest.TestCase):
    def test_startup_runs_requested_instances_and_update_service(self):
        import asyncio
        from unittest.mock import AsyncMock
        import module.server.app as web
        with patch.object(web, 'ensure_api_logger'), \
                patch.object(web.app, 'state', SimpleNamespace(script_instances=['oas1'])), \
                patch.object(web.mm, 'restart_processes', new_callable=AsyncMock) as restart, \
                patch.object(web.update_service, 'start') as update_start:
            asyncio.run(web.on_startup())
        restart.assert_awaited_once_with(['oas1'])
        update_start.assert_called_once_with()

    def launch(self, *, ocr_error=None, image_error=None, web_error=None):
        calls = []

        def operation(name, error=None):
            def run(*args, **kwargs):
                calls.append(name)
                if error:
                    raise error
            return run

        settings = SimpleNamespace(WebuiHost='127.0.0.1', WebuiPort=22267)
        with patch.object(sys, 'argv', ['server.py']), \
                patch.object(server, 'State', SimpleNamespace(deploy_config=settings)), \
                patch.object(server, 'logger'), \
                patch.object(server, 'ensure_image_server_ready', operation('image', image_error)), \
                patch.object(server, 'ensure_ocr_server_ready', operation('ocr', ocr_error)), \
                patch.object(server, 'shutdown_image_server', operation('stop_image')), \
                patch.object(server, 'shutdown_ocr_server', operation('stop_ocr')), \
                patch('uvicorn.Server.run', operation('web', web_error)):
            try:
                server.fun()
            except RuntimeError:
                calls.append('raised')
        return calls

    def test_ocr_failure_keeps_control_panel_available(self):
        self.assertEqual(
            self.launch(ocr_error=ModuleNotFoundError('paddleocr')),
            ['image', 'ocr', 'web', 'stop_image', 'stop_ocr'],
        )

    def test_success_closes_both_services(self):
        self.assertEqual(self.launch(), ['image', 'ocr', 'web', 'stop_image', 'stop_ocr'])

    def test_image_failure_cleans_up(self):
        self.assertEqual(
            self.launch(image_error=RuntimeError('image startup failed')),
            ['image', 'stop_image', 'stop_ocr', 'raised'],
        )

    def test_http_failure_cleans_up(self):
        self.assertEqual(
            self.launch(web_error=RuntimeError('port occupied')),
            ['image', 'ocr', 'web', 'stop_image', 'stop_ocr', 'raised'],
        )

    def test_update_restart_replaces_python_after_rpc_cleanup(self):
        from unittest.mock import Mock
        calls = []
        state = SimpleNamespace(deploy_config=SimpleNamespace(
            WebuiHost='127.0.0.1', WebuiPort=22267))
        web = Mock()

        def run():
            state.request_restart()
            self.assertTrue(web.should_exit)
            calls.append('http_stopped')

        web.run.side_effect = run
        with patch.object(sys, 'argv', ['server.py', '--port', '22267']), \
                patch.object(server, 'State', state), \
                patch.object(server, 'ensure_image_server_ready'), \
                patch.object(server, 'ensure_ocr_server_ready'), \
                patch.object(server, 'shutdown_image_server', side_effect=lambda: calls.append('image_stopped')), \
                patch.object(server, 'shutdown_ocr_server', side_effect=lambda: calls.append('ocr_stopped')), \
                patch('uvicorn.Server', return_value=web), \
                patch.object(server.os, 'execv', side_effect=lambda *args: calls.append('exec')) as restart:
            server.fun()
        self.assertEqual(calls, ['http_stopped', 'image_stopped', 'ocr_stopped', 'exec'])
        restart.assert_called_once_with(sys.executable,
                                       [sys.executable, 'server.py', '--port', '22267'])
        self.assertIsNone(state.request_restart)
