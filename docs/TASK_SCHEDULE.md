# 默认任务调度与总览

## 空闲等待与回庭院

“前往主界面”（`goto_main`）及“关闭模拟器&前往主界面”在没有到期待执行任务时保持当前游戏页面，不再为了等待而强制返回庭院或启动游戏。模拟器关闭阈值和提前预热时间继续生效，预热只拉起模拟器，不提前导航。

主调度器等待结束后重新读取配置并选择任务，在任务实际执行前确认游戏运行，再通过公共导航回庭院。该准备请求仅保存在运行时内存，配置重载和首次打开游戏后的重新调度会保留；成功返回庭院后清除，连续到期任务沿用各自的页面导航。导航失败时不执行目标任务，停服继续按原逻辑延后，异常重启先交给 Restart。停服期间关闭游戏、其他关闭游戏/模拟器策略及任务内部的领奖、退出和安全让位清理沿用原规则。

无需重新构建前端，停止并重新启动配置进程后生效。离线验证（不操作游戏）：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_runtime_idle dev_tools.test_game_startup dev_tools.test_restart_compatibility dev_tools.test_task_schedule dev_tools.test_manual_schedule dev_tools.test_immediate_preemption dev_tools.test_activity_guard dev_tools.test_task_startup dev_tools.test_server_startup -q
```

## 调度顺序

默认使用 `Filter` 调度规则，任务顺序定义于
`module/config/config_manual.py` 的 `SCHEDULER_PRIORITY`。
`Config.update_scheduler()` 将已启用的任务按下次运行时间划为待执行或等待，
待执行任务交由 `TaskScheduler.schedule()` 排序。总览与任务执行共用这一队列。

2026-10-17 修复顺序表遗漏导致任务到期后消失的问题：活动爬塔、活动爬塔2、
简单爬塔、现世年兽、彼世逢魔、自动樱饼、主线剧情，以及当时核查发现的寮礼物（现已按用户要求删除）。
旧实现把顺序表同时当作允许列表，遗漏任务虽然能在前端启用，却无法进入待执行队列。

补齐遗漏任务，保留已有任务的相对顺序。彼世逢魔放在
真蛇、商店任务之后，爬塔等六项放在原顺序表尾部。
默认规则同时增加兜底：顺序表之外的到期任务记录警告，按下次运行时间追加到队尾。
兜底仅处理已进入待执行列表的任务，不启用禁用任务，也不提前执行等待任务。
FIFO、优先级规则及正在运行任务的置顶行为沿用现有实现。

新增带调度器的配置模型时，须同步补齐顺序表，并运行：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_task_schedule dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
```

`test_task_schedule` 覆盖受影响任务单独及同时启用后的选择和总览输出、全部调度模型
在顺序表中恰好出现一次、遗漏任务兜底排序、等待与禁用行为及三种规则的运行任务置顶。
测试读取模板并在内存中修改配置，不写入用户配置，不操作设备。
离线检查通过仅说明调度接入和任务构造正常，不代表活动入口、OCR 或游戏流程实测通过。

应用修复需重启后端，再刷新前端总览；无需重新创建配置。

本次验证：任务调度、配置模板、任务启动、服务启动、狩猎战调度与悬赏调度共
43 项 unittest 通过；`check_i18n.py` 的 721 个键覆盖检查及 `pip check` 通过。
未执行 OCR、设备或游戏流程实测。

## 禁用任务后的总览刷新

2026-10-17 继续修复任务切回“未启用”后总览残留的问题。
此前 WebSocket 查询调用执行器的 `get_next()`，全部任务禁用后抛出
`RequestHumanTakeover`，导致前端无法收到空总览；持有旧任务的配置对象也可能
通过 `self.task` 返回过期的当前任务。

总览查询改为直接调用 `get_schedule_data()`，该方法重新计算已启用任务的队列，
按当前队首生成总览的当前任务项，不读取旧 `self.task`，也不修改执行器持有的任务。
所有任务禁用时返回 `running: {}`、`pending: []`、`waiting: []`。
调度字段通过 HTTP 保存成功后立即广播新总览；旧 GUI 回调也共用该生成逻辑。
这只更新调度展示，不中断已经进入游戏流程的任务。

时间间隔的 HTTP 保存共用 `TimeDelta` 解析器，完整解析 `DD HH:MM:SS` 的天数（含10、30、99及更大值），不截取单个数字。格式错误、负天数和越界时分秒返回400，且不保存或推送；配置序列化沿用原有时间间隔格式。回归见 `dev_tools.test_schedule_api`。

新增禁用最后一个到期任务、禁用队首但保留其他到期和等待任务、推迟旧任务等测试；
`dev_tools.test_schedule_api` 验证 HTTP 开关推送、WebSocket 空队列连接与刷新，
以及保存失败时不推送。API 测试替换全局管理器并模拟连接，不启动服务或写入配置。

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_hunt_schedule dev_tools.test_wanted_quests_schedule -q
```

此次共 49 项 unittest 通过，721 个翻译键覆盖检查、`pip check` 及改动代码的
`git diff --check` 通过。未在实际前端、设备或游戏中实测。


## 启动时同优先级任务随机排序

`script.optimization.startup_task_shuffle_enable` 默认关闭。启动配置、完成启动预热后，对当时已启用且已到期的任务建立快照；只有存在至少两个同优先级的非 Restart 任务才抽签。每次启动只抽签一次，有20%概率调整各符合条件的同优先级组，其余80%保持同优先级组内的基础顺序；无论是否命中随机，启用开关时均按数字优先级排序。成功抽签但随机洗牌恰好未改变顺序时，轮转一位，保证该组确实变化。

启用开关时，在 Filter、FIFO、Priority 三种规则的基础排序之后，先稳定地按数字优先级分组（数字越小越先），再仅在同优先级组内应用启动随机顺序。同组未随机时保留所选规则的基础顺序。关闭开关保持原调度规则；Filter/FIFO 在关闭状态仍不按数字优先级排序。Restart 不参与随机，正在运行的任务仍按原逻辑置顶。所有任务保留，无新任务过滤。

排序键包括任务名、优先级、该次 next_run；启动后新到期的任务、优先级或执行时间被改变的任务、后续轮次不参与启动随机，但在开关启用期间仍遵守数字优先级；同优先级内按基础规则排序。任务结束后继续沿用启动快照中剩余任务的相对顺序。配置重载和执行器重新创建 Config 对象复用本次启动快照。运行中开启须下次启动生效，关闭则立即停用排序覆盖。

只有脚本进程在启动时抽签；服务端查询与刷新总览不会抽签。启动快照通过现有进程队列同步到服务端，校验来源为当前子进程 PID，HTTP/WebSocket 总览重建配置时应用同一份排序；启动和成功停止会清除旧快照。快照只保存在内存，不写入用户配置或持久化运行数据。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_config_lifecycle -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
```

测试使用固定随机结果验证20%边界、关闭与无候选不抽签、刷新稳定、优先级隔离、Restart 排除、运行任务置顶、改期退出随机组和配置重建后复用。不启动游戏；不将随机执行顺序解释为已验证的防检测效果。

2026-10-17 修正：先前“保留各优先级原位置”的实现会保留Filter/FIFO中的优先级倒置。现改为开关启用时始终先按数字优先级分组，再同组随机，覆盖命中与未命中随机、服务端尚未收到快照、新高优先级任务到期及三种调度规则。
