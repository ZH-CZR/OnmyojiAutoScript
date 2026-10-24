"""Synthetic log isolation and request redaction; never read user logs/configs."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from module.logger import normalize_log_name
from module.server import api_logger, log_service, log_stats


class LogIsolationTest(unittest.TestCase):
    def test_full_config_names_have_independent_files_stats_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('account_main', 'account_alt', 'account'):
                (root / f'2026-01-01_{name}.txt').write_text(f'{name}\n', encoding='utf-8')
            with patch.object(log_service, 'LOG_ROOT', root), patch.object(log_stats, 'LOG_ROOT', root):
                browser = log_service.LogBrowserService()
                stats = log_stats.LogStatsService()
                for name in ('account_main', 'account_alt'):
                    self.assertEqual(normalize_log_name(name), name)
                    files = browser.list_log_files(name)
                    self.assertEqual([f.file_name for f in files], [f'2026-01-01_{name}.txt'])
                    self.assertEqual(stats.build_stats(name, date(2026, 1, 1))['script_name'], name)
                    self.assertEqual(log_service.build_error_log_dir_name(name, 1234567890000),
                                     f'{name}_1234567890000')


class ApiPrivacyTest(unittest.IsolatedAsyncioTestCase):
    async def test_query_url_and_body_secrets_do_not_reach_log_summary(self):
        body = json.dumps({'password': 'body-secret', 'notify_config': 'https://notify.invalid/token',
                           'scheduler': {'enable': True}}).encode()
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        request = Request({
            'type': 'http', 'method': 'PUT', 'scheme': 'http', 'server': ('localhost', 1234),
            'path': '/demo/GlobalGame/server/password/value',
            'query_string': b'value=query-secret&types=string&token=direct-secret',
            'headers': [(b'content-type', b'application/json')],
            'path_params': {'argument': 'password'},
        }, receive)
        summary = await api_logger.build_request_summary(request)
        encoded = json.dumps(summary)
        for secret in ('query-secret', 'direct-secret', 'body-secret', 'notify.invalid'):
            self.assertNotIn(secret, encoded)
        self.assertEqual(summary['body']['scheduler']['enable'], True)
        self.assertEqual(summary['query_params']['types'], 'string')

    def test_gui_values_defaults_nested_tokens_and_copy_json_response_redacted(self):
        response = JSONResponse({'groups': [
            {'name': 'password', 'default': 'default-secret', 'value': 'value-secret'},
            {'name': 'notify_config', 'default': 'notify-secret', 'value': 'notify-value'},
        ], 'script': {'error': {'notify_config': 'nested-secret'}}, 'enable': True})
        result = api_logger.summarize_response(response)
        for secret in ('default-secret', 'value-secret', 'notify-secret', 'notify-value', 'nested-secret'):
            self.assertNotIn(secret, json.dumps(result))
        self.assertTrue(result['body']['enable'])

    async def test_validation_error_echo_is_hidden_without_changing_http_response(self):
        app = FastAPI()
        app.router.route_class = api_logger.ApiLoggingRoute
        @app.put('/settings')
        async def settings(value: str):
            return JSONResponse({'detail': f'invalid value {value}'}, status_code=400)

        messages = []
        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        async def send(message):
            messages.append(message)
        with patch.object(api_logger, 'log_http_access') as log:
            await app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                       'method': 'PUT', 'scheme': 'http', 'path': '/settings',
                       'query_string': b'value=private-test-value', 'headers': [],
                       'server': ('localhost', 1234), 'client': ('localhost', 1235)}, receive, send)
        self.assertNotIn('private-test-value', json.dumps(log.call_args.args[0]))
        self.assertIn(b'private-test-value', b''.join(m.get('body', b'') for m in messages))


if __name__ == '__main__':
    unittest.main()
