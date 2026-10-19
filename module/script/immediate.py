"""Cooperative immediate execution; the suspended task keeps its live stack."""
from datetime import timedelta
import os
import time

from module.atom.scatter import RuleScatter
from module.config.manual import MANUAL
from module.exception import GameStuckError, RequestHumanTakeover, TaskEnd
from module.script.runtime_controller import ScriptRuntimeDecision


class ImmediateExecution:
    def __init__(self, script):
        self.script = script
        self.servicing = False
        self.suspended = []

    def publish(self):
        script = self.script
        script.config.suspended_tasks = self.suspended
        if script.state_queue is not None:
            script.state_queue.put({'_task_suspensions': list(self.suspended),
                                    '_task_pid': os.getpid(),
                                    'schedule': script.config.get_schedule_data()})

    def checkpoint(self, task):
        script = self.script
        config = script.config
        if self.servicing or not config.manual_store.pending():
            return False
        if not callable(getattr(task, 'immediate_suspend', None)) or not callable(
                getattr(task, 'immediate_resume', None)):
            return False
        config.reload()
        config.update_scheduler()  # Prunes disabled/changed-mode requests.
        requests = [item for item in config.pending_task if getattr(item, 'manual_request', None)]
        if not requests:
            return False
        parent = config.task
        from module.config.utils import convert_to_underscore
        parent_key = convert_to_underscore(parent.command)
        parent_mode = getattr(config.model, parent_key).scheduler.execution_mode
        previous_outcome = config.__dict__.get('task_runtime_outcome')
        previous_last = script.last_task_runtime_outcome
        previous_guard = getattr(script.device, 'activity_guard', None)
        guard = script.activity_guard
        was_active = guard.active
        started = time.monotonic()
        self.servicing = True
        try:
            # Only an audited task checkpoint may invoke these hooks, after
            # reward handling and before another challenge is launched.
            task.immediate_suspend()
            guard.finish()
            self.suspended[:] = [dict(name=parent.command, count=task.current_count,
                                      status='已暂停，等待手动任务完成')]
            config.model.running_task = ''
            self.publish()
            while True:
                config.reload()
                config.update_scheduler()
                selected = next((item for item in config.pending_task
                                 if getattr(item, 'manual_request', None)), None)
                if selected is None:
                    break
                key = convert_to_underscore(selected.command)
                if selected.command == parent.command:
                    if getattr(config.model, parent_key).scheduler.execution_mode != parent_mode:
                        break
                    # An already live task must never be started a second time.
                    config.manual_store.consume(key, selected.manual_request)
                    continue
                config.task = selected
                decision = script.runtime.prepare_task_execution(selected.command)
                if decision == ScriptRuntimeDecision.RESCHEDULE:
                    continue
                if decision != ScriptRuntimeDecision.READY:
                    raise GameStuckError('立即执行任务的运行环境准备失败')
                config.reload()
                scheduler = getattr(config.model, key).scheduler
                if (not scheduler.enable or scheduler.execution_mode != MANUAL
                        or not config.manual_store.consume(key, selected.manual_request)):
                    continue
                config.model.running_task = selected.command
                self.publish()
                script.device.stuck_record_clear()
                script.device.click_record_clear()
                RuleScatter.begin_task(selected.command)
                try:
                    success = script.run(selected.command)
                finally:
                    RuleScatter.end_task(selected.command)
                script.failure_record[selected.command] = (0 if success else
                    script.failure_record.get(selected.command, 0) + 1)
                if script.failure_record[selected.command] > config.model.restart.restart_config.error_restart_limit:
                    raise RequestHumanTakeover('立即执行任务连续失败，停止恢复暂停任务')
                if script._error_restart_pending:
                    if not script.run('Restart'):
                        raise RequestHumanTakeover('立即执行任务异常恢复失败')
                    script._error_restart_pending = False
                elif not success and not config.script.error.handle_error:
                    raise RequestHumanTakeover('立即执行失败，已关闭自动异常处理')
                config.model.running_task = ''
            config.reload()
            parent_scheduler = getattr(config.model, parent_key).scheduler
            if not parent_scheduler.enable or parent_scheduler.execution_mode != parent_mode:
                raise TaskEnd('暂停期间任务已禁用或模式已更改，取消恢复')
            config.task = parent
            config.model.running_task = parent.command
            script.device.activity_guard = previous_guard
            if was_active:
                guard.start()
            RuleScatter.begin_task(parent.command)
            # Re-enter the original task scene and reapply its loadout. The
            # original Python frame, count, local variables and iterator live on.
            task.immediate_resume()
            return True
        finally:
            elapsed = max(0, time.monotonic() - started)
            task.start_time += timedelta(seconds=elapsed)
            config.task = parent
            config.task_runtime_outcome = previous_outcome
            script.last_task_runtime_outcome = previous_last
            script.device.activity_guard = previous_guard
            if was_active and not guard.active:
                guard.start()
            script.device.stuck_record_clear()
            script.device.click_record_clear()
            script.device.invalidate_image_batch_cache()
            self.suspended.clear()
            self.servicing = False
            self.publish()
