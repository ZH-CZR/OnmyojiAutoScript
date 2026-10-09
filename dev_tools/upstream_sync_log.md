# 上游同步记录（upstream sync log）

> 用途：记录每次从上游同步的**采纳 / 跳过 / 待决策**清单，保证换对话或换人接手时不必从头分析。
> 维护方式：每完成一批 → 在 §1/§2 追加行；新增的跳过项补进 §3；变化更新到 §4。
>
> ⚠ **重要提醒**：`upstream_sync.py list/advise` 的 `applied`（git cherry 等价集）对本地**不可靠**。
> 凡本地 cherry-pick 时做过冲突取舍或自检补正，patch-id 就与上游不同，会被再次列为待同步。
> 因此**以本文件为准**，`applied` 仅作参考。
>
> 工具与命令细节见 [`upstream_sync_doc.md`](./upstream_sync_doc.md)；项目约定见 `.trae/skills/upstream-sync/SKILL.md`。

---

## §1 批次总览

| 批次 | 日期 | 本地 merge commit | 来源 | 候选/落地 | 主题 |
|---|---|---|---|---|---|
| 0（已回退） | 2026-10-07 | `fc1fc355` → 回退 `a85dabdc` | runhey/dev | 14 / 0 | GeneralBattle 战斗等待重构；合并后无法启动，整体回退 |
| 1 | 2026-10-07 | `1c369fa1` | runhey/dev（`--since "2 months ago"`） | 11 / 5 | 低风险单模块（README / RichMan / RyouToppa / Costume） |
| 2 | 2026-10-07 | `aaed5d07` | runhey/dev | 2 / 2 | KekkaiActivation 多尺度收卡 + annotator 静态资源缓存 |
| 3 | 2026-10-07 | `46c8a8fd` | runhey/dev | 6 / 3 | GameUi 导航与庭院/好友识别（3 条已覆盖未合） |
| 4a | 2026-10-07 | （无落地） | runhey/dev | 5 / 0 | RichMan 商店组：4 条已覆盖/不适用，`c363395d8` 待决策 |
| 4b | 2026-10-07 | （无落地） | runhey/dev | 2 / 0 | base_task 竖屏防护：上游次日自我回退，净变更为零 |
| 4c | 2026-10-07 | `86a5b997` | runhey/dev | 5 / 4 | DemonEncounter 逢魔：挑战次数检测 + boss 搜索容错（1 条不适用） |
| 4d | 2026-10-07 | `f484e550` | runhey/dev | 3 / 3 | FrogBoss 对弈竞猜：记录页读取 + 下注恢复 + 负权重策略 |
| 5 | 2026-10-07 | `1951b0a6` | runhey/dev | 23 / 2 | 语义核实剩余候选：仅「契灵战斗判定」+「御魂整理 sk2~5 更换 ROI」可落地，其余已覆盖/不适用 |
| 6 | 2026-10-07 | `88798f14` | runhey/dev | 17 / 1 | 永生之海队长收尾无法结束任务修复；剩余大特性/框架链/CI 归类为「需立项 / 不适用」 |
| 7 | 2026-10-07 | `8b5c6fab`（手工移植，非 cherry-pick） | runhey/dev | 1 / 1 | RichMan 勋章商店售罄优雅收尾（`c363395d8`）；资产侧本地已有 `O_SOLD_OUT`，仅移植 `medal.py` 逻辑 + `back_mall` 超时保护 |
| 8 | 2026-10-07 | `7871ed52`（手工移植，非 cherry-pick） | runhey/dev | 2 / 2 | GeneralBattle `battle_wait` 链「取其精华」：排除式随机点击原子（`00888a40f`）+ 奖励详情浮窗检测（`eff487272`）；**不引入框架** |
| 9 | 2026-10-08 | `44b22f09` | xylolit-mu/self | 209 / 10 | **多源改造后首次实跑**：任务模块小修（Sougenbi/契灵 ROI、秘闻收尾、道馆连战、Chess 选符咒+拖拽）+ base_task 勾协弹窗与 minitouch 连接重建；同时 `ignore` 8 条净零/已覆盖 |
| 10 | 2026-10-08 | `1c34c37c` | xylolit-mu/self | 185 / 7 | 委派完成状态 ROI；狭间快速装配御魂并上阵 + 切换前关残余弹窗；逢魔灯笼按位置识别/事件入口超时 + 宝箱购买弹窗关闭确认；AreaBoss 筛选分类自动重开（手工移植）；GeneralInvite 挑战按钮阈值 0.8→0.7（手工移植） |
| 11 | 2026-10-08 | `87055ee5`（手工移植，非 cherry-pick） | xylolit-mu/self | 3 / 1 | 闲庭（独立庭院皮肤）识别：新增 `page_relax` + `I_CHECK_MAIN_SET`/`I_BACK_BROWN`，`page_main` 加 `not_(I_CHECK_MAIN_SET)` 排除误判（上游 `395fef27`+`a8afe598`，只取闲庭语义） |
| 12 | 2026-10-09 | `47f54223`（2 cherry-pick + 1 手工移植提交） | runhey/dev + xylolit-mu/self | 4 / 4 | 最近 7 天 dev/self 新增候选：Delegation 委派点击位置 + Navigator `accepted_pages`（cherry-pick）+ EvoZone 锁识别区 + 图像零方差拦截/多尺度浮点漂移（手工移植）；其余 8 条判为需立项/需实测/待决策 |

> 批次 0 说明：这批含 GeneralBattle `battle_wait` / `battle.py` 新框架，合并后脚本无法启动，
> 已用 `a85dabdc` 整体回退（删除 `battle_wait.py` 1631 行等）。**再动该链前必须重新做启动验证。**
>
> 「来源」列写法：`<owner>/<分支>`（如 `runhey/dev`、`runhey/master`、`xylolit-mu/self`）；
> 批次 0~8 均为**单源** `runhey/dev`。自**多源改造（§13.15）**起，同一批可能来自多个源，
> 跨源**同 patch-id 的改动已去重合并为一条**，此时记 `A + B`（两源都有）。

---

## §2 已合并提交明细

