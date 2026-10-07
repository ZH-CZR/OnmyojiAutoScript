---
name: "upstream-sync"
description: "List, judge and selectively cherry-pick upstream commits into the local czr branch with conflict pre-check and colored diff preview. Invoke when the user wants to sync/adopt upstream commits, asks which upstream commits are safe to merge, review what upstream changed, resolve or abort sync conflicts, or modify dev_tools/upstream_sync*.py."
---

# 上游提交选择性同步（upstream-sync）

把上游 `runhey/OnmyojiAutoScript` 的 `dev` 分支相对本地 `czr` 未同步的提交列出，交给用户勾选后
逐条 cherry-pick；支持冲突预判、逐文件取舍、彩色改动预览与中文"取舍建议"。
> 比对基线与同步目标均为 `czr`（开发/暂存分支）；测试一段时间无误后再自行把 `czr` 合并到 `mine`。

## 何时使用

- 用户想"同步上游 / 采用上游提交""看看上游改了什么""这条提交要不要用"
- 需要预判 cherry-pick 冲突、解决冲突、或放弃本次同步
- 需要修改或扩展 `dev_tools/upstream_sync.py` / `upstream_sync_web.py`

## 入口

- **完整交接文档**：`dev_tools/upstream_sync_doc.md` —— 先读 §0 速查、§11 自检、§14 提交规范
- 网页：`python dev_tools/upstream_sync_web.py`（监听 `127.0.0.1`，8765 起自动选端口）
- CLI：`python dev_tools/upstream_sync.py --since "2 months ago" <子命令>`（通用参数须在子命令**前**）

## 标准流程

1. `fetch` —— 拉取上游 `dev`（需能连 github；否则只能用本地缓存的 `upstream/dev`）
2. `list --json` —— 看清单；每条带 `level` 取舍建议（`adopt` / `caution` / `review`）与 `adds/dels/changed`
   - **AI 顾问模式请改用 `advise --json`**：在此基础上加「冲突预判 + 本地定制度」，见下节
   - 不想同步的提交：`ignore --hashes <hash,…>`（界面：每行「跳过」/「跳过所选」）移出待同步，随时 `unignore` 恢复；网页「已排除·跳过」页同时展示**已跳过**与**已并入本地**（见文档 §13.13）
3. `show --commit <hash>` —— 需要时查看该提交的摘要与 patch
4. `apply --manifest <清单文件> --pause` —— 建 `sync/*` 分支逐条 cherry-pick
5. 冲突处理（**必须在暂停态**）：
   - `conflicts` 查看未解决文件
   - `conflict-detail --file <路径>` 看三阶段差异 + 中文原因
   - `resolve --choices-file <json>` 按 `{"path":"ours"|"theirs"}` 处理并继续
   - 放弃则 `abort`（回 `czr` 并删 `sync/*` 分支）
6. 验证：`python -m py_compile ...` + `list --json` + 冲突全链路 + 界面回归（见文档 §11）

## AI 顾问模式（全流程托管）

**何时用**：用户不了解项目、不知道哪些提交能合，或直接说"帮我看看上游有什么能同步 / 给个合并建议"。
此时**由 AI 判断、用大白话解释，用户只看结论并批量拍板**，不要把技术细节甩给用户。

**流程**

1. 进入仓库根目录，拉取上游：`python dev_tools/upstream_sync.py --since "2 months ago" fetch`
   （直连不通会自动走本机代理回退，见文档 §13.9）
2. 取深度信号（JSON）：`python dev_tools/upstream_sync.py --since "2 months ago" advise --json --out <临时文件>`
   读 JSON：`summary` 是总览，`commits[]` 每条含 `level`/`judge`/`reasons`/`conflict`/`local_churn`。
3. 对 `caution`/`review` 的重点提交，按需 `show --commit <hash>` 读懂**实际改了什么**（抓重点，不必全看）。
4. 产出**建议表**（模板见下），按"建议采用 / 需实测 / 建议评估"分组，理由写人话。
5. 等用户**批量确认**（回复要哪些 hash，或"按推荐来"）。**未经确认不要执行。**
6. 生成临时清单文件（每行格式：``- [x] `<hash8>` ``），执行：
   `python dev_tools/upstream_sync.py apply --manifest <临时文件> --pause`
   （`apply` 要求工作区干净；用户有未提交改动时先提醒提交或暂存）
7. 冲突处理（**只能在暂停态**，循环到 done）：
   `conflicts` → `conflict-detail --file <路径>` → `resolve --choices-file <json>`（或 `abort`）
8. 收尾验证：`python -m py_compile` 涉及文件；提醒用户测试无误后再合并回 `czr`。

**信号怎么读**

| 信号 | 含义 | 判断用法 |
|---|---|---|
| `conflict.status` | `merge-tree` 模拟 cherry-pick 的结果 | `conflict` = 执行时会冲突、需人工取舍 → 至少"需实测" |
| `conflict.files` | 预计冲突的文件 | 文件多 / 触及核心 → 更谨慎 |
| `local_churn.lines` / `level` | 本地在这些文件上的改动量 | `high` = 本地已大幅定制，合并易覆盖本地改动 → 建议单独评估 |
| `level` / `judge` | 已综合上述信号的结论（`adopt`/`caution`/`review`） | 直接作为建议基线 |
| `reasons` | 中文理由列表 | 转写成人话给用户 |

**建议表模板**

| 提交 | 摘要 | 规模 | 冲突 | 本地定制 | 建议 | 理由 |
|---|---|---|---|---|---|---|
| `abc1234` | 修复御魂战斗等待 | 小 | 无 | 低 | ✅ 采用 | 独立模块小改，不动公共文件 |
| `def5678` | 重构配置加载 | 大 | 3 文件 | 高 | 🛑 单独评估 | 动 framework，且你本地已大改 config |

**约束**

- 判断依据以 `advise` 信号 + `show` 的真实 diff 为准，**不要凭提交标题臆断**。
- 执行前必须拿到用户确认；`apply` 前确保工作区干净。
- 冲突处理只能在暂停态；用户不想继续就 `abort`（会回 `czr` 并删 `sync/*` 分支）。

## 必守约束

- 后端→界面：用 `emit()` 打印 `@@SYNC@@{json}` **单行**；**唯一例外 `list --json`**（写 `--out` 文件）
- 改前端 `PAGE` 后**必须重启** web 服务（无热重载）
- `apply` 要求**工作区干净**；冲突处理只能在暂停态
- `dev_tools/baidu_translate.json` 含密钥，**勿 `git add`**
- `dev_tools/upstream_ignored.json`（已跳过提交的本地记录）**不入库**；`list` / `advise` / `apply` 均已自动剔除被跳过的提交，如需同步先 `unignore`
- 提交信息遵循文档 §14（中文头行 + `Why` / `What` / `Verify` 三段式，`What` 逐文件列出）；**按 agent 可理解的标准写**，便于后续上传与同步
- **运行时与依赖产物一律不入库**：`.gitignore` 已覆盖 `toolkit/`、`oas.exe`、`console.bat`、`oas-backend.bat`、`config/deploy.yaml`、`log/`、`__pycache__/`；提交前用 `git status --short` 复核，**禁止 `git add -f`** 强行加入
- **分支纪律**：改动先落在开发分支 `czr`（跟踪 `origin/czr`），测试通过后再合并回 `mine`；不要直接在 `mine` 上提交，也不要提交到临时 `sync/*` 分支（同步结束会删除）。本工具默认的**比对基线与同步目标也是 `czr`**（见 `--base` / `DEFAULT_BASE`）。