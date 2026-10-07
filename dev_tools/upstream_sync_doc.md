# 上游提交选择性同步工具 —— AI 交接文档

> 面向对象：后续接手/调用此功能的 AI agent / 开发者。
> 适用版本：`czr` 分支最新提交（本文件与该提交同批入库）。文中行号是**近似值**，代码改动后请以符号名（函数名/常量名）为准检索。
> 只描述"是什么、在哪、怎么改、怎么验"，不重复实现细节。

---

## 0. Agent 速查（先看这里）

**定位**：把上游 `upstream/dev` 相对本地 `czr` 未同步的提交列出，供人工/agent 勾选后 cherry-pick。**不联网同步代码**，联网仅用于标题翻译（可关）。
> 同步目标是 `czr`（开发/暂存分支）；测试一段时间无误后再自行把 `czr` 合并到 `mine`。

**启动**

```bash
python dev_tools/upstream_sync_web.py      # 网页界面（127.0.0.1:8765 起自动选端口）
python dev_tools/upstream_sync.py --help   # 命令行
```

**CLI 通用参数**（必须放在子命令**之前**）：`--base czr --since "2 months ago"`
**自定义数据源**（同位置，可选）：`--remote-url <仓库地址> --remote-branch <分支>`；留空即默认 `runhey/dev`（向后兼容）。

| 子命令 | 用途 | 机器可读返回 |
|---|---|---|
| `fetch` | 拉取上游 dev | 无（纯文本） |
| `branches --url U` | 列出任意仓库的远程分支（供界面选数据源分支） | `@@SYNC@@{"url","branches","default"}` |
| `list --json [--out F]` | 生成清单 | 整段 JSON（**走 `--out` 文件，非 emit**，见 §4 例外） |
| `show --commit H` | 单提交摘要 + patch | `@@SYNC@@{"status","commit","stat","patch","truncated"}` |
| `advise --json [--out F]` | 逐条**冲突预判 + 本地定制度**并修正取舍建议（供 AI 顾问） | 整段 JSON（同 `list`，走 `--out` 或 stdout） |
| `apply --manifest F --pause` | 建 `sync/*` 分支逐条 cherry-pick | `@@SYNC@@{"status":"conflict"\|"done",...}` |
| `conflicts` | 查看未解决冲突 | `@@SYNC@@{"status","branch","commit","files"}` |
| `resolve --choices-file F` | 按选择处理冲突并继续 | `@@SYNC@@{"status",...}` |
| `abort` | 中止并清理 | `@@SYNC@@{"status":"aborted","branch"}` |
| `conflict-detail --file P` | 单文件三阶段差异 + 中文分析 | `@@SYNC@@{"status","file","hunks","analysis","ours_text","theirs_text"}` |
| `ignore --hashes H1,H2` | 把提交标记为「跳过」（持久化到 `dev_tools/upstream_ignored.json`，之后不再出现在待同步列表） | `@@SYNC@@{"status":"ok","added","total"}` |
| `unignore --hashes H1,H2` | 恢复被跳过的提交（hash 前缀 **≥8 位**，前缀歧义则报错退出） | `@@SYNC@@{"status":"ok","removed","total"}` |
| `ignored [--json]` | 列出已跳过的提交 | `@@SYNC@@{"items":[...]}` |

**硬约束（调用前必读）**

1. 后端→界面通信：结果用 `emit()` 打印 `@@SYNC@@{json}` **单行**；**唯一例外 `list --json`**（写 `--out` 文件，web 读临时文件）。
2. 改前端 `PAGE` 后**必须重启** `upstream_sync_web.py`（模块级常量，无热重载）。
3. 冲突处理**只能在暂停态**进行（`apply --pause` 之后），`resolve` 前不要再 `apply`。
4. `apply` 要求**工作区干净**（无 tracked 未提交改动），否则直接拒绝。
5. 翻译走免费额度，**别反复全量重跑**。
6. `dev_tools/baidu_translate.json` 含密钥，**勿 `git add`**。
7. 上游数据靠 `fetch`；连不上 github 时只能用本地缓存的 `upstream/dev`。`fetch` 已内置**代理回退**：直连失败会自动探测本机代理（`OAS_GIT_PROXY` 优先，其次 `127.0.0.1:7897` / `10809`）重试一次，**不改 git config**。

**常见任务 → 做法**

| 任务 | 做法 |
|---|---|
| 拉最新上游 | `upstream_sync.py fetch`（直连不通会自动走本机代理回退） |
| 换数据源（任意仓库/分支） | 顶层加 `--remote-url/--remote-branch`，或界面「数据源」行；见 §13.12 |
| 列出某仓库的分支 | `branches --url <地址>` 或 `POST /api/branches {"url":"..."}` |
| 概览可同步提交 + 取舍建议 | `list --json` 或 `GET /api/commits` |
| 跳过不想同步的提交（先搁置） | `ignore --hashes <hash,…>`，或界面每行「跳过」/「跳过所选」；恢复 `unignore --hashes <hash>`；列表里不再出现 |
| 查看被跳过 / 已并入的提交 | `ignored --json`，或界面「已排除·跳过」页（见 §13.13） |
| AI 判断哪些提交能合（全流程托管） | `advise --json` → AI 读信号 + `show` 出建议表 → 用户确认 → `apply --pause`（见 §13.10） |
| 看某提交改了什么 | `show --commit H` 或 `POST /api/show` |
| 预判冲突 | `POST /api/precheck {"hashes":[...]}` |
| 执行同步 / 处理冲突 | `apply --pause` → `conflicts`/`conflict-detail`/`resolve`（或 `abort`） |
| 界面调用 | `POST /api/apply`、`/api/conflicts`、`/api/conflict-detail`、`/api/resolve`、`/api/abort`、`/api/translate`、`/api/show`、`/api/advise`、`/api/branches`、`/api/ignore`、`/api/unignore` |

> 自检清单见 §11；扩展索引见 §9；本次增强记录见 §13；提交规范见 §14。

---

## 1. 一句话概括

把上游 `runhey/OnmyojiAutoScript` 的 `dev` 分支上、本地 `czr` 分支还没有的提交列出来，
让用户**按模块勾选**，新建 `sync/*` 分支逐条 `cherry-pick`；能**预判冲突**、冲突时**逐文件选择保留本地或采用上游**；提交标题带**中英对照**（离线词表 + 可选联网翻译）。
并对每条提交给出**改动规模**与**中文取舍建议**（建议采用 / 采用但需实测 / 建议单独评估），支持在界面内**查看该提交的 diff**。

本工具**不联网同步代码**，只操作本地 git；联网仅用于标题翻译（可关闭）。

---

## 2. 运行方式

```bash
# 网页界面（推荐）：自动选端口 8765~8784 并打开浏览器
python dev_tools/upstream_sync_web.py

# 命令行后端
python dev_tools/upstream_sync.py --help
```

- 依赖：**仅 Python 标准库**（`http.server` / `subprocess` / `urllib` / `hashlib` / `difflib`）。无第三方包。
- 服务只监听 `127.0.0.1`，非交互式；`PAGE` 是模块级常量（见 §10 陷阱）。
- 中文输出，Windows 环境（PowerShell），仓库根目录即工作目录。

---

## 3. 文件清单与职责

