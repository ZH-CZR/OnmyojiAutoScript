# upstream-sync 网页端接入「AI 顾问」（advise）

## Context（为什么做）

网页工具 `dev_tools/upstream_sync_web.py` 的 `/api/commits` 只调用 `upstream_sync.py list --json`（[L1142-1173](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L1142-L1173)），因此界面上拿不到 `advise` 独有的两个决策信号：

- **冲突预判** `conflict.status` / `conflict.files`（逐条 `git merge-tree` 模拟 cherry-pick）
- **本地定制度** `local_churn`（low/medium/high）

同时 `level/judge/reasons` 是**未经这两项修正**的粗判。本次实测 117 条待同步中 **98 条预判冲突、55 条定制度 high**，这两个信号正是"该不该合"的关键依据。

目标：网页端新增 `/api/advise` 路由 + 「AI 顾问」按钮**手动触发**，把顾问结果呈现在现有列表与建议徽章上。

**范围边界（用户已确认，不做）**：顶部汇总条、建议表分组视图、整组勾选。

## 改动清单

### 1. 后端 `dev_tools/upstream_sync_web.py`

- 抽公共函数 `_decorate_commits(commits)`：把 [L1159-1164](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L1159-L1164) 的中文补充（`head_zh` / `desc` / `subject_zh` / `module_zh`）抽出来，供 `get_commits` 与新函数复用。
- 新增 `get_advise(since, force=False)`（接在 `get_commits` 之后，约 L1174），**与 `get_commits` 同构**：
  - `tempfile.mkstemp(suffix=".json")` → `run_sync(["--since", since, "advise", "--json", "--out", tmp], timeout=1800)`
  - 读 tmp → `_decorate_commits` → 返回 `{"commits": [...], "range": ...}`；`finally` 删临时文件
  - **必须走 `--out` 文件**：`advise --json` 写 stdout / `--out`，**不打** `@@SYNC@@`，`parse_sync_json()`（[L362-370](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L362-L370)）解析不到
  - 缓存：模块级 `_ADVISE_CACHE = {"since": None, "data": None}`，命中同 `since` 直接返回；`force` 或 `/api/commits?refresh=1` 时失效。理由：117 条串行 merge-tree 较慢，重复点击应即时
  - 单独捕获 `subprocess.TimeoutExpired` 返回 `{"error": ...}`（否则被 `do_POST` 兜底包成 500）
- 路由：`do_POST` 的 `routes` 集合（[L1292-1294](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L1292-L1294)）加 `"/api/advise"`；elif 链（[L1301-1320](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L1301-L1320)）加一支调用 `get_advise(...)`

### 2. 前端（`PAGE` 内嵌，[L372-569](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L372-L569)）

- 工具栏加 `<button id="btnAdvise">AI 顾问</button>` + `<span id="adviseStatus">`（约 L549-554 区域）
- JS 新增 `runAdvise()`（放 `runPrecheck` 附近，约 L940）：
  - `adviseBusy` 守卫防重复点击；`setInterval` 每 500ms 在 `adviseStatus` 显示**已耗时**；`setLog("AI 顾问分析中…")`
  - `POST /api/advise {since}` 后 `await` 即可——`ThreadingHTTPServer`（[L1332](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L1332)）不阻塞其它请求，现有代码**无**轮询/日志流机制可复用
  - 成功后：`commits = data.commits` → 重建冲突映射 `pc[c.hash] = c.conflict` → `buildTypeChips(); buildModuleSelect(); render();`，**保留已勾选 `selected`**；状态栏显示条数与耗时
  - 失败/`data.error` → 提示原因（含"请先点『拉取上游最新』"）
- 绑定 `$("btnAdvise").onclick = runAdvise;`（约 L1107）

### 3. 展示（复用现有渲染，几乎零新增）

- **冲突**：advise 数据填入 `pc` 映射后，现有 `pcBadge()`（[L638-648](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L638-L648)）与冲突文件清单（L771-789）自动生效，无需新写渲染
- **本地定制度**：`advise` 已把定制度理由并入 `c.reasons`（`upstream_sync.py` L543-552），现有 `judgeBadge()` 悬停提示（[L650-657](file:///d:/codespace/oasCode/OnmyojiAutoScript/dev_tools/upstream_sync_web.py#L650-L657)）即可看到；`level/judge` 也随之被修正

## 涉及文件

- `dev_tools/upstream_sync_web.py`：主要改动（后端 + PAGE）
- `dev_tools/upstream_sync.py`：只读复用，不改
- `dev_tools/upstream_sync_doc.md`：补一节说明新增路由与触发方式（按 §14 规范提交）

## 验证

1. `python -m py_compile dev_tools\upstream_sync.py dev_tools\upstream_sync_web.py`
2. 基线：`python dev_tools\upstream_sync.py --since "2 months ago" advise --json --out %TEMP%\adv.json`，确认含 `conflict` / `local_churn` / 修正后的 `level`
3. **重启** `upstream_sync_web.py`（PAGE 是模块级常量，无热重载），打开页面：首屏仍走 `/api/commits`（快速）；点「AI 顾问」观察耗时提示；核对冲突徽章/冲突文件与建议徽章与 CLI 输出一致；再点一次应即时（缓存命中）
4. 回归：`/api/commits`、冲突预检（已选）、查看改动、执行同步 均正常

## 风险点

- 重复点击/并发：前端 `adviseBusy` + 服务端缓存双保险
- 超时：串行 merge-tree，显式 `timeout=1800` 并单独捕获异常
- 临时文件：`finally` 清理
- CLI 侧并行 `precheck_commit` 属更大改动，本次不做，用缓存替代