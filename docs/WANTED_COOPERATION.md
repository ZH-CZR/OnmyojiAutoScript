# 悬赏协作自动邀请

“悬赏封印 → 邀请好友协作类型”同时控制两种邀请方式：填写“协作任务邀请特定人员”时邀请该昵称；留空时沿用默认邀请列表前五位好友的方式。

例如选择“金币+食协+体协”（配置值 `GoldAndFoodAndSushi`），只自动邀请金币、猫粮/狗粮及体力协作，跳过勾玉协作。选择“不邀请”（`NoInvite`）则不自动邀请任何协作。保留原有配置字段、全部 16 种组合及默认值“全部”（`Any`），不改写已有用户选择。

默认邀请和指定昵称邀请共用筛选；每次邀请及指定昵称重试前，使用新截图核对该位置当前奖励类型。未选类型只跳过当前条目，不阻断后面的协作；缺少前方邀请按钮也继续检查后面的按钮。奖励无法识别时跳过自动邀请。食协包含金币奖励，识别顺序继续优先检查勾玉、猫粮/狗粮及体力，最后检查金币。

此设置仅影响主动邀请好友，不改变接收好友协作邀请的策略，也不改变悬赏早晚调度。

离线验证（不连接设备或操作游戏）：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_wanted_cooperation dev_tools.test_wanted_invitation dev_tools.test_wanted_quests_schedule dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

回归覆盖全部筛选组合、两种邀请方式、猫/狗粮附带金币、跳过首条勾协、邀请按钮空缺、邀请后列表变化、重试前类型变化、未知奖励跳过及配置与界面选项兼容。截图识别准确性与游戏内流程仍需实机验证。
