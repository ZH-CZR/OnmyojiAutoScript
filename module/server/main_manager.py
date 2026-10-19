# This Python file uses the following encoding: utf-8
# @author runhey
# 主进程的管理
# github https://github.com/runhey
import asyncio
import sys
import os
import signal
from asyncio.tasks import Task
from module.config.startup_order import active_startup_orders
from threading import Thread

from module.logger import logger
from module.config.config import Config
from module.server.script_process import ScriptProcess, ScriptState
from module.server.config_manager import ConfigManager


class MainManager(ConfigManager):
    # config_cache: Config = None  # 缓存当前切换的配置
    script_process: dict[str: ScriptProcess] = None  # 脚本进程
    push_data_thread: Thread = None  # 数据推送线程
    signal_kill_server: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.script_process: dict[str: ScriptProcess] = {}  # 脚本进程
        self._all_script_files = self.all_script_files()
        for script_name in self._all_script_files:
            self.script_process[script_name] = ScriptProcess(script_name)
        self.push_data_thread = Thread(target=self.start_push_data_thread, daemon=True)
        self.push_data_thread.start()

    # def ensure_config_cache(self, config_name: str, reload: bool = False):
    #     if self.config_cache is None:
    #         if config_name not in self._all_script_files:
    #             logger.warning(f'[{config_name}] script file does not exist')
    #             return None
    #         self.config_cache = Config(config_name)
    #     elif self.config_cache.config_name != config_name:
    #         self.config_cache = Config(config_name)
    #     if reload:
    #         self.config_cache = Config(config_name)
    #     return self.config_cache

    @staticmethod
    def config_cache(name: str) -> Config:
        from module.config.manual import active_task_suspensions
        config = Config(name)
        process = mm.script_process.get(name)
        config.model.running_task = getattr(process, 'active_task', '') if (
            process is not None and process.state == ScriptState.RUNNING) else ''
        config.startup_task_order = active_startup_orders.get(name)
        config.suspended_tasks = active_task_suspensions.get(name, [])
        return config

    def add_script_file(self, file_name: str):
        # 当你添加了新的脚本文件后，需要添加缓存的列表
        if file_name in self.script_process:
            logger.warning(f'[{file_name}] script file already exists')
            return
        self._all_script_files = self.all_script_files()
        self.script_process[file_name] = ScriptProcess(file_name)

    def start_push_data_thread(self):
        try:
            asyncio.run(self.push_data_handle())
        except SystemExit as e:
            logger.info('Kill the main process')
            # sys.exit(0)
            try:
                os.kill(os.getpid(), signal.SIGILL)
                print("Process killed successfully.")
            except OSError:
                print("Failed to kill the process.")

        except Exception as e:
            logger.exception(e)
            sys.exit(0)

    async def sync_push_tasks(self, tasks):
        """Reconcile push workers by instance identity, including same-name replacements."""
        processes = dict(self.script_process)
        for process in processes.values():
            refresh = getattr(process, 'refresh_state', None)
            if callable(refresh):
                await refresh()
        retired = []
        for key, (owner, task) in list(tasks.items()):
            if processes.get(owner.config_name) is not owner or task.done():
                task.cancel()
                retired.append(task)
                del tasks[key]
        if retired:
            results = await asyncio.gather(*retired, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f'Push worker stopped: {result}')
        for name, process in processes.items():
            if process.state == ScriptState.INACTIVE:
                continue
            for kind in ('state', 'log'):
                key = f'coroutine_{kind}_{name}'
                if key not in tasks:
                    worker = getattr(process, f'coroutine_broadcast_{kind}')
                    tasks[key] = (process, asyncio.create_task(worker(), name=key))

    async def push_data_handle(self):
        tasks: dict[str, tuple[ScriptProcess, Task]] = {}
        try:
            while True:
                await asyncio.sleep(3)
                if MainManager.signal_kill_server:
                    logger.info('Kill all server')
                    for process in list(self.script_process.values()):
                        await process.stop()
                    logger.info('Kill push data thread')
                    sys.exit(0)
                await self.sync_push_tasks(tasks)
        finally:
            for _, task in tasks.values():
                task.cancel()
            await asyncio.gather(*(task for _, task in tasks.values()),
                                 return_exceptions=True)

    async def restart_processes(self, script_instances: list[str]):
        for instance in script_instances:
            logger.info(f'Restart script {instance}')
            if instance not in self.script_process:
                try:
                    self.script_process[instance] = ScriptProcess(instance)
                except FileNotFoundError:
                    logger.error(f'{instance} file not found')
                    continue
            await self.script_process[instance].start()


mm = MainManager()
