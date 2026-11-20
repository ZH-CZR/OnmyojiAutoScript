# 本地 czr 与上游 5 源功能差距对比报告

- 生成日期：2026-11-18
- 对比基准：本地 `czr` @ `4f53ebe0`（2026-11-17）
- 数据源：`dev_tools/upstream_sources.json` 中全部 5 源（数组序 = 优先级）
- 判定口径（用户指定）：**功能覆盖优先**，其次看已有任务行为差异、稳定性修复、框架/UI 能力
- 数据方法：
  1. `python dev_tools/upstream_sync.py fetch` 拉取 5 源到 `refs/remotes/<slug>/<branch>`
  2. `python dev_tools/upstream_sync.py list --json` 生成跨源 patch-id 去重的候选清单（385 条）
  3. 用 `dev_tools/upstream_sync_log.md` 中出现过的 hash 过滤已同步/已决策项，得到 **242 条真实待决策提交**
  4. 任务集合以 `module/config/config_model.py` 的 `ConfigModel` 注册键为准（`config/template.json` 是旧模板，缺新任务键，不能作为注册依据）

## 1. 结论速览

| 维度 | 结论 |
| --- | --- |
| 功能覆盖数量 | `lgg686/self`（65 个注册任务） > `kongdr418/mine`（63） > **本地（61）** > `nearaura/dev`（56） |
| 本地真正缺的**新任务** | 协同对弈 `DraftDuel`；起号套件 `AutoStory`/`ExplorationFight`/`BorrowShikigami`/`CustomTask`；`LBS` 鬼王；`IbukiArena` 狭间幻境；`FrogChallenge` 青蛙瓷器挑战赛 |
| 本地缺的**小功能** | 鼬金币商店礼盒 OCR 购买（lgg686 `WeeklyPurchase` 内 `ItachiCoinShop`）；武道大会「首领战」阶段 |
| 本地缺的**工具/框架** | 绘卷查询 `module/scrolls`（kongdr）；`/tool/doctor` 体检；看门狗 + Apprise 通知；`RuleFrame` 识别框架；OCR 引擎升级（paddleocr 3.7） |
| 本地**独有** | 自定义流程编排 `module/flow` + `CustomFlow` 任务 + 标注器 flow 页面（上游全无）；超鬼王祸主降临 `ChaoGuiWang`/`ChaoGuiWangAssist`；`Chess` 百鬼棋局的本地改造；整合 11 类采购的 `RichMan` |
| **谁更好用** | 单纯论「功能种类」：`lgg686/self` 覆盖最广；但本地在超鬼王专项、自定义流程、棋局上领先，且本地已包含 nearaura/pinkpig 的全部任务。**结论：不建议换仓库，建议定向移植缺口** |
| 真实待决策提交 | 242 条（fix 139 / feat 61 / refactor 24 等），其中框架类 68 条 |

> 说明：`list` 返回的 `applied`（55 条）不可靠——本地做过冲突取舍或自检补正的提交 patch-id 会变，会被重新列为待同步。本报告以**台账**为准做过滤。

## 2. 各源基本情况

| 源 | 分支 | tip | 日期 | 注册任务数 | 特点 |
| --- | --- | --- | --- | --- | --- |
| 本地 `czr` | — | `4f53ebe0` | 2026-11-17 | 61 | 含 flow、超鬼王、棋局、RichMan |
| nearaura | master | `48f34cb0` | 2026-11-12 | 56 | 与 dev 同源，账号封禁后的临时仓库 |
| nearaura | dev | `ac712acc` | 2026-11-16 | 56 | 本地的主要历史参考源 |
| kongdr418 | mine | `f4bf42bc` | 2026-11-18 | 63 | 独有：协同对弈、起号套件、绘卷查询；含未验证依赖升级 |
| lgg686 | self（Gitee） | `761614dc` | 2026-11-14 | 65 | 独有：LBS、狭间幻境、青蛙挑战、每周采购 |
| pinkpig-Peppa | master | `aff78b2c` | 2026-11-15 | 56 | 与 nearaura 高度同源（新增参考源） |

## 3. 任务覆盖矩阵（只列有差异的项）

图例：✓ 有；✗ 无；~ 有同类实现但范围不同；— 不适用