| 文件 | 职责 | 是否入库 |
|---|---|---|
| `dev_tools/upstream_sync.py` | 后端：git 操作、CLI 子命令、冲突解析与中文分析 | 是 |
| `dev_tools/upstream_sync_web.py` | 前端 + 本地 HTTP 服务；内含 HTML/CSS/JS（`PAGE` 常量）与翻译模块 | 是 |
| `dev_tools/upstream_manifest.md` | `list` 生成的 Markdown 清单（生成物） | 否（未跟踪） |
| `dev_tools/baidu_translate.json` | 百度翻译凭据 `{"appid","key"}` | **否，含密钥，勿提交** |

两者通过**子进程 + 约定的 JSON 行协议**解耦（见 §5.1）。前端不直接调 git。

---

## 4. 架构与数据流

```
浏览器 PAGE(HTML/JS)
   │  fetch
   ▼
Handler (ThreadingHTTPServer, 127.0.0.1)
   │  subprocess: [python, upstream_sync.py, ...args]
   ▼
upstream_sync.py ──► git（upstream 远程 / czr 基线 / cherry-pick）
   │
   └─► stdout 里输出一行  @@SYNC@@{json}
          ▲
Handler 用 parse_sync_json() 取"最后一行 @@SYNC@@ 之后的 JSON"
```

关键设计：**大部分需要被界面理解的结果，后端都用 `emit(obj)` 打印成 `@@SYNC@@{json}` 单行**，其余 stdout/stderr 原样透传给界面日志区。
> 例外：`list --json` **不走** `emit`——它把整段 JSON 写入 `--out` 指定文件（无 `--out` 时直接打印到 stdout），web 端 `get_commits()` 读该临时文件，而非用 `parse_sync_json()`。

---

## 5. 后端契约（`upstream_sync.py`）

### 5.1 通信协议

- 常量：`JSON_MARK = "@@SYNC@@"`（两端各有一份，**改要同步改**）。
- `emit(obj)`（backend 约 L86）打印 `@@SYNC@@` + `json.dumps(obj, ensure_ascii=False)`。
- `parse_sync_json(output)`（web 约 L362）取输出中**最后一条** `@@SYNC@@` 行并 `json.loads`，失败返回 `{}`。

### 5.2 全局参数与默认值（backend L30–L35）

| 常量 | 值 | 含义 |
|---|---|---|
| `UPSTREAM_REMOTE` / `UPSTREAM_URL` | `upstream` / `https://github.com/runhey/OnmyojiAutoScript.git` | 上游远程 |
| `UPSTREAM_BRANCH` | `dev` | **对比的就是上游 dev 分支** |
| `DEFAULT_BASE` | `czr` | 本地基线分支（**默认对比基准与同步目标**；测试后再合并到 `mine`） |
| `DEFAULT_SINCE` | `2 months ago` | 默认只对比最近两个月 |
| `DEFAULT_MANIFEST` | `dev_tools/upstream_manifest.md` | 清单默认输出 |

CLI：`python dev_tools/upstream_sync.py [--base czr] [--since "<git 时间表达式>"] [--remote-url <地址>] [--remote-branch <分支>] <子命令>`

> `--remote-url/--remote-branch` 为可选数据源：留空走默认 `upstream/dev`（`runhey/OnmyojiAutoScript`）；
> 指定时改用专用 remote `syncsrc`（`git remote set-url` 指向该地址），`ref` 变为 `syncsrc/<分支>`。见 §13.12。

### 5.3 子命令

| 子命令 | 参数 | 作用 | `emit` 的 JSON |
|---|---|---|---|
| `fetch` | — | 建 remote 并 `git fetch <remote> <branch>`（默认 upstream/dev） | 无（纯文本输出） |
| `branches` | `--url URL` | 列出任意仓库的远程分支（`git ls-remote --heads`，含代理回退与禁交互） | `{"url","branches","default"}` |
| `list` | `--out PATH`、`--json` | 生成清单；`--json` 输出数据供界面消费 | 见下 |
| `apply` | `--manifest`、`--branch`、`--deps`、`--pause` | 建 `sync/*` 分支并逐条 cherry-pick | `{"status":"conflict"\|"done","branch","commit","files":[...]}` |
| `conflicts` | — | 查看当前未解决冲突 | `{"status":"conflict"\|"idle","branch","commit","files":[...]}` |
| `resolve` | `--choices`、`--choices-file` | 按选择处理冲突文件并继续 | `{"status":"done"\|"conflict",...}` |
| `abort` | — | 中止 cherry-pick、回 `czr`、删 sync 分支 | `{"status":"aborted","branch"}` |
| `conflict-detail` | `--file PATH` | 单文件三阶段差异 + 中文原因分析 | 见 §5.4 |
| `show` | `--commit HASH` | 查看某提交的改动摘要（stat）+ diff，供界面预览 | `{"status":"ok","commit","stat","patch","truncated"}` |
| `advise` | `--json`、`--out PATH` | 逐条冲突预判（merge-tree）+ 本地定制度，据此修正 `level`/`judge`/`reasons`；供 AI 顾问解读 | `{"base","ref","since","summary","commits":[...]}` |
| `ignore` | `--hashes H1,H2` | 把提交标记为「跳过」，写入 `DEFAULT_IGNORED`（`dev_tools/upstream_ignored.json`，**不入库**）；反查元数据一并存入 | `{"status":"ok","added","total"}` |
| `unignore` | `--hashes H1,H2` | 按前缀（≥8 位）删除已跳过记录；前缀命中多条即报错退出 | `{"status":"ok","removed","total"}` |
| `ignored` | `--json` | 列出已跳过记录 | `{"items":[...]}` |

`advise --json` 在 `list` 字段基础上，每条追加：

```json
"conflict":    {"status": "ok|conflict|error", "files": ["冲突文件…"]},
"local_churn": {"lines": 529, "level": "low|medium|high"}
```

`summary` = `{"total","adopt","caution","review","conflict"}`。`level`/`judge`/`reasons` 已被冲突与本地定制度**就地修正**（冲突→至少 caution；本地定制 high→review）。仍走 `--out` 文件或 stdout，**不走 emit**。

`list --json` 输出（**界面依赖此结构**）：

```json
{
  "base": "czr",
  "ref": "upstream/dev",
  "since": "2 months ago",
  "commits": [
    {
      "hash": "<40位>", "date": "2026-09-19", "author": "...", "subject": "fix(xxx): ...",
      "type": "fix", "module": "GeneralBattle", "risk": "isolated|multi|shared",
      "files": ["tasks/Component/GeneralBattle/battle_wait.py"],
      "adds": 12, "dels": 4, "changed": 2,
      "size": "small|medium|large", "framework": false,
      "level": "adopt|caution|review", "judge": "✓ 建议采用",
      "reasons": ["中文理由…"]
    }
  ],
  "applied": [ "…元素字段与 commits 相同（只读，内容已在本地）…" ],
  "ignored": [
    {
      "hash": "<40位>", "subject": "…", "date": "…", "module": "…", "type": "…",
      "source": "upstream/dev | <地址> · <分支>", "ignored_at": "2026-10-07 12:00:00",
      "reason": "manual", "present": true
    }
  ]
}
```

- `commits`：待同步（**已剔除** `applied` 与 `ignored`）。
- `applied`：`git cherry` patch-id 等价 = **内容已并入本地**（只读）。其覆盖**全历史**，已与本次 `--since` 窗口**求交**（否则会膨胀）。
- `ignored`：**已跳过**（持久化，可恢复）；`present=false` 表示该 hash **已不在当前上游窗口**（被 rebase / 移除），界面标注「哈希已不存在」。`ignored` 与 `applied` 可能重叠，界面以 `applied` 为准去重。

