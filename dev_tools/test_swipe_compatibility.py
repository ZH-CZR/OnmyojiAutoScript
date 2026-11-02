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
    def test_list_scrolls_keep_distance_duration_and_backend(self):
        from tasks.KekkaiActivation.script_task import ScriptTask as Cards
        from tasks.RyouToppa.script_task import ScriptTask as Raid

        cases = (
            (Cards._scroll_card_list, 'tasks.KekkaiActivation.script_task',
             410, (1.9, 2.1), (200, 400, 580, 600), 'kekkai_activation_card_list'),
            (Raid.flush_area_cache, 'tasks.RyouToppa.script_task',
             101, (0.335, 0.369), (540, 1000, 320, 540), 'ryou_toppa_area_refresh'),
        )
        for action, module, distance, durations, bounds, name in cases:
            for method in ('ADB', 'minitouch', 'scrcpy', 'window_message', 'uiautomator2', 'fallback'):
                for duration in durations:
                    with self.subTest(action=name, method=method, duration=duration):
                        device = fake_device(method)
                        with patch(module + '.time.sleep'), \
                                patch(module + '.random.uniform', return_value=duration), \
                                patch(module + '.random.randint', side_effect=lambda low, high: high), \
                                patch('module.atom.swipe.np.random.randint', side_effect=lambda low, high: high - 1):
                            action(SimpleNamespace(device=device))
                        backend = {
                            'ADB': 'adb', 'fallback': 'adb',
                            'window_message': 'window_message',
                        }.get(method, method)
                        gesture = getattr(device, 'swipe_' + backend)
                        gesture.assert_called_once()
                        p1, p2 = gesture.call_args.args
                        self.assertEqual(p1[1] - p2[1], distance)
                        self.assertLessEqual(abs(p1[0] - p2[0]), 4)
                        for x in (p1[0], p2[0]):
                            self.assertTrue(bounds[0] <= x <= bounds[1])
                        self.assertTrue(bounds[2] <= p1[1] <= bounds[3])
                        if backend in ('adb', 'uiautomator2'):
                            self.assertAlmostEqual(gesture.call_args.kwargs['duration'], duration)
                        if backend != 'adb':
                            device.swipe_adb.assert_not_called()
                        device.handle_control_check.assert_called_once_with(name)
                        device._invalidate_image_batch_cache.assert_called_once()

    def test_list_scroll_control_errors_propagate(self):
        from tasks.KekkaiActivation.script_task import ScriptTask as Cards
        from tasks.RyouToppa.script_task import ScriptTask as Raid
        from module.exception import GameStuckError

        for action in (Cards._scroll_card_list, Raid.flush_area_cache):
            device = fake_device('ADB')
            device.handle_control_check.side_effect = GameStuckError('control blocked')
            with patch('tasks.RyouToppa.script_task.time.sleep'):
                with self.assertRaises(GameStuckError):
                    action(SimpleNamespace(device=device))
            device.swipe_adb.assert_not_called()

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