| 能力 | 本地 | nearaura | kongdr418 | lgg686 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 协同对弈 `DraftDuel` | ✗ | ✗ | ✓ | ✓ | 双实例协同、自动选人评级、训练模型、对局记录；41 条提交 / 70 个文件 |
| 自动剧情 `AutoStory` | ✗ | ✗ | ✓ | ✓ | 起号套件之一，24 个文件 |
| 探索推进 `ExplorationFight` | ✗ | ✗ | ✓ | ✓ | 可配章节区间、自动旋转、稀有度选择 |
| 借用式神 / 15 级起号 `BorrowShikigami` | ✗ | ✗ | ✓ | ✓ | 剧情→借用→探索→经验妖怪，最终校验 15 级 |
| 自定义任务 `CustomTask` | ✗ | ✗ | ✓ | ✓ | 与本地 `CustomFlow` 定位相近但实现不同 |
| LBS 鬼王限时活动 | ✗ | ✗ | ✗ | ✓ | 单人挑战 / 组队匹配 / 开车模式；17 个文件 |
| 狭间幻境 `IbukiArena` | ✗ | ✗ | ✗ | ✓ | 伊吹之擂单人战斗；14 个文件 |
| 青蛙瓷器挑战赛 `FrogChallenge` | ✗ | ✗ | ✗ | ✓ | 11 个文件 |
| 绘卷查询 `module/scrolls` | ✗ | ✗ | ✓ | ✗ | 绘卷进度 / 排行榜 / 碎片库存查询工具，适配 Linux 与 redroid |
| 鼬金币商店 `ItachiCoinShop` | ✗ | ✗ | ✗ | ✓ | OCR 识别礼盒购买，属于 `WeeklyPurchase` |
| 每周采购 `WeeklyPurchase` | ~ | ✗ | ✗ | ✓ | 本地 `RichMan` 已覆盖其中 11 个商店类，仅缺鼬商店 |
| 武道大会 | ✓ | ~ | ✓ | ✓ | 本地：门票+体力；nearaura：门票爬塔（修炼演练被注释）；lgg686：体力+首领战 |
| 百鬼棋局 `Chess` | ✓ | ✗ | ✓ | ✓ | 本地 389 个文件，规模最大 |
| 超鬼王祸主降临 `ChaoGuiWang` | ✓ | ✗ | ✗ | ✗ | 本地独有（另有协战 `ChaoGuiWangAssist`） |
| 超鬼王门票 `MetaDemonTicket` | ✓ | ✗ | ✓ | ✗ | 本地与 kongdr 各有实现 |
| 自定义流程 `flow` + `CustomFlow` | ✓ | ✗ | ✗ | ✗ | 本地独有框架能力 |
| 美术工坊 `GuguArtStudio` | ✓ | ✗ | ✓ | ✓ | — |

**要点**

- `nearaura/master + dev` 与 `pinkpig-Peppa/master` 的任务集合是**本地子集**（唯一例外是武道大会实现：`BudokaiTournament` vs 本地 `MartialTournament`，属同一活动的不同阶段覆盖）。
- 真实功能缺口集中在 `kongdr418/mine`（协同对弈、起号套件、绘卷查询）与 `lgg686/self`（LBS、狭间、青蛙、每周采购）。
- 本地独有能力（flow、祸主降临、棋局改造）没有任何上游可以替代。

## 4. 本地缺的新功能（按性价比排序）

### P1 起号套件（4 个任务，kongdr 2026-11-13 新增）
- 组成：`AutoStory`、`ExplorationFight`、`BorrowShikigami`、`CustomTask`
- 能力：自动过剧情 → 借用式神 → 探索推进 → 经验妖怪，循环直到账号 15 级；含新手弹窗/新手战斗页兼容
- 依据：`547dfba6`、`3a8ba22f`、`fc45a500`、`628c0cfb`、`80751206`
- 风险：与本地 `base_task`、新手引导流程耦合较浅，移植成本低

### P1 协同对弈 `DraftDuel`（最大单项缺口）
- 规模：70 个文件、41 条提交（2026-10-30 起）
- 能力：大厅消耗识别、邀请好友、队长/队员双端、自动选人（阵容矩阵评分 + 火系名单）、训练模型介入、真实对局记录、上阵拖拽
- 依赖：双实例协同。**本地已有 `module/team_flow`（MQTT）**，具备复用基础
- 风险：开放时段限制、头像识别阈值调优、双端时序，属于高投入高收益项

### P2 LBS 鬼王限时活动
- 3 种模式：单人挑战 / 组队匹配 / 开车模式（创建公开房间，有人上车即退）
- 依据：`ad15a023`、`188dee7c`、`a1fb24a6`、`f01a83f0`
- 收益：可自动化的限时活动 +1