> 注意：`list --json` 的输出是**对象**（不再是数组）；无提交时也会输出空 `commits` 数组（`if not commits and not args.json` 才提前返回）。

`conflict-detail` 输出：

```json
{"status":"ok","file":"<路径>","binary":false,
 "has_base":true,"has_ours":false,"has_theirs":true,
 "hunks":[{"ours":"...","theirs":"..."}],
 "analysis":["中文冲突原因分析..."],
 "ours_text":"...","theirs_text":"..."}
```

`has_ours/has_theirs/has_base` 为 `false` 表示该文件在该阶段不存在（如"本地删除 / 上游修改"这种 modify-delete 冲突），前端据此决定按钮是否可用。

### 5.4 关键后端函数（backend）

| 函数 | 约行 | 作用 |
|---|---|---|
| `collect_commits(base, ref, since, exclude_applied)` | L233 | `git log --no-merges --reverse --numstat base..ref`，产出含 `files`、`adds`、`dels`、`changed` 的提交列表，并计算 `size`/`framework`/`level`/`judge`/`reasons` |
| `size_of(changed, churn)` | L173 | 按文件数与增删行数分 `small/medium/large`（阈值 `SIZE_SMALL`/`SIZE_MEDIUM`） |
| `framework_hit(files)` | L152 | 是否触及框架/公共文件（`FRAMEWORK_FILES`/`FRAMEWORK_PREFIXES`） |
| `touched_roots(files)` | L161 | 提交涉及的顶层范围，用于判断是否横跨多模块 |
| `judge(commit)` | L182 | 合成中文取舍建议，返回 `(level, 结论, 理由列表)` |
| `_numstat_path(path)` | L214 | 归一化 `--numstat` 的重命名路径（`{old => new}` → 新路径） |
| `cmd_show(args)` | L782 | `git show --stat` + diff（截断 `MAX_PATCH_CHARS`），供界面改动预览 |
| `cmd_advise(args)` | — | `advise` 子命令：`collect_commits` + 逐条 `precheck_commit` + `local_churn`，修正 `level`/`judge`/`reasons` |
| `precheck_commit(h, base)` | — | 单提交 `git merge-tree --merge-base={h}^ base h` 模拟 cherry-pick，返回 `{"status":"ok\|conflict\|error","files"}` |
| `merge_tree_conflict_files(out)` | — | 解析 merge-tree 输出取冲突文件（首行 tree OID 跳过，空行截止） |
| `local_churn(base, ref)` | — | `git diff --numstat <merge-base(base,ref)>..base` → `{路径: 本地改动行数}`（单次调用，缓存全表） |
| `churn_level(lines)` | — | 按 `LOCAL_CHURN_MEDIUM(80)` / `LOCAL_CHURN_HIGH(300)` 分 `low/medium/high` |
| `already_applied` | L238 | `git cherry` 按 patch-id 过滤"内容已在本地"的提交 |
| `load_ignored` / `save_ignored` | L251 / L265 | 读写 `dev_tools/upstream_ignored.json`（`load` 容错：缺失/损坏返回 `[]`） |
| `ignored_hashes` / `match_ignored` | L273 / L278 | 已跳过 hash 集合；按前缀（**<8 位返回 `[]`**）匹配记录 |
| `parse_hashes` | L286 | 逗号分隔字符串 → 小写 hash 列表 |
| `cmd_ignore` / `cmd_unignore` / `cmd_ignored` | L642 / L689 / L719 | 跳过 / 恢复 / 列出已跳过；`ignore` 反查元数据存档，`unignore` 前缀歧义即退出 |
| `module_of` / `risk_of` | L110 / L127 | 模块归属、冲突风险（`shared` = 触及 i18n/config 等共享文件） |
| `cmd_apply` | L324 | 建分支 + 循环 cherry-pick；`--pause` 时冲突**不中止不清理** |
| `in_cherry_pick` / `skip_empty_pick` / `continue_pick` | L469 / L493 / L503 | cherry-pick 状态机（含空提交 `--skip`/`--quit` 差异处理） |
| `resolve_one` | L536 | 单文件处理：`checkout --ours/--theirs`；缺阶段时退回 `git rm -f` |
| `parse_conflict_hunks` / `analyze_conflict` | L607 / L632 | 解析冲突标记、生成中文原因分析 |
| `_stage_content` | L602 | 取 `:1:`(base)/`:2:`(ours)/`:3:`(theirs) 三阶段内容 |

### 5.5 冲突状态机（重要）

```
apply --pause
  ├─ 全部干净        → status=done
  └─ 某提交冲突      → status=conflict（工作区停在冲突态，分支保留）
        │
        ├─ conflicts / conflict-detail  → 用户查看
        ├─ resolve --choices-file       → resolve_one 逐文件 → continue_pick
        │      ├─ 又有冲突 → status=conflict（循环）
        │      └─ 全部完成 → status=done
        └─ abort                        → 回 czr + 删分支
```

要点：
- 冲突处理**必须在暂停态进行**；`doApply` 在前端会被禁用（`btnApply.disabled`）。
- 单提交无 sequencer，`cherry-pick --skip` 会失败，需 `cherry-pick --quit`（`skip_empty_pick` 已处理）。
- "删除/修改"类冲突缺某个 stage，`checkout --ours/--theirs` 会报错，需 `git rm -f`（`resolve_one` 已处理）。

---

## 6. HTTP API 契约（`upstream_sync_web.py` 的 `Handler`）

所有响应均为 JSON（`Cache-Control: no-store, must-revalidate`），由 `_send()` 统一发出。

| 方法 | 路径 | 请求体 | 响应 |
|---|---|---|---|
| GET | `/`、`/index.html` | — | `PAGE`（内嵌 HTML） |
| GET | `/api/commits?since=&refresh=0\|1&remote_url=&remote_branch=` | — | `{"commits":[...],"applied":[...],"ignored":[...],"range":"runhey/OnmyojiAutoScript · upstream/dev → czr（自 … 起）"}` 或 `{"error":...}`；传 `remote_url` 时 `range` 变「地址 · 分支 → …」 |
| POST | `/api/precheck` | `{"hashes":[...]}` | `{"results":{hash:{"status":"ok"\|"conflict"\|"error","files":[...]}}}` |
| POST | `/api/apply` | `{"hashes":[...],"branch":"...","remote_url":"...","remote_branch":"..."}`（后两个可选） | `{"code","output","result":<apply JSON>}` |
| POST | `/api/conflicts` | `{}` | `run_sync_json` 包装（`{"code","output","result"}`） |
| POST | `/api/conflict-detail` | `{"file":"..."}` | 同上 |
| POST | `/api/show` | `{"commit":"<hash>"}` | `run_sync_json` 包装，`result` 含 `stat`/`patch`/`truncated` |
| POST | `/api/advise` | `{"since":"...","force":false,"remote_url":"...","remote_branch":"..."}`（后两个可选） | `{"commits":[...],"range":"…（… · AI 顾问）"}` 或 `{"error":...}`（同 `get_commits` 结构，每条多 `conflict`/`local_churn`；带进程内缓存，较慢） |
| POST | `/api/branches` | `{"url":"<仓库地址>"}` | `{"url","branches":["dev",...],"default":"dev"}` 或 `{"error":...}`（`git ls-remote --heads`，含代理回退与禁交互，超时 180s） |
| POST | `/api/ignore` | `{"hashes":[...],"remote_url":"...","remote_branch":"..."}`（后两个可选） | `run_sync_json` 包装；成功后**作废 `_ADVISE_CACHE`** |
| POST | `/api/unignore` | `{"hashes":[...]}` | 同上（无需数据源参数） |
| POST | `/api/resolve` | `{"choices":{"<path>":"ours"\|"theirs"}}` | 同上 |
| POST | `/api/abort` | `{}` | 同上 |
| POST | `/api/translate` | `{"texts":["...","..."]}` | `{"translations":{"<原文>":"<中文>"},"provider":"百度"\|"有道"}` |