| 批次 | 上游 hash | 本地 hash | 类型 | 模块 | 标题 | 本地自检 / 取舍 |
|---|---|---|---|---|---|---|
| 1 | `368d5736` | `32800c7e` | docs | README | 修复 Star History 图表链接 | — |
| 1 | `42e0bb453` | `b21b3aac` | fix | RichMan | define sold-out OCR rule in ocr.json and regenerate assets | 与本地重复的 `O_SOLD_OUT` 已去重 |
| 1 | `40a349e46` | `61dc89d4` | fix | RyouToppa | 任务结束后返回庭院避免探索任务不开启加成 | `ui_goto` → `goto_page` |
| 1 | `9ec6101e` | `2307200a` | fix | RichMan | Handle bulk purchase failures in special shop | — |
| 1 | `c1dc50596` | `21989eed` | feat | Costume | Add Chinese names to costume switch logs | — |
| 1 | —（自检） | `a7021067` | fix | upstream-sync | 适配上游导航 API 与清理重复 OCR 规则 | RyouToppa `ui_goto`→`goto_page`；RichMan 去重 `O_SOLD_OUT` |
| 2 | `64dd5d904` | `f2ac8f53` | fix | KekkaiActivation | Retry harvesting expired cards before activation #1708 | — |
| 2 | `f4767278a` | `79269844` | fix | server | annotator 静态资源加 Cache-Control no-cache | — |
| 2 | —（自检，补窗口外 `6009a6e1`） | `ed4da8c1` | fix | upstream-sync | 补入 base_task/RuleImage 多尺度接口 | 新增 `RuleImage.match_multi_scale` / `BaseTask.appear_multi_scale` / `appear_then_click_multi_scale` |
| 3 | `3a6e56c28` | `ecb5dbaa` | fix | GameUi | 修复导航超时不抛异常及 registry 遍历 bug | registry `("page")`→`("page",)`，修复后注册 49 页 |
| 3 | `92223c5b5` | `e6f10c8a` | fix | GameUi | Restore I_CHECK_FRIENDS image and ROI for friend page detection | — |
| 3 | `606517be0` | `cbc7542e` | fix | GameUi | 适配庭院下移后的庭院标志识别区域 | 冲突取本地版，仅保留 `I_CHECK_MAIN` roi_back 61→74，丢弃上游夹带的导航移植噪声 |
| 4c | `7b329e3ea` | `911048b2` | feat | DemonEncounter | 逢魔之时增加今日挑战次数检测 | 冲突：保留本地 `goto_page(page_rwt)`，仅并入检测块 |
| 4c | `0450848ef` | `5eb02545` | fix | DemonEncounter | 调整逢魔 Boss 挑战次数识别区域 | 680,68,75,36 → 705,68,45,36 |
| 4c | `194a3eda2` | `d44975e9` | fix | DemonEncounter | 优化 boss 搜索容错、收缩灯笼点击区、补信件答谢 | `image.json` 冲突：保留本地 `de_to_real_world` 并追加 `de_box_center` |
| 4c | `7738d5d57` | `a39c73cb` | fix | DemonEncounter | 挑战次数 OCR 改为 DigitCounter 模式 | — |
| 4c | —（自检） | `1352f952` | fix | upstream-sync | 补齐 DemonEncounter 上游改动引用的本地接口与页面 | 导入 `GameStuckError` / `page_demon_encounter`；重进分支 `page_demon_encounter_realworld` → 本地 `page_rwt` |
| 4d | `86b2a7efd` | `0aa81e9f` | fix | FrogBoss | 更新活动素材与识别区域 | 多张 `fb/*.png` + ROI 刷新 |
| 4d | `98ce82bbf` | `6f9b99eb` | fix | FrogBoss | 同步记录页面与最新识别素材 | 新增 `I_FROG_LOG*` / `I_FROG_LAST_*` / `O_FROG_LAST_TIME` 与素材 |
| 4d | `670f194a0` | `2d1dbac0` | feat | FrogBoss | 移植记录补结算、下注恢复与负权重策略 | 新增 `record_reader.py`；`frog_oas` 策略改 `signed_win_rate`（v3）；`do_bet` 走 `confirm_bet` |
| 4d | —（自检） | `b9dd22b5` | fix | upstream-sync | 为 GeneralBattleAssets 补回 C_REWARD_1/2/3 结算关闭点击区 | 框架回退时丢失，`confirm_bet` 依赖 `C_REWARD_2` |
| 5 | `ccd7cf186` | `3c7e9bda` | fix | BondlingFairyland | 队员等待改用 is_in_battle 判断战斗场景 #1735 | — |
| 5 | `89ed887c6` | `899b795a` | fix | CostumeShikigami | 修复御魂整理 sk2/3/4/5 皮肤下不点击更换按钮 | sk2~5 `I_ST_REPLACE_*` roiBack 78×63 → 100×100（=roiFront，修复模板大于截图永不命中） |
| 6 | `c46802641` | `6759e56a` | fix | GeneralInvite | 永生之海队长打满次数后无法正常结束任务 | 冲突取并集：新增 `I_GI_SPEAK` 与本地 `I_I_ACCEPT_APPRENTICE` 并存（3 文件） |
| 7 | `c363395d8` | `8b5c6fab` | fix | RichMan | 勋章商店售罄时优雅结束，避免误点返回卡死 | 手工移植（非 cherry-pick）：`medal.py` 加 appear 前置判断 + `count_soldout()` 核对，保留本地 `money_ocr` 取值；`navbar.back_mall` 改本地 `ui_click_until_appear_or_timeout(timeout=15)`。资产侧 `O_SOLD_OUT` 本地已有，未重复引入；`_enter_medal` 的 `I_SIDE_SURE_MEDAL` 本地无 → 不适用 |
| 8 | `00888a40f` + `3dca54e1f` | `7871ed52` | feat | atom | 新增 `RuleClickExclude` 排除式随机点击原子 | 手工移植（非 cherry-pick），**只取 `module/atom/click.py`**：整屏取点排除若干 `roi_back`，`rejection`/`complement` × `uniform`/`normal`，附 `coord_in_excluded()`；`battle_wait.py`、`EvoZone`/`RyouToppa` 接入点属已回退框架 → 不引入 |
| 8 | `eff487272` + `00888a40f` | `7871ed52` | fix | GeneralBattle | 奖励结算页「物品详情浮窗」检测与关闭 | 手工移植（非 cherry-pick）：新增 `gw/gw_end_fix_1/2/3.png` + `gw/image.json` 源描述，`assets.py` 追加 `I_END_FIX_1/2/3`（**0.85**，含 eff487272 的素材/ROI/阈值更新）；`_handle_reward()` 随机点击前 `appear(I_END_FIX_*)` 命中即点 `C_REWARD_2` 并跳过本轮。`gw/click.json`/`click2.json`（活动奖励点击区）本地无对应活动战斗 → 不引入 |
| 9 | `a938c649` | `1b9c97e7` | fix | Sougenbi | 业原火 OCR 识别框 y 坐标下移 | 纯 ROI：贪 589,13→590,20、嗔 770,12→770,18、痴 951,12→944,18（`assets.py` + `s/ocr.json` 同步） |
| 9 | `7aee49c4` | `4cef0af9` | fix | BondlingFairyland | 契灵盘子识别范围扩大 | 纯 ROI：小 543,14,96,33→540,12,107,40；中 734,19,99,25→728,15,113,35；大 928,17,94,30→922,9,102,41；class 识别 roiBack 287,271,36,112→266,271,79,112（=roiFront） |
| 9 | `407544fe` | `6661c82b` + `0a2afa94`（自检） | fix | GlobalGame | 奖励页关闭点击范围改为已验证值 | roi_front 919,160→1048,195 / roi_back 72,107→1019,130；**自检**：丢弃上游夹带的 `"profile"` 字段（本地 click.json 契约为 {itemName,roiFront,roiBack,description}） |
| 9 | `1cda0166` | `dbb24038` | fix | WantedQuests | 秘闻结算后点空白返回挑战界面 | 新增 `_finish_secret_battle_reward()`，在战斗页分支内 `run_general_battle` 后调用；依赖的 `random_click` 本地已有 |
| 9 | `075f75bb` | `e5d61cda` | fix | AbyssShadows | 切换目标前优先补足同类数量 | 新增 `_completion_enemy_type` 追踪 + `get_next()` 前置补足分支；本地符号（`min_count`/`Code.get_enemy_type`/`AreaType`/`IndexMap`）齐备 |
| 9 | `3a2b74a3` | `e00d55fe` | fix | Dokan | 快速退出返回道馆后结束连战 | 新增 `_handle_missing_battle_page` 覆写（`_evaluate_exit_matcher` 命中即 EXIT_WIN/LOSE）；含 `test_battle_exit.py` 3 条单测，本地 `GeneralBattle` 同名方法契约一致 |
| 9 | `e88f4e2f` | `77b84efe` | fix | Chess | 次要羁绊只保留计数第二多一项 | `lineup_bond_context` 由 `2 < count < primary_count` 改为 `max(..., key=counts.__getitem__)` 取单一 `secondary_bond` |
| 9 | `e84779fb` | `fdf26b96` | feat | Chess | 按住拖动拟人化 | `Press_and_Drag` 默认 `hold_duration` 0.5→`(0.2,0.3)` 并经 `ensure_time` 归一；minitouch 按压带随机压力与 `random.randint(6,15)` 移动等待；`hand_operations.py` 6 处调用点同步改区间 |
| 9 | `40e4aa6f` | `f58172ba` | fix | base_task | 勾协弹窗优先清理并复核画面 | `screenshot()` 中 `self._burst()` → `while self._burst(): self.device.screenshot()`（**热路径，需实机验证**） |
| 9 | `27d7e0ab` | `a44eaf4e` | fix | Device | minitouch 连接失效先本地重建 | 新增 `reset_minitouch_connection()`；首次 ConnectionReset/Abort 仅本地重建，二次失败才 `adb_reconnect()`；BrokenPipe 亦改走本地重建（**设备层，需多开实测**） |
| 10 | `602730c67` | `6f1f4a21` | fix | Delegation | 收窄完成状态 OCR 识别区域 | `O_D_DONE` ROI 675,129,441,517→804,129,311,439（`assets.py` + `rewards/ocr.json`）；冲突取本地，**丢弃上游夹带的 `RuleScatter` import 与 `C_D_ALL`**（本地 `click.json` 无 d_all） |
| 10 | `13c3afb52` | `36877101` | feat | AbyssShadows | 接入快速装配御魂并上阵 | 新增 `I_OPEN_QUICK_LOADOUT`/`I_ABYSS_QUICK_LOADOUT_FIGHT` + 2 png；`switch_soul_in_abyss` 改走本地 `run_quick_loadout(config,entry,fight_anchor,dismiss)` |
| 10 | `9f5c7b8cb` | `9e883ff1` | fix | DemonEncounter | 灯笼按位置识别 + 事件入口 3s 超时 | 新增 `scan_lantern_types()` 与 `_enter_lantern_event()`；空灯笼优先级提前，避免兜底成「战斗」 |
| 10 | `9f8841f11` | `6d18aa38` | fix | AbyssShadows | 切换御魂前关闭残留分布弹窗 | 冲突：本地 `switch_soul_in_abyss` 已被 `13c3afb52` 重构（无 `goto_page(page_shikigami_records)`）→ **保本地导航架构**，仅把「残留 `I_ABYSS_MAP_EXIT` 弹窗则点击关闭」守卫并入重构后的流程 |
| 10 | `1c5c57ffc` | `dbb54de0` | fix | DemonEncounter | 宝箱购买后确认弹窗关闭再进 boss | 新增 `_close_box_popup(timeout=5)`，`_box` 末尾调用；依赖本地已有 `Timer`/`I_DE_FIND` |
| 10 | `b21b44acf`（手工移植，**仅 AreaBoss 段**） | `8e2c1e14` | fix | AreaBoss | 筛选分类意外关闭时自动重开并防卡死 | 新增 `_switch_filter_category`（重开计数 + `FILTER_REOPEN_MAX_RETRIES=3` 超限抛 `GameStuckError`）+ 导入 `GameStuckError`；其 DemonEncounter 段依赖本地不存在的 `exist_image`/`is_in_real_battle` 且本地已有等价 `stuck_record` 处理 → **丢弃** |
| 10 | `33c40a65f` | `cb4b022d` | fix | GeneralInvite | 下调挑战按钮识别阈值 | 手工移植（非 cherry-pick）：`assets.py` `I_FIRE`/`I_FIRE_SEA` 0.8→0.7、`general_invite.py` 去内联 `threshold=0.7`、`gi/image.json` 同步；**未引入上游 `profile` 字段** |
| 11 | `395fef27` + `a8afe598` | `87055ee5` | feat | GameUi | 闲庭（独立庭院皮肤）识别 | 手工移植（非 cherry-pick），**只取闲庭语义**：`default_pages.py` 导入 `not_`、`page_main` 改 `all_of(not_(I_CHECK_MAIN_SET), I_CHECK_MAIN)`、新增 `page_relax`(`priority=90`) + 连线 `page_relax->page_main`(`I_BACK_BROWN`)；`assets.py` 追加 `I_CHECK_MAIN_SET`/`I_BACK_BROWN`（本地格式，**未引入上游 `profile`**）；`image_main.json` 追加 `back_brown`/`check_main_set`；新增 2 张 png（取自上游）。**丢弃**上游 `395fef27` 夹带的 GeneralBattle 奖励详情资产与 `assets.py` 258 行重排噪声、以及上游 RuleScatter/状态化点击框架。`0c53d2c6`（旧 `detect_relax_page()` 实现）**已被取代，不合并** |
| 12 | `dedfb11b` | `28bf7a37` | fix | Delegation | 修正式神委派任务点击位置 | 直接 cherry-pick，**零冲突**；`ocr_appear_click(O_D_DONE)` → `ocr_appear` + 取单个命中框点其正下方领取区；本地 `RuleOcr.detect_and_ocr/filter/keyword` 齐备 |
| 12 | `1c3accdf` | `ff3e23ce` | feat | Navigator | `goto_page` 到达判定支持 `accepted_pages` | 直接 cherry-pick，**零冲突**；新增可选关键字参数（默认空元组，向后兼容），命中旁页即 `_finalize_arrival(current,...)` |
| 12 | `44dd4659` | `179f6dc0` | fix | EvoZone | 扩大锁/解锁按钮识别区域 | 手工移植（非 cherry-pick）：**保留本地 `roi_front`**（本地已分叉 703,656,24,32 / 704,658,21,27），仅取上游 `roi_back`（683,646,63,64→**613,614,155,91**、680,643,67,67→**609,623,170,89**）；`o/image.json` 同步 |
| 12 | `cf6fa6a5` | `179f6dc0` | fix | image | 拦截零方差模板并修正多尺度浮点漂移 | 手工移植（非 cherry-pick）：本地匹配走 RPC 且**无掩码特性**，仅取 `module/image/runtime.py` 无掩码语义——新增 `_template_is_degenerate`（逐通道常量即退化）并在 `_template_match_image`/`_multi_scale_template_match`/`_match_all_template` 三处前置拦截；多尺度循环改索引式 `min_scale + index * step` 消除浮点漂移。`module/atom/image.py` 属死代码，**未移植** |

