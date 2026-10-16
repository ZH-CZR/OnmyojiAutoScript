from pathlib import Path
import shutil
import subprocess

import pytest

from deploy.project_update import ProjectUpdater, apply_project_settings, PROJECT_REPOSITORY, PROJECT_BRANCH


def git(root, *args):
    result = subprocess.run([shutil.which('git'), '-C', str(root), *args],
                            capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
    return result.stdout.strip()


def commit(root, text):
    (root / 'task.txt').write_text(text, encoding='utf-8')
    git(root, 'add', 'task.txt')
    git(root, '-c', 'user.name=Port Test', '-c', 'user.email=port-test@example.invalid', 'commit', '-m', text)


@pytest.fixture
def repos(tmp_path):
    remote, seed, local = [tmp_path / name for name in ('remote.git', 'seed', 'local')]
    remote.mkdir()
    git(remote, 'init', '--bare', '--initial-branch=master')
    seed.mkdir()
    git(seed, 'init', '--initial-branch=master')
    commit(seed, 'initial')
    git(seed, 'remote', 'add', 'origin', str(remote))
    git(seed, 'push', '-u', 'origin', 'master')
    git(tmp_path, 'clone', str(remote), str(local))
    return remote, seed, local


def advance(seed):
    commit(seed, 'upstream update')
    git(seed, 'push', 'origin', 'master')


def test_only_project_master_is_configured():
    settings = {'Repository': 'https://gitee.com/pattering-rain/yys.git', 'Branch': 'run_now', 'AutoUpdate': False}
    apply_project_settings(settings)
    assert settings['Repository'] == PROJECT_REPOSITORY
    assert settings['Branch'] == PROJECT_BRANCH == 'master'
    assert settings['KeepLocalChanges'] is True
    assert settings['AutoUpdate'] is False


def test_clean_copy_fast_forwards_to_integration_branch(repos):
    remote, seed, local = repos
    advance(seed)
    updater = ProjectUpdater(local, str(remote))
    info = updater.check()
    assert info['is_update']
    assert info['branch'] == 'master'
    assert updater.update()
    assert git(local, 'rev-parse', 'HEAD') == git(seed, 'rev-parse', 'HEAD')
    assert (local / 'task.txt').read_text(encoding='utf-8') == 'upstream update'


@pytest.mark.parametrize('filename', ['task.txt', 'untracked.txt'])
def test_local_work_is_preserved(repos, filename):
    remote, seed, local = repos
    advance(seed)
    before = git(local, 'rev-parse', 'HEAD')
    (local / filename).write_text('local work', encoding='utf-8')
    updater = ProjectUpdater(local, str(remote))
    assert not updater.update()
    assert git(local, 'rev-parse', 'HEAD') == before
    assert (local / filename).read_text(encoding='utf-8') == 'local work'
    assert '未提交' in updater.message


def test_divergent_history_is_not_merged_or_reset(repos):
    remote, seed, local = repos
    commit(local, 'local commit')
    before = git(local, 'rev-parse', 'HEAD')
    advance(seed)
    updater = ProjectUpdater(local, str(remote))
    assert not updater.update()
    assert git(local, 'rev-parse', 'HEAD') == before
    assert '合入远端' in updater.message


def test_wrong_origin_is_not_fetched(repos):
    _, _, local = repos
    updater = ProjectUpdater(local, 'https://example.invalid/other.git')
    assert not updater.fetch()
    assert 'origin' in updater.message


def test_empty_remote_is_reported_without_replacing_local_code(repos, tmp_path):
    _, _, local = repos
    empty = tmp_path / 'empty.git'
    empty.mkdir()
    git(empty, 'init', '--bare', '--initial-branch=master')
    git(local, 'remote', 'set-url', 'origin', str(empty))
    before = git(local, 'rev-parse', 'HEAD')
    updater = ProjectUpdater(local, str(empty))
    info = updater.check()
    assert not info['is_update']
    assert info['latest_commit'] == (None, None, None, None)
    assert 'master' in info['message']
    assert not updater.update()
    assert git(local, 'rev-parse', 'HEAD') == before
