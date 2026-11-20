# 缺口清单（Backlog）

配套文档：[立项书](README.md) · [对比报告](upstream_feature_gap_20261118.md)

状态：`待办` / `进行中` / `待实机验证` / `已完成` / `搁置`

## 进度快照（2026-11-20）

- **已完成移植、待实机验证**：`B1` 鼬金币商店礼盒、`A7` 青蛙瓷器挑战赛、`A5` LBS 鬼王。
- **已完成评估、未动代码**：`E1` RuleFrame（结论：不整套引入）。
- **未开始**：`A1`~`A4`、`A6`、`B2`、`C1`~`C4`、`D1`~`D6`、`E2`~`E5`。
- **下一会话建议顺序**：`A6` 狭间幻境 → `A2` 探索推进 → `B2` 武道大会首领战。
- **另一立项**：`dev_tools/projects/2026-11-custom-flow/` 的 M1~M5 全部未做，设备已在线，可随时开始实机冒烟。
- **新增约束**：本地上游 ref 中 `kongdr418-mine/mine` 只到 `838d4b7c`（11-15），`f4bf42bc`、`5db01e76`、`95b75dd8` 未拉到；做 `E2`/`E5` 或探索 OCR 修复前需要先 fetch。
- **本轮结果（A5 LBS 鬼王）**：按 lgg686 `ad15a023`/`188dee7c`/`a1fb24a6`/`f01a83f0` 移植 `tasks/LBS`（17 文件，单人/组队匹配/开车三模式）；`GeneralRoom` 建房/权限/确认方法支持传入任务自有弹窗资产，`GeneralInvite.exit_room` 确认弹窗等待 0.8s→1.8s；已注册 config_model / config_menu / config_manual / template.json / i18n。离线回归 `tests/test_lbs_port.py` 10 例通过；全量 `505 passed / 10 failed`（10 个均为既有失败：HeroTest Timer、switch_onmyoji、dailytrifles income）。未实机验证、未提交。

## A. 新功能（M1 / M2）

| ID | 能力 | 来源 | 关键上游提交 | 规模 | 依赖 | 验收要点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | 自动剧情 `AutoStory` | kongdr418 / lgg686 | `547dfba6`、`3a8ba22f` | 24 文件 | 新手引导兼容 | 可连续推进剧情至章节结束 | 待办 |
| A2 | 探索推进 `ExplorationFight` | kongdr418 / lgg686 | `fc45a500` | 约 10 文件 | 复用 `GeneralBattle` | 支持章节区间与稀有度选择 | 待办 |
| A3 | 借用式神 `BorrowShikigami` | kongdr418 / lgg686 | `628c0cfb` | 约 15 文件 | A1/A2 | 完成借用并进入探索 | 待办 |
| A4 | 自定义任务 `CustomTask` | kongdr418 / lgg686 | `80751206` | 约 8 文件 | 与本地 `CustomFlow` 划清边界 | 支持用户自定义步骤序列 | 待办 |
| A5 | LBS 鬼王 | lgg686 | `ad15a023`、`188dee7c`、`a1fb24a6`、`f01a83f0` | `tasks/LBS` 17 文件 | 无 | 单人/组队匹配/开车三模式可切换；配置项 `lbs`；离线回归 `tests/test_lbs_port.py` 10 例通过 | 待实机验证 |
| A6 | 狭间幻境 `IbukiArena` | lgg686 | `5bc76c7e`、`c2390c2a` | 14 文件 | 御魂切换 | 单人战斗可完成一轮 | 待办 |
| A7 | 青蛙瓷器挑战赛 `FrogChallenge` | lgg686 | `1f230af2` | 已移植到 `tasks/FrogChallenge`，配置项 `frog_challenge`；骰子进度实时识别 + 无奖励/无进度保护；离线回归 `tests/test_frog_challenge_port.py` 8 例通过 | 待实机验证 |

## B. 现有任务补齐（M3）