---

## §3 已判定「已覆盖 / 不适用 / 跳过」——不要重复分析

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `722ac818c` | WeeklyTrifles | 添加摸鱼页面识别 | 已覆盖 | 本地 `tasks/WeeklyTrifles/page.py` 已注册 `page_touch_fish`（per-module 页面体系） |
| `526080816` | GameUi | Restore touch fish page navigation | 已覆盖 | 同上；本地 `script_task` 已用 `goto_page(page_touch_fish)` |
| `627ba3399` | TouchFish | 修复摸鱼行动逻辑问题 | 已覆盖 | 本地 `script_task._save_touch_fish` 已含 `not_save_flag` 修复 |
| `9236651f4` | GameUi | 移植 mine 新版页面导航模块到 dev | 已覆盖 | 本地即该移植的来源；`game_ui.py` 已是 facade + `navigator.py` |
| `014219c82` | GameUi | Limit repeated navigation button clicks #1762 | 不适用 | 改的是旧单体 `game_ui.py` 结构，本地已重构为新导航 |
| `fffc3940f` | GameUi | Improve repeated button handling and login screen refresh | 不适用 | 同上 |
| `b08097922` | Restart | 适配十周年登录按钮点击范围 | 不适用 | 改旧 `tasks/Restart/login.py`；本地已迁移到 `tasks/Component/Login/service.py` |
| `17595422d` | Restart | 仅调整进入游戏坐标 | 不适用 | 同上 |
| `bb2bc70af` | Restart | 匹配十周年登录文字 | 不适用 | 同上 |
| `cb8a5f906` | Restart | 保持生成文件格式不变 | 不适用 | 同上 |
| `d0d4720c2` | Restart | 同步十周年登录 OCR 资源源文件 | 不适用 | 同上 |
| `8f4adc61e` | Restart | Support original login screen compatibility | 不适用 | 同上；如需兼容旧登录界面须按本地 `LoginService` 手工移植 |
| `51582666d` | image | 新增掩码模板匹配与多尺度方法分发 | 跳过 | 本地匹配统一走图像服务 RPC，架构不兼容；掩码功能上游自称“暂未处理” |
| `afdc03181` | HeroTest | Attach HeroTest dynamic page edges to session page copies #1861 | 跳过 | 本地 `fc1cbada` navigation 重构已覆盖 |
| `e5ed0cf39` | RichMan | Adjust Orochi scale OCR region and add UI mockups | 已覆盖 | 本地 `mall/scales/ocr.json` 已是 `547,11,...`（上游改动即 x→547） |
| `43ada9d15` | RichMan | 大富翁修复荣誉商店不购买蓝票的问题 | 已覆盖 | 本地 `honor.py` 已用 `buy_more(I_HONOR_BLUE)`；`special.py` 已有等价正则实现 |
| `13ab1a62b` | RichMan | 寮商店购买后先重新识别再滑动 | 不适用 | 本地 `guild.py` 已重写（`goto_page` + `max_swipe` 上限循环），上游补丁面向旧结构 |
| `c426b982c` | RichMan | Improve shrine shop purchase detection and retry handling | 已覆盖 | 本地 `shrine.py` 已是 `Timer(10)` 重试循环，`assets.py` I_S_WHITE_FIVE/FOUR/BLACK 已是上游终值 |
| `c9c13ee38` | base_task | 竖屏截图时跳过突发检测防止 OpenCV 断言崩溃 | 已覆盖 | 本地图像服务 `module/image/runtime.py`（`_template_match_image`，source<template 即返回不匹配）已在根处拦截，`_burst` 处守卫冗余；上游次日亦以同理由回退 |
| `8319a0c61` | base_task | 移除 _burst 中冗余的竖屏防御 | 不适用 | 即 `c9c13ee38` 的回退，两者相互抵消，上游净变更为零 |
| `85c1baff9` | BudokaiTournament | 补 i18n 标签并在修行合训前检查门票 | 不适用 | 本地无 `tasks/BudokaiTournament` 模块；i18n 键 `demon_battle_config` / `best_demon_battle_config` 已存在 |
| `78083db2e` | OtherWorldTwilight | 新增御魂副本任务彼世逢魔 | 已覆盖 | 本地已含 |
| `1c0a01f23` | OtherWorldTwilight | 修复绿标默认值绕过与队长建房失败死循环 | 已覆盖 | 本地已含 |
| `4e32d985c` | GeneralBattle | 支持按式神名点击绿标 | 已覆盖 | 本地 mine 系早已有命名绿标（`green_mark_name` / `GreenMarkEnum.NAME` / `O_GREEN_MARK_AREA`），该提交自述即「移植自 mine」 |
| `5bc3f6e29` | GeneralBattle | Support named green marks in battle wait | 已覆盖 | 同上（上游 `battle_wait` 里的命名绿标本就源自本地 mine 系） |
| `44682816c` | Nian | 更新年等待图标识别区域 | 已覆盖 | 本地自研 `e120b169` 已放宽 `I_N_WAITING.roi_back` 至 `614,10,303,83`，涵盖上游新位置 (825,34) |
| `0f1b83151` | SoulsTidy | 识别条件排除 +0 等级 | 已覆盖 | 本地 `tasks/SoulsTidy/script_task.py:174` 已判 `in ['+0','古']` |
| `7b522c948` | EternitySea | 清理无用导航包装与死代码 | 已覆盖 | 本地已是终态（`goto_page(page_soul_zones)` / `goto_page(page_main)`，被删方法本地均无） |
| `309080cb9` | ActivityShikigami | 每月活动更新图标 | 不适用 | 本地无 `I_SHI`，资产/素材已自研分叉，合并会覆盖本地当月素材 |
| `5ed1d1b03` | image | 模板大于截图时跳过匹配 | 已覆盖 | 本地匹配走 RPC，`module/image/runtime.py:691` 已有根级守卫；`atom/image.py::template_match` 为死代码 |
| `ba1adb6da` | atom | 尺寸守卫移入多尺度循环 | 已覆盖 | 本地 `module/atom/image.py:238` 循环内已有守卫 |
| `c9f17c9a7` | atom | RuleAnimate 首帧用整图作模板 | 已覆盖 | 本地 `module/atom/animate.py:60` 首帧已 `corp(image, roi_back)` |
| `2209dec09` | GeneralInvite | docstring 补 exact 说明 | 不适用 | 本地 `ocr_appear`/`ocr_appear_click` 已无 `exact` 参数，补丁上下文不存在 |
| `e8abc93bd` | GuildActivityMonitor | ADB 多通知漏检 + OCR 模式 | 已覆盖 | 本地已全量等价（`check_run_days` / `get_notification_info_ocr` / `use_ocr` 齐备） |
| `01f24bdba` | device | 登录循环跳过非横屏截图 | 不适用 | 目标 `tasks/Restart/login.py` 本地已重构为 `LoginHandler(LoginService)`；竖屏崩溃已由 `runtime.py:691` 拦截 |
| `f1073050c` | emulator | MuMu Android 15 实例启动 | 已覆盖 | 本地平台层已改用 handler，`handlers/mumu12.py:13` 正则已匹配 12/15 |
| `d7d986909` | Exploration | 还原 I_FLAG_2_ON ROI | 不适用 | 本地无 `tasks/Exploration/solo.py`，目标文件缺失 |
| `31b48aae4` | Exploration | 探索流程等待确认点击 | 已覆盖 | 本地 `tasks/Exploration/base.py:115+` 已在等待循环内 `appear_then_click(I_UI_CONFIRM*)`；其 `battle_wait.py` 部分属已回退框架 |
| `158dc7db4` | HeroTest | buff 未匹配随机兜底 | 不适用 | 本地 HeroTest 已重构为线性点击，无 timer+continue 上下文 |
| `62f488b3c` | Dokan,FallenSun | I_BACK_BL → I_UI_BACK_BLUE | 不适用 | 本地全仓已无 `I_BACK_BL` 引用，目标行不存在 |
| `550b8edb5` | DailyTrifles,GameUi | 好友页识别与点击 | 不适用（半覆盖） | GameUi `I_CHECK_FRIENDS` 已于批次3 并入；DailyTrifles 部分面向旧结构（本地改 `goto_page(page_friends_luck)`） |
| `2df1b78fb` | DailyTrifles | 商城返回按钮加 interval/timeout | 不适用 | 本地该处已改为 `goto_page(page_mall)` / `goto_page(page_main)` |
| `af5fcf056` | Orochi | 改用 page_orochi 导航 | 已覆盖 | 本地 `tasks/Orochi/page.py` 与上游新增文件逐行相同，`script_task` 已用 `goto_page(page_orochi)` |
| `3f8ed0064` | GeneralInvite | 精确昵称匹配好友 #1782 | 已覆盖 | 本地以重构实现：`Component/GeneralInvite/general_invite.py:339 _find_exact_friend_area`（未引入 `exact` 参数） |
| `558ef4f87` | GeneralInvite | revert 精确昵称匹配 | 已覆盖 | 同上（revert 三连中间态，净效果抵消） |
| `b360b1977` | ocr | Revert revert 精确昵称匹配 | 已覆盖 | 同上（三连净效果 = 精确匹配，本地已以重构等价实现） |
| `193aa39f3` | Component | 新增幕间「花札幕台」 | 已覆盖 | 本地 `Component/Costume/config.py:53 COSTUME_SHIKIGAMI_11` + `costume_base.py:79 range(1,13)` + sk11 资产/素材齐 |
| `332b3600b` | i18 | 花札幕台中文翻译 | 已覆盖 | 本地 `assets/i18n/zh-CN.json:258 "costume_shikigami_11": "花札幕台"` |
| `7469f5c5e` | EternitySea | 永生之海队长收尾加固 | 延后 | 本地缺该加固（`run_leader` 收尾直接 `exit_room()`），但上游补丁绑定旧导航（`ui_page_appear` / `I_BACK_BOTTOM` 本地均无），需手工移植，收益低（本地 `run()` 已有 `goto_page(page_main)` 兜底） |
| `aab570fff` | ActivityShikigami | 更新武道大会图标与 ROI | 不适用 | 本地该模块已自研分叉（无 `I_SHI`，`I_CLIMB_MODE_PASS`/`O_FIRE`/`I_TO_BATTLE_MAIN` 均不同），合并会覆盖本地当月素材 |
| `faca04069` | ActivityShikigami | 活动战斗更新 | 需立项 | 含已回退的 `battle_wait.py`，本地该文件不存在 |
| `d26d33e01` | ActivityShikigami | 配置翻译归一化重构 | 需立项 | 本地 config 结构不同 + 含框架链 |
| `9e0e0ae15` | ActivityShikigami | 体力/通关数改 digit OCR | 需立项 | 依赖活动战斗结算框架，且资产分叉 |
| `36e1a822a` | Costume | 新皮肤「玉岚狐庭」多帧时序庭院 | 需立项 | 大特性；本地 `costume_base.py` 无多帧分支 |
| `bb808e1bd` | Costume | 新增 `RuleGif.attach_to` | 需立项 | 新框架能力；本地 `module/atom/gif.py` 无 `attach_to` |
| `08079eaf5` | Costume | 按任务战斗场景皮肤（新模块） | 需立项 | 本地无 `Component/CostumeBattleScene` / `BattleSceneType` |
| `37a884efe` | Costume | 缺资产时跳过 | 需立项 | 依附 `bb808e1bd`（`RuleGif.attach_to`），前置未落地 |
| `dbab53fbe` | Costume | 新皮肤「狐栖归处」 | 需立项 | 本地无 main16 目录/键 |
| `2395c9404` | BudokaiTournament | 新增整任务武道大会 | 需立项 | 本地无 `tasks/BudokaiTournament`（新模块，+596 行） |
| `b3ede5b13` | BudokaiTournament | 门票耗尽关闭 boss 详情 | 不适用 | 目标文件本地不存在 |
| `372609d1b` | BudokaiTournament | 避免重复搜索点击 | 不适用 | 同上 |
| `7de0cd115` | config | anti_ban 抽为 AntiBanGuard | 已覆盖 | 本地 `module/config/anti_ban.py` 的 `AntiBanGuard` 与上游逐行相同，`script.py` 已在用 |
| `1613c0309` | atom | 防风控加固与一键诊断导出 | 需立项 | 15 文件 281 行大特性 |
| `60bf1268f` | WeeklyTrifles | 每周琐事新增惠比寿摸鱼行动 | 需立项 | 新功能 + 新页面/素材（16 文件 258 行） |
| `57475547d` | Duel_Try | 添加队伍试用图像资源及相关规则 | 延后 | 本地无 `I_D_TRY`；需自备素材并把旧 `.additional` 改挂到 `tasks/GameUi/default_pages.py:213 page_duel` 的新 recognizer（非 bug 修复，优先级低） |
| `8d784c72b` | Component | 新增幕间「拾光之窗」+ 战斗主题「灵狐寄愿」及翻译 | 已覆盖 | 本地已有：`Costume/config.py:54 COSTUME_SHIKIGAMI_12 # 拾光之窗`、`:79 COSTUME_BATTLE_15 # 灵狐寄愿`、`costume_base.py:79 range(1,13)`、`i18n/zh-CN.json:272/30` |
| `19ae288c4` | DemonEncounter | 信件答题结束后补点获得奖励弹窗 | 已覆盖 | 本地信件收尾已是等价实现（`sleep(2.5)` + `ui_reward_appear_click`，批次 4c 落地） |
| `8e62ae47e` | Secret | 修复秘闻检测 | 不适用 | 本地层数识别已重构，补丁目标行不存在 |
| `1ebf4f4f0` | TeamScroll | avoid TeamScroll OCR blocking exploration entrance | 跳过（净零） | 与 `0c7f778c6` 互为正反；且本地无 `tasks/TeamScroll/` |
| `0c7f778c6` | TeamScroll | Revert "avoid TeamScroll OCR blocking exploration entrance" | 跳过（净零） | 即 `1ebf4f4f0` 的回退，净效果为零 |

