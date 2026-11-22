# 立项书：上游功能差距补齐（2026-11）

## 1. 基本信息

| 项 | 内容 |
| --- | --- |
| 项目名称 | 上游功能差距补齐 |
| 立项日期 | 2026-11-18 |
| 本地基准 | `czr` @ `76757c8d`（2026-11-22 全量对比基线；2026-11-21 增量同步前为 `3a0237c8`） |
| 状态 | 进行中：P0 三项中突破券、悬赏已合入，武道大会待活动实机；M2 代码完成待实机；M3 部分完成；M1/M4 未开始；M5 按复审结论收缩；P3 两条（keep-alive、OrochiMoans 清理）已合入。全量对比（2026-11-22）：已同步 176 / 部分实现 261 / 完全缺失 46 |
| 关联文档 | [对比报告](upstream_feature_gap_20261118.md) · [HTML 版](upstream_feature_gap_20261118.html) · [全量对比 2026-11-22](upstream-full-compare-20261122/upstream-full-compare-20261122.md)（[HTML](upstream-full-compare-20261122/upstream-full-compare-20261122.html)） · [任务清单](backlog.md) · [增量同步 2026-11-21](upstream-sync-20261121/upstream-sync-20261121.md)（[HTML](upstream-sync-20261121/upstream-sync-20261121.html)） |
| 关联台账 | [upstream_sync_log.md](../../upstream_sync_log.md) |
| 对比数据源 | `dev_tools/upstream_sources.json` 中的 5 个源 |

## 2. 背景

2026-11-18 对 5 个上游源（nearaura/master、nearaura/dev、kongdr418/mine、lgg686/self、pinkpig-Peppa/master）做了全量比对：

- 跨源去重候选提交 385 条，经同步台账过滤后**真实待决策 242 条**（其中框架类 68 条）。
- 本地 `ConfigModel` 注册任务 61 项，少于 lgg686 的 65 项，差集集中在 6 类新功能。
- 本地独有能力（`module/flow`、超鬼王祸主降临/协战、Chess 本地改造、RichMan 采购整合）没有任何上游可以替代，因此**不做整体换库**。

比对细节与证据见[对比报告](upstream_feature_gap_20261118.md)。

## 3. 目标（可验收）

1. 新增可自动化玩法：协同对弈 `DraftDuel`、LBS 鬼王、狭间幻境 `IbukiArena`、青蛙瓷器挑战赛 `FrogChallenge`。
2. 新增起号链路：剧情 → 借用式神 → 探索推进 → 经验妖怪，最终账号达到 15 级。
3. 补齐现有任务缺口：鼬金币商店礼盒（RichMan）、武道大会首领战阶段。
4. 消解高优先级稳定性问题：MetaDemon / FrogBoss / WantedQuests / Chess / GameUi 的 fix 类提交。
5. 框架类能力按需评估：`RuleFrame`、`/tool/doctor`、看门狗 + Apprise、OCR 引擎升级。

本地注册任务数已从立项时的 61 提升到 **67**，数量目标已达成；剩余工作转为「验证 + 补缺 + 稳定性修复」。

## 4. 范围

**做：**

- 按 lgg686 / kongdr 逐条 cherry-pick 或手工移植新任务，适配本地 `base_task` 与 `team_flow`。
- 为每个新任务补 `tests/test_*.py` 回归用例（参照现有 `test_upstream_batch45_fixes.py` 风格）。
- 在 `module/config/config_model.py` 注册新任务，并在 `assets/i18n/zh-CN.json` 补中文名。
- 更新同步台账，记录每个来源提交与本地的对应关系。

**不做：**

- 不切换主干到任何上游分支。
- 不直接 cherry-pick 引擎/依赖级提交：`50dec6ce`、`56529f78`、`26e67b73`（paddleocr / apprise 等），需单独评估。
- 不重构本地 `module/flow`、`team_flow`、`Chess` 既有实现。
- 不动 `dev_tools/baidu_translate.json`（含明文密钥）。

