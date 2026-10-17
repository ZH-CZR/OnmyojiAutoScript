"""Safe project updates. Never stash, reset, switch branches or rewrite remotes."""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import re
from urllib.parse import urlsplit

PROJECT_REPOSITORY = 'https://gitee.com/oYe486/onmyoji-auto-script.git'
PROJECT_BRANCH = 'master'
LEGACY_REPOSITORIES = {
    'https://e.coding.net/onmyojiautoscript/oas/OnmyojiAutoScript.git',
    'https://gitcode.com/OnmyojiAutoScript/OnmyojiAutoScript.git',
    'https://github.com/xylolit-mu/OnmyojiAutoScript.git',
}


def migrate_update_config(config):
    if config.get('Repository') in LEGACY_REPOSITORIES:
        config['Repository'] = PROJECT_REPOSITORY
    config.setdefault('AutoCheckUpdate', True)


class UpdateError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class ProjectUpdater:
    def __init__(self, root=None, git='git', repository=PROJECT_REPOSITORY,
                 git_proxy=None, ssl_verify=True, branch=PROJECT_BRANCH):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.git = str(git)
        self.repository = repository
        self.branch = branch
        self.git_options = ['-c', f'http.sslVerify={str(bool(ssl_verify)).lower()}']
        if git_proxy:
            self.git_options.extend(['-c', f'http.proxy={git_proxy}', '-c', f'https.proxy={git_proxy}'])

    def run(self, *args, timeout=20):
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
        try:
            result = subprocess.run([self.git, *self.git_options, *args], cwd=self.root, env=env,
                                    capture_output=True, text=True, encoding='utf-8',
                                    errors='replace', timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise UpdateError('git_error', f'Git 执行失败或超时：{exc}') from exc
        if result.returncode:
            raise UpdateError('git_error', result.stderr.strip() or 'Git 执行失败')
        return result.stdout.strip()

    @property
    def git_dir(self):
        return Path(self.run('rev-parse', '--absolute-git-dir'))

    @property
    def state_file(self):
        return self.git_dir / 'oas-update-state.json'

    def dependency_pending(self):
        path = self.state_file
        return path.exists() and json.loads(path.read_text(encoding='utf-8')).get('dependencies_pending', False)

    def mark_dependencies(self, pending):
        path = self.state_file
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'dependencies_pending': pending}), encoding='utf-8')
        temporary.replace(path)

    @contextlib.contextmanager
    def lock(self, name='oas-project-update.lock'):
        # A process-wide OS lock: crashes release it without deleting Git's locks.
        common = Path(self.run('rev-parse', '--git-common-dir'))
        if not common.is_absolute():
            common = self.root / common
        with (common / name).open('a+b') as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise UpdateError('busy', '另一个更新操作正在进行') from exc
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def validate(self, clean=False):
        self.validate_source()
        top = Path(self.run('rev-parse', '--show-toplevel')).resolve()
        if top != self.root:
            raise UpdateError('wrong_repository', '更新目录必须是项目仓库根目录')
        urls = self.run('remote', 'get-url', '--all', 'origin').splitlines()
        if urls != [self.repository]:
            raise UpdateError('wrong_remote', 'origin 与配置的更新来源不一致，请维护者检查；未修改远端')
        if clean and self.run('symbolic-ref', '--quiet', '--short', 'HEAD') != self.branch:
            raise UpdateError('wrong_branch', f'仅允许在配置的 {self.branch} 分支安装更新')
        for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'):
            if (self.git_dir / name).exists():
                raise UpdateError('operation_in_progress', 'Git 合并或变基尚未结束')
        changes = self.run('-c', 'core.quotePath=false', 'status', '--porcelain', '--untracked-files=all')
        if clean and changes:
            raise UpdateError('local_changes', '存在未提交或未跟踪文件，已停止安装：\n' + changes)
        return changes

    def validate_source(self):
        repository = self.repository
        if (not isinstance(repository, str) or not repository or repository.startswith('-')
                or any(ord(c) < 32 for c in repository)):
            raise UpdateError('wrong_source', 'Repository 必须是有效的仓库地址或本地仓库路径')
        try:
            parsed = urlsplit(repository) if '://' in repository else None
        except ValueError as exc:
            raise UpdateError('wrong_source', 'Repository 地址格式无效') from exc
        local = Path(repository)
        if not local.is_absolute():
            local = self.root / local
        ssh = re.fullmatch(r'[^\s:@]+@[^\s:/]+:[^\s:]+', repository)
        if parsed is not None:
            valid = not any(c.isspace() for c in repository) and (
                (parsed.scheme in ('https', 'http', 'ssh', 'git') and bool(parsed.hostname)
                 and bool(parsed.path.strip('/'))) or (parsed.scheme == 'file' and bool(parsed.path)))
        else:
            valid = bool(ssh) or local.is_dir()
        if not valid:
            raise UpdateError('wrong_source', 'Repository 仅支持 HTTP(S)、SSH、Git、file 地址或本地仓库路径')
        if not isinstance(self.branch, str) or not self.branch or self.branch.startswith('-'):
            raise UpdateError('wrong_source', 'Branch 必须是有效的分支名称')
        try:
            resolved = self.run('check-ref-format', '--branch', self.branch)
        except UpdateError as exc:
            raise UpdateError('wrong_source', 'Branch 不是有效的分支名称') from exc
        if resolved != self.branch:
            raise UpdateError('wrong_source', 'Branch 必须使用明确的分支名称')

    @property
    def remote_revision(self):
        return f'refs/remotes/origin/{self.branch}'

    def _check(self):
        changes = self.validate()
        try:
            self.run('fetch', '--no-tags', '--', self.repository,
                     f'+refs/heads/{self.branch}:{self.remote_revision}', timeout=45)
        except UpdateError as exc:
            raise UpdateError('network_error', '获取更新失败：' + exc.message) from exc
        current = self.run('rev-parse', 'HEAD')
        target = self.run('rev-parse', self.remote_revision)
        ahead, behind = map(int, self.run('rev-list', '--left-right', '--count', f'{current}...{target}').split())
        status = 'local_commits' if ahead else ('available' if behind else 'up_to_date')
        message = {'local_commits': '本地存在额外提交或历史分叉，已停止安装',
                   'available': '发现新版本', 'up_to_date': '当前已是最新版本'}[status]
        if changes and behind and not ahead:
            status, message = 'local_changes', '发现新版本，但本地有未提交或未跟踪文件，已停止安装'
        return dict(status=status, message=message, current=current, target=target,
                    ahead=ahead, behind=behind, changes=changes.splitlines(),
                    is_update=bool(behind) and not ahead, branch=self.branch, repository=self.repository,
                    restart_required=False)

    def check(self):
        try:
            with self.lock():
                return self._check()
        except UpdateError as exc:
            return self.error(exc)

    @staticmethod
    def error(exc):
        return dict(status=exc.status, message=exc.message, is_update=False, restart_required=False)

    def install(self, install_dependencies=None, *, service_owned=False):
        changed = False
        try:
            with contextlib.ExitStack() as locks:
                if not service_owned:
                    locks.enter_context(self.lock('oas-service-runtime.lock'))
                locks.enter_context(self.lock())
                self.validate(clean=True)
                info = self._check()
                if info['status'] != 'available':
                    return info
                old = info['current']
                self.validate(clean=True)  # Recheck after the potentially slow fetch.
                if self.run('rev-parse', 'HEAD') != old:
                    raise UpdateError('local_changes', '检查期间 HEAD 已变化，已停止安装')
                files = self.run('diff', '--name-only', old, info['target']).splitlines()
                added = self.run('diff', '--diff-filter=A', '--name-only', old, info['target']).splitlines()
                collisions = [path for path in added if os.path.lexists(self.root / path)]
                if collisions:
                    raise UpdateError('local_changes', '新版本文件与本地保留文件重名，已停止安装：\n'
                                      + '\n'.join(collisions))
                dependencies = any(p == 'requirements.txt' or p == 'requirements-in.txt' for p in files)
                if dependencies:
                    self.mark_dependencies(True)  # Remains visible even if the process exits.
                self.run('-c', 'core.hooksPath=', 'merge', '--ff-only', info['target'], timeout=45)
                changed = True
                if self.dependency_pending():
                    if install_dependencies is None:
                        raise UpdateError('dependencies_pending', '代码已更新，依赖尚未安装；任务启动已阻止')
                    install_dependencies()
                    self.mark_dependencies(False)
                info.update(status='updated', message='更新成功，需要重启服务', restart_required=True)
                return info
        except UpdateError as exc:
            result = self.error(exc)
        except Exception as exc:
            result = self.error(UpdateError('dependency_error', f'依赖安装失败：{exc}'))
        result['restart_required'] = changed
        return result

    def complete_dependencies(self, installer):
        with self.lock():
            if self.dependency_pending():
                installer()
                self.mark_dependencies(False)
