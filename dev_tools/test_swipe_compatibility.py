"""Exercise the task-to-device swipe contract without sending device input."""
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, call, patch

from module.device.control import Control


def fake_device(method='minitouch'):
    device = SimpleNamespace(
        config=SimpleNamespace(script=SimpleNamespace(device=SimpleNamespace(control_method=method))),
        image=None, handle_control_check=Mock(), _invalidate_image_batch_cache=Mock(),
        swipe_minitouch=Mock(), swipe_scrcpy=Mock(), swipe_window_message=Mock(),
        swipe_uiautomator2=Mock(), swipe_adb=Mock(),
        _format_action_duration=Control._format_action_duration,
    )
    device.swipe = MethodType(Control.swipe, device)
    return device


class SwipeCompatibilityTest(unittest.TestCase):
    def test_switch_soul_scroll_reaches_group_selection(self):
        from module.config.config import Config
        from module.exception import TaskEnd
        from tasks.Component.SwitchSoul.switch_soul import SwitchSoul

        device = fake_device()
        task = SwitchSoul(config=Config('template'), device=device)
        with patch.object(task, 'screenshot'), \
                patch.object(task.O_SS_GROUP_NAME, 'detect_and_ocr', return_value=[SimpleNamespace(ocr_text='道馆')]), \
                patch.object(task, 'click', side_effect=TaskEnd('group selection boundary')) as click, \
                patch('tasks.Component.SwitchSoul.switch_soul.sleep'):
            with self.assertRaisesRegex(TaskEnd, 'group selection boundary'):
                task.switch_soul_one(2, 1)
        device.swipe_minitouch.assert_called_once()
        click.assert_called_once_with(task.C_SOU_GROUP_2)

    def test_positive_hold_reaches_supported_backends(self):
        for method in ('minitouch', 'scrcpy', 'window_message'):
            with self.subTest(method=method):
                device = fake_device(method)
                device.swipe((10, 20), (40, 90), wait_up_time=0.5)
                gesture = getattr(device, 'swipe_' + method)
                self.assertEqual(gesture.call_args.kwargs, {'wait_up_time': 0.5})

    def test_minitouch_wait_precedes_finger_release(self):
        from module.device.method.minitouch import Minitouch

        builder = Mock()
        for name in ('down', 'move', 'commit', 'wait', 'up'):
            getattr(builder, name).return_value = builder
        device = SimpleNamespace(minitouch_builder=builder, minitouch_send=Mock())
        Minitouch.swipe_minitouch(device, (10, 20), (40, 90), wait_up_time=1)
        self.assertIn(call.wait(1000), builder.mock_calls)
        self.assertLess(builder.mock_calls.index(call.wait(1000)), builder.mock_calls.index(call.up()))

    def test_invalid_hold_does_not_send_gesture(self):
        for hold in (-1, float('nan'), float('inf')):
            device = fake_device()
            with self.assertRaises(ValueError):
                device.swipe((10, 20), (40, 90), wait_up_time=hold)
            device.swipe_minitouch.assert_not_called()

    def test_adb_zero_hold_keeps_existing_interface(self):
        device = fake_device('ADB')
        device.swipe((10, 20), (40, 90), wait_up_time=0)
        device.swipe_adb.assert_called_once()
        self.assertNotIn('wait_up_time', device.swipe_adb.call_args.kwargs)
