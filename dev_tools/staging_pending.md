# 预演批次台账（staging pending log）

> 用途：所有改动先在 `staging/YYYYMMDD-主题` 分支上攒成一个完整批次，自动化测试 + 实机验证通过、经确认后，才合并回 `czr`。
> 维护方式：建批次 → 在 §2 追加一行；状态变化就地更新；合并或废弃后移到 §3。
>
> ⚠ **开工自检**：每次新任务开始前先读本文件 §2。若存在 `进行中` / `待测试` / `待合并` 的批次，先提示用户「有未完成批次」，再决定继续、合并还是废弃。

---

## §1 约定

| 环节 | 规则 |
|---|---|
| 分支命名 | `staging/YYYYMMDD-主题`，从 `czr` 最新提交拉出 |
| 批次命名 | 主题由 AI 按改动内容自动生成英文短横线形式（如 `staging/20261120-metademon-fatigue`）；改动跨多模块或无法归类时用 `misc`，并在台账「改动范围」里写清具体内容 |
| 提交范围 | 批次内所有改动只提交到 staging 分支，`czr` 保持干净 |
| 自动化测试 | `$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q`（无 `toolkit\python.exe` 时用系统 Python）+ 导入冒烟 `python -c "from tasks.GameUi.registry import PageRegistry; PageRegistry.load_all_pages(); print(len(PageRegistry.all()))"`（当前基线 105 个页面），防 `AttributeError` 类启动失败 |
| 实机验证 | 用 adb 在线设备启动相关任务模块跑通，抓截图与日志判定；产生截图放 `.screenshots/`，不入库 |
| 通过标准 | 自动化全绿 + 实机通过 + 用户确认，三者缺一不可 |
| 合并方式 | `git merge --no-ff staging/...` 合入 `czr`，随后按标准推送命令推送并更新本台账 |
| 废弃方式 | 不合并不删代码，分支保留并在 §3 标记 `已废弃`，注明原因 |

状态取值：`进行中` → `待测试` → `待合并` → `已合并` / `已废弃`

---

## §2 进行中的批次

| 批次 | 分支 | 建立日期 | 改动范围 | 自动化测试 | 实机验证 | 状态 |
|---|---|---|---|---|---|---|
| p0-1-mt-boss | `staging/20261120-mt-boss` | 2026-11-20 | `tasks/MartialTournament/config.py`（新增 `boss_limit`）、`tasks/MartialTournament/script_task.py`（`current_limit` / `current_climb_page`）、`assets/i18n/zh-CN.json`（sequence 帮助文本）、`tests/test_martial_tournament_boss_stage.py`（新增） | 新增 5 passed；全量 520 passed / 10 failed（均为既有失败） | 未完成：武道大会未开放（活动总览当前为「祸至无日」），开放后补测 | 待测试 |

---

## §3 已合并 / 已废弃

| 批次 | 分支 | 处理日期 | 结果 |
|---|---|---|---|
| p0-2-realm-raid-roi | `staging/20261120-realm-raid-roi` | 2026-11-20 | 已合并，merge commit `33cc7e06`。突破券 ROI 收窄至 `928,16,69,25`（未照搬上游 `923,16,74,25`，本机该区域仍读成 18/30） |
| p0-3-wq-mystery | `staging/20261120-wq-mystery` | 2026-11-20 | 已合并，merge commit `78d95b2a`。13 条上游修复去重后只补 3 条缺失语义（详情页前往判断、神秘悬赏跳过、仅剩不支持任务退出）；其余等价实现已在 czr，`d296406e` 等资产重构与本地 `I_TRACE_TRUE` 流程冲突故未引入 |
| 合并后校验 | `czr` | 2026-11-20 | 全量 `523 passed / 10 failed`（均为既有失败），页面注册 105 |
| p3-keepalive-cleanup | `staging/20261121-p3` | 2026-11-21 | 已合并，merge commit `997dab48`。`server.py` keep-alive 75s（8s 空闲同连接复用成功，默认 5s 对照断连）；删除 `tasks/OrochiMoans` 占位（旧配置兼容、模板零差集）。合并后全量 `524 passed / 10 failed`（均为既有失败），页面注册 105 |
| workflow-autosync | `staging/20261122-workflow-autosync` | 2026-11-22 | 已合并，merge commit `c9b0322e`。新增 `dev_tools/session_start.py`（开工简报 + 自动 merge czr，冲突自动 abort，脏工作区只报告）与 `.trae/rules/project_rules.md`（IDE 自动加载的开工卡）；README §10 与 SKILL 补开工条目。无运行代码改动，不涉及 pytest 与实机 |
