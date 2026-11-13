"""Detached frontend output must not break logs or a real offline spawn."""
import io
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from module.base.console_stream import DetachedConsoleStream, protect_console_streams


def _offline_console_worker(queue):
    from module.logger import logger
    from module.server.script_process import ScriptState
    logger.info('offline spawned worker ready')
    logger.hr('offline closed-console probe')
    print('ordinary worker output', flush=True)
    print('ordinary worker error output', file=sys.stderr, flush=True)
    queue.put(int(ScriptState.RUNNING))


def run_spawn_probe(result_path):
    from module.logger import logger
    ctx = multiprocessing.get_context('spawn')
    queue = ctx.Queue()
    child = ctx.Process(target=_offline_console_worker, args=(queue,))
    try:
        child.start()
        ready = queue.get(timeout=20)
        child.join(10)
        logger.info('offline parent still logs after spawn')
        Path(result_path).write_text(json.dumps({'ready': ready, 'exitcode': child.exitcode}), encoding='utf-8')
    finally:
        if child.is_alive():
            child.terminate()
            child.join(5)
        queue.close()


class ConsoleStreamTest(unittest.TestCase):
    def test_live_stream_keeps_output_and_metadata(self):
        original = io.StringIO()
        stream = DetachedConsoleStream(original)
        self.assertEqual(stream.write('正常日志'), 4)
        stream.flush()
        self.assertEqual(original.getvalue(), '正常日志')
        self.assertFalse(stream.isatty())

    def test_write_and_flush_failures_detach_without_closing_inherited_handle(self):
        for method in ('write', 'flush', 'isatty', 'fileno'):
            for error in (BrokenPipeError('disconnected frontend'), OSError(22, 'invalid handle'), ValueError('closed file')):
                with self.subTest(method=method, error=type(error).__name__):
                    original = Mock()
                    getattr(original, method).side_effect = error
                    stream = DetachedConsoleStream(original)
                    try:
                        getattr(stream, method)(*(['text'] if method == 'write' else []))
                        stream.write('task continues')
                        stream.flush()
                        original.close.assert_not_called()
                    finally:
                        stream._stream.close()

    def test_installation_is_idempotent_and_allows_missing_console(self):
        original = io.StringIO()
        with patch.object(sys, 'stdout', original), patch.object(sys, 'stderr', None):
            protect_console_streams()
            protected = sys.stdout
            protect_console_streams()
            self.assertIs(sys.stdout, protected)
            self.assertIsNone(sys.stderr)
            print('still attached')
            self.assertEqual(original.getvalue(), 'still attached\n')

    def test_real_spawn_survives_closed_frontend_stdout_and_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / 'ready.json'
            code = ('from dev_tools.test_console_streams import run_spawn_probe; '
                    'import sys; run_spawn_probe(sys.argv[1])')
            child = subprocess.Popen([sys.executable, '-c', code, str(result)],
                                     cwd=Path(__file__).resolve().parents[1],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            child.stdout.close()
            child.stderr.close()
            try:
                self.assertEqual(child.wait(timeout=35), 0)
                self.assertEqual(json.loads(result.read_text(encoding='utf-8')), {'ready': 1, 'exitcode': 0})
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
