"""配置路径、停止顺序及同名实例推送回归；不启动任务或设备。"""
import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from module.server.config_manager import ConfigManager, ConfigNameError
from module.server.script_process import ScriptProcess, ScriptState


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigPathTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config'
        self.config.mkdir()
        self.patch = patch.object(ConfigManager, 'config_dir', return_value=self.config)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.config / 'demo.json').write_text('{}')
        (self.root / 'outside.json').write_text('preserve')

    def test_traversal_absolute_and_template_names_are_rejected(self):
        for name in ('../outside', '..\\outside', str(self.root / 'outside'),
                     'template', 'Template', '', 'bad/name'):
            for operation in (lambda: ConfigManager.rename('demo', name),
                              lambda: ConfigManager.rename(name, 'renamed'),
                              lambda: ConfigManager.delete(name),
                              lambda: ConfigManager.copy(name)):
                with self.subTest(name=name), self.assertRaises(ConfigNameError):
                    operation()
        self.assertTrue((self.config / 'demo.json').exists())
        self.assertEqual((self.root / 'outside.json').read_text(), 'preserve')

    def test_regular_names_are_normalized_and_rename_delete_work(self):
        self.assertTrue(ConfigManager.rename(' demo ', '新配置'))
        self.assertTrue(ConfigManager.delete('新配置'))
        self.assertFalse((self.config / '新配置.json').exists())


class ConfigLifecycleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path_patch = patch.object(ConfigManager, 'config_dir', return_value=self.root)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        (self.root / 'demo.json').write_text('{}')
        self.process = SimpleNamespace(state=ScriptState.RUNNING, stop=AsyncMock())
        self.manager = SimpleNamespace(script_process={'demo': self.process},
                                       rename=ConfigManager.rename, delete=ConfigManager.delete)
        with patch.dict('sys.modules', {
                'module.server.main_manager': SimpleNamespace(mm=self.manager)}):
            self.router = load_module('_config_lifecycle_router', 'module/server/script_router.py')

    async def test_file_and_process_record_stay_until_stop_finishes(self):
        for rename in (False, True):
            with self.subTest(rename=rename):
                (self.root / 'demo.json').write_text('{}')
                self.manager.script_process['demo'] = self.process
                self.process.retiring = False
                entered, release = asyncio.Event(), asyncio.Event()

                async def stop():
                    entered.set()
                    await release.wait()

                self.process.stop = AsyncMock(side_effect=stop)
                operation = asyncio.create_task(
                    self.router.config_rename('demo', 'renamed') if rename
                    else self.router.config_delete('demo'))
                await entered.wait()
                self.assertTrue((self.root / 'demo.json').exists())
                self.assertIn('demo', self.manager.script_process)
                self.assertTrue(self.process.retiring)
                with self.assertRaises(HTTPException) as conflict:
                    await self.router.config_delete('demo')
                self.assertEqual(conflict.exception.status_code, 409)
                release.set()
                self.assertTrue(await operation)
                self.process.stop.assert_awaited_once()
                self.assertNotIn('demo', self.manager.script_process)
                self.assertFalse((self.root / 'demo.json').exists())

    async def test_invalid_name_never_stops_or_removes_runtime(self):
        with self.assertRaises(HTTPException) as error:
            await self.router.config_rename('demo', '../outside')
        self.assertEqual(error.exception.status_code, 400)
        self.process.stop.assert_not_awaited()
        self.assertIn('demo', self.manager.script_process)

    async def test_failed_stop_or_file_operation_keeps_runtime(self):
        self.process.stop.side_effect = RuntimeError('still running')
        with self.assertRaises(RuntimeError):
            await self.router.config_delete('demo')
        self.assertTrue((self.root / 'demo.json').exists())
        self.assertIn('demo', self.manager.script_process)
        self.assertFalse(self.process.retiring)
        self.process.stop.side_effect = None
        self.manager.rename = Mock(return_value=False)
        with self.assertRaises(HTTPException):
            await self.router.config_rename('demo', 'renamed')
        self.assertIn('demo', self.manager.script_process)
        self.assertFalse(self.process.retiring)

    async def test_retiring_instance_cannot_restart(self):
        process = ScriptProcess.__new__(ScriptProcess)
        process.retiring = True
        with self.assertRaisesRegex(RuntimeError, '删除或重命名'):
            await process.start()

    async def test_start_rechecks_retiring_after_awaiting_broadcast(self):
        from module.server.setting import State
        process = ScriptProcess.__new__(ScriptProcess)
        process.retiring = False
        process._process = None

        async def mark_retiring(data):
            process.retiring = True

        process.broadcast_state = mark_retiring
        with patch.object(State, 'project_updating', False):
            with self.assertRaisesRegex(RuntimeError, '删除或重命名'):
                await process.start()
        self.assertEqual(process.state, ScriptState.INACTIVE)

    async def test_stop_waits_for_exit_and_retains_live_process_on_timeout(self):
        process = ScriptProcess.__new__(ScriptProcess)
        process.config_name = 'demo'
        process.state = ScriptState.RUNNING
        process.broadcast_state = AsyncMock()
        child = Mock()
        child.is_alive.side_effect = [True, True]
        process._process = child
        with self.assertRaises(RuntimeError):
            await process.stop()
        self.assertIs(process._process, child)
        self.assertEqual(process.state, ScriptState.RUNNING)
        process.broadcast_state.assert_not_awaited()
        child.is_alive.side_effect = [True, False]
        await process.stop()
        self.assertIsNone(process._process)
        self.assertEqual(process.state, ScriptState.INACTIVE)
        child.join.assert_called_with(10)


class PushLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_same_name_replacement_and_removal_cancel_old_workers(self):
        with patch('threading.Thread.start'), \
                patch.object(ConfigManager, 'all_script_files', return_value=[]):
            module = load_module('_config_lifecycle_manager', 'module/server/main_manager.py')
        manager = module.mm

        def instance():
            async def worker():
                await asyncio.Event().wait()
            return SimpleNamespace(config_name='demo', state=ScriptState.RUNNING,
                                   coroutine_broadcast_state=worker,
                                   coroutine_broadcast_log=worker)

        old, new = instance(), instance()
        tasks = {}
        manager.script_process = {'demo': old}
        await manager.sync_push_tasks(tasks)
        old_tasks = [task for _, task in tasks.values()]
        manager.script_process['demo'] = new
        await manager.sync_push_tasks(tasks)
        self.assertTrue(all(task.cancelled() for task in old_tasks))
        self.assertEqual(len(tasks), 2)
        self.assertTrue(all(owner is new for owner, _ in tasks.values()))
        new_tasks = [task for _, task in tasks.values()]
        manager.script_process.clear()
        await manager.sync_push_tasks(tasks)
        self.assertEqual(tasks, {})
        self.assertTrue(all(task.cancelled() for task in new_tasks))
