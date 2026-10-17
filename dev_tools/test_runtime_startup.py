"""Offline checks for direct startup, retained config and update API integration."""
import asyncio
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]


class RuntimeStartupTest(unittest.TestCase):
    def test_main_entry_starts_existing_services_without_installer(self):
        settings = SimpleNamespace(WebuiHost='127.0.0.1', WebuiPort=22288)
        with patch.object(sys, 'argv', ['server.py']), \
                patch('module.server.setting.State', SimpleNamespace(deploy_config=settings)), \
                patch('module.image.rpc.ensure_image_server_ready') as image, \
                patch('module.ocr.rpc.ensure_ocr_server_ready') as ocr, \
                patch('module.image.rpc.shutdown_image_server') as stop_image, \
                patch('module.ocr.rpc.shutdown_ocr_server') as stop_ocr, \
                patch('uvicorn.Server.run') as web, \
                patch('uvicorn.Config') as web_config:
            runpy.run_path(str(ROOT / 'server.py'), run_name='__main__')
        image.assert_called_once_with()
        ocr.assert_called_once_with()
        self.assertEqual(web_config.call_args.kwargs['port'], 22288)
        stop_image.assert_called_once_with()
        stop_ocr.assert_called_once_with()

    def test_server_help_from_directory_with_spaces(self):
        # Exercise the direct entry point without starting RPC or game tasks.
        with tempfile.TemporaryDirectory(prefix='oas launcher 空格 ') as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'server.py'), '--help'],
                cwd=folder, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(b'--host', result.stdout)
        self.assertIn(b'--port', result.stdout)

    def test_old_config_fields_are_ignored_without_rewriting_user_file(self):
        from deploy.config import DeployConfig
        from module.server.config import DeployConfig as ServerConfig
        content = (b'# preserve my settings\nWebuiPort: 24567\n'
                   b'AutoUpdate: true\nInstallDependencies: true\n'
                   b'EnableReload: true\nPythonExecutable: X:/old/python.exe\n')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'deploy.yaml'
            path.write_bytes(content)
            for cls in (DeployConfig, ServerConfig):
                with self.subTest(config=cls):
                    config = cls(str(path))
                    self.assertEqual(config.WebuiPort, 24567)
                    self.assertTrue(config.AutoUpdate)
                    self.assertNotIn('InstallDependencies', config.config)
                    self.assertFalse(hasattr(config, 'EnableReload'))
                    self.assertEqual(path.read_bytes(), content)

    def test_http_menu_and_normal_service_with_update_routes(self):
        import module.server.app as web

        async def request(path, method='GET'):
            messages = []

            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}

            async def send(message):
                messages.append(message)

            await web.app({
                'type': 'http', 'asgi': {'version': '3.0'},
                'http_version': '1.1', 'method': method, 'scheme': 'http',
                'path': path, 'raw_path': path.encode(), 'query_string': b'',
                'root_path': '', 'headers': [], 'client': ('127.0.0.1', 12345),
                'server': ('127.0.0.1', 22267),
            }, receive, send)
            status = next(m['status'] for m in messages
                          if m['type'] == 'http.response.start')
            body = b''.join(m.get('body', b'') for m in messages
                            if m['type'] == 'http.response.body')
            return status, json.loads(body)

        async def check():
            async with web.app.router.lifespan_context(web.app):
                self.assertEqual(await request('/home/test'),
                                 (200, {'message': 'test'}))
                self.assertEqual(await request('/home/home_menu'),
                                 (200, {'Home': [], 'Updater': [], 'Tool': []}))
                self.assertEqual((await request('/home/update_status'))[0], 200)
                from unittest.mock import AsyncMock
                with patch('module.server.home_router.update_service.check', new_callable=AsyncMock, return_value={'is_update': False}), patch('module.server.home_router.update_service.execute', new_callable=AsyncMock, return_value={'updated': False}):
                    self.assertEqual(await request('/home/update_info'), (200, {'is_update': False}))
                    self.assertEqual(await request('/home/execute_update', 'POST'), (200, {'updated': False}))
                    self.assertEqual(await request('/home/execute_update'), (200, {'updated': False}))

        with patch.object(sys, 'argv', ['server.py']), \
                patch.object(web.State, '_deploy_config_',
                             SimpleNamespace(Run=None), create=True), \
                patch.object(web, 'ensure_api_logger'), \
                patch.object(web, 'mm', SimpleNamespace(script_process={})), \
                patch.object(web.update_service, 'start'), \
                patch.object(web.update_service, 'stop', new_callable=AsyncMock):
            web.fastapi_app()
            asyncio.run(check())

    def test_runtime_emulator_types_still_construct(self):
        from module.device.emulator import EmulatorManager
        self.assertTrue(EmulatorManager.SUPPORTED_EMULATORS)
        for emulator in EmulatorManager.SUPPORTED_EMULATORS.values():
            self.assertTrue(emulator.name)
            self.assertTrue(callable(emulator.get_install_dir_from_reg))


if __name__ == '__main__':
    unittest.main()
