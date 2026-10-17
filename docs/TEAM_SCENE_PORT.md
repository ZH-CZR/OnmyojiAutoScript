# 组队场景移植

2026-10-17，从用户指定的 `D:\yys\yys-install-yu` 实际文件移植至
`D:\yys\OnmyojiAutoScript-oYe`。参考目录为 `master`，提交
`0b17ce281ab255edb6f8256561335761ac68099f`，origin 为
`https://gitee.com/oYe486/yys.git`，相关源码和素材没有未提交改动。
目标目录为 `self` 分支，移植前已有已跟踪修改、删除和未跟踪文件；
相对配置的跟踪分支没有未推送提交。保留现场，没有切换分支、提交或推送。

## 使用与实现

在全局游戏设置的皮肤配置中选择“组队场景”：默认或宛然春意，
选项须与游戏内当前场景一致。新配置默认使用默认场景，旧配置缺少字段时自动补默认，
旧值 `costume_team_default` 转换为 `costume_team_1`。

导入 `tasks/Component/CostumeTeam/` 的公开 Python、JSON 及 14 张图片，
替换通用邀请组件的三人/五人空位和挑战按钮。永生之海专用素材保持原有逻辑。
所有继承 `GeneralInvite` 的任务在构造时自动接入，实例独立创建模板，
避免不同配置或其他任务的同名按钮共享状态。切换场景同时清空人数判断状态。
保留本项目已有的其他皮肤缓存失效及匹配方法适配。

同步参考实现的入场动画等待（3 至 5 秒）、两次至少间隔 0.3 秒的占位确认，
以及点击前再次检查人数。空位重新出现、房间标志丢失或挑战按钮消失均重置确认。
这些检查降低动画导致的误开风险，实际游戏中的识别效果仍需设备验证。

来源文件原始 SHA-256 单独记录在 `upstream/team_scene_port.json`，
未覆盖既有 `upstream/manifest.json` 的参考版本和哈希。
该移植不引入私有 `.pyd`、授权或账号管理功能。
当前缺少 `dev_tools/upstream_policy.py`、`dev_tools/upstream_sync.py` 和
`docs/REFACTOR.md`，无法把适配加入这些工具；后续恢复同步工具时应保留此适配。

## 离线验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_team_scene dev_tools.test_team_room_occupancy dev_tools.test_costume_assets dev_tools.test_config_template dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

组队测试覆盖配置展示和保存、旧值兼容、图片加载、实例隔离、动画等待、
人数确认与点击前复核。未启动游戏任务，不代表 OCR、设备或游戏流程实测通过。

本次上述 43 项 unittest 全部通过；翻译检查覆盖全部 721 个菜单、配置组、
字段与帮助键，`pip check` 未发现依赖冲突。御魂任务构造测试另行确认所选场景
实际接入 `ScriptTask` 且保持共享设备。
