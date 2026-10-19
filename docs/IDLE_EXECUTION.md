# 闲时执行通用接口

所有任务共用配置、调度、目标存储及安全退出接口。
**目前已注册六道之门（椒图、觉）与百鬼棋局的整局适配，详见 `docs/SIX_REALMS_IDLE.md`、`docs/CHESS_IDLE.md`；其他任务仍显示“待适配”，不会进入游戏执行。**
不能仅因某任务有 `limit_count` 或 `limit_time` 就视为完成适配：现有任务在
计数时机、领奖、离队、加成关闭及自然结束条件上不同，须逐项确认。

## 配置与界面

所有继承 `tasks.Component.config_scheduler.Scheduler` 的任务都有：

- `execution_mode`：互斥的“定时执行”（默认）、“闲时执行”与“手动执行”；手动模式见 `docs/MANUAL_EXECUTION.md`。
- `idle_goal`：每日目标（默认）、每周目标、本次目标。
- `idle_start_minutes`：开始或恢复余量 Y，默认15分钟。
- `idle_stop_minutes`：结算后让位余量 X，默认5分钟，要求 Y > X >= 0。

切换模式保留旧配置值。闲时模式忽略旧固定执行时间；前端隐藏 next_run、
成功/失败间隔、固定执行时间（包括悬赏早晚及狩猎战时间）、强制日期间隔和随机延迟，
显示目标及 X/Y。接口通过 `execution_modes` 字段传递可见性，前端草稿切换立即响应。
隐藏字段不会删除或重写。原本任务专用的隐藏字段继续隐藏。

## 调度规则

先执行所有已启用且到期的普通任务，再考虑闲时任务。距离最近的普通等待任务
严格超过 Y 分钟才开始或恢复；没有普通等待任务时允许开始。多个闲时候选按
数字优先级稳定排序。本阶段未引入批次轮转。

只在任务显式确认领奖结束的安全检查点判断让位：普通任务已到期，或距离下一
普通任务 <= X 分钟时清理并返回庭院。不中断战斗，不预测下一轮耗时。
单轮超长仍可能推迟普通任务，由用户设置 X/Y 预留余量。
守卫休息约束继续生效，设备卡死检测保持启用。

`task_delay()`、`task_call()` 不再改变闲时任务的旧调度时间，也不能绕过目标与
空闲判断。通用成功、失败、TaskEnd 不代表闲时目标完成。强制异常恢复仍走原恢复入口。
未适配、目标已完成、空档不足或失败冷却的任务不会作为立即执行任务返回；
执行器最多30秒重新检查一次，普通定时任务更早到期时按其时间唤醒。
总览新增独立 `idle` 列表，前端显示状态及完成次数，不把旧 next_run 当作闲时计划。

## 目标与持久化

`module/config/idle.py` 使用忽略目录 `config/activity/idle.sqlite3`，按配置、任务、
目标类型及周期隔离进度。累计完成次数与实际运行秒数，任一有效上限达到即完成；
零表示该项未启用，两项均无有效上限且没有显式自然目标时不运行。
`NATURAL_GOALS` 提供显式自然完成条件：例如棋局周目标刷满币，允许 `(0, 0)`，
仍须任务在可靠识别后显式完成，不能使用虚构的大次数或默认 TaskEnd 推断。
同一数据库的 `task_blocks` 保存独立于目标类型/周期/会话的任务停刷期限；
`task_state` 保存任务私有进度（如棋局保段位剩余退出局数）。旧数据库增量建表，
不重写已有目标；配置之间隔离。

- 每日默认按本地零点刷新；每周默认按本地周一零点刷新。
- 本次目标在用户通过 HTTP/WebSocket **成功停止配置**后切换会话，下次启动重新累计。
  配置热重载、意外进程退出、后端正常关闭不会重置。本阶段以服务端配置启动入口为准。
- 让位保留进度，等待不计时；通过公共运行守卫发生的任务内休息扣除。
  任务自有等待仍按其原本运行时间口径累计。
- 跨周期战斗在安全检查点结算给开始该执行片段时的周期，再退出并重新调度新周期。
- 异常片段仍记耗时，不凭异常推断完成次数；非让位退出统一至少冷却1分钟，
  避免任务原生结束条件未适配时反复重入。这不是隐藏的旧失败间隔。

## 后续逐任务适配

1. 在 `module/config/idle.py:ADAPTERS` 注册任务的下划线名称，函数参数为该任务
   配置模型，返回原有 `(次数上限, 秒数上限)`；时间须换算为秒。不修改用户原始配置。
2. 任务通过继承自 `BaseTaskParent` 的 `idle_remaining_limits()` 获取本片段剩余
   `(次数, 秒数)`；None 表示该项未启用，接口本身返回 None 表示定时模式。
   使用局部变量处理剩余量，不能因任务初始化重置累计目标。
3. 每轮奖励、延迟奖励处理完成且不会自动开启下一场时，调用
   `idle_checkpoint(completed=本次完成次数增量)`。增量只提交一次，不能传总累计值。
   个性化自然目标确认完成时可以传 `goal_complete=True`。
4. 覆盖 `idle_return_to_main()`：离队、关闭本任务开启的加成、清理私有状态并确认
   回到庭院。失败必须抛出异常，不能伪造成功；不能在该清理方法内递归调用检查点。
   基类默认抛错，防止漏适配的任务带着脏状态切换。
5. 让位抛出 `IdleYield(TaskEnd)`；任务自身清理或异常包装不能吞掉它，也不能把它
   当普通成功、失败或重置用户目标。次数、时限、资源、活动开放和原生周目标均需
   同时验证。没有原有限制的任务后续单独定义目标适配，不自动按一次运行完成。

六道之门及百鬼棋局已完成整局接口接入及离线模拟验证，尚未完成设备、OCR 或游戏流程验证。
其他任务不能仅因具备次数/时间字段就注册为可执行。

## 离线验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_chess_idle dev_tools.test_six_realms_idle dev_tools.test_idle_schedule dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_template dev_tools.test_activity_guard dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_config_lifecycle dev_tools.test_runtime_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

前端源码：`D:\yys\SourceCodes\oasx-monitor-source`，测试 `test/idle_args_test.dart`、
`test/args_test.dart`；接口回退兼容没有可见性元数据或 idle 总览的旧后端。
