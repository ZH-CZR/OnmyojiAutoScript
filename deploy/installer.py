"""Explicit OASX deployment entry; ordinary server startup never installs."""
import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


class Installer:
    def install(self, check_only=False):
        if sys.version_info[:2] != (3, 10):
            print('ERROR: Backend deployment requires Python 3.10.', flush=True)
            return 1
        requirements = ROOT / 'requirements.txt'
        if not requirements.is_file():
            print('ERROR: requirements.txt is missing.', flush=True)
            return 1
        commands = [] if check_only else [
            [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
             '-r', str(requirements)],
        ]
        commands.append([sys.executable, '-m', 'pip', 'check'])
        for command in commands:
            print('INFO: ' + subprocess.list2cmdline(command), flush=True)
            result = subprocess.run(command, cwd=ROOT, shell=False)
            if result.returncode:
                print('ERROR: Deployment failed; backend must not start.', flush=True)
                return result.returncode
        print('INFO: Backend dependencies ready.', flush=True)
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Only run pip check')
    args = parser.parse_args()
    return Installer().install(check_only=args.check)


if __name__ == '__main__':
    raise SystemExit(main())
