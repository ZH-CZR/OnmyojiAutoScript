"""OASX installer contract without installing packages or starting a game."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from deploy.installer import Installer


class FrontendDeployTest(unittest.TestCase):
    def test_install_then_validate_same_interpreter(self):
        with patch('deploy.installer.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(Installer().install(), 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0][:3], commands[1][:3])
        self.assertIn('install', commands[0])
        self.assertEqual(commands[1][-1], 'check')
        self.assertTrue(all(call.kwargs['shell'] is False for call in run.call_args_list))

    def test_failed_install_stops_and_returns_failure(self):
        with patch('deploy.installer.subprocess.run', return_value=SimpleNamespace(returncode=7)) as run:
            self.assertEqual(Installer().install(), 7)
        self.assertEqual(run.call_count, 1)

    def test_check_does_not_install(self):
        with patch('deploy.installer.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(Installer().install(check_only=True), 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], 'check')
