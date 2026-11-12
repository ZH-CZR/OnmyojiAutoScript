"""组队副本选择回放：使用当前帧坐标，失败不得进入创建房间。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.atom.list import RuleList
from module.exception import GameStuckError
from module.ocr.common import BoxedResult
from tasks.ExperienceYoukai.script_task import ScriptTask


class TeamZoneSelectionTest(unittest.TestCase):
    def make_task(self, frames, select_on_click=True, selected=False):
        task = ScriptTask.__new__(ScriptTask)
        task.L_TEAM_LIST = RuleList(
            folder='unused', direction='vertical', mode='ocr',
            roi_back=(26, 106, 360, 549), size=(216, 61),
            array=['经验妖怪', '金币妖怪'])
        task.L_TEAM_LIST.target_check('经验妖怪')
        model = Mock()
        model.detect_and_ocr.side_effect = frames
        task.L_TEAM_LIST._target.__dict__['model'] = model
        task.list_find = Mock(return_value=(140, 360))  # 旧坐标此时已是金币妖怪
        state = {'time': 0, 'selected': selected}
        task.O_GR_ZONES_NAME = SimpleNamespace(
            keyword='', ocr=Mock(return_value='金币妖怪'))
        task.ocr_appear = Mock(side_effect=lambda _: state['selected'])
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))

        def click(**kwargs):
            if select_on_click:
                state['selected'] = True

        task.device.click = Mock(side_effect=click)
        task.screenshot = Mock(side_effect=lambda: state.update(time=state['time'] + 0.4))
        task.config = SimpleNamespace(experience_youkai=SimpleNamespace(
            switch_soul=SimpleNamespace(enable=False, enable_switch_by_name=False),
            experience_youkai=SimpleNamespace(buff_exp_50_click=False, buff_exp_100_click=False)))
        task.ui_goto_page = Mock()
        task.create_room = Mock()
        return task, state

    def box(self, y, text='经验妖怪'):
        return BoxedResult(np.array([[50, y], [150, y], [150, y + 30], [50, y + 30]]),
                           None, text, 0.99)

    def timers(self, state):
        class ReplayTimer:
            def __init__(self, seconds):
                self.seconds = seconds

            def start(self):
                self.started = state['time']
                return self

            reset = start

            def reached(self):
                return state['time'] - self.started >= self.seconds

        return patch('tasks.Component.GeneralRoom.general_room.Timer', ReplayTimer)

    def test_click_uses_current_ocr_box_and_roi_offset(self):
        task, state = self.make_task(lambda *_args, **_kwargs: [self.box(100)])
        with self.timers(state), patch('tasks.Component.GeneralRoom.general_room.randint', return_value=0):
            self.assertTrue(task.check_zones('经验妖怪'))
        task.device.click.assert_called_once_with(x=126, y=221)
        cropped = task.L_TEAM_LIST._target.model.detect_and_ocr.call_args.args[0]
        self.assertEqual(cropped.shape, (549, 360, 3))

    def test_each_retry_relocates_target_after_list_moves(self):
        task, state = self.make_task([[self.box(100)], [self.box(180)], [self.box(250)]], False)
        with self.timers(state), patch('tasks.Component.GeneralRoom.general_room.randint', return_value=0):
            with self.assertRaisesRegex(GameStuckError, '已点击3次'):
                task.run()
        self.assertEqual([c.kwargs['y'] for c in task.device.click.call_args_list], [221, 301, 371])
        task.create_room.assert_not_called()

    def test_empty_detection_waits_for_fresh_target_without_clicking_origin(self):
        task, state = self.make_task([[], [self.box(100)]])
        with self.timers(state):
            self.assertTrue(task.check_zones('经验妖怪'))
        self.assertEqual(task.device.click.call_count, 1)

    def test_no_target_or_invalid_coordinate_times_out_without_creating_room(self):
        for frames in (lambda *_a, **_k: [],
                       lambda *_a, **_k: [self.box(100, '金币妖怪')],
                       lambda *_a, **_k: [self.box(600)]):
            with self.subTest(frames=frames):
                task, state = self.make_task(frames)
                with self.timers(state):
                    with self.assertRaisesRegex(GameStuckError, '标题确认超时'):
                        task.run()
                task.device.click.assert_not_called()
                task.create_room.assert_not_called()

    def test_already_selected_needs_no_click(self):
        task, state = self.make_task([], selected=True)
        with self.timers(state):
            self.assertTrue(task.check_zones('经验妖怪'))
        task.device.click.assert_not_called()

    def test_search_failure_stops_task_before_room_creation(self):
        task, state = self.make_task([])
        task.list_find.return_value = False
        with self.assertRaisesRegex(GameStuckError, '未找到副本'):
            task.run()
        task.create_room.assert_not_called()


if __name__ == '__main__':
    unittest.main()
