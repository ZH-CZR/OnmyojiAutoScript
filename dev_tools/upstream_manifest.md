# 上游待同步提交清单

> 生成时间: 2026-10-04 15:46:51
> 范围: `mine..upstream/dev`（自 2 months ago 起），已排除 merge 提交，并过滤掉内容已在本地者
> 共 117 条 | 类型: feat=29  fix=67  refactor=8  chore=4  docs=2  test=1  revert=3  other=3
> 风险: isolated=73  multi=30  shared(⚠)=14
>
> 图例：`⚠` = 触及共享基础设施文件（i18n/config 等），与本地定制冲突概率高，
>       建议优先挑选无 ⚠ 的提交。
>
> 用法：把要同步的提交勾成 `[x]`（保持缩进），保存后运行：
>   `python dev_tools/upstream_sync.py apply`

## GeneralBattle (17)

- [ ] `d2f98590` [feat] feat(GeneralBattle): Add prepare/preset/green/echo/randomclick hooks and config-driven loadout - add per-task/per-battle states and options for the new battle wait hooks - add loadout_default/loadout_show/state_show and loadout_from_config for config-driven setup - add randomclick_gate with start_delay/execution_limit/cooldown/trigger_probability gates - dispatch options per plan in runtime.update_options and extract setup_hook enable/disable - wire ActivityShikigami ScriptTask to Battle loadout flow - add tests for randomclick_gate and remove debug prints
- [ ] `0e711238` [feat] feat(GeneralBattle): Add completion fallback click and randomclick expectation model
- [ ] `d54042b5` [feat] feat(GeneralBattle): Add battle count and state reset helpers, restore climb counting
- [ ] `08db56bc` [refactor] refactor(GeneralBattle): Split options from strategy and introduce runtime context injection - extract battle_wait_options decorator/with-context so plan and options are managed independently - replace BattleWaitContext with PublicContext/PrivateContext and PerTaskState/PerBattleState dataclasses - wrap _bw_* hooks via runtime in BattleWait.__new__, injecting singleton pub_ctx and per-hook pri_ctx - add hook_enabled_update lifecycle: completion stays disabled until success/failure settles - centralize hook events/sequence/options defaults into module-level constants - add BattleResult enum and migrate hooks to write pub.per_battle.success - update tests: runtime injection/distribution/scope coverage, xfail not-yet-migrated cases
- [ ] `dcd03726` [refactor] refactor(GeneralBattle): Model hook options and runtime state as per-event dataclasses
- [ ] `f214461b` [fix] fix(GeneralBattle): Override class-level battle wait plan and options per decorator
- [ ] `1bec4e5d` [fix] fix(GeneralBattle): Report failed battle as failure to trigger mark and refresh  #1803
- [ ] `4e894c69` [fix] fix(GeneralBattle): Prevent repeated random battle actions and refresh reward detection
- [ ] `04787fc4` [fix] fix(GeneralBattle): Expand chat message close area detection
- [ ] `5951edfb` [fix] fix(GeneralBattle): Select named reward areas for targeted clicks - match excluded click areas by asset names such as C_END_1_1 - randomly select a matching click and generate a coordinate inside its ROI - add regression tests for area matching and random selection
- [ ] `65a6b737` [fix] fix(GeneralBattle): retry prepare click after battle_before timeout
- [ ] `3dca54e1` [fix] fix(GeneralBattle): Fix activity reward area selection
- [ ] `eff48727` [fix] fix(GeneralBattle): Improve reward detail popup detection - add a third reward detail popup template and update template regions - raise matching thresholds for reward popup assets - retry closing detected popups before completing reward collection
- [ ] `00888a40` [fix] fix(GeneralBattle): Avoid accidental clicks on battle result controls - add exclusion-aware random clicking with rejection and complement sampling - exclude battle result controls while collecting rewards - detect gold snake skins and integrate the strategy into EvoZone and RyouToppa - add result-screen assets and regression tests
- [ ] `5a3eaddc` [feat] feat(GeneralBattle): Add hook options support
- [ ] `745ce5eb` [feat] feat(GeneralBattle): Introduce configurable battle wait strategies
- [ ] `6ada723a` [feat] feat(GeneralBattle): Add configurable battle wait strategy framework

## RichMan (9)

