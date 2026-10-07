# upstream-sync 多源比对改造方案（设计与落地记录）

> **状态**：✅ 已实现并入库 · ✅ 已实跑（批次 9）· 已推送 `origin/czr`
>
> | 阶段 | 提交 | 说明 |
> |---|---|---|
> | 多源改造 | `5a118096` | 6 文件 `+805/-274`：配置 + 后端 + 前端 + 文档 + skill + 台账来源列 |
> | 首次实跑 | `44b22f09` | 批次 9：从 `xylolit-mu/self` 精筛 10 条落地（含 1 条自检 `0a2afa94`） |
> | 台账回写 | `384e02c0` | 台账 §1/§2/§3.1/§3.2/§4/§5 更新 |
>
> **本文用途**：给「下一个接手 agent」一份可直接执行的设计 + 落地对照 + 实跑结论。
> 操作手册见 [`upstream_sync_doc.md`](./upstream_sync_doc.md)（§13.15 多源比对）；
> 状态与批次进度见 [`upstream_sync_log.md`](./upstream_sync_log.md)（**开新对话先读它**）。
> 本文只记「为什么这么设计 + 实际做成了什么样 + 实跑发现了什么」，不重复命令细节。

---

## 1. Context（为什么改）

改造前 `upstream-sync` 只支持**单个**上游数据源：全局参数 `--remote-url` / `--remote-branch`，
默认走 `upstream/dev`。

需求：让本地 `czr` 分支**同时**与多个源的最近两个月提交比对，并挑出最适合 `czr` 的引入：
- `https://github.com/runhey/OnmyojiAutoScript.git` 的 `master`（另按用户选择一并保留 `dev`）
- `https://github.com/xylolit-mu/OnmyojiAutoScript.git` 的 `self`
- 以后可能继续加仓库/分支

预期结果：一条命令 / 一次网页点击即可拿到**跨源去重后**的候选清单（标注来源与取舍建议），
再按既有「批次化同步工作流」做语义核实 → 用户拍板 → `apply` → 回写台账。

已确认的三个决策：
1. 默认源清单**入库**为 `dev_tools/upstream_sources.json`；
2. 跨源重复提交**按 patch-id 合并**为一条并标注全部来源；
3. 默认源**保留** runhey 的 `dev`（共三个源：runhey/master、runhey/dev、xylolit-mu/self）。

---

## 2. 关键设计（含一处设计修正）

- **取源**：新增可重复的 `--source <url>#<branch>` 与 `--sources <json>`；`--remote-url/--remote-branch`
  保留为「单源」兼容写法。无参数时读默认配置，文件缺失回退内置 `upstream/dev`。
- **fetch 不写 `.git/config`**：逐源 `git fetch <url> +refs/heads/<branch>:refs/remotes/<slug>/<branch>`，
  `slug` 如 `runhey-master` / `xylolit-mu-self`。取代 `ensure_source()`/`ensure_upstream()`
  （它们会 `git remote add/set-url`）——项目硬约束是「不得修改 git config」。
  ref 放在 `refs/remotes/<slug>/<branch>`（而非 `refs/sync/`）：短名可解析、与既有
  `refs/remotes/upstream` / `syncsrc` 约定一致、不会混进 `git log --all`。
  fetch 失败仍走 `detect_local_proxy()` 代理重试；失败但本地已有该 ref 时告警并用缓存。
- **跨源去重（已修正）**：**不用 `git cherry`**。`git cherry` 是拿第一参数的全历史做等价比对且不返回
  配对关系，会把「窗口内提交在窗口外另有等价物」误判为重复而丢条。改为对窗口内候选自建
  `git patch-id --stable` → `patch_id → [提交]` 分组（每源一次），
  按源优先级取代表条目，产出 `source`（代表来源）与 `sources`（全部来源）。
- **`--deps` 不能吃合并列表**：`cmd_apply` 的 `reversed(all_commits[:ci])` 依赖「单 ref 线性史」。
  改为额外维护 `hash → 所属 ref` 与「每源有序列表」，回溯时用该提交所属源的列表。
  `DEP_CAP` / `MAX_DEP_ROUNDS` 不动。
- **`ignored` 的 patch-id 补漏**：`upstream_ignored.json` 原按 hash 键控，跨源 hash 不同会导致
  跳过失效。写入时增补可选字段 `patch_id`（仍是 `version:1`，旧记录兼容），过滤改为
  「hash 命中 **或** patch_id 命中」。
