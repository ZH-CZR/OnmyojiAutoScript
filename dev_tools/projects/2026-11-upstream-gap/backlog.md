# 缺口清单（Backlog）

配套文档：[立项书](README.md) · [对比报告](upstream_feature_gap_20261118.md)

状态：`待办` / `进行中` / `待实机验证` / `已完成` / `搁置`

## 进度快照（2026-11-22 全量复核）

- **全量对比（2026-09-18 → 2026-11-22）**：5 源去重后 483 条独立变更 + 99 条合并提交，覆盖 59 个模块；本地 **已完整同步 180 / 部分实现 257 / 完全缺失 46**。类型：可复用优化 239、适配风险 144、核心模块大改 87、格式 13；建议：P0 0、P1 95、P2 83、P3 85、P4 7、不引入 33。详见 [全量对比报告](upstream-full-compare-20261122/upstream-full-compare-20261122.md)（[HTML](upstream-full-compare-20261122/upstream-full-compare-20261122.html)）。
- **P0 复核（2026-11-22 完成，2026-11-23 合并）**：11 条全部有结论——`8f945012`/`a9597e77`/`9ec93a44`/`ac482cf2` 本地已覆盖（已处理），`acbdbf1c`/`a70757b1`/`27dc33a4`/`57c3f701`/`91010725`/`885ea02c`/`73cf2c63` 不适用（不引入）；P0 剩余 0。唯一新增代码为 `9ec93a44` 同文件后续修复 `f67e5a80`（结束标志排除遮挡页），已合入 `czr`（`afba9fa4`），对弈竞猜实机待活动开放后补验。
- **完全缺失（46 条）**：DraftDuel 37、AutoStory 2、BorrowShikigami 2、`module/scrolls` 2，其余零散；DraftDuel 单独立项，A1/A3 需新账号，E5 仍搁置。
- **P1 95 条（2026-11-23 首批落地）**：逐条判定见 [p1-triage-20261123.md](p1-triage-20261123/p1-triage-20261123.md)——已覆盖 41、不适用 30、需实机 8、可落地 15、已落地 1。可落地 15 条中 **9 条已移植**进 `staging/20261123-p1-sync`（`17474206`/`ba0d49b7`/`31a853a9`/`fcd496de`/`6084f210`/`1c646ce5`/`dd51be24`+`f0c8473d`/`3ad3ff86`），**6 条因实机/素材/调用点待补**（`69a0fc4f`/`f3f62f43`/`252c6701`/`9eea7c9d`+`bf893c0d`/`d7d98690`）；全量 `528 passed / 10 failed`，页面注册 105。
- **存量批次**：`staging/20261120-mt-boss` 待测试（武道大会未开放）；`staging/20261124-biggod-game-claim` 待测试（游戏内领取导航/收尾实机通过，领奖素材待补验）；`staging/20261123-itachi-shop` 实机通过待合并；`staging/20261122-chess-sync` 已合并 `43a56be5`（百鬼投掷/新增阵容/工坊实机待补验）；`staging/20261122-p0-frog` 已合并 `afba9fa4`（实机待补）；`staging/20261123-p1-sync` 已合并 `79fa6925`（P1 首批移植 9 条；16416 实机通过页面识别/导航与悬赏重扫扫描，活动/战斗类项待活动开放补验）；`staging/20261123-feature-gap-refresh` 已合并 `0e87a5e3`。
- **上游增量（2026-11-21）**：5 源重新 fetch，仅 `lgg686/self` 新增 12 条（含 2 合并），几乎全是 Android/OASA 适配；逐条判定后仅 2 条 P3 可落地（`7b2f2492` uvicorn keep-alive、`ea13a4c6` 移除 OrochiMoans 占位），已按确认落进 `staging/20261121-p3` 并通过自动化与启动验证，已合并 `997dab48`；其余 10 条不适用。详见 [增量同步报告](upstream-sync-20261121/upstream-sync-20261121.md)（[HTML](upstream-sync-20261121/upstream-sync-20261121.html)）。
- **已完成移植、待实机验证**：`A7` 青蛙瓷器挑战赛、`A5` LBS 鬼王、`A6` 狭间幻境（活动未开放，实机挂起）；`B2` 武道大会首领战代码完成（`d541ff7a`，`staging/20261120-mt-boss`）。`B1` 鼬金币商店已实机通过（`staging/20261123-itachi-shop`，待合并）。
- **P0 已合入**：突破券 OCR 区域收窄（`33cc7e06`，实测校准 `928,16,69,25`）、封印悬赏新 UI 三项语义（`78d95b2a`）；合并后全量 `523 passed / 10 failed`，已推送 `510a0052`。
- **改判**：`B2` 由「待办」改为小补丁——`MartialTournament` 已有 boss 搜索、单体/群体识别、战斗与一键御魂，仅缺 `boss_limit` 阶段；`A2` 改为并入现有 `Exploration`（只缺章节区间与稀有度筛选），不新建任务；`A4` 不采纳（与 `module/flow` + `CustomFlow` 重复）。
- **已评估、不采纳**：`E1` RuleFrame（高耦合，不整套引入）、`E3` 看门狗 + Apprise（本地已有 onepush 与失败三次退出机制）、`E4` OCR 升级（2026-11-23 已完成同图 A/B：精度上游优、速度/体积本地优，代码备在 `staging/20261123-ocr-paddle`，**暂缓合并**，见 [对比报告](ocr-engine-ab/ocr-engine-ab.md)）；`E5` 绘卷查询搁置。
- **已落地、需从 D 批次扣除**：Chess 手牌满出售（`23a8b8a4`）、SixRealms 月之海（语义已覆盖：本地为页面式自研实现，上游 `f636e9d9` 未直接合入、不在 HEAD 祖先链）、RealmRaid 突破券上限（`eb156b16`）、悬赏 D3（`78d95b2a`）、突破券 ROI（`33cc7e06`）。
- **未开始**：`A1`、`A3`（需新账号才能验收）、`C1`~`C4`（单独立项）、`D1` 剩余项、`D2` 剩余项、`D5` 剩余项（P1/P2/P3）、`D6` 除突破券 ROI 外的剩余项、`E2`。
- **P3 已合并（2026-11-21）**：`staging/20261121-p3` → merge `997dab48` —— `server.py` keep-alive 75s（8s 空闲同连接复用成功，默认 5s 对照断连）、删除 `tasks/OrochiMoans` 占位（旧配置兼容、模板零差集）；合并后全量 `524 passed / 10 failed`（失败项与基线一致），页面注册 105。
- **下一会话建议顺序（2026-11-22 更新）**：P1 95 条（优先零冲突小补丁）→ `D1` MetaDemon（24 条未同步）→ `D2` FrogBoss（11）→ `D4` Chess（18）→ `D5` GameUi（专项评估完成，剩 4 条）→ `D6` Duel/SixRealms/Exploration/RealmRaid/DailyTrifles（22）→ 活动开放后补 A5/A6/A7/B1/B2 实机；`DraftDuel` 单独立项。
- **另一立项**：`dev_tools/projects/2026-11-custom-flow/` 的 M1~M5 全部未做，设备已在线，可随时开始实机冒烟。
- **前置约束（2026-11-20 已解除）**：已重新 `fetch` 全源，`kongdr418-mine/mine` 更新到 `f4bf42bc`，`95b75dd8`、`5db01e76` 均可取；11-18 后上游仅新增突破券 OCR 区域恢复（3 源等价），本地已等价覆盖。
- **预演流程**：自 2026-11-20 起改动走 `staging/YYYYMMDD-主题` 分支，台账见 `dev_tools/staging_pending.md`。
- **本轮结果（A5 LBS 鬼王）**：按 lgg686 `ad15a023`/`188dee7c`/`a1fb24a6`/`f01a83f0` 移植 `tasks/LBS`（17 文件，单人/组队匹配/开车三模式）；`GeneralRoom` 建房/权限/确认方法支持传入任务自有弹窗资产，`GeneralInvite.exit_room` 确认弹窗等待 0.8s→1.8s；已注册 config_model / config_menu / config_manual / template.json / i18n。离线回归 `tests/test_lbs_port.py` 10 例通过；全量 `505 passed / 10 failed`（10 个均为既有失败：HeroTest Timer、switch_onmyoji、dailytrifles income）。未实机验证、未提交。
- **本轮结果（A6 狭间幻境）**：按 lgg686 `5bc76c7e`+`c2390c2a`（资产名取 `1f230af2` 重命名后的最终版）移植 `tasks/IbukiArena`（14 文件）；右上角剩余次数 OCR 驱动循环、连续 3 次识别失败退出、挑战前补截图避免 exit_matcher 旧帧提前命中；已注册 config_model / config_menu / config_manual / template.json / i18n。离线回归 `tests/test_ibuki_arena_port.py` 10 例通过；全量 `515 passed / 10 failed`（既有失败不变）。未实机验证、未提交。