- [ ] `c426b982` [fix] fix(RichMan): Improve shrine shop purchase detection and retry handling
- [ ] `9ec6101e` [fix] fix(RichMan): Handle bulk purchase failures in special shop
- [ ] `42e0bb45` [fix] fix(RichMan): define sold-out OCR rule in ocr.json and regenerate assets
- [ ] `c363395d` [fix] fix(RichMan): handle sold-out medal shop items gracefully
- [ ] `13ab1a62` [fix] fix(RichMan): 寮商店购买后先重新识别再滑动
- [ ] `43ada9d1` [other] 大富翁修复荣誉商店不购买蓝票的问题
- [ ] `e5ed0cf3` [fix] fix(RichMan): Adjust Orochi scale OCR region and add UI mockups
- [ ] `c90ac04a` [feat] ⚠ feat(RichMan): 千物宝箱新增唤妖借处获取樱灯饰功能
- [ ] `68489090` [feat] ⚠ feat(RichMan): 秘卷屋海汐御魂支持自动选择御魂购买方式

## GameUi (8)

- [ ] `52608081` [fix] fix(GameUi): Restore touch fish page navigation - register the touch fish page in the shared page definitions - export the page through the GameUi page facade - migrate WeeklyTrifles touch fish navigation to goto_page
- [ ] `606517be` [fix] fix(GameUi): 适配庭院下移后的庭院标志识别区域
- [ ] `92223c5b` [fix] fix(GameUi): Restore I_CHECK_FRIENDS image and ROI for friend page detection
- [ ] `3a6e56c2` [fix] fix(GameUi): 修复导航超时不抛异常及 registry 遍历 bug
- [ ] `9236651f` [feat] feat(GameUi): 移植 mine 新版页面导航模块到 dev
- [ ] `988145c0` [fix] fix(GameUi): refresh page_main_goto_summon template to match current game version
- [ ] `fffc3940` [fix] fix(GameUi): Improve repeated button handling and login screen refresh - slow down button retries after repeated recognition attempts - refresh screenshots and process the latest frame before login and reward handling
- [ ] `014219c8` [fix] fix(GameUi): Limit repeated navigation button clicks #1762

## Component (6)

- [ ] `a413ea6f` [revert] Revert "fix(GeneralBattle): retry prepare click after battle_before timeout"
- [ ] `dbab53fb` [feat] ⚠ feat: 添加狐栖归处庭院皮肤
- [ ] `8d784c72` [feat] ⚠ feat(Component):新增幕间“拾光之窗”、战斗主题“灵狐寄愿”及其翻译
- [ ] `c4680264` [fix] 修复永生之海队长打满次数后无法正常结束任务的问题
- [ ] `89ed887c` [fix] 修复御魂整理任务sk2/3/4/5皮肤下不点击更换按钮的问题
- [ ] `193aa39f` [feat] feat(Component):增加幕间“花札幕台”

## Restart (6)

- [ ] `b0809792` [fix] fix(Restart): 适配十周年登录按钮点击范围
- [ ] `17595422` [fix] fix(Restart): 仅调整进入游戏坐标
- [ ] `bb2bc70a` [fix] fix(Restart): 匹配十周年登录文字
- [ ] `cb8a5f90` [chore] chore(Restart): 保持生成文件格式不变
- [ ] `d0d4720c` [fix] fix(Restart): 同步十周年登录 OCR 资源源文件
- [ ] `8f4adc61` [fix] fix(Restart): Support original login screen compatibility

## workflow (6)

- [ ] `1589899a` [chore] chore(workflow): Update automation workflows to gpt-6-luna
- [ ] `a29eb882` [chore] chore(workflow): Trigger mirror on dev pushes and pull requests
- [ ] `96f1e971` [fix] fix(workflow): Restore working AI provider endpoint
- [ ] `eb90f6a0` [fix] fix(workflow): Isolate issue triage dispatch jobs and refresh compiled workflows - add an issue-based concurrency discriminator for issue triage dispatches - recompile agentic workflows with gh-aw v0.88.2 - update locked gh-aw action references and generated workflow metadata
- [ ] `8fceb225` [feat] feat(workflow): Automate weekly sync PR merging
- [ ] `15386ae0` [chore] chore(workflow): Upgrade GitHub Agentic Workflows to v0.86.2

## ActivityShikigami (5)