## 5. 里程碑

| 阶段 | 内容 | 交付物 | 验收 | 状态（2026-11-21 复核） |
| --- | --- | --- | --- | --- |
| M1 | 起号套件 4 任务 | `tasks/AutoStory`、`tasks/ExplorationFight`、`tasks/BorrowShikigami`、`tasks/CustomTask` | 配置可加载；15 级链路可跑通 | 未开始。复审结论：A2 改为并入现有 `Exploration`；A4 不采纳；A1/A3 需新账号才能验收 |
| M2 | 活动任务三件套 | `tasks/LBS`、`tasks/IbukiArena`、`tasks/FrogChallenge` | 各自可独立调度；有回归用例 | 代码完成、离线回归通过；活动未开放，**待实机验证** |
| M3 | 现有任务补齐 | RichMan 增加 `ItachiCoinShop`；武道大会增加首领战阶段 | 单项开关可验证 | B1 完成待实机；B2 代码完成（`d541ff7a`，`staging/20261120-mt-boss` 待实机） |
| M4 | 协同对弈 `DraftDuel` | `tasks/DraftDuel` + 复用 `team_flow` 双端协同 | 双实例可完成一局并按配置退出 | 未开始。复审结论：单独立项，不混入本批 |
| M5 | 稳定性批次 + 框架评估 | 按模块分组的 fix 批次；框架评估结论 | 每批独立提交、可回滚 | 部分完成：D3 悬赏已合入（`78d95b2a`）；D6 突破券 ROI 已合入（`33cc7e06`）；D2/D4 多数已落地 |

## 6. 验收标准

- 新任务在标注器与配置界面可见，中文名完整，默认关闭。
- 每个新任务至少一条离线回归用例；涉及识别的补素材来源说明。
- 不引入未在 `requirements-in.txt` 中声明的依赖。
- 同步台账新增记录，写明「上游 hash → 本地 hash / 手工改造说明」。
- 提交信息遵循仓库规范（Conventional Commits 中文摘要 + Why / What / Verify）。

## 7. 风险与约束

| 风险 | 说明 | 应对 |
| --- | --- | --- |
| 上游实现依赖其自有协同框架 | DraftDuel 用 kongdr 自有心跳调度 | 适配本地 MQTT `team_flow`，不引入第二套协同 |
| 双端时序与识别阈值 | 协同类任务对时序敏感 | 先做单端联调，再开双端；补时序日志 |
| 引擎级提交不可移植 | paddleocr 3.7 与本地 ppocr-onnx 技术栈不同 | 隔离评估，不进入任务移植批次 |
| 台账 `applied` 不可靠 | patch-id 变化会被误列为待同步 | 一律以台账为准 |
| 上游无回归用例 | lgg686/kongdr 多数提交无测试 | 本地移植时补最小用例 |

## 8. 决策记录

