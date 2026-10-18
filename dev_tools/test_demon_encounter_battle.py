"""Replay DemonEncounter waits with real Device timers, without game input."""
import unittest
from unittest.mock import Mock, patch

from module.base.timer import Timer
from module.device.device import Device
from module.exception import GameStuckError
from tasks.DemonEncounter.script_task import ScriptTask


class DemonEncounterBattleTest(unittest.TestCase):
    def replay(self, frames):
        task = ScriptTask.__new__(ScriptTask)
        device = Device.__new__(Device)
        task.device = device
        device.image = None
        device.detect_record = set()
        device.stuck_timer = Timer(60, count=60)
        device.stuck_timer_long = Timer(300, count=300)
        device.stuck_timer._current = device.stuck_timer_long._current = 1000
        device.click_record_clear = Mock()
        device.app_is_running = Mock(return_value=True)
        state = {'time': 1000, 'visible': set(), 'clicks': []}
        sequence = iter(frames)

        def screenshot():
            state['time'], state['visible'] = next(sequence)
            # Satisfy frame-count confirmation as well as elapsed seconds.
            device.stuck_timer._reach_count = 61
            device.stuck_timer_long._reach_count = 301
            device.stuck_record_check()

        def click(asset, **kwargs):
            if asset.name not in state['visible']:
                return False
            device.stuck_record_clear()  # Real device clicks clear wait markers.
            state['clicks'].append(asset.name)
            return True

        task.screenshot = Mock(side_effect=screenshot)
        task.appear = Mock(side_effect=lambda asset: asset.name in state['visible'])
        task.appear_then_click = Mock(side_effect=click)
        clock = patch('module.base.timer.time.time', side_effect=lambda: state['time'])
        return task, state, clock

    def test_prepare_clicks_keep_long_wait_until_victory_and_reward(self):
        task, state, clock = self.replay([
            (1000, {'I_PREPARE_HIGHLIGHT'}),
            (1002, {'I_PREPARE_HIGHLIGHT'}),
            (1063, set()),  # Original failure: 61 seconds after preparing.
            (1200, {'I_DE_WIN'}),
            (1201, {'I_REWARD'}),
            (1262, {'I_BOSS_GATHER'}),  # Reward click also clears the marker.
        ])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(state['clicks'], [
            'I_PREPARE_HIGHLIGHT', 'I_PREPARE_HIGHLIGHT', 'I_DE_WIN', 'I_REWARD'])
        self.assertEqual(task.device.detect_record, set())
        task.device.app_is_running.assert_not_called()

    def test_stuck_battle_still_times_out_after_long_limit(self):
        task, _, clock = self.replay([(1061, set()), (1301, set())])
        with clock, self.assertRaises(GameStuckError):
            task.battle_wait(False)
        self.assertNotIn('BATTLE_STATUS_S', task.device.detect_record)
        task.device.app_is_running.assert_called_once()

    def test_failure_click_restores_long_wait(self):
        task, state, clock = self.replay([
            (1000, {'I_FALSE'}), (1061, set()), (1062, {'I_DE_FIND'})])
        with clock:
            self.assertTrue(task.battle_wait(False))
        self.assertEqual(state['clicks'], ['I_FALSE'])
        self.assertEqual(task.device.detect_record, set())

    def test_normal_exit_removes_only_owned_marker(self):
        for end in ('I_DE_FIND', 'I_BATTLE_OVER'):
            with self.subTest(end=end):
                task, _, clock = self.replay([(1001, {end})])
                task.device.detect_record.add('OTHER_WAIT')
                with clock:
                    self.assertTrue(task.battle_wait(False))
                self.assertEqual(task.device.detect_record, {'OTHER_WAIT'})

    def test_exception_removes_battle_marker(self):
        task, _, clock = self.replay([])
        task.screenshot.side_effect = RuntimeError('capture failed')
        with clock, self.assertRaisesRegex(RuntimeError, 'capture failed'):
            task.battle_wait(False)
        self.assertEqual(task.device.detect_record, set())

    def test_next_page_uses_short_timeout_again(self):
        task, _, clock = self.replay([(1061, {'I_DE_FIND'})])
        with clock:
            self.assertTrue(task.battle_wait(False))
            with self.assertRaises(GameStuckError):
                task.device.stuck_record_check()

    def test_gather_exception_removes_battle_marker(self):
        task, _, clock = self.replay([])
        task.screenshot = Mock()
        task.appear.side_effect = lambda asset: asset.name in {'I_BOSS_FIRE', 'I_BOSS_GATHER'}
        task.O_DE_BOSS_PEOPLE = Mock()
        task.O_DE_BOSS_PEOPLE.ocr.return_value = (1, 299, 300)
        task.wait_until_disappear = Mock(side_effect=RuntimeError('gather failed'))
        with clock, patch('tasks.DemonEncounter.script_task.time.sleep'), \
                self.assertRaisesRegex(RuntimeError, 'gather failed'):
            task.execute_boss()
        self.assertEqual(task.device.detect_record, set())


if __name__ == '__main__':
    unittest.main()
