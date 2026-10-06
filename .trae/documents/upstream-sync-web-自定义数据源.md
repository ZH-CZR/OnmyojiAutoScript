# 上游同步工具：Web 端自定义数据源（任意仓库 + 分支）

## Context（为什么做）

现有 `dev_tools/upstream_sync*.py` 把对比源写死为 `upstream = https://github.com/runhey/OnmyojiAutoScript.git` 的 `dev` 分支
（`UPSTREAM_REMOTE/URL/BRANCH`，见 [upstream_sync.py](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync.py#L31-L34)），
本地基线固定 `mine`。用户希望**在 web 界面直接输入任意 GitHub 仓库地址并选择分支**，与当前项目做比对 / 合并
（例如换成另一个 fork 的提交）。这样就不必手动改常量、加 remote。

用户已确认的三点：
1. 「已合并/删除」那一类，指的是**被我排除/跳过的提交** → 需要持久化记录机制，**本阶段不做**（见文末「下一阶段」）。
2. 数据源输入放在**顶部工具栏**新增一行。
3. **先只做自定义源**，稳定后再做独立视图。

预期结果：打开网页 → 顶部填「仓库地址 + 分支」→ 连接并比对 → 后续 fetch/list/advise/apply 全部作用于该源；
不填时行为与现在**完全一致**（向后兼容）。

---

## 范围边界

**做**：自定义数据源的 CLI 参数、分支列表获取、web 后端透传、前端「数据源」行、文档。
**不做**：被排除/跳过提交的独立视图（下一阶段）；不改变默认源行为；不动 `mine`/`czr` 分支纪律。

---

## 设计

### 1. 后端 CLI（`dev_tools/upstream_sync.py`）

**新增两个顶层参数**（与 `--base`/`--since` 同级，须放在子命令**之前**）：

```
--remote-url    任意仓库地址；留空 = 默认 runhey（向后兼容）
--remote-branch 目标分支；留空 = dev
```

**新增常量**：`SOURCE_REMOTE = "syncsrc"`（自定义源专用的 remote 名，避免与默认 `upstream` 混淆）。

**新增辅助 `resolve_source(args) -> (remote, branch, ref)`**（集中替换现有 5 处硬编码）：

- 无 `--remote-url` → `(UPSTREAM_REMOTE, UPSTREAM_BRANCH, "upstream/dev")`；
- 有 → 确保 remote 存在且 URL 正确（`git remote get-url` 比对，不一致则 `git remote set-url`，不存在则 `add`），
  返回 `(SOURCE_REMOTE, args.remote_branch or UPSTREAM_BRANCH, f"{SOURCE_REMOTE}/{branch}")`。

**改造点**（把 `ref = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"` 换成 `resolve_source(args)`）：
`cmd_fetch`、`cmd_list`、`cmd_advise`、`cmd_apply`。`collect_commits(base, ref, ...)`、`precheck_commit`、`local_churn`
入参已是 `base`/`ref`，**无需改**（`local_churn` 用 `merge-base(base, ref)`，自定义源只要与本地有共同祖先即可正常工作）。

`cmd_fetch` 的 remote 建立逻辑泛化：`ensure_upstream()` → `ensure_source(url)`（沿用现有代理回退 `detect_local_proxy()` /
`git_with_proxy()`，见 L374-L404）。

**新增子命令 `branches`**：`branches --url <仓库地址> --json`
- 执行 `git ls-remote --heads <url>`（取不到时用 `git_with_proxy` 回退一次，复用现有代理探测），解析 `refs/heads/<name>`。
- 为防私有库卡住，这些联网调用注入 `GIT_TERMINAL_PROMPT=0`（失败即返错，不挂起）。
- 用 `emit({"url":..., "branches":[...]})` 输出（符合 `@@SYNC@@` 协议）。

### 2. Web 后端（`dev_tools/upstream_sync_web.py`）

- `get_commits` / `get_advise` / `apply_hashes` 增加 `remote_url` / `remote_branch` 入参，拼进 `run_sync([...])` 参数；
  无值时**不传**这两个 flag（保持默认路径）。
- **缓存键修正**：`_ADVISE_CACHE` 的键由 `since` 改为 `(since, remote_url, remote_branch)`，避免换源后命中旧结果。
- `do_GET /api/commits`：从 query 读 `remote_url` / `remote_branch`。
- `do_POST /api/advise`、`/api/apply`：从 body 读同名字段并透传。
- **新增路由** `POST /api/branches`，body `{"url":"..."}` → 调 `branches --url ... --json`，用 `parse_sync_json()` 解析。

### 3. Web 前端（`PAGE` 常量）

工具栏**新增一行**（放在第一行「时间范围」上方或同排）：

```
数据源  [仓库地址 input#repoUrl，占位“留空 = runhey 默认”]  [分支 select#repoBranch] 
        [加载分支 button#btnLoadBranches]  [连接并比对 button#btnConnect]  <span id="srcStatus">
```

- 默认 `repoUrl` 空、`repoBranch` 为 `dev`；空地址即默认源，界面文案与现有一致。
- JS 新增 `sourceParams()` 统一产出 `{since, remote_url, remote_branch}`，供 `loadCommits()` / `runAdvise()` / `doApply()` 复用。
- `#btnLoadBranches` → `POST /api/branches {url}`，填充 `#repoBranch`（保留并预选当前值）。
- `#btnConnect` → 走 `loadCommits(true)`（**连接即 fetch**，自定义源必须先 fetch 才有 `syncsrc/<branch>` 引用）。
- `#rangeSub` 已由后端 `ref` 驱动，会自然显示自定义源；无需额外改。
- 「重新生成清单」「拉取上游最新」两个按钮同样带上 `sourceParams()`。

### 4. 文档（`dev_tools/upstream_sync_doc.md`）

- §0 速查：子命令表加 `branches --url <url> --json`；常见任务/界面调用表加 `POST /api/branches`；补充
  `--remote-url/--remote-branch` 说明（须在子命令前）。
- §5.3 子命令表、§6 HTTP API 表各加一行。
- §8 关键 DOM id 加 `repoUrl` `repoBranch` `btnLoadBranches` `btnConnect` `srcStatus`，函数加 `sourceParams()` / `loadBranches()`。
- 新增 §13.12 记录本次增强（背景/做法/改动文件/验证/边界）。

---

## 涉及文件

- [dev_tools/upstream_sync.py](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync.py)：新增 `--remote-url/--remote-branch`、`SOURCE_REMOTE`、`resolve_source()`、`ensure_source()`、`cmd_branches()`；改造 fetch/list/advise/apply 的 ref 解析。
- [dev_tools/upstream_sync_web.py](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py)：透传参数、`/api/branches`、缓存键、前端数据源行。
- [dev_tools/upstream_sync_doc.md](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_doc.md)：文档同步。

---

## 验证

1. `python -m py_compile dev_tools/upstream_sync.py dev_tools/upstream_sync_web.py` → exit 0。
2. **向后兼容**：不传新参数跑 `list --json`，应仍是 117 条（`--since "2 months ago"`），`ref` 仍为 `upstream/dev`。
3. **等价性**：显式传 `--remote-url https://github.com/runhey/OnmyojiAutoScript.git --remote-branch dev`，结果应与第 2 步一致。
4. **分支列表**：`python dev_tools/upstream_sync.py branches --url https://github.com/runhey/OnmyojiAutoScript.git --json`
   能返回分支数组（直连失败应自动走本机代理回退；无网时给出明确错误而非挂起）。
5. **Web 回归**（改 `PAGE` 后**必须重启服务**）：启动 `start_upstream_sync.bat` 或 `python dev_tools/upstream_sync_web.py`；
   - 空地址 → 行为与改前一致；
   - 填其它 fork 地址 → 加载分支 → 选分支 → 连接并比对 → 列表/Markdown/advise/apply 均作用于该源；
   - `POST /api/branches` 直连验证返回 JSON。
6. 提交按 §14 规范落到开发分支 `czr`（不直接提交 `mine`）。

---

## 下一阶段（本次不做，仅记录）

「**被我排除/跳过的提交**」独立视图，需先有记录机制：
- 前端「忽略 / 恢复」动作 → 持久化到 `dev_tools/upstream_ignored.json`（键为源 + 分支，值为 hash 列表）；
- `cmd_apply` 的空提交（`skip_empty_pick`）/ 已同步跳过项 → 记入同一文件；
- 独立视图展示这些提交与原因（手动排除 / 应用时空提交跳过），支持一键恢复。

---

## 约束提醒

- 通信协议：结果走 `emit()` 单行 `@@SYNC@@{json}`；`list`/`advise --json` 例外（走 `--out`）。
- 改 `PAGE` 后必须重启 web 服务（无热重载）。
- 联网调用注入 `GIT_TERMINAL_PROMPT=0`；代理仅通过环境变量注入，**不改 git config**。
- `dev_tools/baidu_translate.json` 含密钥，勿 `git add`。