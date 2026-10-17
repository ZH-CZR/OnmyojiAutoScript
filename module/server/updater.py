"""OAS updater adapted from core 00c083e; update this fork using fast-forward only.

Original: xylolit-mu/OnmyojiAutoScript, module/server/updater.py (GPL-3.0).
No installer, stash, reset, remote rewriting or shell command interpolation.
"""
from pathlib import Path
import os
import subprocess

from filelock import FileLock

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'https://gitee.com/oYe486/onmyoji-auto-script.git'
BRANCH = 'master'
REVISION = 'refs/remotes/origin/master'


class UpdateError(RuntimeError):
    pass


class Updater:
    def __init__(self, root=ROOT, git='git'):
        self.root = Path(root).resolve()
        self.git = git

    def command(self, *args, timeout=15):
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
        try:
            result = subprocess.run(
                [self.git, *args], cwd=self.root, env=env, capture_output=True,
                text=True, encoding='utf-8', errors='replace', timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise UpdateError(f'Git 执行失败或超时: {exc}') from exc
        if result.returncode:
            raise UpdateError(result.stderr.strip() or f'Git 返回 {result.returncode}')
        return result.stdout.strip()

    def validate_repository(self):
        top = Path(self.command('rev-parse', '--show-toplevel')).resolve()
        if top != self.root:
            raise UpdateError('更新目录不是仓库根目录')
        # Do not honor legacy Repository/Branch values belonging to OAS or YYS.
        url = self.command('remote', 'get-url', 'origin').rstrip('/').removesuffix('.git')
        if url != REPOSITORY.removesuffix('.git'):
            raise UpdateError('origin 不是本项目的 Gitee 仓库，拒绝更新')
        if self.command('symbolic-ref', '--short', 'HEAD') != BRANCH:
            raise UpdateError('只支持在 master 分支更新')

    def get_commit(self, revision='HEAD', n=1):
        lines = self.command('log', f'-{n}', '--format=%H%x1f%an%x1f%aI%x1f%s', revision)
        commits = [line.split('\x1f', 3) for line in lines.splitlines()]
        return commits[0] if n == 1 else commits

    def version_info(self):
        self.validate_repository()
        return {'branch': BRANCH, 'repository': REPOSITORY,
                'current_commit': self.get_commit()}

    def _info(self, fetch):
        info = self.version_info()
        if fetch:
            self.command('fetch', '--no-tags', 'origin',
                         f'refs/heads/{BRANCH}:{REVISION}', timeout=60)
        ahead, behind = map(int, self.command(
            'rev-list', '--left-right', '--count', f'HEAD...{REVISION}').split())
        dirty = bool(self.command('status', '--porcelain', '--untracked-files=normal'))
        commits = self.get_commit(REVISION, n=15)
        info.update(is_update=bool(behind and not ahead and not dirty),
                    update_available=bool(behind), ahead=ahead, behind=behind,
                    dirty=dirty, latest_commit=commits[0], commit=commits,
                    reason='存在本地修改或未跟踪文件' if dirty else
                           '存在未推送提交或分支已分叉' if ahead else '')
        return info

    def get_update_info(self):
        with FileLock(str(self.root / 'config' / 'project-update.lock'), timeout=0):
            return self._info(fetch=True)

    def execute_pull(self):
        with FileLock(str(self.root / 'config' / 'project-update.lock'), timeout=0):
            info = self._info(fetch=True)
            if not info['is_update']:
                return dict(info, success=False, updated=False)
            # Pin the inspected commit; no second fetch/pull can change the target.
            target = info['latest_commit'][0]
            self.validate_repository()
            if self.command('rev-parse', 'HEAD') != info['current_commit'][0]:
                raise UpdateError('检查后本地提交发生变化，取消更新')
            if self.command('status', '--porcelain', '--untracked-files=normal'):
                raise UpdateError('检查后工作区发生修改，取消更新')
            self.command('-c', 'merge.autostash=false', 'merge', '--ff-only',
                         '--no-overwrite-ignore', target,
                         timeout=60)
            return dict(info, success=True, updated=True,
                        current_commit=self.get_commit(), restart_required=True)
