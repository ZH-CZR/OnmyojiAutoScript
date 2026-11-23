# 本地 czr 与上游 5 源功能差距对比报告

- 初版：2026-11-18（文件名保留初版日期，内容原地更新，不另起报告）
- 最近更新：2026-11-23　对比窗口：2026-09-18 → 2026-11-23
- 对比基准：本地 `czr` @ `e9703b9a`（2026-11-23）
- 数据源：`dev_tools/upstream_sources.json` 中全部 5 源（数组序 = 优先级）
- 判定口径（用户指定）：**功能覆盖优先**，其次看已有任务行为差异、稳定性修复、框架/UI 能力
- 数据方法：
  1. `python dev_tools/upstream_sync.py fetch` 拉取 5 源到 `refs/remotes/<slug>/<branch>`（2026-11-23 刷新）
  2. 跨源按 patch-id 去重、过滤内容已在本地者后，候选 **324 条**（11-20 为 311 条）
  3. 各源能力用 `git ls-tree` / `git show <ref>:module/config/config_model.py` / `git grep` 逐项核验，不凭旧报告推断
  4. 任务集合以 `module/config/config_model.py` 的 `ConfigModel` 注册键为准（`config/template.json` 是旧模板，缺新任务键，不能作为注册依据）

## 1. 结论速览

| 维度 | 结论 |
| --- | --- |
| 功能覆盖数量 | `lgg686/self`（65 个注册任务） > **本地（64）** = `kongdr418/mine`（64） > `nearaura`/`pinkpig`（56） |
| 本地真正缺的**新任务** | 协同对弈 `DraftDuel`；起号套件的 `AutoStory`/`ExplorationFight`/`CustomTask`；借用式神 `BorrowShikigami`（仅 kongdr） |
| 本地缺的**小功能** | 武道大会「首领战」阶段（lgg686 `MartialArts.boss_limit`，已进 `staging/20261120-mt-boss` 待实机）；绘卷查询 `module/scrolls`（kongdr） |
| 2026-11-18 后**已补齐** | LBS 鬼王（`304ed49b`）、狭间幻境（`c91b9021`）、青蛙瓷器挑战赛 + 鼬金币商店（`2c7a95b3`），均已在 `czr` |
| 本地**独有** | 自定义流程编排 `module/flow` + `CustomFlow` 任务 + 标注器 flow 页面（上游全无）；超鬼王祸主降临 `ChaoGuiWang`/`ChaoGuiWangAssist` |
| 框架差异 | RuleFrame 识别框架（kongdr、lgg686 有，本地无）；OCR 引擎 lgg686 已迁 paddleocr 3.7.0，本地与 kongdr 仍为 `ppocr-onnx==0.0.3.9` |
| **谁更好用** | 单纯论「功能种类」：`lgg686/self` 覆盖最广；但本地在自定义流程、超鬼王专项、RichMan 采购整合上不可替代。**结论：不换仓库，定向移植缺口** |
| 真实待决策提交 | 324 条（跨源去重、过滤已同步内容；fix 192 / feat 91 / refactor 23 / 其他 18） |

> 说明：`list` 返回的 `applied` 不可靠——本地做过冲突取舍或自检补正的提交 patch-id 会变，会被重新列为待同步。本报告以**台账** `dev_tools/upstream_sync_log.md` 为准做过滤。

## 2. 各源基本情况

| 源 | 分支 | tip | 日期 | 注册任务 | 9-18 起本地未含提交 | 特点 |
| --- | --- | --- | --- | ---: | ---: | --- |
| 本地 `czr` | — | `e9703b9a` | 2026-11-23 | 64 | — | 含 flow、超鬼王、RichMan、武道大会门票+体力 |
| nearaura | master | `67493454` | 2026-11-22 | 56 | 264 | 与 dev 同源；任务集合是本地子集，武道大会为 `BudokaiTournament`（门票爬塔） |
| nearaura | dev | `fe65e54b` | 2026-11-22 | 56 | 257 | 本地长期主参考源 |
| kongdr418 | mine | `f4bf42bc` | 2026-11-18 | 64 | 131 | 独有：协同对弈、起号套件（含借用式神）、绘卷查询；含未验证依赖升级 |
| lgg686 | self（Gitee） | `43339741` | 2026-11-21 | 65 | 164 | 独有：每周采购、武道大会首领战、起号套件（无 BorrowShikigami）；近期推进 Web 控制台/Android 适配 |
| pinkpig-Peppa | master | `aff78b2c` | 2026-11-15 | 56 | 255 | 与 nearaura 高度同源（新增参考源） |