- **`applied` 组同样要跨源去重**：否则同一逻辑提交会在「已并入本地」里重复出现。

---

## 3. 落地对照（实际符号 / 行号 / 契约）

> 行号为改造完成时（`5a118096`）的快照，后续编辑可能漂移；**以符号名为准**。

### 3.1 入库配置 `dev_tools/upstream_sources.json`（新增）

```json
{ "version": 1, "since": "2 months ago", "sources": [
  { "url": "https://github.com/runhey/OnmyojiAutoScript.git",    "branch": "master" },
  { "url": "https://github.com/runhey/OnmyojiAutoScript.git",    "branch": "dev"    },
  { "url": "https://github.com/xylolit-mu/OnmyojiAutoScript.git","branch": "self"   }
] }
```
数组顺序 = 优先级。**入库**（未命中 `.gitignore`）。

### 3.2 后端 `dev_tools/upstream_sync.py`

| 计划名 | **实际名** | 位置 | 作用 |
|---|---|---|---|
| （常量） | `SOURCES_FILE` | `L44` | 源清单路径 `dev_tools/upstream_sources.json` |
| （常量） | `DEFAULT_SINCE` | `L45` | `"2 months ago"` |
| 内置回退源 | `BUILTIN_SOURCES` | `L47` | 配置文件缺失时的兜底（单源 `upstream/dev`） |
| `source_slug()` | `sanitize_slug()` + `source_slug()` | `L436` / `L449` | slug 消毒与 `<owner>-<分支>` 生成 |
| `parse_source_spec()` | `parse_source_spec()` | `L459` | 解析 `URL#分支` |
| `load_source_specs()` | `load_source_specs()` | `L518` | 读配置文件 |
| `resolve_sources()` | `resolve_sources()` | `L544` | 统一出口，返回 `[(url, branch, slug, ref, label)]` |
| `fetch_sources()` | `fetch_one()` | `L566` | **逐源** fetch（调用方遍历；代理回退内置） |
| `patch_ids()` | `patch_id_map()` | `L572` | `{full_hash: patch_id}`（`--stable`） |
| `collect_all()` | `collect_all()` | `L610` | 合并 + 按 patch-id 去重 + 标注 `source`/`sources`/`patch_id`/`ref` |
| — | `ignored_ids()` | `L286` | 返回 `(hash 集合, patch_id 集合)` |
| — | `ignored_with_present()` | `L602` | 给已跳过项标 `present`（hash 或 patch_id 是否仍在窗口内） |

**契约变更（提交信息必须写明）**
- CLI：新增 `--source`（可重复）、`--sources`；`--remote-url`/`--remote-branch` 保留兼容
- JSON：`commits[]` 增 `source` / `sources` / `patch_id`；顶层增 `sources: []`；`range` 由单源标签改为多源拼接
- 持久化：`upstream_ignored.json` 增可选 `patch_id`（`version:1` 不变，旧记录兼容）
- 新增入库文件：`dev_tools/upstream_sources.json`

### 3.3 服务/前端 `dev_tools/upstream_sync_web.py`

| 计划 | 实际 | 位置 |
|---|---|---|
| 多行源列表 UI | `#srcList`（CSS `.srcList`） | `L560` / `L413` |
| 来源标签 | `srcTag(c)` | `L816` |
| `source_args()` → `sources_args(sources)` | `sources_args()` | `L1505` |
| `_src_label()` → 多源标签 | `_src_label()` | `L1548` |
| 新增路由 | `GET /api/sources` | `L1837` |
| 新增路由 | `POST /api/sources`（显式「保存为默认源」才写盘） | `L1879` |
| 各接口 `sources` 参数 | `/api/commits` `L1612`、`/api/advise` `L1661`、`/api/apply` `L1703`、`/api/precheck` `L1739`；`/api/ignore`、`/api/unignore` 经 `L1857` 路由表 | — |

缓存 key 由 `(since, remote_url, remote_branch)` 改为 `(since, 源标签元组)`。

### 3.4 文档与 skill

- `dev_tools/upstream_sync_doc.md`：**新增 §13.15 多源比对**（`L729`），并同步 §0 速查 / §1 / §3 / §4 / §5.x / §6 / §8 / §9 / §11 / §12
- `.trae/skills/upstream-sync/SKILL.md`：定位改多源；标准流程加「多源 fetch + 跨源去重」；AI 顾问流程加来源标注与「跨源同改动只评一次」；必守约束加「源清单文件 / refs 命名空间 / 不写 `.git/config`」
- `dev_tools/upstream_sync_log.md`：§1 表加「来源」列，历史批次回填 `runhey/dev`

