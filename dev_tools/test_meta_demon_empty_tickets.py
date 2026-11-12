"""Recognize the user-confirmed empty summon queue without game input."""
import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np
from PIL import Image

from dev_tools import test_meta_demon as base


class EmptyTicketsTest(unittest.TestCase):
    def frame(self):
        path = Path(__file__).parent / 'fixtures' / 'meta_demon_empty_tickets.png'
        return np.array(Image.open(path).convert('RGB'))

    def test_actual_empty_panel_and_close_button_match(self):
        task = base.MetaDemonTest().task()
        frame = self.frame()
        for rule in [task.I_MD_EMPTY_TICKETS, task.I_MD_CLOSE_POPUP]:
            self.assertTrue(copy.deepcopy(rule).match(frame), rule.name)
        frame[410:455, 550:730] = 0
        self.assertFalse(copy.deepcopy(task.I_MD_EMPTY_TICKETS).match(frame))

    def test_confirmed_empty_panel_finishes_only_ordinary_run(self):
        for options in [{}, {'_summon_only': True}, {'_probe_only': True}]:
            with self.subTest(options=options):
                task = base.MetaDemonTest().task()
                state, clock = base.MetaDemonTest().replay(task, [(1001, set()), (1002, set())])
                task.device.image = self.frame()
                task.appear = Mock(side_effect=lambda rule, **kwargs: (
                    copy.deepcopy(rule).match(task.device.image)
                    if getattr(rule, 'name', '') in ['I_MD_EMPTY_TICKETS', 'I_MD_CLOSE_POPUP'] else False))
                task._close_boss_popup = Mock()
                task._try_friend_boss = Mock()
                with clock:
                    self.assertFalse(task.check_and_switch_ticket(**options))
                self.assertEqual(task.State.done, not options)
                self.assertTrue(task._tickets_checked)
                self.assertFalse(task.has_summon_ticket)
                task._close_boss_popup.assert_called_once()
                task._try_friend_boss.assert_not_called()
                self.assertEqual(state['clicks'], [])

    def test_transient_empty_message_does_not_finish(self):
        task = base.MetaDemonTest().task()
        task._close_boss_popup = Mock()
        task._classify_selected_ticket = Mock(return_value=None)
        task._refresh_current_boss_type = Mock()
        # A disappearing marker does not authorize an empty-queue finish.
        _, clock = base.MetaDemonTest().replay(task, [
            (1001, {'I_MD_EMPTY_TICKETS', 'I_MD_CLOSE_POPUP'}),
            (1002, {'I_MD_FIRE'})])
        with clock:
            self.assertTrue(task.check_and_switch_ticket())
        self.assertFalse(task.State.done)
        task._close_boss_popup.assert_not_called()

    def test_empty_popup_must_close_before_background_page_is_accepted(self):
        task = base.MetaDemonTest().task()
        state, clock = base.MetaDemonTest().replay(task, [
            (1001, {'I_MD_EMPTY_TICKETS', 'I_MD_CLOSE_POPUP'}), (1002, set())])
        task._boss_page_visible = Mock(return_value=True)
        with clock:
            task._close_boss_popup()
        self.assertEqual(state['clicks'], ['I_MD_CLOSE_POPUP'])


if __name__ == '__main__':
    unittest.main()
