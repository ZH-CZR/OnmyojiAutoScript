"""Exercise login against real Device watchdog methods, without ADB or input."""
from collections import deque
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from module.base.timer import Timer
from module.device.device import Device
from module.exception import GameStuckError, TaskEnd
from tasks.Restart.login import LoginHandler


class LoginDeviceTest(unittest.TestCase):
    def test_login_templates_exist_and_channel_images_decode(self):
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / 'tasks/Restart/login.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == 'self' and node.attr.startswith(('I_', 'C_', 'O_'))):
                self.assertTrue(hasattr(LoginHandler, node.attr), node.attr)
        from tasks.Restart.login_assets import LoginChannelAssets
        for asset in (LoginChannelAssets.I_QD_READ_AND_AGREED, LoginChannelAssets.I_ACCEPT_AGREEMENT):
            self.assertTrue((root / asset.file).is_file())
            self.assertGreater(asset.image.size, 0)

    def setUp(self):
        self.task = LoginHandler.__new__(LoginHandler)
        self.device = Device.__new__(Device)
        self.task.device = self.device
        self.device.detect_record = set()
        self.device.click_record = deque(maxlen=15)
        self.device.stuck_timer = Timer(60, count=60).start()
        self.device.stuck_timer_long = Timer(300, count=300).start()
        self.original_timers = self.device.stuck_timer, self.device.stuck_timer_long
        self.device.app_is_running = Mock(return_value=True)
        self.task.screenshot = Mock(side_effect=self.device.stuck_record_check)
        self.task.appear = Mock(side_effect=[False, True])

    def assert_restored(self):
        self.assertIs(self.device.stuck_timer, self.original_timers[0])
        self.assertIs(self.device.stuck_timer_long, self.original_timers[1])
        self.assertEqual(self.device.detect_record, set())
        self.assertNotIn('stuck_record_check', self.device.__dict__)

    def test_real_login_loop_reaches_success_with_device_interface(self):
        self.task._app_handle_login()
        self.task.screenshot.assert_called_once_with()
        self.assert_restored()

    def test_loading_can_wait_past_normal_watchdog_but_still_times_out(self):
        def screenshot():
            with patch('module.base.timer.time.time', return_value=1061):
                self.assertFalse(self.device.stuck_record_check())
            with patch('module.base.timer.time.time', return_value=1601):
                self.device.stuck_record_check()

        self.task.screenshot.side_effect = screenshot
        with patch('module.base.timer.time.time', return_value=1000), self.assertRaises(GameStuckError):
            self.task._app_handle_login()
        self.assert_restored()

    def test_channel_login_task_end_restores_watchdog(self):
        self.task.appear.side_effect = None
        self.task.appear.return_value = True
        self.task.set_next_run = Mock()
        with self.assertRaises(TaskEnd):
            self.task._app_handle_login()
        self.task.set_next_run.assert_called_once_with()
        self.assert_restored()

    def test_screenshot_error_restores_watchdog(self):
        self.task.screenshot.side_effect = RuntimeError('capture failed')
        with self.assertRaisesRegex(RuntimeError, 'capture failed'):
            self.task._app_handle_login()
        self.assert_restored()

    def _check_login_transition(self, with_character):
        self.task.appear.side_effect = None
        self.task.appear.return_value = False
        self.task.appear_then_click = Mock(return_value=False)
        self.task.ocr_appear_click = Mock(return_value=True)
        self.task.wait_until_appear = Mock(side_effect=AssertionError('blocking character-page wait'))
        frames = iter(['enter', 'character', 'courtyard', 'courtyard'] if with_character
                      else ['enter', 'courtyard'])
        current = None

        def screenshot():
            nonlocal current
            self.device.stuck_record_check()
            current = next(frames)

        def appear(asset, **kwargs):
            if isinstance(asset, list):
                return current == 'courtyard'
            if asset is self.task.I_LOGIN_8:
                return current == 'enter'
            if asset is self.task.I_LOGIN_SPECIFIC_SERVE:
                return current == 'character'
            return False

        self.task.screenshot.side_effect = screenshot
        self.task.appear.side_effect = appear
        self.task._app_handle_login()
        self.task.ocr_appear_click.assert_any_call(self.task.O_LOGIN_ENTER_GAME_1, interval=3)
        if with_character:
            self.task.ocr_appear_click.assert_any_call(self.task.O_LOGIN_SPECIFIC_SERVE, interval=0.6)
        self.task.wait_until_appear.assert_not_called()
        self.assert_restored()

    def test_single_character_login_does_not_wait_for_absent_character_page(self):
        self._check_login_transition(with_character=False)

    def test_character_selection_is_still_handled_on_next_frame(self):
        self._check_login_transition(with_character=True)


if __name__ == '__main__':
    unittest.main()
