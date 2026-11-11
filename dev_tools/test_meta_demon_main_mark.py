"""Top portrait marking and explicit confirmation, without a game/device."""
import copy
import unittest
from unittest.mock import Mock

import numpy as np

from dev_tools import test_meta_demon as base
from module.exception import GameStuckError


class MainMarkTest(unittest.TestCase):
    def task(self, frames):
        task = base.MetaDemonTest().task()
        state, clock = base.MetaDemonTest().replay(task, frames)
        task.is_in_prepare = Mock(side_effect=lambda *_: 'PREPARE' in state['visible'])
        return task, state, clock

    def test_disabled_never_clicks(self):
        task, _, _ = self.task([])
        task.green_mark(False)
        task.screenshot.assert_not_called()
        task.click.assert_not_called()

    def test_clicks_top_portrait_and_confirms_label(self):
        task, _, clock = self.task([(1001, {'BATTLE'}),
                                    (1002, {'BATTLE', 'I_MD_MAIN_MARKED'})])
        with clock:
            self.assertTrue(task.green_mark(True))
        task.click.assert_called_once_with(task.C_MD_MARK_MAIN)
        x, y, w, h = task.C_MD_MARK_MAIN.roi_front
        self.assertTrue(386 < x < x + w < 423)
        self.assertTrue(16 < y < y + h < 53)

    def test_already_marked_does_not_toggle(self):
        task, _, clock = self.task([(1001, {'BATTLE', 'I_MD_MAIN_MARKED'})])
        with clock:
            self.assertTrue(task.green_mark(True))
        task.click.assert_not_called()

    def test_delayed_confirmation_never_reclicks(self):
        task, _, clock = self.task([(1001, {'BATTLE'}), (1005, {'BATTLE'}),
                                    (1010, {'BATTLE', 'I_MD_MAIN_MARKED'})])
        with clock:
            self.assertTrue(task.green_mark(True))
        task.click.assert_called_once_with(task.C_MD_MARK_MAIN)

    def test_unconfirmed_mark_times_out_without_reclick(self):
        task, _, clock = self.task([(1001, {'BATTLE'}), (1010, {'BATTLE'}),
                                    (1016, {'BATTLE'})])
        with clock, self.assertRaises(GameStuckError):
            task.green_mark(True)
        task.click.assert_called_once_with(task.C_MD_MARK_MAIN)

    def test_prepare_and_transition_do_not_click(self):
        task, _, clock = self.task([(1001, {'PREPARE', 'BATTLE'}), (1002, set()),
                                    (1003, {'BATTLE'}), (1004, {'BATTLE', 'I_MD_MAIN_MARKED'})])
        with clock:
            self.assertTrue(task.green_mark(True))
        task.click.assert_called_once_with(task.C_MD_MARK_MAIN)

    def test_battle_end_skips_mark_and_does_not_click_rewards(self):
        for ending in ['I_WIN', 'I_FALSE', 'I_MD_CURRENT_SUMMON']:
            task, _, clock = self.task([(1001, {ending, 'BATTLE'})])
            with clock:
                self.assertFalse(task.green_mark(True))
            task.click.assert_not_called()

    def test_label_template_matches_only_top_region(self):
        task, _, _ = self.task([])
        rule = copy.copy(task.I_MD_MAIN_MARKED)
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertFalse(rule.match(image))
        image[49:60, 383:424] = rule.image
        self.assertTrue(rule.match(image))
        image[49:60, 383:424] = 0
        image[400:411, 383:424] = rule.image
        self.assertFalse(rule.match(image))


if __name__ == '__main__':
    unittest.main()
