"""Check once at backend startup; coordinate manual updates and safe restarts."""
import asyncio
from pathlib import Path

from filelock import FileLock

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
        self.runtime_lease = None
        self.startup_error = None
        self.startup_checked = False
        self.source_archive = False

    @staticmethod
    def archive_status():
        return dict(status='source_archive', message='源码安装可以运行；启用 AutoUpdate 后在下次后端启动时接入更新',
                    restart_required=False, commit=[])

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
        if self.source_archive:
            return self.archive_status()
        async with self.lock:
            self.last_result = await self.blocking(lambda: Updater().get_update_info())
            return self.last_result

    async def install(self, automatic=False):
        if self.source_archive:
            return self.archive_status()
        if self.lock.locked():
            return dict(status='busy', message='另一个更新操作正在进行', restart_required=False)
        async with self.lock:
            if self.start_error():
                return dict(status='restart_required', message=self.start_error(), restart_required=True)
            self.installing = True  # Set before any await so task starts cannot race the update.
            try:
                updater = Updater()
                if automatic and not updater.AutoUpdate:
                    return dict(status='disabled', message='自动安装已关闭', restart_required=False)
                active = self.active_processes()
                if automatic and active:
                    return dict(status='deferred', message='任务运行中，延后自动安装', restart_required=False)
                preflight = await self.blocking(updater.get_update_info)
                if preflight['status'] != 'available':
                    self.last_result = preflight
                    return preflight
                for script in active:
                    process = script._process
                    await script.stop()
                    await asyncio.to_thread(process.join, 10)
                    if process.is_alive():
                        return dict(status='tasks_running', message='任务进程未退出，已停止安装', restart_required=False)
                result = await self.blocking(lambda: updater.execute_pull(service_owned=self.runtime_lease is not None, checked=preflight))
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
        logger.info('正在检查后端运行锁和依赖状态')
        updater = Updater()
        try:
            root = Path(updater.root_filepath)
            self.source_archive = not (root / '.git').exists() or updater.project.is_source_archive()
            if not (root / '.git').exists():
                # ZIP downloads have no Git update state. Still prevent two servers
                # from sharing the same configs; never manufacture a Git history.
                (root / 'config').mkdir(parents=True, exist_ok=True)
                lease = FileLock(str(root / 'config' / 'oas-service-runtime.lock'), timeout=0)
            else:
                lease = updater.project.lock('oas-service-runtime.lock')
            lease.__enter__()
            self.runtime_lease = lease
            self.dependencies_pending = (False if self.source_archive else
                                        await asyncio.to_thread(updater.project.dependency_pending))
            if self.dependencies_pending and updater.InstallDependencies:
                await asyncio.to_thread(updater.project.complete_dependencies, updater.install_dependencies)
                self.dependencies_pending = False
        except Exception as exc:
            self.dependencies_pending = True
            self.startup_error = f'更新状态或依赖未就绪，已阻止任务启动：{exc}'
            logger.exception('无法确认更新依赖状态，已阻止任务启动')
        if not self.start_error():
            await self.check_at_startup(updater)

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

    async def check_at_startup(self, updater=None):
        if self.startup_checked:
            return
        self.startup_checked = True
        updater = updater or Updater()
        if not updater.AutoUpdate and not updater.AutoCheckUpdate:
            return
        logger.info('正在执行本次启动更新检查；远端获取最多等待 45 秒，依赖安装最多等待 600 秒')
        try:
            if self.source_archive:
                if not updater.AutoUpdate:
                    return
                result = await self.blocking(updater.project.prepare_archive)
                self.last_result = result
                # Preparing a ZIP may create .git. Keep installers and the
                # service on the same lock even when network access later fails.
                old_lease = self.runtime_lease
                if isinstance(old_lease, FileLock) and (Path(updater.root_filepath) / '.git').exists():
                    lease = updater.project.lock('oas-service-runtime.lock')
                    try:
                        lease.__enter__()
                    except Exception as exc:
                        self.startup_error = f'无法获取运行锁，任务启动已阻止：{exc}'
                        raise
                    old_lease.__exit__(None, None, None)
                    self.runtime_lease = lease
                if result['status'] == 'prepared':
                    self.source_archive = False
                    result = await self.install(automatic=True)
                    self.last_result = result
            elif updater.AutoUpdate:
                result = await self.install(automatic=True)
            else:
                result = await self.check()
            logger.info(f"启动更新检查：{result['message']}")
        except Exception:
            # A network/version check must not stop a valid installed backend.
            logger.exception('启动更新检查失败，保留本地版本；本次运行不再重试')


update_service = UpdateService()
