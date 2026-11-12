"""六道觉强化弹窗截图回放及有界重试；不创建设备、不启动游戏。"""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from module.exception import GameStuckError
from tasks.SixRealms_jue.moon_sea.map import MoonSeaMap


class JueRuntimeTest(unittest.TestCase):
    def task(self):
        task = MoonSeaMap.__new__(MoonSeaMap)
        task.cnt_skill101, task.cnt_skillpower = 1, 10
        task.screenshot = Mock()
        task.appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=False)
        return task

    def replay(self):
        task = self.task()
        path = Path(__file__).parent / 'fixtures/six_realms_jue/strengthening_overlay.png'
        image = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
        rules = {}

        def appear(rule, **kwargs):
            if rule.name not in rules:
                rules[rule.name] = deepcopy(rule)
            return rules[rule.name].match(image)

        task.appear = appear
        return task

    def test_error_frame_reproduces_false_island_but_blocks_entry(self):
        task = self.replay()
        self.assertTrue(task.appear(task.I_SHENMI))
        self.assertTrue(task.appear(task.I_PEACOCK_SKILL1))
        self.assertFalse(task.appear(task.I_SELECT_3))
        self.assertIsNone(task.enter_island())
        task.appear_then_click.assert_not_called()

    def test_error_frame_resumes_popup_without_outer_select(self):
        task = self.replay()
        original = task.appear
        closed = False

        def appear(rule, **kwargs):
            return rule == task.I_SELECT_3 if closed else original(rule, **kwargs)

        def screenshot():
            nonlocal closed
            closed = True

        task.appear = appear
        task.screenshot.side_effect = screenshot
        task.appear_then_click = Mock(return_value=True)
        self.assertTrue(task.select_skill())
        task.appear_then_click.assert_called_once_with(task.I_PEACOCK_SKILL1, interval=1)
        self.assertEqual(task.cnt_skillpower, 11)
        # 重复刷新不能再次累计同一次升级。
        self.assertFalse(task.select_strengthening())
        self.assertEqual(task.cnt_skillpower, 11)

    def test_popup_retries_only_three_times_and_keeps_count_on_failure(self):
        task = self.replay()
        task.appear_then_click.return_value = True
        with patch('tasks.SixRealms_jue.moon_sea.skills.time.monotonic',
                   side_effect=range(30)):
            with self.assertRaisesRegex(GameStuckError, '强化选择'):
                task.select_skill()
        self.assertEqual(task.appear_then_click.call_count, 3)
        self.assertEqual(task.cnt_skillpower, 10)

    def test_outer_choice_waits_for_delayed_popup_without_counting_click(self):
        task = self.task()
        task.appear.side_effect = lambda rule, **kw: rule.name in ('I_SKILL_REFRESH', 'I_SELECT_3')
        task.appear_then_click.return_value = True
        self.assertTrue(task.select_skill())
        task.appear_then_click.assert_called_once_with(task.I_SELECT_3, interval=1)
        self.assertEqual(task.cnt_skillpower, 10)

    def test_transient_popup_loss_does_not_confirm_or_double_count(self):
        task = self.task()
        clock = [0.]
        frame = [0]
        # 中间一帧误判关闭，随后弹窗恢复；必须重新开始稳定确认。
        visible = [True, False, True, False, False, False, False]
        task.appear.side_effect = lambda rule, **kw: rule == (
            task.I_PEACOCK_SKILL1 if visible[min(frame[0], 6)] else task.I_SELECT_3)
        task.appear_then_click.return_value = True

        def screenshot():
            self.assertEqual(task.cnt_skillpower, 10)
            frame[0] += 1
            clock[0] += .2

        task.screenshot.side_effect = screenshot
        with patch('tasks.SixRealms_jue.moon_sea.skills.time.monotonic',
                   side_effect=lambda: clock[0]):
            self.assertTrue(task.select_strengthening())
        self.assertGreaterEqual(frame[0], 5)
        self.assertEqual(task.cnt_skillpower, 11)

    def test_popup_disappearance_without_destination_does_not_confirm(self):
        task = self.task()
        task.strengthening_appear = Mock(side_effect=[True] + [False] * 20)
        with patch('tasks.SixRealms_jue.moon_sea.skills.time.monotonic',
                   side_effect=range(30)):
            with self.assertRaises(GameStuckError):
                task.select_strengthening()
        self.assertEqual(task.cnt_skillpower, 10)

    def test_alternate_strengthening_does_not_increase_power(self):
        task = self.task()
        closed = False
        task.appear = lambda rule, **kw: rule == (task.I_SELECT_3 if closed else task.I_PEACOCK_SKILL2)
        task.appear_then_click.return_value = True

        def screenshot():
            nonlocal closed
            closed = True

        task.screenshot.side_effect = screenshot
        self.assertTrue(task.select_strengthening())
        task.appear_then_click.assert_called_once_with(task.I_PEACOCK_SKILL2, interval=1)
        self.assertEqual(task.cnt_skillpower, 10)

    def test_skill_page_and_unknown_page_never_click_island(self):
        for visible in ('I_SKILL_REFRESH', 'I_SHENMI'):
            task = self.task()
            task.appear.side_effect = lambda rule, **kw: rule.name == visible
            self.assertIsNone(task.enter_island())
            # 唯一允许检查的点击是原有取消弹窗，不能点击任何岛屿。
            self.assertTrue(all(call.args[0].name == 'I_CANCEL'
                                for call in task.appear_then_click.call_args_list))

    def test_map_entry_keeps_original_priority_and_confirms_departure(self):
        for power, expected in ((0, 'I_ZHAN'), (10, 'I_SHENMI')):
            task = self.task()
            task.cnt_skill101, task.cnt_skillpower = 0, power
            task.appear.side_effect = lambda rule, **kw: rule.name in ('I_SHENMI', 'I_ZHAN')
            task.in_main = Mock(side_effect=[True, True, False])
            task.appear_then_click.side_effect = lambda rule, **kw: rule.name != 'I_CANCEL'
            self.assertTrue(task.enter_island())
            self.assertEqual(task.appear_then_click.call_args.args[0].name, expected)

    def test_unresponsive_map_has_fixed_deadline_and_three_clicks(self):
        task = self.task()
        task.appear.side_effect = lambda rule, **kw: rule == task.I_SHENMI
        task.in_main = Mock(return_value=True)
        task.appear_then_click.side_effect = lambda rule, **kw: rule == task.I_SHENMI
        with patch('tasks.SixRealms_jue.moon_sea.map.monotonic', side_effect=range(30)):
            with self.assertRaisesRegex(GameStuckError, '进入岛屿'):
                task.enter_island()
        clicks = [call for call in task.appear_then_click.call_args_list
                  if call.args[0] == task.I_SHENMI]
        self.assertEqual(len(clicks), 3)

    def test_delayed_popup_interrupts_map_retry(self):
        task = self.task()
        task.in_main = Mock(return_value=True)
        task.strengthening_appear = Mock(side_effect=[False, True])
        self.assertTrue(task._enter_island(task.I_SHENMI))
        task.appear_then_click.assert_called_once_with(task.I_SHENMI, interval=1)


if __name__ == '__main__':
    unittest.main()
