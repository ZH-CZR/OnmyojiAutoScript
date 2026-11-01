# 悬赏邀请与设备卡死检测

公共任务 `tasks/base_task_parent.py` 的 `_burst()` 在截图后处理悬赏邀请。
设备核心 `module/device/device.py` 通过 `detect_record` 中的等待标记、
`stuck_timer` 和 `stuck_timer_long` 判断卡死，没有 `stuck_timeout` 属性。
旧邀请代码读取该属性，导致地域鬼王等任务遇到邀请时抛出 `AttributeError`。

邀请处理在点击前复制设备等待标记，通过 `finally` 合并回当前记录。
这样可以恢复点击时被清除的 `BATTLE_STATUS_S` 等长等待标记，保留处理期间新增的记录，
同时在输入异常时恢复等待状态并继续向外抛出异常。设备计时器仍按原逻辑检查和重置，
不延长超时阈值、不关闭卡死检测。接受、拒绝、忽略及奖励筛选策略保持原行为，
接受后记录一次协作悬赏请求，由主调度器在当前任务结束后执行。

2026-10-28 适配新版公共协作邀请弹窗，素材来源为 YYS `run_now`
提交 [`aed463eaad881fdda5f0b91dae145c0242943545`](https://gitee.com/pattering-rain/yys/commit/aed463eaad881fdda5f0b91dae145c0242943545)。
更新接受、拒绝、勾玉、体力、猫粮、狗粮六张 PNG，以及七项邀请规则的位置；
忽略按钮沿用原关闭图标，仅更新位置。来源及文件哈希记录在
`upstream/wanted_invitation_port.json`，不改全项目参考版本。

`gg/image.json` 保留上游搜索区域，前置区域按 PNG 真实尺寸定义，避免加载时再隐式修正大小；
通过 `ImageExtractor` 同步生成 `GlobalGameAssets` 对应图像区块。
匹配成功后仍使用真实命中位置随机点击，所有邀请策略及等待标记恢复代码保持原样。
本次不覆盖悬赏主面板、详情、黑名单或庭院“封”字素材。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_wanted_invitation dev_tools.test_wanted_quests_schedule dev_tools.test_task_startup dev_tools.test_server_startup -q
```

邀请测试使用未初始化连接的真实 `Device` 对象及模拟截图、输入，覆盖所有邀请策略、
无邀请、输入异常、长战斗等待恢复和卡死检测边界，不连接设备或操作游戏。
新增真实模板拼接画面的离线回放：接受/拒绝/忽略、仅勾玉、四类奖励筛选、
搜索区域内位置偏移及点击位置、旧位置和区域外奖励不触发、JSON/生成定义/实际图片尺寸一致性。
回放使用真实图像匹配及公共 `_burst()` 控制流程，只模拟设备截图和输入，未启动图像/OCR RPC。
2026-11-01 使用用户提供的 1280×720 完整勾玉协作邀请截图补充离线验证。
旧提交的接受/拒绝规则在原搜索区域的最高分仅为 0.313/0.365，低于 0.8 阈值，
无法触发公共处理，弹窗因而遮挡页面识别。当前新版接受/拒绝规则得分为
1.000/1.000，关闭为 0.958，勾玉为 0.962。
原图通过公共 `screenshot()` 入口回放全部五种策略，确认实际命中位置点击、
按钮消失后返回、仅接受策略安排悬赏，以及恢复长等待标记；设备截图和输入均为模拟。
新增可选原图回归，原图只在本地读取，不提交截图及用户昵称：

```powershell
$env:WANTED_INVITATION_REPLAY_IMAGE = '本地勾玉协作邀请截图的绝对路径.png'
.venv\Scripts\python.exe -m unittest dev_tools.test_wanted_invitation -q
Remove-Item Env:WANTED_INVITATION_REPLAY_IMAGE
```

未指定变量时跳过原图用例，其余模板及流程测试照常运行。
重启后端及任务以加载新素材；仅热重载配置不会更新进程已加载的图像规则。
邀请仍按“好友邀请”配置处理，默认“忽略”只关闭弹窗，不自动接受或安排悬赏。
离线验证不能代替游戏内实测。

## 接受好友协作后执行一次悬赏

接受按钮实际点击且弹窗按钮消失后，向独立的
`config/activity/cooperation.sqlite3` 写入一次 `wanted_quests` 请求。
该数据库与手动立即执行请求分开，不进入寮突破安全让位流程，也不触发任务内的优先级中断。
当前任务完整结束（包括手动任务处理后的原任务恢复）后，主调度器执行一次悬赏；
没有当前任务时在下一轮调度执行。已排队的手动立即执行请求仍保持最高优先级，协作请求排在普通定时任务前。

请求按配置隔离；等待期间多次接受合并为一次悬赏执行，开始执行后再接受会排下一次。
配置刷新、热重载和进程重建不丢失未消费请求；准备游戏环境失败或要求重新调度时不消费，
环境准备成功后、进入任务执行前按本次选中的令牌消费，旧令牌不能删除新邀请。
一次请求对应一次任务调用，执行失败沿用现有异常处理，不自动重复消费同一次邀请。

该请求不修改任务开关、执行模式或原计划时间；悬赏未启用、手动或闲时模式下也可以执行这一次。
正常定时模式完成任务后仍按悬赏原有规则安排下一轮；手动模式保留原有不自动改期行为。
请求不享受手动立即执行的作息和每日上限豁免，仍遵守运行限制。
拒绝、忽略、奖励筛选未接受、弹窗未经点击自行消失或处理超时，都不产生请求。

## 空闲等待时处理邀请

2026-11-01 18:23 的原图和运行日志确认：邀请停留在庭院，而执行器持续等待下次任务，
没有调用任务截图入口。17:59 的同类邀请曾在式神委派执行中成功接受，
委派结束后也已运行悬赏；这次漏处理来自空闲循环缺少检测，不是按钮再次失效。

`Script.wait_until()` 在普通空闲等待中每 5 秒调用运行时的邀请检测，
复用公共 `_burst()` 的按钮识别、策略、固定 10 秒处理超时和协作请求队列。
接受成功后结束等待并重新调度；拒绝或忽略后继续原等待。
处理器复用实例但每次重绑最新配置与共享设备，不重复回庭院或运行任务准备流程。
未初始化设备、模拟器关闭、游戏不在运行或停服等待时不截图、不点击、不启动游戏。
已有协作请求也不能中断停服等待造成无休眠的重选循环。

空闲画面本来没有进展要求，故每轮独立邀请检查前重新开始设备卡死计时；
进入邀请处理后不再重置，仍逐张截图执行设备检查，保留长等待标记恢复。
截图或邀请处理异常向外报告，检查结束或异常都释放等待中的截图资源。
新增 `dev_tools.test_wanted_idle_invitation` 覆盖真实模板匹配、空闲唤醒、
拒绝/忽略、5 秒间隔、长时间空闲、异常清理、不启动关闭的游戏及停服请求保留。
用户原始截图通过前述可选环境变量本地回放，不入库；未做游戏内流程实测。

回归（不连接设备、不启动游戏）：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_wanted_idle_invitation dev_tools.test_wanted_cooperation_schedule dev_tools.test_wanted_invitation dev_tools.test_wanted_runtime_routes dev_tools.test_wanted_quests_schedule dev_tools.test_runtime_idle dev_tools.test_game_startup dev_tools.test_restart_compatibility dev_tools.test_manual_schedule dev_tools.test_immediate_preemption dev_tools.test_activity_guard dev_tools.test_idle_schedule dev_tools.test_task_schedule dev_tools.test_schedule_api dev_tools.test_config_consistency dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
```
