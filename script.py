# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import zerorpc
import zmq
import re
import cv2
import time
import os
import inflection
import json

from datetime import date
import threading
from module.device.device import Device
from typing import Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
from cached_property import cached_property
from pydantic import BaseModel, ValidationError
from threading import Thread
from multiprocessing.queues import Queue
from module.config.utils import convert_to_underscore, filepath_config
from module.config.config import Config
from module.config.startup_order import StartupTaskOrder
from module.device.env import IS_WINDOWS
from module.base.utils import load_module
from module.base.decorator import del_cached_property
from module.atom.scatter import RuleScatter
from module.logger import logger
from module.exception import *
from module.server.i18n import I18n
from module.image.rpc import ensure_image_server_ready, set_image_low_spec_mode
from module.ocr.rpc import (
    ensure_ocr_server_ready,
    set_ocr_logging_enabled,
    set_ocr_low_spec_mode,
    set_ocr_model_size,
    get_ocr_client,
)
from module.script import ScriptRuntimeController, ScriptRuntimeDecision
from module.script.activity_guard import ActivityGuard
from tasks.Restart.server_update import delay_pending_tasks_for_server_update, is_server_update_window
from module.server.log_service import build_error_log_dir_name

_log_switch_lock = threading.Lock()#线程锁


class Script:
    def __init__(self, config_name: str ='oas') -> None:
        logger.hr('Start', level=0)
        self.server = None
        self.state_queue: Queue = None
        self._emulator_down = False
        self.runtime = ScriptRuntimeController(self)
        self.gui_update_task: Callable = None  # 回调函数, gui进程注册当每次config更新任务的时候更新gui的信息
        self.config_name = config_name
        self.startup_task_order = StartupTaskOrder()
        # Skip first restart
        self.is_first_task = True
        # Failure count of tasks
        # Key: str, task name, value: int, failure count
        self.failure_record = {}
        self._error_restart_count = 0
        self._error_restart_pending = False
        self.last_task_runtime_outcome: dict[str, Any] | None = None
        # 运行loop的线程
        self.loop_thread: Thread = None
        # 低配模式属于进程级运行参数，只在脚本进程创建时读取一次。
        # OASX 中途修改配置不会影响正在运行的脚本。
        self.low_spec_mode = bool(self.config.script.device.low_spec_mode)
        set_image_low_spec_mode(self.low_spec_mode)
        set_ocr_low_spec_mode(self.low_spec_mode)
        # 低配模式与普通模式统一使用现有 PaddleOCR medium 模型，
        # 避免小模型降低关键文字的识别稳定性。
        set_ocr_model_size('medium')
        self.resource_precache_enable = bool(
            self.config.script.device.resource_precache_enable
        )
        if self.low_spec_mode:
            logger.info(
                'Low spec mode enabled: frame cache=10s, '
                'OCR model=medium, OCR timeout=30s, OCR cache=2s, '
                'image threshold unchanged'
            )

    @cached_property
    def config(self) -> "Config":
        try:
            from module.config.config import Config
            config = Config(config_name=self.config_name)
            config.startup_task_order = self.startup_task_order
            device = self.__dict__.get('device')
            if device is not None:
                # The device is shared across tasks; keep its live settings
                # bound to the same configuration used by the scheduler.
                device.config = config
            return config
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    @cached_property
    def device(self) -> Device | None:
        try:
            from module.device.device import Device
            device = Device(config=self.config)
            return device
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    @cached_property
    def checker(self):
        """
        占位函数，在alas中是检查服务器是否正常的
        :return:
        """
        return None

    def save_error_log(self):
        """
        保存错误现场到 ./log/error/<script_name>_<timestamp_ms>。

        保存内容包括:
        - 最近一段截图, 文件名为时间戳 PNG。
        - 当前脚本日志的截取内容, 文件名为 log.txt。

        说明:
        - 新错误目录名会带上脚本名, 便于前端区分不同脚本产生的错误。
        - 目录名和脚本名都会经过统一净化, 避免路径注入。
        """
        from module.base.utils import save_image
        from module.handler.sensitive_info import (handle_sensitive_image,
                                                   handle_sensitive_logs)
        if self.config.script.error.save_error:
            if not os.path.exists('./log/error'):
                os.mkdir('./log/error')
            # 用统一规则生成错误目录名, 目录格式为 <script_name>_<timestamp_ms>。
            folder_name = build_error_log_dir_name(self.config_name, int(time.time() * 1000))
            folder = f'./log/error/{folder_name}'
            logger.warning(f'Saving error: {folder}')
            os.mkdir(folder)
            for data in self.device.screenshot_deque:
                image_time = datetime.strftime(data['time'], '%Y-%m-%d_%H-%M-%S-%f')
                image = handle_sensitive_image(data['image'])
                save_image(image, f'{folder}/{image_time}.png')
            with open(logger.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                start = 0
                for index, line in enumerate(lines):
                    line = line.strip(' \r\t\n')
                    if re.match('^═{15,}$', line):
                        start = index
                lines = lines[start - 2:]
                lines = handle_sensitive_logs(lines)
            with open(f'{folder}/log.txt', 'w', encoding='utf-8') as f:
                f.writelines(lines)

    def init_server(self, port: int) -> int:
        """
        初始化zerorpc服务，返回端口号
        :return:
        """
        self.server = zerorpc.Server(self)
        try:
            self.server.bind(f'tcp://127.0.0.1:{port}')
            return port
        except zmq.error.ZMQError:
            logger.error(f"Ocr server cannot bind on port {port}")
            return None

    def run_server(self) -> None:
        """
        启动zerorpc服务
        :return:
        """
        self.server.run()

    def gui_args(self, task: str) -> str:
        """
        获取给gui显示的参数
        :return:
        """
        return self.config.gui_args(task=task)

    def gui_menu(self) -> str:
        """
        获取给gui显示的菜单
        :return:
        """
        return self.config.gui_menu

    def gui_task(self, task: str) -> str:
        """
        获取给gui显示的任务 的参数的具体值
        :return:
        """
        return self.config.model.gui_task(task=task)

    def gui_set_task(self, task: str, group: str, argument: str, value) -> bool:
        """
        设置给gui显示的任务 的参数的具体值
        :return:
        """
        # 验证参数
        task = convert_to_underscore(task)
        group = convert_to_underscore(group)
        argument = convert_to_underscore(argument)
        # pandtic验证
        if isinstance(value, str):
            if len(value) == 8:
                try:
                    value = datetime.strptime(value, '%H:%M:%S').time()
                except ValueError:
                    pass


        path = f'{task}.{group}.{argument}'
        task_object = getattr(self.config.model, task, None)
        group_object = getattr(task_object, group, None)
        argument_object = getattr(group_object, argument, None)

        if argument_object is None:
            logger.error(f'Set arg {task}.{group}.{argument}.{value} failed')
            return False

        try:
            setattr(group_object, argument, value)
            argument_object = getattr(group_object, argument, None)
            logger.info(f'Set arg {task}.{group}.{argument}.{argument_object}')
            self.config.save()  # 我是没有想到什么方法可以使得属性改变自动保存的
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    @zerorpc.stream
    def gui_mirror_image(self):
        """
        获取给gui显示的镜像
        :return: cv2的对象将 numpy 数组转换为字节串。接下来MsgPack 进行序列化发送方将图像数据转换为字节串
        """
        # return msgpack.packb(cv2.imencode('.jpg', self.device.screenshot())[1].tobytes())
        img = cv2.cvtColor(self.device.screenshot(), cv2.COLOR_RGB2BGR)
        self.device.stuck_record_clear()
        ret, buffer = cv2.imencode('.jpg', img)
        yield buffer.tobytes()

    def _gui_update_tasks(self) -> None:
        """
        获取更新任务后 pending waiting 的任务 和 当前的任务的数据。打包给gui显示
        :return:
        """
        schedule = self.config.get_schedule_data()
        data = {"task": schedule["running"],
                "pending": schedule["pending"], "waiting": schedule["waiting"]}

        if self.gui_update_task is not None:
            self.gui_update_task(data)

    def _gui_set_status(self, status: str) -> None:
        """
        设置给gui显示的状态
        :param status: 可以在gui中显示的状态 有 "Init", "Empty"(不显示), "Run"(运行中), "Error", "Free"(空闲)
        :return:
        """
        data = {"status": status}
        if self.gui_update_task is not None:
            self.gui_update_task(data)

    def gui_task_list(self) -> str:
        """
        获取给gui显示的任务列表
        :return:
        """
        result = {}
        for key, value in self.config.model.dict().items():
            if isinstance(value, str):
                continue
            if key == "restart":
                continue
            if "scheduler" not in value:
                continue

            scheduler = value["scheduler"]
            item = {"enable": scheduler["enable"],
                    "next_run": str(scheduler["next_run"])}
            key = self.config.model.type(key)
            result[key] = item
        return json.dumps(result)

    def wait_until(self, future):
        """
        Wait until a specific time.

        Args:
            future (datetime):

        Returns:
            bool: True if wait finished, False if config changed.
        """
        future = future + timedelta(seconds=1)
        self.config.start_watching()
        next_invitation_check = 0
        while 1:
            if datetime.now() > future:
                return True
            if self.config.manual_store.pending():
                return False
            if (self.runtime.idle_waiting and not self.runtime._is_server_update_wait_active()
                    and self.config.cooperation_store.pending()):
                return False
            now_monotonic = time.monotonic()
            if now_monotonic >= next_invitation_check:
                handled_invitation = self.runtime.poll_idle_invitation()
                next_invitation_check = time.monotonic() + 5
                if handled_invitation and self.config.cooperation_store.pending():
                    return False
            # if self.stop_event is not None:
            #     if self.stop_event.is_set():
            #         logger.info("Update event detected")
            #         logger.info(f"[{self.config_name}] exited. Reason: Update")
            #         exit(0)

            time.sleep(1)

            if self.config.should_reload():
                return False

    @cached_property
    def activity_guard(self):
        return ActivityGuard(lambda: self.config, self.config_name,
                             refresh=self._refresh_activity_config)

    def _refresh_activity_config(self):
        event = self.config.config_reload_event
        # Current server processes do not supply a shared reload event. Poll
        # metadata too, so a long rest can respond to saved frontend settings.
        stamp = Path(filepath_config(self.config_name)).stat().st_mtime_ns
        previous = getattr(self, '_activity_config_stamp', stamp)
        if stamp != previous or (event is not None and event.is_set()):
            if event is not None:
                event.clear()
            self.config.reload()
            self.config.scheduler_update_dt = None
        self._activity_config_stamp = stamp

    def get_next_task(self) -> str:
        """
        获取下一个任务的名字, 大驼峰。
        :return:
        """
        while True:
            self.config.reload(prune_manual=True)
            task = self.config.get_next()
            # 驻守资格来自当前启用配置及普通计划，不能只依赖上次任务在
            # 当前进程留下的结束标记：手动进入挑战页也可恢复监听。
            if (self.config.meta_demon.scheduler.enable
                    and not getattr(task, 'manual_request', None)
                    and task.next_run > datetime.now()):
                logger.debug('超鬼王已启用，进入驻守助战检查')
                self.run_meta_demon_resident()
                if self._error_restart_pending:
                    return 'Restart'
                self.config.reload(prune_manual=True)
                task = self.config.get_next()
            self.config.task = task
            if self.state_queue:
                self.publish_schedule()
            now = datetime.now()
            # 任务时间到了返回任务名称
            if task.next_run <= now:
                if (not getattr(task, 'manual_request', None)
                        and (getattr(task, 'cooperation_request', None) or not self.config.is_manual(task.command))
                        and self.activity_guard.checkpoint(allow_manual_interrupt=True)):
                    continue
                return task.command
            self.activity_guard.reset_continuous()
            # 根据策略执行等待逻辑
            decision = self.runtime.handle_wait_during_idle(task.next_run)
            if decision == ScriptRuntimeDecision.RESCHEDULE:
                logger.info('Idle wait requested scheduler refresh, reload config and reschedule')
                del_cached_property(self, "config")
            elif decision == ScriptRuntimeDecision.FAILED:
                logger.warning('Idle wait preparation failed, reload config and retry scheduling')
                del_cached_property(self, "config")

    def exception_handler(self, e: Exception, command: str) -> None:
        # 处理御魂溢出
        from tasks.Utils.post_diagnotor import PostDiagnotor, AnalyzeType
        image = getattr(self.device, 'image', None)
        # image为None则不做处理
        if image is None:
            return
        analyse_type = PostDiagnotor().handle(e=e, command=command, image=image)
        if analyse_type == AnalyzeType.SoulOverflow:
            self.config.task_call('SoulsTidy')
            time.sleep(1)

    def _reset_task_runtime_outcome(self) -> None:
        self.last_task_runtime_outcome = None
        if 'config' in self.__dict__:
            self.config.task_runtime_outcome = None

    def _set_task_runtime_outcome(self, task: str, status: str, wait_until: datetime | None = None) -> None:
        outcome = {
            'task': task,
            'status': status,
        }
        if wait_until is not None:
            outcome['wait_until'] = wait_until
        self.last_task_runtime_outcome = outcome
        if 'config' in self.__dict__:
            self.config.task_runtime_outcome = outcome

    def _capture_task_runtime_outcome(self, command: str) -> None:
        outcome = getattr(self.config, 'task_runtime_outcome', None)
        self.last_task_runtime_outcome = outcome if isinstance(outcome, dict) else None
        if self.last_task_runtime_outcome is None:
            return
        status = self.last_task_runtime_outcome.get('status')
        if status == 'server_update_delayed':
            wait_until = self.last_task_runtime_outcome.get('wait_until')
            logger.info(f'{command} runtime outcome: server_update_delayed (wait_until={wait_until})')
            if isinstance(wait_until, datetime):
                self.runtime.server_update_wait_until = wait_until
                self.runtime.server_update_wait_log_until = None
            return
        if command != 'Restart':
            return
        if status == 'recovered':
            logger.info('Restart runtime outcome: recovered')
            return
        logger.info(f'Restart runtime outcome: {status}')

    def _delay_tasks_for_server_update(self, task: str, reason: str) -> bool:
        if not is_server_update_window():
            return False

        delay_target = delay_pending_tasks_for_server_update(self.config, reason=reason)
        self._set_task_runtime_outcome(task=task, status='server_update_delayed', wait_until=delay_target)
        return True

    def prepare_main_page(self) -> bool:
        """Prepare the courtyard once when entering idle wait without loading a separate task."""
        from module.atom.click import RuleClick
        from tasks.GameUi.game_ui import GameUi
        from tasks.GameUi.page import page_main

        self._reset_task_runtime_outcome()
        RuleClick.reset_task_points()
        set_ocr_logging_enabled(self.config.global_game.ocr.save_ocr_log)
        try:
            self.device.stuck_record_clear()
            self.device.screenshot()
            return bool(GameUi(config=self.config, device=self.device).ui_goto_page(page_main))
        except (GamePageUnknownError, GameStuckError, GameTooManyClickError, GameNotRunningError) as exc:
            if self._delay_tasks_for_server_update(
                    task='IdleMainPage', reason=f'{type(exc).__name__} while preparing idle courtyard'):
                self._capture_task_runtime_outcome('IdleMainPage')
                return False
            self._handle_task_exception(exc, 'IdleMainPage')
            return False
        except Exception as exc:
            self._handle_task_exception(exc, 'IdleMainPage')
            return False

    @cached_property
    def immediate_execution(self):
        from module.script.immediate import ImmediateExecution
        return ImmediateExecution(self)

    def publish_schedule(self):
        if self.state_queue:
            self.state_queue.put({'_task_pid': os.getpid(),
                                  '_active_task': self.config.model.running_task,
                                  'schedule': self.config.get_schedule_data()})

    def _finish_task_page(self, command: str) -> None:
        """正常结束后确认庭院；超鬼王保留活动页供驻守使用。"""
        if command in ('MetaDemon', 'Restart', 'GameStartup'):
            return
        outcome = getattr(self.config, 'task_runtime_outcome', None)
        if isinstance(outcome, dict) and outcome.get('status') == 'server_update_delayed':
            return
        from tasks.GameUi.game_ui import GameUi
        from tasks.GameUi.page import page_main

        logger.info(f'{command} 任务结束，返回庭院')
        self.device.screenshot()
        if not GameUi(config=self.config, device=self.device).ui_goto_page(page_main):
            raise GameStuckError(f'{command} 任务结束后返回庭院失败')
        self.runtime.idle_main_prepared = True

    def run_meta_demon_resident(self):
        """Run observation through the normal device/guard/error lifecycle."""
        from module.config.config import Function
        # Observation must not start the game or run environment preparation,
        # which may navigate away from the page selected by the user.
        device = self.__dict__.get('device')
        if (not self.config.meta_demon.scheduler.enable
                or device is None or self._emulator_down
                or self.runtime._is_server_update_wait_active()
                or not device.app_is_running()):
            return
        previous = self.config.task
        previous_activity = self.config.__dict__.get('meta_demon_resident_activity')

        def activity(active):
            if active:
                # Assistance may leave the courtyard confirmed by the previous
                # task. Disabling residency must restore the normal idle policy.
                self.runtime.idle_main_prepared = False
            command = 'MetaDemon' if active else ''
            if self.config.model.running_task != command:
                self.config.model.running_task = command
                self.publish_schedule()

        self.config.meta_demon_resident_activity = activity
        self.config.task = Function('meta_demon', self.config.model.model_dump()['meta_demon'])
        try:
            self.config.model.running_task = ''
            self.publish_schedule()
            self.device.stuck_record_clear()
            self.device.click_record_clear()
            RuleScatter.begin_task('MetaDemon')
            try:
                self.run('MetaDemon', resident=True)
            finally:
                RuleScatter.end_task('MetaDemon')
        finally:
            self.config.model.running_task = ''
            self.config.task = previous
            if previous_activity is None:
                self.config.__dict__.pop('meta_demon_resident_activity', None)
            else:
                self.config.meta_demon_resident_activity = previous_activity
            self.publish_schedule()

    def run(self, command: str, *, resident=False) -> bool:
        """
        :param command:  大写驼峰命名的任务名字
        :return:
        """
        from module.config.capabilities import unavailable_reason
        reason = unavailable_reason(command)
        if reason:
            logger.error(reason)
            return False
        if command == 'start' or command == 'goto_main':
            logger.error(f'Invalid command `{command}`')

        if command == 'Restart':
            self._ensure_restart_enabled()
        self.config.immediate_checkpoint = self.immediate_execution.checkpoint
        self._reset_task_runtime_outcome()
        from module.atom.click import RuleClick
        RuleClick.reset_task_points()
        set_ocr_logging_enabled(self.config.global_game.ocr.save_ocr_log)
        guard = self.activity_guard
        # Also applies to recovery runs which bypass get_next_task().
        from module.config.config import Config
        manual = False if resident else Config.is_manual(self.config, command)
        selected = getattr(self.config, 'task', None)
        if getattr(selected, 'cooperation_request', None):
            manual = False
        if getattr(selected, 'command', None) == command and getattr(selected, 'manual_request', None):
            manual = True
        if command in ('GameStartup', 'Restart') and getattr(selected, 'manual_request', None):
            manual = True
        if resident:
            manual = False  # Automatic listening/assists never inherit an exemption.
        waited = False if manual else guard.checkpoint()
        device = self.device
        if waited:
            device.stuck_record_clear()
            device.click_record_clear()
            device.invalidate_image_batch_cache()
        previous_guard = getattr(device, 'activity_guard', None)
        device.activity_guard = None if manual else guard
        guard.start()
        from module.config.idle import IDLE, IdleExecution, limits_for
        from module.config.utils import convert_to_underscore
        idle_execution = None
        try:
            try:
                idle_key = convert_to_underscore(command)
                idle_model = getattr(getattr(self.config, 'model', None), idle_key, None)
                idle_scheduler = getattr(idle_model, 'scheduler', None)
                if (not resident and idle_scheduler is not None and idle_scheduler.execution_mode == IDLE
                        and not getattr(selected, 'cooperation_request', None)
                        and not self._error_restart_pending):
                    if limits_for(idle_key, idle_model) is None:
                        logger.warning(f'{command}: 闲时任务尚未适配或缺少有效目标限制')
                        return True
                    idle_execution = IdleExecution(self.config, idle_key)
                    self.config.idle_execution = idle_execution
                if command == 'GameStartup':
                    # 启动配置的环境准备不属于定时/异常 Restart，不停止应用、
                    # 不改重启调度，也不执行重启任务的每日附加操作。
                    if self._delay_tasks_for_server_update(command, 'Initial game startup'):
                        return False
                    from tasks.Restart.login import LoginHandler
                    self.device.app_start()
                    return bool(LoginHandler(config=self.config, device=self.device).app_handle_login())
                self.device.screenshot()
                module_name = 'script_task'
                module_path = str(Path.cwd() / 'tasks' / command / (module_name + '.py'))
                logger.debug(f'module_path: {module_path}, module_name: {module_name}')
                task_module = load_module(module_name, module_path)
                instance = task_module.ScriptTask(config=self.config, device=self.device)
                if resident:
                    instance.run_resident()
                else:
                    try:
                        instance.run()
                    except TaskEnd:
                        self._finish_task_page(command)
                        raise
                    self._finish_task_page(command)
                    return True
            finally:
                # Include failing tasks, before error handling/recovery starts.
                guard.finish()
                if idle_execution is not None:
                    idle_execution.finish()
        except Exception as e:
            return self._handle_task_exception(e, command)
        finally:
            device.activity_guard = previous_guard
            self.config.__dict__.pop('idle_execution', None)
            requested = self.config.__dict__.pop('meta_demon_residency_requested', None)
            if requested is not None:
                self.runtime.meta_demon_residency_requested = bool(requested)
        return False

    def loop(self):
        """
        Main loop of scheduler.
        :return:
        """
        with _log_switch_lock:
            logger.set_file_logger(self.config_name, do_cleanup=True)
        start_day = date.today()
        logger.info(f'Start scheduler loop: {self.config_name}')
        if self.resource_precache_enable:
            logger.info('Resource precache enabled: warming up OCR model')
            try:
                get_ocr_client().warmup()
            except Exception as exc:
                logger.exception(exc)
                raise ScriptError('OCR model resource precache failed') from exc
            logger.info('Resource precache completed; scheduler tasks can start')
        self.config.model.running_task = ''

        # Snapshot once per process start, after warmup; UI overview refreshes
        # and later Config object replacements only reuse the resulting ranks.
        self.config.update_scheduler()
        self.startup_task_order.initialize(
            self.config.pending_task,
            enabled=self.config.script.optimization.startup_task_shuffle_enable,
        )
        if self.state_queue is not None:
            self.state_queue.put({'_startup_task_order': self.startup_task_order,
                                  '_startup_pid': os.getpid(),
                                  'schedule': self.config.get_schedule_data()})

        # Update GUI 防呆, 读取设置并立刻显示后台模拟器到前台
        if not self.config.script.device.run_background_only and IS_WINDOWS:
            from module.device.platform2.platform_windows import minimize_by_name, show_window_by_name
            target_window_name = self.config.script.device.handle  # 在这里输入你的具体窗口名称
            if self.config.script.device.emulator_window_minimize:
                minimize_by_name(target_window_name)
                logger.info(f'重新显示: {target_window_name}')
            else:
                show_window_by_name(target_window_name)
                
        while 1:
            if date.today() > start_day:
                with _log_switch_lock:
                    logger.set_file_logger(self.config_name, do_cleanup=True)
                start_day = date.today()

            task = ""
            try:
                # Get task
                task = 'Restart' if self._error_restart_pending else self.get_next_task()
                manual_request = (None if self._error_restart_pending else
                                  getattr(getattr(self.config, 'task', None), 'manual_request', None))
                cooperation_task = (None if self._error_restart_pending else getattr(self.config, 'task', None))
                # Skip first restart
                if self.is_first_task and task == 'Restart' and not self._error_restart_pending and not manual_request:
                    logger.info('Skip task `Restart` at scheduler start')
                    self.config.task_delay(task='Restart', success=True, server=True)
                    del_cached_property(self, 'config')
                    continue
                decision = self.runtime.prepare_task_execution(task)
            except Exception as e:
                self._handle_task_exception(e, task)
                # 本轮 prepare 失败,重新调度
                del_cached_property(self, 'config')
                continue

            if decision == ScriptRuntimeDecision.RESCHEDULE:
                logger.info(f'Runtime preparation for `{task}` requested reschedule, reload config and retry scheduling')
                del_cached_property(self, 'config')
                continue
            if decision == ScriptRuntimeDecision.FAILED:
                logger.warning(f'Runtime preparation for `{task}` failed, reload config and retry scheduling')
                del_cached_property(self, 'config')
                continue

            # Run
            if getattr(cooperation_task, 'cooperation_request', None):
                if not self.config.consume_cooperation_request(cooperation_task):
                    continue
            if manual_request:
                from module.config.utils import convert_to_underscore
                key = convert_to_underscore(task)
                # Preparation may have reloaded configuration. Recheck before
                # consuming exactly the selected request, immediately before run.
                self.config.reload()
                scheduler = getattr(self.config.model, key).scheduler
                from module.config.idle import IDLE
                if (not scheduler.enable or not self.config.is_manual(task)
                        or not self.config.manual_store.consume(key, manual_request)):
                    continue
            logger.info(f'Scheduler: Start task `{task}`')
            self.device.stuck_record_clear()
            self.device.click_record_clear()
            logger.hr(task, level=0)
            self.config.model.running_task = task
            self.publish_schedule()
            RuleScatter.begin_task(task)
            try:
                success = self.run(inflection.camelize(task))
            finally:
                RuleScatter.end_task(task)
            self.config.model.running_task = ''
            self.publish_schedule()
            logger.info(f'Scheduler: End task `{task}`')
            self.is_first_task = False
            if task == 'Restart' and success:
                self._error_restart_pending = False

            # Check failures
            # failed = deep_get(self.failure_record, keys=task, default=0)
            failed = self.failure_record[task] if task in self.failure_record else 0
            failed = 0 if success else failed + 1
            # deep_set(self.failure_record, keys=task, value=failed)
            self.failure_record[task] = failed
            if failed > self.config.model.restart.restart_config.error_restart_limit:
                logger.critical(f"Task `{task}` failed again after recovery.")
                logger.critical("Possible reason #1: You haven't used it correctly. "
                                "Please read the help text of the options.")
                logger.critical("Possible reason #2: There is a problem with this task. "
                                "Please contact developers or try to fix it yourself.")
                logger.critical('Request human takeover')
                # 恢复后再次失败时停止脚本。
                self.config.notifier.push(
                    title=f'{I18n.trans_zh_cn(task)}{task}',
                    content=f"<{self.config_name}> 任务恢复后再次失败，脚本已停止，请上线查看"
                )
                # 关闭模拟器
                if self.config.script.error.error_repeated:
                    self.device.emulator_stop()
                exit(1)

            if success:
                del_cached_property(self, 'config')
                continue
            elif self.config.script.error.handle_error:
                # self.config.task_delay(success=False)
                del_cached_property(self, 'config')
                # self.checker.check_now()
                continue
            else:
                break

    def _ensure_restart_enabled(self) -> None:
        """所有重启入口均尊重任务启用开关，禁止绕过用户配置。"""
        if self.config.model.restart.scheduler.enable:
            return
        self._error_restart_pending = False
        logger.critical('Restart task is disabled; stop script instead of restarting game')
        self.config.notifier.push(
            title='Restart',
            content=f'<{self.config_name}> 重启任务未启用，无法自动恢复，脚本已停止，请手动处理',
        )
        raise SystemExit(1)

    def _request_error_restart(self, command: str) -> None:
        """按重启任务配置限制本次脚本运行的异常重启次数，强制优先调度。"""
        self._ensure_restart_enabled()
        limit = self.config.model.restart.restart_config.error_restart_limit
        if self._error_restart_count >= limit:
            logger.critical(f'Error restart limit reached ({self._error_restart_count}/{limit}): {command}; stop script')
            self.config.notifier.push(
                title=f'{I18n.trans_zh_cn(command)}{command}',
                content=f'<{self.config_name}> 异常重启次数已达上限 {limit} 次，脚本已停止，请上线查看',
            )
            raise SystemExit(1)
        self._error_restart_count += 1
        logger.warning(f'Error recovery restart {self._error_restart_count}/{limit}: {command}')
        self._error_restart_pending = True
        self.config.task_call('Restart', force_call=False)

    def _handle_task_exception(self, e: Exception, command: str) -> bool:
        """
        统一处理任务执行 / 准备阶段抛出的异常。
        Returns:
            True  -> 视为正常结束或已自动恢复 (例如已 task_call('Restart')),
                     调度器继续推进
            False -> 视为失败,脚本继续运行
        对致命异常 (ScriptError / RequestHumanTakeover / 未识别 Exception)
        在内部直接 exit(1)。
        """
        if isinstance(e, TaskEnd):
            self._capture_task_runtime_outcome(command)
            return True

        if isinstance(e, GameNotRunningError):
            logger.warning(e)
            self.exception_handler(e=e, command=command)
            self._request_error_restart(command)
            return True

        if isinstance(e, (GameStuckError, GameTooManyClickError)):
            logger.error(e)
            self.save_error_log()
            self.exception_handler(e=e, command=command)
            self.config.notifier.push(title=f'{I18n.trans_zh_cn(command)}{command}',
                                      content=f"<{self.config_name}> GameStuckError or GameTooManyClickError")
            self._request_error_restart(command)
            logger.warning('任务异常，10 秒后执行重启恢复；如正在手动操作，请停止脚本')
            self.device.sleep(10)
            return False

        if isinstance(e, GameBugError):
            logger.warning(e)
            self.save_error_log()
            self.exception_handler(e=e, command=command)
            logger.warning('游戏客户端异常，申请重启恢复')
            self._request_error_restart(command)
            self.device.sleep(10)
            return False

        if isinstance(e, GamePageUnknownError):
            logger.info('Game server may be under maintenance or network may be broken, check server status now')
            logger.critical('Game page unknown')
            self.save_error_log()
            self.exception_handler(e=e, command=command)
            self.config.notifier.push(
                title=f'{I18n.trans_zh_cn(command)}{command}',
                content=f"<{self.config_name}> GamePageUnknownError",
            )
            self._request_error_restart(command)
            self.device.sleep(10)
            return False

        if isinstance(e, ScriptError):
            logger.critical(e)
            self.exception_handler(e=e, command=command)
            logger.critical('This is likely to be a mistake of developers, but sometimes just random issues')
            self.config.notifier.push(
                title=f'{I18n.trans_zh_cn(command)}{command}',
                content=f"<{self.config_name}> ScriptError",
            )
            exit(1)

        if isinstance(e, RequestHumanTakeover):
            logger.critical(e)
            self.exception_handler(e=e, command=command)
            logger.critical('Request human takeover')
            self.config.notifier.push(
                title=f'{I18n.trans_zh_cn(command)}{command}',
                content=f"<{self.config_name}> RequestHumanTakeover",
            )
            exit(1)

        # generic
        logger.exception(e)
        self.exception_handler(e=e, command=command)
        self.save_error_log()
        self.config.notifier.push(
            title=f'{I18n.trans_zh_cn(command)}{command}',
            content=f"<{self.config_name}> Exception occured",
        )
        exit(1)
        return False

    def start_loop(self) -> None:
        """
        创建一个线程，运行loop
        :return:
        """
        if self.loop_thread is None:
            self.loop_thread = Thread(target=self.loop, name='Script_loop')
            self.loop_thread.start()


if __name__ == "__main__":
    ensure_image_server_ready()
    ensure_ocr_server_ready()
    script = Script("oas1")
    script.loop()