## A. 新功能（M1 / M2）

| ID | 能力 | 来源 | 关键上游提交 | 规模 | 依赖 | 验收要点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | 自动剧情 `AutoStory` | kongdr418 / lgg686 | `547dfba6`、`3a8ba22f` | 24 文件 | 新手引导兼容 | 可连续推进剧情至章节结束 | 待办（需新账号验收） |
| A2 | 探索推进 `ExplorationFight` | kongdr418 / lgg686 | `fc45a500` | 约 10 文件 | 复用 `GeneralBattle` | 支持章节区间与稀有度选择 | 改判：并入 `Exploration` |
| A3 | 借用式神 `BorrowShikigami` | kongdr418 / lgg686 | `628c0cfb` | 约 15 文件 | A1/A2 | 完成借用并进入探索 | 待办（依赖 A1/A2） |
| A4 | 自定义任务 `CustomTask` | kongdr418 / lgg686 | `80751206` | 约 8 文件 | 与本地 `CustomFlow` 划清边界 | 支持用户自定义步骤序列 | 不采纳（与 flow 重复） |
| A5 | LBS 鬼王 | lgg686 | `ad15a023`、`188dee7c`、`a1fb24a6`、`f01a83f0` | `tasks/LBS` 17 文件 | 无 | 单人/组队匹配/开车三模式可切换；配置项 `lbs`；离线回归 `tests/test_lbs_port.py` 10 例通过 | 待实机验证 |
| A6 | 狭间幻境 `IbukiArena` | lgg686 | `5bc76c7e`、`c2390c2a` | `tasks/IbukiArena` 14 文件 | 御魂切换 | 剩余次数 OCR 驱动循环；连续 3 次识别失败退出；离线回归 `tests/test_ibuki_arena_port.py` 10 例通过 | 待实机验证 |
| A7 | 青蛙瓷器挑战赛 `FrogChallenge` | lgg686 | `1f230af2` | 已移植到 `tasks/FrogChallenge`，配置项 `frog_challenge`；骰子进度实时识别 + 无奖励/无进度保护；离线回归 `tests/test_frog_challenge_port.py` 8 例通过 | 待实机验证 |

