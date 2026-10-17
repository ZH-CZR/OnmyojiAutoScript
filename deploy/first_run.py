"""Project-local first installation. Imports only the standard library before pip."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ('requirements.txt', 'requirements-ocr.txt')
DEFAULT_PYPI_MIRROR = 'https://pypi.tuna.tsinghua.edu.cn/simple'


def select_pypi_mirror(override=None):
    if override is not None:
        return override
    from deploy.utils import poor_yaml_read
    return poor_yaml_read(str(ROOT / 'config' / 'deploy.yaml')).get('PypiMirror', DEFAULT_PYPI_MIRROR)


@contextlib.contextmanager
def runtime_lock(git, root=None):
    """Use the service's existing OS lock before changing its environment."""
    root = Path(root or ROOT)
    if (root / '.git').exists():
        common = subprocess.check_output([git, '-C', str(root), 'rev-parse', '--git-common-dir'],
                                         text=True, encoding='utf-8').strip()
        folder = Path(common)
        if not folder.is_absolute():
            folder = root / folder
    else:
        folder = root / 'config'
        folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'oas-service-runtime.lock').open('a+b') as handle:
        # Windows permits locking a byte beyond EOF. Do not write before locking:
        # filelock's archive lease can hold byte zero of an empty file.
        handle.seek(0)
        import msvcrt
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError('The backend is running. Stop it before installing or starting another instance.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def dependency_fingerprint():
    digest = hashlib.sha256()
    digest.update(sys.executable.encode())
    digest.update(sys.version.encode())
    for name in REQUIREMENTS:
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


def install_dependencies(index_url):
    marker = ROOT / 'toolkit' / 'first-run-dependencies.json'
    fingerprint = dependency_fingerprint()
    try:
        ready = json.loads(marker.read_text(encoding='utf-8')).get('fingerprint') == fingerprint
    except (OSError, ValueError):
        ready = False
    if ready:
        # A marker alone must not hide a damaged/deleted environment.
        result = subprocess.run([sys.executable, '-m', 'pip', 'check'], cwd=ROOT)
        if result.returncode == 0:
            try:
                run('-c', 'import cv2, numpy, fastapi, adbutils, paddleocr, onnxruntime, zerorpc, yaml, win32api, fuzzywuzzy')
                return
            except subprocess.CalledProcessError:
                pass
    arguments = ['-m', 'pip', 'install', '--disable-pip-version-check', '--no-input',
                 '--timeout', '60', '--retries', '5']
    for name in REQUIREMENTS:
        arguments.extend(['-r', name])
    if index_url:
        arguments.extend(['--index-url', index_url])
    # Install both constraints in one resolution; do not let OCR upgrade FastAPI's runtime.
    run(*arguments)
    run('-m', 'pip', 'check')
    run('-c', 'import cv2, numpy, fastapi, adbutils, paddleocr, onnxruntime, zerorpc, yaml, win32api, fuzzywuzzy')
    marker.parent.mkdir(parents=True, exist_ok=True)
    temporary = marker.with_suffix('.tmp')
    temporary.write_text(json.dumps({'fingerprint': fingerprint}), encoding='utf-8')
    temporary.replace(marker)


def configure(git, index_url=DEFAULT_PYPI_MIRROR):
    from deploy.utils import poor_yaml_read, poor_yaml_write
    config_path = ROOT / 'config' / 'deploy.yaml'
    existing = poor_yaml_read(str(config_path))
    values = poor_yaml_read(str(ROOT / 'deploy' / 'template'))
    values.update(existing)
    # Existing explicit settings belong to the user, including repository and port.
    defaults = {
        'PythonExecutable': sys.executable.replace('\\', '/'),
        'GitExecutable': str(Path(git).resolve()).replace('\\', '/'),
        'WebuiHost': '127.0.0.1', 'WebuiPort': 22267,
        'AutoUpdate': True, 'AutoCheckUpdate': True, 'SSLVerify': True,
        'ReplaceAdb': False, 'AutoConnect': False, 'InstallUiautomator2': False,
        'PypiMirror': index_url,
    }
    import adbutils
    defaults['AdbExecutable'] = str(Path(adbutils.__file__).parent / 'binaries' / 'adb.exe').replace('\\', '/')
    if not Path(defaults['AdbExecutable']).is_file():
        raise RuntimeError('ADB executable is missing from adbutils; reinstall the dependencies.')
    for key, value in defaults.items():
        if key not in existing:
            values[key] = value
    if all(key in existing for key in defaults):
        return  # Do not rewrite a fully configured user's file, comments or extra fields.
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        poor_yaml_write(values, str(config_path), template_file=str(ROOT / 'deploy' / 'template'))
    else:
        # Older partial YAML may contain custom sections unknown to the template.
        # Fill missing values recursively instead of dropping those sections.
        import yaml
        original = yaml.safe_load(config_path.read_text(encoding='utf-8'))
        template = yaml.safe_load((ROOT / 'deploy' / 'template').read_text(encoding='utf-8'))
        if not isinstance(original, dict):
            raise RuntimeError('Existing deploy.yaml is not a mapping; it has not been overwritten.')

        def fill(target, source):
            for key, value in source.items():
                if isinstance(value, dict):
                    if key not in target:
                        target[key] = {}
                    if not isinstance(target[key], dict):
                        raise RuntimeError(f'Invalid deployment section {key}; configuration has not been overwritten.')
                    fill(target[key], value)
                elif key not in target:
                    target[key] = values.get(key, value)

        fill(original, template)
        temporary = config_path.with_suffix('.yaml.tmp')
        temporary.write_text(yaml.safe_dump(original, allow_unicode=True, sort_keys=False), encoding='utf-8')
        temporary.replace(config_path)


def prepare_models():
    from module.ocr.rpc import _bundled_ocr_model_issues, _repair_bundled_ocr_models
    if _bundled_ocr_model_issues() and not _repair_bundled_ocr_models():
        raise RuntimeError('OCR model download failed. Check the network and run start.bat again.')
    if _bundled_ocr_model_issues():
        raise RuntimeError('OCR models are incomplete; startup stopped.')
    # Verify actual DLL loading and inference pipeline initialization, not just filenames.
    run('-c', 'from module.ocr.rpc import _configure_bundled_paddlex_cache; _configure_bundled_paddlex_cache(); from module.ocr.ppocr import TextSystem; TextSystem()')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--git', required=True)
    parser.add_argument('--index-url', default=None)
    parser.add_argument('--skip-models', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    index_url = select_pypi_mirror(args.index_url)
    print(f'Python package source: {index_url or "pip default"}', flush=True)
    with runtime_lock(args.git):
        install_dependencies(index_url)
        configure(args.git, index_url)
        if not args.skip_models:
            prepare_models()
    print('Installation ready. No emulator or game task has been started.', flush=True)


if __name__ == '__main__':
    main()
