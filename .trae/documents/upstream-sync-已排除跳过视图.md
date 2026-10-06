# upstream-sync：已排除/跳过 独立视图（下一阶段）

## Context（为什么做这个）

上一阶段完成了「自定义数据源」（任意仓库/分支比对，提交 `c1bf1502`）。用户最初的诉求里还有一半没做：

> 「比对合并后或者删除的，可以放到另外的界面」

经确认，其含义是 **「被我排除/跳过的提交」** 需要放到一个**独立视图**里，而不是混在待同步列表中。当前工具存在两个信息黑洞：

1. **已并入本地**：`already_applied()`（patch-id 等价）在 [collect_commits L349-L351](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync.py#L349-L351) 被**静默过滤**，用户看不到「上游这条其实已经进 mine 了」。
2. **被我跳过的**：用户在主列表里看到某条但决定不采用，这个决定**无处留存**；下次 `list` 它又原样出现。

目标：新增同页 Tab「已排除/跳过」，展示上述两类，并让「跳过」成为**显式、可撤销**的动作。

## 已确认的产品决策

| 决策点 | 结论 |
|---|---|
| 收录范围 | **我主动跳过的** + **已并入本地的**（后者只读） |
| 标记方式 | 每条一个「跳过」按钮 **+** 多选后「跳过所选」（复用现有 `selected` 勾选） |
| 视图形态 | **同页 Tab 切换**（待同步 / 已排除·跳过），复用现有渲染与 CSS |
| 恢复 | 被跳过的可「恢复」（un-ignore），回到待同步列表 |

## 范围边界（本阶段不做）

- 不做自动记录：**点「执行同步」时未勾选的不自动记为跳过**（避免污染；用户确认用显式按钮/多选）。
- 不做已并入项的「恢复」（它们本就在 mine 里，恢复无意义）。
- 不做跨数据源的全局忽略：忽略记录带 `source` 字段，但视图按当前数据源展示。
- 不改 `advise` 的信号语义与 `--deps` 回溯算法本身。

## 设计

### 1. 持久化：`dev_tools/upstream_ignored.json`

```json
{ "version": 1,
  "items": [ { "hash": "<40位>", "subject": "...", "date": "2026-09-19",
               "module": "GeneralBattle", "type": "fix",
               "source": "runhey/OnmyojiAutoScript · upstream/dev",
               "ignored_at": "2026-10-07 12:00:00", "reason": "manual" } ] }
```

- 存**元数据**而非只存 hash：上游 rebase/移除后该 hash 可能已不存在，仍需显示它是什么（视图里标「哈希已不存在」）。
- 缺失/损坏文件按空处理（容错）。
- **不入库**：`.gitignore` 追加 `dev_tools/upstream_ignored.json`。注意必须写在 **L32 `!dev_tools/*` 取反规则之后**，否则会被重新放行（已核实该取反规则存在）。

### 2. CLI（`dev_tools/upstream_sync.py`）

新增常量 `DEFAULT_IGNORED = os.path.join("dev_tools", "upstream_ignored.json")`，新增函数：

- `load_ignored()` / `save_ignored(items)`：读写上面的 JSON，容错。
- `ignored_hashes()`：返回**全 hash 集合**（供过滤复用）。
- `_match_ignored(items, prefix)`：前缀匹配（**≥8 位**；命中多条视为歧义并报错，不静默处理）。

新增子命令（遵循 `emit()` 约定，走 `@@SYNC@@`）：

| 子命令 | 参数 | 作用 | emit |
|---|---|---|---|
| `ignore` | `--hashes a,b,c` | 从 `collect_commits(base, ref, since, exclude_applied=False)` 反查元数据；按全 hash 去重后合并进文件 | `{"status":"ok","added":n,"total":m}` |
| `unignore` | `--hashes a,b,c` | 前缀匹配移除；歧义时报错 | `{"status":"ok","removed":n,"total":m,"ambiguous":[...]}` |
| `ignored` | `--json` | 列出已跳过项 | `{"items":[...]}` |

改造点（**关键，评审发现**）：

- `cmd_list`：改用 `collect_commits(exclude_applied=False)`，然后按 `already_applied(base, ref)` **在本窗口内**拆成 `pending` / `applied`（`git cherry` 覆盖全历史，必须与本次 `--since` 窗口求交，否则「已并入」组会膨胀）。`--json` payload 增加 `"applied":[...]` 与 `"ignored":[...]`（字段与 `commits` 同构，便于 `_decorate_commits` 复用），并从 `commits` 中剔除 `ignored`。Markdown 清单同样剔除，并在表头注明「已跳过 N 条 / 已并入 M 条」。
- `cmd_apply`：候选池 `all_commits`（[L711](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync.py#L711)）**也要剔除 ignored**，否则 `--deps` 回溯会把用户明确跳过的提交静默 cherry-pick 进来（web 的 `apply_hashes` 不传 `--deps`，但 CLI 会）。勾选到 ignored 的 hash 归入 `missing` 并单独打印提示「已被跳过，如需同步请先 unignore」。
- `cmd_advise`：同样剔除 ignored，保持与 `cmd_list` 一致。
- argparse：新增三个子命令（[参照 L1067-L1122](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync.py#L1067-L1122) 的组织方式）；`main()` 补三个分支。

### 3. Web 后端（`dev_tools/upstream_sync_web.py`）

- `get_commits()`：透传 `applied` / `ignored`，并对二者也调用 `_decorate_commits()`（中文字段，`_decorate_commits` 已要求 `subject`/`module` 键，忽略项已含）。
- 新增 `do_ignore(hashes, remote_url, remote_branch)`、`do_unignore(hashes)`：`run_sync([*source_args(...), "ignore", "--hashes", ",".join(...)])` → `parse_sync_json`。
- **缓存失效**：`do_ignore` / `do_unignore` 成功后置 `_ADVISE_CACHE["key"] = None`——否则 AI 顾问会继续返回已跳过的那条（`get_advise` 有进程内缓存）。
- `do_POST` 路由集合与 `elif` 链各加 `"/api/ignore"`、`"/api/unignore"`。`/api/commits` 响应自然带上 `applied`/`ignored`，不新增 GET 路由。

### 4. Web 前端（`PAGE`）

- **Tab 栏**（放在 `#banner` 之上）：
  `<div class="tabs"><button id="tabPend">待同步 <b id="tabPendN">0</b></button><button id="tabIgn">已排除·跳过 <b id="tabIgnN">0</b></button></div>`
- 状态：`let applied = [], ignored = [], view = "pend";` + `ignoredSet`（全 hash 的 Set）。`loadCommits()` 从响应写入三者。
- **单一 `render()` 按 `view` 分派**（评审建议，避免复制分组/折叠逻辑）：`view==="pend"` 走现有逻辑；`view==="ign"` 走新增 `renderIgnored()`——**扁平分组**（按模块）、**不做折叠/不做 diff 面板**、不渲染 checkbox，改为：
  - 「我跳过的」组：每行带 `恢复` 按钮（`POST /api/unignore`）；`orphan`（hash 已不在当前上游窗口）标「哈希已不存在」。
  - 「已并入本地」组：只读，默认**折叠成一行汇总**（`已并入本地 N 条 ▸`），点开展开——`git cherry` 命中数可能很多，避免刷屏。
- **跳过入口**：主列表每行加 `跳过` 按钮（`POST /api/ignore`），工具栏第 4 行加 `#btnSkipSel`「跳过所选」（复用 `selected`）。跳过成功后：`commits` 剔除、`ignored` 追加、`selected` 清理、`updateTabCounts()`、`render()`（**不整页重载**，避免清掉 `selected`/`pc`）。
- **视图隔离**：把待同步专属控件（筛选行 + 全选/预检/顾问/已选计数 + footer 的 `#btnApply`）包进 `#pendTools`，`view==="ign"` 时 `display:none`，避免「跳过所选」误带非待同步项（评审发现 `selected` 跨视图残留）。
- 复用既有 CSS 类：`.cwrap` / `.item` / `.mhead` / `.files` / `.badge` / `.ghost` / `.primary` / `.csub`。

### 5. 文档与技能

- `dev_tools/upstream_sync_doc.md`：§0 子命令表与常见任务表补 `ignore`/`unignore`/`ignored`；§5.3 子命令表补三行、说明 `list --json` 新增 `applied`/`ignored`；§6 HTTP API 表补 `/api/ignore`、`/api/unignore` 与 `/api/commits` 响应的 `applied`/`ignored`；§8 补 DOM id（`tabPend`/`tabIgn`/`tabPendN`/`tabIgnN`/`btnSkipSel`/`pendTools`）与函数（`renderIgnored()`/`doIgnore()`/`doUnignore()`/`setView()`/`updateTabCounts()`）；新增 **§13.13** 记录本次增强（背景/做法/改动文件/验证/边界）。
- `.gitignore`：在 L32 之后追加 `dev_tools/upstream_ignored.json`。
- `.trae/skills/upstream-sync/SKILL.md`：在「标准流程」补一句跳过/恢复的用法。

## 涉及文件

| 文件 | 改动 |
|---|---|
| `dev_tools/upstream_sync.py` | 持久化 + 3 个子命令；`cmd_list` 拆分 applied/ignored；`cmd_apply`/`cmd_advise` 剔除 ignored |
| `dev_tools/upstream_sync_web.py` | `get_commits` 透传；`do_ignore`/`do_unignore` + 路由 + 缓存失效；前端 Tab/跳过/恢复 |
| `dev_tools/upstream_sync_doc.md` | §0/§5.3/§6/§8 + 新增 §13.13 |
| `.gitignore` | 忽略 `dev_tools/upstream_ignored.json`（写在 `!dev_tools/*` 之后） |
| `.trae/skills/upstream-sync/SKILL.md` | 一句话补充 |

## 验证

1. `python -m py_compile dev_tools/upstream_sync.py dev_tools/upstream_sync_web.py`。
2. **CLI 闭环**：`list --json` 断言含 `applied` / `ignored` 且 `ref` 仍正确；`ignore --hashes <h>` → 再 `list --json` 该 h 出现在 `ignored`、不在 `commits`；重复 `ignore` 不产生重复项；`unignore --hashes <h>` 后回到 `commits`；`unignore` 传 7 位前缀应报错（歧义/过短）。
3. **apply 一致性**：把某个 ignored 的 hash 写进临时清单后 `apply`，应打印「已被跳过」且**不** cherry-pick。
4. **gitignore**：`git check-ignore -v dev_tools/upstream_ignored.json` 命中新规则；`git status` 不出现该文件。
5. **Web 回归**（改 `PAGE` 后**必须重启服务**）：Tab 切换；主列表「跳过」与「跳过所选」；已排除页「恢复」；「已并入本地」默认折叠可展开；`POST /api/ignore`、`/api/unignore` 返回 200 且刷新后状态正确；`GET /api/commits` 含 `applied`/`ignored`。
6. 按文档 §14 规范提交到开发分支 **`czr`**（不直接提交 `mine`）。

## 风险与已规避项

- `git cherry` 覆盖全历史 → 已并入组**必须**与 `--since` 窗口求交（§2 `cmd_list`）。
- `ignored` 与 `applied` 可能重叠（跳过之后那条又被 merge 进 mine）→ 渲染时**按 hash 去重、applied 优先**，同一提交不在两个组重复出现。
- 上游 rebase 后 hash 失效 → 保留元数据显示为「哈希已不存在」，不静默残留。
- 现有 `list --json` 消费方（web `get_commits`）用 `data.get("commits")`，新增字段**向后兼容**。