## B. 现有任务补齐（M3）

| ID | 能力 | 来源 | 关键上游提交 | 说明 | 状态 |
| --- | --- | --- | --- | --- | --- |
| B1 | 鼬金币商店礼盒 | lgg686 `WeeklyPurchase/ItachiCoinShop` | `05fca68a` | 已移植到 `tasks/RichMan/itachi_shop.py`，配置项 `itachi_coin_shop.itachi_coin_buy_jade`；离线回归 `tests/test_richman_itachi_coin_shop.py` 14 例通过；16416 实机两次运行买齐大/中/小三个礼盒；本地差异：名称匹配容忍 OCR「鼬→融/丢字」，余额读数不可信时跳过校验 | 已实机通过（`staging/20261123-itachi-shop` 待合并） |
| B2 | 武道大会首领战 | lgg686 `MartialArts` | 模块整体 | 已加 `boss_limit`（默认 20）+ `current_limit` / `current_climb_page`，boss 复用门票页；`staging/20261120-mt-boss` | 待实机验证（活动未开放） |
| B3 | 游戏内领取大神福利 | Maratrain/mine `game_claim.py` | `9023e04`、`54302449` | 移植 `GameClaimMixin` 全链路（庭院曜日牌 → 日程 → 通知 → 大神福利中心 → 领奖 → 收尾），`script_task.py` 5 处挂载；新增本机红木牌曜日牌 `I_GAME_BOARD_RED`；`tests/test_biggod_game_claim.py` 14 项；已合并 `7f4af19b3` | 已实机通过（12 素材中 11 项；仅「领奖」金色按钮待账号绑定大神且有可领取条目） |

