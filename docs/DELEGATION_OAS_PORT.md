# 式神委派参考 OAS 调整

2026-10-17，按用户要求将当前工作树 `tasks/Delegation/` 的任务流程改为
OAS 一键选择方案。参考仓库为 https://github.com/xylolit-mu/OnmyojiAutoScript.git，
使用 `upstream/manifest.json` 已指定且本地 Git 对象库可读取的提交
`00c083e83a6ad8a258b05536dab8454a77e20325`，未查询或更新远端版本。
目标为 `D:\yys\OnmyojiAutoScript-oYe` 的 `master` 分支，已有其他未提交修改、
删除和未跟踪文件，本次保留这些现场，没有切换分支、提交或推送。

## 任务行为

- 保留原有六类委派开关和领取奖励后再派遣的顺序。
- 使用 `C_D_ALL` 点击一键选择，按 OAS 的首位出战标记 `I_D_SELECT_FIRST`
  确认选择结果，再执行出发流程；选择及出发期间沿用 OAS 的一键选择重试间隔。
- 任务未找到时跳过；发现已在委派中的返回按钮时退回任务列表，不重新派遣。
- 同步 OAS 的奖励对话推进：点击“完成”后，OCR 检测底部对话区域，
  在对话界面点击该区域，直到奖励确认按钮出现；5 秒未出现则抛出
  `GameStuckError`，交给现有异常恢复流程。
- 保留本项目 `ui_goto_page()` 导航及 `ScriptTask(config, device)` 设备复用接口，
  不引入 OAS 独立调试入口和无用导入。

## 素材与来源

同步一键选择坐标、首位出战图片、跳过图片、识别区域及完成对话 OCR 定义。
移除已无调用的五个逐个选择坐标、五条旧出战标记及五张旧图片。
未导入 OAS 未被流程调用的“再考虑下”图片及定义。
资源索引由本项目 `dev_tools/assets_extract.py` 仅针对 `tasks/Delegation/` 重新生成。

OAS 原始来源文件 SHA-256 单独记入 `upstream/delegation_oas_port.json`，
包括与本地已有文件内容相同但本次核对使用的素材。
该记录保存适配前的参考哈希；原 `upstream/manifest.json` 的 YYS 来源快照不覆盖。
后续从 YYS 同步时应保留本次经用户指定的 OAS 委派方案。

## 离线验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_delegation dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

23 项 unittest 通过。委派场景覆盖选择动画延迟、首位出战确认后才出发、
任务缺失及委派中跳过、奖励对话推进、空文本或非对话界面不误点及超时异常，
另验证实际任务构造复用设备和全部委派图片可加载。
未连接设备、未调用真实 OCR、未运行游戏流程，游戏中的按钮坐标及识别效果仍需实测。

翻译检查覆盖全部 719 个菜单、配置组、字段及帮助键；`pip check` 未发现依赖冲突。
