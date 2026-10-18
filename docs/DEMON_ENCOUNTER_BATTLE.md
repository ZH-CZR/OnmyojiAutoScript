# 逢魔之时战斗等待

## 60 秒超时误判

2026-10-18 的错误日志显示：Boss 战斗最后一次点击准备后约 60 秒抛出
`GameStuckError`，保存的截图仍是正常战斗画面。

任务此前调用 `Device.stuck_record_add(500)`，但该接口只把参数转成字符串保存到
`detect_record`，并不设置超时秒数。`'500'` 不属于长等待标记，仍受普通约 60 秒
无操作检测限制。集结阶段的 `BATTLE_STATUS_S` 在进入战斗前已清除，准备点击也会
清空等待标记。

## 修复行为

- 战斗等待使用设备现有的 `BATTLE_STATUS_S`，沿用约 300 秒的长等待检测。
- 准备、胜利、奖励和失败点击会清空标记；下一次截图前恢复标记，不循环重置计时器。
- 战斗正常返回或异常退出均移除本阶段的长等待标记，避免影响后续页面。
- 集结等待异常时也清理长等待标记。设备卡死检测始终保留，真正长时间无操作仍报错。
- 不改变战斗结果识别、任务调度和 Restart 开关行为。

## 离线验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_demon_encounter_battle dev_tools.test_wanted_invitation dev_tools.test_task_startup dev_tools.test_server_startup -q
```

回放使用真实 `Device` 卡死检测和计时器，模拟准备后的 61 秒战斗、结算点击后的
等待、超过 300 秒无操作、失败点击、正常结束、异常清理及后续页面恢复短超时。
测试不连接设备；离线通过不代表已完成游戏内流程实测。