| 日期 | 决策 | 理由 |
| --- | --- | --- |
| 2026-11-18 | 以本地为主干，定向移植；不换库 | 本地独有 flow / 超鬼王 / 棋局改造不可替代 |
| 2026-11-18 | 优先级按「功能覆盖优先」排序 | 用户明确口径 |
| 2026-11-18 | `pinkpig-Peppa/master` 加入参考源 | 用户要求；与 nearaura 同源，暂未发现独有任务 |
| 2026-11-20 | 复审：注册任务数已达 67，数量目标完成 | 以 `ConfigModel` 实测为准，立项时的 61 已过时 |
| 2026-11-20 | 复审：B2 改判为小补丁 | `MartialTournament` 已具备 boss 搜索、单体/群体识别、战斗与一键御魂，仅缺 `boss_limit` 阶段与 `run_sequence` 的 `boss` 项 |
| 2026-11-20 | 复审：A2 不新建任务 | 本地 `Exploration` 已覆盖章节单选、战斗次数、自动候补、up 类型，仅缺章节区间与稀有度筛选，补字段即可 |
| 2026-11-20 | 复审：A4 不采纳 | 与本地 `module/flow` + `CustomFlow` 重复，且本地支持编排与生成可调度任务，能力更强 |
| 2026-11-20 | 复审：E1/E3/E4/E5 不采纳或搁置 | RuleFrame 高耦合；本地已有 onepush 与失败三次退出机制；paddleocr 与 `ppocr-onnx` 技术栈冲突；绘卷属查询工具、优先级最低 |
| 2026-11-20 | 新增预演批次流程 | 改动先进 `staging/YYYYMMDD-主题` 分支，台账 `dev_tools/staging_pending.md`，测试与确认后才合并回 `czr` |
| 2026-11-20 | P0-3 悬赏 13 条只移植 3 条语义 | 10 条在 czr 已有等价实现或被更宽的本地配置覆盖；`d296406e` 等资产重构会删除本地仍在用的 `I_TRACE_TRUE` 资产，判不适用 |
| 2026-11-20 | P0-2 突破券 ROI 取 `928,16,69,25` | 上游 `923,16,74,25` 在本机仍把图标边缘读成前导 1（18/30），按实机逐列扫描校准 |
| 2026-11-20 | P0-2/P0-3 合并并推送 | `33cc7e06`、`78d95b2a` 合入 `czr`，推送至 `510a0052`；P0-1 等武道大会开放后实机再合 |
| 2026-11-21 | P3 两条采纳并进 `staging/20261121-p3` | 用户确认落地；`7b2f2492` 属低风险防御，`ea13a4c6` 属未实现占位清理，均不触碰运行链路 |
| 2026-11-21 | P3 批次暂不合并 `czr` | 按 R2/R3 闸门，自动化与启动验证已过，等用户确认后再 `--no-ff` 合入 |
| 2026-11-21 | P3 批次合并并推送 | 用户确认后 `997dab48` 合入 `czr`；合并后 `524 passed / 10 failed`（失败项与基线一致）、页面注册 105 |

## 9. 增量同步（2026-11-20）

重新 `fetch` 5 源后的对比结果：

| 源 | 11-18 tip | 11-20 tip | 新增提交 |
| --- | --- | --- | --- |
| nearaura/master | `48f34cb0` | `48f34cb0` | 无 |
| nearaura/dev | `ac712acc` | `bb6f2103` | 1 条：`bb6f2103` 突破券 OCR 区域收窄 |
| kongdr418/mine | `f4bf42bc`（本地 ref 当时只到 `838d4b7c`） | `f4bf42bc`（已补齐） | 无新提交，但 `95b75dd8`、`5db01e76` 现已可取 |
| lgg686/self | `761614dc` | `0f99fd02` | 1 条：`0f99fd02` 恢复突破券 OCR 区域 |
| pinkpig-Peppa/master | `aff78b2c` | `aff78b2c` | 无 |

结论：

- 11-18 之后上游**只新增一类改动**：突破券 OCR 恢复/收窄，但三源并非同一补丁（patch-id 各不相同）：
  - kongdr `f4bf42bc`：只改 `base.py`，把 `_META` 变体切回常规变体；
  - nearaura/dev `bb6f2103`：只改 ROI（`assets.py` + `ocr.json`），`realm_raid_number1` 从 `920,12,78,30` 收窄为 `923,16,74,25`；
  - lgg686/self `0f99fd02`：`base.py` + ROI + 更新 MetaDemon 入口模板。