- [ ] `faca0406` [fix] fix(ActivityShikigami): Update
- [ ] `d26d33e0` [fix] ⚠ fix(ActivityShikigami): Normalize configuration translations
- [ ] `9e0e0ae1` [fix] fix(ActivityShikigami): Improve activity battle result handling - switch activity stamina and pass counters to digit OCR mode - handle multi-digit all-zero OCR results as a valid remaining count - continue reward processing after closing accidental item detail popups
- [ ] `309080cb` [other] 每月活动更新图标
- [ ] `aab570ff` [feat] feat(ActivityShikigami): Update 此版将失效武道大会

## Costume (5)

- [ ] `08079eaf` [feat] ⚠ feat(Costume): Add task-scoped battle scene skin support #1843
- [ ] `c1dc5059` [feat] feat(Costume): Add Chinese names to costume switch logs
- [ ] `bb808e1b` [feat] feat(Costume): Attach GIF multi-frame behavior in-place so page routing works  #1824 - add RuleGif.attach_to to swap GIF match methods onto a RuleImage instance - switch COSTUME_MAIN_17 replacement from set_asset to in-place attach_to - retune pet_house 17_a/17_b frame ROI and images
- [ ] `37a884ef` [fix] fix(Costume): Skip missing assets when attaching GIF frames
- [ ] `36e1a822` [feat] ⚠ feat(Costume): Support time-variant courtyard skin 玉岚狐庭 #1824

## DemonEncounter (5)

- [ ] `194a3eda` [fix] fix(DemonEncounter): 优化boss搜索容错、收缩灯笼点击区、补信件答谢
- [ ] `7738d5d5` [fix] fix(DemonEncounter): 挑战次数OCR改为DigitCounter 模式
- [ ] `0450848e` [fix] fix(DemonEncounter): 调整逢魔Boss挑战次数识别区域
- [ ] `7b329e3e` [feat] feat(DemonEncounter): 逢魔之时增加今日挑战次数检测
- [ ] `85c1baff` [fix] ⚠ fix(DemonEncounter): Add missing i18n labels for battle lineup switching configs  #1732 - add Chinese labels for demon_battle_config and best_demon_battle_config - check tickets before scout in BudokaiTournament cultivation drills

## FrogBoss (4)

- [ ] `98ce82bb` [refactor] 调整(对弈竞猜)：同步记录页面与最新识别素材
- [ ] `670f194a` [fix] 修复(对弈竞猜)：移植记录补结算、下注恢复与负权重策略
- [ ] `86b2a7ef` [refactor] 调整(对弈竞猜)：更新活动素材与识别区域
- [ ] `9b3c9b67` [feat] 新增(对弈竞猜)：移植OAS胜率策略与赛果记录

## BondlingFairyland (3)

- [ ] `ccd7cf18` [fix] fix(BondlingFairyland): Detect battle scene with is_in_battle in member wait  #1735
- [ ] `f4913ccb` [fix] fix(BondlingFairyland): Add loop limit guard in stone purchase to prevent infinite loop  #1723
- [ ] `fe7f8e1c` [fix] fix(BondlingFairyland): Switch mitama separately before search and capture  #1715

## BudokaiTournament (3)

- [ ] `372609d1` [fix] fix(BudokaiTournament): avoid repeated search clicks
- [ ] `b3ede5b1` [fix] fix(BudokaiTournament): close boss detail when tickets run out
- [ ] `2395c940` [feat] ⚠ feat(BudokaiTournament): Add BudokaiTournament task and register it into config

## GeneralInvite (3)

- [ ] `558ef4f8` [revert] revert(GeneralInvite): restore partial nickname matching
- [ ] `2209dec0` [docs] docs(GeneralInvite): Document exact OCR matching rationale #1782
- [ ] `3f8ed006` [fix] fix(GeneralInvite): Match invited friends by exact nickname #1782 - add opt-in exact matching for OCR full-text results - use exact matching when selecting invited friends - add regression tests for partial and complete nickname matches

## HeroTest (3)

- [ ] `fd46e065` [test] test(HeroTest): cover skill selection timeout fallback
- [ ] `158dc7db` [feat] feat(HeroTest): buff未匹配到目标时随机选择兜底，避免卡死
- [ ] `741ec8f3` [fix] fix(HeroTest): Add 10s timeout to hero2_skill_wait to prevent infinite loop  #1633

## atom (3)

- [ ] `c9f17c9a` [fix] fix: RuleAnimate uses full screenshot as template causing false animation-stable and invalid template (265,0,3)
- [ ] `ba1adb6d` [fix] fix: move size guard into multi-scale loop to preserve downscaling; use ASCII punctuation in comments
- [ ] `1613c030` [feat] ⚠ feat: 防风控加固与一键诊断导出

