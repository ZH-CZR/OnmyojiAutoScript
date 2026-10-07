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

| 批次 | 日期 | 本地 merge commit | 上游来源 | 候选/落地 | 主题 |
|---|---|---|---|---|---|
| 0（已回退） | 2026-10-07 | `fc1fc355` → 回退 `a85dabdc` | upstream/dev | 14 / 0 | GeneralBattle 战斗等待重构；合并后无法启动，整体回退 |
| 1 | 2026-10-07 | `1c369fa1` | upstream/dev（`--since "2 months ago"`） | 11 / 5 | 低风险单模块（README / RichMan / RyouToppa / Costume） |
| 2 | 2026-10-07 | `aaed5d07` | upstream/dev | 2 / 2 | KekkaiActivation 多尺度收卡 + annotator 静态资源缓存 |
| 3 | 2026-10-07 | `46c8a8fd` | upstream/dev | 6 / 3 | GameUi 导航与庭院/好友识别（3 条已覆盖未合） |
| 4a | 2026-10-07 | （无落地） | upstream/dev | 5 / 0 | RichMan 商店组：4 条已覆盖/不适用，`c363395d8` 待决策 |
| 4b | 2026-10-07 | （无落地） | upstream/dev | 2 / 0 | base_task 竖屏防护：上游次日自我回退，净变更为零 |
| 4c | 2026-10-07 | `86a5b997` | upstream/dev | 5 / 4 | DemonEncounter 逢魔：挑战次数检测 + boss 搜索容错（1 条不适用） |
| 4d | 2026-10-07 | `f484e550` | upstream/dev | 3 / 3 | FrogBoss 对弈竞猜：记录页读取 + 下注恢复 + 负权重策略 |
| 5 | 2026-10-07 | `1951b0a6` | upstream/dev | 23 / 2 | 语义核实剩余候选：仅「契灵战斗判定」+「御魂整理 sk2~5 更换 ROI」可落地，其余已覆盖/不适用 |
| 6 | 2026-10-07 | `88798f14` | upstream/dev | 17 / 1 | 永生之海队长收尾无法结束任务修复；剩余大特性/框架链/CI 归类为「需立项 / 不适用」 |

> 批次 0 说明：这批含 GeneralBattle `battle_wait` / `battle.py` 新框架，合并后脚本无法启动，
> 已用 `a85dabdc` 整体回退（删除 `battle_wait.py` 1631 行等）。**再动该链前必须重新做启动验证。**

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
| `4e32d985c` | GeneralBattle | 支持按式神名点击绿标 | 延后 | 依赖 czr 已回退的 GeneralBattle 新框架（`battle_wait.py` / `battle.py`） |
| `5bc3f6e29` | GeneralBattle | Support named green marks in battle wait | 延后 | 同上 |
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

> **GeneralBattle `battle_wait` 框架链（14 条，统一「需立项」，不必单独分析）**：
> `02fe012f1` / `745ce5ebf` / `6ada723ac` / `5a3eaddc5` / `00888a40f` / `5951edfb8` / `d2f98590f` /
> `d54042b53` / `f214461b7` / `a413ea6f7` / `3dca54e1f` / `eff487272` / `0e7112381` / `e70f40ee2`。
> 本地该框架已整体回退（见 §1 批次 0 / §4 第 3 项），落地须先立项并重做启动验证。
>
> **CI / `workflow` 类（6 条，统一「不适用」）**：
> `15386ae06` / `eb90f6a0c` / `96f1e9710` / `1589899ac` / `a29eb8829` / `8fceb225d`。
> 本地 `.github/` 仅含 `workflows/auto-create-pr.yaml` 与 3 个 ISSUE_TEMPLATE，这些目标文件
> （agentic lock / mirror / auto-merge）本地均不存在。

---

## §4 待决策

