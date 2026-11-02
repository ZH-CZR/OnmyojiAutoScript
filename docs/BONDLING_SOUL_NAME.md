# 契灵抓捕按契灵名选择御魂队伍

“执行任务前切换御魂”的“队伍名”下方提供“队伍名与契灵名保持一致”，默认关闭。开启且启用“通过OCR来切换御魂预设”时，以“使用契石时选择召唤类型”的名称作为队伍名，例如选择“月魔兔”便查找“月魔兔”队伍；所有召唤类型均直接使用其名称。

开启后无需填写队伍名，原手填值仍保留，关闭后继续使用。御魂分组名仍需填写。数字编号切换及“探查切换御魂”保持原行为，该开关不会写入公共御魂配置模型或探查配置。

离线验证（不启动游戏）：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_bondling_soul_name dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
```

回归覆盖默认关闭、配置字段位置与范围、全部契灵名称、关闭后手填队伍恢复及探查队伍不受影响。真实 OCR 匹配与游戏内切换仍需设备实测。
