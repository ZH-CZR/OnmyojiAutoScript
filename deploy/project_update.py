"""Update installed copies only from the project's integration repository."""
from pathlib import Path
import shutil
import subprocess

PROJECT_REPOSITORY = 'https://gitee.com/oYe486/onmyoji-auto-script.git'
PROJECT_BRANCH = 'master'
ROOT = Path(__file__).resolve().parents[1]


def normalize_repository(value):
    return value.strip().rstrip('/').removesuffix('.git').lower()


def apply_project_settings(settings):
    """Old deployment files must not redirect updates to either source repo."""
    settings.update(Repository=PROJECT_REPOSITORY, Branch=PROJECT_BRANCH, KeepLocalChanges=True)
    return settings


class ProjectUpdater:
    def __init__(self, root=ROOT, repository=PROJECT_REPOSITORY, branch=PROJECT_BRANCH, enabled=True):
        self.root = Path(root)
        self.repository = repository
        self.branch = branch
        self.enabled = enabled
        self.message = ''
        bundled = self.root / 'toolkit/Git/mingw64/bin/git.exe'
        self.git = str(bundled) if bundled.is_file() else shutil.which('git') or 'git'

    def run(self, *args, timeout=10):
        try:
            return subprocess.run([self.git, '-C', str(self.root), *args], capture_output=True,
                                  text=True, encoding='utf-8', errors='replace', timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.message = f'Git 执行失败：{exc}'
            return None

    def output(self, *args):
        result = self.run(*args)
        return result.stdout.strip() if result is not None and result.returncode == 0 else ''

    def fetch(self):
        if not self.enabled:
            self.message = '自动更新已关闭。'
            return False
        remote = self.output('remote', 'get-url', 'origin')
        if normalize_repository(remote) != normalize_repository(self.repository):
            self.message = f'origin 与项目更新仓库不一致，请设置为 {self.repository}。'
            return False
        result = self.run('fetch', '--no-tags', 'origin',
                          f'+refs/heads/{self.branch}:refs/remotes/origin/{self.branch}', timeout=30)
        if result is None or result.returncode:
            self.message = f'无法获取远端 {self.branch} 分支；请确认仓库已初始化且网络、访问权限正常。'
            return False
        return True

    def commits(self, ref='HEAD', count=1):
        text = self.output('log', f'-{count}', '--date=iso-strict', '--pretty=format:%H---%an---%ad---%s', ref)
        items = [tuple(line.split('---', 3)) for line in text.splitlines() if line]
        return (items[0] if items else (None, None, None, None)) if count == 1 else items

    def distance(self):
        value = self.output('rev-list', '--left-right', '--count', f'HEAD...origin/{self.branch}')
        try:
            return tuple(int(part) for part in value.split()) if len(value.split()) == 2 else None
        except ValueError:
            return None

    def check(self):
        result = {'is_update': False, 'branch': self.branch, 'repository': self.repository,
                  'current_commit': self.commits(), 'latest_commit': (None, None, None, None), 'commit': []}
        if self.fetch():
            commits = self.commits(f'origin/{self.branch}', 15)
            result.update(commit=commits, latest_commit=commits[0] if commits else (None, None, None, None))
            distance = self.distance()
            if distance is None:
                self.message = '无法比较本地与远端历史。'
            elif distance[0]:
                self.message = '本地存在尚未合入远端的提交，请先完成合并。'
            else:
                result['is_update'] = bool(distance[1])
                self.message = '发现项目更新。' if distance[1] else '已是最新版本。'
        result['message'] = self.message
        return result

    def update(self):
        # Refuse the complete dirty tree, including untracked files; never stash,
        # merge divergent histories, reset, or discard a user's development work.
        status = self.run('status', '--porcelain', '--untracked-files=all')
        if status is None or status.returncode:
            self.message = '无法检查本地工作区，更新已停止。'
            return False
        if status.stdout.strip():
            self.message = '本地有未提交或未跟踪的改动，请保存后再更新。'
            return False
        info = self.check()
        if not info['is_update']:
            return False
        result = self.run('merge', '--ff-only', f'origin/{self.branch}', timeout=30)
        if result is None or result.returncode:
            self.message = '快进更新失败，请检查本地状态；本地改动不会被强制覆盖。'
            return False
        self.message = '项目更新完成，请重启服务和前端。'
        return True
