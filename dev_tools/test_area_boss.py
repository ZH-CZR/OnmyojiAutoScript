"""地域鬼王数量与战斗场次分离的离线回归，不连接设备。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from module.exception import TaskEnd
from tasks.AreaBoss.config_boss import Boss
from tasks.AreaBoss.script_task import ScriptTask


class AreaBossCountTest(unittest.TestCase):
    def task(self, reward=False, number=3):
        task = object.__new__(ScriptTask)
        task.current_count = 0
        task.config = SimpleNamespace(area_boss=SimpleNamespace(
            scheduler=SimpleNamespace(execution_mode='手动执行'),
            boss=Boss(boss_reward=reward, boss_number=number),
            general_battle=SimpleNamespace(lock_team_enable=True),
            switch_soul=SimpleNamespace(enable=False, enable_switch_by_name=False)))
        for name in ('ui_goto_page', 'switch_to_famous', 'switch_to_collect',
                     'set_next_run', 'push_notify'):
            setattr(task, name, Mock())
        return task

    def run_task(self, task):
        with self.assertRaises(TaskEnd):
            task.run()

    def test_reward_with_two_battles_counts_as_one_boss(self):
        task = self.task(reward=True)

        def reward():
            task.current_count += 2  # 同一鬼王普通60级解锁后再打极地鬼
            return True

        def fight(*args, **kwargs):
            task.current_count += 1
            return True

        task.fight_reward_boss = Mock(side_effect=reward)
        task.boss_fight = Mock(side_effect=fight)
        self.run_task(task)
        self.assertEqual(task.boss_fight.call_count, 2)
        self.assertEqual(task.current_count, 4)
        task.push_notify.assert_not_called()

    def test_reward_also_in_popular_list_is_not_counted_twice(self):
        task = self.task(reward=True)
        task.fight_reward_boss = Mock(return_value=True)
        task.boss_fight = Mock(side_effect=[False, True, True])
        self.run_task(task)
        self.assertEqual(task.boss_fight.call_count, 3)
        task.push_notify.assert_not_called()

    def test_failed_battle_does_not_hide_shortfall(self):
        task = self.task()

        def fight(*args, **kwargs):
            task.current_count += 1
            return task.current_count != 2

        task.boss_fight = Mock(side_effect=fight)
        self.run_task(task)
        task.push_notify.assert_called_once()
        self.assertIn('数量2小于要求数量3', task.push_notify.call_args.kwargs['content'])

    def test_without_reward_fights_three_candidates(self):
        task = self.task()
        task.boss_fight = Mock(return_value=True)
        self.run_task(task)
        self.assertEqual(task.boss_fight.call_count, 3)
        task.push_notify.assert_not_called()

    def test_configured_two_stops_after_two_successes(self):
        task = self.task(number=2)
        task.boss_fight = Mock(return_value=True)
        self.run_task(task)
        self.assertEqual(task.boss_fight.call_count, 2)

    def test_existing_rank_is_not_a_new_success(self):
        task = self.task()
        task.screenshot = Mock()
        task.appear = Mock(return_value=True)
        task.open_boss_detail = Mock(return_value=True)
        task.wait_until_appear = Mock(return_value=False)
        task.ui_click_until_disappear = Mock()
        task.start_fight = Mock()
        self.assertFalse(task.boss_fight(task.I_BATTLE_1))
        task.start_fight.assert_not_called()

    def test_reward_unlock_and_ultra_share_one_completion(self):
        task = self.task(reward=True)
        task.config.area_boss.boss.attack_60 = True
        task.screenshot = Mock()
        task.appear = Mock(side_effect=lambda asset: asset == task.I_AB_FILTER_OPENED)
        task.open_boss_detail = Mock(return_value=True)
        task.wait_until_appear = Mock(return_value=True)
        task.get_difficulty = Mock(return_value=False)
        task.switch_to_level_60 = Mock()
        task.switch_difficulty = Mock()
        task.switch_to_floor_1 = Mock()
        task.ui_click_until_disappear = Mock()
        task.start_fight = Mock(side_effect=[True, True])
        self.assertTrue(task.boss_fight(task.I_BATTLE_1, ultra=True))
        self.assertEqual(task.start_fight.call_count, 2)


if __name__ == '__main__':
    unittest.main()