`/api/commits` 会在后端提交对象上**补充** `head_zh`、`desc`、`subject_zh`、`module_zh` 四个字段（界面直接消费）；`applied` / `ignored` 两路同样经 `_decorate_commits()`。

预检实现（`precheck()`，web 约 L1133）：对每个 hash 执行

```bash
git merge-tree --write-tree --name-only --merge-base=<hash>^ czr <hash>
```

- 返回码 `0` → `ok`；`1` → `conflict`；其他 → `error`。
- 冲突文件解析见 `_merge_tree_files()`：输出**第 1 行是 tree OID**，其后到**第一个空行**之间才是冲突文件名列表。

`/api/advise`（`get_advise()`）与 `/api/commits`（`get_commits()`）同构，差异：① 子命令换成 `advise --json --out <临时文件>`（同样**不走 emit**，读文件解析）；② 结果带**进程内缓存** `_ADVISE_CACHE`（键为 `(since, remote_url, remote_branch)`，换数据源自动失效），同一份上游数据重复点击即时返回；`/api/commits?refresh=1`（重新 fetch）会令缓存失效；③ 超时设为 1800s，超时返回 `{"error":"…超时…"}`。两者均可选带 `force` 跳过缓存。因 `advise` 全量较慢，界面**手动触发**（见 §13.11）。

**自定义数据源**：`/api/commits`、`/api/advise`、`/api/apply` 均接受可选 `remote_url` / `remote_branch`。后端用 `source_args()` 拼成 CLI 前置参数（留空 url → 不产出任何参数 → 走默认 `upstream/dev`，向后兼容）；`_src_label()` 决定 `range` 里的显示名。见 §13.12。

---

## 7. 翻译链路（可整体关闭）

优先级：**百度 → 有道 demo → MyMemory → 离线词表**；任一步失败静默降级。

- 离线词表（始终可用，首屏立即渲染）：`TYPE_ZH` / `MODULE_ZH` / `WORD_ZH`（web L37–L107），
  `translate_phrase()` 按 **`\b` 词边界**替换整词，**不会破坏 CamelCase / 下划线标识符**。
- 标题拆分：`split_subject()` 用正则 `^([A-Za-z]+)(\((.*)\))?(!?):\s*(.*)$` 拆出"中文类型前缀 + 英文描述"，
  只有**描述部分**参与联网翻译（`translate_subject()` 给首屏离线结果）。
- 联网：`translate_texts(texts)` 把多条英文用 `"\n"` 拼接成**一次请求**（后端接口按行返回），
  再按行拆回；批大小受 `TR_BATCH_CHARS=900` / `TR_MAX_ITEM=400` / `TR_SLEEP=0.3` 控制。
- 百度凭据：环境变量 `BAIDU_TRANSLATE_APPID` / `BAIDU_TRANSLATE_KEY` 优先，其次 `dev_tools/baidu_translate.json`。
  `baidu_ready()` 懒加载；签名 `md5(appid + q + salt + key)`。
- MyMemory 被限流（429/503）后冷却 300s（`_MM_DISABLED_UNTIL`）；有道 `errorCode 411` 会重试一次。
- 前端：`onlineTr` 开关（默认开）、`translateMissing()` 按批补全、`trCache`（原文→译文）、`trFail`（失败集合，保证循环终止）。
  **译文不落盘**，进程重启即清空。

---

## 8. 前端结构（`PAGE` 内嵌 HTML/JS）

**布局**：`header`（标题 + `#rangeSub` 对比范围 + `#stats`）→ `toolbar`（**数据源行** + 时间范围/拉取 + 筛选/预检）→ **`.tabs`（待同步 / 已排除·跳过）** → `#banner` → `#cpanel`（冲突面板）→ `#list`（提交列表，**两个视图共用**）→ `footer`（分支名 + `#btnApply`）→ `#log`。筛选行 / 操作行 / `#cpanel` / `footer` 带 `pend-only` 类，切到「已排除·跳过」时由 `body.view-ign .pend-only{display:none!important}` 隐藏。

**关键 DOM id**：`repoUrl` `repoBranch` `btnLoadBranches` `btnConnect` `srcStatus` `since` `btnRefresh` `btnFetch` `q` `typeChips` `risk` `level` `module` `orig` `online` `trStatus` `btnSelAll` `btnClear` `btnPrecheck` `btnAdvise` `btnSkipSel` `adviseStatus` `selCount` `tabPend` `tabPendN` `tabIgn` `tabIgnN` `banner` `cpanel` `list` `branch` `btnApply` `log` `rangeSub` `stats`。

**关键 JS 状态**：

| 变量 | 含义 |
|---|---|
| `commits` | 后端返回的**待同步**提交数组（含 `files`、`*_zh`） |
| `applied` / `ignored` | 「已并入本地」（只读）/「已跳过」（可恢复）；均来自 `/api/commits` |
| `view` | `"pend"`（待同步）/ `"ign"`（已排除·跳过）；`render()` 按它分派 |
| `selected` | 已勾选 hash 的 `Set` |
| `chosenTypes` / `collapsed` | 类型筛选、模块折叠 |
| `pc` | 预检结果：`hash -> {status, files}`（`precheck` 或 `advise` 写入） |
| `pcBusy` / `adviseBusy` | 冲突预检 / AI 顾问进行中（互不阻塞，各自禁用按钮） |
| `showOriginal` / `onlineTr` | 显示英文原文 / 联网翻译开关 |
| `trCache` / `trFail` | 联网译文缓存 / 失败集合 |
| `conflict` | 当前冲突上下文 `{commit,subject,branch,files,choices,details}` |
| `diffCache` | `hash -> 改动预览结果`（点「查看改动」时按需加载并缓存；换清单时清空） |

**关键函数**：`filtered()`（筛选 **+ 按 `date` 倒序排序**；含 `risk` / `level` / 类型 / 模块 / 搜索过滤）、`render()`（**先按 `view` 分派**：`ign` → `renderIgnored()`，否则按模块分组渲染，每条提交显示 `size` 规模与 `judge` 中文建议徽章，下方带可展开的"更新文件 N 个"清单与"查看改动"面板；冲突文件标红并自动展开；每行末尾带「跳过」按钮）、`subjectText()`（联网译文 > 离线译文 > 原文）、`judgeBadge()` / `sizeText()`（取舍建议与规模展示）、`pcBadge()` / `pcState()` / `pcFiles()`、`runPrecheck()`、`runAdvise()`、`doApply()`、`showConflict()` / `renderConflict()` / `doResolve()` / `doAbort()`、`loadCommits()`、`translateMissing()`、`srcUrl()` / `srcBranch()` / `sourceParams()`（数据源取值，留空 url 即默认源）、`setSrcStatus()`、`loadBranches()`（`POST /api/branches` 填充 `#repoBranch`）、**`updateTabCounts()`**（Tab 计数）、**`ignoredView()`**（按 `applied` 去重后的已跳过列表）、**`setView(v)`**（切 Tab：切 `body.view-ign` 类 + 重渲染）、**`doIgnore(hashes)` / `doUnignore(hash)`**（就地增删，不整页重载）、**`renderIgnored()`**（扁平分组：「我跳过的」带「恢复」按钮；「已并入本地」默认折叠）。

