"""棋局提速的帧隔离、并行匹配及共享设备恢复；不连接设备。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, PropertyMock, patch

import numpy as np

from tasks.Chess.runtime.performance import frame_cached, match_hand_templates
from tasks.Chess.runtime.press_and_drag import Press_and_Drag
from tasks.Chess.script_task import ScriptTask


class PerformanceTest(unittest.TestCase):
    def test_cache_is_invalidated_by_frame_or_image_identity_and_caches_none(self):
        calls = Mock(return_value=None)
        class Probe:
            @frame_cached
            def read(self, position):
                return calls(position)
        probe = Probe()
        probe.device = SimpleNamespace(image_frame_id='one', image=np.zeros((1, 1)))
        probe.read(1)
        probe.read(1)
        calls.assert_called_once_with(1)
        probe.read(2)
        self.assertEqual(calls.call_count, 2)
        probe.device.image_frame_id = 'two'
        probe.read(1)
        self.assertEqual(calls.call_count, 3)
        probe.device.image = np.ones((1, 1))
        probe.read(1)
        self.assertEqual(calls.call_count, 4)
        probe.device.image_frame_id = None
        probe.read(1)
        probe.read(1)
        self.assertEqual(calls.call_count, 6)

    def test_parallel_matches_retain_threshold_nms_coordinates_and_rule_roi(self):
        rng = np.random.default_rng(23)
        image = rng.integers(0, 256, (100, 150, 3), dtype=np.uint8)
        rule = SimpleNamespace(image=image[35:55, 50:70].copy(), roi_back=(1, 2, 3, 4))
        result = match_hand_templates(image, [('target', rule)], (20, 20, 100, 70), .75)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1:], ('target', (55, 40, 20, 20)))
        self.assertAlmostEqual(result[0][0], 1., places=5)
        self.assertEqual(rule.roi_back, (1, 2, 3, 4))
        noise = SimpleNamespace(image=rng.integers(0, 256, (20, 20, 3), dtype=np.uint8))
        self.assertEqual(match_hand_templates(image, [('noise', noise)], (20, 20, 100, 70), .75), [])

    def test_fast_drag_still_checks_controls_and_preserves_explicit_retry_duration(self):
        device = SimpleNamespace(config=SimpleNamespace(script=SimpleNamespace(
            device=SimpleNamespace(control_method='minitouch'))), handle_control_check=Mock())
        with patch('tasks.Chess.runtime.press_and_drag._press_and_drag_minitouch') as drag:
            Press_and_Drag(device, (10, 10), (100, 100), name='fast')
            device.handle_control_check.assert_called_once_with('fast')
            self.assertEqual(drag.call_args.kwargs['hold_duration'], .25)
            self.assertEqual(drag.call_args.kwargs['swipe_duration'], .16)
            Press_and_Drag(device, (10, 10), (100, 100), hold_duration=.35)
            self.assertEqual(drag.call_args.kwargs['hold_duration'], .35)

    def test_screenshot_interval_restores_exact_snapshot_on_success_and_failure(self):
        for failed in (False, True):
            task = object.__new__(ScriptTask)
            timer = SimpleNamespace(limit=.27)
            task.device = SimpleNamespace(_screenshot_interval=timer)
            task.device.screenshot_interval_set = lambda value: setattr(timer, 'limit', value)
            def run():
                self.assertEqual(timer.limit, .05)
                if failed:
                    raise RuntimeError('interrupted')
                return 'done'
            task._run_configured_chess = run
            with patch.object(ScriptTask, 'manual_execution', new_callable=PropertyMock, return_value=True):
                if failed:
                    with self.assertRaises(RuntimeError):
                        task.run()
                else:
                    self.assertEqual(task.run(), 'done')
            self.assertEqual(timer.limit, .27)


if __name__ == '__main__':
    unittest.main()
