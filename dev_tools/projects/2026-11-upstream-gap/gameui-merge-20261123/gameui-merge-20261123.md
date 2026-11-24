# GameUi 模块上游整合评估（2026-11-23）

> 口径：本地基线 `czr @ eae565ee8`；上游 7 源（runheng/gitee master+dev、kongdr418 mine、lgg686 self、pinkpig-Peppa master、oYe486 master、Shu_Li_x mine），均取本地已 fetch 的 `refs/remotes/*`。
> 结论先行：**不做整体整合**。本地 GameUi 已是「mine 系导航 + 本地增强」的分叉版本，上游差异以素材 / ROI / 页面注册为主；推荐按点移植 1 条故障恢复补丁，另有 3 条留待实机评估，其余不采纳或已覆盖。
> HTML 呈现层：[gameui-merge-20261123.html](gameui-merge-20261123.html)。

---

## 1. 是否有必要整合：核心文件已分叉，整体替换会回退本地能力

| 文件 | 本地 czr | runheng/master | lgg686/self | oYe486/master | 判定 |
|---|---:|---:|---:|---:|---|
| `navigator.py` | 775 | 740 | 719 | 709 | 所有源内容哈希互不相同；本地独有「未知页连续 5 次失败强制重启」「跨边失败累计」「闲庭页」 |
| `default_pages.py` | 345 | 308 | 483 | 479 | 各方页面注册集合不同（本地有闲庭/庭院事务/棋局；上游有活动页/现世逢魔/摸鱼/阵容助手） |
| `page.py` | 123 | 121 | 133 | 252 | 本地= kongdr=ShuLi；runheng/pinkpig 另一版；oYe486 重写版 |
| `assets.py` | 225 | 209 | 242 | 316 | 7 源 7 个哈希，全部不同 |
| `game_ui.py` | 16 | 16 | 15 | **478** | oYe486 把运行层搬进 facade，属架构级分叉 |
| `registry.py` | 28fc5ac | 28fc5ac | **8438ecc** | 8438ecc | lgg686/kongdr/oYe486/ShuLi 含退化 `("page")`（本地已修为 `("page",)`） |

核心判定依据：

1. **本地导航能力上游没有**：`UNKNOWN_PAGE_FORCE_RESTART_THRESHOLD`、失败计数跨边累计（本地 `f078e039`）、`accepted_pages`（本地 `ff3e23ce`）、闲庭独立页（本地 `87055ee5`）。上游 runheng 的 `navigator.py` 仍是「失败计数换边归 1」的旧逻辑。
2. **上游差异集中在素材与页面注册**：runheng/master 未同步的 GameUi 提交中，绝大多数是 ROI / 模板 / 页面注册（六道、逢魔现世、摸鱼、活动），不是框架缺陷修复。
3. **oYe486 是另一套框架**：`RuleImage(file=..., path=...)` 拆分、`common/` `res/` `win_false/` 分目录、`page_img*.json` 拆分、`game_ui.py` 478 行。整体引入等于把本地再分叉一次。
4. **lgg686 存在退化**：`registry.py` 的 `("page")` 会让目录注册退化为按字符遍历；其 `assets.py` 全量加 `profile="High"`，需要识别层配套改造，收益未验证。

> **推荐**：GameUi 只做「按点移植 + 本地补强」，不整体合并任一上游的 `tasks/GameUi`。

---

## 2. 冲突簇清单（跨源同位置修改）

