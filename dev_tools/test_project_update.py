"""Offline tests: only disposable local Git repositories are fetched/merged."""
import asyncio
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

from deploy.project_update import ProjectUpdater, UpdateError, migrate_update_config, PROJECT_REPOSITORY


class ProjectUpdateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote = root / 'remote.git'
        self.writer = root / 'writer'
        self.local = root / 'local'
        self.git = shutil.which('git')
        self.command(root, 'init', '--bare', str(self.remote))
        self.command(root, 'init', '-b', 'master', str(self.writer))
        self.configure(self.writer)
        (self.writer / 'code.txt').write_text('one', encoding='utf-8')
        (self.writer / 'requirements.txt').write_text('', encoding='utf-8')
        self.command(self.writer, 'add', '.')
        self.command(self.writer, 'commit', '-m', 'initial')
        self.command(self.writer, 'remote', 'add', 'origin', str(self.remote))
        self.command(self.writer, 'push', 'origin', 'master')
        self.command(root, 'clone', '-b', 'master', str(self.remote), str(self.local))
        self.configure(self.local)
        self.updater = ProjectUpdater(self.local, self.git, str(self.remote))
        self.original = self.command(self.local, 'rev-parse', 'HEAD')

    def command(self, root, *args):
        return subprocess.run([self.git, *args], cwd=root, check=True, capture_output=True,
                              text=True, encoding='utf-8').stdout.strip()

    def configure(self, root):
        self.command(root, 'config', 'user.email', 'offline@example.invalid')
        self.command(root, 'config', 'user.name', 'Offline Test')
        self.command(root, 'config', 'core.autocrlf', 'false')

    def publish(self, filename='code.txt'):
        (self.writer / filename).write_text('two', encoding='utf-8')
        self.command(self.writer, 'add', filename)
        self.command(self.writer, 'commit', '-m', 'update')
        self.command(self.writer, 'push', 'origin', 'master')

    def assert_preserved(self):
        self.assertEqual(self.original, self.command(self.local, 'rev-parse', 'HEAD'))

    def test_clean_fast_forward_and_no_repeated_pip(self):
        self.assertEqual('up_to_date', self.updater.check()['status'])
        self.publish()
        installer = unittest.mock.Mock()
        result = self.updater.install(installer)
        self.assertEqual('updated', result['status'])
        self.assertTrue(result['restart_required'])
        installer.assert_not_called()
        self.assertEqual('two', (self.local / 'code.txt').read_text())
        self.assertEqual('up_to_date', self.updater.install()['status'])

    def test_ocr_constraint_change_records_pending_dependencies(self):
        self.publish('requirements-ocr.txt')
        self.assertEqual('dependencies_pending', self.updater.install()['status'])
        self.assertTrue(self.updater.dependency_pending())

    def test_modified_staged_deleted_and_untracked_are_preserved(self):
        self.publish()
        for mode in ('modified', 'staged', 'deleted', 'untracked'):
            with self.subTest(mode=mode):
                target = self.local / 'code.txt'
                target.write_text('my changes', encoding='utf-8')
                if mode == 'staged':
                    self.command(self.local, 'add', 'code.txt')
                elif mode == 'deleted':
                    target.unlink()
                elif mode == 'untracked':
                    target.write_text('one', encoding='utf-8')
                    (self.local / 'extra.txt').write_text('keep', encoding='utf-8')
                before = self.command(self.local, 'status', '--porcelain')
                self.assertEqual('local_changes', self.updater.install()['status'])
                self.assert_preserved()
                self.assertEqual(before, self.command(self.local, 'status', '--porcelain'))
                # Only restore disposable fixture files, never the real project.
                self.command(self.local, 'restore', '--staged', 'code.txt')
                self.command(self.local, 'restore', 'code.txt')
                (self.local / 'extra.txt').unlink(missing_ok=True)

    def test_ahead_and_diverged_never_merge(self):
        (self.local / 'private.txt').write_text('local', encoding='utf-8')
        self.command(self.local, 'add', '.')
        self.command(self.local, 'commit', '-m', 'local change')
        self.original = self.command(self.local, 'rev-parse', 'HEAD')
        self.assertEqual('local_commits', self.updater.install()['status'])
        self.publish()
        self.assertEqual('local_commits', self.updater.install()['status'])
        self.assert_preserved()

    def test_ignored_local_file_cannot_be_overwritten_by_a_new_tracked_file(self):
        (self.local / '.git/info/exclude').write_text('private.txt\n', encoding='utf-8')
        (self.local / 'private.txt').write_text('user data', encoding='utf-8')
        self.publish('private.txt')
        self.assertEqual('local_changes', self.updater.install()['status'])
        self.assertEqual('user data', (self.local / 'private.txt').read_text())
        self.assert_preserved()

    def test_wrong_origin_and_branch_never_rewritten(self):
        self.command(self.local, 'remote', 'set-url', 'origin', 'https://example.invalid/repo')
        self.assertEqual('wrong_remote', self.updater.install()['status'])
        self.assertEqual('https://example.invalid/repo', self.command(self.local, 'remote', 'get-url', 'origin'))
        self.command(self.local, 'remote', 'set-url', 'origin', str(self.remote))
        self.command(self.local, 'switch', '-c', 'self')
        self.assertEqual('wrong_branch', self.updater.install()['status'])
        self.assert_preserved()

    def test_fork_repository_and_nested_release_branch_fast_forward(self):
        fork = Path(self.temp.name) / 'fork.git'
        self.command(Path(self.temp.name), 'clone', '--bare', str(self.remote), str(fork))
        self.command(self.writer, 'remote', 'set-url', 'origin', str(fork))
        self.command(self.writer, 'switch', '-c', 'release/stable')
        (self.writer / 'code.txt').write_text('fork release', encoding='utf-8')
        self.command(self.writer, 'add', '.')
        self.command(self.writer, 'commit', '-m', 'fork update')
        self.command(self.writer, 'push', 'origin', 'release/stable')
        self.command(self.local, 'remote', 'set-url', 'origin', str(fork))
        self.command(self.local, 'switch', '-c', 'release/stable')
        updater = ProjectUpdater(self.local, self.git, str(fork), branch='release/stable')
        result = updater.install()
        self.assertEqual('updated', result['status'])
        self.assertEqual('release/stable', result['branch'])
        self.assertEqual(str(fork), result['repository'])
        self.assertEqual('fork release', (self.local / 'code.txt').read_text())
        self.assertEqual('one', self.command(self.local, 'show', 'master:code.txt'))
        self.assertEqual('up_to_date', updater.check()['status'])

    def test_invalid_branch_or_repository_is_rejected_without_fetch(self):
        for branch in ('', '--upload-pack=bad', 'main:other', '../main', 'release/*', 'HEAD', '@{-1}'):
            with self.subTest(branch=branch):
                updater = ProjectUpdater(self.local, self.git, str(self.remote), branch=branch)
                self.assertEqual('wrong_source', updater.install()['status'])
                self.assert_preserved()
        for repository in ('', '--upload-pack=bad', 'ext::echo bad', 'https://[broken/repo', 'https://host/has space'):
            with self.subTest(repository=repository):
                updater = ProjectUpdater(self.local, self.git, repository)
                self.assertEqual('wrong_source', updater.check()['status'])
                self.assert_preserved()

    def test_fork_config_survives_repeated_migration(self):
        config = dict(Repository='git@github.com:someone/fork.git', Branch='release/stable', AutoUpdate=False)
        migrate_update_config(config)
        migrate_update_config(config)
        self.assertEqual('git@github.com:someone/fork.git', config['Repository'])
        self.assertEqual('release/stable', config['Branch'])
        self.assertFalse(config['AutoUpdate'])

    def test_network_failure_never_changes_worktree(self):
        original = self.updater.run
        def fail(*args, **kwargs):
            if args[0] == 'fetch':
                raise UpdateError('git_error', 'offline')
            return original(*args, **kwargs)
        with patch.object(self.updater, 'run', side_effect=fail):
            self.assertEqual('network_error', self.updater.install()['status'])
        self.assert_preserved()

    def test_edits_during_fetch_are_rechecked(self):
        self.publish()
        original = self.updater._check
        def edit():
            info = original()
            (self.local / 'code.txt').write_text('concurrent edit', encoding='utf-8')
            return info
        with patch.object(self.updater, '_check', side_effect=edit):
            self.assertEqual('local_changes', self.updater.install()['status'])
        self.assert_preserved()

    def test_mutual_exclusion(self):
        with self.updater.lock():
            other = ProjectUpdater(self.local, self.git, str(self.remote))
            self.assertEqual('busy', other.install()['status'])
        self.assertEqual('up_to_date', self.updater.check()['status'])

    def test_running_service_blocks_external_installer(self):
        self.publish()
        with self.updater.lock('oas-service-runtime.lock'):
            self.assertEqual('busy', self.updater.install()['status'])
            self.assert_preserved()
            self.assertEqual('available', self.updater.check()['status'])
            self.assertEqual('updated', self.updater.install(service_owned=True)['status'])

    def test_dependencies_pending_survive_failure_and_can_recover(self):
        self.publish('requirements.txt')
        def fail():
            raise RuntimeError('pip unavailable')
        result = self.updater.install(fail)
        self.assertEqual('dependency_error', result['status'])
        self.assertTrue(result['restart_required'])
        self.assertTrue(self.updater.dependency_pending())
        self.updater.complete_dependencies(lambda: None)
        self.assertFalse(self.updater.dependency_pending())

    def test_disabled_dependency_install_is_reported(self):
        self.publish('requirements.txt')
        self.assertEqual('dependencies_pending', self.updater.install()['status'])
        self.assertTrue(self.updater.dependency_pending())

    def test_legacy_config_migration_preserves_preferences(self):
        config = dict(Repository='https://e.coding.net/onmyojiautoscript/oas/OnmyojiAutoScript.git',
                      AutoUpdate=False, AutoRestartTime='03:50', CheckUpdateInterval=5)
        migrate_update_config(config)
        self.assertEqual(PROJECT_REPOSITORY, config['Repository'])
        self.assertFalse(config['AutoUpdate'])
        self.assertTrue(config['AutoCheckUpdate'])
        self.assertEqual('03:50', config['AutoRestartTime'])
        self.assertEqual(5, config['CheckUpdateInterval'])

    def test_startup_installer_obeys_runtime_lock_before_any_mutation(self):
        with patch('deploy.patch.pre_checks'):
            from deploy.installer import Installer
        installer = SimpleNamespace(project_updater=lambda: self.updater,
                                    git_install=unittest.mock.Mock(), process_kill=unittest.mock.Mock())
        with self.updater.lock('oas-service-runtime.lock'):
            with self.assertRaises(SystemExit) as stopped:
                Installer.install(installer)
        self.assertEqual(1, stopped.exception.code)
        installer.git_install.assert_not_called()
        installer.process_kill.assert_not_called()