> 「9-18 起本地未含提交」= `git rev-list --count --since=2026-09-18 <ref> --not czr`，**未跨源去重**，仅表示各源相对本地的提交规模；跨源去重后的真实候选为 324 条。

## 3. 任务覆盖矩阵（只列有差异的项）

图例：✓ 有；✗ 无；~ 有同类实现但范围不同；— 不适用

| 能力 | 本地 | nearaura | kongdr418 | lgg686 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 协同对弈 `DraftDuel` | ✗ | ✗ | ✓ | ✓ | 双实例协同、自动选人评级、训练模型、对局记录；kongdr 70 文件 / lgg686 121 文件 |
| 自动剧情 `AutoStory` | ✗ | ✗ | ✓ | ✓ | 起号套件之一，kongdr 24 文件 / lgg686 23 文件 |
| 探索推进 `ExplorationFight` | ✗ | ✗ | ✓ | ✓ | 可配章节区间、自动旋转、稀有度选择 |
| 借用式神 / 15 级起号 `BorrowShikigami` | ✗ | ✗ | ✓ | ✗ | 剧情→借用→探索→经验妖怪，最终校验 15 级；仅 kongdr 有独立任务（21 文件），lgg686 未包含 |
| 自定义任务 `CustomTask` | ✗ | ✗ | ✓ | ✓ | 与本地 `CustomFlow` 定位相近但实现不同 |
| LBS 鬼王限时活动 | ✓ | ✗ | ✗ | ✓ | 本地已于 2026-11-20 移植（`304ed49b`）；单人 / 组队 / 开车模式 |
| 狭间幻境 `IbukiArena` | ✓ | ✗ | ✗ | ✓ | 本地已于 2026-11-20 移植（`c91b9021`）；伊吹之擂单人战斗 |
| 青蛙瓷器挑战赛 `FrogChallenge` | ✓ | ✗ | ✗ | ✓ | 本地已于 2026-11-19 移植（`2c7a95b3`）；与本地对弈竞猜 FrogBoss 不同 |
| 绘卷查询 `module/scrolls` | ✗ | ✗ | ✓ | ✗ | 绘卷进度 / 排行榜 / 碎片库存查询工具，适配 Linux 与 redroid；20 文件 |
| 鼬金币商店 `ItachiCoinShop` | ✓ | ✗ | ✗ | ✓ | 本地已并入 `RichMan/itachi_shop.py`（`2c7a95b3`）；lgg686 在 `WeeklyPurchase` 内 |
| 每周采购 `WeeklyPurchase` | ~ | ✗ | ✗ | ✓ | 本地 `RichMan` 已整合鼬商店等采购；lgg686 为独立任务（156 文件） |
| 武道大会 | ~ | ~ | ✓ | ✓ | 本地：门票+体力，首领阶段在 `staging/20261120-mt-boss` 待实机；nearaura：`BudokaiTournament` 门票爬塔；kongdr：`MartialTournament`；lgg686：`MartialArts`（体力+首领 `boss_limit`） |
| 百鬼棋局 `Chess` | ✓ | ✗ | ✓ | ✓ | 文件规模：本地 389 / kongdr 816 / lgg686 462 |
| 超鬼王祸主降临 `ChaoGuiWang` | ✓ | ✗ | ✗ | ✗ | 本地独有（另有协战 `ChaoGuiWangAssist`） |
| 超鬼王门票 `MetaDemonTicket` | ✓ | ✗ | ✓ | ✓ | 本地与 kongdr、lgg686 各有实现 |
| 自定义流程 `flow` + `CustomFlow` | ✓ | ✗ | ✗ | ✗ | 本地独有框架能力 |
| 美术工坊 `GuguArtStudio` | ✓ | ✗ | ✓ | ✓ | — |
| 采购整合 `RichMan` | ✓ | ✓ | ✓ | ✗ | lgg686 用 `WeeklyPurchase` 替代 |

**要点**