---

## 4. 与原方案的偏差（实测修正）

| 原方案写法 | 实际落地 | 原因 |
|---|---|---|
| `fetch_sources()` / `patch_ids()` | `fetch_one()` / `patch_id_map()` | 单个职责更小、便于调用方在遍历时统一处理代理与缓存回退 |
| `--since` 默认取配置文件 `since` | 保留 `DEFAULT_SINCE`，配置文件同名字段并存 | 兼容既有调用方式，避免「配置文件缺失即无默认值」 |
| 前端改 `PAGE` 后需重启服务 | 已确认：Windows 下 Python `HTTPServer` 会**双绑定 8765** | 重启前必须 `netstat` / `Stop-Process` 清旧实例，否则改前端口测不到新代码 |

另有一处**契约层自检**（批次 9 实跑发现，`0a2afa94`）：
上游 `407544fe` 在 `tasks/GlobalGame/ui/click.json` 夹带 `"profile": "Default"`，
而本地 click.json 契约固定为 `{itemName, roiFront, roiBack, description}`（`RuleClick.__init__`
只接受 `roi_front/roi_back/name`）→ **保留 ROI 取值、丢弃 `profile`**。
> 通用教训：上游 fork 常夹带本地没有的 JSON 字段/键，**契约以本地为准**，落地时剥离。

---

## 5. 验证（已实际执行）

1. ✅ `toolkit\python.exe -m py_compile dev_tools/upstream_sync.py dev_tools/upstream_sync_web.py`
2. ✅ CLI 默认 `fetch` 三源成功（`refs/remotes/runhey-master` / `runhey-dev` / `xylolit-mu-self` 就位）
3. ✅ `list --json --out <tmp>`：`sources` / `commits[].source` / `commits[].sources` 存在；
   跨源等价提交被合并为一条且 `sources` 标齐；**无丢条**（合并后条数 ≥ 任一单源条数）
4. ✅ 单源兼容：`--remote-url` 结果与改造前一致
5. ✅ HTTP：`/api/sources` 读写、`/api/commits`、`/api/advise` 多源 body 返回 200 且二次命中缓存
6. ✅ 浏览器回归：源列表增删、连接并比对、列表来源标签、跳过/恢复闭环
7. ✅ 台账/文档无冲突标记，`git status --short` 干净

---

## 6. 批次 9 实跑结论（本轮真正的交付）

### 6.1 数字

| 指标 | 值 |
|---|---|
| `advise` 合并后待同步（剔除台账 §2/§3 后） | **209** 条新候选 |
| 其中来源分布 | **全部** `xylolit-mu/self`（runhey/master + runhey/dev 已被批次 0~8 判定完毕） |
| 精筛落地 | **10** 条 |
| 新 `ignore` | 8 条（累计 90） |
| 本地 merge commit | `44b22f09`（父 `5a118096` + `0a2afa94`） |

### 6.2 落地清单（上游 hash → 本地 hash）

| 上游 | 本地 | 模块 | 摘要 |
|---|---|---|---|
| `a938c649` | `1b9c97e7` | Sougenbi | 业原火 OCR 识别框 y 坐标下移 |
| `7aee49c4` | `4cef0af9` | BondlingFairyland | 契灵盘子识别范围扩大 |
| `407544fe` | `6661c82b` | GlobalGame | 奖励页关闭点击范围（另有自检 `0a2afa94` 剥离 `profile`） |
| `1cda0166` | `dbb24038` | WantedQuests | 秘闻结算后点空白返回挑战界面 |
| `075f75bb` | `e5d61cda` | AbyssShadows | 切换目标前优先补足同类数量 |
| `3a2b74a3` | `e00d55fe` | Dokan | 快速退出返回道馆后结束连战（含 3 条单测） |
| `e88f4e2f` | `77b84efe` | Chess | 次要羁绊只保留计数第二多一项 |
| `e84779fb` | `fdf26b96` | Chess | 按住拖动拟人化（时长区间 + 随机压力） |
| `40e4aa6f` | `f58172ba` | base_task | 勾协弹窗优先清理并复核（**热路径**） |
| `27d7e0ab` | `a44eaf4e` | Device | minitouch 连接失效先本地重建（**设备层**） |

