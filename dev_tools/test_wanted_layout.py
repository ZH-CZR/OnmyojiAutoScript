"""用户新版面板局部截图回放，不连接设备或 OCR 服务。"""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, call

import cv2
import numpy as np

from tasks.WantedQuests.assets import WantedQuestsAssets as Assets
from dev_tools.test_wanted_ui import make_task
from tasks.GameUi.page import page_exploration


FIXTURES = Path(__file__).parent / 'fixtures' / 'wanted_layout'


class WantedLayoutTest(unittest.TestCase):
    def canvas(self, actions):
        image = np.full((720, 1280, 3), 90, dtype=np.uint8)
        for name, x, y in [('panel_title', 566, 30), (actions, 1015, 578)]:
            patch = cv2.cvtColor(cv2.imread(str(FIXTURES / (name + '.png'))), cv2.COLOR_BGR2RGB)
            h, w = patch.shape[:2]
            image[y:y+h, x:x+w] = patch
        return image

    def test_untracked_panel_is_recognized_without_exploration_button(self):
        image = self.canvas('untracked_actions')
        self.assertTrue(deepcopy(Assets.I_WQ_PANEL).match(image))
        self.assertTrue(deepcopy(Assets.I_TRACE_ENABLE).match(image))
        self.assertFalse(deepcopy(Assets.I_TARCE_DISENABLE).match(image))
        self.assertFalse(deepcopy(Assets.I_WQ_GOTO_EXPLORATION).match(image))

    def test_tracked_panel_can_navigate_instead_of_being_treated_as_complete(self):
        image = self.canvas('tracked_actions')
        self.assertTrue(deepcopy(Assets.I_WQ_PANEL).match(image))
        self.assertFalse(deepcopy(Assets.I_TRACE_ENABLE).match(image))
        self.assertTrue(deepcopy(Assets.I_TARCE_DISENABLE).match(image))
        goto = deepcopy(Assets.I_WQ_GOTO_EXPLORATION)
        self.assertTrue(goto.match(image))
        self.assertEqual(goto.roi_front[:2], [1031, 633])
        for _ in range(100):
            x, y = goto.coord()
            self.assertTrue(1031 <= x <= 1124 and 633 <= y <= 710)

    def test_missing_title_is_not_a_confirmed_panel(self):
        image = self.canvas('tracked_actions')
        image[30:96, 566:719] = 90
        self.assertFalse(deepcopy(Assets.I_WQ_PANEL).match(image))

    def test_real_panel_frames_track_and_confirm_navigation(self):
        task = make_task()
        task.play_count = 0
        image = self.canvas('untracked_actions')
        arrived = False

        def appear(rule):
            if arrived:
                return rule is page_exploration.check_button
            return rule.match(image)

        def click(rule, **kwargs):
            nonlocal image, arrived
            if rule is task.I_TRACE_ENABLE:
                image = self.canvas('tracked_actions')
            elif rule is task.I_WQ_GOTO_EXPLORATION:
                arrived = True
            return True

        task.appear = Mock(side_effect=appear)
        task.click.side_effect = click
        task.appear_then_click = lambda rule, **kwargs: appear(rule) and task.click(rule, **kwargs)
        task.ui_goto_page = Mock()
        self.assertTrue(task.pre_work())
        self.assertEqual(task.click.call_args_list, [call(task.I_TRACE_ENABLE, interval=3),
                                                   call(task.I_WQ_GOTO_EXPLORATION, interval=1)])
        self.assertIs(task.ui_current, page_exploration)
        task.ui_goto_page.assert_not_called()


if __name__ == '__main__':
    unittest.main()
