"""Coordinate background checks, task starts, installation and service restart."""
import asyncio
import datetime

from module.logger import logger
from module.server.updater import Updater


class UpdateService:
    def __init__(self):
        self.installing = False
        self.restart_required = False
        self.dependencies_pending = False
        self.last_result = None
        self.lock = asyncio.Lock()
        self.task = None
        self.last_install_date = None
        self.next_install = 0.0
        self.runtime_lease = None
        self.startup_error = None
        self.next_check = 0.0
        self.check_failures = 0
        self.install_failures = 0

    @staticmethod
    async def blocking(function, *args):
        # Cancellation must not leave a Git/pip thread running after the gate opens.
        worker = asyncio.create_task(asyncio.to_thread(function, *args))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            await worker
            raise

    def start_error(self):
        if self.startup_error:
            return self.startup_error
        if self.installing:
            return '正在安装更新，请稍后启动任务'
        if self.dependencies_pending:
            return '更新依赖未就绪，请安装依赖并重启服务'
        if self.restart_required:
            return '代码已更新，请重启服务后再启动任务'
        return None

    @staticmethod
    def active_processes():
        from module.server.main_manager import mm
        return [p for p in mm.script_process.values()
                if p._process is not None and p._process.is_alive()]

    async def check(self):
        async with self.lock:
            self.last_result = await self.blocking(lambda: Updater().get_update_info())
            return self.last_result

    async def install(self, automatic=False):
        if self.lock.locked():
            return dict(status='busy', message='另一个更新操作正在进行', restart_required=False)
        async with self.lock:
            if self.start_error():
                return dict(status='restart_required', message=self.start_error(), restart_required=True)
            self.installing = True  # Set before any await so task starts cannot race the update.
            try:
                updater = Updater()
                if automatic and (not updater.AutoUpdate or not updater.schedule_time):
                    return dict(status='disabled', message='自动安装已关闭', restart_required=False)
                active = self.active_processes()
                if automatic and active:
                    return dict(status='deferred', message='任务运行中，延后自动安装', restart_required=False)
                preflight = await self.blocking(updater.get_update_info)
                if preflight['status'] != 'available':
                    self.last_result = preflight
                    return preflight
                if not preflight.get('changes'):
                    for script in active:
                        process = script._process
                        await script.stop()
                        await asyncio.to_thread(process.join, 10)
                        if process.is_alive():
                            return dict(status='tasks_running', message='任务进程未退出，已停止安装', restart_required=False)
                result = await self.blocking(lambda: updater.execute_pull(service_owned=self.runtime_lease is not None))
                result['stopped_scripts'] = [getattr(p, 'config_name', '') for p in active]
                self.restart_required = result.get('restart_required', False)
                self.dependencies_pending = result['status'] in ('dependency_error', 'dependencies_pending')
                self.last_result = result
                if result['status'] == 'updated':
                    from module.server.setting import State
                    if updater.EnableReload and State.restart_event is not None:
                        State.update_resume_instances = [p.config_name for p in active]
                        # Let the HTTP response leave before shutting down the service.
                        asyncio.get_running_loop().call_later(1, State.restart_event.set)
                        result['message'] = '更新成功，服务即将重启'
                return result
            except Exception as exc:
                logger.exception('安装更新失败')
                self.last_result = dict(status='error', message=f'安装更新失败：{exc}',
                                        restart_required=self.restart_required)
                return self.last_result
            finally:
                self.installing = False

    async def start(self):
        self.lock = asyncio.Lock()
        updater = Updater()
        try:
            lease = updater.project.lock('oas-service-runtime.lock')
            lease.__enter__()
            self.runtime_lease = lease
            self.dependencies_pending = await asyncio.to_thread(updater.project.dependency_pending)
            if self.dependencies_pending and updater.InstallDependencies:
                await asyncio.to_thread(updater.project.complete_dependencies, updater.install_dependencies)
                self.dependencies_pending = False
        except Exception as exc:
            self.dependencies_pending = True
            self.startup_error = f'更新状态或依赖未就绪，已阻止任务启动：{exc}'
            logger.exception('无法确认更新依赖状态，已阻止任务启动')
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception('停止更新后台任务失败')

    def release_runtime(self):
        if self.runtime_lease:
            self.runtime_lease.__exit__(None, None, None)
            self.runtime_lease = None

    async def tick(self, now, monotonic):
        updater = Updater()
        interval = updater.delay
        if updater.AutoCheckUpdate and interval and monotonic >= self.next_check:
            result = await self.check()
            self.check_failures = (self.check_failures + 1
                                   if result['status'] in ('network_error', 'git_error') else 0)
            self.next_check = monotonic + min(interval * (2 ** min(self.check_failures, 4)), 86400)
            logger.info(f"更新检查：{result['message']}")
        scheduled = updater.schedule_time
        if (updater.AutoUpdate and scheduled and now.time() >= scheduled
                and self.last_install_date != now.date() and not self.start_error()
                and monotonic >= self.next_install):
            result = await self.install(automatic=True)
            network_error = result['status'] in ('network_error', 'git_error')
            self.install_failures = self.install_failures + 1 if network_error else 0
            self.next_install = monotonic + (min(60 * 2 ** min(self.install_failures, 6), 3600)
                                             if network_error else 60)
            if result['status'] not in ('deferred', 'busy', 'network_error', 'git_error'):
                self.last_install_date = now.date()

    async def run(self):
        while True:
            try:
                now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
                monotonic = asyncio.get_running_loop().time()
                await self.tick(now, monotonic)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('自动更新检查失败，稍后重试')
            await asyncio.sleep(60)


update_service = UpdateService()
