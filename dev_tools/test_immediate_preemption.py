"""Reward-gated guild raid suspension: no device, OCR or game input."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from dev_tools import test_manual_schedule as manual_tests
from module.config.manual import active_task_suspensions
from module.exception import GameStuckError, TaskEnd
from module.script.immediate import ImmediateExecution
from module.script.runtime_controller import ScriptRuntimeDecision
from tasks.RyouToppa.script_task import ScriptTask


class ImmediatePreemptionTest(manual_tests.ManualScheduleTest):
    def make_execution(self):
        parent = self.config.model.ryou_toppa.scheduler
        parent.enable = True
        parent.next_run = datetime.now() - timedelta(days=1)
        self.config.get_next()
        self.config.model.running_task = 'RyouToppa'
        guard = SimpleNamespace(active=True, finish=Mock(), start=Mock())
        guard.finish.side_effect = lambda: setattr(guard, 'active', False)
        guard.start.side_effect = lambda: setattr(guard, 'active', True)
        device = SimpleNamespace(activity_guard=guard, stuck_record_clear=Mock(),
                                 click_record_clear=Mock(), invalidate_image_batch_cache=Mock())
        runner = SimpleNamespace(config=self.config, state_queue=Mock(), activity_guard=guard,
                                 device=device, failure_record={}, _error_restart_pending=False,
                                 last_task_runtime_outcome=None, run=Mock(return_value=True),
                                 runtime=SimpleNamespace(prepare_task_execution=Mock(
                                     return_value=ScriptRuntimeDecision.READY)))
        task = SimpleNamespace(current_count=7, start_time=datetime(2026, 10, 19, 12),
                               immediate_suspend=Mock(), immediate_resume=Mock())
        return ImmediateExecution(runner), runner, task

    def test_reward_checkpoint_services_manual_fifo_then_returns_to_same_live_task(self):
        execution, runner, task = self.make_execution()
        parent = self.config.task
        self.enable('orochi')
        self.enable('pets')
        self.config.manual_store.request('orochi')
        seen = []
        def run(command):
            seen.append(command)
            self.assertEqual(task.current_count, 7)
            data = self.config.get_schedule_data()
            self.assertEqual(data['running']['name'], command)
            self.assertEqual(data['suspended'][0]['name'], 'RyouToppa')
            self.assertNotIn('RyouToppa', [item['name'] for item in data['pending'] + data['waiting']])
            if command == 'Orochi':
                self.config.manual_store.request('pets')
                self.assertFalse(execution.checkpoint(task))  # no recursive equal-priority preemption
            return True
        runner.run.side_effect = run
        with patch.object(self.config, 'reload'), patch('module.script.immediate.RuleScatter'), \
                patch('module.script.immediate.time.monotonic', side_effect=[100, 160]):
            self.assertTrue(execution.checkpoint(task))
        self.assertEqual(seen, ['Orochi', 'Pets'])
        self.assertIs(self.config.task, parent)
        self.assertEqual(self.config.model.running_task, 'RyouToppa')
        self.assertEqual(task.current_count, 7)
        self.assertEqual(task.start_time, datetime(2026, 10, 19, 12, 1))
        task.immediate_suspend.assert_called_once()
        task.immediate_resume.assert_called_once()
        self.assertEqual(execution.suspended, [])
        self.assertTrue(runner.activity_guard.active)
        self.assertEqual(self.config.manual_store.pending(), {})

    def test_wait_during_preparation_cancels_only_selected_request(self):
        execution, runner, task = self.make_execution()
        self.enable('orochi')
        self.config.manual_store.request('orochi')
        runner.runtime.prepare_task_execution.side_effect = lambda command: (
            self.config.manual_store.clear('orochi') or ScriptRuntimeDecision.READY)
        with patch.object(self.config, 'reload'), patch('module.script.immediate.RuleScatter'):
            self.assertTrue(execution.checkpoint(task))
        runner.run.assert_not_called()
        task.immediate_resume.assert_called_once()

    def test_suspend_failure_never_consumes_request_or_runs_manual_task(self):
        execution, runner, task = self.make_execution()
        self.enable('orochi')
        self.config.manual_store.request('orochi')
        task.immediate_suspend.side_effect = GameStuckError('no main page')
        with patch.object(self.config, 'reload'), self.assertRaises(GameStuckError):
            execution.checkpoint(task)
        self.assertIn('orochi', self.config.manual_store.pending())
        runner.run.assert_not_called()
        task.immediate_resume.assert_not_called()
        self.assertFalse(execution.servicing)

    def test_resume_navigation_failure_propagates_and_clears_snapshot(self):
        execution, runner, task = self.make_execution()
        self.enable('orochi')
        self.config.manual_store.request('orochi')
        task.immediate_resume.side_effect = GameStuckError('cannot return to raid')
        with patch.object(self.config, 'reload'), patch('module.script.immediate.RuleScatter'), \
                self.assertRaises(GameStuckError):
            execution.checkpoint(task)
        self.assertEqual(task.current_count, 7)
        self.assertEqual(execution.suspended, [])
        self.assertFalse(execution.servicing)
        self.assertEqual(self.config.task.command, 'RyouToppa')

    def test_disabled_parent_is_not_restarted_after_manual_task(self):
        execution, runner, task = self.make_execution()
        self.enable('orochi')
        self.config.manual_store.request('orochi')
        def disable(command):
            self.config.model.ryou_toppa.scheduler.enable = False
            return True
        runner.run.side_effect = disable
        with patch.object(self.config, 'reload'), patch('module.script.immediate.RuleScatter'), \
                self.assertRaises(TaskEnd):
            execution.checkpoint(task)
        task.immediate_resume.assert_not_called()
        self.assertEqual(execution.suspended, [])

    def simulate_battle(self, frames, *, pending=True):
        task = ScriptTask.__new__(ScriptTask)
        task.config = self.config
        task.device = Mock()
        task.current_count = 7
        task.start_time = datetime.now()
        task.immediate_checkpoint = Mock()
        position = [-1]
        clicked = []
        if pending:
            self.enable('orochi')
            self.config.manual_store.request('orochi')
        def screenshot():
            position[0] += 1
            if position[0] >= len(frames):
                self.fail('battle did not exit at the expected stable lobby')
        def appear(marker, **kwargs):
            frame = frames[position[0]]
            return ((marker is task.I_TOPPA_RECORD and frame == 'lobby')
                    or (marker is task.I_REWARD and frame == 'reward'))
        def click(marker, **kwargs):
            if marker is task.I_REWARD and frames[position[0]] == 'reward':
                clicked.append('reward')
                return True
            return False
        task.screenshot, task.appear, task.appear_then_click = screenshot, appear, click
        with patch('tasks.RyouToppa.script_task.time.sleep'), patch(
                'tasks.RyouToppa.script_task.time.monotonic', side_effect=[10, 10, 10.5, 11.1]):
            self.assertTrue(task.battle_wait(False))
        return task, clicked

    def test_guild_raid_waits_for_real_reward_and_stable_lobby(self):
        task, clicked = self.simulate_battle(['battle', 'reward', 'reward', 'lobby', 'lobby', 'lobby'])
        self.assertEqual(clicked, ['reward', 'reward'])
        task.immediate_checkpoint.assert_called_once()
        self.assertEqual(task.current_count, 7)

    def test_guild_raid_never_preempts_battle_or_infers_reward_from_lobby(self):
        task, _ = self.simulate_battle(['battle', 'battle', 'lobby'])
        task.immediate_checkpoint.assert_not_called()

    def test_guild_raid_without_pending_request_does_not_yield(self):
        task, _ = self.simulate_battle(['reward', 'lobby'], pending=False)
        task.immediate_checkpoint.assert_not_called()

    def test_only_current_child_pid_can_update_suspension_snapshot(self):
        from module.server.script_process import ScriptProcess
        process = ScriptProcess.__new__(ScriptProcess)
        process.config_name, process._process = 'one', SimpleNamespace(pid=321)
        with patch.dict(active_task_suspensions, {}, clear=True):
            self.assertFalse(process._consume_startup_order(
                {'_task_pid': 123, '_task_suspensions': [{'name': 'RyouToppa'}]}))
            self.assertEqual(active_task_suspensions, {})
            self.assertTrue(process._consume_startup_order(
                {'_task_pid': 321, '_task_suspensions': [{'name': 'RyouToppa'}]}))
            self.assertEqual(active_task_suspensions['one'], [{'name': 'RyouToppa'}])


if __name__ == '__main__':
    unittest.main()