**数据源行绑定**：`#btnLoadBranches` → `loadBranches`；`#btnConnect` → `loadCommits(true)`（连接自定义源并拉取比对）；`#btnRefresh`/`#btnFetch` 沿用 `loadCommits(false|true)`。`loadCommits` / `runAdvise` / `doApply` 均读 `sourceParams()` 并透传 `remote_url` / `remote_branch`。见 §13.12。

**排序**：`filtered()` 末尾 `.sort((a,b) => b.date.localeCompare(a.date) || b.hash.localeCompare(a.hash))` —— 模块**内**按时间倒序；模块之间的顺序仍是**提交数量降序**（`render()` 中的 `names.sort`）。若要"整页时间轴"，需同时改这两处。

---

## 9. 改哪里（扩展索引）

| 想改的东西 | 位置 |
|---|---|
| 汉化词表 / 术语 | web `TYPE_ZH` / `MODULE_ZH` / `WORD_ZH`（L37–L107） |
| 高风险文件判定 | backend `SHARED_PREFIXES` / `SHARED_FILES`（L58–L63）、`risk_of()` |
| 改动规模阈值 | backend `SIZE_SMALL` / `SIZE_MEDIUM` / `MULTI_REVIEW_CHURN`（L70–L72）、`size_of()` |
| 中文取舍建议规则 | backend `judge()`（L182）；"框架文件"范围用 `FRAMEWORK_FILES` / `FRAMEWORK_PREFIXES`（L66–L67） |
| 改动预览（diff） | backend `cmd_show()`（L782）+ `MAX_PATCH_CHARS`（L74）；web `/api/show`、前端 `render()` 的"查看改动"面板 |
| 默认时间范围 | backend `DEFAULT_SINCE`（L35）、web `DEFAULT_SINCE`（L30） |
| 跳过/恢复的持久化 | backend `DEFAULT_IGNORED`（L37）→ `dev_tools/upstream_ignored.json`（**不入库**）；`.gitignore` 已加白名单；界面「已排除·跳过」视图（§13.13） |
| 提交列表新增字段 | backend `collect_commits()` → `cmd_list --json` → web `get_commits()` → 前端 `render()` |
| 排序规则 | `filtered()`（组内）、`render()` 的 `names.sort`（模块间） |
| 冲突中文分析文案 | backend `analyze_conflict()`（L632） |
| 冲突文件差异展示 | 前端 `renderConflict()` + `/api/conflict-detail` |
| 预检逻辑（不落地、只模拟） | web `precheck()` / `_merge_tree_files()` |
| 翻译提供方顺序 | web `_translate_chunk()` / `translate_texts()` |
| 端口 / 绑定地址 | web `HOST`、`DEFAULT_PORT`、`pick_port()` |

---

## 10. 已知约束与陷阱

1. **`PAGE` 是模块级常量**：改前端代码后必须**重启** `upstream_sync_web.py`，没有热重载。
2. **浏览器缓存**：曾出现"改了看不到"的误导性现象。`_send()` 已加 `no-store`；若新增绕过 `_send` 的响应路径，记得补缓存头。调试时用 `?v=<时间戳>` 强制刷新。
3. **`origin` 是 gh-proxy 只读镜像**：`git push origin` 会报 `No anonymous write access`。需要**直连 `github.com`** 推送（把 token 放进 URL，并用 `-c credential.helper=` 避免凭据管理器弹窗）。
4. **`baidu_translate.json` 含明文密钥**，且仓库未加 `.gitignore`（用户明确要求不加）。提交前务必确认**没有被 `git add`**。
5. **`or` 短路陷阱**：`_translate_chunk` / `translate_texts` 用 `A or B` 串行降级，注意返回 `None` 与返回空列表的语义差别。
6. **`merge-tree --name-only` 输出格式**：第 1 行是 tree OID，随后是冲突文件名，遇**空行**结束。不要直接 `len(输出行)`。
7. **PowerShell 不支持 heredoc**（`<<`）与 `&&`：写临时脚本请用 Write 工具生成 `.py` 再执行。
8. **`git cherry` 过滤**：`list` 默认排除"内容已在本地（hash 不同）"的提交；排查"提交不见了"时先确认这里。
9. **翻译接口是免费额度**：百度通用翻译每月约 5 万字；有道 demo / MyMemory 易限流。调试时别反复全量重跑。
10. **服务只监听 127.0.0.1**，端口从 8765 起自动顺延最多 20 个（`pick_port()`）。
11. **规模/建议是启发式**：`judge()` 只看文件数、增删行数与触及目录，不读代码语义，仅作取舍参考。重命名路径经 `_numstat_path()` 归一化；二进制文件 numstat 为 `-`，不计入增删行数。阈值可调（见 §9）。

---

## 11. 验证方法（改完必做）

```bash
# 1) 语法
python -m py_compile dev_tools/upstream_sync.py dev_tools/upstream_sync_web.py

# 2) 后端数据面（应含 commits[].files 及 adds/dels/size/level/judge/reasons）
python dev_tools/upstream_sync.py list --json | more

# 2b) 改动预览（应含 stat 与 patch）
python dev_tools/upstream_sync.py show --commit 0e711238

# 2c) 跳过/恢复闭环（hash 前缀至少 8 位；先记下一条 hash 再还原）
python dev_tools/upstream_sync.py ignored --json          # 初态 items
python dev_tools/upstream_sync.py ignore  --hashes <hash前8位>
python dev_tools/upstream_sync.py list --json             # commits 少 1 条、ignored 多 1 条
python dev_tools/upstream_sync.py unignore --hashes <同一前缀>
python dev_tools/upstream_sync.py ignore  --hashes abc     # 期望：报「至少 8 位」并 exit=1
```

```powershell
# 3) HTTP 面（服务已启动时）
$j = (Invoke-WebRequest "http://127.0.0.1:8765/api/commits?since=2%20months%20ago&refresh=0" -UseBasicParsing).Content | ConvertFrom-Json
$j.range; $j.commits.Count; $j.commits[0].files

# 4) 预检（已知用例：0e711238 会与 czr 冲突）
Invoke-WebRequest "http://127.0.0.1:8765/api/precheck" -Method POST -ContentType "application/json" -Body '{"hashes":["0e711238"]}' -UseBasicParsing | Select-Object -Expand Content
# 期望：{"results":{"0e711238":{"status":"conflict","files":["tasks/Component/GeneralBattle/battle_wait.py"]}}}
```

```bash
# 5) 冲突全链路（手工）
python dev_tools/upstream_sync.py apply --manifest <含冲突提交的清单> --pause
python dev_tools/upstream_sync.py conflicts
python dev_tools/upstream_sync.py conflict-detail --file tasks/Component/GeneralBattle/battle_wait.py
python dev_tools/upstream_sync.py resolve --choices '{"tasks/Component/GeneralBattle/battle_wait.py":"ours"}'
# 或放弃： python dev_tools/upstream_sync.py abort
```

