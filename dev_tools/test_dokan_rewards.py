"""道馆奖励点击区域与结算等待回归，不连接设备。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import GameStuckError
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Dokan.config import Dokan
from tasks.Dokan.script_task import DokanScene, ScriptTask


class DokanRewardTests(unittest.TestCase):
    def make_task(self, frames):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(dokan=Dokan())
        task.device = Mock()
        task.team_switched = True
        task.open_welfare = False
        task.save_image = Mock()
        state = [None]
        iterator = iter(frames)
        task.screenshot = Mock(side_effect=lambda: state.__setitem__(0, next(iterator)))
        task.appear = Mock(side_effect=lambda target, *args, **kwargs: target is state[0])
        task.appear_then_click = Mock(return_value=True)
        task.last_scene = None
        return task

    def test_gold_tooltip_and_following_soul_reward_use_continue_area(self):
        gold, soul = GeneralBattle.I_REWARD_GOLD, ScriptTask.I_REWARD
        task = self.make_task([gold, gold, None, soul, None, None])
        with patch('tasks.Dokan.script_task.time.sleep') as sleep:
            task.collect_dokan_rewards()
        self.assertEqual(task.screenshot.call_count, 6)
        self.assertEqual(task.appear_then_click.call_count, 3)
        for call in task.appear_then_click.call_args_list:
            self.assertIs(call.kwargs['action'], task.C_REWARD_BOTTOM)
            self.assertEqual(call.kwargs['interval'], 1)
        self.assertEqual(sleep.call_count, 2)
        task.device.click_record_clear.assert_not_called()
        task.device.stuck_record_clear.assert_not_called()

    def test_reward_stuck_has_fixed_deadline(self):
        task = self.make_task([GeneralBattle.I_REWARD_GOLD] * 4)
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=[0, 1, 20, 30]):
            with self.assertRaisesRegex(GameStuckError, '道馆领奖超过30秒'):
                task.collect_dokan_rewards()
        self.assertEqual(task.appear_then_click.call_count, 2)

    def test_device_errors_propagate(self):
        task = self.make_task([GeneralBattle.I_REWARD_GOLD])
        task.screenshot.side_effect = GameStuckError('device watchdog')
        with self.assertRaisesRegex(GameStuckError, 'device watchdog'):
            task.collect_dokan_rewards()

    def test_outer_scene_and_inner_battle_both_collect_gold_and_soul(self):
        for target in (GeneralBattle.I_REWARD_GOLD, ScriptTask.I_REWARD):
            for outer in (True, False):
                with self.subTest(target=target.name, outer=outer):
                    task = self.make_task([target])
                    task.collect_dokan_rewards = Mock()
                    if outer:
                        self.assertEqual(task.get_current_scene(),
                                         (True, DokanScene.RYOU_DOKAN_SCENE_BATTLE_OVER))
                    else:
                        task.dokan_battle(task.config.dokan)
                    task.collect_dokan_rewards.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
