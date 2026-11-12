"""棋局提速的帧隔离、并行匹配及共享设备恢复；不连接设备。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, PropertyMock, patch

import numpy as np
from concurrent.futures import ThreadPoolExecutor

from tasks.Chess.runtime.performance import frame_cached, match_hand_templates
from tasks.Chess.runtime.press_and_drag import Press_and_Drag
from tasks.Chess.script_task import ScriptTask
from tasks.Chess.strategy.lineup import LINEUP_REGISTRY


class PerformanceTest(unittest.TestCase):
    def test_hand_templates_follow_selected_lineup_and_include_only_its_substitutes(self):
        task = object.__new__(ScriptTask)
        task._load_hand_template_folder = Mock(side_effect=AssertionError('不得遍历全式神目录'))
        for key, entry in LINEUP_REGISTRY.items():
            task.select_lineup_strategy(key)
            expected = set(entry['strategy']['shikigami']) | set(entry['strategy'].get('substitutes', {}))
            self.assertEqual({name for name, _ in task.shikigami_hand_rules}, expected)
        task._load_hand_template_folder.assert_not_called()

    def test_unchanged_hand_pixels_reuse_recognition_across_fresh_frames(self):
        task = object.__new__(ScriptTask)
        task.select_lineup_strategy('counter_ubume')
        task.device = SimpleNamespace(image_frame_id=0, image=np.zeros((720, 1280, 3), dtype=np.uint8))

        def new_frame(x, y):
            task.device.image = task.device.image.copy()
            task.device.image[y, x] = 255
            task.device.image_frame_id += 1
            return task._scan_inventory_hand()

        with patch('tasks.Chess.runtime.card_tracking.match_hand_templates', return_value=[]) as match:
            task._scan_inventory_hand()
            new_frame(200, 300)
            match.assert_called_once()
            new_frame(620, 560)
            self.assertEqual(match.call_count, 2)
            task._invalidate_inventory_hand_observation()
            new_frame(201, 300)
            self.assertEqual(match.call_count, 3)
            task.select_lineup_strategy('qijiaoshan')
            new_frame(202, 300)
            self.assertEqual(match.call_count, 4)

    def test_matching_parallelism_is_capped_at_two(self):
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        rules = [('one', SimpleNamespace(image=np.ones((20, 20, 3), dtype=np.uint8))),
                 ('two', SimpleNamespace(image=np.ones((20, 20, 3), dtype=np.uint8)))]
        with patch('tasks.Chess.runtime.performance.ThreadPoolExecutor', wraps=ThreadPoolExecutor) as pool:
            match_hand_templates(image, rules, (0, 0, 100, 100), .75)
        self.assertLessEqual(pool.call_args.kwargs['max_workers'], 2)

    def test_equipment_and_special_text_reads_are_shared_only_within_current_frame(self):
        task = object.__new__(ScriptTask)
        task.device = SimpleNamespace(image_frame_id=1, image=np.zeros((720, 1280, 3), dtype=np.uint8))
        task.O_BADGE_AREA = SimpleNamespace(roi=(0, 0, 1, 1), detect_and_ocr=Mock(return_value=[]))
        task._template_soul_hand_cards = Mock(return_value=[])
        for _ in range(2):
            task._soul_hand_cards()
            task._discover_soul_hand_cards()
            task._discover_badge_hand_cards()
            task._find_badge_hand_card()
        task._template_soul_hand_cards.assert_called_once()
        task.O_BADGE_AREA.detect_and_ocr.assert_called_once()
        task.device.image_frame_id = 2
        task._soul_hand_cards()
        task._discover_soul_hand_cards()
        self.assertEqual(task._template_soul_hand_cards.call_count, 2)
        self.assertEqual(task.O_BADGE_AREA.detect_and_ocr.call_count, 2)

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
                self.assertEqual(timer.limit, .1)
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