6) **界面回归**：打开 `http://127.0.0.1:8765/?v=<时间戳>`，确认
   ① 副标题显示 `upstream/dev → czr`；
   ② 每条提交下有"▸ 更新文件 N 个"可展开；
   ③ 搜索 `0e711238` → 勾选 → "冲突预检" → 出现红色徽章 `⛔ 冲突 1 文件`，文件清单自动展开且路径标红；
   ④ 每条提交标题前有中文取舍建议徽章（✓/⚠/🛑），标题后有 `+X/-Y · N文件`；顶部统计含"建议采用/需实测/建议评估"计数；
   ⑤ 点某条"查看改动" → 展开显示 diff（`commit <hash>` + 文件改动）；"全部建议"下拉可按建议筛选。

---

## 12. 术语表

| 词 | 含义 |
|---|---|
| `czr` | 开发/暂存分支：**默认对比基准与同步目标**（`DEFAULT_BASE` / `BASE_BRANCH`）；测试一段时间无误后自行合并到 `mine` |
| `mine` | 本地定制基线分支，`czr` 的最终合并去向（**不再是默认同步基准**） |
| `upstream/dev` | 上游官方开发分支（对比目标） |
| `sync/*` | 每次同步新建的临时分支，验证后自行合并回 `czr` |
| `risk=shared` | 触及共享基础设施文件（i18n/config 等），冲突概率高 |
| `isolated` / `multi` | 只动一个模块 / 跨多个模块 |
| `ours` / `theirs` | 冲突时"保留本地" / "采用上游" |

---

## 13. 本次增强记录：取舍建议 + 改动预览

> 目的：让**不懂代码**的使用者也能一眼判断某条上游提交"该不该采用"，并在界面内看清"到底改了什么"（彩色 diff）。
> 本节是给其他 agent 工具接手优化的入口，请先读这里再动 §5–§9。

### 13.1 改了哪些文件

| 文件 | 改动点 |
|---|---|
| `dev_tools/upstream_sync.py` | ① `collect_commits()` 改用 `git log --numstat` 采集增删行数；② 新增 `size_of()` / `framework_hit()` / `touched_roots()` / `judge()` / `_numstat_path()`；③ `list --json` 暴露新字段；④ Markdown 清单行尾追加规模与建议；⑤ 新增 `cmd_show()` 与 `show` 子命令 |
| `dev_tools/upstream_sync_web.py` | ① 新增 `/api/show` 路由与 `get_commit_detail()`；② 前端新增 `judgeBadge()` / `sizeText()` / `renderDiff()`；③ 列表显示建议徽章与规模；④ 新增"查看改动"彩色 diff 面板；⑤ 工具栏新增"建议"筛选 `#level`；⑥ 统计区新增三档计数 |
| `dev_tools/upstream_sync_doc.md` | 同步上述契约，并新增本节 |

### 13.2 新增数据字段（`list --json` 的 `commits[]`）

| 字段 | 类型 | 含义 |
|---|---|---|
| `adds` / `dels` | int | 该提交新增 / 删除行数（二进制文件不计） |
| `changed` | int | 改动文件数 |
| `size` | `small` / `medium` / `large` | 改动规模 |
| `framework` | bool | 是否触及框架/公共文件 |
| `level` | `adopt` / `caution` / `review` | 取舍建议等级 |
| `judge` | str | 中文结论（如"✓ 建议采用"） |
| `reasons` | str[] | 中文理由列表（前端徽章悬停显示） |

### 13.3 常量与调参（backend 顶部）

| 常量 | 默认值 | 作用 |
|---|---|---|
| `FRAMEWORK_PREFIXES` | `("module/", "assets/i18n/")` | 视为"框架/公共设施"的路径前缀 |
| `FRAMEWORK_FILES` | `{"gui.py","script.py","server.py"}` | 同上，入口脚本 |
| `SIZE_SMALL` | `(3, 60)` | 文件数/增删行数均不超过 → `small` |
| `SIZE_MEDIUM` | `(10, 300)` | 均不超过 → `medium`，否则 `large` |
| `MULTI_REVIEW_CHURN` | `150` | 横跨 ≥3 目录且增删行数超过此值才升为 `review` |
| `MAX_PATCH_CHARS` | `200000` | `show` 返回 diff 上限，超出截断并置 `truncated=true` |

调参：想更"宽松"（少报 review）就调大 `SIZE_MEDIUM` / `MULTI_REVIEW_CHURN`；更"保守"就调小。改这些值即可，无需改逻辑。

### 13.4 `judge()` 决策规则（伪代码）

```
level = adopt
若 framework_hit(files):               level = caution；理由 += "触及框架/公共文件…"
若 size == large:                      level = review； 理由 += "改动很大…"
否则若 size == medium:                  level==adopt → caution；理由 += "中等改动…"
若 len(touched_roots(files)) >= 3:
        增删 >= MULTI_REVIEW_CHURN    → review
        否则 level==adopt             → caution
        理由 += "横跨 N 个模块/目录…"
若 level == adopt:                     理由 += "改动集中、范围独立…"
```

### 13.5 `show` 子命令 / `/api/show`

- CLI：`python dev_tools/upstream_sync.py show --commit <hash>`
- 内部：`git show --stat --format=`（摘要）+ `git show --format= --no-color --unified=3`（**纯 patch，无 Author/Date 头部噪声**）。
- `emit`：`{"status":"ok","commit","stat","patch","truncated"}`；`patch` 超 `MAX_PATCH_CHARS` 截断。
- HTTP：`POST /api/show`，体 `{"commit":"<hash>"}`，用 `run_sync_json` 包装（响应 `{"code","output","result"}`）。

### 13.6 前端"查看改动"的渲染（"直观"的关键）

- 状态：`diffCache = {hash: result}`，按需加载；`loadCommits()` 时清空。
- 交互：每条提交下方"▸ 查看改动" → 点击展开 → `fetch('/api/show')` → 渲染。
- 面板结构：`摘要 .diffsum`（共改动 N 文件 · 新增 +X · 删除 -Y）→ `文件统计 pre.diffstat` → `彩色 diff pre.diffpatch` →（截断提示）。
- `renderDiff(patch)` 按行前缀分类着色：

| 行前缀 / 正则 | class | 样式 |
|---|---|---|
| `diff --git` `new file` `deleted file` `rename ` `copy ` | `.fhead` | 黄色加粗（文件头） |
| `@@` | `.hunk` | 灰蓝底 |
| `index ` `similarity` `+++` `---` `\ ` | `.meta` | 灰色（元信息） |
| `+`（非 `+++`） | `.add` | 浅绿底 + 绿字 |
| `-`（非 `---`） | `.del` | 浅红底 + 红字 |
| 其他 | `.dctx` | 普通上下文 |

实现要点：`patch.split("\n")` 逐行生成 `<span class="dline <cls>">`，`display:block` 使每行独立；空行用 `&nbsp;` 占位保持行高；**所有文本都经 `esc()` 转义**。

### 13.7 界面上的表现（改完自查）

- 工具栏第三个下拉 `#level`："全部建议 / ✓ 仅建议采用 / 隐藏 🛑 建议评估"。
- 每条提交：标题前建议徽章（悬停显示 `reasons`），标题后 `+X/-Y · N文件`。
- 顶部统计：`建议采用 N · 需实测 N · 建议评估 N · ⚠ 高风险 N · 模块 N`。

### 13.8 后续可优化点（交接建议）

1. diff 视图可增加**行号**、"仅看改动文件"跳转、折叠未改动区块（`@@` 之间）。
2. `judge()` 可结合 `czr` 侧同文件 diff，判断"本地是否也已大改"，降低误报。
3. 支持一次展开多个提交，或"导出选中提交的合并预览"。

