"""福利寮离馆后跳过15分钟限制，普通道馆保持原规则；不操作游戏。"""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import TaskEnd
from tasks.Dokan.config import Dokan
from tasks.Dokan.script_task import DokanScene, ScriptTask


class DokanIntervalTests(unittest.TestCase):
    def make_task(self, welfare, elapsed=10, offline=False):
        task = object.__new__(ScriptTask)
        task.config = SimpleNamespace(dokan=Dokan(
            welfare_config={'offline_battle_enable': offline}))
        task.open_welfare = welfare
        task.team_switched = True
        task.dokan_battle_number = 2
        task.first_open_dokan_time = datetime.now() - timedelta(minutes=elapsed)
        task.set_next_run = Mock()
        task.finish_task = Mock(side_effect=TaskEnd)
        task.goto_dokan = Mock(side_effect=TaskEnd)
        task.get_current_scene = Mock(return_value=(False, DokanScene.RYOU_DOKAN_RYOU))
        return task

    def test_welfare_bypasses_interval_with_or_without_offline_mode(self):
        for offline in (False, True):
            task = self.make_task(True, offline=offline)
            with self.assertRaises(TaskEnd):
                task.dokan_process(task.config.dokan)
            task.goto_dokan.assert_called_once_with()
            task.set_next_run.assert_not_called()
            task.finish_task.assert_not_called()
            self.assertFalse(task.open_welfare)  # 下一场需要重新识别，不能继承豁免。
            self.assertFalse(task.team_switched)

    def test_welfare_waits_for_actual_exit_before_selecting_next(self):
        task = self.make_task(True)
        events = []
        frames = iter([(True, DokanScene.RYOU_DOKAN_SCENE_GATHERING),
                       (True, DokanScene.RYOU_DOKAN_SCENE_UNKNOWN),
                       (False, DokanScene.RYOU_DOKAN_SCENE_FINDING_DOKAN)])

        def scene():
            result = next(frames)
            events.append('inside' if result[0] else 'closed')
            task.goto_dokan.assert_not_called()
            return result

        def goto():
            events.append('next')
            raise TaskEnd

        task.get_current_scene.side_effect = scene
        task.goto_dokan.side_effect = goto
        with self.assertRaises(TaskEnd):
            task.dokan_process(task.config.dokan)
        self.assertEqual(events, ['inside', 'inside', 'closed', 'next'])
        task.set_next_run.assert_not_called()

    def run_boss_waiting(self, task):
        task.get_current_scene = Mock(side_effect=[
            (True, DokanScene.RYOU_DOKAN_SCENE_BOSS_WAITING), TaskEnd])
        task.screenshot = Mock()
        # 发起放弃 -> 确认 -> 等待再战/投票页面；没有提前假定已离馆。
        task.appear = Mock(side_effect=lambda target, **kwargs:
                           target is task.I_CONTINUE_DOKAN
                           and task.appear_then_click.call_count >= 2)
        task.appear_then_click = Mock(side_effect=lambda target, **kwargs:
                                      target is task.I_QUIT_DOKAN
                                      or (target is task.I_DOKAN_QUIT_CONFIRM
                                          and task.appear_then_click.call_count >= 2))
        with patch('tasks.Dokan.script_task.time.sleep') as sleep:
            with self.assertRaises(TaskEnd):
                task.dokan_process(task.config.dokan)
        return sleep

    def test_welfare_quits_boss_without_delay_for_each_count_and_offline_mode(self):
        for count in (1, 2):
            for offline in (False, True):
                with self.subTest(count=count, offline=offline):
                    task = self.make_task(True, offline=offline)
                    task.config.dokan.dokan_config.dokan_enable = True
                    task.config.dokan.dokan_config.dokan_battle_count = count
                    task.dokan_quit = False  # 包括第二场或重新加入的福利寮。
                    sleep = self.run_boss_waiting(task)
                    sleep.assert_not_called()
                    clicks = [call.args[0] for call in task.appear_then_click.call_args_list]
                    self.assertIn(task.I_QUIT_DOKAN, clicks)
                    self.assertIn(task.I_DOKAN_QUIT_CONFIRM, clicks)
                    task.goto_dokan.assert_not_called()

    def test_normal_single_battle_does_not_quit_boss(self):
        task = self.make_task(False)
        task.config.dokan.dokan_config.dokan_enable = True
        task.config.dokan.dokan_config.dokan_battle_count = 1
        task.dokan_quit = True
        sleep = self.run_boss_waiting(task)
        sleep.assert_not_called()
        task.appear_then_click.assert_called_once_with(task.I_CROWD_QUIT_DOKAN, interval=1)

    def test_normal_first_battle_preserves_quit_and_delay(self):
        task = self.make_task(False)
        task.config.dokan.dokan_config.dokan_enable = True
        task.dokan_quit = True
        sleep = self.run_boss_waiting(task)
        sleep.assert_called_once_with(5)
        self.assertTrue(any(call.args[0] is task.I_QUIT_DOKAN
                            for call in task.appear_then_click.call_args_list))

    def test_welfare_member_agrees_to_quit_without_management_clicks(self):
        task = self.make_task(True)
        sleep = self.run_boss_waiting(task)
        sleep.assert_not_called()
        task.appear_then_click.assert_called_once_with(task.I_CROWD_QUIT_DOKAN, interval=1)

    def test_normal_guild_still_waits_until_fifteen_minutes(self):
        task = self.make_task(False)
        with self.assertRaises(TaskEnd):
            task.dokan_process(task.config.dokan)
        task.set_next_run.assert_called_once_with(
            target=task.first_open_dokan_time + timedelta(minutes=15))
        task.goto_dokan.assert_not_called()

    def test_normal_guild_continues_after_fifteen_minutes(self):
        task = self.make_task(False, elapsed=16)
        with self.assertRaises(TaskEnd):
            task.dokan_process(task.config.dokan)
        task.goto_dokan.assert_called_once_with()
        task.set_next_run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