> **GeneralBattle `battle_wait` 框架链（14 条，统一「不适用（框架）」，不必单独分析）**：
> `02fe012f1` / `745ce5ebf` / `6ada723ac` / `5a3eaddc5` / `00888a40f` / `5951edfb8` / `d2f98590f` /
> `d54042b53` / `f214461b7` / `a413ea6f7` / `3dca54e1f` / `eff487272` / `0e7112381` / `e70f40ee2`。
> 结论（2026-10-07 判定）：本地 mine 系战斗体系（`BattleContext` / `BattleBehaviorScope` /
> `BattleTimedInspection` / 连战 / 快速退出 / 预设 / buff / 命名绿标）**优于** dev 的该框架，
> 且与其新版 GameUi 导航（`page_battle*` / `goto_page` / `exit_matcher`）深度绑定；引入框架
> 即重蹈批次 0（`fc1fc355` → 回退 `a85dabdc`）。**该链只做「取其精华」手工移植，不引入框架**：
> 精华已落地于批次 8（`00888a40f`+`3dca54e1f` 的 `RuleClickExclude`、`eff487272`+`00888a40f`
> 的 `I_END_FIX_*` 浮窗检测）。其余（`battle_wait.py` / `battle.py` 框架、`battle_wait_strategy`
> 装饰器、`08db56bc`/`dcd03726` 重构、`a413ea6f` 净零 revert、12 个附带任务文件、FallenSun
> `battle_wait_v2` 委托）均为糟粕 → 弃。**不要再按「需立项」重提该链。**
>
> **CI / `workflow` 类（6 条，统一「不适用」）**：
> `15386ae06` / `eb90f6a0c` / `96f1e9710` / `1589899ac` / `a29eb8829` / `8fceb225d`。
> 本地 `.github/` 仅含 `workflows/auto-create-pr.yaml` 与 3 个 ISSUE_TEMPLATE，这些目标文件
> （agentic lock / mirror / auto-merge）本地均不存在。

