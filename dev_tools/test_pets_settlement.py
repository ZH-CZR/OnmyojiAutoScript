"""宠物魂十结算与下一任务交接的离线回放，不连接设备。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import GameStuckError
from tasks.Orochi.config import Layer
from tasks.Pets.script_task import ScriptTask


class PetsSettlementTest(unittest.TestCase):
    def test_failed_pet_navigation_does_not_feed_battle_or_schedule(self):
        task = object.__new__(ScriptTask)
        task.ui_goto_page = Mock(return_value=False)
        task._feed = Mock()
        task.orochi_ten = Mock()
        task.set_next_run = Mock()
        with self.assertRaisesRegex(GameStuckError, '宠物屋导航失败'):
            task.run()
        task._feed.assert_not_called()
        task.orochi_ten.assert_not_called()
        task.set_next_run.assert_not_called()

    def test_failed_soul_navigation_does_not_enter_or_battle(self):
        task, state, timer = self.replay([])
        task.ui_goto_page.return_value = False
        with self.assertRaisesRegex(GameStuckError, '宠物魂十导航失败'):
            task.orochi_ten()
        task.orochi_enter.assert_not_called()
        task.run_general_battle.assert_not_called()

    def replay(self, frames):
        task = object.__new__(ScriptTask)
        battle_config = SimpleNamespace(lock_team_enable=False)
        task.config = SimpleNamespace(orochi=SimpleNamespace(
            switch_soul=SimpleNamespace(enable=False), general_battle_config=battle_config))
        task.current_count = 0
        clock = [0.0]
        state = {'battle': False, 'frame': 'challenge', 'index': 0, 'clicks': []}

        class ReplayTimer:
            def __init__(self, limit, count=0):
                self.limit, self.count = limit, count
                self.reset()

            def reset(self):
                self.since, self.checks = clock[0], 0
                return self

            start = reset

            def reached(self):
                self.checks += 1
                return clock[0] - self.since > self.limit and self.checks > self.count

        def screenshot():
            clock[0] += 0.25
            if state['battle']:
                index = state['index']
                state['frame'] = frames[min(index, len(frames) - 1)]
                state['index'] += 1

        def appear(asset, **kwargs):
            return (asset.name, state['frame']) in {
                ('I_COMMON_FIRE', 'challenge'), ('I_PET_PRESENT', 'pet'),
                ('I_REWARD', 'reward')}

        def click(asset, **kwargs):
            if not appear(asset):
                return False
            state['clicks'].append(asset.name)
            return True

        def battle(**kwargs):
            task.current_count += 1
            state['battle'] = True

        task.screenshot = Mock(side_effect=screenshot)
        task.appear = Mock(side_effect=appear)
        task.appear_then_click = Mock(side_effect=click)
        task.save_image = Mock()
        task.ui_goto_page = Mock()
        task.orochi_enter = Mock()
        task.check_layer = Mock()
        task.check_lock = Mock()
        task.ui_click_until_disappear = Mock()
        task.run_general_battle = Mock(side_effect=battle)
        task.get_random_reward_action = Mock(return_value='reward-click')
        return task, state, patch('tasks.Pets.script_task.Timer', ReplayTimer)

    def test_delayed_treasure_is_collected_before_handoff(self):
        task, state, timer = self.replay(
            ['animation'] * 4 + ['pet'] * 2 + ['reward'] * 2 + ['challenge'])
        with timer:
            task.orochi_ten()
        self.assertEqual(state['frame'], 'challenge')
        self.assertIn('I_PET_PRESENT', state['clicks'])
        self.assertIn('I_REWARD', state['clicks'])
        task.run_general_battle.assert_called_once()
        task.ui_click_until_disappear.assert_called_once_with(task.I_COMMON_FIRE)
        task.check_layer.assert_called_once_with(task.L_LAYER_LIST, Layer.TEN)

    def test_no_treasure_still_waits_for_stable_challenge(self):
        task, state, timer = self.replay(
            ['challenge', 'animation', 'animation', 'challenge'])
        with timer:
            task.orochi_ten()
        self.assertGreaterEqual(state['index'], 8)
        self.assertEqual(state['clicks'], [])
        task.run_general_battle.assert_called_once()

    def test_unfinished_settlement_times_out_in_pets(self):
        for frame in ('animation', 'pet', 'reward'):
            with self.subTest(frame=frame):
                task, state, timer = self.replay([frame])
                with timer, self.assertRaises(GameStuckError):
                    task.orochi_ten()
                task.run_general_battle.assert_called_once()
                self.assertGreaterEqual(state['index'], 120)


if __name__ == '__main__':
    unittest.main()