验证：12 个改动 `.py` 全部 `py_compile` 通过；`import tasks.Dokan/WantedQuests/AbyssShadows/Chess
.script_task`、`tasks.base_task` 通过；`unittest tasks.Dokan.test_battle_exit` 3 条 OK；全仓无冲突标记。

### 6.3 关键结论（对后续定批有决定性影响）

1. **`xylolit-mu/self` 与本地 `czr` 同源度极高**：本地 `czr` 源自 `mine`，而 self 亦是
   **mine 系派生 fork**（自述同步 Azur/mine）。209 条候选里真正可落地**仅 10 条**（约 5%），
   其余为语义重复或框架分叉。
   → **定批必须做语义核实**（`show` 真实 diff + 本地 grep 比对），**不能只信 `advise`**。
2. **「净零对」识别法**（可复用）：同一源内出现「`X` 紧跟 `Revert X`」时，只需判断
   **本地当前是否等于 revert 后的终态**；若是，则整对一并 `ignore`，不必合并。
   本批识别出 4 对：`950145ed`/`cd36bd16`、`258e8b8f`/`5a5d3dc4`、`1d67a992`/`3b161aba`，
   外加 1 条空提交 `a9fa1e26`。
3. **`applied` 判据依旧不可靠**：本批再次验证——凡本地做过冲突取舍或自检补正，
   patch-id 就与上游不同，已合入的会被**重复列为待同步**。**以台账为准**。
4. **余量必须按簇立项**：剩余 ~199 条高度集中于**大特性/框架级**簇（全仓级重构、
   ActivityShikigami 活动战斗、Chess 状态机、导航与图像框架），`advise` 多为 `conflict=conflict`，
   不适合小批次 cherry-pick。已归档到台账 **§3.2**。

### 6.4 待实机验证（批次 9）

1. 勾协弹窗能被 `while self._burst()` 循环清理且不卡死（`screenshot()` 热路径）
2. 道馆连战主动退出后能正确收尾
3. Chess 拖拽/选符咒手感与稳定性
4. 多开时 minitouch 不再频繁重连 ADB

---

## 7. 给接手 agent 的可复用要点

1. **先读台账** `dev_tools/upstream_sync_log.md`（§1 批次总览 → §3/§3.1/§3.2 → §4），再动手。
2. **advise 结果不要整段读进上下文**（200+ 条会炸）：写 `--out <tmp>` 文件，再用脚本
   按「台账 §2/§3 的 hash 集」过滤 + 按 `level`/`conflict`/`local_churn`/`changed` 分类，
   **只取候选 5~10 条的字段**。
3. **定批口径**：优先「`conflict=ok` + 单模块 + `local_churn=low` + 体量小」。
4. **逐条 `show` 语义核实**，三类判定写进台账 §3：**已覆盖 / 不适用 / 可落地**。
   「已覆盖」的高频证据：本地该文件该行**已是上游补丁的目标值**，或本地**已存在同名符号/缓存变量**。
5. 执行 `apply --manifest --pause`（要求工作区**已跟踪文件**干净；未跟踪文件不影响）
   → 冲突循环 `conflicts` → `conflict-detail` → `resolve` / `abort`
   → `py_compile` + `import` + 单测 + 全仓无冲突标记
   → `git switch czr` → `merge --no-ff -F <文件>` → 删 `sync/*` → 代理推 `origin/czr` → 回写台账。
6. **判定项随手 `ignore --hashes …`**，避免每轮重现。
7. 通用参数与数据源参数**必须放在子命令之前**；`list/advise --json` 走 `--out` 文件（唯一不走 `emit` 的例外）。

---

## 8. 遗留 / 未完成

- **余量 ~199 条**（台账 §3.2）：须按簇立项，不适合小批次同步。
- **既有需立项（大特性）**：Costume 皮肤/多帧时序；ActivityShikigami 活动战斗更新；
  BudokaiTournament 新任务；防风控加固；每周琐事惠比寿摸鱼行动。
- **待决策**：掩码匹配 / 零方差拦截 / nan-inf 清洗是否以**服务端**方式补进
  `module/image/runtime.py`（思路源自 `51582666`；同源实现 `8753481b`）。
- **延后**：`582eae75`（删除本地 `tests/`，需先评估与本地测试体系的关系）。
