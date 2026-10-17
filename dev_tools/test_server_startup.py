"""Run with: python -m unittest dev_tools.test_server_startup"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import server


class ServerStartupTest(unittest.TestCase):
    def test_startup_update_preserves_requested_instances_until_restart(self):
        import asyncio
        from unittest.mock import AsyncMock
        import module.server.app as web
        state = SimpleNamespace(update_resume_instances=None)
        updater = SimpleNamespace(start=AsyncMock(), last_result={'status': 'updated'},
                                  start_error=lambda: 'restart required')
        with patch.object(web, 'State', state), \
                patch.object(web, 'update_service', updater), \
                patch.object(web, 'ensure_api_logger'), \
                patch.object(web.app, 'state', SimpleNamespace(script_instances=['oas1'])), \
                patch.object(web.mm, 'restart_processes', new_callable=AsyncMock) as restart:
            asyncio.run(web.on_startup())
        self.assertEqual(['oas1'], state.update_resume_instances)
        restart.assert_not_awaited()

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
                patch('uvicorn.run', operation('web', web_error)):
            try:
                server.fun(None)
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