## DailyTrifles (2)

- [ ] `2df1b78f` [fix] fix(DailyTrifles): Add click interval and timeout for back button in mall page
- [ ] `550b8edb` [fix] fix(DailyTrifles): Improve friend love page detection and navigation

## EternitySea (2)

- [ ] `7b522c94` [refactor] refactor(EternitySea): 清理无用的导航包装与死代码
- [ ] `7469f5c5` [other] 永生之海队长收尾加固: 等待奖励动画结束再退房间并导航回御魂界面

## Exploration (2)

- [ ] `d7d98690` [fix] fix(Exploration): Restore I_FLAG_2_ON ROI to unblock friend tab switching  #1844
- [ ] `31b48aae` [fix] fix(Exploration): Prevent exploration clicks from getting stuck #1814

## FallenSun (2)

- [ ] `e70f40ee` [fix] fix(FallenSun): Adopt battle wait strategy to avoid too many reward clicks  #1721
- [ ] `02fe012f` [fix] fix(FallenSun): Rewrite battle_wait with v2 and add yellow back button for exiting team

## Orochi (2)

- [ ] `af5fcf05` [feat] feat(Orochi): 改用 page_orochi 进行御魂页导航
- [ ] `ab3c8842` [feat] ⚠ feat(Orochi): 御魂结束后检测真蛇并自动拉起真蛇任务

## WeeklyTrifles (2)

- [ ] `722ac818` [feat] feat(WeeklyTrifles):添加摸鱼页面识别
- [ ] `60bf1268` [feat] ⚠ feat(WeeklyTrifles):每周琐事新增执行惠比寿的摸鱼行动功能

## base_task (2)

- [ ] `8319a0c6` [refactor] refactor(base_task): 移除_burst中冗余的竖屏防御
- [ ] `c9c13ee3` [fix] fix(base_task): 竖屏截图时跳过突发检测防止OpenCV断言崩溃

## Dokan,FallenSun (1)

- [ ] `62f488b3` [fix] fix(Dokan,FallenSun): replace removed I_BACK_BL with I_UI_BACK_BLUE

## Duel_Try (1)

- [ ] `57475547` [fix] fix(Duel_Try): 添加队伍试用图像资源及相关规则

## GuildActivityMonitor (1)

- [ ] `e8abc93b` [refactor] refactor(GuildActivityMonitor): 修复ADB多通知漏检问题并新增OCR检测模式

## KekkaiActivation (1)

- [ ] `64dd5d90` [fix] fix(KekkaiActivation): Retry harvesting expired cards before activation #1708

## Nian (1)

- [ ] `44682816` [fix] fix(Nian): Update waiting image recognition region

## README (1)

- [ ] `368d5736` [docs] docs(README): 修复 Star History 图表链接

## RyouToppa (1)

- [ ] `40a349e4` [fix] fix(RyouToppa): 任务结束后返回庭院避免探索任务不开启加成

## ScriptTask (1)

- [ ] `0f1b8315` [fix] fix(ScriptTask): 修复识别条件以处理 +0 等级

## SwitchAccount (1)

- [ ] `175e1dc5` [fix] fix(SwitchAccount): Fix attribute name typo O_SA_CHECK_SELCET_SVR causing AttributeError

## SwitchOnmyoji (1)

- [ ] `929c6a11` [fix] fix(SwitchOnmyoji): give both switch_role loops a bounded exit

## TouchFish (1)

- [ ] `627ba339` [feat] feat(TouchFish):修复摸鱼行动逻辑问题

## config (1)

- [ ] `7de0cd11` [refactor] ⚠ refactor: 将 anti_ban 作息逻辑从 script.py 抽出为 AntiBanGuard

## device (1)

- [ ] `01f24bdb` [fix] fix(device): Skip processing for non-landscape screenshots - add a simple 1280x720 screenshot shape check - skip login and harvest processing until the screen is landscape - remove the redundant template-size guard

## emulator (1)

- [ ] `f1073050` [fix] fix(emulator): support MuMu Android 15 instance startup

## i18 (1)

- [ ] `332b3600` [feat] ⚠ feat(i18): 添加花札幕台的中文翻译

## image (1)

- [ ] `5ed1d1b0` [fix] fix(image): 模板大于截图时跳过匹配

## ocr (1)

- [ ] `b360b197` [revert] Revert "revert(GeneralInvite): restore partial nickname matching"
