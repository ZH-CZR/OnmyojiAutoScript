---
name: "upstream-sync"
description: "List, judge and selectively cherry-pick upstream commits into the local mine branch with conflict pre-check and colored diff preview. Invoke when the user wants to sync/adopt upstream commits, review what upstream changed, resolve or abort sync conflicts, or modify dev_tools/upstream_sync*.py."
---

# 上游提交选择性同步（upstream-sync）

把上游 `runhey/OnmyojiAutoScript` 的 `dev` 分支相对本地 `mine` 未同步的提交列出，交给用户勾选后
逐条 cherry-pick；支持冲突预判、逐文件取舍、彩色改动预览与中文"取舍建议"。

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
3. `show --commit <hash>` —— 需要时查看该提交的摘要与 patch
4. `apply --manifest <清单文件> --pause` —— 建 `sync/*` 分支逐条 cherry-pick
5. 冲突处理（**必须在暂停态**）：
   - `conflicts` 查看未解决文件
   - `conflict-detail --file <路径>` 看三阶段差异 + 中文原因
   - `resolve --choices-file <json>` 按 `{"path":"ours"|"theirs"}` 处理并继续
   - 放弃则 `abort`（回 `mine` 并删 `sync/*` 分支）
6. 验证：`python -m py_compile ...` + `list --json` + 冲突全链路 + 界面回归（见文档 §11）

## 必守约束

- 后端→界面：用 `emit()` 打印 `@@SYNC@@{json}` **单行**；**唯一例外 `list --json`**（写 `--out` 文件）
- 改前端 `PAGE` 后**必须重启** web 服务（无热重载）
- `apply` 要求**工作区干净**；冲突处理只能在暂停态
- `dev_tools/baidu_translate.json` 含密钥，**勿 `git add`**
- 提交信息遵循文档 §14（`Why` / `What` / `Verify` 三段式）