## C. 协同对弈（M4）

| ID | 能力 | 来源 | 关键提交 | 说明 | 状态 |
| --- | --- | --- | --- | --- | --- |
| C1 | 对战大厅与邀请 | kongdr418 / lgg686 | 见报告第 4 节 | 消耗识别、邀请好友、队长/队员 | 待办 |
| C2 | 自动选人 | 同上 | 阵容矩阵评分 + 火系名单 | 可配置权重 | 待办 |
| C3 | 双端协同接入 | 同上 | `ed25cc79` 等 | 复用本地 `module/team_flow`（MQTT），不引入第二套框架 | 待办 |
| C4 | 训练模型与对局记录 | 同上 | 训练脚本 + 记录 | 可选能力，先留接口 | 待办 |

> 复审备注（2026-11-20）：C 系列体量 70 文件 / 41 提交，涉及双实例时序与开放时段，整体**单独立项**，不进入本批执行。

## D. 稳定性批次（M5）

按模块分批立项，每批一个提交，便于回滚。条数为 **2026-11-22 全量口径的未同步数**（部分实现 + 完全缺失，含 P0~P3）；括号内为 11-18 决策池旧值。

| 批次 | 模块 | 条数 | 代表问题 | 状态 |
| --- | --- | --- | --- | --- |
| D1 | MetaDemon | 24（旧 19） | 上供自定义星级、召唤顺序、双端协同、新 UI 识别 | 待办（优先） |
| D2 | FrogBoss | 11（旧 15） | 下注确认遮挡死循环（`9ec93a44`）、对弈竞猜策略（`27dc33a4`）、零权重随机 | 待办（2 条 P0 优先） |
| D3 | WantedQuests | 18（旧 13） | 新版封印悬赏 UI、目标子串匹配、追踪按钮范围（`ac482cf2` 为 P0） | 已完成主体（`78d95b2a`）；剩余 18 条未同步待排期 |
| D4 | Chess | 18（旧 9） | 手牌满出售腾位、点记录清理（`acbdbf1c`/`8f945012`/`a9597e77` 为 P0）、OCR v6-small | 待办（3 条 P0 优先；手牌满出售 `23a8b8a4` 已落地） |
| D5 | GameUi | 9 | 已做专项评估（7 源 15 条冲突簇）：1 条 P1（`script.py` 强制 Restart）+ 1 条 P2（棋局退出确认 alt）+ 2 条 P3（商店第 4 候选、町中保底），其余不采纳/已覆盖 | 待决策（见 `gameui-merge-20261123/`，不整体整合） |
| D6 | Duel / SixRealms / Exploration / RealmRaid / DailyTrifles | 22（旧 14） | 魂魄溢出点击、斗技识别资源、月之海识别、突破券 OCR 区域（Exploration `a70757b1` 为 P0） | 部分完成：突破券 ROI 已合入 `33cc7e06`（校准 `928,16,69,25`）；月之海 `f636e9d9`、突破券上限 `eb156b16` 已落地；其余待办 |