### §3.1 批次 9 扫描（`xylolit-mu/self` 源，209 条新候选）——已明确判定

> **背景（重要）**：批次 0~8 已把 `runhey/master` + `runhey/dev` 的待同步项判定完毕；
> 批次 9 的 209 条新候选**全部来自第三源 `xylolit-mu/self`**（该源为 mine 系派生 fork，
> 自述「同步 Azur / mine」）。故其多数改动与本地同源，**语义全覆盖率高**，必须逐条 `show` 核实。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `a9fa1e26` | chore | 同步 Azur 2026-08-28 更新 | 跳过（空） | `+0/-0` 空提交，无可合并内容 |
| `950145ed` | 御魂切换 | 限制装配点击并增加随机间隔 | 跳过（净零） | 与 `cd36bd16` 互为正反；本地 `switch_soul.py` 已是回退后终态（`sleep(0.5)` / `range(3)` / `cnt_click>=4`） |
| `cd36bd16` | 御魂切换 | 回退：恢复原装配点击次数与等待 | 跳过（净零） | 即 `950145ed` 的回退，本地已等价 |
| `258e8b8f` | config | group cross-script tasks under cooperative menu | 跳过（净零） | 与 `5a5d3dc4` 互为正反 |
| `5a5d3dc4` | config | Revert 上述 cooperative menu | 跳过（净零） | 即 `258e8b8f` 的回退，净效果为零 |
| `1d67a992` | Chess | 新增 Chess 测试状态决策流程（仅 MUMU-2） | 跳过（净零） | 与 `3b161aba` 互为正反，且属临时调试分支（`tasks/Chess/test_branch/`） |
| `3b161aba` | Chess | Revert 上述测试状态决策流程 | 跳过（净零） | 即 `1d67a992` 的回退 |
| `65d156d0` | Chess | 刷新后稳定 grigri 识别 | 已覆盖 | 本地 `runtime/round_state.py` 已有 `_grigri_quality_cache` + `cached_quality` 兜底 + `ACTION_SETTLE_INTERVAL` |
| `582eae75` | 测试 | 移除本地测试目录 | 延后 | 删除 `tests/` 4 文件；本地 `tests/` 有内容，需单独评估是否与本地测试体系冲突 |
| `8753481b` | image | 新增掩码模板匹配 | 待决策 | 与 §4 第 1 项同源议题（`51582666`）；本地匹配走图像服务 RPC，落地须服务端化 |

> 以上 8 条（除 `582eae75`、`8753481b`）已 `ignore`，不再出现在待同步列表（`upstream_ignored.json` 共 90 条）。

### §3.2 批次 9 未评估余量（~199 条）——**不要凭标题认为「已覆盖」**

> ⚠ **已被 §3.4 取代**：批次 10 后实跑 `advise` 已把余量**精确为 169 条**（全部来自 `xylolit-mu/self`）。**以 §3.4 的最新数值为准**；本节仅保留「大特性/框架级簇」的归类视角，不再作为条数依据。

