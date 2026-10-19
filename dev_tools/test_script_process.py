"""Worker lifecycle regressions; spawned probes never construct game tasks."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from module.config.manual import active_task_suspensions
from module.config.startup_order import active_startup_orders
from module.server.script_process import ScriptProcess, ScriptState, _SCRIPT_PROCESS_CONTEXT, func


def _offline_bootstrap_failure(queue, log_pipe):
    # Exercise the real spawn/worker error path before Script/device creation.
    with patch('module.logger.set_file_logger', side_effect=OSError('offline bootstrap failure')), \
            patch('module.server.script_process.logger'):
        try:
            func('offline-probe', queue, log_pipe)
        except OSError:
            pass


class ScriptProcessTest(unittest.IsolatedAsyncioTestCase):
    def make_process(self):
        process = ScriptProcess.__new__(ScriptProcess)
        process.config_name, process.retiring = 'offline-probe', False
        process.state, process.active_task = ScriptState.INACTIVE, ''
        process._starting, process._has_started = False, False
        process._process = None
        process.state_queue, process.log_pipe_in, process.log_pipe_out = Mock(), Mock(), Mock()
        process.broadcast_state = AsyncMock()
        return process

    async def test_failed_spawn_never_leaves_configuration_running(self):
        process = self.make_process()
        child = Mock()
        child.start.side_effect = OSError('cannot start child')
        with patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Process', return_value=child), \
                patch('module.server.script_process.logger'):
            with self.assertRaisesRegex(OSError, 'cannot start child'):
                await process.start()
        self.assertEqual(process.state, ScriptState.WARNING)
        self.assertFalse(process._starting)
        self.assertIn('cannot start child', process.broadcast_state.call_args.args[0]['error'])

    async def test_stop_during_start_broadcast_cancels_pending_spawn(self):
        process = self.make_process()
        entered, release = asyncio.Event(), asyncio.Event()

        async def broadcast(data):
            if data['state'] == ScriptState.UPDATING:
                entered.set()
                await release.wait()

        process.broadcast_state = broadcast
        with patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Process') as factory:
            starting = asyncio.create_task(process.start())
            await asyncio.wait_for(entered.wait(), timeout=1)
            stopping = asyncio.create_task(process.stop())
            await asyncio.sleep(0)
            self.assertFalse(stopping.done())
            release.set()
            await asyncio.wait_for(asyncio.gather(starting, stopping), timeout=2)
            factory.assert_not_called()
        self.assertEqual(process.state, ScriptState.INACTIVE)
        self.assertIsNone(process._process)

    async def test_start_waits_for_concurrent_stop_before_replacing_child(self):
        process = self.make_process()
        child = Mock()
        child.is_alive.side_effect = [True, False]
        process._process = child
        process.state = ScriptState.RUNNING
        entered, release = asyncio.Event(), asyncio.Event()

        async def join(*args):
            entered.set()
            await release.wait()

        with patch('module.server.script_process.asyncio.to_thread', side_effect=join), \
                patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Process') as factory:
            stopping = asyncio.create_task(process.stop())
            await asyncio.wait_for(entered.wait(), timeout=1)
            starting = asyncio.create_task(process.start())
            await asyncio.sleep(0)
            factory.assert_not_called()
            release.set()
            await asyncio.wait_for(asyncio.gather(stopping, starting), timeout=2)
            factory.return_value.start.assert_called_once()
        self.assertIs(process._process, factory.return_value)

    async def test_start_waits_for_worker_ready_before_showing_running(self):
        process = self.make_process()
        child = Mock(pid=123)
        with patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Process', return_value=child):
            await process.start()
        self.assertEqual(process.state, ScriptState.UPDATING)
        child.start.assert_called_once()
        process.state_queue.empty.return_value = False
        process.state_queue.get_nowait.return_value = {'state': ScriptState.RUNNING, '_worker_pid': 123}
        process.broadcast_state.side_effect = asyncio.CancelledError()
        with patch('module.server.script_process.sleep', new_callable=AsyncMock):
            await process.coroutine_broadcast_state()
        self.assertEqual(process.state, ScriptState.RUNNING)

    async def test_dead_worker_clears_runtime_once_and_reports_exitcode(self):
        process = self.make_process()
        process.state, process.active_task = ScriptState.RUNNING, 'Dokan'
        process._process = Mock(exitcode=1)
        process._process.is_alive.return_value = False
        with patch.dict(active_task_suspensions, {'offline-probe': [{'name': 'RyouToppa'}]}, clear=True), \
                patch.dict(active_startup_orders, {'offline-probe': object()}, clear=True), \
                patch('module.server.script_process.logger'):
            await process.refresh_state()
            await process.refresh_state()
            self.assertNotIn('offline-probe', active_task_suspensions)
            self.assertNotIn('offline-probe', active_startup_orders)
        self.assertEqual(process.state, ScriptState.WARNING)
        self.assertEqual(process.active_task, '')
        process.broadcast_state.assert_awaited_once()
        self.assertIn('exitcode=1', process.broadcast_state.call_args.args[0]['error'])

    async def test_live_or_starting_worker_is_not_marked_dead(self):
        process = self.make_process()
        process.state, process._starting = ScriptState.UPDATING, True
        await process.refresh_state()
        process._starting = False
        process._process = Mock()
        process._process.is_alive.return_value = True
        await process.refresh_state()
        self.assertEqual(process.state, ScriptState.UPDATING)
        process.broadcast_state.assert_not_awaited()

    async def test_restart_uses_new_queue_and_pipes(self):
        process = self.make_process()
        process._has_started = True
        old_queue, old_in, old_out = process.state_queue, process.log_pipe_in, process.log_pipe_out
        new_queue, new_in, new_out = Mock(), Mock(), Mock()
        with patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Pipe', return_value=(new_out, new_in)), \
                patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Queue', return_value=new_queue), \
                patch('module.server.script_process._SCRIPT_PROCESS_CONTEXT.Process') as factory:
            await process.start()
        old_queue.cancel_join_thread.assert_called_once()
        old_queue.close.assert_called_once()
        old_in.close.assert_called_once()
        old_out.close.assert_called_once()
        self.assertEqual(factory.call_args.kwargs['args'][1:], (new_queue, new_in))

    async def test_stale_worker_ready_is_rejected(self):
        process = self.make_process()
        process._process = SimpleNamespace(pid=123)
        self.assertFalse(process._consume_startup_order({'state': 1, '_worker_pid': 122}))


class SpawnDiagnosticTest(unittest.TestCase):
    def test_real_spawn_reports_failure_before_task_logging_or_device_setup(self):
        queue = _SCRIPT_PROCESS_CONTEXT.Queue()
        reader, writer = _SCRIPT_PROCESS_CONTEXT.Pipe(False)
        child = _SCRIPT_PROCESS_CONTEXT.Process(target=_offline_bootstrap_failure, args=(queue, writer))
        try:
            child.start()
            data = queue.get(timeout=15)
            child.join(10)
            self.assertFalse(child.is_alive())
            self.assertEqual(data['state'], ScriptState.WARNING)
            self.assertEqual(data['_worker_pid'], child.pid)
            self.assertIn('offline bootstrap failure', data['error'])
        finally:
            if child.is_alive():
                child.terminate()
                child.join(5)
            queue.close()
            reader.close()
            writer.close()


if __name__ == '__main__':
    unittest.main()
