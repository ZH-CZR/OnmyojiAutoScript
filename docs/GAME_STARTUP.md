# 配置启动时打开游戏

## 冷启动竖屏截图等待

2026-10-19 后续日志显示，MuMu 已完成安卓启动并打开游戏，但第一帧仍是 `720x1280` 竖屏，设备方向为 `0`，无法旋转为横屏。旧截图检查仍放行该帧，登录模板按横屏 ROI 裁剪后得到空区域，触发 OpenCV `matchTemplate` 断言失败。

截图入口现在逐帧检查尺寸，竖屏无法按设备方向转换时继续获取新截图，最多等待 30 秒；超时抛出 `GameStuckError`，等待期间保持截图间隔和设备卡死检查。即使之前已确认过横屏，后续截图也重新核对实际尺寸。仅通过尺寸检查的画面进入识别、图像 RPC 注册和截图队列；需要旋转的帧先完成旋转再注册，保证本地图片与 RPC 帧一致。其他不支持的分辨率仍保留配置错误提示，不拉伸或猜测旋转方向。

离线回归在下方启动测试组中增加 `dev_tools.test_screenshot_startup`，覆盖连续竖屏后恢复横屏、已有尺寸缓存后再次竖屏、旋转后 RPC 图片一致、等待超时、卡死检测与不支持分辨率。未启动真实模拟器或操作游戏，实际冷启动仍需重新启动配置验证；前端无需重新构建。

## 模拟器冷启动就绪等待

2026-10-19 日志显示，MuMu 冷启动时 ADB 已上线且 `echo pong` 可执行，但查询包列表仍触发 `AdbTimeout`，随后进入普通任务级重连，重连后才打开游戏。ADB 上线并不表示安卓系统及包管理服务已就绪。

Windows 启动监视现在先直接向目标序列号查询 `getprop sys.boot_completed`，返回 `1` 后再查询 `pm list packages` 确认游戏包可见。两项探测均使用原始 ADB shell，单次超时最多 3 秒，并受剩余启动时间限制；启动期间的连接重置、包管理查询超时或空结果返回等待，由监视循环继续轮询，不调用任务级 ADB 重试和重连。设备状态必须为 `device`，`unauthorized` 等状态不能进入后续就绪检查。

保留原有 120 秒整体启动上限、窗口就绪确认及最终失败处理，不用固定长时间休眠替代就绪探测，不修改普通游戏任务的连接恢复策略。前端无需重新构建，下次启动配置进程加载修复。

离线回归：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_screenshot_startup dev_tools.test_emulator_cold_start dev_tools.test_game_startup dev_tools.test_login_device dev_tools.test_restart_compatibility dev_tools.test_runtime_startup dev_tools.test_task_startup dev_tools.test_server_startup -q
```

新增回归模拟 ADB 先上线、系统稍后完成启动、包查询暂时超时后恢复的完整监视循环，并验证目标序列号、剩余超时预算、未授权设备与整体超时失败。未关闭或启动真实模拟器，未进行游戏流程实测。

前端点击启动配置后，模拟器可能被设备初始化拉起，但仍停留在安卓桌面。原运行时将这一状态一律交给 `Restart`，配置禁用重启任务时会记录 `Restart task is disabled` 并退出。

现在每个配置进程在首次需要游戏运行时，会使用内部 `GameStartup` 入口调用设备的 `app_start()`，复用 `LoginHandler.app_handle_login()`，成功后重新选择待执行任务。模拟器已开启但游戏未打开的情况也适用；游戏已在前台时直接执行任务。

首次打开游戏不要求启用重启任务，不强制停止应用，不改动 Restart 的调度时间，不执行其日志备份、大神签到、集体任务等每日附加操作。登录仍使用当前配置的角色与收取设置，沿用运行时长统计及现有异常处理。

运行时控制器记录首次启动机会，配置重载不会重置。已发现游戏在运行、已执行重启或首次启动失败后，后续游戏缺失仍进入原来的 Restart 恢复，遵守重启任务开关及异常恢复规则。停服窗口按现有机制延后待执行任务，等待结束后保留首次启动机会。

无需重新构建前端。更新后的代码在下次启动配置进程时生效；已经运行的配置需停止后重新启动。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_game_startup dev_tools.test_restart_compatibility dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_activity_guard -q
```

测试模拟冷启动后的设备、登录与异常路径，不连接模拟器、不操作游戏。通过离线测试不代表实际渠道服登录流程已验证。

## 登录设备接口修复

2026-10-18 实际启动已进入登录，但旧代码调用 `stuck_record_add(timeout=600)`。公开设备接口只接收识别标记，不接受超时参数。现在登录阶段临时使用 600 秒无操作计时器，保留截图卡死检测和点击后的正常重置；成功、TaskEnd 或异常退出时恢复并重置原计时器，不影响后续任务。

同时补齐登录引用但本项目未提供的“已阅读并同意”和“接受协议”公开图像模板。模板及 ROI 来自本地 YYS 参考检出，文件哈希和参考提交记录于 `upstream/login_device_port.json`，仅用于现有登录分支，不引入账号管理模块。

补充回归 `dev_tools.test_login_device` 使用真实 `Device` 的卡死检测方法运行登录循环，验证成功、超时、渠道服退出和截图异常的恢复行为，并检查登录素材引用与新增 PNG 解码；不操作真实设备。
