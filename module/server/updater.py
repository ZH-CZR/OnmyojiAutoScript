"""Web adapter for the shared project updater.

Original updater by runhey: https://github.com/runhey
"""
import datetime
import subprocess
import sys
from pathlib import Path

from deploy.project_update import ProjectUpdater, UpdateError
from deploy.utils import DEPLOY_CONFIG
from module.server.config import DeployConfig


class Updater(DeployConfig):
    def __init__(self, file=DEPLOY_CONFIG):
        super().__init__(file=file)
        self.project = ProjectUpdater(self.root_filepath, self.filepath('GitExecutable'),
                                      repository=self.Repository, branch=self.Branch,
                                      git_proxy=self.GitProxy, ssl_verify=self.SSLVerify)

    @property
    def delay(self):
        self.read()
        return max(0, int(self.CheckUpdateInterval)) * 60

    @property
    def schedule_time(self):
        self.read()
        return datetime.time.fromisoformat(str(self.AutoRestartTime)) if self.AutoRestartTime else None

    def configuration_error(self):
        try:
            self.project.validate_source()
        except UpdateError as exc:
            return self.project.error(exc)
        return None

    def get_commit(self, revision='HEAD', n=1, short_sha1=False):
        try:
            fmt = '%h' if short_sha1 else '%H'
            output = self.project.run('--no-pager', 'log', revision,
                                      f'--pretty=format:{fmt}---%an---%ad---%s', '--date=iso', f'-{n}')
            commits = [tuple(line.split('---', 3)) for line in output.splitlines()]
            return commits[0] if n == 1 and commits else commits
        except Exception:
            return (None, None, None, None) if n == 1 else []

    def get_update_info(self):
        info = self.configuration_error() or self.project.check()
        if info['status'] == 'available':
            try:
                self.project.validate(clean=True)
            except UpdateError as exc:
                info.update(status=exc.status, message=exc.message)
        # Only show history from a successful fetch, not stale refs from the previous source.
        commits = self.get_commit(info['target'], n=15) if info.get('target') else []
        info.update(branch=self.Branch, repository=self.Repository, current_commit=self.get_commit(),
                    latest_commit=commits[0] if commits else None, commit=commits)
        return info

    def install_dependencies(self):
        # Use this service's interpreter, never another project's configured Python.
        requirements = Path(self.root_filepath) / 'requirements.txt'
        constraint_args = ['-r', str(requirements)]
        ocr = Path(self.root_filepath) / 'requirements-ocr.txt'
        if ocr.is_file():
            constraint_args.extend(['-r', str(ocr)])
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', *constraint_args,
                                 '--disable-pip-version-check', '--no-input',
                                 *(['-i', self.PypiMirror] if self.PypiMirror else [])],
                                cwd=self.root_filepath, timeout=600)
        if result.returncode:
            raise RuntimeError('pip install 失败，请检查服务日志')
        result = subprocess.run([sys.executable, '-m', 'pip', 'check'], cwd=self.root_filepath, timeout=60)
        if result.returncode:
            raise RuntimeError('pip check 失败，请检查服务日志')

    def execute_pull(self, *, service_owned=False):
        return self.configuration_error() or self.project.install(
            self.install_dependencies if self.InstallDependencies else None,
            service_owned=service_owned)
