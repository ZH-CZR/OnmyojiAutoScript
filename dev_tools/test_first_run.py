"""First-install state and archive startup checks, without network or game input."""
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from deploy import first_run
from deploy.utils import poor_yaml_read
from module.server.update_service import UpdateService


class FirstRunTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'deploy').mkdir()
        (self.root / 'deploy' / 'template').write_bytes((first_run.ROOT / 'deploy' / 'template').read_bytes())
        for name in first_run.REQUIREMENTS:
            (self.root / name).write_text(name, encoding='utf-8')
        self.patch = patch.object(first_run, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_config_defaults_are_local_and_explicit_fields_survive(self):
        first_run.configure(self.root / 'Git' / 'cmd' / 'git.exe')
        config = self.root / 'config' / 'deploy.yaml'
        values = poor_yaml_read(str(config))
        self.assertEqual('127.0.0.1', values['WebuiHost'])
        self.assertFalse(values['ReplaceAdb'])
        self.assertTrue(values['AutoUpdate'])
        self.assertTrue(Path(values['AdbExecutable']).is_file())
        text = config.read_text(encoding='utf-8').replace('WebuiPort: 22267', 'WebuiPort: 29999')
        text = text.replace('https://gitee.com/oYe486/onmyoji-auto-script.git', 'https://example.invalid/fork.git')
        config.write_text(text, encoding='utf-8')
        before = config.read_bytes()
        first_run.configure(self.root / 'other-git.exe')
        self.assertEqual(before, config.read_bytes())

    def test_failed_pip_does_not_mark_installation_complete(self):
        with patch.object(first_run, 'run', side_effect=subprocess.CalledProcessError(1, 'pip')):
            with self.assertRaises(subprocess.CalledProcessError):
                first_run.install_dependencies('https://example.invalid/simple')
        self.assertFalse((self.root / 'toolkit' / 'first-run-dependencies.json').exists())

    def test_new_bundled_paths_are_relative_and_external_paths_survive(self):
        bundled_python = self.root / '.venv' / 'Scripts' / 'python.exe'
        git = self.root / 'toolkit' / 'Git' / 'cmd' / 'git.exe'
        with patch.object(first_run.sys, 'executable', str(bundled_python)):
            first_run.configure(git)
        config = self.root / 'config' / 'deploy.yaml'
        values = poor_yaml_read(str(config))
        self.assertEqual('.venv/Scripts/python.exe', values['PythonExecutable'])
        self.assertEqual('toolkit/Git/cmd/git.exe', values['GitExecutable'])
        before = config.read_bytes()
        first_run.configure('D:/external/git.exe')
        self.assertEqual(before, config.read_bytes())

    def recovery_fixture(self):
        from deploy.project_update import ProjectUpdater
        git = shutil.which('git')
        subprocess.run([git, 'init', '-b', 'master', str(self.root)], check=True, capture_output=True)
        config = self.root / 'config' / 'deploy.yaml'
        config.parent.mkdir(exist_ok=True)
        config.write_text(f'GitExecutable: {Path(git).as_posix()}\nInstallDependencies: true\n', encoding='utf-8')
        project = ProjectUpdater(self.root, git)
        project.mark_dependencies(True)
        return project, config

    def test_dependency_recovery_works_before_third_party_imports(self):
        project, _ = self.recovery_fixture()
        with patch.object(first_run, 'install_dependencies') as install:
            self.assertTrue(first_run.recover_before_imports())
            self.assertFalse(project.dependency_pending())
            self.assertFalse(first_run.recover_before_imports())
        install.assert_called_once_with(first_run.DEFAULT_PYPI_MIRROR)

    def test_recovery_failure_or_disabled_install_keeps_pending_state(self):
        project, config = self.recovery_fixture()
        with patch.object(first_run, 'install_dependencies', side_effect=RuntimeError('offline')):
            with self.assertRaisesRegex(RuntimeError, 'offline'):
                first_run.recover_before_imports()
        self.assertTrue(project.dependency_pending())
        config.write_text(config.read_text().replace('true', 'false'), encoding='utf-8')
        with patch.object(first_run, 'install_dependencies') as install:
            with self.assertRaisesRegex(RuntimeError, 'InstallOnly'):
                first_run.recover_before_imports()
        install.assert_not_called()
        self.assertTrue(project.dependency_pending())

    def test_running_backend_blocks_early_dependency_recovery(self):
        project, _ = self.recovery_fixture()
        with project.lock('oas-service-runtime.lock'), patch.object(first_run, 'install_dependencies') as install:
            with self.assertRaisesRegex(RuntimeError, 'backend is running'):
                first_run.recover_before_imports()
        install.assert_not_called()

    def test_recovery_bootstrap_runs_with_site_packages_disabled(self):
        project, _ = self.recovery_fixture()
        script = '''from pathlib import Path
import sys
from deploy import first_run
first_run.ROOT = Path(sys.argv[1])
first_run.install_dependencies = lambda index: None
assert first_run.recover_before_imports()
assert 'module.logger' not in sys.modules
assert 'yaml' not in sys.modules
assert 'filelock' not in sys.modules
'''
        result = subprocess.run([__import__('sys').executable, '-S', '-c', script, str(self.root)],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr.decode(errors='replace'))
        self.assertFalse(project.dependency_pending())

    def test_pypi_prefers_tuna_and_preserves_an_explicit_existing_source(self):
        self.assertEqual(first_run.DEFAULT_PYPI_MIRROR, first_run.select_pypi_mirror())
        first_run.configure(self.root / 'git.exe', 'https://example.invalid/simple')
        self.assertEqual('https://example.invalid/simple', first_run.select_pypi_mirror())
        self.assertEqual('https://pypi.org/simple', first_run.select_pypi_mirror('https://pypi.org/simple'))
        with patch.object(first_run, 'run') as run:
            first_run.install_dependencies(first_run.DEFAULT_PYPI_MIRROR)
        command = run.call_args_list[0].args
        self.assertEqual(first_run.DEFAULT_PYPI_MIRROR, command[command.index('--index-url') + 1])
        self.assertIn('--timeout', command)
        self.assertIn('--retries', command)

    def test_installer_and_zip_service_share_the_runtime_lock(self):
        from filelock import FileLock, Timeout
        with first_run.runtime_lock('unused-git'):
            with self.assertRaises(Timeout):
                with FileLock(str(self.root / 'config' / 'oas-service-runtime.lock'), timeout=0):
                    pass
        with FileLock(str(self.root / 'config' / 'oas-service-runtime.lock'), timeout=0):
            with self.assertRaises(RuntimeError):
                with first_run.runtime_lock('unused-git'):
                    pass

    def test_frontend_installer_accepts_zip_and_empty_git_without_local_logger_error(self):
        with patch('deploy.patch.pre_checks'):
            from deploy.installer import Installer
        from deploy.project_update import ProjectUpdater
        for empty_git in (False, True):
            with self.subTest(empty_git=empty_git):
                git = shutil.which('git')
                if empty_git:
                    subprocess.run([git, 'init', str(self.root)], check=True, capture_output=True)
                updater = ProjectUpdater(self.root, git)
                installer = SimpleNamespace(project_updater=lambda: updater, InstallDependencies=True,
                                            pip_install=Mock(), adb_install=Mock())
                with patch('deploy.installer.logger') as logger:
                    Installer.install(installer)
                logger.info.assert_called_once()
                installer.pip_install.assert_called_once()
                installer.adb_install.assert_called_once()

    def test_web_dependency_install_uses_both_constraints(self):
        from module.server.updater import Updater
        settings = SimpleNamespace(root_filepath=str(self.root), PypiMirror=None)
        with patch('module.server.updater.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            Updater.install_dependencies(settings)
        command = run.call_args_list[0].args[0]
        self.assertIn(str(self.root / 'requirements.txt'), command)
        self.assertIn(str(self.root / 'requirements-ocr.txt'), command)
        for call in run.call_args_list:
            self.assertEqual(getattr(subprocess, 'CREATE_NO_WINDOW', 0), call.kwargs['creationflags'])

    def test_partial_configuration_retains_custom_sections(self):
        config = self.root / 'config' / 'deploy.yaml'
        config.parent.mkdir()
        config.write_text('Deploy:\n  Webui:\n    WebuiPort: 28888\nCustom:\n  example: retained\n', encoding='utf-8')
        first_run.configure(self.root / 'git.exe')
        import yaml
        tree = yaml.safe_load(config.read_text(encoding='utf-8'))
        self.assertEqual('retained', tree['Custom']['example'])
        self.assertEqual(28888, tree['Deploy']['Webui']['WebuiPort'])

    def test_constraints_are_installed_together_and_changes_invalidate_marker(self):
        with patch.object(first_run, 'run') as run:
            first_run.install_dependencies('')
        command = run.call_args_list[0].args
        self.assertIn('requirements.txt', command)
        self.assertIn('requirements-ocr.txt', command)
        with patch.object(first_run.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
                patch.object(first_run, 'run') as run:
            first_run.install_dependencies('')
        self.assertEqual(1, run.call_count)  # import smoke check only
        (self.root / 'requirements-ocr.txt').write_text('changed', encoding='utf-8')
        with patch.object(first_run, 'run') as run:
            first_run.install_dependencies('')
        self.assertEqual('pip', run.call_args_list[0].args[1])


class ArchiveStartupTest(unittest.IsolatedAsyncioTestCase):
    async def test_zip_can_start_tasks_without_git_and_reports_update_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            updater = SimpleNamespace(root_filepath=folder, project=Mock(), InstallDependencies=True, AutoUpdate=False, AutoCheckUpdate=False)
            service = UpdateService()
            with patch('module.server.update_service.Updater', return_value=updater):
                await service.start()
                try:
                    self.assertIsNone(service.start_error())
                    self.assertTrue(service.source_archive)
                    updater.project.lock.assert_not_called()
                    updater.project.dependency_pending.assert_not_called()
                    self.assertEqual('source_archive', (await service.check())['status'])
                    self.assertEqual('source_archive', (await service.install())['status'])
                finally:
                    await service.stop()
                    service.release_runtime()

    async def test_zip_second_server_is_blocked_by_runtime_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            updater = SimpleNamespace(root_filepath=folder, project=Mock(), InstallDependencies=True, AutoUpdate=False, AutoCheckUpdate=False)
            first, second = UpdateService(), UpdateService()
            with patch('module.server.update_service.Updater', return_value=updater):
                await first.start()
                try:
                    await second.start()
                    self.assertIsNotNone(second.start_error())
                finally:
                    await first.stop()
                    await second.stop()
                    first.release_runtime()
                    second.release_runtime()


class FrontendStartupTest(unittest.IsolatedAsyncioTestCase):
    async def test_empty_git_backend_finishes_startup_and_answers_frontend_probe(self):
        from deploy.project_update import ProjectUpdater
        import module.server.app as web
        with tempfile.TemporaryDirectory() as folder:
            git = shutil.which('git')
            subprocess.run([git, 'init', folder], check=True, capture_output=True)
            updater = SimpleNamespace(root_filepath=folder, project=ProjectUpdater(folder, git),
                                      InstallDependencies=True, AutoUpdate=False, AutoCheckUpdate=False)
            service = UpdateService()
            with patch('module.server.update_service.Updater', return_value=updater), \
                    patch.object(web, 'update_service', service), \
                    patch.object(web, 'ensure_api_logger'), \
                    patch.object(web.app.state, 'script_instances', None, create=True):
                async with web.lifespan(web.app):
                    self.assertIsNone(service.start_error())
                    messages = []

                    async def receive():
                        return {'type': 'http.request', 'body': b'', 'more_body': False}

                    async def send(message):
                        messages.append(message)

                    await web.app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                                   'method': 'GET', 'scheme': 'http', 'path': '/test', 'raw_path': b'/test',
                                   'query_string': b'', 'headers': [], 'root_path': '',
                                   'client': ('127.0.0.1', 12345), 'server': ('127.0.0.1', 22267)}, receive, send)
                    self.assertEqual(200, messages[0]['status'])
                    self.assertEqual('success', json.loads(b''.join(
                        message.get('body', b'') for message in messages)))
                self.assertIsNone(service.runtime_lease)


class OnnxModelFilesTest(unittest.TestCase):
    def test_official_onnx_package_needs_no_paddle_static_graph_json(self):
        from module.ocr.rpc import _BUNDLED_MODEL_DIRS, _bundled_ocr_model_issues
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in _BUNDLED_MODEL_DIRS:
                model = root / name
                model.mkdir()
                with (model / 'inference.onnx').open('wb') as handle:
                    handle.truncate(1024 * 1024)
                (model / 'inference.yml').write_text('model_name: test\n#' + 'x' * 150, encoding='utf-8')
            self.assertEqual([], _bundled_ocr_model_issues(root))
            (root / _BUNDLED_MODEL_DIRS[0] / 'inference.yml').write_text('[' + 'x' * 150, encoding='utf-8')
            self.assertTrue(any(issue.startswith('invalid-yaml:') for issue in _bundled_ocr_model_issues(root)))


@unittest.skipUnless(shutil.which('powershell.exe'), 'Windows PowerShell required')
class DownloadFailoverTest(unittest.TestCase):
    def test_ucrt_git_gets_a_real_legacy_path_without_copying_or_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copyfile(first_run.ROOT / 'deploy' / 'git_layout.ps1', root / 'git_layout.ps1')
            script = root / 'test.ps1'
            script.write_text('''$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'git_layout.ps1')
$git = Join-Path $PSScriptRoot 'Git'
New-Item -ItemType Directory -Path (Join-Path $git 'ucrt64/bin') -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $git 'ucrt64/bin/git.exe'), 'fixture')
Initialize-GitLayout $git
Initialize-GitLayout $git
$alias = Get-Item -LiteralPath (Join-Path $git 'mingw64')
if ($alias.LinkType -ne 'Junction') { throw 'Compatibility entry must be a junction' }
[IO.File]::WriteAllText((Join-Path $git 'ucrt64/bin/git.exe'), 'updated')
if ([IO.File]::ReadAllText((Join-Path $git 'mingw64/bin/git.exe')) -ne 'updated') { throw 'Git was copied instead of linked' }
$old = Join-Path $PSScriptRoot 'OldGit'
New-Item -ItemType Directory -Path (Join-Path $old 'mingw64/bin') -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $old 'mingw64/bin/git.exe'), 'old')
Initialize-GitLayout $old
if ((Get-Item (Join-Path $old 'mingw64')).LinkType) { throw 'Existing old layout was changed' }
$broken = Join-Path $PSScriptRoot 'BrokenGit'
New-Item -ItemType Directory -Path (Join-Path $broken 'ucrt64/bin') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $broken 'mingw64') -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $broken 'ucrt64/bin/git.exe'), 'fixture')
$failed = $false
try { Initialize-GitLayout $broken } catch { $failed = $true }
if (-not $failed) { throw 'Existing directory was silently replaced' }
''', encoding='utf-8')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                                    capture_output=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr.decode(errors='replace'))

    def test_mirrors_reject_wrong_hash_fall_back_and_reuse_verified_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copyfile(first_run.ROOT / 'deploy' / 'download.ps1', root / 'download.ps1')
            entry = dict(filename='runtime.zip', mirrors=['bad-mirror', 'good-mirror'], url='official',
                         sha256=hashlib.sha256(b'valid archive').hexdigest())
            (root / 'entry.json').write_text(json.dumps(entry), encoding='utf-8')
            script = root / 'test.ps1'
            script.write_text('''$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'download.ps1')
$calls = [Collections.Generic.List[string]]::new()
function Receive-Download([string]$url, [string]$destination) {
    $calls.Add($url)
    $content = if ($url -eq 'good-mirror') { 'valid archive' } else { 'corrupt' }
    [IO.File]::WriteAllText($destination, $content, [Text.Encoding]::ASCII)
}
$entry = Get-Content -Raw (Join-Path $PSScriptRoot 'entry.json') | ConvertFrom-Json
$first = Get-VerifiedDownload $entry $PSScriptRoot
$second = Get-VerifiedDownload $entry $PSScriptRoot
if ($first -ne $second) { throw 'Cache not reused' }
ConvertTo-Json -InputObject @($calls.ToArray()) | Set-Content (Join-Path $PSScriptRoot 'calls.json')
$entry.filename = 'never-installed.zip'
$entry.mirrors = @('bad-mirror')
$failed = $false
try { Get-VerifiedDownload $entry $PSScriptRoot } catch { $failed = $true }
if (-not $failed -or (Test-Path (Join-Path $PSScriptRoot 'never-installed.zip'))) { throw 'Invalid download accepted' }
''', encoding='utf-8')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                                    capture_output=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr.decode(errors='replace'))
            self.assertEqual(['bad-mirror', 'bad-mirror', 'good-mirror'],
                             json.loads((root / 'calls.json').read_text(encoding='utf-8-sig')))


if __name__ == '__main__':
    unittest.main()
