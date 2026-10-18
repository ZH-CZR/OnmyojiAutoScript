"""Replay the experience task's real waiting/click path without a device."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import TaskEnd
from tasks.Component.Costume.config import TeamType
from tasks.ExperienceYoukai.script_task import ScriptTask


class ExperienceRoomTest(unittest.TestCase):
    def replay(self, scene, join_at=None, leave_before_click=False, buff=False):
        task = ScriptTask.__new__(ScriptTask)
        task.check_costume_team(scene)
        con = SimpleNamespace(buff_exp_50_click=buff, buff_exp_100_click=False)
        task.config = SimpleNamespace(experience_youkai=SimpleNamespace(
            switch_soul=SimpleNamespace(enable=False, enable_switch_by_name=False),
            experience_youkai=con))
        task.ui_goto_page = Mock()
        task.check_zones = Mock()
        task.ensure_public = Mock()
        task.create_ensure = Mock()
        task.exit_room = Mock()
        task.set_next_run = Mock()
        task.check_buff = Mock()
        task.run_general_battle = Mock()
        clock = [0.0]
        state = {'in_room': False, 'room_start': 0.0, 'clicks': []}

        class ReplayTimer:
            def __init__(self, seconds):
                self.seconds = seconds

            def start(self):
                self.started = clock[0]
                return self

            def reached(self):
                return clock[0] - self.started >= self.seconds

        def create():
            state.update(in_room=True, room_start=clock[0])
            task._room_animation_timer = None
            task._room_member_checks = {}
            return True

        def appear(asset, **kwargs):
            if not state['in_room']:
                return False
            if asset.name in ('I_GI_IN_ROOM', 'I_FIRE'):
                return True
            if asset.name == 'I_ADD_5_1':
                elapsed = clock[0] - state['room_start']
                # Initial room animation temporarily hides an empty seat.
                return elapsed >= 1 and (join_at is None or elapsed < join_at)
            return False

        def click(asset, **kwargs):
            if asset.name != 'I_FIRE':
                return False
            elapsed = clock[0] - state['room_start']
            self.assertIsNotNone(join_at, 'Empty room must never be started')
            self.assertGreaterEqual(elapsed, join_at)
            state['clicks'].append(elapsed)
            state['in_room'] = False
            return True

        original_click_fire = task.click_fire

        def recheck(*args, **kwargs):
            if leave_before_click:
                # A teammate leaves between the decision and the click screenshot.
                nonlocal join_at
                join_at = None
            return original_click_fire(*args, **kwargs)

        task.create_room = Mock(side_effect=create)
        task.screenshot = Mock(side_effect=lambda: clock.__setitem__(0, clock[0] + 0.2))
        task.appear = Mock(side_effect=appear)
        task.appear_then_click = Mock(side_effect=click)
        task.click_fire = Mock(side_effect=recheck)
        with patch('tasks.ExperienceYoukai.script_task.Timer', ReplayTimer), \
                patch('tasks.Component.GeneralInvite.general_invite.Timer', ReplayTimer), \
                patch('tasks.Component.GeneralInvite.general_invite.monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises(TaskEnd):
                task.run()
        return task, state

    def test_empty_room_and_animation_never_start_even_after_timeout(self):
        for scene in TeamType:
            with self.subTest(scene=scene):
                task, state = self.replay(scene, buff=True)
                self.assertEqual(state['clicks'], [])
                task.click_fire.assert_not_called()
                task.run_general_battle.assert_not_called()
                task.exit_room.assert_called_once()
                task.set_next_run.assert_called_once_with(
                    task='ExperienceYoukai', success=False, finish=False)
                self.assertEqual(task.check_buff.call_count, 2)

    def test_joined_member_starts_two_battles_and_finishes_successfully(self):
        for scene in TeamType:
            with self.subTest(scene=scene):
                task, state = self.replay(scene, join_at=6)
                self.assertEqual(len(state['clicks']), 2)
                self.assertEqual(task.run_general_battle.call_count, 2)
                task.set_next_run.assert_called_once_with(
                    task='ExperienceYoukai', success=True, finish=False)

    def test_member_leaving_before_click_does_not_start_or_count_battle(self):
        task, state = self.replay(TeamType.COSTUME_TEAM_1, join_at=6, leave_before_click=True)
        self.assertEqual(state['clicks'], [])
        task.run_general_battle.assert_not_called()
        task.set_next_run.assert_called_once_with(
            task='ExperienceYoukai', success=False, finish=False)


if __name__ == '__main__':
    unittest.main()
