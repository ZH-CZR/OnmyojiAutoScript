# 悬赏邀请与设备卡死检测

公共任务 `tasks/base_task_parent.py` 的 `_burst()` 在截图后处理悬赏邀请。
设备核心 `module/device/device.py` 通过 `detect_record` 中的等待标记、
`stuck_timer` 和 `stuck_timer_long` 判断卡死，没有 `stuck_timeout` 属性。
旧邀请代码读取该属性，导致地域鬼王等任务遇到邀请时抛出 `AttributeError`。

邀请处理在点击前复制设备等待标记，通过 `finally` 合并回当前记录。
这样可以恢复点击时被清除的 `BATTLE_STATUS_S` 等长等待标记，保留处理期间新增的记录，
同时在输入异常时恢复等待状态并继续向外抛出异常。设备计时器仍按原逻辑检查和重置，
不延长超时阈值、不关闭卡死检测。接受、拒绝、忽略及奖励筛选策略保持原行为，
接受后仍通过显式目标安排悬赏任务。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_wanted_invitation dev_tools.test_wanted_quests_schedule dev_tools.test_task_startup dev_tools.test_server_startup -q
```

邀请测试使用未初始化连接的真实 `Device` 对象及模拟截图、输入，覆盖所有邀请策略、
无邀请、输入异常、长战斗等待恢复和卡死检测边界，不连接设备或操作游戏。
离线验证不能代替游戏内实测。