1. **掩码匹配 / 零方差拦截 / nan-inf 清洗**：是否以**服务端**方式补进 `module/image/runtime.py`（思路源自 `51582666`）。
2. **是否标记 ignore**：已累计 `ignore` 82 条（§3 中除「延后」项外的全部判定项）。**以后 §3 新增条目应随手 `ignore`**，避免每轮重现。
3. **GeneralBattle `battle_wait` 链（14 条 + 依赖它的绿标 2 条 = 16 条）**：是否单独立项攻坚。本地曾因该框架整体回退（`fc1fc355` → `a85dabdc`），重做需逐条重建并重新验证启动。清单见 §3 表下注记（`02fe012f1`/`745ce5ebf`/`6ada723ac`/`5a3eaddc5`/`00888a40f`/`5951edfb8`/`d2f98590f`/`d54042b53`/`f214461b7`/`a413ea6f7`/`3dca54e1f`/`eff487272`/`0e7112381`/`e70f40ee2`，另 `4e32d985c`/`5bc3f6e29`）。
4. **RichMan `c363395d8`（勋章商店售罄处理）**：本地 `medal.py` 无该逻辑（结构相近但 `money_ocr` 取值不同），需按本地结构手工移植「`appear` 前置判断 + `count_soldout()` 核对」；其 `navbar.py` 部分不适用（本地无 `I_SIDE_SURE_MEDAL`）。
5. **下一批候选**：批次 5/6 已把「可直接落地的小修」核完（3 条落地：契灵战斗判定、御魂整理 sk2~5 ROI、永生之海队长收尾）。**剩余上游项已全部判定，无新的「可落地」小修**，只剩下需立项或延后：
   - **需立项（大特性）**：GeneralBattle `battle_wait` 框架链（14 条，见第 3 项）；Costume 皮肤/多帧时序（`36e1a822a`/`bb808e1bd`/`08079eaf5`/`37a884efe`/`dbab53fbe`）；ActivityShikigami 活动战斗更新（`faca04069`/`d26d33e01`/`9e0e0ae15`）；BudokaiTournament 新任务（`2395c9404`）；防风控加固（`1613c0309`）；每周琐事惠比寿摸鱼行动（`60bf1268f`）
   - **延后（需手工适配，价值低）**：`7469f5c5e`（永生之海队长收尾加固）、`57475547d`（Duel_Try 队伍试用）
   - **不适用（已 ignore）**：ActivityShikigami `aab570fff`、BudokaiTournament `b3ede5b13`/`372609d1b`、CI `workflow` 6 条
6. **经验（重要）**：本地 `czr` 源自 `mine`，在 RichMan 等模块**已含上游同期改动** → 定批必须做**语义核实**（`show` 真实 diff + 本地 grep 比对），不能只信 `advise` 的冲突信号；否则会把"已覆盖"的提交当成待同步重复分析。

---

## §5 续接步骤（开新对话时）

1. 先读本文件 §1 / §3 / §4，恢复已做/未做/跳过状态。
2. 拉取上游：
   `toolkit\python.exe dev_tools/upstream_sync.py --base czr --since "2 months ago" --remote-branch dev fetch`
3. 生成顾问信号并按 §3 过滤：
   `... advise --json --out %TEMP%\oas_advise.json`（用 §3 的 hash 剔除已判定项）
4. 定批 → `apply --manifest <清单> --pause`；冲突按「**保本地 RPC / 导航架构**」原则处理，必要时只手工移植该提交自身的语义改动。
5. 验证：`py_compile` + 关键模块 `import` + 全仓无冲突标记。
6. `git switch czr` → `git merge --no-ff sync/<分支> -F <消息文件>` → 删 sync 分支 → 用本地代理推 `origin/czr`。
7. **回到本文件更新 §1/§2/§3/§4。**

> 环境要点（代理、分支纪律、提交规范）见项目记忆与 `upstream_sync_doc.md`；git 直连 github 不通，
> fetch/push 需 `-c http.proxy=http://127.0.0.1:7897`，禁止修改 git config。