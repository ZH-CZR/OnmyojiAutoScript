"""Exercise startup orientation transitions without ADB, RPC or game input."""
from collections import deque
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from module.base.timer import Timer
from module.device.device import Device
from module.exception import GameStuckError, RequestHumanTakeover


class ScreenshotStartupTest(unittest.TestCase):
    def setUp(self):
        self.device = Device.__new__(Device)
        self.device.config = SimpleNamespace(
            config_name='offline', script=SimpleNamespace(
                device=SimpleNamespace(screenshot_method='nemu_ipc'),
                error=SimpleNamespace(save_error=True, screenshot_length=5)))
        self.device._screenshot_interval = Mock()
        self.device.detect_record = set()
        self.device.click_record = deque(maxlen=15)
        self.device.stuck_timer = Timer(60, count=60).start()
        self.device.stuck_timer_long = Timer(300, count=300).start()
        self.device.app_is_running = Mock(return_value=True)
        self.device.handle_night_commission = Mock(return_value=False)
        self.device.get_orientation = Mock()
        self.device.orientation = 0
        self.portrait = np.full((1280, 720, 3), 60, dtype=np.uint8)
        self.landscape = np.full((720, 1280, 3), 80, dtype=np.uint8)
        self.capture = Mock()
        self.device.screenshot_methods = {'nemu_ipc': self.capture}
        self.client = Mock()
        self.client.register_frame.return_value = {'frame_id': 'valid-frame'}
        self.rpc_patch = patch('module.device.screenshot.get_image_client', return_value=self.client)
        self.rpc_patch.start()
        self.addCleanup(self.rpc_patch.stop)

    def test_portrait_frames_are_not_published_or_returned(self):
        self.capture.side_effect = [self.portrait] * 3 + [self.landscape]
        result = self.device.screenshot()
        self.assertIs(result, self.landscape)
        self.assertEqual(self.capture.call_count, 4)
        self.client.register_frame.assert_called_once_with(self.landscape, 'offline')
        self.assertEqual(len(self.device.screenshot_deque), 1)
        self.assertIs(self.device.screenshot_deque[0]['image'], self.landscape)
        self.assertEqual(self.device._image_batch_cache_frame_id, 'valid-frame')

    def test_valid_size_cache_does_not_accept_later_portrait(self):
        self.capture.side_effect = [self.landscape, self.portrait, self.landscape]
        self.device.screenshot()
        self.device.screenshot()
        self.assertEqual(self.capture.call_count, 3)
        self.assertEqual(self.client.register_frame.call_count, 2)

    def test_rotated_frame_is_also_the_registered_rpc_frame(self):
        self.device.orientation = 1
        self.portrait[0, 0] = 120
        self.capture.return_value = self.portrait
        result = self.device.screenshot()
        expected = cv2.rotate(self.portrait, cv2.ROTATE_90_COUNTERCLOCKWISE)
        np.testing.assert_array_equal(result, expected)
        self.assertIs(self.client.register_frame.call_args.args[0], result)
        self.assertEqual(result.shape, (720, 1280, 3))

    def test_permanent_portrait_has_bounded_wait(self):
        self.capture.return_value = self.portrait
        with patch('module.device.screenshot.time.monotonic', side_effect=[100, 101, 131]):
            with self.assertRaisesRegex(GameStuckError, '30 seconds'):
                self.device.screenshot()
        self.assertEqual(self.capture.call_count, 2)
        self.client.register_frame.assert_not_called()
        self.assertIsNone(self.device.image_frame_id)

    def test_watchdog_still_runs_during_orientation_wait(self):
        self.capture.return_value = self.portrait
        self.device.stuck_record_check = Mock(side_effect=[False, GameStuckError('watchdog')])
        with self.assertRaisesRegex(GameStuckError, 'watchdog'):
            self.device.screenshot()
        self.assertEqual(self.device.stuck_record_check.call_count, 2)
        self.client.register_frame.assert_not_called()

    def test_unsupported_resolution_still_requires_configuration_fix(self):
        self.capture.return_value = np.ones((600, 800, 3), dtype=np.uint8)
        with self.assertRaises(RequestHumanTakeover):
            self.device.screenshot()
        self.client.register_frame.assert_not_called()


if __name__ == '__main__':
    unittest.main()