### 13.9 「拉取上游最新」报错修复（fetch 健壮性）

**症状**：界面点「拉取上游最新」报错。两条独立根因，均已修：

1. **UnicodeEncodeError（必现，与网络无关）**——`upstream_sync_web.py` 的 `run_sync()` 用管道捕获子进程 stdout，Windows 中文环境默认 **GBK**，`cmd_fetch` 打印的 `⚠`(U+26A0) 无法编码 → `'gbk' codec can't encode character '\u26a0'`，fetch 直接崩溃。
   **修**：`run_sync()` 给子进程注入 `env = {**os.environ, "PYTHONIOENCODING": "utf-8"}`（子进程编码固定 UTF-8，父进程沿用 `encoding="utf-8", errors="replace"`）。
2. **直连 github 超时**——本机 git 未配代理，直连 `github.com:443` 20s 后失败（浏览器走系统代理所以能上）。
   **修**：新增 `detect_local_proxy()` 与 `git_with_proxy()`（backend，`cmd_fetch` 附近）。`fetch` 先直连，失败则探测本机代理重试一次；代理来源优先级 `OAS_GIT_PROXY` > `127.0.0.1:7897` > `127.0.0.1:10809`（探测方式：0.3s TCP 连接）。**仅对 `fetch` 生效、仅注入子进程 env，不改 git config**（遵守"不改 git config"约束）。

**代价**：直连失败需等约 20s 才回退，`refresh=1` 整体约 24s（可接受，属手动低频操作）。
**自验**：`python dev_tools/upstream_sync.py fetch`（不设任何代理环境变量）→ 打印"直连失败，改用本机代理 … 重试"→ exit=0，118 条；`GET /api/commits?refresh=1` → `commits=118` 且无 `error` 字段。

### 13.10 AI 顾问模式（`advise` 子命令）

**目的**：让不了解项目的用户不必自己判断"哪些提交能合"。AI 调用 `advise` 拿深度信号 → 产出人话建议表 → 用户确认 → AI 执行 cherry-pick / 解冲突。

**新增信号（相对 `list`）**：

| 字段 | 来源 | 说明 |
|---|---|---|
| `conflict.status` / `conflict.files` | `precheck_commit()`（`git merge-tree`） | 模拟 cherry-pick 是否冲突及冲突文件；等价于真实 cherry-pick 的冲突结果 |
| `local_churn.lines` / `level` | `local_churn()` + `churn_level()` | 本地 `base` 相对共同祖先在涉及文件上的改动行数；`high` = 本地已大幅定制 |

**等级修正规则**（`cmd_advise`）：在原 `judge()` 结论上叠加——预计冲突 → 至少 `caution`；`local_churn=medium` → 至少 `caution`；`local_churn=high` → `review`；理由同步追加进 `reasons`。

**实测（本仓）**：118 条，耗时约 10s；`adopt=4 / caution=52 / review=62`，预计冲突 **98** 条——旧 `risk=shared` 只标出 13 条，可见"冲突预判"信息量远大于旧启发式，正是 AI 顾问的主要依据。

**技能**：`.trae/skills/upstream-sync/SKILL.md` 新增「AI 顾问模式（全流程托管）」章节（8 步流程 + 信号解读表 + 建议表模板）。

**自验**：`python dev_tools/upstream_sync.py advise --json --out <f>`（无网络依赖，exit=0，约 10s）→ 读取 `summary` 与 `commits[].conflict/local_churn`；`advise`（无 `--json`）打印可读总览。

### 13.11 Web 界面接入 AI 顾问（`/api/advise`）

**背景**：§13.10 的 `advise` 只在 CLI 可用，网页界面拿不到 `conflict` / `local_churn` 两个深度信号——界面的冲突徽章只能靠用户手动「冲突预检（已选）」，取舍建议也停留在 `judge()` 的旧启发式。

**做法**：把 `advise` 接到界面，**手动触发**（不随打开页面自动跑，避免每次进页面都等全量分析）。

- **后端**：抽出 `_decorate_commits()`（`list` / `advise` 共用补中文显示字段）；`get_commits()` 改为调用它；新增 `get_advise()`（子命令 `advise --json --out`、`_ADVISE_CACHE` 缓存、`timeout=1800`）；`do_POST` 路由集合与 `elif` 链各加 `"/api/advise"`。
- **前端**：工具栏第三行新增按钮 `#btnAdvise`（"AI 顾问(全量分析)"）与状态位 `#adviseStatus`；新增 `runAdvise()`——`adviseBusy` 守卫 + `setInterval` 每 500ms 刷新"已耗时 Ns" → `POST /api/advise {since}` → 成功后 `commits = data.commits`、以 `c.conflict` 重建 `pc`、`buildTypeChips(); buildModuleSelect(); render();`，**保留已勾选**（`selected` 不动），`#banner` 与日志给出冲突/三档计数与耗时；失败提示引导先点「拉取上游最新」。绑定 `$("btnAdvise").onclick = runAdvise;`。
- **复用**：列表渲染零新增——`pcBadge()`（冲突）与 `judgeBadge()`（已就地修正的 `level`/`judge`/`reasons`）直接消费 advise 结果。

**改动文件**：`dev_tools/upstream_sync_web.py`（后端 + 前端 `PAGE`）。

**验证**：① `python -m py_compile dev_tools/upstream_sync_web.py`；② **重启 web 服务**（`PAGE` 无热重载）后打开页面，点「AI 顾问(全量分析)」，观察耗时提示与列表冲突徽章/建议刷新；③ 直接 `POST /api/advise {"since":"2 months ago"}` 断言 `commits[].conflict` / `local_churn` 存在；④ 再点一次应**立即返回**（命中 `_ADVISE_CACHE`）。

**边界**：仅描述"接入与触发"，`advise` 本身的信号语义见 §13.10；不做顶部汇总条 / 分组视图 / 整组勾选。

### 13.12 自定义数据源（与任意 fork 比对）

**背景**：原先比对源写死为 `upstream/dev`（`runhey/OnmyojiAutoScript`）。用户想拿**另一个 fork 的提交**与本地比对合并，需要能在界面填「仓库地址 + 分支」。

**做法**：CLI 顶层加可选 `--remote-url` / `--remote-branch`（须在子命令之前），web 端在工具栏顶部加「数据源」行并全程透传。

- **CLI（`upstream_sync.py`）**：
  - 新增常量 `SOURCE_REMOTE = "syncsrc"`（自定义源专用 remote 名，避免覆盖 `upstream`）。
  - 新增 `remote_url_of(name)`（读现有 remote URL）、`ensure_source(remote, url)`（不存在则 `remote add`、与目标不符则 `remote set-url`，**只动 remote、不动其它 git config**）、`resolve_source(args)`（返回 `(remote, branch, ref)`；url 为空 → `upstream/dev`，否则 `syncsrc/<branch>`）。
  - `git_with_proxy()` **改名并增强为 `git_net(git_args, proxy=None)`**：额外注入 `GIT_TERMINAL_PROMPT=0`（私有库直接报错而非卡住），代理仍走 `GIT_CONFIG_KEY_*` 环境变量（不改 git config）。
  - `fetch` 改为 source-aware（对目标 remote/branch fetch，两次尝试均走 `git_net`）；新增 `branches --url U`（`git ls-remote --heads` + 代理回退 + 禁交互，`emit {"url","branches","default"}`）；`list` / `advise` / `apply` 三处的 ref 全部改由 `resolve_source(args)` 解析。
