# 立项书：上游功能差距补齐（2026-11）

## 1. 基本信息

| 项 | 内容 |
| --- | --- |
| 项目名称 | 上游功能差距补齐 |
| 立项日期 | 2026-11-18 |
| 本地基准 | `czr` @ `4f53ebe0`（2026-11-17） |
| 状态 | 已立项，未开始实施 |
| 关联文档 | [对比报告](upstream_feature_gap_20261118.md) · [HTML 版](upstream_feature_gap_20261118.html) · [任务清单](backlog.md) |
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

完成后本地注册任务数应从 61 提升到 **66~67**，且 P1 功能有回归用例。

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

| 阶段 | 内容 | 交付物 | 验收 |
| --- | --- | --- | --- |
| M1 | 起号套件 4 任务 | `tasks/AutoStory`、`tasks/ExplorationFight`、`tasks/BorrowShikigami`、`tasks/CustomTask` | 配置可加载；15 级链路可跑通 |
| M2 | 活动任务三件套 | `tasks/LBS`、`tasks/IbukiArena`、`tasks/FrogChallenge` | 各自可独立调度；有回归用例 |
| M3 | 现有任务补齐 | RichMan 增加 `ItachiCoinShop`；武道大会增加首领战阶段 | 单项开关可验证 |
| M4 | 协同对弈 `DraftDuel` | `tasks/DraftDuel` + 复用 `team_flow` 双端协同 | 双实例可完成一局并按配置退出 |
| M5 | 稳定性批次 + 框架评估 | 按模块分组的 fix 批次；框架评估结论 | 每批独立提交、可回滚 |

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