| ID | 能力 | 来源 | 关键上游提交 | 说明 | 状态 |
| --- | --- | --- | --- | --- | --- |
| B1 | 鼬金币商店礼盒 | lgg686 `WeeklyPurchase/ItachiCoinShop` | `05fca68a` | 已移植到 `tasks/RichMan/itachi_shop.py`，配置项 `itachi_coin_shop.itachi_coin_buy_jade`；离线回归 `tests/test_richman_itachi_coin_shop.py` 9 例通过 | 待实机验证 |
| B2 | 武道大会首领战 | lgg686 `MartialArts` | 模块整体 | 本地为门票+体力，需补 `boss_limit` 阶段 | 待办 |

## C. 协同对弈（M4）

| ID | 能力 | 来源 | 关键提交 | 说明 | 状态 |
| --- | --- | --- | --- | --- | --- |
| C1 | 对战大厅与邀请 | kongdr418 / lgg686 | 见报告第 4 节 | 消耗识别、邀请好友、队长/队员 | 待办 |
| C2 | 自动选人 | 同上 | 阵容矩阵评分 + 火系名单 | 可配置权重 | 待办 |
| C3 | 双端协同接入 | 同上 | `ed25cc79` 等 | 复用本地 `module/team_flow`（MQTT），不引入第二套框架 | 待办 |
| C4 | 训练模型与对局记录 | 同上 | 训练脚本 + 记录 | 可选能力，先留接口 | 待办 |

## D. 稳定性批次（M5）

按模块分批立项，每批一个提交，便于回滚。数量为台账过滤后的真实待决策数。

| 批次 | 模块 | 条数 | 代表问题 | 状态 |
| --- | --- | --- | --- | --- |
| D1 | MetaDemon | 19 | 上供自定义星级、召唤顺序、双端协同、新 UI 识别 | 待办 |
| D2 | FrogBoss | 15 | 下注确认遮挡死循环、零权重随机、失败素材 | 待办 |
| D3 | WantedQuests | 13 | 新版封印悬赏 UI、目标子串匹配、追踪按钮范围 | 待办 |
| D4 | Chess | 9 | 手牌满出售腾位、随机投掷、OCR v6-small | 待办 |
| D5 | GameUi | 9 | 探索标记偏移容错、庭院阈值、町中保底点击 | 待办 |
| D6 | GeneralBattle / Duel / SixRealms / Exploration / RealmRaid / DailyTrifles | 14 | 魂魄溢出点击、斗技识别资源、月之海识别、突破券 OCR 区域 | 待办 |

## E. 框架能力（M5 评估项）

| ID | 能力 | 来源 | 关键提交 | 结论 | 状态 |
| --- | --- | --- | --- | --- | --- |
| E1 | `RuleFrame` 识别框架 | nearaura 系 | `92bb2f2e`、`8753481b`、`7c5f380b` | 需评估与本地识别层兼容性 | 待办 |
| E2 | `/tool/doctor` 体检 | kongdr418 | `5db01e76` | 独立工具，可后置 | 待办 |
| E3 | 看门狗 + Apprise | kongdr418 | `50dec6ce`、`d389f83a` | 本地已有 onepush，需评估是否并存 | 待办 |
| E4 | OCR 引擎升级 | kongdr418 | `56529f78`、`26e67b73` | 与本地 `ppocr-onnx==0.0.3.9` 技术栈不同，隔离评估 | 待办 |
| E5 | 绘卷查询 `module/scrolls` | kongdr418 | `95b75dd8`、`92ada2c7` | 查询工具，非任务，优先级低 | 待办 |

## F. 排除项

| 项 | 原因 |
| --- | --- |
| 整体切换到 lgg686 / kongdr 分支 | 会丢失 `flow`、超鬼王祸主降临/协战、Chess 改造、RichMan 整合 |
| 直接 cherry-pick 引擎/依赖级提交 | 与本地技术栈冲突，需单独评估 |
| 移植 nearaura 的 `General` 目录 | 2023 年遗留，无实际功能 |
