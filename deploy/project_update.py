"""Startup source replacement; preserve runtime data and never update another workspace."""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import re
import tempfile
from urllib.parse import urlsplit

PROJECT_REPOSITORY = 'https://gitee.com/oYe486/onmyoji-auto-script.git'
PROJECT_BRANCH = 'master'
REQUIREMENT_FILES = {'requirements.txt', 'requirements-in.txt', 'requirements-ocr.txt'}
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

    def is_source_archive(self):
        if not (self.root / '.git').exists():
            return True
        if Path(self.run('rev-parse', '--show-toplevel')).resolve() != self.root:
            raise UpdateError('wrong_repository', '更新目录必须是项目仓库根目录')
        try:
            self.run('rev-parse', '--verify', 'HEAD^{commit}')
            return False
        except UpdateError:
            # An old frontend may have run git init on an extracted ZIP.
            self.run('symbolic-ref', '--quiet', 'HEAD')
            return True

    @staticmethod
    def archive_result(message='源码目录没有有效 Git 版本，保留原文件并跳过更新'):
        return dict(status='source_archive', message=message, is_update=False, restart_required=False)

    def prepare_archive(self):
        """Prepare Git metadata for a ZIP installation without changing source files."""
        try:
            self.validate_source()
            if not (self.root / '.git').exists():
                self.run('init', '--initial-branch', self.branch)
            if self.run('symbolic-ref', '--quiet', '--short', 'HEAD') != self.branch:
                raise UpdateError('wrong_branch', '分支与部署配置不一致，未切换分支')
            if 'origin' not in self.run('remote').splitlines():
                self.run('remote', 'add', 'origin', self.repository)
            if self.run('remote', 'get-url', '--all', 'origin').splitlines() != [self.repository]:
                raise UpdateError('wrong_remote', 'origin 与配置不一致，未改写远端')
            return dict(status='prepared', message='源码目录已准备更新元数据，原文件尚未修改', restart_required=False)
        except UpdateError as exc:
            return self.error(exc)

    @staticmethod
    def protected_path(name):
        parts = Path(name).parts
        if not parts:
            return True
        first = parts[0].lower()
        if first == 'config':
            return not (len(parts) == 2 and parts[1].startswith('template') and Path(name).suffix in ('.json', '.ini'))
        return (first in {'.git', '.venv', 'venv', 'toolkit', 'configs', 'log', 'logs', 'screenshots',
                          'data', '.codex', '.claude', '.idea', '.vscode'}
                or any(part in {'__pycache__', '.pytest_cache'} for part in parts)
                or Path(name).name == '.env' or Path(name).suffix.lower() in {'.pem', '.key', '.crt', '.log'})

    def replace_sources(self, target, before_write=None):
        old = set(filter(None, self.run('ls-files', '-z').split('\0')))
        new = set(filter(None, self.run('ls-tree', '-r', '--name-only', '-z', target).split('\0')))
        restore = sorted(name for name in new if not self.protected_path(name))
        remove = old - new
        ignored = set(filter(None, self.run('ls-files', '--others', '--ignored', '--exclude-standard', '-z').split('\0')))
        collisions = (new - old) & ignored
        if any(not self.protected_path(name) for name in collisions):
            raise UpdateError('protected_path', '新版源码与本地被忽略文件重名，保留文件并停止更新')
        for name in set(restore) | {n for n in remove if not self.protected_path(n)}:
            if not (self.root / name).resolve().is_relative_to(self.root):
                raise UpdateError('protected_path', '源码路径指向项目外部，未执行覆盖：' + name)
        if before_write is not None:
            before_write()
        self._source_write_started = True
        # Replace the entire managed source tree, including locally modified files.
        # No reset --hard or clean operation can delete a user's runtime directories.
        self.run('read-tree', '--reset', target)
        for name in remove:
            path = self.root / name
            if not self.protected_path(name) and (path.is_file() or path.is_symlink()):
                path.unlink()
        with tempfile.NamedTemporaryFile(dir=self.git_dir, delete=False) as handle:
            pathspec = Path(handle.name)
            handle.write(b''.join((':(literal)' + name).encode('utf-8') + b'\0' for name in restore))
        try:
            if restore:
                self.run('-c', 'core.hooksPath=', 'restore', '--source', target, '--worktree',
                         '--pathspec-from-file=' + str(pathspec), '--pathspec-file-nul', timeout=120)
            self.run('update-ref', 'HEAD', target)
        finally:
            pathspec.unlink(missing_ok=True)

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
        initial = self.is_source_archive()
        try:
            self.run('fetch', '--no-tags', *(['--depth', '1'] if initial else []), '--', self.repository,
                     f'+refs/heads/{self.branch}:{self.remote_revision}', timeout=45)
        except UpdateError as exc:
            raise UpdateError('network_error', '获取更新失败：' + exc.message) from exc
        current = None if initial else self.run('rev-parse', 'HEAD')
        target = self.run('rev-parse', self.remote_revision)
        ahead, behind = (map(int, self.run('rev-list', '--left-right', '--count', f'{current}...{target}').split())
                         if current else (0, 1))
        status = 'available' if current != target else 'up_to_date'
        message = '云端版本不同，启动时将完整替换受管理源码' if status == 'available' else '当前已是最新版本'
        return dict(status=status, message=message, current=current, target=target,
                    ahead=ahead, behind=behind, changes=changes.splitlines(),
                    is_update=current != target, branch=self.branch, repository=self.repository,
                    restart_required=False)

    def check(self):
        try:
            if not (self.root / '.git').exists():
                return self.archive_result()
            with self.lock():
                return self._check()
        except UpdateError as exc:
            return self.error(exc)

    @staticmethod
    def error(exc):
        return dict(status=exc.status, message=exc.message, is_update=False, restart_required=False)

    def install(self, install_dependencies=None, *, service_owned=False, checked=None):
        changed = False
        self._source_write_started = False
        try:
            if not (self.root / '.git').exists():
                return self.archive_result()
            with contextlib.ExitStack() as locks:
                if not service_owned:
                    locks.enter_context(self.lock('oas-service-runtime.lock'))
                locks.enter_context(self.lock())
                self.validate(clean=True)
                info = checked if checked is not None else self._check()
                if info['status'] != 'available':
                    return info
                old = info['current']
                self.validate(clean=True)
                current = None if self.is_source_archive() else self.run('rev-parse', 'HEAD')
                if current != old:
                    raise UpdateError('local_changes', '检查期间 HEAD 已变化，已停止安装')
                files = self.run('diff', '--name-only', old, info['target']).splitlines() if old else list(REQUIREMENT_FILES)
                local_requirements = self.run('diff', '--name-only', info['target'], '--', *sorted(REQUIREMENT_FILES))
                dependencies = bool(local_requirements) or any(p in REQUIREMENT_FILES for p in files)
                self.replace_sources(info['target'], before_write=(lambda: self.mark_dependencies(True)) if dependencies else None)
                changed = True
                if self.dependency_pending():
                    if install_dependencies is None:
                        raise UpdateError('dependencies_pending', '代码已更新，依赖尚未安装；任务启动已阻止')
                    install_dependencies()
                    self.mark_dependencies(False)
                info.update(status='updated', message='源码完整更新成功，需要重启服务', restart_required=True)
                return info
        except UpdateError as exc:
            result = self.error(exc)
        except Exception as exc:
            result = self.error(UpdateError('dependency_error', f'依赖安装失败：{exc}'))
        result['restart_required'] = changed or self._source_write_started
        return result

    def complete_dependencies(self, installer):
        with self.lock():
            if self.dependency_pending():
                installer()
                self.mark_dependencies(False)