> 批次 9 只做了「小体量 + 无冲突 + 低 churn」子集的语义核实（见 §2 批次 9 行）。
> 余量中 **`conflict=conflict` 占绝大多数**，且高度集中于下列**大特性/框架级**簇，
> 与本地架构分叉明显，**需立项或专项改造后才能评估**，不属于「小批次同步」范畴：
>
> | 簇 | 条数 | 说明 |
> |---|---|---|
> | `(无模块)` 混合大改 | ~60 | 多为 `+10536/-6025` 量级的多文件重构；含 `010298e0`（186 文件）、`efb0c2c9`（101 文件）、`0fdb4656`（95 文件）等全仓级改动 |
> | Chess / 百鬼棋局 | 12+5+2 | 状态机、`decision`/`events`/`state`、`chess_battle` 页框架；与本地 Chess 同源但已分叉 |
> | ActivityShikigami / 式神活动 | 12+11 | 活动战斗结算框架（与已回退的 `battle_wait` 链耦合） |
> | 对弈竞猜（FrogBoss 系） | 10 | 记录页/下注/权重策略；本地批次 4d 已落地 3 条，余量为重写 |
> | RichMan / 百鬼棋局 / 狭间 / LBS / MatialArts | 5+5+3+4+3 | 模块级重写或新玩法 |
> | image / 点击规则 / 全局页面 | 各 1~2 | 图像服务与导航框架级改动（`24010e18` +352/-220、`010298e0` 等） |
>
> **续接方式**：如需继续推进，按簇立项（先读该簇全部 diff → 判定可否局部移植），
> 不要按「逐条 cherry-pick」思路处理——`advise` 的 `conflict=conflict` 已提示必然人工取舍。

### §3.3 批次 10 未决余量（`xylolit-mu/self` 源，3 条）——**已缓存在 `%TEMP%\oas_shows\`**

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `4f0b246b3` | Costume | 修正 main13 庭院皮肤识别区域与素材 | 待决策（疑似可落地） | 纯 ROI + 2 张素材：`I_PET_HOUSE_13` 811,271,58,34→**813,270,37,35**；`I_CHECK_MAIN_13` 367,191,90,94→**1042,235,85,86**、roiBack 281,136→928,177；`main13/image.json` 同步。**风险**：该补丁夹带 `RuleScatter` import 与全局 `profile:"Default"` 字段（本地 json 契约为 `{itemName,imageName,roiFront,roiBack,method,threshold,description}`）→ 若采纳须剔除这两项。素材为二进制无法语义核实，**须实机确认是否与本地十周年/庭院下移版本匹配** |
| `028ca1f84` | Exploration | 探索大地图拆分「主线 / 玩法」tab 并继承大地图出口 | 待决策（导航框架级） | 新增 `page_mainline`/`page_gameplay`（锚点 `I_CHECK_MAIN_TITLE`/`I_CHECK_PLAY_TITLE`）+ `inherit_transitions()` 复制出边；`page_exploration` 降级为通用态并新增 tab 桥接边；`base.py::activate_realm_raid` 放开 `page_mainline`/`page_gameplay` 并改 `goto_page(page_mainline)`。**与本地 per-module 页面体系耦合**，需评估是否会影响既有 `page_exploration` 识别与导航缓存 |
| `aaede1dbe` | TrueOrochi | 改用玩法 tab 模块存在性判断本周次数 | 待决策（**依赖 `028ca1f84`**） | 以 `I_ST_MODULE`（玩法tab八岐大蛇模块，in-place 命中即本周有次数）替换 `O_TIMES` OCR 与 `current_success` 计数；`check_times` 简化为按 `success/failure_interval` 设下次运行；`config.py` 删除 `current_success` 与 `dynamic_hide`。**须先落地 `028ca1f84`（依赖 `page_gameplay`）**；并注意其为**行为语义变更**（不再精确计数，改模块在场兜底） |

> 三条均已缓存 `show` 补丁，接手时直接读 `%TEMP%\oas_shows\<hash>.patch` 即可，无需重新 `show`。

### §3.4 批次 10 后剩余余量刷新（2026-10-08 实跑 `advise`）——**169 条，全部来自 `xylolit-mu/self`**

> **数据方法**：`advise --json` 原始 **287** 条 → 按 §2/§3/§3.1/§3.3 全部反引号 hash（取前 8 位）+ `upstream_ignored.json`(4) 构建 **205** 条排除集 → 剔除 2 条 `Merge` → **剩余 169 条**。
> 过滤结果缓存：`%TEMP%\oas_remaining.json`（字段 `hash/date/subject/module/type/source/risk/size/level/judge/conflict`）；原始 `advise` 在 `%TEMP%\oas_advise_survey.json`。
> **根因**：`runhey/master` + `runhey/dev` 两源已全部判定完毕，剩余**全部**为第三源 `xylolit-mu/self`（~~§3.2 的「~199 条」现已精确为 169 条~~）。
> **复核**：批次 10 台账推送后（`9939927f`）再次 `fetch` 三源 + `advise` 重跑，原始仍 287、剩余仍 **169**，风险/冲突/level 分布与下表逐项一致 → 数值已确认。

风险 / 判定分布（169 条）：

| 维度 | 分布 |
|---|---|
| `risk` | isolated **78** / shared **51** / multi **40** |
| `conflict` | conflict **165** / ok **4**（其中 `isolated + ok` **仅 2 条**） |
| `level` | review **76** / caution **93** |
| `judge` | 🛑 建议单独评估 **76** / ⚠ 采用但需实测 **93** |

按 module 分组（count ≥ 5；其余 ~47 条散落约 30 个小模块）：

| module | 条数 | 代表条目（hash type[risk] 标题） |
|---|---|---|
| ActivityShikigami | 26 | `9cd478da1` fix[multi] zero activity tickets · `b61821577` fix[iso] 当期爬塔保底点击 · `bff3c9060` fix[iso] 补充页面迁移 |
| Chess | 14 | `58d1c95fc` fix[iso] 新增大厅异常界面处理 · `c0a9df863` fix[iso] 调整素材识别范围 |
| config | 13 | `e6e0e07ac` feat[shared] TeamScroll cooperative scroll · `a7eafd376` refactor[shared] TeamScroll self-contained |
| Component | 13 | `494107392` fix[multi] 寮突/个突保守改动 · `0eccaaebd` fix[shared] 幕间拾光之窗适配 |
| FrogBoss | 10 | `b41680710` refactor[shared] 十周年素材+非等权策略 · `bcb27d7fa` fix[iso] 记录页补结算+胜率权重 |
| GameUi | 8 | `6943fd4db` feat[multi] shared activity navigation · ~~`0c53d2c68` fix[iso] 闲庭轮换庭院识别~~（**已被取代，见下**） |
| assets | 7 | `ecdae3f3d` fix[shared] 调整汉化 · `f38ad6a19` fix[shared] 调整寄养逻辑 |
| KekkaiUtilize | 6 | `77c96473f` fix[iso] 调整寄养逻辑 · `54aac2238` fix[shared] 怠惰防检测模式 |
| WantedQuests | 5 | `23793489a` refactor[shared] 识别与 OCR 选型 · `0a393ece2` fix[iso] 正则变量遮蔽 |
| MartialArts | 5 | `883f5927f` feat[shared] 首领战流程 · `8d28225ee` fix[iso] 门票识别与搜寻 |
| RichMan | 5 | `9657817cf` feat[iso] 自动首领挑战 · `4225e6e23` feat[iso] 等级提升后处理 |
| DemonEncounter | 5 | `3651fcc87` fix[multi] 回退逢魔+大富翁+空票 · `a28103f25` fix[iso] 限首领搜寻重试 |
| atom | 5 | `7b8b22799` feat[shared] 防风控加固+诊断导出 · `04fe9da95` fix[shared] 新增区域选定方法 |

**低风险可落地 TOP（isolated，优先零冲突 / 单文件冲突）**——真正适合「小批次同步」的候选：

| hash | module | type | 标题 | 备注 |
|---|---|---|---|---|
| `a9cad51cd` | FrogBoss | refactor | 引入负向胜率权重 | **零冲突** |
| `b94dc89cd` | Chess | other | 状态决策流程迁入正式版本 | **零冲突**，体量偏大 |
| `0a393ece2` | WantedQuests | fix | 修复悬赏封印正则变量遮蔽 | small |
| `adf24d8e6` | WantedQuests | other | 收紧悬赏头像点击区域 | small |
| `ac2b10446` | WantedQuests | other | 上移悬赏头像点击区域 | small |
| `df3ff4303` | WeeklyTrifles | fix | 修正摸鱼行动御守数量读取与存储判断 | small |
| `6f4a87f50` | Chess | feat | 切换百鬼棋局默认为荒川 | small |
| `a8afe5986` | GameUi | fix | 优先识别闲庭并排除庭院误判 | **✅ 已并入（批次 11，`87055ee5`，手工移植；含 `395fef27` 闲庭识别）** |
| `cf9eba733` | Duel | fix | 达到名士星数目标后延至下周一运行 | — |
| `b61821577` | ActivityShikigami | fix | 修改当期爬塔保底点击逻辑 | small |