## E. 框架能力（M5 评估项）

| ID | 能力 | 来源 | 关键提交 | 结论 | 状态 |
| --- | --- | --- | --- | --- | --- |
| E1 | `RuleFrame` 识别框架 | nearaura 系 | `92bb2f2e`、`8753481b`、`7c5f380b` | 需评估与本地识别层兼容性 | 不采纳 |
| E2 | `/tool/doctor` 体检 | kongdr418 | `5db01e76` | 独立工具，可后置 | 待办（ref 已就绪） |
| E3 | 看门狗 + Apprise | kongdr418 | `50dec6ce`、`d389f83a` | 本地已有 onepush，需评估是否并存 | 不采纳 |
| E4 | OCR 引擎升级 | kongdr418 / lgg686 | `56529f78`、`26e67b73` | 已完成 40 条同图 A/B：全对 38/40 vs 32/40、平均 CER 3.33% vs 7.52%（上游优）；单行中位 118.5ms vs 3.2ms、模型 132.9MB vs 10.9MB（本地优）。移植代码备在 `staging/20261123-ocr-paddle`（`5d60b803`），全量 542 passed / 10 failed，实机未做 | 暂缓合并（需要时直接合并） |
| E5 | 绘卷查询 `module/scrolls` | kongdr418 | `95b75dd8`、`92ada2c7` | 查询工具，非任务，优先级低 | 搁置（ref 已就绪） |
| E6 | 统一队伍预设与御魂切换框架 | Shu_Li_x | `c95d4e7e`（后续 `cccad7086`、`7fa733863`） | `QuickLoadout` 新增 `dungeon`/`dungeon_config`/`activity`，13 个任务接入，配置层合并御魂与阵容并废弃 `switch_soul_config`；不落盘 cherry-pick 演练 23 个冲突路径，且与狭间暗域自有预设实现、本地 35 个 `SwitchSoulConfig` 任务冲突。A+B 档（准备页钩子、续邀识别、锁定解锁模板）已在 `staging/20261124-loadout-partial` | 待立项（C 档，先选 1~2 个单人任务试点） |
| E7 | 海汐礼盒售罄守卫 + 剩余数量 ROI | 本地（2026-11-26 实机发现） | 批次 54 实机 | 两个账号海汐礼盒「本周剩余数量 0 个」时，`_scales_buy_sea_more` 对禁用「购买」连点 8 次后抛 `GameTooManyClickError`；同时 `O_SCA_NUMBER_SEA` 把 0 误读为 29/30 导致 `remain_number` 钳制失效。旧切轮逻辑与上游新逻辑同表现，非本批引入 | 待立项（售罄识别后优雅结束 + ROI 重标定，需下周刷新后实机标定） |

## F. 排除项

| 项 | 原因 |
| --- | --- |
| 整体切换到 lgg686 / kongdr 分支 | 会丢失 `flow`、超鬼王祸主降临/协战、Chess 改造、RichMan 整合 |
| 直接 cherry-pick 引擎/依赖级提交 | 与本地技术栈冲突，需单独评估 |
| 移植 nearaura 的 `General` 目录 | 2023 年遗留，无实际功能 |
| `A4` 自定义任务 `CustomTask` | 与 `module/flow` + `CustomFlow` 重复，本地支持编排并生成可调度任务，能力更强 |
| `E3` 看门狗 + Apprise | 本地已有 onepush，且内置失败三次退出/推送/可选关模拟器，缺的只是卡死检测这一小块 |
| `E4` OCR 引擎升级 | 不再是「技术栈冲突即否决」：A/B 显示精度上游更优，但单行延迟约 37 倍、模型约 12 倍、内存约 3 倍，当前性价比不高；代码保留在 `staging/20261123-ocr-paddle`，暂不合并 |
| `E5` 绘卷查询 | 查询工具而非自动化任务，优先级最低，搁置 |
