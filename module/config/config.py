# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import copy
import datetime
import operator
import threading
import random

from datetime import datetime, timedelta
from cached_property import cached_property
from threading import Lock

from module.base.filter import Filter
from module.config.config_updater import ConfigUpdater
from module.config.config_manual import ConfigManual
from module.config.config_watcher import ConfigWatcher
from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from module.config.config_state import ConfigState
from module.config.scheduler import TaskScheduler
from module.config.idle import IDLE, IdleStore, select_idle
from module.config.utils import *
from module.notify.notify import Notifier

from module.exception import RequestHumanTakeover, ScriptError
from module.logger import logger


class Function:
    def __init__(self, key: str, data: dict):
        """
        输入的是每一个ConfigModel的一个字段对象
        :param data:
        """
        if isinstance(data, dict) is False:
            self.enable = False
            self.command = "Unknown"
            self.next_run = DEFAULT_TIME
            return
        if data.get("scheduler") is None:
            self.enable = False
            self.command = "Unknown"
            self.next_run = DEFAULT_TIME
            return

        self.enable: bool = data['scheduler']['enable']
        self.command: str = ConfigModel.type(key)
        next_run = data['scheduler']['next_run']
        if isinstance(next_run, str):
            next_run = datetime.strptime(next_run, "%Y-%m-%d %H:%M:%S")
        self.next_run: datetime = next_run
        priority = data['scheduler']['priority']
        if isinstance(priority, str):
            priority = int(priority)
        self.priority: int = priority
        if not isinstance(self.priority, int):
            logger.error(f"Invalid priority: {self.priority}")

        # self.enable = deep_get(data, keys="Scheduler.Enable", default=False)
        # self.command = deep_get(data, keys="Scheduler.Command", default="Unknown")
        # self.next_run = deep_get(data, keys="Scheduler.NextRun", default=DEFAULT_TIME)

    def __str__(self):
        enable = "Enable" if self.enable else "Disable"
        return f"{self.command} ({enable}, {self.priority}, {str(self.next_run)})"

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, Function):
            return False

        if self.command == other.command and self.next_run == other.next_run:
            return True
        else:
            return False


def name_to_function(name):
    """
    Args:
        name (str):

    Returns:
        Function:
    """
    function = Function({})
    function.command = name
    function.enable = True
    return function


