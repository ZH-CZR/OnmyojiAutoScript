# 悬赏路线入口与好友邀请确认

2026-10-30 补充运行时保护。

悬赏详情四行按当前截图逐行识别；没有式神挑战行时直接选择可用秘闻，不要求存在挑战券路线。
每条路线进入最多等待 15 秒，点击不重置总超时。到期仍确认在详情页时，排除本次失败行并尝试其他可用路线；
已离开详情但无法确认战斗入口时抛出 `GameStuckError`，避免使用旧详情坐标点击其他页面。
全部可用入口失败时保留追踪并报错，不能视为悬赏完成。探索路线仍未接入执行。
秘闻准备、对话及战后对话有固定超时，保留原有设备卡死检测，秘闻多次战斗也遵守本任务 20 场上限。

公共好友邀请入口可由接受或拒绝按钮识别。仍按 `friend_invitation` 配置选择接受、拒绝、忽略或奖励筛选，
不修改用户设置（默认仍为忽略）。处理最多等待 10 秒，点击不延长；选定按钮暂时漏识别但其他邀请按钮仍存在时，
继续等待而非直接报告成功。必须实际点击且邀请按钮消失后才报告处理结果，接受成功后才安排悬赏。
等待标记仍在 `finally` 中恢复，保留设备卡死计时。

用户提供的樱花妖详情完整截图使用本机现有 PP-OCRv6 ONNX 模型离线回放：
进度为 `0/6`、左侧挑战券 `3864`，四行依次为“秘闻烽火”“秘闻山巅”“秘闻道成”“探索第八”，
关卡数量分别为 6、3、4、3；四个前往按钮匹配分数为 0.962–1.000。
在此静态截图上，原有选路已经能够选择“烽火寄情·贰”一次，因此不能将该截图本身视为旧选路失败的复现。
本次改动覆盖入口未进入后的换路与异常反馈；运行时卡住的具体页面仍需日志或连续截图进一步确认。
好友邀请尚缺实际弹窗截图，本次未据此调整素材或坐标，也未验证游戏内邀请识别。
完整截图不入库，不启动游戏或图像/OCR RPC。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_wanted_runtime_routes dev_tools.test_wanted_detail dev_tools.test_wanted_ui dev_tools.test_wanted_cooperation dev_tools.test_wanted_invitation dev_tools.test_wanted_quests_schedule dev_tools.test_config_template dev_tools.test_config_consistency dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

额外回归公共截图入口的活动限制和结算点击：`dev_tools.test_activity_guard`、`dev_tools.test_click_timing`。