- 本地没有 `_META` 变体（那是上游在 MetaDemon 活动期间临时加的），所以 `f4bf42bc`/`0f99fd02` 的 `base.py` 部分**无法直接套用**；只有 `bb6f2103` 的纯 ROI 改动能干净合并。
- 本地 `O_REALM_RAID_NUMBER1` 仍是旧 ROI；现有 `0 <= cu <= total == 30` 校验挡不住「多认一位」的前导数字，因此 `bb6f2103` 的 ROI 收窄**归入 D6 批次，先进 staging 实机验证读数，通过后再合**。
- 之前因 ref 陈旧不可见的 `95b75dd8`、`5db01e76` 已可取到，`E2`/`E5` 不再受 fetch 阻塞。
- 5 源跨源去重、过滤已在本地内容后仍有 **311 条**候选，构成本立项后续 D 批次的取数池。
- fix 类提交的通用取舍规则（五类分型 + 判定五步）已写入 [upstream_sync_doc.md §15](file:///f:/codespace/OnmyojiAutoScript/dev_tools/upstream_sync_doc.md)，后续新更新直接按该规则判定。

### 9.1 P0 执行结果（2026-11-20）

| 项 | 分支 | 结果 | 验证 |
| --- | --- | --- | --- |
| P0-2 突破券 OCR | `staging/20261120-realm-raid-roi` | 已合并 `33cc7e06` | ROI `928,16,69,25`；困难 28 入口连拍 3 张均 `8/30`（0.998）；回归 4 passed |
| P0-3 悬赏新 UI | `staging/20261120-wq-mystery` | 已合并 `78d95b2a` | 13 条去重后仅补 3 条语义；goto_1~4 匹配 1.000、`wq_exit` 0.995；回归 8 passed |
| P0-1 武道大会首领战 | `staging/20261120-mt-boss` | 待实机（`d541ff7a`） | 回归 5 passed；活动总览为「祸至无日」，开放后补测再合 |

合并后全量 `523 passed / 10 failed`（10 项均为既有失败），`PageRegistry` 105 个页面，`czr` 已推送。

### 9.2 增量同步（2026-11-21）

重新 `fetch` 5 源后，只有 `lgg686/self` 有新提交（`0f99fd02` → `8b06fd35`，12 条，含 2 条合并提交）；其余四源 tip 未变。工具口径跨源去重并剔除本地已有内容后候选 **316 条**。

| 判定 | 数量 | 提交 |
| --- | --- | --- |
| 可落地（P3，已落地待合并） | 2 | `7b2f2492`（uvicorn keep-alive 75s）、`ea13a4c6`（移除 OrochiMoans 占位） |
| 不适用 | 8 | `db601816`、`adfa6e84`、`52f23c56`、`9d9a6fbd`/`e7ca7b1a`（同 patch）、`17bb2993`、`f7a3f643`、`8b06fd35` |
| 合并提交（无独立内容） | 2 | `bb5a54a7`、`12e61d99` |

结论：本轮新增几乎全部是 Android/OASA 适配（oasaos 设备后端、热更新、Android 鉴权、SemiAuto 常驻工具），本地无 APK 运行时与对应模块，**不引入**；两条 P3 已按用户确认落进 `staging/20261121-p3`，验证结果见 §9.3。

- `7b2f2492`：本地 `server.py` 的 `uvicorn.run` 未设 `timeout_keep_alive`（默认 5 秒），上游改为 75 秒；标注器轮询 2.5 秒当前未触发，但属低风险防御。
- `ea13a4c6`：本地 `tasks/OrochiMoans` 与上游删除前一致（空 `assets.py` + 仅 `scheduler` 的配置），且不在配置菜单与 i18n；删除后 `config/oas1.json` 的旧键由 pydantic 默认忽略。

逐条证据与「上游值 → 本地值 → 验证」见[增量同步报告](upstream-sync-20261121/upstream-sync-20261121.md)（[HTML](upstream-sync-20261121/upstream-sync-20261121.html)）。

### 9.3 P3 落地结果（2026-11-21）

分支 `staging/20261121-p3`（从 `czr` @ `3a0237c8` 拉出），已合并 `997dab48`；台账见 [staging_pending.md §3](../../staging_pending.md)。

| 项 | 改动 | 验证 |
| --- | --- | --- |
| `7b2f2492` keep-alive | `server.py` 的 `uvicorn.run` 增加 `timeout_keep_alive=75` | 启动本分支服务后，同一 HTTP 连接空闲 8 秒再发请求成功；同应用默认 keep-alive 对照在 8 秒后报 `WinError 10053` 断连 |
| `ea13a4c6` OrochiMoans | 删除 `tasks/OrochiMoans`（2 文件）；`config_model.py` 去 import 与字段；`config_manual.py` 优先级串去掉 `OrochiMoans`/`OrochiJudgement`（两者均无任务目录）；`config/template.json` 删 `orochi_moans` 段 | `ConfigModel` 无该字段但仍接受含 `orochi_moans` 的旧配置；模板键与模型字段零差集；`PageRegistry` 105 页不变 |

全量 `pytest tests/ -q`：**524 passed / 10 failed**（7 项 HeroTest `Timer`、2 项 SwitchOnmyoji 环境失败、1 项 DailyTrifles 收益历史，均与基线一致；通过数比 11-20 基线多 1 项，来自工作区已存在但未提交的重连守卫用例，与本批无关）。

未删除 `module/config/i18n/zh_CN.xml` 与标注器 `app.js` 中同名映射，与上游删除范围保持一致。合并后已跑全量回归与页面冒烟，结果同上。

## 10. 工作规则（用户约定，2026-11-20 固化）

> 优先级：**用户习惯（`project_memory.md` / `user_profile.md`）> 本节 > Skill**。本节是习惯的书面化；两处冲突时按用户习惯执行，并立即同步修改本文件与 [Skill](file:///f:/codespace/OnmyojiAutoScript/.trae/skills/upstream-sync/SKILL.md)。

| # | 规则 | 落地方式 |
| --- | --- | --- |
| R1 | 改动只进预演分支 | `staging/YYYYMMDD-主题` 从 `czr` 最新提交拉出；`czr` 验收前保持干净 |
| R2 | 合并闸门三条件 | 自动化全绿 + 实机通过 + 用户明确确认，缺一不可，齐备才 `git merge --no-ff` |
| R3 | 每批停下等确认 | 不自行合并，不连续合并未确认批次；先报测试与实机证据再问 |
| R4 | 批次台账唯一 | `dev_tools/staging_pending.md`：开工先读 §2，建批登记，合并/废弃迁 §3；状态 `进行中 → 待测试 → 待合并 → 已合并 / 已废弃` |
| R5 | 自动化口径 | 全量 `pytest tests/ -q`（记录通过/失败数，说明既有 10 项失败有无变化）+ `PageRegistry` 冒烟（基线 105 页） |
| R6 | 实机证据 | adb 设备跑相关任务；截图放 `.screenshots/` 不入库；报告写截图张数、匹配分、OCR 读数；无法验证必须标阻塞 |
| R7 | 偏离上游留痕 | 按「上游值 → 本地值 → 实测原因」写进测试 docstring、提交信息与台账 |
| R8 | 上游按语义取 | 先跨源去重，再逐条判「已覆盖 / 不适用 / 可落地」，只补真缺口，不机械全量套用 |
| R9 | 呈现与提交格式 | 比对/清单出 §16 自包含 HTML（md 为权威源）；提交按 §14 中文头行 + Why/What/Verify，多行走 `git commit -F` 临时文件 |
| R10 | 推送后回写立项 | 更新本 README、`backlog.md`、`remaining-work.html` 与 `upstream_sync_log.md`，保持代码 — 台账 — 立项一致 |
| R11 | 先清单后动手 | 上游同步或大范围改动，先出比对清单与取舍建议（HTML），确认后才改代码 |
| R12 | 规则单一来源 | 习惯 → 本节 → Skill 顺序同步，禁止只改一处；用户明确指令可临时覆盖，但执行前提示风险 |
| R13 | 精度优先 | 上游以启发式/近似替换本地精确计数的提交默认不采纳；确需采纳须附实机数据证明精度不降 |
| R14 | 汉化可读 | 提交标题、模块名、冲突分析、工具界面用中文；数值展示要精确，缩写场景点详情读取完整值 |
| R15 | 上游差异总账唯一 | `upstream-full-compare-20261122/` 的 md 为唯一差异总账（HTML 为同结论呈现层）；每次 `fetch` / 同步 / 判定后**原地增删改**并追加 §11.7 更新记录，不另起新报告替代 |

操作细节：

- **开工自检**：先跑 `python dev_tools/session_start.py`（打印 `staging_pending.md §2` 与 `upstream_sync_log.md §1` 摘要，并把 `czr` 自动合并进当前 `staging/*` 分支；工作区脏或冲突时只报告不合并），存在未完成批次时先报告再决定继续/合并/废弃；只要简报不改工作区用 `--check`。
- **跨机开工**：新电脑 `git fetch` → `git switch czr` → `git pull` → 跑上面的脚本。仓库内条款随 git 同步；单机记忆（`~/.trae-cn/memory`）不随仓库走，以本节与台账为准。
- **推送**：`git push origin czr`；直连 github 失败按 [upstream_sync_doc.md §13.9](file:///f:/codespace/OnmyojiAutoScript/dev_tools/upstream_sync_doc.md) 走本机代理回退，禁止修改 git config。
- **收尾定义**：合并 → 推送 → 台账 → 立项，四步做完才算一批结束。

## 11. 全量对比（2026-09-18 → 2026-11-22）

> **本报告自 2026-11-22 起为「上游差异总账」（活文档）**，按 R15 原地维护：新提交追加、状态变更改写、确认不引入的标记保留可追溯；md 为权威源，HTML 与 md 结论必须一致。
> 完整逐条数据：[全量对比 md](upstream-full-compare-20261122/upstream-full-compare-20261122.md) · [HTML](upstream-full-compare-20261122/upstream-full-compare-20261122.html)。本节只保留结论。

### 11.1 口径与证据链

- 5 源重新 `fetch`（2026-11-22）；窗口内原始提交 585 个（跨源哈希重复），按 `patch-id` 去重后 **483 条独立变更**，另 **99 条合并提交**（98 条含首父差异、1 条空合并），覆盖 **59 个模块**。
- 「已完整同步」按以下任一证据判定：① `patch-id` 与 `czr` 精确一致；② 本地提交信息显式引用该上游哈希（cherry-pick / 移植说明）；③ 台账表格行记录已合入/已覆盖；④ backlog 明确移植（A5/A6/A7/B1）；⑤ 已落地 `staging/*`（待验收）。
- 其余项：本地模块目录存在 → **部分实现**；本地无对应模块 → **完全缺失**。
- 基线为 `czr`，**不含** `staging/20261122-chess-sync` 与工作区未提交改动。

### 11.2 总览

| 维度 | 分布 |
| --- | --- |
| 本地状态 | 已完整同步 **176** · 部分实现 **261** · 完全缺失 **46** |
| 变更类型 | 可直接复用优化 **239** · 适配风险 **144** · 核心模块大改 **87** · 格式/文档 **13** |
| 同步建议 | 已处理 **176** · P1 可排期 **95** · P2 单独评估 **83** · P3 谨慎评估 **85** · P4 低优先 **7** · 不引入 **26** · **P0 优先合并 11** |

### 11.3 重点模块

| 模块 | 总条数 | 已同步 | 部分实现 | 完全缺失 | 建议 |
| --- | ---: | ---: | ---: | ---: | --- |
| Component | 60 | 21 | 39 | 0 | 可排期（共享战斗框架，需隔离批次） |
| DraftDuel | 39 | 2 | 0 | 37 | **单独评估（新功能缺口）** |
| MetaDemon | 33 | 9 | 24 | 0 | 可排期 |
| Chess | 24 | 6 | 18 | 0 | 优先合并（3 条 P0） |
| GameUi | 23 | 14 | 9 | 0 | 可排期（全仓导航，高影响） |
| WantedQuests | 23 | 5 | 18 | 0 | 优先合并（1 条 P0） |
| module/server | 22 | 4 | 18 | 0 | 不引入（Android/OASA 为主） |
| FrogBoss | 21 | 10 | 11 | 0 | 优先合并（2 条 P0） |
| Exploration | 19 | 9 | 10 | 0 | 优先合并（1 条 P0） |
| ActivityShikigami | 14 | 0 | 14 | 0 | 单独评估（核心模块大改） |

完全缺失的 46 条集中在：DraftDuel（37）、AutoStory（2）、BorrowShikigami（2）、`module/scrolls`（2）及其余零散项；其中 A1/A3 需新账号验收，E5 绘卷仍搁置。

### 11.4 P0 优先合并清单（11 条）

| 提交 | 模块 | 摘要 |
| --- | --- | --- |
| `acbdbf1c` | Chess | 加宽鼬乐币 OCR 区域，修复刷满不停止 |
| `8f945012` | Chess | 买卡成功与商店换卡后清理格子点击记录 |
| `a9597e77` | Chess | 卖卡与上御魂前清理点击记录，修复 GameTooManyClickError |
| `a70757b1` | Exploration | 退出时避免过早返回导航 |
| `27dc33a4` | FrogBoss | 调整对弈竞猜策略逻辑 |
| `9ec93a44` | FrogBoss | 修复下注确认被弹窗遮挡导致的死循环 |
| `57c3f701` | GlobalGame | 放宽协作图标识别区域 |
| `91010725` | GlobalGame | 放宽忽略按钮识别区域 |
| `885ea02c` | Restart | 调整登录界面「进入游戏」OCR 区域 |
| `ac482cf2` | WantedQuests | 调整悬赏列表 OCR 区域，适配新 UI |
| `73cf2c63` | base_task.py | 补 `clock_time` 导入，修复 `set_next_run_next_monday` NameError |

> P0 仅代表「小范围、模块内聚、本地定制低」，**不等于零冲突**；仍需按 R1/R2 进 `staging/*`，以 `apply` 预检与实测为准。

### 11.5 判断与下一步

1. **结构性分叉已固化**：本地独有 `flow`、超鬼王祸主降临/协战、Chess 改造、RichMan 整合，上游 483 条中仅 176 条能确认已同步；继续禁止整体换库。
2. **先做低风险 P0（11 条）**：Chess 3 条、FrogBoss 2 条、GlobalGame 2 条与 Exploration/Restart/WantedQuests/base_task 各 1 条，建议合并为 1~2 个 staging 批次。
3. **DraftDuel 单独立项**：39 条提交、37 条本地完全缺失，涉及双端协同与开放时段，不混入稳定性批次。
4. **框架/共享模块隔离**：`module/*`（144 条适配风险）与 `Component`/`GameUi` 必须单独批次，先启动验证再实机。
5. **活动类维持阻塞**：A5/A6/A7/B1/B2 等待活动开放，不用推理替代实机证据。
6. **存量批次提醒（2026-11-22）**：`staging/20261120-mt-boss` 为「待测试」，`staging/20261122-chess-sync` 为「进行中」，另有工作区未提交的重连守卫改动；本次全量对比未修改任何运行代码。

### 11.6 关联决策

| 日期 | 决策 | 说明 |
| --- | --- | --- |
| 2026-11-22 | 建立 9-18 起全量对比基线 | 统一「已同步 / 部分实现 / 完全缺失」三分类与 P0~P4 建议口径，后续增量对比沿用 |
| 2026-11-22 | 精度优先继续生效 | `f7db71b2`、`aaede1db`（启发式 tab 检测替代精确计数）标记不采纳 |

### 11.7 更新记录

| 日期 | 版本 | 变更 | 来源 |
| --- | --- | --- | --- |
| 2026-11-22 | v1 | 首次建立 9-18 起全量基线：483 条独立变更 + 99 条合并；确定三类状态、四类变更、P0~P4 建议 | 只读分析，无代码改动 |

> 维护规则：每次 `fetch` / 同步 / 判定后，在本表追加一行并同步修改 md 与 HTML；状态变化只改对应行，不删除历史条目，避免无法追溯。