> **结论**：与 §3.2 判断一致——剩余 **169** 条高度集中于大特性 / 框架级簇（全仓级重构、活动战斗、Chess 状态机、导航与图像框架），**须按簇立项**，不适合逐条 cherry-pick。
> 可作为下一「小批次」继续推进的，仅上表 TOP 这类 isolated 小修（多为 WantedQuests / Chess / RichMan / MartialArts，且大多带 1 个冲突文件，因本地同源分叉）。

### §3.5 批次 12 扫描（最近 7 天 `runhey/dev` + `xylolit-mu/self`）——已明确判定

> **背景**：应「看看最近 7 天 dev/self 有什么新提交、能不能合」之请求，窗口内 dev **26** 条、self **10** 条；
> 绝大多数属批次 1~11 已合并/已判定项（见 §2/§3），**真正新且未处理的仅 4 条可落地 + 8 条判退**。

**新判定（本批次未纳入同步）**：

| 上游 hash | 源 | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|---|
| `c56e2c9b` | dev | Exploration | 大地图拆「主线/玩法」tab 导航 | 需立项 | 与 §3.3 的 self 版 `028ca1f84` 同一特性；新增 `page_mainline`/`page_gameplay` + `inherit_transitions()`，属 per-module 页面体系改造，须整体评估 |
| `f7db71b2` | dev | TrueOrochi | 用玩法 tab 模块在场检测替代次数记账 | 需立项 | 依赖 `c56e2c9b`（对应 §3.3 的 `aaede1dbe`），且为行为语义变更 |
| `431e3458` | self | GameUi | 回退：移除町中固定位置点击保底 | 需评估 | 本地 [navigator.py](../../tasks/GameUi/navigator.py) **已含该保底**，此提交是删除安全网，是否采纳取决于该保底线上是否致误 |
| `5a2d99bf` | self | FrogBoss | 处理商店弹窗并二次确认结束标志 | 需实测（可手工移植） | 真实兜底修复（`close_frog_mall` + `C_BET_REWARD_CLOSE`）；3 冲突文件、churn 高 |
| `8753481b` | self | image | 新增掩码模板匹配 | 待决策 | 同 §4 第 1 项（本地匹配走 RPC，须服务端化） |
| `5bc76c7e` | self | IbukiArena | 移植狭间幻境活动任务（新模块） | 需立项 | 本地无 `tasks/IbukiArena/` |
| `1f230af2` | self | FrogChallenge | 移植青蛙瓷器挑战赛（新模块，10 文件） | 需立项 | 本地无 `tasks/FrogChallenge/` |
| `c2390c2a` | self | IbukiArena | 修挑战判定可能提前命中 exit_matcher | 不适用 | 依赖 `5bc76c7e` 新模块，目标文件本地不存在 |

**新判定（已覆盖）**：

| 上游 hash | 源 | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|---|
| `a9cad51c` | self | FrogBoss | 引入负向胜率权重 | 已覆盖 | 本地 [frog_oas.py](../../tasks/FrogBoss/frog_oas.py) 已含 `rate - 0.5` + `signed_win_rate`（批次 4d `670f194a0` 落地） |
| `df3ff430` | self | WeeklyTrifles | 修正摸鱼行动御守数量读取与存储判断 | 已覆盖 | 本地 [script_task.py](../../tasks/WeeklyTrifles/script_task.py) 已含 `cu_tickts, _, _` + `not_save_flag` |

> dev 窗口内其余条目（`f4767278`/`c1dc5059`/`7738d5d5`/`194a3eda`/`606517be` 已合并；`5bc3f6e2`/`4e32d985`/`afdc0318`/`1c0a01f2`/`78083db2`/`52608081`/`7b522c94`/`af5fcf05`/`62f488b3`/`1589899a`/`08079eaf`/`51582666` 已判定）均见 §2/§3。

---

## §4 待决策

1. **掩码匹配 / 零方差拦截 / nan-inf 清洗**：是否以**服务端**方式补进 `module/image/runtime.py`（思路源自 `51582666`）。**批次 9 新增同源实现 `8753481b`（+152/-30，`module/image/runtime.py` + `module/atom/image.py`）**——与上述议题合并评估，仍为「待决策」。<br>**进展（批次 12）**：其中**与掩码无关**的两项（`_template_is_degenerate` 零方差拦截 + 多尺度 `min_scale + index*step` 浮点漂移修复）已按无掩码方式移植进本地 `module/image/runtime.py`（源 `cf6fa6a5`，见 §2 批次 12）；**仅剩「掩码模板匹配」本身仍待决策**（本地匹配走 RPC，须服务端化）。
2. **是否标记 ignore**：历史累计 `ignore` **90** 条（§3 + §3.1 中除「延后 / 待决策」项外的全部判定项）。**以后 §3 新增条目应随手 `ignore`**，避免每轮重现。
   - ⚠ **注意（批次 10 发现）**：`dev_tools/upstream_ignored.json`（工具 `DEFAULT_IGNORED`，**不入库**）曾**本地缺失**——此前 90 条 ignore 状态在本地已丢失。**批次 10 已重建该文件但仅含 4 条**（下述），历史 90 条仍未恢复 → `advise` 仍会把它们重新列为待同步。**接手续接时必须按本文件 §3 hash 集在脚本侧过滤**（不能依赖该文件），如需恢复可用 `ignore --hashes <§3 全部 hash,…>` 重建。
   - 批次 10 新增判定 4 条**已 `ignore`**：`19ae288c4`（已覆盖）、`8e62ae47e`（不适用）、`1ebf4f4f0` + `0c7f778c6`（净零对）。当前 `upstream_ignored.json` 仅这 4 条。
