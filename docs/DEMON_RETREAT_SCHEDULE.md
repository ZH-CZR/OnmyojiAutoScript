# 首领退治调度

首领退治仅在每周六本地时间 11:00（含）至 23:00（不含）开放。调度器统一显示“周六执行时间”，默认 11:00；新设置必须在该时段内。23:00 视为活动已经关闭。

成功完成战斗及领奖，或识别到已完成并领取奖励后，安排下周六配置时间。失败保留“失败间隔”，默认10分钟；重试时间超过开放窗口时安排下一周。隐藏不参与本任务的成功间隔、服务时间与强制日期。保留随机延迟 `float_time`：成功及失败自动安排时，在基础时间上叠加一次 0 至配置秒数的随机延迟，抽签上限同时限制为距离 22:59:59 的剩余秒数。结果随下次执行时间保存，总览刷新和重载不重新抽签。显式目标不追加随机延迟。手动显式目标位于开放窗口内时原样保留，不被通用服务时间或成功间隔覆盖；位于窗口外时移到下一开放周六的配置时间。

旧 `demon_retreat_time.custom_run_time` 优先迁移到 `scheduler.saturday_time`；缺少旧自定义时间时使用旧 `scheduler.server_update`。早于11点调整到11点，23点及之后回落11点。已有显式 `saturday_time` 始终优先；旧字段仍可加载但隐藏且不参与调度，读取时不写回用户文件。

调度选择与总览共同将过期计划映射到下一开放窗口；周六窗口内的过期任务可补执行，未来窗口内的显式计划保持原时间。任务入口再次检查当前时间，防止手动运行或排队延误在关闭时段进入游戏。已开始的战斗沿用原流程，不在23点强制中断。未接入闲时执行适配器。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_demon_retreat_schedule dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

测试覆盖随机延迟单次应用、关闭边界、总览不重复抽签、开放边界、每周完成、失败跨窗口、显式目标、旧字段迁移、界面字段及非开放时段入口保护。不连接设备，不代表游戏内流程实测通过。
