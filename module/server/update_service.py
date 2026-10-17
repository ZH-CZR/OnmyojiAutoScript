"""Nonblocking update checks; apply only with no live game processes."""
import asyncio
from datetime import datetime, time

from module.logger import logger
from module.server.setting import State
from module.server.updater import Updater


class UpdateService:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.task = None
        self.stopping = False
        self.wakeup = None
        self.status = {'state': 'idle', 'restart_required': False}

    def start(self):
        self.stopping = False
        self.wakeup = asyncio.Event()
        self.task = asyncio.create_task(self.run(), name='project-auto-update')

    async def stop(self):
        # Finish any Git subprocess before shutdown; do not orphan to_thread work.
        if self.task:
            self.stopping = True
            if self.wakeup:
                self.wakeup.set()
            await self.task
            self.task = None
        async with self.lock:
            pass

    async def check(self):
        async with self.lock:
            try:
                info = await asyncio.to_thread(Updater().get_update_info)
                self.status.update(info, state='checked', error='')
                return dict(self.status)
            except Exception as exc:
                self.status.update(state='error', error=str(exc), is_update=False)
                logger.warning(f'检查项目更新失败: {exc}')
                return dict(self.status)

    async def execute(self):
        # Client disconnect / graceful shutdown cancellation must not release the
        # task-start guard while a to_thread Git merge is still running.
        operation = asyncio.create_task(self._execute())
        try:
            return await asyncio.shield(operation)
        except asyncio.CancelledError:
            await operation
            raise

    async def _execute(self):
        from module.server.main_manager import mm
        async with self.lock:
            if self.status['restart_required']:
                return dict(self.status, success=False, reason='等待后端重启')
            # Set before yielding; ScriptProcess.start checks the same flag.
            State.project_updating = True
            try:
                if any((p._process is not None and p._process.is_alive()) or
                       getattr(p, 'state', None) == 1
                       for p in mm.script_process.values()):
                    self.status.update(state='waiting', success=False, updated=False,
                                       reason='游戏任务正在运行，等待空闲后更新')
                    return dict(self.status)
                self.status.update(state='updating', error='')
                result = await asyncio.to_thread(Updater().execute_pull)
                self.status.update(result, state='updated' if result['updated'] else 'blocked')
                if result['updated']:
                    callback = State.request_restart
                    if callback:
                        # Allow the HTTP response to leave before closing the listener.
                        asyncio.get_running_loop().call_later(1, callback)
                return dict(self.status)
            except Exception as exc:
                self.status.update(state='error', error=str(exc), success=False,
                                   updated=False, is_update=False)
                logger.warning(f'应用项目更新失败: {exc}')
                return dict(self.status)
            finally:
                State.project_updating = self.status['restart_required']

    async def run(self):
        while not self.stopping:
            delay = 300
            try:
                config = State.deploy_config
                config.read()
                delay = max(1, int(config.CheckUpdateInterval)) * 60
                if config.AutoUpdate and not self.status['restart_required']:
                    info = await self.check()
                    scheduled = config.AutoRestartTime
                    if info.get('is_update') and (not scheduled or
                            datetime.now().time() >= time.fromisoformat(str(scheduled))):
                        await self.execute()
            except Exception as exc:
                logger.warning(f'自动更新失败，下轮重试: {exc}')
                self.status.update(state='error', error=str(exc))
            if not self.stopping:
                try:
                    await asyncio.wait_for(self.wakeup.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass


update_service = UpdateService()