- `nearaura/master + dev` 与 `pinkpig-Peppa/master` 的任务集合基本是**本地子集**；唯一差异是武道大会实现（`BudokaiTournament` 门票爬塔 vs 本地 `MartialTournament` 门票+体力）及 `General`/`OrochiMoans` 占位。
- 真实功能缺口集中在 `kongdr418/mine`（协同对弈、起号套件、借用式神、绘卷查询）与 `lgg686/self`（协同对弈、起号套件、每周采购、武道大会首领战）。
- 本地独有能力（flow、祸主降临、RichMan 整合）没有任何上游可以替代。

## 4. 本地缺的新功能（按性价比排序）

### P1 起号套件（kongdr 4 个任务）
- 组成：`AutoStory`、`ExplorationFight`、`BorrowShikigami`、`CustomTask`（lgg686 无独立 `BorrowShikigami`）
- 能力：自动过剧情 → 借用式神 → 探索推进 → 经验妖怪，循环直到账号 15 级；含新手弹窗/新手战斗页兼容
- 依据：`547dfba6`、`3a8ba22f`、`fc45a500`、`628c0cfb`、`80751206`
- 风险：与本地 `base_task`、新手引导流程耦合较浅，移植成本低

### P1 协同对弈 `DraftDuel`（最大单项缺口）
- 规模：kongdr 70 个文件、lgg686 121 个文件（2026-10-30 起）
- 能力：大厅消耗识别、邀请好友、队长/队员双端、自动选人（阵容矩阵评分 + 火系名单）、训练模型介入、真实对局记录、上阵拖拽
- 依赖：双实例协同。**本地已有 `module/team_flow`（MQTT）**，具备复用基础
- 风险：开放时段限制、头像识别阈值调优、双端时序，属于高投入高收益项

### P2 绘卷查询 `module/scrolls`（kongdr）
- 非自动化任务，是查询工具（官方资源解析 + 排行榜/碎片），需 `cryptography` 等依赖
- 依据：`95b75dd8`、`92ada2c7`；20 文件

### P3 武道大会首领战阶段（lgg686）
- 本地：门票 `pass` + 体力 `ap`；lgg686：体力 `ap` + 首领 `boss`（`boss_limit`，`run_sequence` 可配）
- 现状：移植已进 `staging/20261120-mt-boss`，自动化 5 passed、全量 520/10（既有失败），**待武道大会开放后实机验收**
- 结论：不需要新建批次，等活动开放补测后按闸门合并

### 已补齐（2026-11-18 后完成，不再列为缺口）
- LBS 鬼王：`304ed49b`（2026-11-20 merged）
- 狭间幻境 `IbukiArena`：`c91b9021`（2026-11-20 merged）
- 青蛙瓷器挑战赛 `FrogChallenge` + 鼬金币商店：`2c7a95b3`（2026-11-19 merged）

## 5. 同任务行为 / 稳定性差距

P1 首轮（批次 51，merge `79fa6925`）已落地 9 条：百鬼夜行画面外目标忽略、悬赏 2x 重扫/阈值放宽、MetaDemon 遗留奖励页接管、GeneralBattle 随机点击 ROI 微调、Login 等待 10s、协作忽略退化、契灵补邀 8s、FrogBoss 零权重回退、爬塔弹窗重试。下表为**仍在台账中的代表性缺口**。