class UpdateAdapterTest(unittest.TestCase):
    def test_both_entry_points_forward_fork_source_and_preserve_configuration(self):
        from deploy.git import GitManager
        from module.server.updater import Updater
        for adapter, target in ((GitManager, 'deploy.git.ProjectUpdater'),
                                (Updater, 'module.server.updater.ProjectUpdater')):
            with self.subTest(adapter=adapter.__name__), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / 'deploy.yaml'
                config.write_text('Repository: https://github.com/someone/fork.git\n'
                                  'Branch: release/stable\nAutoUpdate: true\nInstallDependencies: false\n',
                                  encoding='utf-8')
                project = unittest.mock.Mock()
                project.check.return_value = dict(status='available', target='fork-sha', is_update=True)
                project.run.return_value = 'fork-sha---author---date---fork update'
                project.install.return_value = dict(status='up_to_date', message='done')
                with patch(target, return_value=project) as factory:
                    updater = adapter(str(config))
                    if adapter is GitManager:
                        updater.git_install()
                    else:
                        info = updater.get_update_info()
                        self.assertEqual('release/stable', info['branch'])
                        self.assertEqual('https://github.com/someone/fork.git', info['repository'])
                        project.run.assert_any_call('--no-pager', 'log', 'fork-sha',
                                                    '--pretty=format:%H---%an---%ad---%s', '--date=iso', '-15')
                        updater.execute_pull()
                    self.assertEqual('https://github.com/someone/fork.git', factory.call_args.kwargs['repository'])
                    self.assertEqual('release/stable', factory.call_args.kwargs['branch'])
                    self.assertIn('Branch: release/stable', config.read_text(encoding='utf-8'))
                    self.assertIn('Repository: https://github.com/someone/fork.git', config.read_text(encoding='utf-8'))
                    project.install.assert_called_once_with(None, service_owned=False)

    def test_failed_fetch_does_not_display_previous_source_history(self):
        from module.server.updater import Updater
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'deploy.yaml'
            config.write_text('Repository: https://github.com/someone/fork.git\nBranch: main\n', encoding='utf-8')
            project = unittest.mock.Mock()
            project.check.return_value = dict(status='network_error', message='offline', is_update=False)
            project.run.return_value = 'abc---author---date---local commit'
            with patch('module.server.updater.ProjectUpdater', return_value=project):
                info = Updater(str(config)).get_update_info()
            self.assertIsNone(info['latest_commit'])
            self.assertEqual([], info['commit'])
            self.assertEqual('main', info['branch'])
            self.assertEqual(1, project.run.call_count)

    def test_manual_check_and_install_are_independent_of_auto_install(self):
        from module.server.updater import Updater
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'deploy.yaml'
            config.write_text('Repository: https://e.coding.net/onmyojiautoscript/oas/OnmyojiAutoScript.git\n'
                              'AutoUpdate: false\nInstallDependencies: false\n', encoding='utf-8')
            project = unittest.mock.Mock()
            project.check.return_value = dict(status='available', is_update=True, restart_required=False)
            project.run.return_value = 'abc---author---date---message'
            project.install.return_value = dict(status='updated', restart_required=True)
            with patch('module.server.updater.ProjectUpdater', return_value=project):
                updater = Updater(str(config))
                self.assertFalse(updater.AutoUpdate)
                self.assertTrue(updater.get_update_info()['is_update'])
                self.assertEqual('updated', updater.execute_pull()['status'])
                project.install.assert_called_once_with(None, service_owned=False)
                self.assertEqual(PROJECT_REPOSITORY, updater.Repository)
                self.assertIn('AutoUpdate: false', config.read_text(encoding='utf-8'))

    def test_restart_controller_exits_the_http_server_when_requested(self):
        import server
        event = __import__('threading').Event()
        web = unittest.mock.Mock()
        web.should_exit = False
        def run():
            event.set()
            import time
            deadline = time.monotonic() + 2
            while not web.should_exit and time.monotonic() < deadline:
                __import__('threading').Event().wait(0.005)
        web.run.side_effect = run
        settings = SimpleNamespace(WebuiHost='127.0.0.1', WebuiPort=22267)
        with patch('sys.argv', ['server.py']), \
                patch.object(server, 'State', SimpleNamespace(deploy_config=settings)), \
                patch.object(server, 'ensure_image_server_ready'), \
                patch.object(server, 'ensure_ocr_server_ready'), \
                patch.object(server, 'shutdown_image_server') as image_stop, \
                patch.object(server, 'shutdown_ocr_server') as ocr_stop, \
                patch('uvicorn.Server', return_value=web):
            server.fun(event)
        self.assertTrue(web.should_exit)
        image_stop.assert_called_once()
        ocr_stop.assert_called_once()

    def test_update_api_returns_structured_failures_and_live_status(self):
        import importlib.util
        from fastapi import FastAPI
        path = Path(__file__).resolve().parents[1] / 'module/server/home_router.py'
        spec = importlib.util.spec_from_file_location('_update_api_test_router', path)
        router = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {
                'module.server.main_manager': SimpleNamespace(MainManager=object)}):
            spec.loader.exec_module(router)
        failed = dict(status='dependencies_pending', message='依赖未就绪', restart_required=True)
        coordinator = SimpleNamespace(check=AsyncMock(return_value=dict(status='available', is_update=True)),
                                      install=AsyncMock(return_value=failed), last_result=failed,
                                      installing=False, restart_required=True, dependencies_pending=True)
        app = FastAPI()
        app.include_router(router.home_app)
        async def request(method, path):
            sent = []
            scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1',
                         method=method, scheme='http', path=path, raw_path=path.encode(),
                         query_string=b'', root_path='', headers=[],
                         server=('localhost', 80), client=('localhost', 1234))
            async def receive():
                return dict(type='http.request', body=b'', more_body=False)
            async def send(message):
                sent.append(message)
            await app(scope, receive, send)
            self.assertEqual(200, sent[0]['status'])
            return json.loads(b''.join(m.get('body', b'') for m in sent))
        with patch.object(router, 'update_service', coordinator):
            self.assertTrue(asyncio.run(request('GET', '/home/update_info'))['is_update'])
            for method in ('GET', 'POST'):
                self.assertEqual(failed, asyncio.run(request(method, '/home/execute_update')))
            self.assertTrue(asyncio.run(request('GET', '/home/update_status'))['dependencies_pending'])


class UpdateServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from module.server.update_service import UpdateService
        self.service = UpdateService()

    def updater(self):
        return SimpleNamespace(AutoUpdate=False, InstallDependencies=False, EnableReload=False,
                               schedule_time=None, get_update_info=lambda: dict(status='available', changes=[]),
                               execute_pull=lambda **kwargs: dict(status='updated', message='done', restart_required=True))

    async def test_manual_install_works_with_auto_install_disabled_and_requires_restart(self):
        with patch('module.server.update_service.Updater', return_value=self.updater()), \
                patch.object(self.service, 'active_processes', return_value=[]):
            result = await self.service.install()
        self.assertEqual('updated', result['status'])
        self.assertIsNotNone(self.service.start_error())

    async def test_automatic_install_defers_running_tasks(self):
        updater = self.updater()
        updater.AutoUpdate, updater.schedule_time = True, '03:50'
        updater.execute_pull = unittest.mock.Mock()
        with patch('module.server.update_service.Updater', return_value=updater), \
                patch.object(self.service, 'active_processes', return_value=[object()]):
            self.assertEqual('deferred', (await self.service.install(True))['status'])
        updater.execute_pull.assert_not_called()
        self.assertFalse(self.service.installing)

    async def test_failed_preflight_does_not_stop_running_tasks(self):
        updater = self.updater()
        updater.get_update_info = lambda: dict(status='local_changes', message='keep')
        script = SimpleNamespace(stop=AsyncMock())
        with patch('module.server.update_service.Updater', return_value=updater), \
                patch.object(self.service, 'active_processes', return_value=[script]):
            self.assertEqual('local_changes', (await self.service.install())['status'])
        script.stop.assert_not_awaited()

    async def test_manual_install_waits_for_process_exit(self):
        process = unittest.mock.Mock()
        process.is_alive.return_value = False
        script = SimpleNamespace(_process=process, stop=AsyncMock())
        with patch('module.server.update_service.Updater', return_value=self.updater()), \
                patch.object(self.service, 'active_processes', return_value=[script]):
            self.assertEqual('updated', (await self.service.install())['status'])
        script.stop.assert_awaited_once()
        process.join.assert_called_once_with(10)

    async def test_background_checks_independent_and_network_backoff(self):
        updater = self.updater()
        updater.AutoCheckUpdate, updater.delay = True, 3600
        now = datetime.datetime(2026, 10, 17, 4, 0)
        self.service.check = AsyncMock(return_value=dict(status='network_error', message='offline'))
        with patch('module.server.update_service.Updater', return_value=updater):
            await self.service.tick(now, 1)
            self.assertEqual(7201, self.service.next_check)
            await self.service.tick(now, 3601)
            self.service.check.assert_awaited_once()
            await self.service.tick(now, 7201)
            self.assertEqual(21601, self.service.next_check)

    async def test_schedule_waits_for_time_and_retries_when_idle(self):
        updater = self.updater()
        updater.AutoCheckUpdate, updater.delay = False, 3600
        updater.AutoUpdate, updater.schedule_time = True, datetime.time(3, 50)
        self.service.install = AsyncMock(side_effect=[dict(status='deferred'), dict(status='up_to_date')])
        with patch('module.server.update_service.Updater', return_value=updater):
            await self.service.tick(datetime.datetime(2026, 10, 17, 3, 49), 1)
            self.service.install.assert_not_awaited()
            await self.service.tick(datetime.datetime(2026, 10, 17, 3, 50), 61)
            self.assertIsNone(self.service.last_install_date)
            await self.service.tick(datetime.datetime(2026, 10, 17, 3, 51), 121)
            self.assertEqual(datetime.date(2026, 10, 17), self.service.last_install_date)
            await self.service.tick(datetime.datetime(2026, 10, 17, 4), 181)
            self.assertEqual(2, self.service.install.await_count)

    async def test_pending_dependencies_block_task_start(self):
        self.service.dependencies_pending = True
        self.assertIn('依赖', self.service.start_error())
        self.assertEqual('restart_required', (await self.service.install())['status'])

    async def test_install_gates_task_start_during_git_operation(self):
        updater = self.updater()
        def install(**kwargs):
            self.assertIn('正在安装', self.service.start_error())
            return dict(status='up_to_date', restart_required=False)
        updater.execute_pull = install
        with patch('module.server.update_service.Updater', return_value=updater), \
                patch.object(self.service, 'active_processes', return_value=[]):
            await self.service.install()
        self.assertIsNone(self.service.start_error())


if __name__ == '__main__':
    unittest.main()
