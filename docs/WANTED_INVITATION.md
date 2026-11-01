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

2026-10-28 适配新版公共协作邀请弹窗，素材来源为 YYS `run_now`
提交 [`aed463eaad881fdda5f0b91dae145c0242943545`](https://gitee.com/pattering-rain/yys/commit/aed463eaad881fdda5f0b91dae145c0242943545)。
更新接受、拒绝、勾玉、体力、猫粮、狗粮六张 PNG，以及七项邀请规则的位置；
忽略按钮沿用原关闭图标，仅更新位置。来源及文件哈希记录在
`upstream/wanted_invitation_port.json`，不改全项目参考版本。

`gg/image.json` 保留上游搜索区域，前置区域按 PNG 真实尺寸定义，避免加载时再隐式修正大小；
通过 `ImageExtractor` 同步生成 `GlobalGameAssets` 对应图像区块。
匹配成功后仍使用真实命中位置随机点击，所有邀请策略、接受后的调度及等待标记恢复代码保持原样。
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