| 模块 | 状态 | 代表性缺口（具体） |
| --- | --- | --- |
| `MetaDemon` | 部分已落地 | 上供自定义星级（`ea8e72f3`）、上供召唤顺序 + 中文显示（`7478e169`）、双端协同或独立好友上供（`fe19476d`）、`battle_boss` 迁移为 `battle_wait` 策略钩子（`5a752388`）、协同心跳等待与退出截图过期（`83b82fd5`）；新 UI 识别图/ROI 已落地 |
| `FrogBoss` | 部分已落地 | 下注确认被弹窗遮挡死循环（`9ec93a44`）、失败结果识别素材（`16d1205d`）；零权重随机下注已落地，结束标志遮挡问题已于 P0 修复（`7aa7e23d`） |
| `WantedQuests` | 部分已落地 | 新版封印悬赏 UI 适配（`b37b56d2`/`c4d40686`/`d296406e`）、目标改子串匹配避免漏判（`82fae57e`）、地点数量识别失败收紧区域重试（`df572d01`）、追踪按钮识别范围（`5ac08e11`）；2x 重扫/阈值放宽已落地 |
| `Chess` | 待排期 | 手牌满且无可操作时出售阵容卡腾位（`ce9903bf`）、无需御魂时等全员解锁后随机投掷（`45b5772d`）、买卡/换卡后清理格子点击记录（`8f945012`）、OCR 接入 v6-small（`5a8f7385`）、新版棋局策略与标注器（`5001c0bc`） |
| `GameUi` | 部分已落地 | 探索标记横向偏移容错 + 回归测试（`fd7e20a5`/`0b8ef1cb`/`b8624012`）、庭院标志阈值下调修复登录卡死（`03429729`）、町中保底点击（`9d39f0c0`）；百鬼夜行画面外目标已落地 |
| `GeneralBattle` | 部分已落地 | 魂魄溢出清理点击（`4a6ad558`）、退出战斗确认按钮新旧 UI 兼容（`e68b0b74`）、超鬼王门票 OCR 区域校准（`209f8fad`）；随机点击 ROI 已微调 |
| `Duel` | 待排期 | 斗技识别资源补齐 + 返回庭院函数修正（`9eea7c9d`/`bf893c0d`）、名士星数达标后延至下周一（`cf9eba73`） |
| `SixRealms` | 待排期 | 月之海岛屿漏识别与点击偏移（`f636e9d9`）、保留 OCR 已选岛屿（`043d3aa9`）、选岛自愈重读 + 宁息岛兜底（`03b5f1ef`，11-22 新） |
| `Exploration` | 已处理 | 突破券 OCR 区域已在 P0 收窄（本地 `3e1e7e7d`；上游 `bb6f2103` 各自实现） |
| `Hyakkiyakou` | 已处理 | 热力图无匹配时忽略画面外目标（本地 `bd05d91e`；上游 `4785e4bf` 各自实现） |

## 6. 框架与 UI 能力对比

| 能力 | 本地 | 上游 | 结论 |
| --- | --- | --- | --- |
| 自定义流程编排 | `module/flow`（schema/rules/runtime/codegen/store）+ 标注器 `flow.html/js` 单步调试 + 生成可调度任务 | 无（lgg686 仅有标注器 schema） | **本地领先** |
| 多实例协同 | `module/team_flow`（MQTT） | 各源均有 `module/team_flow`；协同对弈接入调度 | 各有实现 |
| 识别框架 | 无 RuleFrame（`module/atom` 无 `frame.py`） | kongdr、lgg686 有 `module/atom/frame.py`（RuleFrame + 灰度/掩码匹配、`roi_pad` 容差） | 上游领先 |
| OCR 引擎 | `ppocr-onnx==0.0.3.9` | lgg686 已迁 `paddleocr==3.7.0`（PP-OCRv5 + ONNX Runtime）；kongdr 仍为 ppocr-onnx | lgg686 领先，迁移需评估稳定性 |
| 桌面端 | 已支持（`module/device/desktop_device.py`、`desktop_impl.py`） | nearaura、lgg686 有；kongdr 无 desktop_device | 本地可用，需吸收边界修复 |
| 通知 | `module/notify`（onepush） | 当前 5 源 tip 中未找到 Apprise/看门狗实现（11-18 报告依据的提交已不在可查 ref 内） | 本地为主，无需移植 |
| 诊断工具 | 无 | 当前 5 源 tip 中未找到 `/tool/doctor`（早期提交 `5db01e76` 已不可见） | 不适用 |
| Web 控制台 | 有 web 页面 | lgg686 新增 `/gui` 条件挂载、提交历史、自动更新（`bd4614ac`~`43339741`） | lgg686 领先，可选评估 |
| Android 适配 | 无 | lgg686 新增 OASA 设备后端与热更（`17bb2993`~`12e61d99`） | 视需求评估 |

## 7. 建议