### P2 狭间幻境 `IbukiArena`
- 单人战斗活动，配 `SwitchSoul` + `GeneralBattle`；依据 `5bc76c7e`、`c2390c2a`

### P3 青蛙瓷器挑战赛 `FrogChallenge`
- 依据 `1f230af2`；与本地 `FrogBoss`（对弈竞猜）不是同一功能，不重复

### P3 鼬金币商店礼盒
- 仅需给 `RichMan` 补一个 `ItachiCoinShop` 子模块（OCR 识别礼盒）
- 依据 `05fca68a`

### P3 武道大会阶段补齐
- 本地：门票 `pass` + 体力 `ap`
- lgg686：体力 `ap` + 首领 `boss`（`boss_limit`）
- nearaura：门票爬塔（`daily_training`），修炼演练 `cultivation_drills` 在配置中被注释、未启用
- 结论：想要「首领战」需从 lgg686 移植阶段逻辑，属中等改动

### P4 绘卷查询 `module/scrolls`
- 非自动化任务，是查询工具（官方资源解析 + 排行榜/碎片），需 `cryptography` 等依赖
- 依据 `95b75dd8`、`92ada2c7`

## 5. 同任务行为 / 稳定性差距（本地有但落后）

| 模块 | 待决策 | 代表性缺口（具体） |
| --- | --- | --- |
| `MetaDemon` | 19 | 上供支持自定义星级（`ea8e72f3`）、上供召唤顺序 + 中文显示（`7478e169`）、双端协同或独立好友上供（`fe19476d`）、`battle_boss` 迁移为 `battle_wait` 策略钩子（`5a752388`）、协同心跳等待与退出截图过期（`83b82fd5`）、新 UI 识别图/ROI（`041e8686`） |
| `FrogBoss` | 15 | 下注确认被弹窗遮挡导致死循环（`9ec93a44`）、全员零权重时随机下注（`fcd496de`）、失败结果识别素材（`16d1205d`） |
| `WantedQuests` | 13 | 新版封印悬赏 UI 适配（`b37b56d2`/`c4d40686`/`d296406e`）、目标改子串匹配避免漏判（`82fae57e`）、地点数量识别失败收紧区域重试（`df572d01`）、追踪按钮识别范围（`5ac08e11`） |
| `Chess` | 9 | 手牌满且无可操作时出售阵容卡腾位（`ce9903bf`）、无需御魂时等全员解锁后随机投掷（`45b5772d`）、买卡/换卡后清理格子点击记录（`8f945012`）、OCR 接入 v6-small（`5a8f7385`）、新版棋局策略与标注器（`5001c0bc`） |
| `GameUi` | 9 | 探索标记横向偏移容错 + 回归测试（`fd7e20a5`/`0b8ef1cb`/`b8624012`）、庭院标志阈值下调修复登录卡死（`03429729`）、町中保底点击（`9d39f0c0`） |
| `GeneralBattle` | 5 | 魂魄溢出清理点击（`4a6ad558`）、退出战斗确认按钮新旧 UI 兼容（`e68b0b74`）、超鬼王门票 OCR 区域校准（`209f8fad`） |
| `Duel` | 4 | 斗技识别资源补齐 + 返回庭院函数修正（`9eea7c9d`/`bf893c0d`）、名士星数达标后延至下周一（`cf9eba73`） |
| `SixRealms` | 3 | 月之海岛屿漏识别与点击偏移（`f636e9d9`）、保留 OCR 已选岛屿（`043d3aa9`） |
| `Exploration` | 1 | 恢复常规突破券 OCR 区域（`f4bf42bc`，2026-11-18 最新） |
| `RealmRaid` | 1 | 突破券数量上限校验（`eb156b16`） |
| `DailyTrifles` | 1 | 商店签到导航与商城识别（`ad778fba`） |

## 6. 框架与 UI 能力对比