3. ~~**GeneralBattle `battle_wait` 链（14 条 + 依赖它的绿标 2 条 = 16 条）**：是否单独立项攻坚。~~ **已决策并收口（批次 8，`7871ed52`）**：判定**本地 mine 系战斗体系更优**，该框架**不引入**（引入即重蹈批次 0）。只做「取其精华」手工移植，已落地 2 项：`RuleClickExclude` 原子（`00888a40f`+`3dca54e1f`）、奖励详情浮窗检测 `I_END_FIX_*`（`eff487272`+`00888a40f`）。另 `4e32d985c`/`5bc3f6e29` 命名绿标经核实**本地早已覆盖**（上游自述移植自 mine）→ 已改判「已覆盖」。14 条框架链在 §3 统一改判「不适用（框架）」。**待实机验证：结算页误点奖励弹出详情浮窗后能被自动关闭、奖励正常收完。**
4. ~~**RichMan `c363395d8`（勋章商店售罄处理）**~~ **已落地（批次 7，`8b5c6fab`，手工移植）**：`medal.py` 加 `appear` 前置判断 + `count_soldout()` 核对，保留本地 `money_ocr`；`navbar.back_mall` 加 15s 超时保护。资产侧 `O_SOLD_OUT` 本地已有，未重复引入；`_enter_medal` 的 `I_SIDE_SURE_MEDAL` 本地无 → 不适用。**待实机验证：勋章商店整店/部分售罄时能正常收尾不卡死。**
5. **下一批候选**：
   - **批次 12（2026-10-09，`47f54223`）已落地 4 条**（2 cherry-pick + 2 手工移植合 1 提交，§2 批次 12 行）：`dedfb11b`（Delegation 委派点击位置）、`1c3accdf`（Navigator `accepted_pages`）、`44dd4659`（EvoZone 锁识别区）、`cf6fa6a5`（图像零方差拦截 + 多尺度浮点漂移）。**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` = `dbc630d7` = 本地（合并 `47f54223` + 台账回写 `dbc630d7`）；临时分支 `sync/upstream-20261009-084842` 已删除。推送方式见 §5 注（原生 GCM 直连，不带代理、不带显式 PAT）。<br>源：`runhey/dev`（`dedfb11b`/`1c3accdf`/`44dd4659`）+ `xylolit-mu/self`（`cf6fa6a5`）。
   - **待实机验证（批次 12）**：① 委派任务"完成"卡片按新逻辑点正下方领取区可正常领取；② `goto_page(..., accepted_pages=...)` 旁页可达时不再强转目标页（调用点目前尚无，属预备 API）；③ 阴界之门锁/解锁新识别区命中正常；④ 多尺度规则恢复原尺寸档命中、退化（纯色）模板不再假阳性。
   - **批次 12 判退（见 §3.5）**：需立项 `c56e2c9b`/`f7db71b2`（探索 tab 导航）、`5bc76c7e`/`1f230af2`（IbukiArena/FrogChallenge 新模块）；需评估 `431e3458`（移除本地町中保底）；需实测 `5a2d99bf`（FrogBoss 商店兜底）；不适用 `c2390c2a`；待决策 `8753481b`（掩码匹配）；已覆盖 `a9cad51c`/`df3ff430`。
   - **批次 10（2026-10-08，`1c34c37c`）已落地 7 条**（5 条 cherry-pick + 2 条手工移植，§2 批次 10 行）。**✅ 推送状态：已推送 `origin/czr`** —— 远端与本地同为 `9939927f`（合并提交 `1c34c37c` + 台账回写 `2438bb43` + §3.4 刷新 `9939927f`）。<br>**推送方式**：见 §5 注「push 标准做法（原生 GCM 直连，不带代理、不带显式 PAT）」。
   - **待实机验证（批次 10）**：① 委派完成状态收窄后识别正常；② 狭间快速装配御魂并上阵成功、切换前残留分布弹窗被关闭；③ 逢魔灯笼按位置识别 + 事件入口 3s 超时不会卡「战斗」兜底；④ 宝箱购买后确认弹窗关闭再进 boss；⑤ AreaBoss 筛选分类意外关闭能自动重开（≤3 次）否则 `GameStuckError`；⑥ GeneralInvite 挑战按钮 0.7 阈值点击成功率。
   - **批次 10 未决余量 3 条**：见 **§3.3**（`4f0b246b3` Costume main13 ROI 疑似可落地、`028ca1f84` Exploration tab 导航、`aaede1dbe` TrueOrochi 模块检测依赖前者）。
   - **批次 11（2026-10-08，`87055ee5`，手工移植）已落地 1 项（闲庭识别）**：源 `xylolit-mu/self`（`395fef27`+`a8afe598`，`0c53d2c6` 旧实现已被取代）。**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` = `87055ee5` = 本地。改动：`tasks/GameUi/default_pages.py` + `assets.py` + `page/image_main.json` + 2 png。**待实机验证：使用独立皮肤/设置的「闲庭」能被识别为 `page_relax`（priority 90），且庭院主页不再被误判为闲庭；闲庭点 `I_BACK_BROWN` 返回庭院正常。**
   - **批次 10 后剩余余量已刷新（2026-10-08 实跑 `advise`）**：剩余 **169 条**，**全部**来自 `xylolit-mu/self`（`runhey` 两源已判定完毕）；risk isolated 78 / shared 51 / multi 40，零冲突仅 4 条。按 module 分组与 isolated 可落地 TOP 10 见 **§3.4**。下一「小批次」候选即 §3.4 的 TOP（WantedQuests / Chess / RichMan / MartialArts 等小修）。
   - **批次 9（2026-10-08，`44b22f09`）已把 `xylolit-mu/self` 的「小体量 + 无冲突 + 低 churn」子集核完并落地 10 条**（§2 批次 9 行）。
   - **待实机验证（批次 9）**：① 勾协弹窗能被 `while self._burst()` 循环清理且不卡死（`screenshot()` 热路径）；② 道馆连战主动退出后能正确收尾；③ Chess 拖拽/选符咒手感与稳定性；④ 多开时 minitouch 不再频繁重连 ADB。
   - **剩余 `xylolit-mu/self` 余量（已精确为 **169** 条）**：见 **§3.4**（精确清单与 isolated TOP）/ **§3.2**（簇归类），高度集中于大特性/框架级簇（全仓级重构、活动战斗、Chess 状态机、导航与图像框架），**须按簇立项**，不适合小批次同步。
   - **既有需立项（大特性）**：Costume 皮肤/多帧时序（`36e1a822a`/`bb808e1bd`/`08079eaf5`/`37a884efe`/`dbab53fbe`）；ActivityShikigami 活动战斗更新（`faca04069`/`d26d33e01`/`9e0e0ae15`）；BudokaiTournament 新任务（`2395c9404`）；防风控加固（`1613c0309`）；每周琐事惠比寿摸鱼行动（`60bf1268f`）
   - **延后（需手工适配，价值低）**：`7469f5c5e`（永生之海队长收尾加固）、`57475547d`（Duel_Try 队伍试用）、`582eae75`（删除本地 `tests/`）
   - **不适用（已 ignore）**：GeneralBattle `battle_wait` 框架链 14 条（见第 3 项与 §3 表下注记）、ActivityShikigami `aab570fff`、BudokaiTournament `b3ede5b13`/`372609d1b`、CI `workflow` 6 条、§3.1 净零/空/已覆盖 8 条
6. **经验（重要，批次 9 再次验证）**：本地 `czr` 源自 `mine`，而 `xylolit-mu/self` 亦为 **mine 系派生 fork**（自述同步 Azur/mine）→ **同源度高、语义重复率极高**（206 条 `adopt/caution` 里真正可落地仅 10 条）。定批**必须做语义核实**（`show` 真实 diff + 本地 grep 比对），不能只信 `advise`；否则会把"已覆盖"的提交当成待同步重复分析。**判「已覆盖」的高频证据**：本地该文件该行已是上游补丁的目标值，或本地已存在上游补丁引入的同名符号/缓存变量。
7. **净零对识别法（批次 9 新增，可复用）**：同一源内出现「`X` 后紧跟 `Revert X`」的两条时，只需看**本地当前是否等于 revert 后终态**；若是，则两条一并 `ignore`，不必合并。本次识别出 4 对：`950145ed`/`cd36bd16`、`258e8b8f`/`5a5d3dc4`、`1d67a992`/`3b161aba`（外加 `a9fa1e26` 空提交）。

---

## §5 续接步骤（开新对话时）

1. 先读本文件 §1 / §3（含 §3.1 / §3.2）/ §4，恢复已做/未做/跳过状态。
2. 拉取上游（**多源，默认三源**）：
   `toolkit\python.exe dev_tools/upstream_sync.py --base czr --since "2 months ago" fetch`
3. 生成顾问信号并按 §3 过滤：
   `... advise --json --out %TEMP%\oas_advise.json`（用 §3 的 hash 剔除已判定项；
   结果文件较大，**用脚本按 §3 hash 集过滤后再看**，勿整段读入上下文）
4. 定批 → `apply --manifest <清单> --pause`；冲突按「**保本地 RPC / 导航架构**」原则处理，必要时只手工移植该提交自身的语义改动。
5. 验证：`py_compile` + 关键模块 `import` + 单测（如 `unittest tasks.Dokan.test_battle_exit`）+ 全仓无冲突标记。
6. `git switch czr` → `git merge --no-ff sync/<分支> -F <消息文件>` → 删 sync 分支 → 推送 `origin/czr`（见下方注）。
7. **回到本文件更新 §1/§2/§3/§4**；判定项随手 `ignore --hashes <hash,…>`。

> 环境要点（代理、分支纪律、提交规范）见项目记忆与 `upstream_sync_doc.md`；禁止修改 git config。
> - **fetch**：git 直连 github 常不通 → `-c http.proxy=http://127.0.0.1:7897`。
> - **push（标准做法，用户已确认 2026-10-08）**：全局 `url.*.insteadof` 会把 `github.com` 改写成 `gh-proxy.com`，而 gh-proxy **不转发写认证**。
>   **统一用端口形式绕过重写、走原生 GCM 直接出网**（**不带 `http.proxy`、不带显式 PAT**）：
>   `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr`
>   - ⚠ 不要再使用 `https://<PAT>@github.com/...` 或 `https://<PAT>@gh-proxy.com/...` 形式（凭据明文、且 gh-proxy 写认证不可用）。