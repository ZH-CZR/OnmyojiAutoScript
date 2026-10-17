"""Offline Git fixtures: never fetch or update the real project."""
import asyncio
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from datetime import time

from module.server.updater import REPOSITORY, UpdateError, Updater
from module.server.update_service import UpdateService
from module.server.setting import State


class LocalUpdater(Updater):
    def command(self, *args, **kwargs):
        if args == ('remote', 'get-url', 'origin'):
            return REPOSITORY
        return super().command(*args, **kwargs)


class GitUpdateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='oas 更新 ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / 'remote.git'
        self.seed = self.base / 'seed'
        self.work = self.base / 'work'
        self.git(self.base, 'init', '--bare', str(self.remote))
        self.git(self.base, 'init', '-b', 'master', str(self.seed))
        self.identity(self.seed)
        (self.seed / 'app.txt').write_text('v1')
        (self.seed / '.gitignore').write_text('*.lock\nprivate.txt\n')
        self.git(self.seed, 'add', '.')
        self.git(self.seed, 'commit', '-m', 'first')
        self.git(self.seed, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.seed, 'push', 'origin', 'master')
        self.git(self.base, 'clone', '-b', 'master', str(self.remote), str(self.work))
        self.identity(self.work)
        (self.work / 'config').mkdir()
        self.updater = LocalUpdater(self.work)
        self.first = self.git(self.work, 'rev-parse', 'HEAD')
        (self.seed / 'app.txt').write_text('v2')
        self.git(self.seed, 'commit', '-am', 'second')
        self.git(self.seed, 'push', 'origin', 'master')

    def git(self, cwd, *args):
        return subprocess.run(['git', *args], cwd=cwd, capture_output=True,
                              text=True, check=True, timeout=15).stdout.strip()

    def identity(self, root):
        self.git(root, 'config', 'user.email', 'offline@example.invalid')
        self.git(root, 'config', 'user.name', 'Offline Test')

    def test_check_does_not_change_worktree_then_fast_forward(self):
        info = self.updater.get_update_info()
        self.assertTrue(info['is_update'])
        self.assertEqual(self.git(self.work, 'rev-parse', 'HEAD'), self.first)
        self.assertTrue(self.updater.execute_pull()['updated'])
        self.assertEqual((self.work / 'app.txt').read_text(), 'v2')
        self.assertFalse(self.updater.execute_pull()['updated'])

    def test_dirty_and_untracked_files_block_without_losing_data(self):
        for name in ('app.txt', 'new.txt'):
            with self.subTest(name=name):
                path = self.work / name
                path.write_text('user change')
                result = self.updater.execute_pull()
                self.assertFalse(result['updated'])
                self.assertTrue(result['dirty'])
                self.assertEqual(path.read_text(), 'user change')
                self.assertEqual(self.git(self.work, 'rev-parse', 'HEAD'), self.first)
                if name == 'app.txt':
                    path.write_text('v1')
                else:
                    path.unlink()

    def test_local_commits_and_wrong_branch_block(self):
        (self.work / 'local.txt').write_text('local')
        self.git(self.work, 'add', '.')
        self.git(self.work, 'commit', '-m', 'local')
        result = self.updater.execute_pull()
        self.assertFalse(result['updated'])
        self.assertEqual(result['ahead'], 1)
        self.git(self.work, 'switch', '-c', 'feature')
        with self.assertRaises(UpdateError):
            self.updater.execute_pull()

    def test_foreign_remote_and_detached_head_rejected(self):
        with self.assertRaises(UpdateError):
            Updater(self.work).get_update_info()
        self.git(self.work, 'checkout', '--detach')
        with self.assertRaises(UpdateError):
            self.updater.execute_pull()

    def test_fetch_failure_cannot_use_stale_remote_to_update(self):
        self.updater.get_update_info()
        self.git(self.work, 'remote', 'set-url', 'origin', str(self.base / 'missing.git'))
        with self.assertRaises(UpdateError):
            self.updater.execute_pull()
        self.assertEqual(self.git(self.work, 'rev-parse', 'HEAD'), self.first)

    def test_new_tracked_file_cannot_overwrite_ignored_user_file(self):
        private = self.work / 'private.txt'
        private.write_text('user data')
        (self.seed / 'private.txt').write_text('remote data')
        self.git(self.seed, 'add', '-f', 'private.txt')
        self.git(self.seed, 'commit', '-m', 'new tracked file')
        self.git(self.seed, 'push', 'origin', 'master')
        with self.assertRaises(UpdateError):
            self.updater.execute_pull()
        self.assertEqual(private.read_text(), 'user data')
        self.assertEqual(self.git(self.work, 'rev-parse', 'HEAD'), self.first)


class UpdateServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        State.project_updating = False
        State.request_restart = None

    async def test_running_task_prevents_git_mutation(self):
        import module.server.main_manager as manager
        service = UpdateService()
        process = SimpleNamespace(_process=Mock(is_alive=Mock(return_value=True)))
        with patch.object(manager.mm, 'script_process', {'x': process}), \
                patch('module.server.update_service.Updater') as updater:
            result = await service.execute()
        self.assertFalse(result['updated'])
        updater.assert_not_called()
        self.assertFalse(State.project_updating)

    async def test_updated_holds_start_guard_and_requests_restart(self):
        import module.server.main_manager as manager
        service = UpdateService()
        callback = Mock()
        State.request_restart = callback
        with patch.object(manager.mm, 'script_process', {}), \
                patch('module.server.update_service.Updater') as updater, \
                patch.object(asyncio.get_running_loop(), 'call_later') as later:
            updater.return_value.execute_pull.return_value = {
                'updated': True, 'success': True, 'restart_required': True}
            result = await service.execute()
        self.assertTrue(result['restart_required'])
        self.assertTrue(State.project_updating)
        later.assert_called_once_with(1, callback)

    async def test_disabled_background_service_never_fetches(self):
        service = UpdateService()
        config = SimpleNamespace(AutoUpdate=False, CheckUpdateInterval=1, read=Mock())
        with patch.object(State, '_deploy_config_', config, create=True), \
                patch.object(service, 'check', new_callable=AsyncMock) as check:
            service.start()
            await asyncio.sleep(0)
            await service.stop()
        check.assert_not_awaited()

    async def test_enabled_background_service_checks_and_applies(self):
        service = UpdateService()
        config = SimpleNamespace(AutoUpdate=True, CheckUpdateInterval=1,
                                 AutoRestartTime=None, read=Mock())
        with patch.object(State, '_deploy_config_', config, create=True), \
                patch.object(service, 'check', new_callable=AsyncMock,
                             return_value={'is_update': True}) as check, \
                patch.object(service, 'execute', new_callable=AsyncMock) as execute:
            service.start()
            await asyncio.sleep(0)
            await service.stop()
        check.assert_awaited_once()
        execute.assert_awaited_once()

    async def test_scheduled_update_waits_until_configured_time(self):
        service = UpdateService()
        config = SimpleNamespace(AutoUpdate=True, CheckUpdateInterval=1,
                                 AutoRestartTime='03:50', read=Mock())
        with patch.object(State, '_deploy_config_', config, create=True), \
                patch('module.server.update_service.datetime') as clock, \
                patch.object(service, 'check', new_callable=AsyncMock,
                             return_value={'is_update': True}), \
                patch.object(service, 'execute', new_callable=AsyncMock) as execute:
            clock.now.return_value.time.return_value = time(3, 49)
            service.start()
            await asyncio.sleep(0)
            await service.stop()
        execute.assert_not_awaited()

    async def test_cancellation_keeps_guard_until_git_finishes(self):
        import module.server.main_manager as manager
        service = UpdateService()
        entered, finish = asyncio.Event(), asyncio.Event()

        async def git(*args):
            entered.set()
            await finish.wait()
            return {'updated': False, 'success': False}

        with patch.object(manager.mm, 'script_process', {}), \
                patch('module.server.update_service.asyncio.to_thread', side_effect=git):
            operation = asyncio.create_task(service.execute())
            await entered.wait()
            operation.cancel()
            await asyncio.sleep(0)
            self.assertFalse(operation.done())
            self.assertTrue(State.project_updating)
            finish.set()
            with self.assertRaises(asyncio.CancelledError):
                await operation
        self.assertFalse(State.project_updating)

    async def test_task_start_refused_during_update(self):
        from module.server.script_process import ScriptProcess
        State.project_updating = True
        task = object.__new__(ScriptProcess)
        with self.assertRaises(RuntimeError):
            await task.start()