| 能力 | 本地 | 上游 | 结论 |
| --- | --- | --- | --- |
| 自定义流程编排 | `module/flow`（schema/rules/runtime/codegen/store）+ 标注器 `flow.html/js` 单步调试 + 生成可调度任务 | 无 | **本地领先** |
| 多实例协同 | `module/team_flow`（MQTT） | `DraftDuel/cooperation` 心跳接入调度（`ed25cc79`） | 本地有底座，上游做了调度集成 |
| 通知 | `module/notify`（onepush） | 看门狗 + Apprise（`50dec6ce`、`d389f83a`） | 各有实现，上游多「看门狗」 |
| 识别框架 | 无 `RuleFrame` | `RuleFrame` + 灰度匹配（`92bb2f2e`）、掩码匹配（`8753481b`）、`roi_pad` 容差 | 上游领先 |
| OCR 引擎 | `ppocr-onnx==0.0.3.9` | paddleocr 3.7.0（PP-OCRv5 + ONNX Runtime） | 上游在迁移中，需评估稳定性 |
| 桌面端 | 已支持（`module/device/desktop_device.py`、`desktop_impl.py`） | 桌面端加固：PID 复用误杀、多开竞态、`press_and_drag` 走 `window_message` | 本地有功能，上游补了边界修复 |
| 诊断工具 | 无 | `/tool/doctor` 一键体检（`5db01e76`） | 上游领先 |
| 统计/日志 | 无独立模块 | 移植统计/日志模块（`50dec6ce`） | 上游领先 |
| 调度白名单 | 已含超鬼王门票（本地已有） | `d2feec52` 同类修复 | 已追平 |

## 7. 建议

1. **不要整体切换上游**：会丢掉 `flow`、超鬼王祸主降临/协战、`Chess` 本地改造、`RichMan` 整合与 `MetaDemonTicket`。
2. 按「功能覆盖优先」，性价比排序：
   1. 起号套件 4 任务（新增功能面最大、风险最低）
   2. LBS + 狭间幻境 + 青蛙挑战（3 个独立活动任务，可按 lgg686 逐条 cherry-pick）
   3. 鼬商店礼盒 + 武道大会首领战（小补丁，补齐现有任务）
   4. 协同对弈 `DraftDuel`（大工程，建议单独立项，复用本地 `team_flow`）
   5. 稳定性批（`FrogBoss`/`WantedQuests`/`Chess`/`GameUi` 的 fix 类提交，按台账逐簇立项）
3. 框架类（`RuleFrame`、`/tool/doctor`、看门狗、paddleocr 3.7）建议单独评估，不与任务移植混在同一批。

## 8. 口径与风险说明

- 本报告为**静态代码 + 台账**分析，未实跑验证；「能跑通」需另行回归测试。
- `kongdr` 的 2026-11-14 系列（`50dec6ce`、`56529f78`、`26e67b73`）含第三方依赖/引擎级改动，与本地 `ppocr-onnx` 技术栈不同，不能直接 cherry-pick。
- `applied` 列表（55 条）与 `git cherry` 等价集在本地不可靠，请以 `dev_tools/upstream_sync_log.md` 台账为准。
- 新增的 `pinkpig-Peppa/master` 与 nearaura 高度同源，本轮未提供本地缺失的独有任务。

## 9. 增量复审（2026-11-20）

重新 `fetch` 5 源后的增量结果（基准 = 本报告 11-18 采样时的各源 tip）：

| 源 | 11-18 tip | 11-20 tip | 新增 |
| --- | --- | --- | --- |
| nearaura/master | `48f34cb0` | `48f34cb0` | 无 |
| nearaura/dev | `ac712acc` | `bb6f2103` | `bb6f2103` 突破券 OCR 区域收窄 |
| kongdr418/mine | `f4bf42bc`（本地 ref 当时仅到 `838d4b7c`） | `f4bf42bc`（ref 已补齐） | 无新提交；`95b75dd8`、`5db01e76` 现已可取 |
| lgg686/self | `761614dc` | `0f99fd02` | `0f99fd02` 恢复突破券 OCR 区域 |
| pinkpig-Peppa/master | `aff78b2c` | `aff78b2c` | 无 |

判定：

- 新增改动只有一类，但三源**不是同一补丁**：`f4bf42bc` 只改 `base.py`（`_META` → 常规）、`bb6f2103` 只改 ROI（`realm_raid_number1` 收窄为 `923,16,74,25`）、`0f99fd02` 改 `base.py` + ROI + MetaDemon 入口模板，patch-id 各不相同。
- 本地没有 `_META` 变体，`base.py` 部分无法直接套用；只有 `bb6f2103` 的纯 ROI 改动可干净合并。本地已有 `0 <= cu <= total == 30` 校验，OCR 误读会被丢弃，本轮**暂不移植 ROI**。
- 第 1~8 节的缺口结论不变；候选提交池从 242 条（过滤后）更新为 **311 条**（当前 `fetch` 统计，含跨源去重与已在本地内容过滤）。