| # | 标签 | 冲突点 | 上游各源做法 | 本地现状 | 推荐 | 证据 |
|---|---|---|---|---|---|---|
| 1 | 不做 | 是否整体替换 GameUi 框架 | runheng 与本地同源但落后；lgg686/oYe486 各自分叉 | 本地已是增强分叉 | 不整体整合 | §1 哈希与行数 |
| 2 | 不做 | oYe486 架构迁移（`res/` `common/` `win_false/` `page_img*.json`） | oYe486 独有 | 本地目录结构稳定 | 不采纳 | `git diff czr refs/remotes/oYe486-master/master -- tasks/GameUi` 149 文件 / +2855 |
| 3 | P3 | 商店页识别 | 本地：普通/紫色/灯笼三招牌；runheng `eddc6171a` 双招牌（本地已覆盖）；ShuLi `efdea405a` 改用左下建筑 `8,550,140,72`；oYe486 改主招牌 + `page_check_mall_2.png` | `I_CHECK_MALL`+`I_CHECK_MALL_PURPLE`+`I_CHECK_MALL_LANTERN`，`page_mall = any_of(3)` | 保留本地三招牌；可选把 ShuLi 左下建筑做成第 4 候选（需裁模板 + 实机） | `tasks/GameUi/default_pages.py` 124-125；ShuLi `efdea405a` |
| 4 | 不做 | 庭院主页识别（换皮 / 镜头偏移） | 本地：`not_(I_CHECK_MAIN_SET)` + `I_CHECK_MAIN` 或「图鉴/商店/每日」三图标兜底；pinkpig `cf7e8a50a`：式神录+阴阳术双 HUD；oYe486：入口交叉定位；runheng：单 `I_CHECK_MAIN`（0.95） | 三图标兜底 + 闲庭独立页 | 保留本地，等价方案已覆盖 | `default_pages.py` 65-85；pinkpig `cf7e8a50a` |
| 5 | 不做 | 探索标识 ROI | runheng 2026-05~08 连续把 `roi_back` 收窄到与 `roi_front` 相同 | `I_CHECK_EXPLORATION` 保留外扩 `(1138,134,56,50)` 偏移容错 | 不采纳收窄（会降低横向偏移容错） | `assets.py` `I_CHECK_EXPLORATION`；本地上游批次 43 回归测试 |
| 6 | P2 | 百鬼棋局退出确认弹窗变体 | oYe486 `7975b037e` 新增 `page_chess_exit_confirm_alt.png` 与 `image_chess.json`，随后 `725baa1a0` 废弃 alt、直接替换 `page_chess_exit_confirm.png`；lgg686 `40e2f5278`/`40cea8653` 整体棋局更新 | 本地棋局 mixin + 结算未知页恢复（`43a56be5`） | **已修复，待实机验证后合并**：2026-11-24 实机诊断定位旧 confirm 素材偏移 5~7px、ROI 无搜索余量，弹窗已出现却识别失败，19s 内连点 `PAGE_CHESS_EXIT` 10 次触发 `GameTooManyClickError`；按 `725baa1a0` 换素材（离线复核 0.155→0.9995），confirm/cancel 的 `roi_back` 各扩 16px，分支 `staging/20261124-chess-exit-confirm` | oYe486 `7975b037e`/`725baa1a0`；2026-11-24 `log/error/少时之约(笔记本)_1795451256348` |
| 7 | 不做 | 六道页面注册位置 | runheng 在 GameUi 注册 `page_check_six_gates` / `six_gates_jue` / boss；本地在 `tasks/SixRealms` 注册月海/孔雀/香境/季鸣/净佛/真言/神龛 | SixRealms 模块自管页面 | 不引入 GameUi 版（重复注册 → 优先级/误判风险） | `tasks/SixRealms/page.py`；runheng `12eaff8bc`/`9d120ecd8` |
| 8 | 不做 | 现世逢魔 / 摸鱼页注册 | runheng 在 GameUi 注册 `page_demon_encounter_realworld`、`page_touch_fish` | 现世逢魔在 `tasks/DemonEncounter/page.py`；摸鱼在 `tasks/WeeklyTrifles/page.py` | 已覆盖，不重复注册 | `DemonEncounter/page.py` 7-12；`WeeklyTrifles/page.py` 32-41 |
| 9 | 不做 | 活动页 / 活动总览 / 阵容助手 / 协斗导航 | lgg686 `default_pages.py` +175 行（`page_activity`、`page_lineup_helper`、`page_chess*`、`I_DRAFT_DUEL`） | 无同名页面；协斗按 backlog `C*` 单独立项 | 不整合，随 DraftDuel 立项处理 | lgg686 `default_pages.py` 函数级 diff |
| 10 | P1 | 卡死 / 未知页失败后强制先跑 Restart | pinkpig `cf7e8a50a`：`script.py` 增加 `_force_restart`，避免过期任务抢占 Restart | 本地 `script.py` 无 `_force_restart`，空闲期 GotoMain 失败后仍可能静默等到下个任务 | **建议移植**（1 文件、可加单测） | `script.py` 无匹配；pinkpig `cf7e8a50a` |
| 11 | 不做 | 未知页关闭动作顺序 + 强制重启阈值 | runheng：`BACK_RED` 在前、无强制重启；本地：`CONFIRM` 在前 + 连续 5 次失败重启 | 本地顺序经实机验证，且有重启兜底 | 保留本地 | `navigator.py` 44-47；本地 `73c1bfb9` |
| 12 | 不做 | 资产参数全量 `profile="High"` | lgg686 全量加 profile | 本地 `RuleImage` 无该参数用法 | 不采纳（需识别层改造，收益未证） | lgg686 `assets.py` |
| 13 | 不做 | `registry.py` 目录名元组 | lgg686/kongdr/oYe486/ShuLi 写成 `("page")` | 本地为 `("page",)` | 不采纳（上游退化 bug） | `registry.py` 82 |
| 14 | 不做 | `game_ui.py` 调试入口 | lgg686/kongdr/ShuLi 改 `Config("oas2")` 与 `page_main`；oYe486 重构 facade | 本地 16 行门面 | 不采纳 | `game_ui.py` |
| 15 | P3 | 町中固定位置保底点击是否移除 | lgg686 `431e3458` 及 lgg686/oYe486 `navigator.py` 均删除该保底 | 本地保留 `TOWN_FALLBACK_*` | 暂保留；若实机出现误点再移除 | `navigator.py` 546/765；lgg686/oYe486 navigator diff |

---

## 3. 推荐执行顺序

1. **P1（立即可做）**：移植 pinkpig `cf7e8a50a` 的 `script.py` 部分（`_force_restart` + 空闲期 GotoMain 失败就地 Restart）。`default_pages.py` 部分本地已有等价兜底，不重复引入。补 1 个单测覆盖「失败任务 next_run 更早时仍先跑 Restart」。
2. **P2（需实机）**：棋局退出确认 alt 变体（oYe486 `7975b037e`），在棋局开放时抓图比对，只加素材与规则，不动导航。
3. **P3（需实机）**：商店第 4 候选（ShuLi 左下建筑）与町中保底是否移除，均以实机日志为准，不做代码预改。
4. **其余 11 条**：不采纳或已覆盖，登记后不再重复评估。

---

## 4. 与总账 / backlog 的关系

- 本文是 `upstream-full-compare-20261122` 总账的 GameUi 专项展开，不替代总账；总账 §9 追加指针。
- backlog `D5 GameUi` 由「9 条待办」收敛为「1 条 P1 + 1 条 P2 + 2 条 P3 + 11 条不采纳/已覆盖」。

## 5. 更新记录

| 日期 | 变更 | 来源 |
| --- | --- | --- |
| 2026-11-23 | 首次建立 GameUi 专项评估：7 源哈希/行数对比 + 15 条冲突簇判定 | 只读分析，无代码改动 |
