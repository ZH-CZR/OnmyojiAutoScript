# 狭间暗域开放日调度

开放范围为每周五00:00至下周一00:00前，即周五、周六、周日全天，按本地时间计算。

`AbyssShadowsScheduler` 保留原配置字段，无需迁移用户数据。`server_update` 表示开放日执行时间（默认09:00）；成功后按成功间隔天数和强制日期间隔的较大值（至少一天）选择目标日期，再把周一至周四的日期顺延到周五。默认依次为周五→周六→周日→下周五。关闭服务时间覆盖时使用原成功间隔，仍须遵守开放日。

失败按失败间隔重试，不再被通用固定执行时间覆盖；跨入周一至周四时顺延至周五的配置时间。手动显式目标在开放日内保持原值，关闭日目标顺延到周五的配置时间，不被成功间隔截短。

保留随机延迟 `float_time`，自动安排成功或失败的下一次执行时追加一次0至配置秒数的延迟。抽签范围同时限制在目标日23:59:59以内，避免随机到非开放日。结果保存到原 `next_run`，重载和总览不重新抽签；显式目标不追加随机延迟。

调度及总览把旧的非开放日到期计划投影到周五，不在读取时写回配置。任务入口再次检查开放日；已开始的战斗沿用现有流程，不在午夜强行中断。未新增闲时执行适配器。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_abyss_shadows_schedule dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

覆盖开放日全天边界、周末成功安排、失败跨周、显式目标、随机延迟、旧字段重载、总览及入口保护。离线测试不连接设备，不代表游戏流程实测通过。
