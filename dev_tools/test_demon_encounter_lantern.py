"""Offline chest entry replay; no device or game input."""
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.exception import GameStuckError
from tasks.DemonEncounter.script_task import ScriptTask


class DemonEncounterLanternTest(unittest.TestCase):
    def replay(self, frames):
        task = ScriptTask.__new__(ScriptTask)
        task.config = SimpleNamespace(demon_encounter=SimpleNamespace(
            switch_soul=SimpleNamespace(enable_100ap=False)))
        task.device = SimpleNamespace(image=None)
        task.ui_click_until_smt_disappear = Mock()
        state = {'time': 1000, 'visible': set(), 'clicks': []}
        sequence = iter(frames)

        def screenshot():
            state['time'], state['visible'] = next(sequence)

        def click(asset, **kwargs):
            state['clicks'].append((asset.name, tuple(asset.roi_front)))
            return True

        task.screenshot = Mock(side_effect=screenshot)
        task.appear = Mock(side_effect=lambda asset: asset.name in state['visible'])
        task.click = Mock(side_effect=click)
        task.appear_then_click = Mock(side_effect=lambda asset, **kw: (
            click(asset) if asset.name in state['visible'] else False))
        clock = patch('module.base.timer.time.time', side_effect=lambda: state['time'])
        return task, state, clock

    def test_click_uses_current_template_location_and_keeps_shared_asset(self):
        task, state, clock = self.replay([
            (1001, {'I_DE_BOX'}), (1002, {'I_JADE_50'}), (1003, set())])
        shared_front = list(task.I_DE_BOX.roi_front)
        shared_back = task.I_DE_BOX.roi_back
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        template = deepcopy(task.I_DE_BOX).image
        height, width = template.shape[:2]
        image[422:422 + height, 1203:1203 + width] = template
        # A second chest in another slot must not influence this entry.
        image[295:295 + height, 1210:1210 + width] = template
        task.device.image = image

        def appear(asset):
            if asset.name == 'I_DE_BOX':
                return asset.match(image)
            return asset.name in state['visible']

        task.appear.side_effect = appear
        with clock:
            task._box(task.C_DE_2)
        self.assertEqual(state['clicks'], [('I_DE_BOX', (1203, 422, width, height))])
        self.assertEqual(task.I_DE_BOX.roi_front, shared_front)
        self.assertEqual(task.I_DE_BOX.roi_back, shared_back)

    def test_unresponsive_chest_stops_after_three_clicks(self):
        task, state, clock = self.replay([
            (1001, {'I_DE_BOX'}), (1003, {'I_DE_BOX'}),
            (1005, {'I_DE_BOX'}), (1007, {'I_DE_BOX'}), (1016, {'I_DE_BOX'})])
        with clock, self.assertRaisesRegex(GameStuckError, 'de_2.*15秒.*3次'):
            task._box(task.C_DE_2)
        self.assertEqual(len(state['clicks']), 3)

    def test_missing_chest_never_clicks_old_fixed_area(self):
        task, state, clock = self.replay([(1001, set()), (1016, set())])
        with clock, self.assertRaisesRegex(GameStuckError, '0次'):
            task._box(task.C_DE_2)
        self.assertEqual(state['clicks'], [])

    def test_delayed_dialog_after_last_click_is_accepted(self):
        task, state, clock = self.replay([
            (1001, {'I_DE_BOX'}), (1003, {'I_DE_BOX'}), (1005, {'I_DE_BOX'}),
            (1007, set()), (1010, {'I_JADE_50'}), (1011, set())])
        with clock:
            task._box(task.C_DE_2)
        self.assertEqual(len(state['clicks']), 3)
        task.ui_click_until_smt_disappear.assert_called_once()

    def test_wrong_boss_page_recovery_is_also_bounded(self):
        task, state, clock = self.replay([
            (1001, {'I_BOSS_FIRE', 'I_BACK_RED'}),
            (1003, {'I_BOSS_FIRE', 'I_BACK_RED'}),
            (1005, {'I_BOSS_FIRE', 'I_BACK_RED'}),
            (1007, {'I_BOSS_FIRE', 'I_BACK_RED'}), (1016, set())])
        with clock, self.assertRaises(GameStuckError):
            task._box(task.C_DE_2)
        self.assertEqual([name for name, _ in state['clicks']], ['I_BACK_RED'] * 3)

    def test_capture_error_propagates(self):
        task, _, clock = self.replay([])
        task.screenshot.side_effect = RuntimeError('capture failed')
        with clock, self.assertRaisesRegex(RuntimeError, 'capture failed'):
            task._box(task.C_DE_2)


if __name__ == '__main__':
    unittest.main()