1. **不要整体切换上游**：会丢掉 `flow`、超鬼王祸主降临/协战、`RichMan` 采购整合与本地棋局改造。
2. 按「功能覆盖优先」，剩余性价比排序：
   1. 起号套件（`AutoStory`/`ExplorationFight`/`CustomTask`，kongdr 另有 `BorrowShikigami`）
   2. 协同对弈 `DraftDuel`（大工程，建议单独立项，复用本地 `team_flow`）
   3. 绘卷查询 `module/scrolls`（查询工具，按需）
   4. 武道大会首领战：等 `staging/20261120-mt-boss` 实机通过后合并，不另建批次
   5. 稳定性批（`Chess`/`Duel`/`SixRealms`/`GameUi` 的剩余 fix 类提交，按台账逐簇立项）
3. 框架类（RuleFrame、paddleocr 3.7、lgg686 Web 控制台/Android 适配）建议单独评估，不与任务移植混在同一批。

## 8. 口径与风险说明

- 本报告为**静态代码 + 台账**分析，未实跑验证；「能跑通」需另行回归测试。
- 注册任务数按 `ConfigModel` 的 `Field(...)` 键统计，各源若用不同注册方式会有 ±1 误差。
- `kongdr` 的 2026-11-14 系列（`50dec6ce`、`56529f78`、`26e67b73`）含第三方依赖/引擎级改动，与本地 `ppocr-onnx` 技术栈不同，不能直接 cherry-pick。
- `applied` 列表与 `git cherry` 等价集在本地不可靠，请以 `dev_tools/upstream_sync_log.md` 台账为准。
- 新增的 `pinkpig-Peppa/master` 与 nearaura 高度同源，本轮仍未提供本地缺失的独有任务。

## 9. 增量复审

### 2026-11-20

| 源 | 11-18 tip | 11-20 tip | 新增 |
| --- | --- | --- | --- |
| nearaura/master | `48f34cb0` | `48f34cb0` | 无 |
| nearaura/dev | `ac712acc` | `bb6f2103` | 突破券 OCR 区域收窄 |
| kongdr418/mine | `f4bf42bc` | `f4bf42bc` | 无新提交 |
| lgg686/self | `761614dc` | `0f99fd02` | 恢复突破券 OCR 区域 |
| pinkpig-Peppa/master | `aff78b2c` | `aff78b2c` | 无 |

### 2026-11-23

| 源 | 11-20 tip | 11-23 tip | 新增要点 |
| --- | --- | --- | --- |
| nearaura/master | `48f34cb0` | `67493454` | 合入 dev：GeneralInvite 好友页 ROI、SixRealms 选岛自愈、Hyakkiyakou 画面外目标、MetaDemon 疲劳召唤、CollectiveMissions 奖励超时 |
| nearaura/dev | `bb6f2103` | `fe65e54b` | 上述 5 条（`fe65e54b`/`03b5f1ef`/`4785e4bf` 等） |
| kongdr418/mine | `f4bf42bc` | `f4bf42bc` | 无新提交（11-18 后停滞） |
| lgg686/self | `0f99fd02` | `43339741` | Web 控制台 `/gui` 条件挂载/提交历史/自动更新、git 锁清理、Android 适配批次、OCR 档位环境变量、keep-alive 75s |
| pinkpig-Peppa/master | `aff78b2c` | `aff78b2c` | 无 |

判定：

- 本地已吸收本轮可直接复用的修复：GeneralInvite ROI 已在 P1 批次落地；SixRealms 选岛自愈（`03b5f1ef`）仍待排期；Hyakkiyakou 画面外目标已由本地 `bd05d91e` 等价实现。
- lgg686 本周新增集中在服务端/Web/Android/OCR，与本地上游同步主线（任务行为修复）不冲突，建议单独评估。
- 第 1~8 节缺口结论不变：本地剩余缺口为 `DraftDuel`、起号套件、`module/scrolls`，以及待实机的武道大会首领阶段。

## 10. 更新记录

| 日期 | 变更 |
| --- | --- |
| 2026-11-18 | 初版：5 源对比，矩阵 17 项，242 条待决策 |
| 2026-11-20 | 增量复审：3 源 tip 变化，候选池更新为 311 条，缺口结论不变 |
| 2026-11-23 | 全面复核：本地基准更新至 `e9703b9a`（64 任务），补齐 LBS/狭间/青蛙挑战/鼬商店，修正 BorrowShikigami、MetaDemonTicket、RichMan、Chess 规模等 4 处旧结论，新增框架项（Web 控制台/Android），候选池 324 条 |