- **Web 后端（`upstream_sync_web.py`）**：新增 `source_args()`（留空 url 返回 `[]` → 向后兼容）、`_src_label()`（range 显示名）、`get_branches(url)`；`get_commits` / `get_advise` / `apply_hashes` 加可选参数并把 `src` 前置到 `run_sync` 参数；`_ADVISE_CACHE` 键改为 `(since, remote_url, remote_branch)`；`/api/commits` 读 query 的 `remote_url`/`remote_branch`；`do_POST` 路由集合与 `elif` 链各加 `/api/branches`。
- **Web 前端（`PAGE`）**：工具栏最前新增数据源行（`#repoUrl` 地址输入、`#repoBranch` 分支下拉、`#btnLoadBranches`、`#btnConnect`、`#srcStatus`）；新增 `srcUrl()`/`srcBranch()`/`sourceParams()`/`setSrcStatus()`/`loadBranches()`；`loadCommits`/`runAdvise`/`doApply` 改读 `sourceParams()` 并透传。

**改动文件**：`dev_tools/upstream_sync.py`、`dev_tools/upstream_sync_web.py`、`dev_tools/upstream_sync_doc.md`。

**验证**：① `py_compile` 两个 .py；② 向后兼容：`--since "2 months ago" list --json` 仍返回默认源且 `ref=upstream/dev`；③ 等价性：显式传 `--remote-url https://github.com/runhey/OnmyojiAutoScript.git --remote-branch dev` 结果应与默认一致；④ `branches --url <地址>` 能返回分支数组；⑤ **重启 web 服务**（`PAGE` 无热重载）后回归数据源行与 `/api/branches`。

**边界**：本阶段**只做自定义数据源**；「被我排除/跳过的提交」独立视图已在 §13.13 完成。

---

### 13.13 「已排除·跳过」独立视图（跳过 / 恢复 / 已并入）

**背景**：用户希望把**不想同步（跳过）**的提交从待同步列表里移走，且能随时**恢复**；同时能看到哪些提交其实**内容已并入本地**（`git cherry` 等价，hash 不同）。原先把这三类混在同一个列表里，容易误选、也看不清来源。

**做法**：新增持久化文件 + 三个 CLI 子命令 + 两个 HTTP 路由 + 界面 Tab 视图。

- **持久化**：`dev_tools/upstream_ignored.json`（`{"version":1,"items":[...]}`，**不入库**）。每条记 `hash / subject / date / module / type / source / ignored_at / reason`，便于提交失效后仍能显示它是什么。`load_ignored()` 容错（缺失/损坏 → `[]`）。`.gitignore` 在 `!dev_tools/*` **之后**追加该文件名。
- **CLI（`upstream_sync.py`）**：新增 `load_ignored` / `save_ignored` / `ignored_hashes` / `match_ignored`（**<8 位返回 `[]`**）/ `parse_hashes`；新增 `ignore` / `unignore` / `ignored` 子命令。`cmd_list` 拆出 `applied`（与 `--since` 窗口**求交**后的 `git cherry` 等价集）与 `ignored`（带 `present` 标记），`commits` 两者都剔除；`cmd_advise` 与 `cmd_apply` 也**剔除 ignored**（否则 `--deps` 回溯会静默 cherry-pick 被跳过的提交）。
- **Web 后端（`upstream_sync_web.py`）**：`get_commits()` 返回 `applied` / `ignored`（均过 `_decorate_commits()`）；新增 `do_ignore` / `do_unignore`（成功后**作废 `_ADVISE_CACHE`**）；`do_POST` 路由集合与 `elif` 链各加 `/api/ignore`、`/api/unignore`。
- **Web 前端（`PAGE`）**：`#banner` 上方加 `.tabs`（`#tabPend` / `#tabIgn` + 计数）；新增状态 `applied` / `ignored` / `view`；`render()` **先按 `view` 分派**（`ign` → `renderIgnored()`）；主列表每行加「跳过」按钮、工具栏加 `#btnSkipSel`「跳过所选」；新增 `setView()` / `updateTabCounts()` / `ignoredView()` / `doIgnore()` / `doUnignore()` / `renderIgnored()`；筛选行 / 操作行 / `#cpanel` / `footer` 加 `pend-only` 类，`body.view-ign` 时隐藏。跳过/恢复**就地更新**（不整页重载，保留勾选与预检状态）。

**改动文件**：`dev_tools/upstream_sync.py`、`dev_tools/upstream_sync_web.py`、`dev_tools/upstream_sync_doc.md`、`.gitignore`、`.trae/skills/upstream-sync/SKILL.md`。

**验证**：① `py_compile` 两个 .py；② CLI 闭环见 §11 步骤 2c（ignore → list 少 1 / ignored 多 1 → unignore → 7 位前缀报错）；③ `git check-ignore -v dev_tools/upstream_ignored.json` 命中白名单；④ **重启 web 服务**（`PAGE` 无热重载）后：Tab 切换正常、「跳过」与「跳过所选」生效、已排除页「恢复」生效、「已并入本地」默认折叠可展开、`POST /api/ignore` `/api/unignore` 返回 200 且刷新后状态正确、`GET /api/commits` 含 `applied`/`ignored`。

**边界与已规避项**：`applied` 与 `ignored` 可能重叠，界面以 `applied` 为准去重；`ignored` 中 hash 已不在当前上游窗口时标「哈希已不存在」（`present=false`），恢复仍允许（只是下次 `list` 不会出现）；本视图**不做折叠分组以外**的交互（无勾选、无 diff 面板）。

---

## 14. 提交规范（agent 方便理解优先）

> 约定：本项目**所有提交**的信息都要让其他 agent 一眼看懂"为什么改、改了什么、怎么验"。写得比给人看的更结构化。

格式 = Conventional Commits 头行 + `Why/What/Verify` 三段正文：

```
<type>(<scope>): <中文一句话摘要>

Why: <背景与要解决的问题，1~3 行>
What:
- <文件/模块>: <改动点>
- <文件/模块>: <改动点>
Verify: <验证方式与结果，如 py_compile / list --json / 冲突全链路 / 界面截图>
```

- `type`：`feat` / `fix` / `docs` / `refactor` / `chore` / `test`。
- `scope`：模块名（如 `dev_tools`）。
- 头行保留**中文摘要**（沿用仓库现有习惯，见 `git log`）。
- 正文三段缺一不可；**禁止**"update code""fix bug"等无信息量描述。
- 改动跨多文件时在 `What` **逐文件列出**；涉及契约变更（JSON 字段、HTTP 路由、CLI 参数）必须写明变化。
- 敏感文件（`dev_tools/baidu_translate.json` 等）**不得入库**。

示例：

```
feat(dev_tools): 上游同步工具新增取舍建议与彩色改动预览

Why: 面对大改动/框架级上游提交时无法判断是否采用；查看改动只有裸 diff，不直观。
What:
- dev_tools/upstream_sync.py: collect_commits 改用 --numstat；新增 size_of/framework_hit/judge；新增 show 子命令
- dev_tools/upstream_sync_web.py: 新增 /api/show 与 renderDiff 彩色渲染；建议徽章与筛选；统计计数
- dev_tools/upstream_sync_doc.md: 新增 §0 速查 / §13 增强记录 / §14 提交规范
Verify: py_compile 通过；list --json 字段齐全；冲突全链路 apply→resolve→abort 通过；界面回归截图通过
```