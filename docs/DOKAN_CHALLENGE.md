# 道馆失效后的重复挑战修复

2026-10-17，修复道馆仍在右侧列表、但已被其他玩家攻破时，选馆阶段反复点击挑战和确认的问题。

参考聊天：`codex://threads/01a13fc7-017b-7c52-b9ac-a84df5acd53e`。审查了该聊天对应的 `D:/yys/yys-install-yu` 中的选馆、挑战方法、OCR 定义和模拟测试，仅移植相关修复，不同步该项目其他代码或配置。

## 行为

- 显示挑战按钮仅代表详情已打开；只有识别到 `I_RYOU_DOKAN_CHECK` 才确认进入道馆并发送开启通知。
- 在挑战点击后通过 `O_DOKAN_CHALLENGE_MESSAGE` 读取服务器提示，出现“击破”或“其他道馆”时立即放弃当前候选。
- 每个候选最多等待 15 秒，挑战、确认各最多点击 3 次，并保留原有点击保护。未识别到失效提示也会超时退出。这些限制不影响馆内挑战、准备和再战投票。
- 失败寮名在当前一次 `find_dokan()` 搜索中跳过，包括滑动列表、刷新和最低系数兜底；下次调用重新开始记录。
- 换候选前收起旧详情，最多尝试 3 次；挑战按钮仍存在时跳过当前候选，避免误用旧详情。选新候选最多等待 5 秒。
- 每个候选重新判断福利寮及退出标记，保留搜索开始时的退出配置。失败后仍能识别后续福利寮。
- 最低系数兜底从小到大尝试尚未失败的候选，空列表安全返回。普通搜索全部失败时结束本轮任务，不记录开启时间、不切换御魂。
- 不在选馆页面时使用场景检测的实际入馆结果，避免把未知页面直接当作成功。

## 验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_dokan_challenge dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe -m pip check
```

道馆测试使用模拟页面、虚拟时间及点击记录重现服务器拒绝、提示漏识别、延迟进入、候选切换、最低系数兜底、详情收起失败、确认卡住及无按钮超时；另检查真实任务导入及 OCR 资源定义一致性。测试不会连接设备或操作游戏。

OCR 提示区域为参考修复中的 `(280,215,730,50)`，尚未在本项目运行环境进行 OCR、设备或游戏流程实测；离线测试不代表游戏内验证通过。

## 五六七开启狭间

道馆配置新增 `weekend_abyss_enable`，界面名称“五六七开启狭间”，默认关闭，旧配置缺少该字段时也关闭。启用后按本地日期在周五、周六、周日跳过道馆流程，安排下周一原调度器执行时间；周四道馆完成后的安排也直接跳到周一。该条件在QQ群消息查询前检查，避免被跳过的任务消耗消息检查次数。周一至周四正常运行。

此选项独立于狭间暗域调度器开关，取代此前依据 `abyss_shadows.scheduler.enable` 隐式跳过周末的行为；不会自动启用或执行狭间暗域。关闭选项时，即使狭间任务启用也保持道馆原流程。周一目标通过 `success=None, server=False` 保存，避免成功间隔截短或通用固定执行时间将其覆盖成次日。

新增验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_dokan_weekend dev_tools.test_dokan_challenge dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
```

覆盖默认值、界面布尔字段、配置重载、所有星期、周四完成、与狭间任务开关独立及QQ群查询前跳过；未进行游戏实测。
