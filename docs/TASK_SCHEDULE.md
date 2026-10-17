# 默认任务调度与总览

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

新增禁用最后一个到期任务、禁用队首但保留其他到期和等待任务、推迟旧任务等测试；
`dev_tools.test_schedule_api` 验证 HTTP 开关推送、WebSocket 空队列连接与刷新，
以及保存失败时不推送。API 测试替换全局管理器并模拟连接，不启动服务或写入配置。

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_hunt_schedule dev_tools.test_wanted_quests_schedule -q
```

此次共 49 项 unittest 通过，721 个翻译键覆盖检查、`pip check` 及改动代码的
`git diff --check` 通过。未在实际前端、设备或游戏中实测。