class Config(ConfigState, ConfigManual, ConfigWatcher, ConfigMenu):

    def __init__(self, config_name: str, task=None) -> None:
        """

        :param config_name:
        :param task:
        """
        super().__init__(config_name)  # 调用 ConfigState 的初始化方法
        super(ConfigManual, self).__init__()
        super(ConfigWatcher, self).__init__()
        super(ConfigMenu, self).__init__()
        self.model = ConfigModel(config_name=config_name)
        self.scheduler_update_dt = None  # 调度器更新时间

    def __getattr__(self, name):
        """
        一开始是打算直接继承ConfigModel的，但是pydantic会接管所有的变量
        故而选择持有ConfigModel
        :param name:
        :return:
        """
        try:
            return getattr(self.model, name)
        except AttributeError:
            # 这个导致 大量的无用log
            # logger.error(f'can not ask this variable {name}')
            return None  # 或者抛出异常，或者返回其他默认值

    @cached_property
    def lock_config(self) -> Lock:
        return Lock()

    @cached_property
    def notifier(self):
        notifier = Notifier(self.model.script.error.notify_config, enable=self.model.script.error.notify_enable)
        notifier.config_name = self.config_name.upper()
        logger.info(f'Notifier: {notifier.config_name}')
        return notifier

    def gui_args(self, task: str) -> str:
        """
        获取给gui显示的参数
        :return:
        """
        return self.model.gui_args(task=task)

    def get_arg(self, task: str, group: str, argument: str):
        """

        :param task:
        :param group:
        :param argument:
        :return: str/int/float
        """
        try:
            return self.data[task][group][argument]
        except:
            logger.exception(f'have no arg {task}.{group}.{argument}')

    def set_arg(self, task: str, group: str, argument: str, value) -> None:
        """

        :param task:
        :param group:
        :param argument:
        :param value:
        :return:
        """
        try:
            self.data[task][group][argument] = value
        except:
            logger.exception(f'have no arg {task}.{group}.{argument}')

    def reload(self):
        self.model = ConfigModel(config_name=self.config_name)

    def save(self) -> None:
        """
        保存配置文件
        :return:
        """
        self.model.write_json(self.config_name, self.model.dict())

    @cached_property
    def idle_store(self):
        return IdleStore(self.config_name)

    def update_scheduler(self) -> None:
        """
        更新调度器， 设置pending_task and waiting_task
        :return:
        """
        pending_task = []
        waiting_task = []
        error = []
        self.scheduler_update_dt = datetime.now()
        for key, value in self.model.dict().items():
            func = Function(key, value)
            if not func.enable:
                continue
            if value['scheduler'].get('execution_mode') == IDLE:
                continue
            if key == 'abyss_shadows' and isinstance(func.next_run, datetime):
                scheduler = self.model.abyss_shadows.scheduler
                effective = max(func.next_run, self.scheduler_update_dt)
                if not scheduler.is_open(effective):
                    func.next_run = scheduler.within_open_window(effective)
            if key == 'demon_retreat' and isinstance(func.next_run, datetime):
                scheduler = self.model.demon_retreat.scheduler
                effective = max(func.next_run, self.scheduler_update_dt)
                if not scheduler.is_open(effective):
                    func.next_run = scheduler.next_weekly_run(effective)
            if key == 'chess':
                blocked = self.idle_store.blocked(key, self.scheduler_update_dt)
                if blocked and isinstance(func.next_run, datetime):
                    func.next_run = max(func.next_run, blocked['until'])
            if not isinstance(func.next_run, datetime):
                error.append(func)
            elif func.next_run < self.scheduler_update_dt:
                pending_task.append(func)
            else:
                waiting_task.append(func)

        # f = Filter(regex=r"(.*)", attr=["command"])
        # f.load(self.SCHEDULER_PRIORITY)
        if pending_task:
            pending_task = TaskScheduler.schedule(rule=self.model.script.optimization.schedule_rule,
                                                  pending=pending_task)
            order = self.__dict__.get('startup_task_order')
            if self.model.script.optimization.startup_task_shuffle_enable:
                # Filter/FIFO do not themselves honor numeric priority. Establish
                # strict groups even when the startup draw did not shuffle.
                pending_task = sorted(pending_task,
                                      key=lambda task: (task.command != 'Restart', task.priority))
                if order is not None:
                    pending_task = order.apply(pending_task, running=self.model.running_task)
            # 防止正在运行的任务被新上来的pending队列中的任务给顶替掉
            if self.model.running_task and pending_task:
                for i, obj in enumerate(pending_task):
                    if obj.command == self.model.running_task:
                        pending_task.insert(0, pending_task.pop(i))
                        logger.info(f'{self.model.running_task} is running')
                        break
        if waiting_task:
            # waiting_task = f.apply(waiting_task)
            waiting_task = sorted(waiting_task, key=operator.attrgetter("next_run"))
        if error:
            pending_task = error + pending_task

        self.pending_task = pending_task
        self.waiting_task = waiting_task
        self.normal_pending_task = pending_task.copy()
        self.normal_waiting_task = waiting_task.copy()
        self.idle_status = []
        idle_keys = [key for key in self.model.model_fields
                     if getattr(getattr(self.model, key), 'scheduler', None) is not None
                     and getattr(self.model, key).scheduler.enable
                     and getattr(self.model, key).scheduler.execution_mode == IDLE]
        if idle_keys:
            candidates, self.idle_status = select_idle(
                self, self.scheduler_update_dt, pending_task, waiting_task)
            if not pending_task and candidates:
                key = candidates[0]
                task = Function(key, self.model.dict()[key])
                task.next_run = self.scheduler_update_dt
                self.pending_task = [task]
            # Wake periodically for goal resets, newly due tasks, and configuration
            # changes. This is a future wakeup only, never an executable fake task.
            elif not pending_task:
                poll = Function(idle_keys[0], self.model.dict()[idle_keys[0]])
                poll.next_run = self.scheduler_update_dt + timedelta(seconds=30)
                if not waiting_task or waiting_task[0].next_run > poll.next_run:
                    self.waiting_task = [poll] + waiting_task

    def get_next(self) -> Function:
        """
        获取下一个要执行的任务
        :return:
        """
        self.update_scheduler()

        if self.pending_task:
            logger.info(f"Pending tasks: {[f.command for f in self.pending_task]}")
            task = self.pending_task[0]
            self.task = task
            logger.attr("Task", task)
            return task

        # 哪怕是没有任务，也要返回一个任务，这样才能保证调度器正常运行
        if self.waiting_task:
            logger.info("No task pending")
            task = copy.deepcopy(self.waiting_task[0])
            # task.next_run = (task.next_run + self.hoarding).replace(microsecond=0)
            logger.attr("Task", task)
            return task
        else:
            logger.critical("No task waiting or pending")
            logger.critical("Please enable at least one task")
            raise RequestHumanTakeover

    def get_schedule_data(self) -> dict[str, dict]:
        """
        按当前配置刷新总览；没有启用任务时返回空列表，不选择执行任务。
        :return:
        """
        self.update_scheduler()
        running = {}
        if self.pending_task:
            task = self.pending_task[0]
            running = {"name": task.command, "next_run": str(task.next_run)}

        pending = []
        for p in self.pending_task[1:]:
            item = {"name": p.command, "next_run": str(p.next_run)}
            pending.append(item)

        waiting = []
        for w in self.waiting_task:
            item = {"name": w.command, "next_run": str(w.next_run)}
            waiting.append(item)

        data = {"running": running, "pending": pending, "waiting": waiting}
        if self.idle_status:
            active = self.model.running_task
            if active and any(item['name'] == active for item in self.idle_status):
                data['running'] = {'name': active, 'next_run': str(self.scheduler_update_dt)}
                data['pending'] = [{'name': task.command, 'next_run': str(task.next_run)}
                                   for task in self.normal_pending_task]
                for item in self.idle_status:
                    if item['name'] == active:
                        item['status'] = '闲时执行中'
            # Idle tasks have their own state rather than their obsolete next_run.
            idle_names = {item['name'] for item in self.idle_status}
            data['waiting'] = [item for item in waiting if item['name'] not in idle_names]
            data['idle'] = self.idle_status
        return data

    def task_call(self, task: str = None, force_call=True):
        """
        回调任务，这会是在任务结束后调用
        :param task: 调用的任务的大写名称
        :param force_call:
        :return:
        """
        task = convert_to_underscore(task)
        if self.model.deep_get(self.model, keys=f'{task}.scheduler.next_run') is None:
            raise ScriptError(f"Task to call: `{task}` does not exist in user config")

        task_enable = self.model.deep_get(self.model, keys=f'{task}.scheduler.enable')
        if self.model.deep_get(self.model, keys=f'{task}.scheduler.execution_mode') == IDLE:
            return False
        if force_call or task_enable:
            logger.info(f"Task call: {task}")
            next_run = datetime.now().replace(
                microsecond=0
            )
            self.model.deep_set(self.model, keys=f'{task}.scheduler.next_run', value=next_run)
            self.save()
            return True
        else:
            logger.info(f"Task call: {task} (skipped because disabled by user)")
            return False

    def task_delay(self, task: str, start_time: datetime = None,
                   success: bool = None, server: bool = True, target: datetime = None) -> None:
        """
        设置下次运行时间  当然这个也是可以重写的
        :param target: 可以自定义的下次运行时间
        :param server: True
        :param success: 判断是成功的还是失败的时间间隔
        :param task: 任务名称，大驼峰的
        :param finish: 是完成任务后的时间为基准还是开始任务的时间为基准
        :return:
        """
        # 加载配置文件
        self.reload()
        # 任务预处理
        if not task:
            task = self.task.command
        task = convert_to_underscore(task)
        task_object = getattr(self.model, task, None)
        if not task_object:
            logger.warning(f'No task named {task}')
            return
        scheduler = getattr(task_object, 'scheduler', None)
        if not scheduler:
            logger.warning(f'No scheduler in {task}')
            return

        if scheduler.execution_mode == IDLE:
            # Old task delays are dormant in idle mode; only the goal adapter
            # may record completion. In particular failure is not completion.
            return

        # 任务开始时间
        if not start_time:
            start_time = datetime.now().replace(microsecond=0)

        # 依次判断是否有自定义的下次运行时间
        run = []
        if task == 'demon_retreat':
            now = datetime.now()
            if target is None:
                if success:
                    run.append(scheduler.next_weekly_run(now, completed=True))
                elif success is not None:
                    retry = max(now, start_time + scheduler.failure_interval)
                    run.append(scheduler.within_open_window(retry))
        elif task == 'wanted_quests' and success is not None:
            if target is None:
                run.append(scheduler.next_refresh_run(datetime.now(), random_delay=True))
        elif success is not None:
            interval = (
                scheduler.success_interval
                if success
                else scheduler.failure_interval
            )
            if isinstance(interval, str):
                interval = timedelta(interval)
            run.append(start_time + interval)
        # if server is not None:
        #     if server:
        #         server = scheduler.server_update
        #         run.append(get_server_next_update(server))
        if target is not None:
            target = [target] if not isinstance(target, list) else target
            target = nearest_future(target)
            run.append(target)

        next_run = None
        # 排序
        if not len(run):
            raise ScriptError(
                "Missing argument in delay_next_run, should set at least one"
            )

        run = min(run).replace(microsecond=0)
        next_run = run
        if task in ('hunt', 'wanted_quests', 'demon_retreat', 'abyss_shadows') and target is not None:
            next_run = target.replace(microsecond=0)

        if task == 'abyss_shadows':
            now = datetime.now().replace(microsecond=0)
            if target is None and success and server:
                next_run = scheduler.next_daily_run(now)
            next_run = scheduler.within_open_window(max(now, next_run))
            if target is None:
                next_run = scheduler.add_random_delay(next_run)
        elif task == 'demon_retreat':
            next_run = scheduler.within_open_window(max(datetime.now().replace(microsecond=0), next_run))
            if target is None:
                next_run = scheduler.add_random_delay(next_run)
        elif server and task == 'hunt':
            # 显式目标及失败重试保持原时间；成功后按目标日期选择活动。
            if target is None and success:
                days = max(scheduler.delay_date, scheduler.success_interval.days, 1)
                day = (datetime.now() + timedelta(days=days)).date()
                next_run = datetime.combine(day, scheduler.execution_time(day))
                float_seconds = (scheduler.float_time.hour * 3600 +
                                 scheduler.float_time.minute * 60 +
                                 scheduler.float_time.second)
                next_run += timedelta(seconds=random.randint(0, float_seconds))
        elif server and task != 'wanted_quests' and hasattr(scheduler, 'server_update'):
            # 悬赏每天两轮，始终屏蔽通用的“非9点强制次日”规则。
            # 加入随机延迟时间
            float_seconds = (scheduler.float_time.hour * 3600 +
                             scheduler.float_time.minute * 60 +
                             scheduler.float_time.second)
            random_float = random.randint(0, float_seconds)
            # 如果有强制运行时间
            if scheduler.server_update == time(hour=9):
                next_run += timedelta(seconds=random_float)
            else:
                next_run = parse_tomorrow_server(scheduler.server_update, scheduler.delay_date, random_float)

        # 将这些连接起来，方便日志输出
        kv = dict_to_kv(
            {
                "success": success,
                "server_update": server,
                "target": target,
            },
            allow_none=False,
        )
        # logger.info(f"Delay task `{task}` to {next_run} ({kv})")

        # 保证线程安全的
        self.lock_config.acquire()
        try:
            scheduler.next_run = next_run
            self.save()
        finally:
            self.lock_config.release()
        # 设置
        logger.attr(f'{task}.scheduler.next_run', next_run)


if __name__ == '__main__':
    config = Config(config_name='oas1')
    config.notifier.push(title="0000", content="dddddddd")

    # print(config.get_next())
