"""Replay room transitions without ADB, sleeps, or running game tasks."""
import unittest
from unittest.mock import Mock, patch

from tasks.Component.GeneralInvite.general_invite import GeneralInvite, RoomType


class RoomOccupancyTests(unittest.TestCase):
    def setUp(self):
        self.task = GeneralInvite.__new__(GeneralInvite)
        self.visible = {'I_GI_IN_ROOM', 'I_FIRE'}
        self.task.appear = Mock(side_effect=lambda asset, **kwargs: asset.name in self.visible)
        self.task.appear_rgb = Mock(side_effect=lambda asset: asset.name in self.visible)
        self.task.screenshot = Mock()
        self.task.appear_then_click = Mock(return_value=False)
        self.animation = Mock()
        self.animation.start.return_value = self.animation
        self.animation.reached.return_value = True
        self.clock = 0.0
        self.timer_patch = patch('tasks.Component.GeneralInvite.general_invite.Timer', return_value=self.animation)
        self.clock_patch = patch('tasks.Component.GeneralInvite.general_invite.monotonic', side_effect=lambda: self.clock)
        self.timer_patch.start()
        self.clock_patch.start()
        self.addCleanup(self.timer_patch.stop)
        self.addCleanup(self.clock_patch.stop)

    def observe(self, time, room=RoomType.NORMAL_5, required=1):
        self.clock = time
        return self.task.room_has_members(room, required)

    def calibrate(self, *names):
        self.visible.update(names)
        self.task.is_in_room(False)
        self.visible.difference_update(names)

    def test_creation_animation_missing_plus_does_not_mean_someone_joined(self):
        self.calibrate('I_ADD_5_1')
        self.animation.reached.return_value = False
        for time in (0.1, 0.9, 1.5, 2.5):
            self.assertFalse(self.observe(time))
        self.task.appear_then_click.assert_not_called()

    def test_empty_room_never_confirms_member(self):
        self.visible.add('I_ADD_5_1')
        for time in (0, 1, 2, 4, 8):
            self.assertFalse(self.observe(time))

    def test_immediate_join_or_initially_full_room_does_not_require_empty_history(self):
        self.assertFalse(self.observe(0))
        self.assertFalse(self.observe(0.1))
        self.assertTrue(self.observe(0.31))
        self.task.appear.assert_any_call(self.task.I_FIRE, threshold=0.7)

    def test_one_missing_observation_is_discarded_when_empty_slot_returns(self):
        self.assertFalse(self.observe(0))
        self.visible.add('I_ADD_5_1')
        self.assertFalse(self.observe(0.1))
        self.visible.remove('I_ADD_5_1')
        self.assertFalse(self.observe(0.31))
        self.assertTrue(self.observe(0.62))

    def test_initially_full_room_reaches_the_real_click_guard(self):
        self.assertFalse(self.observe(0))
        self.assertTrue(self.observe(0.31))
        def click(*args, **kwargs):
            self.visible.remove('I_GI_IN_ROOM')
            return True
        self.task.appear_then_click.side_effect = click
        self.assertTrue(self.task.click_fire(RoomType.NORMAL_5))
        self.task.appear_then_click.assert_called_once_with(
            self.task.I_FIRE, interval=1, threshold=0.7)

    def test_stable_missing_plus_after_calibration_confirms_member(self):
        self.calibrate('I_ADD_5_1')
        self.assertFalse(self.observe(0))
        self.assertTrue(self.observe(0.6))
        self.assertTrue(self.observe(1.3))

    def test_empty_slot_reappearing_cancels_transient_missing_detection(self):
        self.calibrate('I_ADD_5_1')
        self.assertFalse(self.observe(0))
        self.assertTrue(self.observe(0.7))
        self.visible.add('I_ADD_5_1')
        self.assertFalse(self.observe(1.4))
        self.visible.remove('I_ADD_5_1')
        self.assertFalse(self.observe(1.5))
        self.assertTrue(self.observe(2.1))
        self.assertTrue(self.observe(2.8))

    def test_two_member_configuration_requires_both_seats_occupied(self):
        self.calibrate('I_ADD_1', 'I_ADD_2')
        self.visible.add('I_ADD_1')
        for time in (0, 0.6, 1.3):
            self.assertFalse(self.observe(time, RoomType.NORMAL_3, 2))
        self.visible.remove('I_ADD_1')
        self.assertFalse(self.observe(2, RoomType.NORMAL_3, 2))
        self.assertTrue(self.observe(2.6, RoomType.NORMAL_3, 2))
        self.assertTrue(self.observe(3.3, RoomType.NORMAL_3, 2))

    def test_room_or_fire_marker_loss_cancels_confirmation(self):
        self.calibrate('I_ADD_5_1')
        self.assertFalse(self.observe(0))
        self.visible.remove('I_FIRE')
        self.assertFalse(self.observe(1.3))
        self.visible.add('I_FIRE')
        self.assertFalse(self.observe(1.4))
        self.visible.remove('I_GI_IN_ROOM')
        self.assertFalse(self.observe(2.7))
        self.visible.add('I_GI_IN_ROOM')
        self.assertFalse(self.observe(3))
        self.assertTrue(self.observe(3.6))
        self.assertTrue(self.observe(4.3))

    def test_full_room_after_battle_reconfirms_without_requiring_teammates_to_leave(self):
        self.calibrate('I_ADD_5_1')
        for time in (0, 0.6, 1.3):
            self.observe(time)
        self.visible.remove('I_GI_IN_ROOM')
        self.assertFalse(self.observe(2))
        self.visible.add('I_GI_IN_ROOM')
        self.animation.reached.return_value = False
        self.assertFalse(self.observe(3))
        self.animation.reached.return_value = True
        self.assertFalse(self.observe(6))
        self.assertTrue(self.observe(6.6))
        self.assertTrue(self.observe(7.3))

    def test_switching_scene_restarts_consecutive_observations(self):
        from tasks.Component.Costume.config import TeamType
        self.assertFalse(self.observe(0))
        self.assertTrue(self.observe(0.6))
        self.task.check_costume_team(TeamType.COSTUME_TEAM_2)
        self.assertFalse(self.task._room_member_checks)
        self.assertFalse(self.observe(1))
        self.assertTrue(self.observe(1.4))

    def test_click_rechecks_occupancy_and_does_not_use_previous_decision(self):
        self.calibrate('I_ADD_5_1')
        for time in (0, 0.6, 1.3):
            self.observe(time)
        self.visible.add('I_ADD_5_1')
        self.assertFalse(self.task.click_fire(RoomType.NORMAL_5))
        self.task.appear_then_click.assert_not_called()

    def test_two_person_room_accepts_either_empty_slot_variant(self):
        self.calibrate('I_ADD_2')
        self.visible.add('I_ADD_1')
        for time in (0, 0.6, 1.3):
            self.assertFalse(self.observe(time, RoomType.NORMAL_2))

    def test_room_marker_disappearance_before_click_is_not_a_started_battle(self):
        self.visible.remove('I_GI_IN_ROOM')
        self.assertFalse(self.task.click_fire(RoomType.NORMAL_5))
        self.task.appear_then_click.assert_not_called()

    def test_confirmed_click_followed_by_room_exit_reports_started_battle(self):
        self.task.is_in_room = Mock(side_effect=[True, False])
        self.task._room_animation_timer = self.animation
        self.task.room_has_members = Mock(return_value=True)
        self.task.appear_then_click.return_value = True
        self.assertTrue(self.task.click_fire(RoomType.NORMAL_5))
        self.task.appear_then_click.assert_called_once()


if __name__ == '__main__':
    unittest.main()
