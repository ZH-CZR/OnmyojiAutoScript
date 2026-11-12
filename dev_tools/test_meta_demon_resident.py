"""Post-completion residency and scheduler handoff, without game input."""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from dev_tools import test_meta_demon as base
from dev_tools import test_meta_demon_friend_assist as friends
from module.config.config import Config
from module.exception import GameStuckError, TaskEnd
from module.script import ScriptRuntimeController, ScriptRuntimeDecision
from script import Script
from tasks.MetaDemon.config import BossType


class ResidentTest(unittest.TestCase):
    def task(self, pending=False):
        task = base.MetaDemonTest().task()
        task.conf.scheduler.enable = True
        task._friend_active = False
        task._friend_settlement_pending = False
        task._resident_mode = True
        task.config.reload = Mock()
        task.config.update_scheduler = Mock()
        task.config.normal_pending_task = [SimpleNamespace(command='Pets')] if pending else []
        task.config.pending_task = []
        task.device.activity_guard = None
        task.device.stuck_record_clear = Mock()
        task.screenshot = Mock()
        task.appear = Mock(return_value=False)
        task._enter_boss_page = Mock(side_effect=AssertionError("must not navigate"))
        task._boss_page_visible = Mock(return_value=True)
        task._read_fatigue = Mock(return_value=(0, 100))
        task._try_friend_boss = Mock(return_value=None)
        task.check_and_switch_ticket = Mock()
        task.check_and_synthesize = Mock()
        return task

    def test_completed_enabled_task_stays_on_event_without_navigation(self):
        task = self.task()
        task._resident_mode = False
        with self.assertRaises(TaskEnd):
            task.finish_task()
        self.assertTrue(task.config.meta_demon_residency_requested)
        task.ui_goto_page.assert_not_called()

    def test_completed_disabled_task_also_preserves_current_page(self):
        task = self.task()
        task._resident_mode = False
        task.conf.scheduler.enable = False
        with self.assertRaises(TaskEnd):
            task.finish_task()
        task.ui_goto_page.assert_not_called()

    def test_manual_leave_pauses_scan_and_manual_return_resumes(self):
        task = self.task()
        task._boss_page_visible.side_effect = [True, False, True]
        with patch('tasks.MetaDemon.resident.time.sleep', side_effect=[None, None, TaskEnd]):
            with self.assertRaises(TaskEnd):
                task._resident_loop()
        self.assertEqual(task._try_friend_boss.call_count, 2)
        self.assertEqual(task._read_fatigue.call_count, 2)
        task._enter_boss_page.assert_not_called()
        task.ui_goto_page.assert_not_called()

    def test_other_page_waits_without_reading_fatigue_or_clicking(self):
        task = self.task()
        task._boss_page_visible.return_value = False
        with patch('tasks.MetaDemon.resident.time.sleep', side_effect=TaskEnd):
            with self.assertRaises(TaskEnd):
                task._resident_loop()
        task._try_friend_boss.assert_not_called()
        task._read_fatigue.assert_not_called()
        task.click.assert_not_called()
        task._enter_boss_page.assert_not_called()
        task.ui_goto_page.assert_not_called()

    def test_other_page_yields_to_due_task_without_navigation(self):
        task = self.task(pending=True)
        task._boss_page_visible.return_value = False
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._try_friend_boss.assert_not_called()
        task.ui_goto_page.assert_not_called()

    def test_no_friend_stays_and_polls_without_summon_or_plan_write(self):
        task = self.task()
        with patch('tasks.MetaDemon.resident.time.sleep', side_effect=TaskEnd) as sleep:
            with self.assertRaises(TaskEnd):
                task._resident_loop()
        sleep.assert_called_once_with(5)
        task.ui_goto_page.assert_not_called()
        task.check_and_switch_ticket.assert_not_called()
        task.check_and_synthesize.assert_not_called()
        task.set_next_run.assert_not_called()
        self.assertTrue(task.config.reload.call_count >= 1)
        self.assertTrue(all(not call.args and not call.kwargs for call in task.config.reload.call_args_list))

    def test_no_friend_and_due_task_yields_without_navigation(self):
        task = self.task(pending=True)
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.ui_goto_page.assert_not_called()
        task._try_friend_boss.assert_not_called()

    def test_executable_idle_goal_yields_before_scanning(self):
        task = self.task()
        task.config.pending_task = [SimpleNamespace(command='SixRealms')]
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._try_friend_boss.assert_not_called()
        task._read_fatigue.assert_not_called()

    def test_due_task_arriving_during_lineup_blocks_next_battle(self):
        task = self.task()
        task._try_friend_boss.return_value = True
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
        task.appear = Mock(side_effect=lambda rule: rule is task.I_MD_FIRE or rule is task.I_MD_FRIEND_OWNER)
        task._refresh_current_boss_type = Mock()
        task._select_attack = Mock(return_value=True)
        def prepare():
            task.config.normal_pending_task = [SimpleNamespace(command='WantedQuests')]
            return True
        task._prepare_lineup = Mock(side_effect=prepare)
        task.check_and_switch_powerful = Mock(return_value=True)
        task.start_battle = Mock()
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.start_battle.assert_not_called()

    def test_continuous_friends_yield_after_current_battle_when_task_becomes_due(self):
        task = self.task()
        task._friend_active = True
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
        task.appear = Mock(side_effect=lambda rule: rule is task.I_MD_FIRE or rule is task.I_MD_FRIEND_OWNER)
        task._refresh_current_boss_type = Mock()
        task._select_attack = task._prepare_lineup = task.check_and_switch_powerful = Mock(return_value=True)
        task.start_battle = Mock(side_effect=lambda: setattr(
            task.config, 'normal_pending_task', [SimpleNamespace(command='WantedQuests')]))
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.start_battle.assert_called_once()

    def test_due_work_skips_residency_with_enabled_or_disabled_meta_demon(self):
        for enabled in (False, True):
            runner = self.runner()
            runner.config.meta_demon.scheduler.enable = enabled
            runner.run_meta_demon_resident = Mock(side_effect=AssertionError('ready work must run first'))
            for key in runner.config.model.model_fields:
                if getattr(getattr(runner.config.model, key), 'scheduler', None) is None:
                    continue
                task = SimpleNamespace(command=runner.config.model.type(key),
                                       next_run=datetime.now() - timedelta(seconds=1))
                with self.subTest(enabled=enabled, task=task.command), \
                        patch.object(runner.config, 'reload'), \
                        patch.object(runner.config, 'get_next', return_value=task):
                    self.assertEqual(runner.get_next_task(), task.command)
            runner.run_meta_demon_resident.assert_not_called()

    def test_due_task_precedes_eligible_friend_even_after_normal_limit(self):
        task = self.task(pending=True)
        task.limit_count = task.total_count = 0
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
        task._try_friend_boss.side_effect = [True, None]
        task._refresh_current_boss_type = Mock()
        task.appear = Mock(side_effect=lambda rule: rule is task.I_MD_FIRE or rule is task.I_MD_FRIEND_OWNER)
        task._select_attack = Mock(return_value=True)
        task._prepare_lineup = Mock(return_value=True)
        task.check_and_switch_powerful = Mock(return_value=True)
        task.start_battle = Mock()
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task.start_battle.assert_not_called()
        task._try_friend_boss.assert_not_called()
        task.ui_goto_page.assert_not_called()
        task.set_next_run.assert_not_called()

    def test_full_fatigue_without_tea_yields_without_selecting(self):
        task = self.task(pending=True)
        task._read_fatigue.return_value = (112, 100)
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._try_friend_boss.assert_not_called()
        task.ui_goto_page.assert_not_called()

    def test_post_completion_friend_identity_must_be_confirmed_before_attack(self):
        for missing in ['star', 'name', 'owner', 'fire', 'settling']:
            with self.subTest(missing=missing):
                task = self.task()
                task._try_friend_boss.side_effect = lambda **kwargs: setattr(task, '_friend_active', True) or True
                task.cur_boss_type = None if missing == 'star' else BossType.FOUR_STARS
                task.cur_boss_name = '' if missing == 'name' else '鬼切'
                task._refresh_current_boss_type = Mock()
                task.appear = Mock(side_effect=lambda rule: (
                    (rule is task.I_MD_FIRE and missing != 'fire')
                    or (rule is task.I_MD_FRIEND_OWNER and missing != 'owner')
                    or (rule is task.I_MD_SETTLING and missing == 'settling')))
                task._prepare_lineup = Mock()
                task.start_battle = Mock()
                with self.assertRaises(GameStuckError):
                    task._resident_loop()
                task._prepare_lineup.assert_not_called()
                task.start_battle.assert_not_called()

    def test_real_counter_can_cross_full_after_a_strong_attack(self):
        task = base.MetaDemonTest().task()
        for current in [100, 112, 129]:
            task.O_MD_FATIGUE.ocr.return_value = (current, 100 - current, 100)
            self.assertEqual(task._read_fatigue(), (current, 100))
        for counter in [(130, -30, 100), (112, 0, 100), (0, -1, 100)]:
            task.O_MD_FATIGUE.ocr.return_value = counter
            with self.assertRaises(GameStuckError):
                task._read_fatigue()

    def test_disable_on_reload_exits_without_clicking_or_pruning(self):
        task = self.task()
        task.config.reload.side_effect = lambda: setattr(task.conf.scheduler, 'enable', False)
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        self.assertFalse(task.config.meta_demon_residency_requested)
        task._enter_boss_page.assert_not_called()
        task.config.reload.assert_called_once_with()

    def test_manual_request_is_not_consumed_or_delayed_for_assistance(self):
        task = self.task()
        task.config.normal_pending_task = [SimpleNamespace(manual_request='new-token')]
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._try_friend_boss.assert_not_called()
        task.config.reload.assert_called_once_with()

    def test_rest_reload_disabling_task_is_checked_before_navigation(self):
        task = self.task()
        guard = Mock()
        guard.checkpoint.side_effect = lambda: setattr(task.conf.scheduler, 'enable', False)
        task.device.activity_guard = guard
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        guard.checkpoint.assert_called_once_with()
        task._enter_boss_page.assert_not_called()

    def test_attempt_cap_on_same_live_friend_is_preserved(self):
        task = self.task()
        task._friend_active = True
        task._encounter_attempts = 3
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
        task.appear = Mock(side_effect=lambda rule: rule is task.I_MD_FIRE or rule is task.I_MD_FRIEND_OWNER)
        task._refresh_current_boss_type = Mock()
        task._select_attack = Mock(return_value=False)
        with patch('tasks.MetaDemon.resident.time.sleep', side_effect=TaskEnd):
            with self.assertRaises(TaskEnd):
                task._resident_loop()
        self.assertEqual(task._encounter_attempts, 3)
        task._try_friend_boss.assert_not_called()

    def test_failed_lineup_clears_actual_running_status_and_finishes_guard(self):
        task = self.task()
        activity = Mock()
        task.config.meta_demon_resident_activity = activity
        task.device.activity_guard = Mock()
        task._try_friend_boss.return_value = True
        task.cur_boss_type, task.cur_boss_name = BossType.FOUR_STARS, '鬼切'
        task.appear = Mock(side_effect=lambda rule: rule is task.I_MD_FIRE or rule is task.I_MD_FRIEND_OWNER)
        task._refresh_current_boss_type = Mock()
        task._select_attack = Mock(return_value=True)
        task._prepare_lineup = Mock(side_effect=GameStuckError('lineup failed'))
        with self.assertRaises(GameStuckError):
            task._resident_loop()
        self.assertEqual([call.args[0] for call in activity.call_args_list], [False, True, False])
        task.device.activity_guard.start.assert_called_once()
        self.assertEqual(task.device.activity_guard.finish.call_count, 2)

    def test_resident_navigation_is_restored_on_exception(self):
        task = self.task()
        task._resident_loop = Mock(side_effect=GameStuckError('failed'))
        original_close = task.ui_close
        with self.assertRaises(GameStuckError):
            task.run_resident()
        self.assertNotIn('_navigation_snapshot', task.__dict__)
        self.assertIs(task.ui_close, original_close)

    def test_settling_candidates_are_skipped_with_one_shared_deadline(self):
        for other in [False, True]:
            task = base.MetaDemonTest().task()
            initial = friends.FriendAssistTest.card_image(4)
            template = task.I_MD_FRIEND_REMAINING.image
            h, w = template.shape[:2]
            initial[408:408+h, 147:147+w] = template
            first = initial.copy()
            second = friends.FriendAssistTest.card_image(5, top=485)
            second[408:408+h, 147:147+w] = template
            if other:
                first[523:523+h, 147:147+w] = template
                second[523:523+h, 147:147+w] = template
            task.device.image = initial
            state, clock = base.MetaDemonTest().replay(task, [
                (1001, {'I_MD_SETTLING'}), (1002, {'I_MD_SETTLING'}),
                (1003, {'SECOND', 'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
                (1004, {'SECOND', 'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
            original_screenshot = task.screenshot.side_effect

            def screenshot():
                original_screenshot()
                task.device.image = second if 'SECOND' in state['visible'] else first

            task.screenshot.side_effect = screenshot
            original_appear = task.appear.side_effect
            task.appear.side_effect = lambda target, **kwargs: (
                target.match(task.device.image) if getattr(target, 'name', '') == 'I_MD_FRIEND_REMAINING'
                else original_appear(target, **kwargs))
            with clock:
                self.assertEqual(task._try_friend_boss(skip_settling=True), True if other else None)
            self.assertEqual(task.click.call_count, 2 if other else 1)

    def test_manual_request_arriving_during_rest_is_rechecked(self):
        task = self.task()
        task.device.activity_guard = Mock()
        task.device.activity_guard.checkpoint.side_effect = lambda: setattr(
            task.config, 'normal_pending_task', [SimpleNamespace(manual_request='new-token')])
        with self.assertRaises(TaskEnd):
            task._resident_loop()
        task._try_friend_boss.assert_not_called()

    def test_resident_scans_other_row_after_owner_mismatch(self):
        task = base.MetaDemonTest().task()
        first = friends.FriendAssistTest.card_image(4)
        second = friends.FriendAssistTest.card_image(5, top=485)
        template = task.I_MD_FRIEND_REMAINING.image
        h, w = template.shape[:2]
        for image in [first, second]:
            image[408:408+h, 147:147+w] = template
            image[523:523+h, 147:147+w] = template
        initial = first.copy()
        initial[523:523+h, 147:147+w] = 0  # First observation sees the first card.
        task.device.image = initial
        state, clock = base.MetaDemonTest().replay(task, [
            (1001, {'I_MD_FIRE'}), (1002, {'I_MD_FIRE'}),
            (1003, {'SECOND', 'I_MD_FIRE', 'I_MD_FRIEND_OWNER'}),
            (1004, {'SECOND', 'I_MD_FIRE', 'I_MD_FRIEND_OWNER'})])
        original_screenshot = task.screenshot.side_effect

        def screenshot():
            original_screenshot()
            task.device.image = second if 'SECOND' in state['visible'] else first

        task.screenshot.side_effect = screenshot
        original_appear = task.appear.side_effect
        task.appear.side_effect = lambda target, **kwargs: (
            target.match(task.device.image) if getattr(target, 'name', '') == 'I_MD_FRIEND_REMAINING'
            else original_appear(target, **kwargs))
        task._return_to_self_discovery = Mock()
        with clock:
            self.assertTrue(task._try_friend_boss(skip_settling=True))
        task._return_to_self_discovery.assert_called_once()
        self.assertEqual(task.click.call_count, 2)

    def runner(self):
        runner = Script.__new__(Script)
        runner.__dict__['config'] = Config('template')
        runner.__dict__['device'] = Mock(activity_guard=None)
        runner.__dict__['activity_guard'] = Mock()
        runner.activity_guard.checkpoint.return_value = False
        runner.runtime = ScriptRuntimeController(runner)
        runner.runtime.meta_demon_residency_requested = True
        runner.config.meta_demon.scheduler.enable = True
        runner._error_restart_pending = False
        runner._emulator_down = False
        runner.state_queue = None
        runner.publish_schedule = Mock()
        return runner

    def test_scheduler_rechecks_fresh_queue_after_resident_handoff(self):
        runner = self.runner()
        pets = SimpleNamespace(command='Pets', next_run=datetime.now() + timedelta(seconds=60))
        wanted = SimpleNamespace(command='WantedQuests', next_run=datetime.now() - timedelta(seconds=1))
        runner.run_meta_demon_resident = Mock()
        with patch.object(runner.config, 'reload') as reload, \
                patch.object(runner.config, 'get_next', side_effect=[pets, wanted]):
            self.assertEqual(runner.get_next_task(), 'WantedQuests')
        runner.run_meta_demon_resident.assert_called_once()
        self.assertEqual(reload.call_args_list[-1].kwargs, {'prune_manual': True})

    def test_restarted_process_resumes_residency_without_previous_completion_flag(self):
        for next_command in ['Pets', 'MetaDemon']:
            with self.subTest(next_command=next_command):
                runner = self.runner()
                runner.runtime.meta_demon_residency_requested = False
                waiting = SimpleNamespace(command=next_command, next_run=datetime.now() + timedelta(days=1))
                due = SimpleNamespace(command='WantedQuests', next_run=datetime.now() - timedelta(seconds=1))
                runner.run_meta_demon_resident = Mock()
                runner.runtime.handle_wait_during_idle = Mock(side_effect=AssertionError('must resume residency'))
                with patch.object(runner.config, 'reload'), \
                        patch.object(runner.config, 'get_next', side_effect=[waiting, due]):
                    self.assertEqual(runner.get_next_task(), 'WantedQuests')
                runner.run_meta_demon_resident.assert_called_once()
                runner.runtime.handle_wait_during_idle.assert_not_called()

    def test_residency_recovery_preserves_disable_manual_and_due_normal_run(self):
        for case in ['disabled', 'manual', 'due_meta_demon']:
            with self.subTest(case=case):
                runner = self.runner()
                runner.runtime.meta_demon_residency_requested = False
                runner.config.meta_demon.scheduler.enable = case != 'disabled'
                task = SimpleNamespace(command='MetaDemon' if case == 'due_meta_demon' else 'Pets',
                                       next_run=datetime.now() - timedelta(seconds=1),
                                       manual_request='token' if case == 'manual' else None)
                runner.run_meta_demon_resident = Mock()
                with patch.object(runner.config, 'reload'), patch.object(runner.config, 'get_next', return_value=task):
                    self.assertEqual(runner.get_next_task(), task.command)
                runner.run_meta_demon_resident.assert_not_called()

    def test_resident_wrapper_reuses_device_and_cleans_snapshot(self):
        runner = self.runner()
        previous = runner.config.task
        runner.runtime.prepare_task_execution = Mock(return_value=ScriptRuntimeDecision.READY)

        def execute(command, **kwargs):
            self.assertEqual(command, 'MetaDemon')
            self.assertTrue(kwargs['resident'])
            self.assertEqual(runner.config.model.running_task, '')
            runner.config.meta_demon_resident_activity(True)
            self.assertFalse(runner.runtime.idle_main_prepared)
            self.assertEqual(runner.config.model.running_task, 'MetaDemon')
            runner.config.meta_demon_resident_activity(False)
            return True

        runner.run = Mock(side_effect=execute)
        runner.runtime.idle_main_prepared = True
        with patch('script.Device', side_effect=AssertionError('must reuse device')):
            runner.run_meta_demon_resident()
        runner.runtime.prepare_task_execution.assert_not_called()
        self.assertIs(runner.config.task, previous)
        self.assertEqual(runner.config.model.running_task, '')
        self.assertNotIn('meta_demon_resident_activity', runner.config.__dict__)

    def test_observation_does_not_create_device_or_start_closed_game(self):
        for state in ['disabled', 'uninitialized', 'closed', 'emulator_down', 'maintenance']:
            with self.subTest(state=state):
                runner = self.runner()
                runner.run = Mock()
                runner.runtime.prepare_task_execution = Mock()
                if state == 'disabled':
                    runner.config.meta_demon.scheduler.enable = False
                elif state == 'uninitialized':
                    runner.__dict__.pop('device')
                elif state == 'closed':
                    runner.device.app_is_running.return_value = False
                elif state == 'emulator_down':
                    runner._emulator_down = True
                else:
                    runner.runtime.server_update_wait_until = datetime.now() + timedelta(hours=1)
                with patch('script.Device', side_effect=AssertionError('must not create device')):
                    runner.run_meta_demon_resident()
                runner.run.assert_not_called()
                runner.runtime.prepare_task_execution.assert_not_called()

    def test_resident_run_dispatches_explicit_method_with_automatic_guard(self):
        runner = self.runner()
        runner.config.task = SimpleNamespace(command='MetaDemon', manual_request='stale-token')
        runner.config.meta_demon.scheduler.execution_mode = 'manual'
        runner.__dict__['immediate_execution'] = Mock()
        runner._reset_task_runtime_outcome = Mock()
        runner._handle_task_exception = Mock(return_value=True)
        instance = Mock()

        def exit_residency():
            runner.config.meta_demon_residency_requested = False
            raise TaskEnd

        instance.run_resident.side_effect = exit_residency
        module = SimpleNamespace(ScriptTask=Mock(return_value=instance))
        with patch('script.load_module', return_value=module), patch('script.set_ocr_logging_enabled'):
            self.assertTrue(runner.run('MetaDemon', resident=True))
        instance.run_resident.assert_called_once()
        instance.run.assert_not_called()
        runner.activity_guard.checkpoint.assert_called_once_with()
        self.assertIsNone(runner.device.activity_guard)
        self.assertFalse(runner.runtime.meta_demon_residency_requested)
        self.assertNotIn('meta_demon_residency_requested', runner.config.__dict__)


if __name__ == '__main__':
    unittest.main()
