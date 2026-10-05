# 上游提交选择性同步工具 —— AI 交接文档

> 面向对象：后续接手优化此功能的 AI agent / 开发者。
> 适用版本：commit `935cf8e4`（`mine` 分支）。文中行号是**近似值**，代码改动后请以符号名（函数名/常量名）为准检索。
> 只描述"是什么、在哪、怎么改、怎么验"，不重复实现细节。

---

## 1. 一句话概括

把上游 `runhey/OnmyojiAutoScript` 的 `dev` 分支上、本地 `mine` 分支还没有的提交列出来，
让用户**按模块勾选**，新建 `sync/*` 分支逐条 `cherry-pick`；能**预判冲突**、冲突时**逐文件选择保留本地或采用上游**；提交标题带**中英对照**（离线词表 + 可选联网翻译）。

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
upstream_sync.py ──► git（upstream 远程 / mine 基线 / cherry-pick）
   │
   └─► stdout 里输出一行  @@SYNC@@{json}
          ▲
Handler 用 parse_sync_json() 取"最后一行 @@SYNC@@ 之后的 JSON"
```

关键设计：**所有需要被界面理解的结果，后端都必须用 `emit(obj)` 打印成 `@@SYNC@@{json}` 单行**，其余 stdout/stderr 原样透传给界面日志区。

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
| `DEFAULT_BASE` | `mine` | 本地基线分支 |
| `DEFAULT_SINCE` | `2 months ago` | 默认只对比最近两个月 |
| `DEFAULT_MANIFEST` | `dev_tools/upstream_manifest.md` | 清单默认输出 |

CLI：`python dev_tools/upstream_sync.py [--base mine] [--since "<git 时间表达式>"] <子命令>`

### 5.3 子命令

| 子命令 | 参数 | 作用 | `emit` 的 JSON |
|---|---|---|---|
| `fetch` | — | 建 `upstream` remote 并 `git fetch upstream dev` | 无（纯文本输出） |
| `list` | `--out PATH`、`--json` | 生成清单；`--json` 输出数据供界面消费 | 见下 |
| `apply` | `--manifest`、`--branch`、`--deps`、`--pause` | 建 `sync/*` 分支并逐条 cherry-pick | `{"status":"conflict"\|"done","branch","commit","files":[...]}` |
| `conflicts` | — | 查看当前未解决冲突 | `{"status":"conflict"\|"idle","branch","commit","files":[...]}` |
| `resolve` | `--choices`、`--choices-file` | 按选择处理冲突文件并继续 | `{"status":"done"\|"conflict",...}` |
| `abort` | — | 中止 cherry-pick、回 `mine`、删 sync 分支 | `{"status":"aborted","branch"}` |
| `conflict-detail` | `--file PATH` | 单文件三阶段差异 + 中文原因分析 | 见 §5.4 |

`list --json` 输出（**界面依赖此结构**）：

```json
{
  "base": "mine",
  "ref": "upstream/dev",
  "since": "2 months ago",
  "commits": [
    {
      "hash": "<40位>", "date": "2026-09-19", "author": "...", "subject": "fix(xxx): ...",
      "type": "fix", "module": "GeneralBattle", "risk": "isolated|multi|shared",
      "files": ["tasks/Component/GeneralBattle/battle_wait.py"]
    }
  ]
}
```

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
| `collect_commits(base, ref, since, exclude_applied)` | L152 | `git log --no-merges --reverse --name-only base..ref`，产出含 `files` 的提交列表 |
| `already_applied` | L142 | `git cherry` 按 patch-id 过滤"内容已在本地"的提交 |
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
        └─ abort                        → 回 mine + 删分支
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
| GET | `/api/commits?since=&refresh=0\|1` | — | `{"commits":[...],"range":"runhey/OnmyojiAutoScript · upstream/dev → mine（自 … 起）"}` 或 `{"error":...}` |
| POST | `/api/precheck` | `{"hashes":[...]}` | `{"results":{hash:{"status":"ok"\|"conflict"\|"error","files":[...]}}}` |
| POST | `/api/apply` | `{"hashes":[...],"branch":"..."}` | `{"code","output","result":<apply JSON>}` |
| POST | `/api/conflicts` | `{}` | `run_sync_json` 包装（`{"code","output","result"}`） |
| POST | `/api/conflict-detail` | `{"file":"..."}` | 同上 |
| POST | `/api/resolve` | `{"choices":{"<path>":"ours"\|"theirs"}}` | 同上 |
| POST | `/api/abort` | `{}` | 同上 |
| POST | `/api/translate` | `{"texts":["...","..."]}` | `{"translations":{"<原文>":"<中文>"},"provider":"百度"\|"有道"}` |

`/api/commits` 会在后端提交对象上**补充** `head_zh`、`desc`、`subject_zh`、`module_zh` 四个字段（界面直接消费）。

预检实现（`precheck()`，web 约 L1133）：对每个 hash 执行

```bash
git merge-tree --write-tree --name-only --merge-base=<hash>^ mine <hash>
```

- 返回码 `0` → `ok`；`1` → `conflict`；其他 → `error`。
- 冲突文件解析见 `_merge_tree_files()`：输出**第 1 行是 tree OID**，其后到**第一个空行**之间才是冲突文件名列表。

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

**布局**：`header`（标题 + `#rangeSub` 对比范围 + `#stats`）→ `toolbar`（筛选/预检）→ `#banner` → `#cpanel`（冲突面板）→ `#list`（提交列表）→ `footer`（分支名 + `#btnApply`）→ `#log`。

**关键 DOM id**：`since` `btnRefresh` `btnFetch` `q` `typeChips` `risk` `module` `orig` `online` `trStatus` `btnSelAll` `btnClear` `btnPrecheck` `selCount` `banner` `cpanel` `list` `branch` `btnApply` `log` `rangeSub` `stats`。

**关键 JS 状态**：

| 变量 | 含义 |
|---|---|
| `commits` | 后端返回的提交数组（含 `files`、`*_zh`） |
| `selected` | 已勾选 hash 的 `Set` |
| `chosenTypes` / `collapsed` | 类型筛选、模块折叠 |
| `pc` | 预检结果：`hash -> {status, files}` |
| `showOriginal` / `onlineTr` | 显示英文原文 / 联网翻译开关 |
| `trCache` / `trFail` | 联网译文缓存 / 失败集合 |
| `conflict` | 当前冲突上下文 `{commit,subject,branch,files,choices,details}` |

**关键函数**：`filtered()`（筛选 **+ 按 `date` 倒序排序**）、`render()`（按模块分组渲染，每条提交下方带可展开的"更新文件 N 个"清单，冲突文件标红并自动展开）、`subjectText()`（联网译文 > 离线译文 > 原文）、`pcBadge()` / `pcState()` / `pcFiles()`、`runPrecheck()`、`doApply()`、`showConflict()` / `renderConflict()` / `doResolve()` / `doAbort()`、`loadCommits()`、`translateMissing()`。

**排序**：`filtered()` 末尾 `.sort((a,b) => b.date.localeCompare(a.date) || b.hash.localeCompare(a.hash))` —— 模块**内**按时间倒序；模块之间的顺序仍是**提交数量降序**（`render()` 中的 `names.sort`）。若要"整页时间轴"，需同时改这两处。

---

## 9. 改哪里（扩展索引）

| 想改的东西 | 位置 |
|---|---|
| 汉化词表 / 术语 | web `TYPE_ZH` / `MODULE_ZH` / `WORD_ZH`（L37–L107） |
| 高风险文件判定 | backend `SHARED_PREFIXES` / `SHARED_FILES`（L58–L63）、`risk_of()` |
| 默认时间范围 | backend `DEFAULT_SINCE`（L35）、web `DEFAULT_SINCE`（L30） |
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

---

## 11. 验证方法（改完必做）

```bash
# 1) 语法
python -m py_compile dev_tools/upstream_sync.py dev_tools/upstream_sync_web.py

# 2) 后端数据面（应含 commits[].files 与 base/ref/since）
python dev_tools/upstream_sync.py list --json | more
```

```powershell
# 3) HTTP 面（服务已启动时）
$j = (Invoke-WebRequest "http://127.0.0.1:8765/api/commits?since=2%20months%20ago&refresh=0" -UseBasicParsing).Content | ConvertFrom-Json
$j.range; $j.commits.Count; $j.commits[0].files

# 4) 预检（已知用例：0e711238 会与 mine 冲突）
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
   ① 副标题显示 `upstream/dev → mine`；
   ② 每条提交下有"▸ 更新文件 N 个"可展开；
   ③ 搜索 `0e711238` → 勾选 → "冲突预检" → 出现红色徽章 `⛔ 冲突 1 文件`，文件清单自动展开且路径标红。

---

## 12. 术语表

| 词 | 含义 |
|---|---|
| `mine` | 本地定制基线分支（默认对比基准） |
| `upstream/dev` | 上游官方开发分支（对比目标） |
| `sync/*` | 每次同步新建的临时分支，验证后自行合并回 `mine` |
| `risk=shared` | 触及共享基础设施文件（i18n/config 等），冲突概率高 |
| `isolated` / `multi` | 只动一个模块 / 跨多个模块 |
| `ours` / `theirs` | 冲突时"保留本地" / "采用上游" |