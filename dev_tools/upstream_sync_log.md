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
| 44 | 2026-11-13 | `8532a981`（3 cherry-pick + 1 自检补正 + 回归测试） | nearaura/master + kongdr418/mine | 11 / 3 | 每日琐事商店签到入口重试、突破券 0~30 上限校验、标注器截图帧缓存隔离；商店模板两版改动与斗技资源、MetaDemon 协助、AutoStory 迁移判不采纳/不适用（§3.21） |
| 43 | 2026-11-12 | `870dc9ec` | nearaura master/dev + kongdr418/mine + lgg686/self（**首次剔除 xylolit-mu**） | 132 / 4 | 棋局手牌满出售、未知页关闭顺序 + 种树标识、狭间暗域确认按钮收敛、删除重名 `I_CLOSE_RED`；同批先落 1 条本地修复提交（覆盖 9 项修复：超鬼王胜利/门票/锁队、探索与寮宴会搜索区、悬赏按卡去重） |
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
| 13 | 2026-10-09 | `9e6b3b6e`（手工移植，非 cherry-pick） | xylolit-mu/self | 1 / 1 | 对弈竞猜商店弹窗兜底 + 结束标志二次确认（`5a2d99bf`）：`close_frog_mall`/`confirmed_finish_marker`/`C_BET_REWARD_CLOSE` + 2 张新图 + 3 用例；批次 12 判退项维持需立项（`c56e2c9b`/`f7db71b2`/`5bc76c7e`/`1f230af2`）、需评估（`431e3458`）、待决策（`8753481b`），本轮不再纳入 |
| 14 | 2026-10-09 | `018a4ad4`（手工移植，非 cherry-pick） | runhey/dev（同源更早见 xylolit-mu/self `028ca1f8`） | 1 / 1 | **探索大地图「主线/玩法」tab 选关卡死根治（最小修）**：只取主线一侧资产（`C_CLICK_MAIN_TITLE` + `I_E_CHECK_MAIN_TITLE` + `res_check_main_title.png`），在 `open_expect_level` 首行加 `ensure_mainline_tab()` 守卫；**实机复现故障（部署版 12:23 连续失败 3 次）+ 仓库/部署双端真机验证通过**；未引入上游 tab 页框架 |
| 15 | 2026-10-09 | `7e98ce39`（**本地自研**；上游 dev/self 该处代码与本地旧版逐字相同，无补丁可移植） | 本地 `czr` | 1 / 1 | **探索候补式神填充重写**：新版 UI 满级式神不能作候补（游戏提示「该式神经验已满」），旧逻辑只盯单一稀有度 → 恒为 0 → 抛 `GameStuckError`（部署版 13:27~13:29 连续失败 3 次）。改为按 素材→N→R→SR→SSR→SP 逐类尝试、填到 40/50、全类无果仅告警；自实现带超时的切类；删 `choose_rarity`；真机验证 **47/50** |
| 16 | 2026-10-09 | `2f0dabda`（**本地自研**） | 本地 `czr` | 1 / 1 | **启动/登录流程补「确认退出探索吗」弹窗处理**：游戏被留在探索页时，启动流程按返回会弹出该确认框，原流程只认黄色关闭按钮 → 连点 12 次 → `GameTooManyClickError` → 重启 app → 仍判 `Login failed`（实例：少时之约 20:24:18）。在已知弹窗链补 `I_E_EXIT_CONFIRM`。**导航侧本就有该资产**（`DEFAULT_UNKNOWN_CLOSERS`），缺的只是登录服务这一环 |
| 17 | 2026-10-10 | `9bb8a6ad`（手工移植，非 cherry-pick） | runhey/dev | 5 / 1 | 逢魔重进地图改走町中 + 搜索/集结重试 2→3 轮（`4e4e9079f`）；另 2 条已覆盖（Component `run_task_or_default_general_battle`）、2 条 workflow 不适用 |
| 18 | 2026-10-11 | `f585d8b2`（**本地自研 / 上游机制移植**） | runhey/dev（机制） | 1 / 1 | **RealmRaid 退四改走上游 `run_general_battle_back(exit_four=True)`**：修复快速退出战斗后残留「确认退出战斗吗」(`I_EXIT_ENSURE`) 弹窗 → `fire_again` 被挡 → `GameStuckError`（实例 2026-10-10 18:34:20 少时之约） |
| 19 | 2026-10-11 | `7654a223`（**本地自研**；上游无此守卫，无补丁可移植） | 本地 `czr` | 1 / 1 | **收紧重连守卫 OCR 判据，修复吉闻弹窗误判卡死**：`O_UI_CONNECTING` 由 `mode="Full", keyword="连接"` 改为 `mode="Single", keyword="正在连接"`。根因 = `RuleOcr.filter` 单字兜底把吉闻输入框「欧运连连」的「连」、「接受」的「接」误判为重连 → 原地等待 → `GameStuckError`（实例 2026-10-11 08:11:53 少时之约 DailyTrifles）。新增 2 个回归测试文件（8 项全绿） |
| 20 | 2026-10-11 | `0ed4fb18`（7 cherry-pick + 1 回归测试提交） | runhey/dev + runhey/master | 8 / 7 | **共享 UI 资产统一化**：「确认/取消/勾选」按钮收敛为 `GlobalGameAssets.I_UI_CONFIRM`/`I_UI_CANCEL`/`I_UI_CHECK`/`I_UI_UNCHECK`，删除 `I_EXIT_ENSURE`/`I_FRESH_ENSURE`/`I_SOU_SWITCH_SURE`/`I_GI_*`/`I_I_*` 等私有同义资产；导航未知页兜底新增 `I_UI_BACK_CIRCLE`；ActivityShikigami `43c7f334` 判为不适用 |
| 21 | 2026-10-12 | `93d94a1f`（2 cherry-pick + 2 回归测试提交） | runhey/dev（+ self 核对） | 6 / 2 | **绘卷捐献改用「最大」按钮并限制 10 轮**（`4f0a4856`）；**斗技 MVP 分享页识别**（`d638c11f`，掩码模板本地不支持 → 裁剪雾化左缘改普通模板匹配）；`27241886`/`b3d6fe98` 不适用、`efd39e18` 已覆盖、`e930e2e1`+`8195cc60` 净零、self `cf6fa6a5` 已覆盖（批次 12 `179f6dc0`） |
| 22 | 2026-10-12 | `ede87a14`（手工移植，非 cherry-pick） | xylolit-mu/self | 2 / 1 | **掩码模板匹配服务端化落地**（self `8753481b`）：服务端 `_match_rule`/`_match_all_template` 放行 `Masked template matching`（掩码取同目录 `xxx_mask.png`，非零参与/零忽略，缺失或尺寸不符自动回退普通匹配）+ 模板缓存指纹纳入掩码 mtime:size + 退化判据改按「参与区域」+ 匹配结果 nan/inf 清洗；客户端 `RuleImage` 补常量/property/`test_match` 分派，标注器下拉补选项。同源 runhey `51582666`（客户端落点）判**不适用**（已被本项覆盖）。**影响面**：全仓所有图像规则共用的服务端匹配链路（`match_rule`/`match_all`/`match_all_any`）与模板缓存；普通/多尺度/SIFT 行为不变。**回归测试**：新增 `tests/test_masked_template_match.py`（20 项，本机实跑全绿） |
| 23 | 2026-10-13 | `aa77eb3e`（2 cherry-pick + 1 手工移植 + 1 回归测试） | runhey/master + runhey/dev | 5 / 4 | **共享 UI 收尾**：`5b556e92`（登录三处私有取消按钮收敛为共享 `I_UI_CANCEL_SAMLL` + 共享确认/取消/勾选框 ROI 放宽 + 删 `Restart` 私有取消资产）+ `e8df3ae0`（`GeneralInvite.check_and_invite` 勾选框/确认点击间隔 1→3）；`916e6eb8`（勾选框新素材）；`92578cd0`（#1926 突破券 OCR 区域 920,12,78,30）；`d6c42bee` 判**不适用**（目标 `battle_wait.py`/`battle.py` 本地不存在）。**影响面**：全仓共享确认/取消/勾选点击（`I_UI_CONFIRM`/`I_UI_CANCEL`/`I_UI_UNCHECK`）、登录弹窗关闭链、默认邀请流程、突破券数量识别。**回归测试**：新增 `tests/test_shared_ui_assets_followup.py` + `tests/test_exploration_realm_raid_ocr.py`（共 18 项，本机实跑全绿） |
| 24 | 2026-10-13 | `0b68a9bc`（**本地自研**；上游无该缺陷的补丁） | 本地 `czr` | 1 / 1 | **`GeneralBattle.exit_battle` 兜底对象兼容修复**：`run_task_or_default_general_battle` 造的裸 `GeneralBattle` 只注入 `navigator`/`match_page_once`，而 `exit_battle` 用 `GameUi.get_current_page(self)` 会访问不存在的 `_detect_current_page` → 快速退出链路 `AttributeError`（实例 2026-10-13 16:15:49 少时之约 KekkaiUtilize）。改走与 `run_general_battle` 同款的 `GameUi.detect_page_in(self, ...)` 显式页面识别；新增 `tests/test_general_battle_exit_fallback.py`（9 项） |

| 25 | 2026-10-14 | `6ec09b31`（手工移植，非 cherry-pick） | runhey/dev（PR #1934） | 3 / 1 | **斗技开战前等待收敛**：上游 `ui_click(..., interval=6, timeout=45)`（PR #1934）本地 `ui_click` 无 `timeout` → 复用本地等价且更成熟的 `ui_click_until_appear_or_timeout(..., interval=6, timeout=45)`；同轮 PR #1905（Exploration `Scene+solo` 自适应滑屏）评估为**需立项**（本地无 `solo.py`/`Scene`），其余 6 条判退/净零/已覆盖 |
| 38 | 2026-11-09 | `2dba211b`（手工移植，非 cherry-pick） | xylolit-mu/self | 1 / 1 | **超鬼王六星鬼王上供**：`591508f6` 上供模式（召唤六星 → 分享指定好友 → 等待击杀，不参战）；本地无门票刷取模块，`MetaDemonTicket`/票池预检不适用 |
| 39 | 2026-11-11 | `0e2c6da7`（手工移植，非 cherry-pick） | nearaura/dev + kongdr418/mine | 10 / 2 | **minitouch 压力下限 + 动画帧裁剪区固定**：`a787a58a`（PR #2，`max_pressure < 20` 时 `randint` 抛 `ValueError`）、`3ede58e1`（部分采纳：`RuleAnimate.stable()` 帧比较固定初始 `roi_front`；同一提交的无条件 `roi_pad` 外扩不采纳）；MetaDemon 2025 新代际三连 / workflow 镜像 / docs 域名 / DraftDuel 记录判不适用（§3.16） |
| 40 | 2026-11-11 | `2b7f72e0`（整模块替换，非 cherry-pick） | nearaura/dev `a86b0e50` | — / 25 文件 | **超鬼王整模块替换**：本地旧代际 `tasks/MetaDemon` 全部换为上游新代际（含 `image_2025.json`、18 张新模板、5/6 星策略、公开共享鬼王），删 36 个旧文件；同时补 `O_BOSS_MARK` + `boss_mark`/`boss_mark_reset`（§3.17）。用户决策：旧代际不保留 |
| 41 | 2026-11-11 | `a49eec9a`（3 cherry-pick + 1 fix + 1 回归测试） | kongdr418/mine + lgg686/self | 10 / 3 | **配置导入泛型误判 + 协斗模板重做 + 交换身份半量切换**：`f99d75c2`（`list[Model]` 注解被判成 pydantic 模型 → 配置导入崩溃）、`bf71e3a5`（协斗协作类型改整卡识别 + 好友邀请筛选放宽 + GlobalGame 勾玉/猫粮/狗粮 `roi_back` 放宽 0.8→0.7 + 契灵球数 OCR 区域）、`844d3bec`（handoff1/2 单任务内半量切换，队员段与抓捕循环受次数上限约束）；kongdr MetaDemon 三连 / 探索 `_META` / DraftDuel 两批判不适用，lgg686 `a279ab60` 整包 sync 暂缓立项（§3.18） |
| 42 | 2026-11-11 | 见 §3.19（手工移植） | lgg686/self `a279ab60`（摘取） | 225 文件整包 / 1 任务 | **超鬼王门票刷取（MetaDemonTicket）**：移植门票任务 4 文件 + 续用觉醒/探索战斗流程；新增结算界面门票 OCR `O_METADEMON_PASS`，刷取前检测改用本地 `O_MD_TICKET`；注册配置与 Activity Task 菜单 |
| 37 | 2026-11-09 | `8334c797`（手工移植，非 cherry-pick） | xylolit-mu/self | 4 / 3 | **御魂自选弹窗 + 活动入口轮换 + 逢魔保底 + 门票 0 复核**：`dd96057e`（`I_GB_CLOSE_RED` + Orochi 结算/奖励/未知页先关弹窗）、`38a8f00d`（庭院活动栏目最多轮换 8 次；寄养开关本地已有等价 `utilize_harvest` 未重复引入）、`904686c1`（boss 页 3 轮失败改 `TaskEnd`）、`18ededee`（pass/boss 门票 OCR=0 先进战复核）；新增 `tests/test_upstream_batch37_fixes.py`（17 项） |
| 33 | 2026-11-06 | `c97328d3`（7 cherry-pick + 1 回归测试） | runhey/master + kongdr418/mine | 99 / 7 | **低风险小批**：TalismanPass 任务页签、KekkaiActivation 跨皮肤收卡区 + 激活误判、GlobalGame 协作邀请素材、GeneralInvite 勾选框间隔、标注器文件夹上传；余 89 条按簇留待（§3.12 / §4） |
| 34 | 2026-11-09 | `021be78a`（手工移植，非 cherry-pick） | nearaura/master（原 runhey）+ xylolit-mu/self | 23 / 4 | **上游账号迁移 + 新提交小批**：悬赏 #2006 地点数量 OCR 重试、探索退出状态保持、超鬼王召唤票阈值 0.8、登录选服 OCR ROI；其余因上游新架构或本地无对应模块判退（§3.13） |
| 32 | 2026-10-29 | `19008619`（13 cherry-pick + 1 自检补正 + 1 回归测试） | runhey/dev + kongdr418/mine | 15 / 13 | **蓝票按单价买多张 + 悬赏封印/接受拒绝新 UI + 海汐一次买完 + 道馆每次开馆 + 皮肤模板刷新**：`120c881a`+`be5f3c97`+`47b9064b`（Buy 多买窗口/单价上限/逐张买）、`094b30b9`（`wait_until_disappear` 超时）、`a9597e77`（Chess 点击记录清理）、`329ecfc7`（永生之海队员开战准备）、`e68c2d26`（GlobalGame 新 UI）、`921a2b82`（悬赏封印新 UI）、`2db22cc3`（海汐一次买完）、`3f085151`（道馆每次开馆）、`506564c6`（皮肤模板缓存刷新）、`d1ad2c09`（棋局阵容预设搜索区，含 assets.py 自检补正 `4698b48c`）、`91f7d916`（标注器任务中文名）；`6360d6a9` 判已覆盖；其余判退/需立项/延后（§3.11） |
| 31 | 2026-10-23 | `9e66d1d7`（2 cherry-pick + 2 手工移植 + 1 回归测试） | runhey/master（PR #1963）+ xylolit-mu/self + kongdr418/mine | 102 / 4 | **馆主修习模板修正 + 加成开关按类型拆分 + 寮宴会第二旗帜 + 棋局商店防连点**：`4354df46`+`8bbf87b8`（Dokan 模板换图 + 阈值 0.8→0.7，直接 cherry-pick）、`51dbf564`（GeneralBuff 金币/经验/通用三类型开关资产 + GuildBanquet `I_BANQUET_FLAG_2`，手工移植）、`1410590f`+`fa7a87e7`+`47a3a3bc`（Chess 商店槽位点击记录清理，手工移植）；其余 98 条判已覆盖/不适用/需立项（§3.10） |
| 30 | 2026-10-21 | `4a8bd2f3`（3 cherry-pick + 1 回归测试） | kongdr418/mine | 28 / 3 | **标注工具停止卡死 + 导航交替换路空转 + 服务端画面接口**：`51115b4a8`（标注工具停止连接时 Web 服务卡死：截图子进程超时分级 terminate→kill、远程截图方法集合、`_drain_status_queue` 竞态）、`a9eb4843c`（`navigator.py` 交替换路反复重置进度计时器 → 空转不报错）、`9f07623b5`（新增 `/screen` 模拟器画面截取接口，叠加式不改现有截图链路）；其余 25 条判已覆盖/不适用（§3.9） |
| 29 | 2026-10-20 | `a095e311`（6 cherry-pick + 1 回归测试） | kongdr418/mine | 6 / 6 | **每日收益统计（DailyTrifles）**：本地 czr 原先完全没有该功能 → 整链引入。新增 `module/log_income.py`（任务侧/服务端共用的快照解析与日汇总读写）+ `module/server/income_router.py`（`/income` 查询 / `/history` / 按天删除）+ `tasks/DailyTrifles/income/ocr.json`；`script_task.py` 新增 `run_income_stat`（开关 `income_stat` 默认关闭）、`config.py` 新增 `IncomeSnapshot`、`assets.py` 新增 8 条 `O_INCOME_*` 并重排、`app.py` 注册 `income_app`、i18n 新增 `income_stat`。**工具 bug**：`apply` 按 `--date=short` 同日提交退化为按 hash 排序（`upstream_sync.py:1142`）致 cherry-pick 顺序错乱报冲突 → 改手工按时间序 cherry-pick，6 条零冲突 |
| 28 | 2026-10-20 | `137610f0`（2 cherry-pick + 1 回归测试） | runhey/dev | 3 / 2 | **邀请确认 ROI（#1939 后续）+ 桌面 Restart 收敛（#1935）**：`I_INVITE_ENSURE` 改 517,553/473,505,409,121；桌面已登录才先停、登录页复用；`a70757b1` 不适用（本地无 `I_BACK_YOLLOW` 旧退出循环） |
| 27 | 2026-10-19 | `a074e599`（8 cherry-pick + 1 手工移植 + 1 回归测试） | runhey/dev + runhey/master | 19 / 13 | **桌面客户端 PR #1887（8 条直合 + roi_pad 服务端化）+ 新 Merge PR 修复（Delegation/WantedQuests/GeneralBattle/WeeklyTrifles/MPay/Restart）**；跳过 5 条（见 §3） |
| 26 | 2026-10-15 | `de7e5616`（手工移植，非 cherry-pick） | xylolit-mu/self（积压 triage 第二轮） | 104 / 3 | **self 积压第二轮**：三源 tip 与批次 25 **逐字相同**（runhey 零新增）→ 台账 hash 过滤后 104 条全部来自 `self`；机械覆盖度 + 逐条语义核实后仅 3 条可落地：GeneralRoom 勾选框阈值入资产（0.8→0.7）、RyouToppa 挑战失败判定（只有等待超时才算失败，上限 4）、WeeklyTrifles 摸鱼入口 `Timer(15)` 超时兜底；另 17 条已覆盖、10 条不适用（OASX 框架结构性差异）、73 条按簇需立项 |

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
| 44 | `ad778fba7` | `d2714287` + 补正 `b18a986a` | fix | DailyTrifles | 商店签到入口点击重试 | 冲突仅 `__main__` 调试行，取本地 `run_guild_donate()`；`run_store_sign` 改为最多 4 次点击、出现 `I_GIFT_SIGN` 即停；**本地补正**：点击未命中时直接退出，避免上游循环无进展空转。**未采纳**同提交的 `I_CHECK_MALL` ROI（1087,413,47,114）与模板：本地已有紫色招牌 + 「商」灯笼三选一识别（批次 9/本地 11-11 修复） |
| 44 | `eb156b16e` | `7f466112` | fix | RealmRaid + Exploration | 突破券数量上限校验并忽略无效识别 | `Exploration/base.py` 冲突（本地用 `O_REALM_RAID_NUMBER.ocr` 而非上游 `_META.ocr_digit_counter`）：保留本地识别方式，仅追加 `0 <= cu <= total == 30` 拦截；`RealmRaid` 新增 `read_ticket_count()`，`is_ticket`/`check_ticket` 与聊天框遮挡识别统一走它；上游自带 `dev_tools/realm_raid_ticket_checks.py` 依赖本地不存在的 `_META` 接口，删除并按本地架构迁入 `tests/` |
| 44 | `27b9f5343` | `ca19f878` | fix | device/screenshot + server/annotator | 标注器预览截图缓存隔离 | 直接 cherry-pick，零冲突（2 文件 +5/-3）：`Screenshot.__init__` 新增仅关键字参数 `frame_cache_name` 并在 `super().__init__` 前赋值（连接期截图也要归属正确）；`register_frame` 用 `self.frame_cache_name or self.config.config_name`；`tool_capture_worker._build_device` 传 `annotator:<session_id>` |
| 44 | —（回归测试） | `b18a986a` | test | tests | 批次 44 回归测试 | 新增 `tests/test_upstream_batch44_fixes.py`（16 项）：签到重试/4 次上限/无进展退出/当日已完成短路、突破券无效读数丢弃与 0 票保留、`is_ticket`/`check_ticket` 阈值、聊天框遮挡计数校验、探索 `activate_realm_raid` 无效读数拦截、`frame_cache_name` 顺序与标注器接线、商店页三变体/签到资产/斗技返回庭院守卫 |
| 43 | `ce9903bf4` | `23a8b8a4` + 补正 `d3b4abab` | fix | Chess | 手牌满且清理无效时出售一张阵容卡 | 直接 cherry-pick，零冲突（2 文件 +15/-2）：`_free_one_hand_slot_for_purchase` 清理后仍无空位则 `sell_one_lineup_hand_card()`；`_buy_shop_slot` 恢复分支改为 `sell_lineup or recovery.type == 'lineup'` 并同步置位两个 cleanup 标记 |
| 43 | `476617e0e` | `28aed3e1` + 补正 `6fb56aa0` | fix | GameUi/AreaBoss/Chess | 删除与 GeneralBuff 重名的 I_CLOSE_RED | 冲突取本地资产（本地已无 `close_red` 引用），仅手工删除 AreaBoss `I_CLOSE_RED` 规则/JSON/png；Chess `script_task.py` 整文件冲突**撤回整文件上游版**，只补 `_burst` 红叉兜底（详见补正提交） |
| 43 | `d38f6e95a` | `ccdf4a63` | fix | AbyssShadows | 确认按钮改用通用资产 I_UI_CONFIRM | 冲突取本地资产后手工删除 `I_ENSURE_BUTTON`/`I_START_ENSURE` 规则 + JSON + 2 张 png；`script_task.py` 自动合并，4 处确认点击全部收敛到 `self.I_UI_CONFIRM` |
| 43 | `0311c1894` | `73c1bfb9` | fix | GameUi/KekkaiUtilize | 未知页关闭顺序 + 种树关闭标识搜索区 | `navigator.py` 冲突保留本地 `I_UI_BACK_CIRCLE` 并追加 `I_PLANT_TREE_CLOSE`；`KekkaiUtilize` 取本地资产，仅把 `I_PLANT_TREE_CLOSE.roi_back` 改为 (711,52,395,143) 并同步 JSON |
| 43 | —（回归测试） | `1fbb5ac2` | test | tests | 批次 43 回归测试 | 新增 `tests/test_upstream_batch43_fixes.py`（25 项）；更新批次 42 门票 ROI 期望为 1119,7,114,32；补 `MetaDemon/md/image.json` 的 `md_win` 条目 |
| 33 | `bf889f02d` | `f9723b8c` | feat | TalismanPass | 收奖励前先识别「任务」页签 | 直接 cherry-pick，零冲突（2 文件 +9/-0）：`run()` 内联 `RuleImage(tp/tp_task_tab.png, threshold=0.8, roi_front=1198,328,30,72, roi_back=1200,310,50,110)` + `appear_then_click(task_tab)`；后续 `c08fe24f9` 再收紧 ROI |
| 33 | `c08fe24f9` | `3ec1bc99` | fix | TalismanPass | 任务页签模板与识别区收紧 | 直接 cherry-pick，零冲突（2 文件 +4/-1）：roi_front (1198,328,36,73) / roi_back (1185,307,64,117)，`tp_task_tab.png` 换为 36×73 版本 |
| 33 | `4944b3df8` | `90930fa5` | fix | KekkaiActivation | 收获奖励识别区跨庭院皮肤扩大 | 直接 cherry-pick，零冲突（2 文件 +16/-16）：8 条 `I_A_HARVEST_*` roi_back 统一为 (750,90,250,230)，`a/image.json` 同步 |
| 33 | `1cc1707bf` | `d93c35ad` | fix | KekkaiActivation | 桌面版「激活」按钮误判防护 | 直接 cherry-pick，零冲突（1 文件 +4/-1）：黄色命中后还需 `I_A_ACTIVATE_GRAY` 同时命中且 `I_A_ACTIVATE_YELLOW.last_score > I_A_ACTIVATE_GRAY.last_score` |
| 33 | `8d499033c` | `cff18d6c` | fix | GlobalGame | 协作邀请素材与坐标更新 | 直接 cherry-pick，零冲突（6 文件 +9/-9）：`I_G_ACCEPT`/`I_G_REJECT`/`I_G_JADE`/`I_G_IGNORE` 换新 ROI 与 4 张 png，`gg/image.json` 同步；**同时更新批次 32 回归基线**（旧值已随新素材失效） |
| 33 | `4b823fdeb` | `a3698bc6` | fix | Component/GeneralInvite | 重新邀请勾选框点击间隔 1→3 | 直接 cherry-pick，零冲突（1 文件 +1/-1）：`invite_again` 的 `I_UI_UNCHECK` 与 `check_and_invite` 对齐 |
| 33 | `cf9fe93ca` | `bae0645f` | feat | Server/annotator | 标注器上传支持选择文件夹 | 直接 cherry-pick，零冲突（2 文件 +56/-19）：`app.js` 分批 20 张上传、扩展名过滤、按名称/大小/时间去重；`left-window.html` 增加 `webkitdirectory` |
| 33 | —（回归测试） | `4ec862c6` | test | tests | 批次 33 回归测试 | 新增 `tests/test_upstream_batch33_fixes.py`（9 项）：TalismanPass 页签 ROI/模板尺寸、KekkaiActivation 8 条 roi_back 与 json 一致、激活误判防护、GlobalGame 4 条 ROI ↔ json ↔ png、GeneralInvite interval=3；并更新批次 32 `GG_NEW_UI_ASSETS` 基线 |
| 34 | `df572d01c` + `181801d1c` + `a3e6e028` | `021be78a` | fix | WantedQuests | 悬赏地点数量 OCR 漏读重试（#2006） | **手工移植（非 cherry-pick）**：抽出 `_parse_location_info`（保留本地 `[数教]` 与全角兼容，未采用上游严格 `数量` 锚点）；首次识别失败时 `copy(info_rule)` 收紧 ROI 为 `(x, y+7, w, h-14)` 重试一次；本地归一化与未知文本告警保留 |
| 34 | `1fd87d347` | `021be78a` | fix | Exploration | 保持探索退出状态（self） | **手工移植（仅 Exploration 2 文件）**：`base.fire` 删除 `page_exp_exit` 时的 `need_exit=False`；`run_on_exp_main` 在 `need_exit` 时先 `quit_exp_main()` 再返回，避免渲染延迟一帧重新开战。EvoZone `_config` 属 self 门票刷取特性，未取 |
| 34 | `23edaa78` | `021be78a` | fix | MetaDemon | 1~6 星召唤票阈值回落 0.8（self） | **手工移植**：`assets.py` 6 条 threshold 0.85→0.8、`md/image.json` 同步；上游 `boss_battle.py` 识别重试本地无对应文件，未取；本地 ROI 保持不变 |
| 34 | `5ba75f9b` | `021be78a` | fix | Component/SwitchAccount | 登录选服「已有角色」OCR 区左扩（#1979） | **手工移植单行**：`O_SA_CHECK_SELECT_SVR` roi `(252,145,97,32)`→`(231,145,102,32)`、area `(248,141,102,38)`→`(231,141,103,38)`；该提交其余内容为 battle_wait 溢出清理与素材清理，判不适用 |
| 34 | —（回归测试 + 源迁移） | `021be78a` | test | tests + dev_tools | 批次 34 回归测试与 nearaura 源迁移 | 新增 `tests/test_upstream_batch34_fixes.py`（10 项）：WQ 半角/全角/教量解析 + 重试 ROI、探索 fire 不清退出标记 + 主界面早退、超鬼王 6 条阈值 ↔ json、选服 OCR ROI；`upstream_sources.json` runhey→nearaura |
| 37 | `dd96057e` | `8334c797` | fix | Component/GeneralBattle + Orochi | 御魂自选活动弹窗遮挡战斗结算 | **手工移植**：新增 `I_GB_CLOSE_RED`（1108,128,45,41，阈值 0.8）+ `gb_gb_close_red.png` + `gb/image.json`；`Orochi.ScriptTask` 新增 `_close_orochi_soul_choice_popup`，并覆写 `_handle_result` / `_handle_missing_battle_page`、在 `_handle_reward` 首部各关一次（关掉后清 `reward_no_battle_ts` 并 CONTINUE），避免弹窗把页面顶成 unknown 后误判战斗结束 |
| 37 | `38a8f00d` | `8334c797` | fix | ActivityShikigami（+ KekkaiUtilize 核对） | 庭院右侧活动栏目轮换找活动入口 | **手工移植（仅 page.py 部分）**：新增 `ACTIVITY_COLUMN_SWITCH_MAX_TRIES=8` 与 `find_activity_entry(task)`（每次截图判 `I_MAIN_GOTO_ACT`，未出现则点 `I_TOGGLE_BUTTON`，8 次仍未出现抛 `GamePageUnknownError`），替换 `page_act` 原先单次 `I_TOGGLE_BUTTON` hook。**寄养开关未引入**：本地 `KekkaiUtilize` 已有 `utilize_harvest`（「是否领取寄养奖励」，关闭即不领），与上游 `disable_utilize_harvest` 同义反向，重复引入会造成两个互相冲突的开关 |
| 37 | `904686c1` | `8334c797` | fix | DemonEncounter | 逢魔 boss 页 3 轮重进仍失败时优雅收尾 | **手工移植**：本地 `find_boss` 末尾 `raise GameStuckError('Cannot enter ... after 3 re-enter rounds')` → `logger.warning(... treat boss as already challenged today)` + `set_next_run(task='DemonEncounter', success=False, finish=True, server=True)` + `raise TaskEnd('DemonEncounter')`；「找不到搜索按钮」的 `GameStuckError` 保留 |
| 37 | `18ededee` | `8334c797` | fix | ActivityShikigami + Component/BaseActivity | pass/boss 门票 OCR 为 0 时先进战复核 | **手工移植**：`BaseAct` 混入本地已有的 `BaseActivity`；`check_tickets_enough` 先清 `_ticket_needs_verification`，pass/boss 且 OCR≤0 时置 True 并返回 True；`_run_common` 遇标记时用 `verify_zero_ticket(..., lambda: enter_battle(max_times=1))` 实探一次，未进战才抛 `TicketsNotEnough`；`enter_battle(max_times=None)` 新增 fallback 模式（`max_times` 显式传入时失败返回 False 而非抛异常，正常路径行为不变） |
| 37 | —（回归测试） | `8334c797` | test | tests | 批次 37 回归测试 | 新增 `tests/test_upstream_batch37_fixes.py`（17 项）：`I_GB_CLOSE_RED` 资产/JSON/PNG 一致性 + Orochi 三处先关弹窗；`find_activity_entry` 命中/8 次放弃/`page_act` hook 不再直挂 `I_TOGGLE_BUTTON`；逢魔 `GameStuckError` 仅剩搜索按钮一处；`BaseAct` 继承 `BaseActivity`、fallback 返回 False、正常路径仍抛 `TicketsNotEnough`、门票 0 置标记、`_run_common` 接线 |
| 38 | `591508f6` | `2dba211b` | feat | MetaDemon | 六星鬼王上供 | **手工移植（仅上供部分）**：新增 `tasks/MetaDemon/assistance.py`（`GhostOffering`：好友列表扫描/按名精确勾选/提交分享/按 `boss_generation` 防重复分享/等待击杀）+ `MetaDemonMode.BOSS_ASSIST` + `MetaDemonAssistanceConfig`（role / friend_names / poll_interval）；`run()` 按 mode 分派；`check_and_switch_ticket(sequence=...)` 支持指定级别，**召唤确认后才设置 `cur_boss_type` 并递增 `boss_generation`**（修复本地原先在开面板前就赋值、会把残留鬼王误判为刚召唤的问题）。**未移植**：门票刷取（`tasks/MetaDemonTicket`）、票池容量预检、上游多模式列表框架 —— 本地无对应模块。**资产无需新增**：`I_MD_INVITE` / `I_MD_INVITE_FRIENDS` / `I_MD_FRIEND_SELECTED` / `O_MD_FRIENDS` / `S_MD_SWIPE_FRIEND_UP` 本地已存在 |
| 38 | —（回归测试） | `2dba211b` | test | tests | 批次 38 回归测试 | 新增 `tests/test_upstream_metademon_assist.py`（11 项）：模式/协助配置默认值与好友名解析去重、分享资产齐全、`run` 分派上供、`check_and_switch_ticket` 的 `sequence` 参数与「召唤后才换代」顺序、`within_limit`、好友名归一化、ASSIST 未实现时的失败收尾、OFFERING 未填好友触发人工接管 |
| 39 | `a787a58a` | `0e2c6da7` | fix | device/minitouch | 低 `max_pressure` 设备点击抛 `ValueError`（PR #2） | **手工移植单行**：`_humanized_pressure` 的 `randint(max(20, top // 2), top)` → `max(1, top // 2)`；设备上报 `max_pressure < 20` 时 low > high 直接抛异常，`click_minitouch`/`long_click_minitouch` 全部失效。常规 `max_pressure=100` 区间 [50,100] 与改前一致 |
| 39 | `3ede58e1` | `0e2c6da7` | fix | atom/animate（部分采纳） | 模板搜索区初始化外扩 + 动画帧比较区固定 | **部分采纳**：新增 `RuleAnimate._crop_roi`（构造时固定为 `roi_front`），`stable()` 两处裁剪统一用它，命中回写的 `roi_front` 不再改变比较区域；搜索区仍用 `roi_back` 下发图像服务。**不采纳**同提交的「`roi_pad` 无条件外扩 2px + 删除 `set_roi_match_padding`」：本地 `roi_pad` 由 `to_service_payload` 下发、桌面模式置 2（批次 27），模拟器保持 0 以保证匹配行为逐位不变（上游自己也留了「资产按运行环境初始化后再删统一扩展」的 TODO） |
| 39 | —（回归测试） | `0e2c6da7` | test | tests | 批次 39 回归测试 | 新增 `tests/test_upstream_batch39_fixes.py`（8 项）：`max_pressure` 1/5/10/19 不抛异常且落在 [1,top]、100 → [50,100]、0 回退 100；`_crop_roi` 等于初始 `roi_front`（RuleImage / RuleClick 两种来源）、首帧裁剪区、命中后 `roi_front` 回写但裁剪区不漂移、服务调用仍透传 `roi_back` 搜索区 |
| 40 | `a86b0e50` 整树 | `2b7f72e0` | feat | tasks/MetaDemon | 超鬼王整模块替换为上游新代际 | `git checkout nearaura-dev/dev -- tasks/MetaDemon` 覆盖 25 文件（assets/config/script_task + `image.json`/`image_2025.json`/`ocr.json` + 18 张模板），删除 36 个旧代际文件（`md_md_*`、`goto_metademon_list.json`、`swipe.json`、`md_check_*`）。**丢失能力**（上游最新亦无）：门票 1~6 星合成、邀请好友、昨日奖励、强力追击开关、按星级切御魂，以及批次 38 刚移植的上供/协助模式 |
| 40 | `226566aa` | `2b7f72e0` | feat | Component/GeneralBattle + base_task | 战斗内鬼王标记 | `O_BOSS_MARK`（「已标记」OCR，roi `379,44,50,21`）、`boss_mark()`/`boss_mark_reset()`、`_boss_mark_flag`；本地 FSM 战斗不回调 `battle_wait`，故该方法当前为上游同源的保留链路（上游同样无调用点） |
| 40 | —（回归测试） | `2b7f72e0` | test | tests | 新代际回归测试 | 新增 `tests/test_metademon_module.py`（12 项）：每张 RuleImage 的 png 存在且与 `image.json`/`image_2025.json` 的 `roiFront`/阈值一致、公开鬼王与 5/6 星规则齐全、旧资产与旧导航已删除、配置默认值 + `auto_tea` 强制 False、`parse_names`/`parse_group_team`/`parse_all`、`md_strategies_N` 展开与拍平、任务继承与入口；删除 `tests/test_upstream_metademon_assist.py` 与 `MetaDemonTicketThresholdTests`（旧代际专有） |
| 41 | `f99d75c2` | `9a2ae877` | fix | module/server | 配置导入把泛型注解误判成 pydantic 模型 | 直接 cherry-pick，零冲突（1 文件 +11/-2）：`_is_model_type` 先判 `get_origin(annotation) is not None → False`，再 `isinstance(annotation, type) and issubclass(annotation, BaseModel)`；`list[Model]`/`dict[str, Model]` 不再抛 `TypeError`，配置导入/导出恢复 |
| 41 | `bf71e3a5` | `f95294d9` | fix | WantedQuests + GlobalGame + BondlingFairyland | 协斗协作类型模板重做、好友邀请筛选放宽 | **手工移植**（冲突根因：上游 regenerator 重排 `assets.py` 且带本地不支持的 `profile="High"`）：只取语义改动——`I_WQ_INVITE_1~3` roi 改 116,385,681 并换图；5 类×3 档协斗类型改整卡识别（`roi_front` 44~59×31~36 图标区、`roi_back` 整卡）；`I_G_JADE/CAT/DOG` 的 `roi_back` 用上游放宽值、阈值 0.8→0.7（勾玉 `roi_front` 保留本地标定 682,518,32,38）；`O_B_BALL_NUMBER` 改 1183,666,68,27；9 张模板随提交落地并同步 `image.json` |
| 41 | `844d3bec` | `690db5bb` | fix | BondlingFairyland | 交换身份恢复单任务内半量切换 | **手工移植**（冲突根因：本地把 handoff1 第二段写在 `run_leader` 尾部并 `raise TaskEnd`，上游改为 `run()` 统一收尾）：新增 `_finish_bondling_task()`、`run_leader` 末尾返回 True；handoff1 先队长段再清零+队员段，handoff2 反向；队员段与 `switch_ball` 循环入口加次数上限，`run_search`/`run_catch` 改用半量后的 `self.limit_count`；`user_status` 说明改写 `zh_CN.xml`（`.qm` 需另行 lrelease 编译才对界面生效） |
| 41 | —（回归测试） | `1bd8a798` | test | tests | 批次 41 回归测试 | 新增 `tests/test_upstream_batch41_fixes.py`（12 项）：`_is_model_type`/`_list_item_model` 泛型注解；handoff1/handoff2 半量切换与计数清零顺序、单一身份仍用完整限次、次数已满时 `switch_ball` 立即退出；GlobalGame/WantedQuests 的 `assets.py`↔`image.json` 数值一致、本批 9 张模板存在、协斗整卡 `roi_back` 更大、契灵球数 OCR 1183,666,68,27；同步批次 32 的 GlobalGame 几何期望值 |
| 42 | `a279ab60`（`tasks/MetaDemonTicket`） | 见 §3.19 | feat | tasks/MetaDemonTicket | 超鬼王门票刷取任务（从整包 sync 中摘取） | **手工移植 + 本地适配**：新增 `__init__.py`/`config.py`/`script_task.py`/`ticket_farming.py`（约 370 行）；`GeneralBattleAssets` 新增结算门票 OCR `O_METADEMON_PASS`（`1126,3,95,39`，`DigitCounter`）+ `gb/ocr.json`；注册 `ConfigModel.meta_demon_ticket`、Activity Task 菜单、`config_manual` 优先级注释 |
| 42 | —（回归测试） | 见 §3.19 | test | tests | 批次 42 回归测试 | 新增 `tests/test_upstream_batch42_fixes.py`（22 项）：配置默认值/模式取值、`ConfigModel` 与菜单注册、门票 OCR 资产 ↔ `gb/ocr.json`、本地 `O_MD_TICKET` 复用、觉醒/探索配置映射、`TicketConfigProxy` 只覆盖目标字段、满票判定（非奖励页不 OCR / 部分票 / 满票 / 无效上限）、`check_ticket_reward` 抛 `TicketsFull` 与完成标记短路、奖励页 hook 注入 |
| 32 | `120c881a` | `242807f9` | fix | Component/Buy | 蓝票多买窗口改用 `buy_more` | 直接 cherry-pick，零冲突（3 文件 +42/-2）：`buy_one_or_more` 改走 `buy_more(number)` 多数量窗口，`MysteryShop` 蓝票不再逐张点 |
| 32 | `be5f3c97` | `2bb9f4a9` | fix | Component/Buy + MysteryShop + RichMan | 蓝票按单价判断，高于 85 勾玉不买 | 直接 cherry-pick（7 文件 +164/-8）：新增 `I_BUY_JADE`(604,537,42,52 / 540,480,200,120) 与 `O_BUY_PRICE`(646,537,60,52，`Digit`)，`buy_one_or_more` 增 `max_price`/`money`/`remain`；`_buy_with_price` 六分支（超价取消 / 读不到价取消 / 单窗买 1 / 够钱买满 / 不够逐张 / 不够 1 张取消）；`_buy_read_price(min_price=40)` 裁剪 `[x+w, y, 60, h]`、`<40` 视为读错；`MysteryShop` 传 `max_price=85` + `more_window=True`，`FriendshipPoints` 传 `money`/`remain` |
| 32 | `47b9064b` | `d00f88b2` | fix | Component/Buy | 蓝票余额不够买满时逐张购买 | 直接 cherry-pick（1 文件 +4/-1）：`_buy_more_default` 用 `buy_more(start, None)` 只买 1 张 |
| 32 | `094b30b9` | `81681f0c` | fix | base_task | `wait_until_disappear` 支持 `timeout`，修复邀请组件报错 | 直接 cherry-pick（1 文件 +10/-1）：`timeout=None` 保持原「一直等它消失」语义；传入时 `Timer(timeout).start()`，超时仅告警（`still visible after ...`）不抛出。**影响全仓所有 `wait_until_disappear` 调用**（默认行为逐位不变） |
| 32 | `a9597e77` | `be3a3790` | fix | Chess | 卖卡与上御魂前清理点击记录 | 直接 cherry-pick（1 文件 +9/-1）：新增 `_reset_click_record(name)`，`sell_hand_card`（`CHESS_SELL_*`）与 `_equip_soul_card`（`CHESS_EQUIP_SOUL_*_SET_*`）拖拽前清同名记录，修复 `GameTooManyClickError` |
| 32 | `329ecfc7` | `e65f63bc` | fix | EternitySea | 队员模式开战前补齐进本、选层与锁队检查 | 直接 cherry-pick（1 文件 +10/-6）：抽出 `_prepare_eternity_sea()`（`goto_page(page_soul_zones)` → `_enter_eternity_sea()` → `check_layer(layer)` → `check_lock(True, I_NEWETERNITYSEA_LOCK, I_ETERNITYSEA_UNLOCK)`），`run_leader`/`run_member` 各调用一次且早于建队/卡死计时 |
| 32 | `e68c2d26` | `5e991f0d` | fix | GlobalGame | 适配接受/拒绝按钮新 UI | 直接 cherry-pick（4 文件 +18/-18）：6 条 `I_G_*` ROI 换新（`gg/image.json` 同步 + png 随提交落地）；共享接受/拒绝按钮被全仓多任务复用 |
| 32 | `921a2b82` | `a948b0d5` | fix | WantedQuests | 适配悬赏封印新 UI，目标名改子串匹配 | 直接 cherry-pick（23 文件 +123/-141）：8 条新 UI 几何 + `O_WQ_NUMBER`(541,14,97,33) / `O_WQ_MONSTER_TYPE`(634,154,483,52, `Full`)；`trace_one` 改 `ui_click_until_smt_disappear(self.I_UI_BACK_RED, stop=self.I_WQ_TRACE_ONE_CHECK_OPENED)`；`execute_mission` 判不想打改为子串匹配（`any(name in monster_name ...)`）；删 legacy `C_WQ_TRACE_ONE_CLOSE`/`I_WQ_CHECK_TASK` 与 2 png；**同时带 `invite/assets.py`(84 行) + `invite/image.json` + 3 png**，故 invite 侧资产与 json 一致（无 `d1ad2c09` 那类 json/assets 漂移） |
| 32 | `2db22cc3` | `1b5c2590` | fix | RichMan/scales | 海汐御魂开启自动选择时一次买完 | 直接 cherry-pick（1 文件 +15/-8）：`enable_book_auto` 分支早退（余额 <400 直接返回）→ `_scales_buy_more(self.I_SCA_PICTURE_BOOK)` + 0.5s + return；手动路径仍走 `_scales_buy_sea_more` |
| 32 | `3f085151` | `e4e7dd4a` | feat | Dokan | 每次运行都尝试开启道馆，不再限定周一 | 直接 cherry-pick（1 文件 +2/-2）：去掉 `datetime.now().weekday() == 0` 判断。本地落点在 `run_on_dokan_map`，由既有 `found_dokan_cnt > 0 → raise DokanNotStartedError` 守卫保证每次运行只尝试开馆一次（即 `1e18c251` 的等价语义，见 §3.11） |
| 32 | `506564c6` | `8f0845b4` | fix | Costume + atom/image | 替换皮肤模板后清掉缓存的模板图 | 直接 cherry-pick（2 文件 +12/-1）：`RuleImage.refresh()` 清 `_image`/`_kp`/`_des`/`_match_init` + `del_cached_property('name'/'kp'/'des')`（**不引入本地没有的 `_mask`/`_mask_loaded`**）；`costume_base` 在 `asset_before_object.file` 赋值后调用 `refresh()` |
| 32 | `d1ad2c09` | `d68467e5` | fix | Chess | 放宽棋局「打开阵容预设」的搜索区 | cherry-pick 本体（1 文件 +1/-1）：`I_OPEN_LINEUP` roiFront (271,17,33,34) / roiBack (196,7,120,54)。**本地自检发现上游只改 `c/image.json` 而未同步 `assets.py`**（本地资产以 `assets.py` 为准）→ 追加补正 `4698b48c`，并在回归测试中钉死 assets ↔ json 一致 |
| 32 | —（自检补正） | `4698b48c` | fix | Chess | 棋局 `open_lineup` 新搜索区同步到 assets.py | 见上行；`tasks/Chess/assets.py` 的 `I_OPEN_LINEUP` roiBack 对齐 json，避免「json 改了、运行时仍用旧 ROI」 |
| 32 | `91f7d916` | `2b9092d3` | feat | Server/annotator | 标注器任务下拉显示中文名 | 直接 cherry-pick（1 文件 +67/-1）：`app.js` 新增 `TASK_LABELS`（Chess 百鬼棋局 / Dokan 道馆 / EternitySea 永生之海 / MysteryShop 神秘商店 / WantedQuests 悬赏封印 等），`createOption(select, name, zh ? \`${zh}（${name}）\` : name)`；纯前端显示，不改任务调度 |
| 32 | —（回归测试） | `0b5a35da` | test | tests | 批次 32 回归测试 | 新增 `tests/test_upstream_batch32_fixes.py`（932 行 / 10 个测试类 / 68 项 + 33 subTest）：Buy 多价购买六分支与窗型路由、`wait_until_disappear` 超时语义、Chess 卖卡/上御魂点击记录、Costume 模板刷新、EternitySea 开战准备顺序、Scales 一次买完、Dokan 每次开馆 + 本地状态机保留、WantedQuests/GlobalGame 新 UI 几何 + json/png 一致性、标注器中文名 |
| 31 | `4354df46` | `02dff57b` | fix | Dokan | 修正道馆馆主名模板（PR #1963） | 直接 cherry-pick，零冲突；`tasks/Dokan/res/res_ryou_dokan_center_guanzhu_xiuxi.png` 换为上游修正版（3339 → 1864 字节，sha256 `26ccd129…3694b9`），`image.json` 同步 |
| 31 | `8bbf87b8` | `091eeb02` | fix | Dokan | 馆主模板阈值 0.8 → 0.7（PR #1963 后续） | 直接 cherry-pick，零冲突；仅 `I_CENTER_GUANZHU_XIUXI` 阈值一处 |
| 31 | `51dbf564` | `ef8bed27` | feat | GeneralBuff + GuildBanquet | 加成开关资产重名拆分 + 兼容第二种寮宴会旗帜 | **手工移植（非 cherry-pick）**：`I_OPEN_YELLOW`/`I_CLOSE_RED` → `I_BUFF_*` 并新增 `I_GOLD_*`/`I_EXPERIENCE_*` 四套（threshold 0.6，ROI 沿用旧值，未引入上游 `profile` 字段）；`general_buff.py` 新增 `set_switch_area(area, kind)`，gold/exp/awake+soul 分别改用对应类型；`gb/image.json` 与 4 张新模板同步；`GuildBanquet` 新增 `I_BANQUET_FLAG_2`（972,12,33,60 / 967,7,43,70）+ `res_banquet_flag_2.png`，`script_task.py` 新增 `_banquet_flag_visible()` 并在入口与循环两处替换，**保留本地 `goto_page` 导航**（未引入上游 `finish_task_navigation()`/frame 相关 import） |
| 31 | `1410590f` + `fa7a87e7` + `47a3a3bc` | `d3284573` | fix | Chess | 商店合法重复点击不再触发 `GameTooManyClickError` | **手工移植（非 cherry-pick）**：`_clear_economy_click_history` 扩展为清理 `I_EXPERIENCE`/`I_REFRESH`/`C_SHIKIGAMI_1..5` 共 7 条；`_buy_shop_slot` 点击前清理 + 购买成功分支再清理（旧卡记录不顺延）；`_click_shop_refresh_and_confirm_slots` 仅清理实际变更槽位（`changed`），未变更槽位保留原阈值保护 |
| 31 | —（回归测试） | `727ebe58` | test | tests | 批次 31 回归测试 | 新增 `tests/test_upstream_batch31_fixes.py`（17 项）：Dokan 阈值/JSON/模板 sha256；GeneralBuff 三类资产拆分、`set_switch_area` 落点、各开关调用类型；GuildBanquet `I_BANQUET_FLAG_2` 与两处调用；Chess 7 条记录清理、容错、买卡前后顺序、刷新后仅清变更槽位 |
| 30 | `51115b4a8` | `21ce6c13` | fix | Server/annotator | 标注工具停止连接导致 Web 服务卡死 | 直接 cherry-pick，零冲突（本地 4 文件与上游逐字一致，`git apply --check --binary` 干净）：`tool.py` 新增 `EMULATOR_CAPTURE_PROCESS_JOIN_TIMEOUT_NETWORK_SECONDS = 8.0`/`_TERMINATE_WAIT_SECONDS`/`_KILL_WAIT_SECONDS`/`_REMOTE_SCREENSHOT_METHODS`、`_drain_status_queue` 改局部绑定队列消除竞态；`tool_capture_worker.py`/`tool_router.py`/annotator `app.js` 同步 |
| 30 | `a9eb4843c` | `f078e039` | fix | GameUi | 导航交替换路时空转不报错 | 直接 cherry-pick，零冲突：`tasks/GameUi/navigator.py` 两处 —— (a) 删除 `if path_signature != last_progress_signature: progress_timer.reset()` 改为只赋值；(b) 失败计数改跨边累计（`repeated_failure_count += 1`），不再换边归 1 | 本地 `navigator.py:902-905`/`:913-917` 与修复前逐字相同 → 确有同缺陷 |
| 30 | `9f07623b5` | `112de0e4` | feat | Server | 新增模拟器画面截取接口 | 直接 cherry-pick，零冲突：新增 `module/server/screen_router.py`（`APIRouter(prefix="/screen")`、`SCREEN_DIR = Path('./log/screen')`、`CAPTURE_TIMEOUT_SECONDS = 15`、`_capture_lock`）与 `module/server/screen_capture_worker.py`，`app.py` +2 行（import + `include_router(screen_app)`） | 叠加式新增，不改现有 adb 截图/采集链路 |
| 30 | —（回归测试） | `acc7e8c7` | test | tests | 批次 30 回归测试 | 新增 `tests/test_upstream_batch30_fixes.py`（17 项）：导航 3（交替换路能超时抛 `GPageUnknownError`、第 3 次跨边失败触发 `close_unknown_pages`、源码钉死修复）+ 标注工具 7（停止超时分级 8.0/2.5、`_REMOTE_SCREENSHOT_METHODS`、`stop()` 逐级 terminate→kill→如实报错、`_drain_status_queue` 容 `ValueError`、`_release_device` 告警、`tool_router` 2s 超时）+ 画面 6（名称清洗/路径布局/错误文案/路由注册） |
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
| 13 | `5a2d99bf` | `9e6b3b6e` | fix | FrogBoss | 对弈竞猜商店弹窗兜底与结束标志二次确认 | 手工移植（非 cherry-pick）：新增 `close_frog_mall()`/`confirmed_finish_marker()`/`C_BET_REWARD_CLOSE` 并接入记录页开/关、进入、主循环、竞猜成功分支、`do_bet`、`confirm_bet`；确认流程关闭奖励详情由 `C_REWARD_2`（中心 137,370，左侧商店气泡区）改为 `C_BET_REWARD_CLOSE`（1075,452）；新增 `fb_frog_mall.png`/`fb_forg_mall_close.png`（取自上游）、`assets.py`+`image2.json` 登记、`test_betting_flow.py` 新增 3 用例并改断言 |
| 14 | `c56e2c9b`（dev）；同源更早 `028ca1f8`（self） | `018a4ad4` | fix | Exploration | 探索大地图选关适配「主线/玩法」tab（最小修） | 手工移植，**只取主线一侧**（上游另含 `C_CLICK_PALY_TITLE`/`I_CHECK_PLAY_TITLE` 与 prio-60 tab 页 + `inherit_transitions` + 分发表改造，**均未引入**）：① `assets.py`+`res/click.json` 新增 `C_CLICK_MAIN_TITLE`(1070,174,77,28)；② `assets.py`+`res/image.json` 新增 `I_E_CHECK_MAIN_TITLE`（roi_back 1069,222,113,336、阈值 0.85）；③ 新增 `res/res_check_main_title.png`（与上游 **字节相同**，blob `cb81854b`）；④ `base.py` 新增 `ensure_mainline_tab()`（`appear(I_E_CHECK_MAIN_TITLE)` → 缺则 `click(C_CLICK_MAIN_TITLE)` + `wait_until_appear`）并在 `open_expect_level` 首行调用。**本地改名**：上游 `I_CHECK_MAIN_TITLE` → 本地前缀惯例 `I_E_CHECK_MAIN_TITLE` |
| 15 | —（本地自研，无上游来源） | `7e98ce39` | fix | Exploration | 候补式神按稀有度优先级填充，无可用时不再让任务失败 | `fill_shikigami` 重写：① 先点 `C_CLICK_STANDBY_TEAM`（**必须**，否则在列表里选卡完全不生效）；② 面板已开判据改用左下角 `I_RS_*_SELECTED` 徽标（`I_E_OPEN_SETTINGS` 不可靠）；③ 新增 `switch_alternate_class`（**带 15s 超时**：点当前徽标开扇形菜单再点目标类；共享组件的 `switch_shikigami_class` 在「当前徽标不是『全部』」时会死等『全部』徽标而卡死）；④ 逐类长按 `L_ROTATE_1..4` 上卡（长按会把该式神的重复副本一次上满，实测素材每次 +9~10），连续 2 轮无进展即换下一类，≥40 收手；⑤ 全部类别无果只 `logger.warning` 跳过，**不再 raise**。`config.py` 删除 `ChooseRarity` 与 `choose_rarity` 字段（pydantic 忽略多余键，旧配置仍可加载）。**真机实测**：面板预置 SP → 自动切素材 → 长按 4 卡位 → **47/50** |
| 16 | —（本地自研，无上游来源） | `2f0dabda` | fix | Login | 启动/登录流程补「确认退出探索吗」弹窗处理 | `tasks/Component/Login/service.py` 的已知弹窗处理链新增一条：`appear_then_click(ExplorationAssets.I_E_EXIT_CONFIRM, interval=1)` → 点确认退回庭院（惰性导入，沿用文件内既有写法）。**触发链路**：手动/测试把游戏留在探索页 → 账号启动 → 登录服务 BACK 触发「确认退出探索吗：」→ 只认 `I_LOGIN_YELLOW_CLOSE` → 连点 12 次 → `GameTooManyClickError` → app 重启重试 → `CRITICAL Login failed` / `Request human takeover` → 进程退出（2026-10-09 20:24:18 少时之约）。**注**：该资产早已在 `navigator.DEFAULT_UNKNOWN_CLOSERS`（navigator.py:51）与 `page_exp_exit` 中生效，故仅登录服务缺失此环 |
| 17 | `4e4e9079f` | `9bb8a6ad` | fix | DemonEncounter | 修正重进地图导航（重试 2→3 轮） | 手工移植（非 cherry-pick）：本地该处已分叉（页面 `page_rwt`、宝箱 `I_DE_BOX_CENTER` / 勾玉 `I_JADE_50` 弹窗处理），仅取该提交语义改动 —— 重进 `goto_page(page_demon_encounter)` → `goto_page(page_town)`、搜索重试 `range(1,3)` → `range(1,4)`、每轮集结点击 `range(1,3)` → `range(1,4)`，日志/注释同步 `/2`→`/3`、`2次`→`3次`；导入 `page_demon_encounter` 改 `page_town`（前者不再使用）；`GameStuckError` 本地已导入 |
| 18 | runhey/dev `general_battle.py:82`（**机制移植**，无对应独立补丁提交） | `f585d8b2` | fix | RealmRaid | 退四改走 `run_general_battle_back(exit_four=True)`，修复战后确认弹窗卡死 | **机制移植**：本地/self 的退四实现（`build_quick_exit_config` + `fire_again`）快速退出战斗后残留「确认退出战斗吗」(`I_EXIT_ENSURE`)，`fire_again` 开头 `wait_until_appear(I_FIRE_AGAIN)` 被挡 → ~55s → `GameStuckError`（实例 2026-10-10 18:34:20 少时之约）；上游 dev 退四用 `run_general_battle_back(exit_four=True)` 显式走完「退出 → 退出确认 → 失败确认」整链。改法：① 本地 `tasks/Component/GeneralBattle/general_battle.py` 新增 `run_general_battle_back(config=None, exit_four=False)`（复用已有资产 `I_PREPARE_HIGHLIGHT`/`I_PRESET`/`I_PRESET_WIT_NUMBER`/`I_EXIT`/`I_EXIT_ENSURE`/`I_FALSE`）；② `tasks/RealmRaid/script_task.py` 退四分支 `run_general_battle(build_quick_exit_config)+fire_again` ×4 → `fire+run_general_battle_back(exit_four=True)` ×4，随后统一 `fire+run_general_battle`，删 `handled_first_target`。**未改**共享 `exit_battle`（避免波及他任务）；`fire_again` 保留为未用方法。**待实机验证** |
| 19 | —（本地自研，无上游来源；上游无此重连守卫） | `7654a223` | fix | GameUi | 收紧重连守卫 OCR 判据，修复吉闻弹窗误判卡死 | **本地自研**：`f5a0891a` 引入的重连守卫判据 `O_UI_CONNECTING`（`mode="Full", keyword="连接"`）经 `RuleOcr.filter` 的**单字兜底**（`module/ocr/base_ocr.py` 该处自带 TODO），把吉闻「一键祝福」输入框「欧运连连」的「连」、「接受/直接」的「接」误判为断线重连 → 守卫原地等待、不再点击 → ~74s → `GameStuckError`（实例 2026-10-11 08:11:53 少时之约 DailyTrifles，截图弹窗「一键祝福所有好友」）。改法：`tasks/GlobalGame/assets.py` + `tasks/GlobalGame/ui/ocr.json` 将 `O_UI_CONNECTING` 改为 `mode="Single", keyword="正在连接"`（精确匹配，`ocr_appear` 走 `result == keyword`，不再触发单字兜底）；`base_task.py` 守卫逻辑不变。**新增回归测试**：`tests/test_reconnect_guard.py`（判据不误伤「欧运连连/接受/孤立单字」、真正的「正在连接」必须命中；守卫非重连帧零副作用、重连帧先清点击/卡死记录）、`tests/test_realm_raid_exit_four.py`（退四链路 `I_EXIT→I_EXIT_ENSURE→I_FALSE` 顺序与返回 True）。**上游检索（三源 403 条）**：无该守卫的补丁（本地自研）；吉闻相关 `9be90329`（master/dev）、`296dda06`（self）经核实本地已有 `page_friends_luck`/`O_LUCK_MSG`/`I_CLOSE_LUCK_RED`，判为**已覆盖**，不合并。**待实机验证**：真实「正在连接……」弹窗的 OCR 文本是否恰为「正在连接」；若含省略号等偏差，需再微调 keyword。**注**：既存 `tests/test_hero_test_skill_fallback.py` 已失效（patch 不存在的 `Timer`，7 errors），与本次无关，未处理 |
| 20 | `ca7a4189` | `d99afd22` | fix | GeneralInvite | 点击「默认邀请」后加 0.8s 延时等 UI 刷新 | 根因：点 `I_I_NO_DEFAULT` 后立即截图判 `I_I_DEFAULT`，UI 未渲染完 → 无法 break → 重复点击（#1881）。该文件其后被 `84eda193` 重写为共享资产，0.8s 延时已并入本地结构 |
| 20 | `fda09fde` | `f71a1ddb` | fix | GlobalGame | 奖励图标匹配优化并去重资产 | `ui_ui_reward.png` 更新、删 `ui_ui_rewards.png` 与 `Exploration res_get_reward.png`；DemonEncounter/Exploration/FrogBoss `assets.py` 同步。自动合并零冲突 |
| 20 | `5d546f0b` | `5133afc6` | fix | GlobalGame | 保留现行与历史「确认/取消」按钮资产 | 更新 `ui_ui_confirm.png`/`ui_ui_cancel.png` 并新增 `_old` 变体（`I_UI_CONFIRM_OLD`/`I_UI_CANCEL_OLD`）；零冲突 |
| 20 | `cdde0e49` | `97c5f0ce` | refactor | GlobalGame | 退出/刷新弹窗改用共享确认按钮 | 删 `GeneralBattleAssets.I_EXIT_ENSURE`（+`gb_exit_ensure.png`）、`RealmRaidAssets.I_FRESH_ENSURE`（+`res_fresh_ensure.png`）；AbyssShadows/GeneralBattle/Duel/RealmRaid 调用点改 `I_UI_CONFIRM`。**连带**：批次 18 退四链路内的 `I_EXIT_ENSURE` 一并替换为 `I_UI_CONFIRM`，`tests/test_realm_raid_exit_four.py` 已同步更新 |
| 20 | `71e33265` | `981904a6` | refactor | SwitchSoul | 皮肤流程复用共享确认按钮 | 删 `SwitchSoulAssets.I_SOU_SWITCH_SURE`（+png）、`CostumeShikigamiAssets` 及 sk1~sk12 的 `sk*_sou_switch_sure_*.png`；`GeneralBattle`/`RealmRaid`/`AbyssShadows`/`costume_*`/`switch_soul.py` 调用点改 `self.I_UI_CONFIRM`；**本地专有 `QuickLoadout` 同步迁移**（2 处 → `I_UI_CONFIRM`） |
| 20 | `84eda193` | `1463372e` | fix | GeneralInvite | 邀请确认改用共享 UI 资产 #1915 | 删 `GeneralInviteAssets.I_GI_SURE`/`I_GI_CANCEL`/`I_I_DEFAULT`/`I_I_NO_DEFAULT`（+6 png）；`general_invite.py` 改 `I_UI_CONFIRM`/`I_UI_CANCEL`/`I_UI_CHECK`/`I_UI_UNCHECK`；**冲突三处取本地结构**（`timeout_timer`/`is_in_room` 守卫、`sleep(0.8)`）；**本地专有引用同步迁移**：`BondlingFairyland`/`EternitySea`/`EvoZone`/`Orochi`/`OtherWorldTwilight` 的 `I_GI_SURE` → `I_UI_CONFIRM`，并删本地重复的 `BondlingFairyland/general_invite.py` |
| 20 | `9ce0fd2f` | `317f3170` | fix | GameUi | 未知页恢复新增圆形返回按钮 | `tasks/GameUi/navigator.py::DEFAULT_UNKNOWN_CLOSERS` 末尾加 `GlobalGameAssets.I_UI_BACK_CIRCLE`；零冲突 |
| 20 | —（回归测试） | `413f8cda` | test | tests | 批次 20 回归测试 | 更新 `tests/test_realm_raid_exit_four.py`（`I_EXIT_ENSURE`→`I_UI_CONFIRM`，链路 `I_EXIT→I_UI_CONFIRM→I_FALSE`）；新增 `tests/test_shared_ui_assets.py`（共享资产存在 / 私有资产已删 / 任务类经 MRO 解析 `I_UI_CONFIRM` / 未知页兜底含 `I_UI_BACK_CIRCLE`） |
| 21 | `4f0a4856` | `56ff7902` | fix | MemoryScrolls | 用最大按钮代替滑动并限制捐献轮数 | 直接 cherry-pick，**零冲突**：新增 `C_MS_MAX_S/M/L`(1106,116/258/398,36,36) + `ms/click.json` 3 项；`contribute_memoryscrolls` 外层改 `for i in range(1, max_rounds+1)`(上限 10)、每行「最大」按钮点 2 次（`sleep(0.3)`）代替 3 次 `swipe`、内层等待捐献动画同样限 10 次并加超限告警。`from time import sleep` 本地已导入 |
| 21 | `d638c11f` | `38d8db64` | fix | Duel | 检测 MVP 分享页（分享按钮模板） | 冲突手工解决（`assets.py`/`image.json`）：上游 `I_D_VICTORY_SHARE` 用 `Masked template matching`，而本地匹配框架（`module/image/runtime.py::_match_rule` 仅认 Template/Multi-scale/Sift，未知 method **raise ValueError**）不支持掩码 → **裁剪掉被掩码的雾化左缘**（模板列 `28:72`，90×120 → 44×120），改 `Template matching`，阈值 0.8 沿用；`roi_front` 随之 `1100,580,90,120` → `1128,580,44,120`（`roi_back` 保持 `1080,560,130,160`）；**删除未使用的 `duel_d_victory_share_mask.png`**；`is_battle_win` 追加 `or self.appear(self.I_D_VICTORY_SHARE)`；**保留本地专有 `I_D_WIN_SHARE`（拔得头筹）与 `I_WHITE_DOG`**，**不并入上游上下文里的 `I_D_TRY`**（本地无 `duel_d_try.png`，属另一未同步特性） |
| 21 | —（回归测试） | `25a4cdeb` + `e39e555b` | test | tests | 批次 21 回归测试 | 新增 `tests/test_memory_scrolls_contribute.py`（不再 `swipe`、每轮 6 次「最大」按钮、轮数上限 10、已满即返回）；新增 `tests/test_duel_victory_share.py`（资产存在且 method 为本地可用的普通模板匹配、模板尺寸与 `roi_front` 一致、`image.json` 同步、分享页计入 `is_battle_win`、原胜利判定不受影响）；补 `tests/test_realm_raid_exit_four.py`（退四实机延迟弹窗 + 非退四回归） |
| 22 | `8753481b` | （手工移植 `ede87a14`） | feat | image | 新增掩码模板匹配 | **服务端化移植**（本地匹配走 RPC，上游 runhey 版 `51582666` 的客户端落点不适用）：`module/image/runtime.py` 新增 `_resolve_mask_path`/`_load_template_mask`/`_sanitize_match_result`，`TemplateEntry.mask` + `_get_template_entry(with_mask=True)` 且缓存指纹纳入掩码 `mtime:size`，`_match_rule`/`_match_all_template` 放行 `Masked template matching`（掩码缺失或尺寸不符自动回退普通匹配），`_template_is_degenerate` 改按「掩码非零区域」判定，`_template_match_image` 支持 `mask=`；`module/atom/image.py` 补 `METHOD_MASKED_TEMPLATE_MATCH`/`is_masked_template_match`/`test_match` 分派；`module/server/annotator_rule_schema.py` 下拉补选项。**未采用**上游 4 元组 `extra`（scale 回显）——本地无消费方（`assets_test.py` 未入库） |
| 22 | —（回归测试） | （含于 `ede87a14`） | test | tests | 批次 22 回归测试 | 新增 `tests/test_masked_template_match.py`（20 项，本机 `pytest` 实跑全绿）：掩码剔除变化背景后仍命中且坐标正确（普通匹配落榜对照）、掩码缺失/尺寸不符回退且分数与普通匹配逐位一致、`match_all` 支持掩码、掩码参与缓存指纹、退化判据按参与区域、同色窗口 nan/inf 无假阳性、普通匹配分数与位置对照 cv2 一致、多尺度/SIFT 分派与未知 method `raise ValueError` 不变、客户端 method 透传、全仓 `image.json`/`assets.py` method 白名单与标注器选项一致 |
| 23 | `92578cd0` | `95cfcb47` | fix | Exploration | 修正突破券数量 OCR 区域 #1926 | 直接 cherry-pick，**零冲突**：`O_REALM_RAID_NUMBER1` roi 920,12,78,30（area 919,12,80,30）；`res/ocr.json` 同步；`O_REALM_RAID_NUMBER` 保持 739,11,78,37 不受影响 |
| 23 | `916e6eb8` | `44881fa6` | fix | GlobalGame | 更新 `ui_ui_check`/`ui_ui_uncheck` 勾选框素材 | 直接 cherry-pick，**零冲突**；落地 blob 与上游一致（check=`0a21262c…`、uncheck=`eb41e476…`）；与 `5b556e92` 的 `I_UI_UNCHECK` roi_front 调整成对 |
| 23 | `5b556e92` + `e8df3ae0` | `7aff707d` | fix | GlobalGame / Login / GeneralInvite | 复用共享取消按钮 + 放宽默认邀请点击间隔 | **手工移植（非 cherry-pick）**——本地登录已迁 `tasks/Component/Login/service.py`，上游仍在 `tasks/Restart/login.py`：① `assets.py`+`ui/image.json`：`I_UI_CONFIRM` roi_back 643,389,214,95→**643,345,231,320**、`I_UI_CANCEL` 356,384,276,125→**356,384,275,256**、`I_UI_UNCHECK` roi_front 567,343,33,36→**545,343,33,36**；② `service.py` 三处登录弹窗关闭（取消继续战斗 / 关闭视频 / 关闭绑定手机）改共享 `I_UI_CANCEL_SAMLL`，`GameUi/default_pages.py` 进入钩子 `RestartAssets.I_CANCEL_BATTLE`→`GlobalGameAssets.I_UI_CANCEL_SAMLL`（不改会 AttributeError）；③ 删 `Restart/assets.py` 的 `I_WATCH_VIDEO_CANCEL`/`I_LOGIN_LOGIN_CANCEL_BIND_PHONE`/`I_CANCEL_BATTLE` + `login/image.json` 3 条目 + 3 png；④ `general_invite.py::check_and_invite` 的 `I_UI_UNCHECK`(L633)/`I_UI_CONFIRM`(L643) interval 1→**3**（`invite_again`/`check_then_accept` 维持 1，与上游改动范围一致）。上游 `ActivityShikigami`/`harvest` 段与本地结构不符 → **丢弃**（本地无 `I_CHECK_BATTLE_MAIN`/`I_UI_BACK_YELLOW` 上下文、无 `I_HARVEST_MAIL_CONFIRM`） |
| 23 | —（回归测试） | `1bfa8b4a` | test | tests | 批次 23 回归测试 | 新增 `tests/test_shared_ui_assets_followup.py`（共享勾选框素材 blob hash + `I_UI_UNCHECK` roi + `image.json` 一致 / `Restart` 私有资产与 3 png 已删 / `service.py` 三处 + `default_pages` 钩子引用 `I_UI_CANCEL_SAMLL` / `check_and_invite` 用 interval=3）+ `tests/test_exploration_realm_raid_ocr.py`（`O_REALM_RAID_NUMBER1` roi+area、`O_REALM_RAID_NUMBER` 不变、`mode=DigitCounter`、`res/ocr.json` 同步）；两文件共 **18 项，本机 `pytest` 全绿** |
| 24 | —（本地自研，无上游来源；上游 `990c45900`/`55f51238f`（§3.6）针对的是 `task.config.general_battle_config` 缺失的**另一处** AttributeError，本地 `getattr` 实现已覆盖，与本缺陷无关） | `0b68a9bc` | fix | GeneralBattle | 修复 `exit_battle` 在裸兜底对象上抛 `AttributeError` | 单点改法：`GameUi.get_current_page(self)` → `GameUi.detect_page_in(self, page_battle_result, page_reward, include_global=False)`（与 `run_general_battle` 一致，裸兜底对象与真实任务通用）。新增回归测试 `tests/test_general_battle_exit_fallback.py`（修复前精确复现 `_detect_current_page` 缺失）；**该路径突发触发、对所有任务通用**（`page_battle*` 为 global 页且挂 `handle_battle_page` 钩子）——后续 `bb2dd032` 追加「直接驱动生产真造兜底对象」用例（本模块 10 项）；重定基于批次 23 后两模块 16 项本机 `unittest` 全绿 |
| 25 | `bedff718`+`985ac267`+`5770f91e`（PR #1934，合并 `124acb68`） | `6ec09b31` | fix | Duel | 斗技开战前等待增加超时与点击上限 | **手工移植（非 cherry-pick）**：上游把 `ui_click(O_BATTLE_HAND, O_BATTLE_AUTO, interval=0.8)` 改为 `interval=6, timeout=45`（上游 `ui_click` 自 `13cf4303` 才有 `timeout` 参数）；**本地 `BaseTask.ui_click` 无 `timeout`** → 改用语义等价的 `ui_click_until_appear_or_timeout(..., interval=6, timeout=45)`（主体源 `05298287`，本地 6+ 处在用）。新增回归测试 `tests/test_duel_setup_wait_timeout.py`（4 项，本机实跑全绿） |
| 28 | `b1c7186c` | `796fe7ec` | fix | GeneralInvite | 更新「想做的事」邀请确认 ROI（#1939 后续） | 冲突取上游新值：`I_INVITE_ENSURE` roi_front `710,544,132,60` → `517,553,132,60`、roi_back `486,532,373,84` → `473,505,409,121`；`gi/image.json` 同步；阈值 0.8 不变 |
| 28 | `107e9542` | `68a2ef07` | fix | Restart | 桌面客户端重启时避免提前关闭导致退出导航被打断（#1935） | 直接 cherry-pick（本地 `app_restart` 桌面分支已有同位置）：`if self.device.app_is_running(): self.device.app_stop()` 后再 `_desktop_start_and_login()`；停在登录页（未运行）则直接复用 |
| 28 | —（回归测试） | `994864c1` | test | tests | 批次 28 回归测试 | 新增 `tests/test_upstream_batch28_fixes.py`（4 项：ROI/阈值、image.json 同步、roiBack 覆盖 roiFront、WantedQuests 仍用共享确认）；更新 `tests/test_upstream_batch27_fixes.py` 桌面重启两分支 |
| 29 | `802643de` | `78cc37ff` | feat | DailyTrifles | 新增每日收益统计 | 直接 cherry-pick（按时间序），零冲突：新增 `tasks/DailyTrifles/income/ocr.json` + `assets.py` 8 条 `O_INCOME_*` 重排 + `config.py` `IncomeSnapshot` + `script_task.py` `run_income_stat`（`income_stat` 开关默认关闭）+ i18n `income_stat` |
| 29 | `97575ca7` | `da0cb2c8` | refactor | DailyTrifles | 每日收益改为从日志读取 | 直接 cherry-pick，零冲突 |
| 29 | `a0fe1e8d` | `3cef793a` | feat | DailyTrifles / server | 新增每日收益查询接口 | 直接 cherry-pick，零冲突：新增 `module/log_income.py`、`module/server/income_router.py`；`module/server/app.py` 追加 `income_app` 的 import + `include_router`（本地 `NoCacheStaticFiles` 与既有 5 个路由保留） |
| 29 | `f3c61ba4` | `b2fcf4ac` | feat | DailyTrifles | 收益快照另存日汇总 | 直接 cherry-pick，零冲突：日汇总 `log/income/<配置名>.jsonl` 突破日志 7 天限制（`cleanup_logs` 只递归 `error` 目录，其余子目录跳过）；日汇总名用 `income_store_name` 保留全名（不按首个下划线截断，避免 `大号_日常`/`大号_活动` 互相覆盖） |
| 29 | `e6b00fbe` | `fd0fdbf2` | feat | DailyTrifles / server | 收益支持历史查询与按天删除 | 直接 cherry-pick，零冲突：删除留「墓碑」（`deleted: true`）挡住日志回退，避免 7 天内日志把已删记录「复活」 |
| 29 | `83377a19` | `26045955` | fix | DailyTrifles | 修复统计每日收益缺少分组常量导致的 NameError | 直接 cherry-pick，零冲突：补回 `INCOME_MAIN`/`INCOME_SCALES`/`INCOME_MALL`（抽取公共模块时遗漏） |
| 29 | —（回归测试） | `4540f271` | test | tests | 批次 29 回归测试 | 新增 `tests/test_upstream_dailytrifles_income.py`（19 项：`log_income` 快照解析/折行续段/日汇总读写与墓碑/日期并集/基准日查找/历史查询/报告做差 + `script_task` 分组常量覆盖性（回归 `83377a19`）/顶栏数字解析 + 服务端 `/income` 路由注册守卫）；本机 `pytest` **19/19 全绿**；全量 `tests/` 由 czr 基线 148→**167 passed**、失败数保持 9（既有 HeroTest `Timer` AttributeError 与 SwitchOnmyoji 环境性失败，czr 上同样失败） |
| 27 | `d0bc419a` | `beebb926` | feat | DesktopClient | 新增桌面客户端窗口后端（后台截图/窗口消息输入/PID 绑定） | 直接 cherry-pick，零冲突：新增 `module/device/method/desktop_impl.py`、`dev_tools/bind_desktop_window.py`；`module/base/cBezier.py`/`connection_attr.py`/`handle.py`/`windows_impl.py` 同步 |
| 27 | `cafe832b` | `9ff651c3` | feat | DesktopClient | 设备层接入桌面模式（免 adb、无模拟器生命周期） | 直接 cherry-pick，零冲突；`app_control`/`connection`/`method/adb`/`platform_windows`/`screenshot` |
| 27 | `0e7edcc8` | `d9b7220f` | feat | DesktopClient | Device 层桌面生命周期（DesktopDevice mixin） | 直接 cherry-pick，零冲突；新增 `module/device/desktop_device.py` |
| 27 | `7c5f380b` | `2db43f1d` | feat | image | 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差 | **手工移植（服务端化）**：上游改 `module/atom/image.py` 的本地同步匹配（`_pad_roi`/`corp`/`match`），本地匹配走图像服务 RPC → 在 `module/atom/image.py` 保留 `ROI_MATCH_PAD`/`DESKTOP_ROI_MATCH_PAD`/`set_roi_match_padding()` 并把 `roi_pad` 随 `to_service_payload()` 下发；`module/image/runtime.py::_normalize_rule` 四边外扩（左上夹 0），命中坐标仍以原图 ROI 原点回算。默认 0 时逐位不变 |
| 27 | `3252b071` | `7fdbe133` | fix | Login/GameUi | 桌面登录期处理 MPay 弹窗，避免误判未知页面 | 冲突取本地 `tasks/Restart/login.py`（仅兼容 shim，实际实现已迁 `tasks/Component/Login/service.py`）；自动并入 `navigator.py` 的 `app_lost_login()` 守卫；**MPay 逻辑在 `2db43f1d` 移植进 `service.py`**（5 次封顶 + 截图后二次检查） |
| 27 | `6ea67658` | `56d01ead` | fix | Restart | 桌面客户端启动/登录失败时就地重试，避免无限重启循环 | 冲突按本地 Restart/`LoginService` 架构重写：`DESKTOP_RESTART_ATTEMPTS=3`、桌面分支不先 `app_stop`、`desktop_stop_client()` 失败即 `RequestHumanTakeover`；保留本地 `delay_pending_tasks(reason=...)` |
| 27 | `f80c3a6d` | `29f5aba0` | feat | Config | 桌面模式配置项与界面说明 | 冲突：i18n 保留本地条目并追加 `desktop_game_path`（后被 `1d990fce` 的 desktop 组取代）；`config_device.py` 保留本地字段风格只加 `desktop_game_path` |
| 27 | `251cb1cd` | `d322accd` | fix | Scheduler | ensure desktop client logged in before gameplay tasks | 直接 cherry-pick，零冲突 |
| 27 | `1d990fce` | `c4117bf2` | feat | Script/Device | 桌面客户端独立配置组与多开账号隔离 | 冲突：i18n 保留本地 Chess 条目 + 新 `desktop` 组；`config_device.py` 采纳上游（移除旧的 `desktop_game_path`，`Union[EmulatorInfoType, str]`）；`handle.py` 采纳 `desktop_mode_enabled` 分支；新增 `tasks/Script/config_desktop.py`、`config/template.json` desktop 组 |
| 27 | `84366fc5` | `7113513c` | fix | Delegation | 避免勾玉确认误点与返回死循环（PR #1940） | 直接 cherry-pick，零冲突：任务名点击 interval 1→3、`I_UI_CANCEL` 优先、返回循环 6s 超时、进入/开始 15s/10s 超时 |
| 27 | `9afe3d32` | `1422d173` | fix | WantedQuests | 邀请时按已选好友判定（PR #1939） | 直接 cherry-pick，一行：`I_SELECTED` → `I_WQ_INVITE_SELECTED` |
| 27 | `43c84c88` | `f0fb1449` | fix | GeneralBattle | 关 buff 面板后点准备 | 直接 cherry-pick，一行：`check_and_open_buff` 末尾 `ui_click_until_disappear(I_PREPARE_HIGHLIGHT, interval=0.8)` |
| 27 | `55b7d957` | `6d4c6404` | fix | WeeklyTrifles | 上周存储弹窗遮挡全部存储标志（PR #1943） | 冲突：保留本地批次 26 的 `fold_timer = Timer(15)` 超时；并入 `ui_click_until_smt_disappear(random_click(...), I_WT_LAST_SAVE)` + `sleep(0.5)`，内层等待去掉 `sleep(0.5)` 并给各点击补 `interval=1` |
| 27 | —（回归测试） | `2db43f1d` | test | tests | 批次 27 回归测试 | 新增 `tests/test_upstream_batch27_desktop.py`（13 项：配置组/模板同步/`desktop_mode_enabled`/DesktopDevice 登录态/`_init_desktop`/roi_pad 端到端+边缘+payload）与 `tests/test_upstream_batch27_fixes.py`（13 项：Delegation/WantedQuests/GeneralBattle/摸鱼/Restart 桌面重试/Login 接线） |
| 26 | `7c850c3ca` | `de7e5616` | fix | GeneralRoom | 建房勾选框阈值入资产（0.8→0.7） | **手工移植（非 cherry-pick）**：本地 `ensure_private`/`ensure_public` 调用点**无内联** `threshold=`，资产却仍是 0.8（上游是把内联 0.7 挪进资产，语义为「小图标 0.8 太严，降阈值适配渲染偏差设备」）→ 把 8 条 `I_ENSURE_*` 规则统一为 **0.7**：`tasks/Component/GeneralRoom/assets.py` + `gr/image.json`（同 ROI 条目同步，保持单一真源）。回归测试 `tests/test_general_room_ensure_threshold.py`（4 项） |
| 26 | `3ee4e53db`（含 `3f45805b7` 的 `TOPPA_CLICK_FAILURE_LIMIT` 语义） | `de7e5616` | fix | RyouToppa | 寮突挑战进入失败判定：只有等待超时才算失败 | **手工移植（非 cherry-pick）**：新增 `TOPPA_CLICK_FAILURE_LIMIT = 4` / `TOPPA_POPUP_WAIT_TIMEOUT = 3.0` / `TOPPA_BATTLE_WAIT_TIMEOUT = 5.0`；`attack_area` 改为 popup/battle 双计数器 + 两个等待窗口——**点击结界卡片后浮窗未出现**或**点击挑战按钮后未进入战斗**（等待超时）才各记一次失败，合并到 4 即跳过该区域。旧实现是「每发出一次点击就 +1（上限 5）」，设备慢一帧即误判 `Click failure, check your click position` 并提前放弃区域。**本地架构差异保留**：上游用 `is_in_battle(False)`，本地继续用 `I_TOPPA_RECORD` 消失 + `sleep(1)` 二次确认作为战斗判据。回归测试 `tests/test_ryou_toppa_click_failure.py`（4 项） |
| 26 | `28e8f060b`（**仅超时保护部分**） | `de7e5616` | fix | WeeklyTrifles | 摸鱼行动入口折叠等待加超时兜底 | **部分采纳（手工移植）**：`_save_touch_fish` 的「防入口折叠」`while 1` 原无任何超时，公会入口改版或页面未加载完时空转 `sleep(1)` 直至全局卡死检测判失败 → 按上游加 `fold_timer = Timer(15).start()`，reached 时 `logger.warning('Touch fish guild entry timeout')` + `goto_page(page_main)` + `return`。**不采纳**其 `_, cu_tickts, _`：本地 `cu_tickts, _, _` 取 `DigitCounter` 第一项（current）才是正确读数（`module/ocr/sub_ocr.py:130` 契约 `(current, total-current, total)`），且该处已被 self 后续 `df3ff430` 自行修正。回归测试 `tests/test_weekly_trifles_fold_timeout.py`（2 项） |

---

## §3 已判定「已覆盖 / 不适用 / 跳过」——不要重复分析

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `a70757b1` | Exploration | Prevent premature back navigation during exit #1935 | 不适用 | 补丁依赖 `I_BACK_YOLLOW` 与上游 `BaseExploration.run` 旧退出循环；本地已改为页面导航（`quit_exp_main` + `page_exp_exit`），全仓无 `I_BACK_YOLLOW`，无落点 |
| `7e506bc3` | BaseTask | Skip task name mismatch validation | 已覆盖 | 本地 `tasks/base_task.py` 已无 `Task name mismatch` 校验（全文无该字符串），补丁无落点 |
| `911e996d` | workflow | Correct auto-merge schedule comment | 不适用 | 本地 `.github/workflows/auto-merge-pr.yaml` 不存在（仅 `auto-create-pr.yaml`） |
| `60117f17` | GeneralBattle/Orochi | 处理御魂溢出 | 部分已覆盖 | 目标 `tasks/Component/GeneralBattle/battle_wait.py` 本地不存在；本地 `general_battle.py:747` 的 `_handle_reward` 与 `GameUi/default_pages.py:366/389` 已对 `I_OVER_GHOST` 做 `appear_then_click`；`C_OVERFLOW_GHOST` 本地无调用点 |
| `7f0728bf` | GeneralBattle | 点击御魂溢出提示 | 已覆盖 | 同 `60117f17`；本地 `I_OVER_GHOST` 已在奖励页/全局页处理 |
| `c2023476` + `d8677dc0` | EvoZone | 关 buff 面板并开 50% 经验 + Revert | 净零 | 后者 revert 前者，净变更为零；同主题的 `43c84c88`（GeneralBattle 行）已单独落地 |
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
| `51582666d` | image | 新增掩码模板匹配与多尺度方法分发 | 不适用 | 客户端落点（改 `RuleImage` 里的 cv2 直调），本地匹配统一走图像服务 RPC，该处已是死代码；功能已由 self `8753481b` **服务端化落地（批次 22）** 覆盖 |
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
| `43c7f334` | ActivityShikigami | Broaden pass screen detection area | 不适用 | 本地该模块已自研重构（`tasks/ActivityShikigami/activities/{rich_man,fake_god,normal}.py` + `base_act.py` + `as/` 目录，通关资产为 `I_AS_TO_PASS`），上游仍是旧结构（`fire/`、`I_PASS_4`）→ 合并会覆盖本地当月素材；批次 20 `cherry-pick --skip` |
| `27241886` | GeneralBattle | 完成兜底时避免误点奖励弹窗 #1913 | 不适用 | 目标 `tasks/Component/GeneralBattle/battle_wait.py` 本地**不存在**（批次 0 框架已回退），且改的 `ActivityShikigami/script_task.py` 本地已自研重构 → 无法应用 |
| `b3d6fe98` | ActivityShikigami | Update（素材/ROI 刷新） | 不适用 | 改 `fire/`（本地已删）+ 已重构 `script_task.py`；其夹带的 `tasks/GlobalGame/assets.py` 是把 `I_UI_BACK_CIRCLE` 注释掉，而上游最新 master/dev tip 与本地均已启用该资产 → **不套用** |
| `efd39e18` | GlobalGame | 替换 `ui_ui_confirm.png`（5729→7565 字节） | 已覆盖 | master 该文件历史顺序中 `efd39e18` 之后紧接 `5d546f0b`（批次 20 已并入最终版） |
| `e930e2e1` + `8195cc60` | （多模块） | `sleep(0.8)`→`interval=3` 及其 Revert | 跳过（净零） | 两者互为正反，净变更为零 |
| `cf6fa6a5`（self） | image | 拦截零方差模板并修正多尺度浮点漂移 | 已覆盖 | 本地批次 12 `179f6dc0` 已手工移植 `module/image/runtime.py` 版本（`_template_is_degenerate` + 索引式 `min_scale + index*step`）；`module/atom/image.py` 同名改动属死代码（本地匹配全走 RPC） |
| `d6c42bee`（dev） | GeneralBattle | `log_battle_start` 装饰器 | 不适用 | 目标 `tasks/Component/GeneralBattle/battle.py` / `battle_wait.py` 本地**不存在**（批次 0 框架已整体回退，见本文 §3 注）；合并即死代码 |

> **批次 23 上游 merge commit（跳过，无独立内容）**：dev tip `92578cd0`；master tip `04f3b234`（合并 dev）。`5b556e92` 触达的 `tasks/Restart/login.py`/`GameUi/default_pages.py` 已回溯上游历史，**无后续解决提交**——本地分叉（登录迁 `Component/Login`）系 mine 系所致，故须手工移植。

> **批次 21 上游 merge commit（跳过，无独立内容）**：dev `a39e7375`(#1923)、`582d8f5b`(#1910)；master `fc68a2af`(#1916 from dev)、`3ffe7d30`(#1886)、`5a5d5dba`(#1898)。
> 同批 `d638c11f` 的掩码匹配子议题与 §3.1 `8753481b`/同源 `51582666` 同源，本地以「裁剪雾化左缘改普通模板匹配」规避，**掩码框架本身仍待决策**（见 §4）。

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

> 以上 8 条（除 `582eae75` 外）已 `ignore`，不再出现在待同步列表（`upstream_ignored.json` 共 16 条）；`8753481b` 于批次 22 改判「已合并」后一并 `ignore`。

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
| `028ca1f84` | Exploration | 探索大地图拆分「主线 / 玩法」tab 并继承大地图出口 | **已按最小修覆盖（批次 14）**；框架部分仍「需立项」 | 与 dev 的 `c56e2c9b` **同一特性**（两提交锚点图字节相同 `cb81854b`/`dc67cd05`，互不为祖先）。**急需的部分（选关依赖主线 tab）已由批次 14 最小修解决**：取主线一侧资产 + `open_expect_level` 前置 `ensure_mainline_tab()`。**剩余部分**（新增 `page_mainline`/`page_gameplay` 节点 + `inherit_transitions()` 复制出边、`page_exploration` 降级为通用态 + tab 桥接边、`base.py::activate_realm_raid` 白名单放开、`script_task.py` 分发表改指）属导航框架级改造，**与本地 per-module 页面体系耦合，维持需立项**，不要按「需修复」重复评估 |
| `aaede1dbe` | TrueOrochi | 改用玩法 tab 模块存在性判断本周次数 | 需立项（**优先级下调**，同 §3.5 `f7db71b2`） | 与 dev 的 `f7db71b2` 同一特性。以 `I_ST_MODULE`（玩法tab八岐大蛇模块，in-place 命中即本周有次数）替换 `O_TIMES` OCR 与 `current_success` 计数；`check_times` 简化为按 `success/failure_interval` 设下次运行；`config.py` 删除 `current_success` 与 `dynamic_hide`。**机制实测成立**（`I_ST_MODULE` 命中 0.9975），但 ① 两账号该任务均 `enable=false` 且日志无运行记录 → 落地即死代码；② **本地真蛇流程整体在新版 UI 上已失效**（`I_ST_CREATE_ROOM` 0.0000、`I_ST_FRAME` 0.0000、`I_ST_FIRE` 0.2245、`I_FIND_TS` 0.4407、`O_TIMES` ROI 空白），须连同战斗流程资产单独立项 |

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
| `c56e2c9b` | dev | Exploration | 大地图拆「主线/玩法」tab 导航 | ✅ **已合并（批次 14，最小修）** | 同特性 **self 源更早版本为 `028ca1f8`（2026-09-25）**，两提交锚点图**字节完全相同**（blob `cb81854b`/`dc67cd05`）且 `merge-base --is-ancestor` 为否 → 同一改动在两源各落一次（dev 版因当时无 per-module `page.py` 而显示为新建文件）。本批次只取「主线一侧」资产 + `open_expect_level` 前置守卫，**未引入** prio-60 tab 页 / `inherit_transitions` / 分发表改造 |
| `f7db71b2` | dev | TrueOrochi | 用玩法 tab 模块在场检测替代次数记账 | 需立项（**优先级下调**） | 依赖 `c56e2c9b` 的 `page_gameplay`。机制**实测成立**：`I_ST_MODULE` 在玩法 tab「真·八岐大蛇」模块行命中 **0.9975**（该行同时显示"本周剩余 2/2 次"），故它是对新版 UI 的**适配**而非精度回退。**但两点**：① TrueOrochi 在两账号均 `scheduler.enable=false`、`current_success=0`，且全部日志无真蛇运行记录 → 落地即死代码；② 实机发现真蛇相关页面**本地资产全数不命中**（组队→真·八岐大蛇页：`I_ST_CREATE_ROOM` **0.0000**、`I_ST_FRAME` **0.0000**、`I_ST_FIRE` 0.2245、`I_FIND_TS` 0.4407；`O_TIMES` 旧 ROI (461,388,40,26) 为**空白面板**）→ **本地真蛇流程整体已失效**，须连同战斗流程资产单独立项 |
| `431e3458` | self | GameUi | 回退：移除町中固定位置点击保底 | 需评估 | 本地 [navigator.py](../../tasks/GameUi/navigator.py) **已含该保底**，此提交是删除安全网，是否采纳取决于该保底线上是否致误 |
| `5a2d99bf` | self | FrogBoss | 处理商店弹窗并二次确认结束标志 | ✅ 已合并（批次 13，`9e6b3b6e`） | 真实兜底修复：`close_frog_mall` 自愈意外商店页 + `confirmed_finish_marker` 二次确认结束标志 + `C_BET_REWARD_CLOSE` 规避左侧商店气泡；手工移植见 §2 |
| `8753481b` | self | image | 新增掩码模板匹配 | ✅ 已合并（批次 22，手工移植） | 服务端化落地（本地匹配走 RPC）：`Masked template matching` 分派 + 掩码进缓存指纹 + 退化判据按参与区域 + nan/inf 清洗；回归测试 `tests/test_masked_template_match.py`。同源 runhey `51582666` 为客户端落点，判不适用（见 §3.1） |
| `5bc76c7e` | self | IbukiArena | 移植狭间幻境活动任务（新模块） | 需立项 | 本地无 `tasks/IbukiArena/` |
| `1f230af2` | self | FrogChallenge | 移植青蛙瓷器挑战赛（新模块，10 文件） | 需立项 | 本地无 `tasks/FrogChallenge/` |
| `c2390c2a` | self | IbukiArena | 修挑战判定可能提前命中 exit_matcher | 不适用 | 依赖 `5bc76c7e` 新模块，目标文件本地不存在 |

**新判定（已覆盖）**：

| 上游 hash | 源 | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|---|
| `a9cad51c` | self | FrogBoss | 引入负向胜率权重 | 已覆盖 | 本地 [frog_oas.py](../../tasks/FrogBoss/frog_oas.py) 已含 `rate - 0.5` + `signed_win_rate`（批次 4d `670f194a0` 落地） |
| `df3ff430` | self | WeeklyTrifles | 修正摸鱼行动御守数量读取与存储判断 | 已覆盖 | 本地 [script_task.py](../../tasks/WeeklyTrifles/script_task.py) 已含 `cu_tickts, _, _` + `not_save_flag` |

> dev 窗口内其余条目（`f4767278`/`c1dc5059`/`7738d5d5`/`194a3eda`/`606517be` 已合并；`5bc3f6e2`/`4e32d985`/`afdc0318`/`1c0a01f2`/`78083db2`/`52608081`/`7b522c94`/`af5fcf05`/`62f488b3`/`1589899a`/`08079eaf`/`51582666` 已判定）均见 §2/§3。

### §3.6 批次 17 扫描（`runhey/dev` 单源，2026-10-10）——已明确判定

> **背景**：应「与 `runhey/dev` 合并」之请求，用 `--source https://github.com/runhey/OnmyojiAutoScript.git#dev`
> 单源 `advise` 得 **102** 条候选；按 §1/§2/§3 全部 hash（688 个）过滤后**仅剩 5 条**未判定
> → 其中 **仅 1 条可落地（已合并）**，2 条已覆盖、2 条不适用。
> **教训**：`4e4e9079f`（2026-10-06）早于批次 10「dev 已判定完毕」的结论却从未入台账 ——
> 即早期的「dev 全判定」**存在漏项**，单源 `advise` + 台账 hash 过滤是发现漏项的有效手段。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `4e4e9079f` | DemonEncounter | 修正重进地图导航 | ✅ **已合并（批次 17，`9bb8a6ad`，手工移植）** | 见 §2 批次 17 行 |
| `990c45900` | Component | 新增 `run_task_or_default_general_battle` | 已覆盖 | 本地 [general_battle.py:1168](../../tasks/Component/GeneralBattle/general_battle.py#L1168) 已有同名函数且为**更完善**实现（读 `global_game.battle.on_takeover` 决定快速退出 config、优先调用任务自身 `run_general_battle`），并已被 [default_pages.py:329](../../tasks/GameUi/default_pages.py#L329) 调用 |
| `55f51238f` | Component | 为该函数加 AttributeError 兜底 | 已覆盖 | 本地实现全程用 `getattr(..., 默认值)` 取值，天然不抛 `AttributeError` |
| `f871f3795` | workflow | 升级 GitHub Agentic Workflow 运行时 | 不适用 | 目标文件 `.github/workflows/*.lock.yml` / `.github/aw/*` 本地**不存在**（同 §3 CI/workflow 类） |
| `a27a91fe9` | workflow | 恢复受支持 AI 模型定价 | 不适用 | 同上 |

> 上述 4 条判定项已 `ignore`（`upstream_ignored.json` 由 4 → 8 条）。

### §3.7 批次 25 扫描（`runhey/dev`，2026-10-11~14）——已明确判定

> **背景**：应「合并上游新提交与 Merge PR」之请求。`fetch` 三源后，`runhey-dev/dev` tip = `4c688865`（2026-10-14）、`runhey-master/master` tip = `04f3b234`（落后 dev）、`xylolit-mu-self/self` tip = `00c083e8`（2026-10-03，**无新增**）。按 §1/§2/§3 全部 hash 过滤后，本轮真实新增仅为 dev 2026-10-11~14 的提交。
> **结果**：1 条可落地（PR #1934，已合并）、1 组需立项（PR #1905，已评估）、1 条不适用、1 条已覆盖、1 组净零。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `bedff718`+`985ac267`+`5770f91e` | Duel | 斗技开战前等待增加超时与点击上限（PR #1934） | ✅ **已合并（批次 25，`6ec09b31`，手工移植）** | 见 §2 批次 25 行 |
| `af6d1bcb`+`c8f93d1b`+`2bc21f59`+`69a0fc4f` | Exploration | 按 UP 类型自适应滑屏找怪 + 抽取滑屏/重置辅助方法（PR #1905，合并 `4c688865`） | **需立项（已评估）** | 上游改 `tasks/Exploration/solo.py`（+120）与 `base.py`（+13）——依赖**本地已废弃的 `Scene` 枚举 + `solo.py`（`run_solo`/`run_leader`）运行架构**；本地 `tasks/Exploration/` **无 `solo.py`、无 `Scene`**，采用 **per-page** 架构（`page.py` + `script_task.py` 的 `exp_page_handle_dict`）；`base.py` 改动锚点函数（`is_swipe_unchanged`/`quit_explore`）本地亦不存在 → **无法干净完整合并**。本地对应能力已由自研 `search_up_fight`（`match_all`）+ `open_expect_level`（min/max 自适应滑屏，上限 `swipeCount>=25`）+ `arrive_end`（`click_record.count>=6`）覆盖。**保留为需立项**（若日后上游大改该链，以本地 `tasks/Exploration/base.py::open_expect_level`/`search_up_fight` 为落点） |
| `2f5c306e` | GeneralInvite | `invite_friends` 邀请前 `sleep(3)` | 不适用 | 本地 `invite_friends` 已重构为**批量选人一次确认**（`_select_recent_mode_friends`/`_select_auto_mode_friends` → `_confirm_invite_and_validate`），无上游「逐个邀请」路径，无对应改动点 |
| `aaac78b3` | Exploration | `open_expect_level` 选关滑动反向（UP→DOWN） | 已覆盖 | 本地 `open_expect_level` 用 min/max **自适应**条件选 `S_SWIPE_LEVEL_UP`/`S_SWIPE_LEVEL_DOWN`（上限 25 次），已能选到 28 章；且两枚 `S_SWIPE_LEVEL_*` 资产 ROI 与上游**逐字相同**，无需反向 |
| `372ef8f3`+`54803c50`+`614b6b84`+`e56482ca` | Exploration | 新增 / 删除 / 回退 / 回退 `S_SWIPE_LEVEL_DOWN_PRO` | 净零 | 4 条互为增删回退（`add` → `delete` → `Revert delete` → `Revert add`），净变更为零；本地亦无 `S_SWIPE_LEVEL_DOWN_PRO` |

> 批次 25 已 `ignore` 9 条：`bedff718`/`985ac267`/`5770f91e`（已合并）、`2f5c306e`（不适用）、`aaac78b3`（已覆盖）、`372ef8f3`+`54803c50`+`614b6b84`+`e56482ca`（净零对）；PR #1905 的 4 条**保留为需立项，不 ignore**。

### §3.8 批次 26 扫描（`xylolit-mu/self` 积压第二轮 triage，2026-10-15）——已明确判定

> **背景**：应「合并上游新提交与 Merge PR」之请求。`fetch` 三源后与批次 25 台账核对：
> `runhey/master` tip = `04f3b234`、`runhey/dev` tip = `4c688865`、`xylolit-mu/self` tip = `00c083e8`
> ——**与批次 25 记录逐字相同**（`git ls-remote` 直连核对），即 **runhey 两源零新增**；
> 台账全部反引号 hash（375 个）过滤后剩余 **104** 条未逐条记录的提交，**全部来自 `xylolit-mu/self`**
> （2026-08-15..2026-10-01），属 §3.4「剩余余量 169 条」中尚未单列的部分 → 本批 = **self 积压 triage 第二轮**。
>
> **方法（可复用）**：① 机械「本地已覆盖度」检测——把每个提交的 `+` 行（去噪）与**本地当前文件**
> 逐行归一化比对，得 covered ratio 与**缺失行原文**（脚本 `coverage.py`，结果 `coverage.json`）；
> ratio=1.0 的 10 条直接判「已覆盖」，ratio 低但**缺失行很少**的重点看，其余按簇归并。
> ② 对每条候选**读真实 diff + 本地文件**做语义核实（**不得只信 `advise`**，见 §4.6）。
> ③ **关键结构发现**：本地 `czr` 是 runhey/OAS 谱系（`tasks/ActivityShikigami/config.py` 为 165 行
> `ActivityShikigami(ConfigBase)`：scheduler/general_climb/rich_man/switch_soul_config；
> 无 `module/config/multi_select.py`；无 `tasks/LBS/`；无 `tasks/ActivityShikigami/activities/exploration.py`），
> 而 `xylolit-mu/self` 是 **OASX 式重写** → 大量「配置/玩法框架」类候选**结构性不适用**，
> 不能用「逐条 cherry-pick」或「按标题判断」处理。
>
> **本批结果**：可落地 **3**（含 1 条部分采纳）/ 已覆盖 **17** / 不适用 **10** / 需立项 **73**。可落地 3 条见 §2 批次 26 行；判定项已 `ignore` 28 条。

**已覆盖（17 条，逐条语义核实）**：

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `eab0f2182` | Chess | Chess 恢复棋局匹配超时自定义 | 已覆盖 | add 行 100% 命中本地 |
| `84374647a` | config | ActivityShikigami 调整 UI | 已覆盖 | add 行 100% 命中本地 |
| `37c393b57` | KekkaiUtilize | KekkaiUtilize 优化蹭卡逻辑 | 已覆盖 | add 行 100% 命中本地 |
| `bdad06806` | Duel | Duel 添加小白弹窗识别 | 已覆盖 | add 行 100% 命中本地 |
| `a3a2c8938` | assets | Merge PR #286 KekkaiUtilize | 已覆盖 | add 行 100% 命中本地 |
| `ef0f8d110` | AutoCheckinBigGod | AutoCheckinBigGod 新版领取界面 | 已覆盖 | add 行 100% 命中本地 |
| `05560e29f` | assets | Costume 接入灵狐寄愿主题 | 已覆盖 | add 行 100% 命中本地 |
| `8ec6ae477` | Component | 生成资源注释/空白清理 | 已覆盖 | add 行 100% 命中本地 |
| `1ad34a789` | FrogBoss | FrogBoss 无操作五秒保底下一局 | 已覆盖 | 本地 `script_task.py:112` 已有 `_try_next_competition_fallback` + `Timer(5)` |
| `1eb9fe3f6` | FrogBoss | FrogBoss 下一局后休息状态 | 已覆盖 | add 行 100% 命中本地 |
| `3f15a9815` | BondlingFairyland | 契灵建房过渡识别已进房 | 已覆盖 | 仅差 `:param room_mark:` 一行注释，`room_mark` 兜底代码本地已在（`general_room.py:70`） |
| `225c7a137` | GuildActivityMonitor | 寮活动监控通知漏检 + OCR 模式 | 已覆盖 | 本地 `init_keyword` 等价；上游 `last_keyword = notification_text` 在 `trigger_activity_task`（`raise TaskEnd`）之后**不可达** |
| `9ea4a0317` | KekkaiUtilize | 结界蹭卡选卡逻辑 | 已覆盖 | 本地 `taiko_ok`/`fish_ok` + `min_taiko`/`min_fish` 阈值实现**更完善**（上游为无阈值简版） |
| `d5837031c` | DemonEncounter | 逢魔灯笼点击区收缩 | 已覆盖 | ROI 改动本地已在；仅缺 `demon/click.json` 的 `profile:"Default"`——本地点击规则无 `profile` 字段 |
| `5f408cd4a` | FrogBoss | 对弈竞猜下注弹窗优先 + 限次 | 已覆盖 | 本地已含 `confirm_bet`/`select_gold_30` 与收紧后的 `I_GOLD_30_CHECK` roi；差异仅 `profile="High"`，且本地用 `C_BET_REWARD_CLOSE`（批次 13 专门规避左侧商店气泡） |
| `9d39f0c04` | GameUi | 庭院导航增加进町中保底点击 | 已覆盖 | 本地 `navigator.py:544` 已有 `TOWN_FALLBACK_{action}`（f-string 换行形式不同） |
| `622720ab9` | assets | 花礼幕台幕间汉化 | 已覆盖 | 同一 `costume_shikigami_11` 本地译名「花札幕台」≠ 上游「花礼幕台」，保留本地译名 |

**部分采纳（1 条）**：

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `28e8f060b` | assets | 摸鱼行动入口增加超时保护 | 部分采纳 | **部分采纳**：只取折叠入口 `Timer(15)` 超时兜底（本批已落地）；其 `_, cu_tickts, _` 不采纳——本地 `cu_tickts, _, _` 取 `DigitCounter` 第一项(current)正确，且该处已被 self 后续 `df3ff430` 修正 |

**不适用（10 条，多为 OASX 框架/新模块结构性差异）**：

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `8c95d9497` | module | 配置多选单项/列表兼容 | 不适用 | 本地无 `module/config/multi_select.py`，`module/config/config_model.py` 亦无 `set_argument`/`multi_enum`（配置为 OAS 结构） |
| `74f613003` | assets | 简化式神活动/百鬼棋局配置说明 | 不适用 | 本地 `tasks/ActivityShikigami/config.py` 为 165 行 OAS 结构，无 `GeneralConfig`/`task_sequence` |
| `27176b66e` | assets | 任务启用项改为固定顺序多选 | 不适用 | 同上：本地无 `task_sequence` 多选字段与 `ACTIVITY_NAME_ALIASES` |
| `ddfebb121` | ActivityShikigami | 兼容旧版活动输入 + 复用上游 mall/契灵修 | 不适用 | 同上：本地无 `parse_task_sequence`；其 mall/契灵部分本地已有等价或更优实现 |
| `1ccddb5f5` | ActivityShikigami | 爬塔两种难度共用门票预检 | 不适用 | 本地 `tasks/ActivityShikigami/activities/normal.py` 无 `_run_climb_type`/`O_REMAIN_PASS`/`page_climb_ap`/`_update_climb_consumable_count` |
| `ad15a0233` | assets | 新增 LBS 鬼王限时活动任务 | 不适用 | 本地无 `tasks/LBS/`（新模块 20 文件） |
| `188dee7c4` | assets | LBS 开车模式 + 运行模式三选一 | 不适用 | 本地无 `tasks/LBS/` |
| `a1fb24a64` | Component | LBS 开车模式等进房渲染完成 | 不适用 | 目标 `tasks/LBS/script_task.py` 本地不存在 |
| `f01a83f0d` | module | LBS 挑战次数判断 + 调度优先级 | 不适用 | 目标 `tasks/LBS/script_task.py` 本地不存在 |
| `7e8e0f566` | MartialTournament | 清除冗余文件（27 文件） | 不适用 | 删除的是 OASX 侧冗余文件路径，本地无对应文件 |

**需立项（73 条，按文件簇归并——★未逐条语义核实，只做了覆盖度+簇归属）**：

| 文件簇 | 条数 | 全部 hash | 代表条目（hash 标题） |
|---|---|---|---|
| `ActivityShikigami` | 18 | `e319d27e1`、`06bcd50a8`、`9dfc25eef`、`ce953ff0e`、`62121983c`、`7b035a106`、`15198f451`、`72109baef`、`ed684414f`、`3f70c2801`、`01e7b622f`、`8ddf92b92`、`e45f95d6c`、`e64e2b836`、`e1fd388d0`、`ef48a3fdf`、`1f9e14d4b`、`e49355607` | `e319d27e1` feat(tasks):修正荒川代号，修复大富翁已知、`06bcd50a8` fix(ActivityShikigami):保守改、`9dfc25eef` fix(ActivityShikigami):优化五 |
| `assets` | 14 | `d90ccd257`、`90bca1ac8`、`aadc868fc`、`0b7cb5254`、`5ce1abc97`、`4336f5cf5`、`b805eaa9f`、`faddfbe82`、`f0e08d0c2`、`a123a02b9`、`29b2d8cb7`、`6114d5b81`、`d9c877a4e`、`69ded977d` | `d90ccd257` fix(MartialArts):添加武道大会继续挑、`90bca1ac8` fix(RichMan):合并大富翁战斗预设配置，回、`aadc868fc` fix(ActivityShikigami):新增五 |
| `Chess` | 8 | `0d8ec9200`、`fe7aff531`、`ee18af9ff`、`a65ef964f`、`37c737f8b`、`49a0b1c42`、`1a9a1f61b`、`1aacf5a57` | `0d8ec9200` fix(Chess): 优化操作确认与荒川金鱼处理、`fe7aff531` fix(Chess):新增匹配超时后进入对局处理。、`ee18af9ff` fix(Chess):优化按住并拖动路径，调整荒川阵 |
| `Component` | 5 | `b03775af6`、`29988f3e7`、`6c3d29270`、`1c646ce54`、`8f0ebc1cd` | `b03775af6` fix(GeneralBattle): 扩展结算随机、`29988f3e7` 修复(探索)：优先关闭聊天侧栏并调整安全点击区域、`6c3d29270` 调整(通用战斗)：更新探索与活动Scatter安全区 |
| `module` | 5 | `2503580f8`、`c1052a67d`、`731836c7d`、`a27768222`、`8328e623c` | `2503580f8` fix(Device, Chess): 优化MuMu、`c1052a67d` fix:回退幽默拟人化点击，同步调整Chess任务点、`731836c7d` fix: scope settlement scat |
| `AbyssShadows` | 3 | `0237278eb`、`b4d9431b6`、`014ffa84b` | `0237278eb` fix(AbyssShadow):调整QuickLo、`b4d9431b6` 调整(狭间)：恢复式神录装魂与对局上阵流程、`014ffa84b` 优化(狭间)：跳过重复御魂装配并识别已击破目标 |
| `FrogBoss` | 3 | `414d42dfd`、`1f1fdbef4`、`16d1205da` | `414d42dfd` 调整(对弈竞猜):调整竞猜对应素材。、`1f1fdbef4` 调整(对弈竞猜):调整竞猜对应素材。、`16d1205da` 修复(对弈竞猜)：更新失败结果识别素材 |
| `config` | 3 | `8716a84d1`、`36cdcc74f`、`0c3b971a0` | `8716a84d1` feat(RichMan):修改骰子耗尽检测逻辑，修、`36cdcc74f` 优化(斗技)：匹配超时竞态保护与周目标调度、`0c3b971a0` 优化(重启)：支持配置异常重启容忍次数并优先执行恢复 |
| `BondlingFairyland` | 2 | `0e0bac665`、`641998988` | `0e0bac665` fix(GameUi):调整页面寻路逻辑，调整mal、`641998988` feat(GeneralInvite): 等待好友列 |
| `DemonEncounter` | 2 | `a04d51da7`、`f3f62f433` | `a04d51da7` fix(DemonEncounter): 优化bos、`f3f62f433` 修复(逢魔之时)：确认弹窗关闭与首领识别并限制三轮召 |
| `dev_tools` | 2 | `a93521f70`、`f130ab3f2` | `a93521f70` fix:新增区域选定方法，新增点击策略、`f130ab3f2` 调整(图像点击)：统一Image规则为High并更新 |
| `Delegation` | 1 | `d814b589f` | `d814b589f` 修复(委派)：补充领奖对话验证并更新出战识别资源 |
| `Duel` | 1 | `7114d0cf3` | `7114d0cf3` fix(Duel):处理新增页面 |
| `GameUi` | 1 | `30d058244` | `30d058244` 调整(通用页面)：统一奖励识别并注册误触页面与结算策 |
| `KekkaiUtilize` | 1 | `973a5f237` | `973a5f237` fix:调整寄养逻辑. |
| `Restart` | 1 | `93cdaf2b8` | `93cdaf2b8` 修复(登录)：调整进入游戏文字识别区域与关键词 |
| `RichMan` | 1 | `dcb7c6eb8` | `dcb7c6eb8` feat(RichMan):修复重复点击异常。 |
| `Secret` | 1 | `5150e29eb` | `5150e29eb` fix(secret):调整秘闻点击逻辑、范围。 |
| `WeeklyPurchase` | 1 | `2510590ef` | `2510590ef` fix(WeeklyPurchase):新增鼬乐币购 |

> ⚠ `0237278eb`/`b4d9431b6`/`014ffa84b`（AbyssShadows 御魂装配时机）**保留为需立项、不 ignore**：上游终态改为「狭间地图 → 式神录 `run_switch_soul` 装配」，并把 quick loadout 降级为**备用方法**（自述「当前狭间流程不接入」）；本地是 quick-loadout 面板「装配**并上阵**」耦合机制（`I_OPEN_QUICK_LOADOUT` + `I_ABYSS_QUICK_LOADOUT_FIGHT` + `dismiss`），`cur_soul_preset` 相等跳过已覆盖重复装配，而按敌人类型去重会**连上阵一起跳过** → 不能整包移植。
>
> **其余簇的处置建议**：与 §3.2/§3.4 一致——这是**框架级重写**（OASX 配置多选/活动战斗/大富翁 GUI/
> Chess 状态机/atom 点击策略/图像 `profile="High"` 统一/低配与休息模式/模型预加载），
> 须**按簇立项**（先读该簇全部 diff → 再判可否局部移植），不适合小批次同步。
> 其中体量最大的 `f130ab3f2`（282 文件，`profile="High"` 统一 + 默认值）与本地「点击/图像规则不带
> `profile` 字段」的框架选择**直接冲突**，单列最高优先级议题。

### §3.9 批次 30 扫描（runhey master/dev + kongdr418/mine + xylolit-mu/self，2026-10-21）

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `77bd7fd7` | Restart | 邮件领取确认 `Timer(3)`→`Timer(6)`（PR #1956） | 不适用 | 本地 `tasks/Restart/login.py` 是 19 行兼容垫片（`class LoginHandler(LoginService)`），真实现在 `tasks/Component/Login/service.py`；该类无 harvest-mail 流程（全仓无 `Exec harvest mail`，`I_HARVEST_MAIL_*` 只出现在 DailyTrifles） |
| `fe98ffef` | ActivityShikigami | UpdateClimbBossResources（PR #1959：换 2 张 boss 模板 + ROI） | 不适用（另立项） | 本地已重写为页面图框架（`page.py` 用 `page_act_boss = Page(I_CHECK_BATTLE_BOSS)` 作锚点）；看图证实两边是**不同活动 UI**：本地模板 `as_check_battle_boss.png` 129x46 是横排「炼石成金」、`as_to_battle_boss.png` 79x87 是竖排同字（roi `(151,18,129,46)`/`(126,421,79,87)`）；上游新版 18x99 是竖排「磐长神木」、96x26 是橙色横条（roi `(402,142,20,90)`/`(1071,302,80,30)`）→ 换图会让本地 boss 页锚点错乱；上游 `script_task.py` 那行改的是本地不存在的 `battle_wait` 框架 `options['completion'].check_imgs`。**本地爬塔模块相对当前活动已陈旧 → §4 立项适配** |
| `04787fc4` | GeneralBattle | 扩大聊天框关闭区（`C_END_MESSAGE_RIGHT_TOP` + `gw/click.json`） | 不适用 | 本地战斗已重写，无 `C_END_MESSAGE_RIGHT_TOP`，也无 `tasks/Component/GeneralBattle/gw/click.json` |
| `65a6b737` | GeneralBattle | battle_before 超时后重试准备点击 | 不适用 | 依赖 `battle_wait.py`/上游 `general_battle.py` 结构；本地是自有状态机（`PREPARE_CLICK_DELAY = 3.0`、`_handle_prepare`/`_handle_in_battle`、`prepare_click_timer`） |
| `1bec4e5d` | GeneralBattle | 战斗失败如实上报为失败 | 不适用 | 同上（本地无 `battle_wait.py`），失败判定在自有状态机内 |
| `4e894c69` | GeneralBattle | 防止随机战斗动作重复执行 | 不适用 | 同上 |
| `0f6e60a5` | RyouToppa | 点击后加 0~0.3s 随机延时（#1748） | 已覆盖 | `tasks/RyouToppa/script_task.py:369` 已有 `time.sleep(random.uniform(0, 0.3))` |
| `ac4016f0` | WeeklyTrifles | 调整执行顺序（`save_touch_fish` 移到三个 share_* 之后） | 已覆盖 | 本地 `run()` 已是 share_* 在前、`_save_touch_fish` 在后 |
| `ed8eda48` | CostumeShikigami | 契光水境式神录识别区域 | 已覆盖 | 本地 `tasks/Component/CostumeShikigami/assets.py:309` 已是 `I_CHECK_RECORDS_5 roi_front=(313,75,44,43) roi_back=(308,70,54,53)` |
| `929c6a11` | SwitchOnmyoji | 两个内层循环加有界退出 | 已覆盖 | 本地已有 `SWITCH_TAB_TIMEOUT = 20`/`SWITCH_BATTLE_TIMEOUT = 20` + `ScriptError`，`tests/test_switch_onmyoji.py` 已存在 |
| `988145c0` | GameUi | 刷新 `page_main_goto_summon.png` | 已覆盖 | 本地 blob `6199521c` == 上游新版 |
| `9b3c9b67` | FrogBoss | 移植 OAS 胜率策略与赛果记录 | 已覆盖 | 本地 `tasks/FrogBoss/frog_oas.py`、`oas_sources.py`、`tests/test_frog_oas.py` 均已在 |
| `fd46e065` | HeroTest | 补技能选择超时回退测试 | 已覆盖 | 本地 `tests/test_hero_test_skill_fallback.py` blob `6a7a1037` == 上游新版（该文件 7 项既有失败与本批无关） |
| `17474206c` | Login | 进入游戏后 `wait_time` 5→10 | 不采纳（上游已回退） | 上游自己用 `03429729f`（2026-09-30，同一作者）把 `wait_time` 由 10 回退为 5，理由 `I_LOGIN_SPECIFIC_SERVE` 长期 0 命中；按「以最新提交为主」本地 `tasks/Component/Login/service.py:190` 保持 `wait_time=5` |
| `03429729f` | GameUi | `I_CHECK_MAIN` 阈值 0.95→0.9 | 暂不采纳（§4 观察） | 本地 `tasks/GameUi/assets.py:129` 与 `page/image_main.json` 均为 0.95，但 roi_back 已本地定制为 `(49,98,1033,74)`；`log/2026-10-19*`/`2026-10-20_script.txt` 无庭院识别失败记录 → 不动全局页识别阈值 |
| `65c5b1273` | Deploy | 默认仓库指向作者 mine 分支 | 不适用 | fork 专属 |
| `b9f33b8b1` | doc | 变更日志 | 不适用 | 已被 `a192e085` 删除，无落点 |
| `885ea02cb` | Restart | `O_LOGIN_ENTER_GAME` OCR ROI `543,530,194,125`→`543,554,196,84` | 不适用 | 本地已是 `(460,460,360,180)`（更大范围，已按本机环境适配） |
| `9ec93a440`/`fcd496def`/`fb06df056`/`27dc33a45`/`8dcf5b59b` | FrogBoss | 下注弹窗死循环、零权重随机、模板阈值等 | 不适用/已重写 | 本地 `tasks/FrogBoss/script_task.py:216 do_bet` 为本地实现（`I_GOLD_30_CHECK` + `submit_attempts < 3` 上限），与上游 `flag_glod_30` 乒乓结构不同；`frog_oas.py` 亦已本地化 |
| `89e3ad09a` | Server | 截图改 adb 直抓 | 本批不采纳（保留待议） | 与 `9f07623b5` 配套但会改写现有截图链路（`module/server/tool.py` 的 adb 取图），本批只叠加新接口、不动既有链路 |
| `631968c6` | GameUi | OASX 页面框架级重写（951 文件：`page_checks/` 模板文件化、`task_pages.py` +884、删 `ActivityShikigami/page.py`） | 不适用 | self 系框架重写，本地页面识别体系不同，须按簇立项 |
| `90a03025` | Chess | 棋局红叉浮窗 + 鼬乐币识别范围 | 不适用 | 本地 Chess 已重写 |
| `a8af5223` | Chess | 百鬼投掷 + 黄金复制术 + 平安京阵容评分（36 文件） | 不适用 | 同上 |
| `dd72b786` | GameUi | 「高阶山岚」位置替换为「六道千门」 | 不适用 | 素材/位置类，随 self 框架条目不适用 |

### §3.10 批次 31 扫描（runhey master/dev + xylolit-mu/self + kongdr418/mine，2026-10-23）

> 本轮 `advise` 实跑 369 条（四源跨源去重），按台账 hash 集过滤后剩 **102 条**未记录候选。
> 落地 4 组（§2），其余按下列分类判定；`6029ad08` 一带的**新版棋局链**属框架级重写，保留为需立项、不 `ignore`。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `6029ad08` | Chess | 移植新版百鬼棋局（含帧规则与识别能力，412 文件） | 需立项 | 引入上游 frame/re-scatter 识别框架并整体重写 `tasks/Chess`；本地 Chess 为自研状态机（`runtime/economy.py`、`strategy/shikigami_catalog.py`），合入即覆盖本地实现，须按簇单独立项 |
| `4c5d633a` | Chess | 同步百鬼投掷、黄金复制术与平安京阵容（39 文件） | 需立项 | 与 `6029ad08` 同一新版链，依赖其帧规则与阵容模型 |
| `74425d03` | Chess | 同步上游百鬼主动投掷与特殊回合识别修复（17 文件） | 需立项 | 同链；目标文件为上游新版 `tasks/Chess` 结构 |
| `d856707a` | Chess | 修复百鬼主动投掷与特殊回合识别，统一阵容配置及符咒复核（17 文件） | 需立项 | self 侧同链等价改动 |
| `d304586b` | Chess | 修改棋局识别标志（41 文件） | 需立项 | 同链，整体换识别资产 |
| `0501cb19` | Chess | 手牌紧急清理无操作时直接出售一张阵容卡腾位 | 需立项 | 依赖上游新版手牌/阵容状态机 |
| `521e1a8d` | Chess | 百鬼无所需御魂时等待全员解锁后随机投掷 | 需立项 | 同上 |
| `acbdbf1c` | Chess | 加宽鼬乐币 OCR 区域（`O_COIN` 406,660,87,25 → 400,660,93,25），修「600/600 读成 00/600 恒不停止」 | 不适用 | 上游 `O_COIN` 布局与本地不同（本地 `141,659,87,25`），且本地 `_read_coin` 已走 `DigitCounter` 三元组 + 文本双路解析（`_parse_coin_text` 还会恢复斜杠丢失），不存在该缺陷 |
| `73cf2c63` | base_task | 补 `clock_time` 导入修 `set_next_run_next_monday` NameError | 不适用 | 本地全仓无 `set_next_run_next_monday`（grep 零命中），无调用点 |
| `6141a8ca` | SwitchAccount | 资产 ROI 由浮点改为整数（`I_SA_LOGIN_FORM_ANDROID`/`I_SA_CHECK_SELECT_SVR_2`） | 已覆盖 | 本地 `tasks/Component/SwitchAccount/assets.py:84/88` 与 `res/image.json` 已是整数 `671,353` / `209,131` |
| `d34761fe` | SwitchAccount | 同上并顺带改 FindJade 一处 | 已覆盖 | 本地已为整数 ROI 与 `O_SA_CHECK_SELECT_SVR` 命名 |
| `175e1dc5` | SwitchAccount | 修 `O_SA_CHECK_SELCET_SVR` 拼写导致的 AttributeError | 已覆盖 | 本地 `assets.py:52` 即 `O_SA_CHECK_SELECT_SVR`（拼写正确），`login_account.py:85` 已用该名 |
| `cd284a89` | 御灵 | 御灵更新 | 延后（本轮未选） | 用户本轮明确未选该项；本地御灵/灵御体系与上游差异未核，留待后续批次单独评估 |
| 其余 self 7–8 月积压 / mine 9–10 月积压 | — | — | 维持既有判定 | 已由 §3.2 / §3.4 / §3.9 判定（已覆盖 / 不适用 / 按簇需立项），本轮不重复分析 |

> 本批**不涉及上游冲突修复提交**：4 组落地项均为「上游单侧小改 + 本地零冲突或手工局部移植」，`git cherry-pick` 两条 Dokan 提交零冲突，无需要回溯上游历史查找冲突解决方案的场景。

### §3.11 批次 32 扫描（runhey master/dev + kongdr418/mine + xylolit-mu/self，2026-10-29）

> 四源 `fetch` 后按 §2/§3 全部 hash 过滤，逐条 `show` 真实 diff + 本地 grep 核实，落地 13 条（§2）。下列 16 条为判退项；其中 3 条 WantedQuests 后续修复构成一条**依赖链**（`c695e50d` → `c3a88af9` → `9a6eb783`），判**延后**而非判退（不 `ignore`）。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `6360d6a9` | Dokan | 修复道馆首次攻击后的任务间隔 | 已覆盖 | `set_next_run(task="Dokan", server=False, target=now + failure_interval)` 本地 `script_task.py:633/639` 已带 `server=False`；`git merge-base --is-ancestor` 证实它是已合入 `3f085151` 的祖先，语义随本批一并落入 |
| `1e18c251` | Dokan | 道馆开启尝试移出查找循环 | 已覆盖 | 上游把 `creat_dokan()` 从 `find_dokan` 循环挪到主循环前「只试一次」；本地 `run_on_dokan_map` 已有 `self.found_dokan_cnt > 0 → raise DokanNotStartedError` 守卫（`find_dokan` 一失败即结束任务）→ 每次运行实际只开馆一次，语义等价。本地为页面状态机，无上游的 `find_dokan` while 循环结构 |
| `cacc2af3` | GeneralBattle | 御魂溢出处理升级 | 已覆盖 | `battle_wait.py` 本地不存在（批次 8 已判不引入该框架）；`general_battle.py` 侧语义本地已由 `_handle_reward` 每轮 `appear_then_click(self.I_OVER_GHOST, interval=0.8)` 实现（`general_battle.py:747`） |
| `85632077` | AreaBoss + device | fox battle 结算（#1967） | 不适用 | 补丁核心依赖 `Battle` / `battle_wait_strategy` / `battle_wait_options`（本地无该框架，`battle_wait.py` 不存在）；`device.py` 侧只是 `IS_WINDOWS` 条件导入 `DesktopDevice`（Linux 兼容），本地 Windows 无条件导入即正确 |
| `1f5149f3` | Server/screen | 截图前自动重连 adb | 不适用 | 上游落点 `module/server/screen_capture_worker.py` 本地已重写为 `Device.screenshot()`（adbutils）实现，没有上游的 `_configured_serial`/`_auto_serial` 子进程 `adb` 路径；掉线重连由设备层 `Device` 负责 |
| `c3a88af9` | WantedQuests | 详情页改用「前往」按钮判断 | **延后**（依赖链首项） | 依赖 `c695e50d` 引入的 `close_unsupported_wq()`/`is_mystery_wq()`；本地 `open_wq_info` 仍只看 `I_TRACE_TRUE`（`script_task.py:98`） |
| `c695e50d` | WantedQuests | 识别神秘妖怪悬赏后关闭面板并跳过 | **延后**（依赖链中项） | `assets.py` 整表重排（196 行）+ 新增 `wq_exit.png`，与本地「`image.json` 生成 assets」流程相冲，须单独一轮核对资产；`script_task.py` +73 行是后两条的前置 |
| `9a6eb783` | WantedQuests | 修复取消追踪卡死与数量识别 | **延后**（依赖链末项） | 依赖同链的 `appear_any_goto()`/`cancel_trace()`：本地 `script_task.py:236/243/249/260` 仍是 `ui_click(self.I_TRACE_TRUE, self.I_TRACE_FALSE)` 死循环（神秘妖怪详情页无追踪图标 → 空转到 `GameStuckError`），且 `execute_mission:233` 只看 `I_GOTO_1`；数量 OCR 失败时的 `detect_and_ocr` 按 score 兜底也未落。**价值明确，建议下一批优先立项** |
| `31484b10` | Chess + Server | 阵容编辑器与 JSON 配置（斗技补 ban 检测） | 需立项 | 新增 `module/server/chesslineup_router.py` + 整套前端（`web/chesslineup/`、卡牌 webp）、`module/cooperation.py`、`config_model` 新段、`.gitignore` 33 行；属大特性，须按簇立项 |
| `73d4ae84` | Chess | 棋局阵容编辑工具与 JSON 配置 | 需立项 | 与 `31484b10` 同簇（self/mine 两侧同一功能的不同实现） |
| `14cbd413` | GeneralInvite + Cooperation | 同步上游邀请组件（适配新界面 + 等好友列表加载） | 需立项 | 新增 `module/cooperation.py`(243 行) 与 `config_invite.py` 配置段、`gi/image.json` 重排 + 多张换图/新图；本地邀请已是批量选人重构，须按簇评估后再合并 |
| `76490d67` | GeneralBuff + GuildBanquet | 兼容第二种寮宴会旗帜并修复加成开关资产重名 | 已被取代 | 与批次 31 落地的 `51dbf564` 同源等价（同为 GeneralBuff 三类型拆分 + `I_BANQUET_FLAG_2`），已在批次 31 覆盖 |
| `57c3f701` | GlobalGame | 放宽协作图标识别区域 | 已被取代 | mine 侧同义改动（`assets.py` 58 行 ROI 重排）；本批以 runhey 新 UI 版 `e68c2d26` 的 6 条新 ROI 为准，两套并存会互相覆盖 |
| `91010725` | GlobalGame | 放宽忽略按钮识别区域 | 已被取代 | 同上，1 行 ROI 改动已含在 `e68c2d26` 的 6 条新 ROI 内 |
| `7b8155d9` | WantedQuests | 重截前往按钮图标，适配悬赏列表新布局 | 已被取代 | mine 侧重截 `wq_goto_1..4.png` + json；本批以 runhey 新 UI 版 `921a2b82` 为准（含 8 条新几何与去 legacy 资产） |
| `ac482cf2` | WantedQuests | 调整悬赏列表 OCR 区域，适配新 UI 排版 | 已被取代 | `wq/ocr.json` 区域调整已被 `921a2b82` 的 `O_WQ_NUMBER`(541,14,97,33) / `O_WQ_MONSTER_TYPE`(634,154,483,52) 取代 |

> **冲突说明**：本批 13 条 cherry-pick **无一冲突**；唯一需本地自检补正的是 `d1ad2c09`（上游只改 `c/image.json` 未同步 `assets.py`，而本地运行时以 `assets.py` 为准）→ 补 `4698b48c`。因确实无冲突，**不需回溯上游历史查找冲突修复提交**。另两条易误判项（`6360d6a9` 与 `76490d67`）已分别用 `git merge-base --is-ancestor` / 同源 diff 比对核实为「已覆盖 / 已被取代」。

---

### §3.12 批次 33 扫描（四源，2026-11-06）

`fetch` 后 tips：`runhey/master 2211ba5d`（#2022）、`runhey/dev 55c3b151`（#2020）、`xylolit-mu/self 96215a7a`、`kongdr418/mine e53cb30f`（均 2026-11-05，本地 `czr` 停在 2026-10-29）。
`advise` 实跑 **306 条**（跨源去重），按 §2/§3 全部 hash 过滤后剩 **99 条**未记录候选；本批只取「零冲突 + 单模块 + 低定制」7 条（另 2 条为其后续修订），其余 89 条按簇留待。

> ⚠ 环境记录：本轮 `upstream_sync.py fetch` 直连失败——`.git/config` 的 `http.proxy=127.0.0.1:7897` 仍在，而本机 7897/10809 **均未监听**。改用 `git -c http.proxy= -c https.proxy= fetch …`（仅命令行覆盖，**未改任何 git config**）逐源直连成功。下次跑工具 `fetch` 前需先启动代理，或沿用此覆盖方式手工 fetch 后再 `advise`。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `8b4dc669b` | FindJade | 调度优先级表补 `FindJade` | 已覆盖 | 本地 `module/config/config_manual.py:17` 已含 `FindJade`，且顺序比上游更靠前 |
| `ce0e78d64` | Delegation | 「完成」改用独立点击区 | 已覆盖 | 本地 `tasks/Delegation/script_task.py:150-163` 已按 `O_D_DONE` 命中框动态点击缎带正下方的领取区，比上游固定 `C_D_DONE`(1169,175) 更稳；上游 assets 重排属移植噪声 |
| `940ba61b3` | deploy | 公开版更新器校验官方仓库来源 | 不适用 | 白名单写死 `xylolit-mu/OnmyojiAutoScript`，本 fork 的 origin 为 `ZH-CZR` → 会拒绝自身更新；`toolkit/` 等运行时产物也不入库 |

**余 89 条簇分布（下一批按簇评估，均未 ignore）**

| 簇 | 条数 | 主要来源 | 处理建议 |
|---|---|---|---|
| DraftDuel（含 `draft-duel`） | 35 | mine 29 + self 6 | **需立项**：新任务整链（大厅识别/邀请/选卡/上阵/V6 OCR），不可拆条 |
| WantedQuests | 9 | master 3 / mine 4 / self 2 | 部分被批次 32 `921a2b82` 取代，逐条核实后再定 |
| Component（runhey 新境界共享模板） | 6 | master | 需评估（`b46be8a68`/`cfcdad39d`/`9636b7240` 等大改） |
| SixRealms | 4 | master/self | 需评估（选岛限点、月之海漏识别） |
| GeneralBattle | 4 | master/mine | 多与 #1979 溢出清理/退出确认相关，先核是否已被本地覆盖 |
| Chess | 4 | self/mine | 新版棋局同步（`d3e81d3ad`/`ab9ea08ef`）→ **需立项** |
| MetaDemon | 4 | self/mine | 六星上供等大特性 → **需立项** |
| GlobalGame | 3 | master/mine | 余下为图标/阈值微调，可进小批 |
| dev_tools | 3 | self | 协斗/棋局配套（`96215a7a` 移除 latent policy） |
| workflow | 2 | master | **不适用**（本地无 `workflow` 目录） |
| FrogBoss | 2 | self | 需核实 |
| annotator | 1 | mine | `b68f1a686` V6 模型测试，依赖 V6 模型支持 |
| 其余单条 | 12 | 混合 | GameUi 商店招牌、Costume 幕间主题、Restart/desktop 空闲关闭、AreaBoss 同名跳过、Exploration 券刷、SwitchSoul/RealmRaid 素材重截（后两者大概率已被共享 UI 取代）等 |

> §3.10 的 WantedQuests 神秘妖怪/取消追踪链（`c695e50d`→`c3a88af9`→`9a6eb783`）**仍延后**，本批未动。

### §3.13 批次 34 扫描（nearaura master/dev + xylolit-mu/self，2026-11-09）

**源迁移**：`runhey` 账号已封禁（GitHub API 404，仓库 URL 直连 not found）；上游现为
`nearaura/OnmyojiAutoScript`（README 自述「账号被封后的临时仓库」），本轮 tip：
master `69b7ca1a`、dev `fd767a1d`；`dev_tools/upstream_sources.json` 已由 runhey 改为 nearaura。
`kongdr418/mine` 本轮直连多次超时，未纳入（本地已有批次 33 缓存 ref）。

11-04 后未记录候选 **23 条**，落地 4 项（见 §2），其余判定如下：

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `f636e9d99` / `043d3aa92` | SixRealms | 月之海岛屿漏识别 / 保留已选岛屿 | 不适用 | 本地 `tasks/SixRealms/moon_sea/base_moon_sea.py` 无 island marker / `_read_map_ocr` 架构，上游 `moon_sea/map.py` 本地不存在 |
| `657bb1b3b` | Costume | main16 庭院入口模板与规则 | 不适用 | 本地 `I_MAIN_GOTO_TOWN_16` roi=(839,330,23,43)，上游 (1014,346,14,34)，不是同一 UI |
| `4a6ad5583` / `5ba75f9b4` | GeneralBattle | #1979 御魂溢出清理点击 | 不适用（仅取 1 行） | 该规则只被本地未采用的 `battle_wait.py` 点击池使用；本地 `GeneralBattle` 无 `OVERFLOW_GHOST` 引用。仅移植其中与架构无关的 `SwitchAccount` OCR ROI |
| `9cfb4d290` / `d9c28f51e` | workflow | 周一自动建 PR / Agentic Workflows 升级 | 不适用 | 上游仓库自动化；本地仅 `auto-create-pr.yaml`，fork 不向 upstream 发 PR |
| `fd767a1dd` | README | 账号封禁后的临时仓库链接 | 不适用 | 纯上游仓库说明，与 fork 无关 |
| `181801d1c` / `a3e6e028f` | WantedQuests | 新增识别辅助 / 移除非法字符 | 已合入 | 与 `df572d01c` 同属 #2006 修复链，按最终语义一并移植 |
| `52e95af36` / `cc1a09ce1` | MetaDemon / 设置界面 | 恢复设置默认值 / 隐藏开发者配置 | 不适用 | 属 self 分支向 mine 收敛的回退，会删掉本地有意保留的设置项 |
| `d9ec87335` / `c2ac1adf6` / `c20c07498` / `7e0372214` | 多模块 | 大同步 / 策略更新 | 需立项 | 38~47 文件高定制批量，且依赖本地不存在的 DraftDuel / MetaDemon 协战 / 设置布局模块 |
| `591508f61` / `66f7d818e` / `fbfff8344` / `f219e8354` | MetaDemon / MetaDemonTicket / CustomTask / GameUi | 六星上供 / 门票房间 / 活动页路由 / 任务序列 | 需立项 | 本地无 `tasks/MetaDemon/boss_battle.py`、`tasks/MetaDemonTicket`、`tasks/CustomTask`、`tasks/GameUi/task_pages.py`，单条移植无法闭环 |
| `96215a7a9` | DraftDuel / dev_tools | 移除未使用 latent policy | 不适用 | 本地无 `tasks/DraftDuel`（棋局在 `tasks/Duel`） |
| `1fd87d347` | Exploration + EvoZone | 保持探索退出 / 专属门票设置 | 已合入（部分） | 只取 Exploration 两处；EvoZone `_config` 属 self 门票刷取特性依赖，本地不适用 |

**冲突**：本轮无 cherry-pick，全部按本地架构手工移植；无需回溯上游修复提交
（#2006 的 `a3e6e028` 即上游自带后续修复，已随语义吸收）。





### §3.14 批次 35 扫描（仅 `xylolit-mu` 四分支，2026-11-09）——本轮无小修可落地

`fetch` 后 tips：`mine 1ac78957`（2026-07-15，**已是 czr 祖先**，`rev-list` 差集 `414/0`，含 PR #193/#198 全部内容）、
`self 23edaa78`（2026-11-08，即批次 34 已吸收的 tip）、`pr 670f194a`（2026-09 旧分支）、`test f9d7220c`（2026-08 前）。
`advise` 实跑 125 条（三源跨去重），按 §2/§3 hash 过滤后仅剩 **15 条 + `2d396bfa`**，全部为簇级改动：

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `10047b2d` | SixRealms | 六道宁息确定兼容修复 | 不适用 | 依赖已判不适用 `631968c6`（951 文件页面框架重写）新增的 `page_sr_confirm_tip` 与扩展版 `ui_click_until_appear`；新增资产 `I_UI_CONFIRM_BACKUP` 为 self 系平铺小按钮（109×41，roi 700,419），本地共享确认/取消为 179×66 / 177×62（roi 664,407 / 438,407）——非同一 UI 代际，模板与坐标均不可复用（需实机取图后立项） |
| `d944d411` | Chess | 限制棋局每轮购买最多三次点击 | 不适用 | 改的是本地不存在的 `ui_click_until_disappear(..., confirm_frames=2, max_clicks=3)` 调用（本地该方法仅 3 参数，全仓无 `confirm_frames`） |
| `f715ce27` / `161c1c0a` / `bbb7f1d0` / `3a74669c` / `e3b4bb00` / `7b1e1a4d` / `3b29b9af` / `96dbafdd` / `5e55c673` / `fe4206af` | DraftDuel | 协同对弈整链（大厅/邀请/手牌/上阵/结算） | 不适用（需立项） | 本地无 `tasks/DraftDuel`（棋局在 `tasks/Duel`），整链依赖新任务目录与 `module/cooperation.py` 扩展，不可拆条 |
| `1019131f` | DraftDuel / dev_tools | 协斗大轮切换与棋局结算恢复 | 需立项 | 配套 DraftDuel 整链 |
| `9a60107c` | desktop | 接入 PR #6 桌面后端 + 多开/异步启动加固（34 文件） | 需立项 | 桌面/设备/服务端框架级改动；本地桌面层来自批次 27（runhey 版），需专项评估差异 |
| `2d396bfa` | 多模块 | 悬赏/委派/结界轮换/六道/协同聚合同步（70 文件） | 部分已覆盖 / 需立项 | WantedQuests 段已被批次 32 `921a2b82` 取代；Delegation「完成」本地 `O_D_DONE` 方案更优（`ce0e78d64` 已判已覆盖）；GlobalGame/六道资产属 self 代际（`ui_confirm.png` 124×39）不能复用；其余为 self 框架配套 |

**冲突**：本轮无 cherry-pick，因此无冲突。**结论**：`self` 的「零冲突 + 单模块 + 低定制」小修已清空；
批次 34 建议的小批（GlobalGame 3 / annotator 1 / desktop 3）来自其它源（master/mine），不在 self 范围内。
**未做**代码改动，故无新增回归测试、无代码推送。**下一批建议**：如需继续小批，改从
`nearaura/master` + `nearaura/dev` + `kongdr418/mine` 取 §3.12 的 GlobalGame 3 / annotator 1 / desktop 3；
self 仅剩 DraftDuel / Chess / MetaDemon / desktop 四个大簇，需单独立项。

### §3.15 批次 36「从头重评 self」（2026-11-09，只读，不改代码）

**口径**：以 `czr...self` 的分叉点 `371b4ec9`（2026-08-14）为基线，对 self 独有 **320 条**全量重评。
**方法**：① `git cherry czr self` 判 patch 等价（312 行，`-` 23 / `+` 289）；② 与本文件 §2/§3 hash 集交叉；
③ 未记录条目逐簇 `git show` + 本地 `git ls-files` / 符号 grep 核对落点。**不改代码、不 cherry-pick**。

**总量对账**

| 项 | 数量 | 说明 |
|---|---|---|
| self 独有提交 | 320 | 分叉点 `371b4ec9`，全树差异 2004 文件 / +63,879 / -8,384 |
| 台账已记录（§2/§3） | 227 | 前 35 批已判（含已合并 / 已覆盖 / 不适用 / 需立项） |
| 未记录 | 93 | 此前被 `--since 2 months` 与「patch 已在本地」过滤 |
| └ `git cherry` 判已等价 | 11 | **已覆盖**（patch 已在 czr，无需再判） |
| └ 逐簇核实 | 82 | 见下表 |

**82 条逐簇判定**

| 簇 | 条数 | 代表 hash | 判定 | 依据 |
|---|---|---|---|---|
| Chess 早期链（7-17~8-14） | 34 | `ba0e8d46` / `44577968` / `53b2035a` / `efc52da8` / `03044ed4` / `a2c78920` / `f662b808` | 不适用（已被取代） | 本地 `tasks/Chess` 来自 mine 系新版链（`6029ad08`，批次 31 判需立项）；self 这套是更早的独立实现，资产/状态机不兼容；`03044ed4`/`efc52da8`/`a2c78920` 为 219~435 文件的批量图片更新，本地仅命中 2~26 个路径 |
| MartialArts（7 月版） | 5 | `c7705a64` / `71a906e0` / `863d8e5c` / `2f40968e` / `d8bccf26` | 不适用 | 本地 **无 `tasks/MartialArts`**，对应能力在 `tasks/MartialTournament`（不同代际）；`71a906e0` 的 QuickLoadout 组件本地已有，但挂载点不存在 |
| OCR 后端实验 | 3 | `3882364a`（ONNX）/ `97ff22a5` / `d60fc53a`（回退 Paddle） | 不适用 | 本地 `module/ocr` 已用 `ppocronnx`，与上游实验链无关 |
| TeamScroll 增删对 | 8 | `673838d0`→`e6b5eaa7`、`65dad70f`→`3de9a587`、`3478228b`→`ed4667ac`、`4055f276` | 不适用（净零） | 4 组 add→revert 净零；且本地 **无 `tasks/TeamScroll`** |
| ActivityShikigami 资产 | 2 | `ac6109a1` / `bfcdb6e9` | 已覆盖 | `as_climb_mode_ap/pass/switch`、`as_to_battle_main`、`as_main_goto_act` 等 PNG 本地均已存在 |
| 空过 / 文档 / i18n | 4 | `76cf8cc5`（docs）/ `b588f923`（斗技 i18n）/ `d84a9024`（merge 无实质 diff）/ `78b426de`（删冗余 0 行） | 不适用或已覆盖 | 无运行语义或文本已在本地 i18n |
| 驭灵 / 斗技 / 鼬乐园 / 秘闻 / 日课 | 8 | `955b09f1` / `9708c4c0` / `ac1a43b1` / `ba9c9355` / `731cad1f` / `e087b8c6` / `c5c2d073` / `e467fb7b` | 已覆盖 | `C_GR_C_*` 新 ROI 本地一致；`I_D_CELEB_HONOR`/`I_DUEL_HONOR` 已在；`I_TOWN_GOTO_ENTERTAINMENT` 本地已是 35×26；`_wq_icon_click_area` 本地不存在（直接点进度条）；`I_SIDE_SURE_SPECIAL` 本地已移除；navigator 已有 `TOWN_FALLBACK_*`；`demon_de_defeat_1~4` 已在 |
| 大合并 / 搬运 | 4 | `3bc2d41d` + `73bcafcb`（60 文件）、`d098e5b9`（98 文件）、`3772e03f`（PR #3，50 文件） | 已覆盖（mine 系） / 需立项 | 均为「self ↔ Azur mine」对搬提交，本地经 mine 系 1~35 批已获得大部分；`3772e03f` 的逢魔新实现与本地 `find_boss` 三轮重进实现不同，若要采用须立项 |
| 设备层合并 | 1 | `71c9ab81`（mumu12 +114 / platform_windows +66） | 需评估 | 本地设备层为自研 `module/device/*`，与 self `platform2` 框架不同，不能直接 cherry-pick |
| 逢魔保底 / 道馆 | 3 | `bee5887e` / `904686c1` / `95163e66` | **部分可移植** | `bee5887e` 的 find_boss 重写已被本地更完善的三轮重进实现取代；但 `904686c1`（打开 boss 页 3 轮失败 → `TaskEnd` 而非 `GameStuckError`）本地尚未吸收（`script_task.py:165` 仍 `GameStuckError`） |
| 御魂自选弹窗 | 1 | `dd96057e` | **可移植** | 本地 `GeneralBattleAssets` 无 `I_GB_CLOSE_RED`、`Orochi` 无 `_handle_result`/`_handle_missing_battle_page` 覆写，御魂自选活动弹窗仍会挡结算 |
| 寄养开关 + 活动入口 | 1 | `38a8f00d` | **可移植** | 本地 `KekkaiUtilize` 无 `disable_utilize_harvest`；`ActivityShikigami/page.py` 仍单次 `I_TOGGLE_BUTTON` hook，未做最多 8 次轮换 |
| 门票 0 OCR 复核接入 | 1 | `18ededee` | **部分可移植** | `BaseActivity.verify_zero_ticket` 本地已有，但 `ActivityShikigami/base_act.py` 未接 `_ticket_needs_verification` |

**下一批（批次 37）建议短名单（4 组，预计 12~15 文件）**：**✅ 已于批次 37 落地（`8334c797`，手工移植 + 17 项回归测试）**
1. `dd96057e` 御魂自选弹窗（含 `gb_gb_close_red.png`）—— 已落地；
2. `38a8f00d` 寄养开关 + 活动入口 8 次轮换 —— 活动入口已落地；寄养开关本地 `utilize_harvest` 已覆盖，未重复引入；
3. `904686c1` 逢魔 boss 页打开失败改 `TaskEnd` —— 已落地；
4. `18ededee` 活动门票 0 时的进战复核接入 —— 已落地。
以上 4 组均不依赖 self 页面框架与 self 代际资产（仅 1 张通用弹窗关闭图），已手工移植 + 补回归测试。

**仍未逐条核实（3 条）**：`3bc2d41d`/`73bcafcb`/`d098e5b9` 三个大合并的内部零散改动——已按「mine 系同期提交」判已覆盖，若后续在实机发现 self 独有行为，再回查这三个提交。

### §3.16 批次 39 扫描（nearaura/dev + kongdr418/mine，2026-11-11）

**可达性**：`runhey/OnmyojiAutoScript` 与 `xylolit-mu/OnmyojiAutoScript` 现已 `Repository not found`
（账号封禁），`fetch` 自动回退到本地缓存 ref；实际有新增的只有 `nearaura/dev`（tip 由 `fd767a1d`
→ `a86b0e50`，9 条，含 PR #2 merge 与 `origin/dev` merge）与 `kongdr418/mine`（`91f7d916` → `446e869e`，1 条）。
`nearaura/master` 仍为 `69b7ca1a`（批次 34 已吸收）。

**Gitee 镜像（2026-11-11 补充）**：`runhey` 的 Gitee 镜像 `https://gitee.com/runheng/OnmyojiAutoScript`
**可直接访问**，`ls-remote` 结果与 `nearaura` 完全一致：`master 69b7ca1a`、`dev a86b0e50`；
另有一条独立分支 `solana 372ccc3d`（2026-11-03），含 `dev` 之外的 **88 条**提交——内容是
uvicorn 后端入口 / supervisor / MPipe / WS 各 topic（ConfigNav、TaskQueue、Dashboard、Preview 等）
的服务端重写线，属框架级大改，与本批「新提交小修」无关，**未纳入、需立项**。
`xylolit-mu` 与 `kongdr418` 在 Gitee 无镜像（404），仍只能靠本地缓存 ref。

| 上游 hash | 模块 | 标题 | 判定 | 原因 |
|---|---|---|---|---|
| `a787a58a` / `41753016` | device/minitouch | 低 `max_pressure` 压力区间修复（PR #2） | 已合入 | 见 §2 批次 39；merge `41753016` 只含该提交，无额外内容 |
| `3ede58e1` | atom/image + atom/animate + base/utils + device/desktop | 模板搜索区初始化外扩 | 部分采纳 | 动画比较区固定（`_crop_roi`）已合入；「无条件外扩 2px / 删除 `set_roi_match_padding`」不采纳，见 §2 理由 |
| `835338cb` | MetaDemon | 2025 版鬼王识别模板与 ROI 刷新 | **已落地（批次 40）** | 原判「本地旧代际无落点」；用户决策「不是最新的不用理会」后，按 **§3.17** 整模块替换为上游新代际，该条随替换一并生效 |
| `8d48055c` | MetaDemon | 删除未使用图片资产 | **已落地（批次 40）** | 原判「本地仍引用 `I_MD_FIRE` 等，删除即破坏」；整模块替换后这些资产本身即不再存在，该条的删除清单已随 §3.17 一次性完成 |
| `411ef6d3` | MetaDemon | 公开（已共享）鬼王识别 | **已落地（批次 40）** | 原判「需立项」；新代际提供 `I_BOOS_PUBLIC` + `run()` 的 self-boss 分支，已随 §3.17 整模块替换落地 |
| `305defd0` | workflow | 镜像源改用当前仓库 owner | 不适用 | 本地 `.github/workflows` 无 `github-mirror.yml`（仅 bug_report/feature-request/others/auto-create-pr） |
| `bc2211da` | docs | 文档链接换新域名 | 不适用 | 仅 README 与任务 README 的外链，无功能影响；本地 README 为 fork 版 |
| `a86b0e50` / `41753016` | — | merge 提交 | 无内容 | 只聚合上述已判定条目 |
| `446e869e` | DraftDuel | 记录真实协同对局 | 不适用 | 本地无 `tasks/DraftDuel`（棋局在 `tasks/Duel`），与 §3.14 DraftDuel 整链判定一致 |

**冲突**：本批无 cherry-pick，全部手工移植，因此无冲突；`3ede58e1` 属于批次 27（`7c5f380b`）已移植特性的后续演进，
上游没有额外的「冲突解决」提交需要回溯。
**影响面**：`a787a58a` 影响 minitouch 点击/长按压力取值（仅 `max_pressure < 20` 的设备行为变化，其余区间不变）；
`3ede58e1` 影响 `wait_animate_stable` 两个调用点（`Exploration.sweep_end`、`base_task` 通用入口），搜索区不变、仅帧比较区固定。
**回归测试**：`tests/test_upstream_batch39_fixes.py` 8 项，本机全绿；全仓 discover 321 项仅 7 项既有 HeroTest 失败（与基线一致）。

---

### §3.17 批次 40：超鬼王（MetaDemon）整模块替换

**触发**：用户「现在有个超鬼王活动，上游有没有相关的功能」→ 上游新代际 `tasks/MetaDemon` 是当前 2025/2026 版活动的唯一维护实现（`835338cb` 2025 版模板、`411ef6d3` 公开共享鬼王，2026-11 仍在更新）；本地旧代际（`md_md_*` 资产 + 门票 1~6 星合成 + 邀请好友 + 上供）在上游历史中**从不存在**，属 mine/self 系分支的独立实现。

**决策**：用户答「**不是最新的不用理会**」，据此**不保留本地旧代际**，直接以上游最新实现为准，不做新旧双轨。

**上游来源**：`nearaura/dev` = `a86b0e50`（与 Gitee `runheng/OnmyojiAutoScript` `dev` 同 tip），执行 `git checkout nearaura-dev/dev -- tasks/MetaDemon` 整体覆盖。

**改动清单**（提交 `2b7f72e0`）：
- 覆盖 25 个文件：`assets.py`、`config.py`、`script_task.py`、`md/image.json`、`md/image_2025.json`（18 条）、`md/ocr.json`、18 张新模板。
- 删除 36 个旧文件：全部 `md_md_*.png`、`goto_metademon_list.json`、`swipe.json`、`md_check_act_list_metademon_act.png`、`md_check_boss_page.png`。
- 新代际核心：`I_ENTER2`/`I_FIND_DEMON`/`I_BATTLE_DEMON`/`I_BOSS_EMPTY(_1/_2)`/`I_BOSS_CONVENE`/`I_BOOS_PUBLIC`/`I_CRAFTING_*`/`I_STAR56_POS_1`/`I_STAR56_HP_THRESHOLD_T|F`/`I_ENTER_ENSURE`；OCR `O_MD_EXHAUSTION`(DigitCounter)、`O_MD_TICKET`、`O_MD_COUNT_INFO`、`O_CRAFTING_CARD_1`、`O_MD_FULL_NAME`(Full)、`O_BOSS_EMPTY_1`。
- 新代际策略：5/6 星走「式神全名 → 自定义阵容组」映射（`Strategy.parse_all` / `strategy2group_team` 双字符容错 / 血量阈值高低切换 `group_team[0:2]` vs `[2:4]`），普通鬼王首战用默认阵容组。

**本地框架适配**（上游新代际依赖、本地缺失的部分）：
1. `tasks/base_task.py`：新增 `self._boss_mark_flag = False`（本场战斗是否已点过「标记」）。
2. `tasks/Component/GeneralBattle/assets.py`：新增 `O_BOSS_MARK`（`roi=(379,44,50,21)`，keyword `已标记`）。
3. `tasks/Component/GeneralBattle/general_battle.py`：新增 `boss_mark(enable=True)` / `boss_mark_reset()`——首次 `ocr_appear` 即置位，否则 `click`；`click_record` 达 3 次放弃，避免 `GameTooManyClickError`。
4. `config/template.json`：只替换 `meta_demon` 块为新 schema（`scheduler` / `switch_soul` / `meta_demon_config` / `md_default_strategy` / `md_strategies_1`），其它任务块零改动（整表重生成曾产生 134/29 无关 churn，已改为 splice）。
5. `tests/test_upstream_batch34_fixes.py`：移除 `MetaDemonTicketThresholdTests`（旧代际门票阈值，随替换作废）。
6. 删除 `tests/test_upstream_metademon_assist.py`（批次 38 上供/协助，随旧代际作废）。

**随之移除的本地独有能力（未回补，需要时须另做叠加）**：门票 1~6 星按阈值合成、邀请好友、昨日奖励领取、强力追击开关、按星级切御魂、批次 38 的六星上供/好友协助（`Mode.BOSS_ASSIST` / `assistance.py`）、`tasks/MetaDemon/md/goto_metademon_list.json` 导航。

**验证**：
- `python -m py_compile` 通过；`ScriptTask` 可导入，MRO 含 `GeneralBattle`/`RightActivity`/`MetaDemonAssets`。
- 配置往返：`md_strategy_count=2` 时 `md_strategies_1/2` 正确展开为 list 并拍平回 JSON；`count=0` 得到空列表且 `Strategy.parse_all([]) == {}`；`auto_tea` 被 `field_validator` 强制 False。
- OCR API 兼容：`O_MD_EXHAUSTION.ocr()` 返回 `(current, remain, total)`，`current_exhaustion()` 取 `cu`；`O_MD_FULL_NAME.mode.name == 'FULL'`（本地 Full 解析可用）。
- 新增 `tests/test_metademon_module.py` 12 项全绿（每张 RuleImage 的 png 存在、ROI/阈值与 `image*.json` 一致、旧资产已删、配置默认值与往返、继承与方法存在性）。
- 全仓 discover 320 项，仅 7 项既有 HeroTest `Timer` 失败（与基线一致）。

**未验证 / 遗留**：
- 18 张新模板的阈值与 ROI **需实机标定**（本轮全部来自上游截图，本地区服 UI 可能有差异）。
- 上游 `buy_tea()` 仍为 `pass` 空实现（`auto_tea` 被强制 False，`current_exhaustion() > 100` 时直接结束本轮）。
- `md_use_strategy` 默认 False，即默认走 `cached_default_group_team`；自定义 5/6 星阵容需用户自行配置。

**判定**：§3.16 的 MetaDemon 三连（`835338cb` / `8d48055c` / `411ef6d3`）由「不适用 / 需立项」改判为**已落地**；§3.13/§3.14 中 MetaDemon 整链立项条目一并收口。

**✅ 推送状态：已推送** —— 直连两次失败（`Recv failure: Connection was reset` + 21s `Could not connect to server`），第 3 次成功（`feafea1a..3138ff1f czr -> czr`）；代码提交 `2b7f72e0` 与本台账 `3138ff1f` 同批送达。

---

### §3.18 批次 41：2026-11-09~11-11 新提交 triage（2026-11-11）

**已落地**：`f99d75c2`（配置泛型）、`bf71e3a5`（协斗模板/好友邀请/GlobalGame 阈值/契灵球数 OCR）、`844d3bec`（交换身份半量切换）；明细见 §2。

**不适用**（不要重复分析）：

- kongdr418/mine `4d75666a` / `61d3f8cf` / `36dde020`（MetaDemon：鬼王页识别图、一键配置 frame、礼包窗口点右上亮叉）：本地 MetaDemon 已按批次 40 换成 nearaura 新代际，无 `md_check_boss_page`、`md/frame.json`、`boss_battle.py`、`md_quick_loadout_frame_badge_*`；要跟进须再做一次整模块换代。
- kongdr418/mine `fb3c10a0`（突破券 OCR 区域）：本地 `O_REALM_RAID_NUMBER`/`O_REALM_RAID_NUMBER1` 没有 `_META` 变体，且 ROI 已在批次 23 独立标定（`920,12,78,30`），非同一实现。
- kongdr418/mine `c7e0c7bd`（DraftDuel 训练模型，+3014 行）/ `363d676b`（DraftDuel 邀请超时）：本地无 `tasks/DraftDuel` 模块。

**暂缓 / 需立项**：

- lgg686/self `a279ab60`（「同步上游」整包，225 文件、+1.1 万行）：含 `AutoStory` 新任务、超鬼王快速预设、`module/cooperation.py` 与配置 schema 改动，同时覆盖旧代际 `tasks/MetaDemon/assistance.py`、`boss_battle.py`；与本地批次 40 新代际直接冲突，须单独批次评估。**（2026-11-11 更新：仅摘取 `tasks/MetaDemonTicket` 门票任务落地为批次 42，其余部分仍暂缓，见 §3.19）**

**验证与收尾**：

- 合并提交 `a49eec9a`（`--no-ff`）；`pytest tests` → **339 passed / 9 failed**，9 项均为既有的 HeroTest `Timer`（7）与 SwitchOnmyoji 环境用例（2），与批次前基线一致；新增 12 项用例全绿。
- 冲突按「保本地架构、只取语义」处理：`assets.py` 的 regenerator 重排与 `profile="High"`（本地 `RuleImage` 无该参数）一律不取；勾玉 `roi_front` 保留本地标定值，仅取上游放宽后的 `roi_back`/阈值。
- 上游后续修复核对：`844d3bec` 之后 lgg686 无再动 `tasks/BondlingFairyland` 的提交（`git log 844d3bec..lgg686-self/self -- tasks/BondlingFairyland` 为空），无补丁可追加。

**需实机验证**：协斗邀请/协作类型识别在新模板下的命中率（9 张图来自上游截图）、勾玉/猫粮/狗粮放宽后的 `roi_back` 是否会误命中相邻按钮、交换身份两段实际次数是否各占一半、配置导入含列表字段的 `template.json`。

**✅ 推送状态：已推送** —— 直连一次成功（`577ef9ff..bf9d7408 czr -> czr`），代码合并提交 `a49eec9a` 与本台账同批送达。

---

### §3.19 批次 42：超鬼王门票刷取（2026-11-11）

**来源**：lgg686/self `a279ab60` 整包中的 `tasks/MetaDemonTicket`（4 文件、390 行）。整包其余 221 文件（旧代际 MetaDemon、DraftDuel、AutoStory、配置框架改造 `settings_presentation`、协同运行时 `module/cooperation.py`）**本轮不取**，仍按 §3.18 暂缓。

**已落地（手工移植 + 本地适配）**：

- `tasks/MetaDemonTicket/__init__.py` / `config.py` / `script_task.py` / `ticket_farming.py`：门票任务本体。`TicketMode`（觉醒/探索）、`ExplorationTarget`（全部/金币/经验/达摩）、`TicketGeneralConfig`（刷票玩法、限时 45 分、身份、探索候补轮换、觉醒加成/麒麟/层数、探索目标）。
- 复用而非重写：觉醒走 `tasks/EvoZone` 的 `run_leader`/`run_member`/`run_alone`，探索走 `tasks/Exploration` 的 `pre_process`/`exec_exp_page`；用 `TicketConfigProxy` 只把 `config.evo_zone` / `config.exploration` 替换为门票专用配置，其余字段（`global_game` 等）回落真实配置，避免改动两个任务本体。
- `Component/GeneralBattle`：新增 `O_METADEMON_PASS`（结算界面门票计数，`1126,3,95,39`，`DigitCounter`）+ `gb/ocr.json` 同步。
- 注册：`ConfigModel.meta_demon_ticket`、Activity Task 菜单（`MetaDemonTicket` 位于 `MetaDemon` 之前）、`config_manual` 优先级注释。

**本地适配（与上游不同之处）**：

1. **门票资产**：刷取前的庭院检测改用本地既有 `MetaDemonAssets.O_MD_TICKET`（`923,18,82,30`），上游 `O_METADEMON_PASS_EXP`（`919,16,114,34`）在本地不存在。
2. **去掉 `settings_layout`**：本地没有 `tasks/Component/config_settings_layout.py` 与 `module/config/settings_presentation.py` 的后端下发机制；`split_legacy_meta_demon` 与其依赖的 `module/config/multi_select.py` 未引入（本地无旧版门票选项，无需迁移）。
3. **去掉协同运行时**：本地无 `config.cooperation_runtime` / `module/cooperation.py`，`TicketPartnerFinished`、`screenshot()` 轮询、`peer_task_completion`/`prepare`/`notify_task_completion` 一律移除；门票任务按本号满票即结束。
4. **去掉探索难度与结界突破钩子**：本地 `ExplorationConfig` 无 `difficulty` 字段（探索流程只走困难逻辑），`Exploration` 也没有 `activate_realm_raid` / 绘卷突破调度，故不引入 `ExplorationDifficulty` 与该方法覆写。

**验证**：

- `pytest tests/test_upstream_batch42_fixes.py` → **22 passed**。
- `pytest tests` → **361 passed / 9 failed**，9 项仍为既有 HeroTest `Timer`（7）与 SwitchOnmyoji 环境用例（2），与批次前基线（339/9）一致（+22 为本批新增）。
- 导入自检：`tasks.MetaDemonTicket.script_task`、`module.config.config_model.ConfigModel`（`meta_demon_ticket` 默认 `TicketMode.AWAKE`）均通过。

**需实机验证**：

- 结算界面 `O_METADEMON_PASS` 的 `DigitCounter` 读数是否稳定（`x/y` 格式、上限非 0）。
- 庭院探索入口 `O_MD_TICKET` 的满票判定（`current >= total`）在不同皮肤下的命中。
- 觉醒/探索复用流程在 `TicketConfigProxy` 下是否读到门票限时（45 分）与无限次数（`2**31-1`）。
- 探索模式下的候补式神轮换 + 关闭锁队组合。

**✅ 推送状态：已推送** —— `45035889..df77f964 czr -> czr`（代码、测试与本台账同批送达，未拆第二次提交）。

---

### §3.20 批次 43 扫描（nearaura master/dev + kongdr418/mine + lgg686/self，2026-11-12）——已剔除 xylolit-mu

`advise` 实跑 298 条（跨源去重），按台账 hash 过滤后 **132 条**未记录候选；逐条 `show` 语义核实后分类如下（**不要重复分析**）。

**已覆盖（同批本地修复提交已等价落地，共 18 条）**：
- 超鬼王/门票/锁队：`ec8ef406c`（auto_shared_boss + `md_md_win.png`）、`484337f57`（胜利界面识别循环）、`09571eb4e`（开战前解锁队伍）、`209f8fad4`（门票 OCR 改 1119,7,114,32）、`c8c9c6488`（探索章节可选）、`429b8570a`（门票越界按识别错误）、`d2feec52d`（调度白名单已含 `meta_demon_ticket`）。
- 探索/寮宴会/悬赏：`fd7e20a5e` + `0b8ef1cbe`（探索标识 ROI）、`cc83b1a20`（寮宴会旗帜）、`cc131ec58`（悬赏去重按卡清零）、`82fae57e2`（目标名子串匹配）、`5ac08e11f`（追踪按钮搜索区，本地更宽）、`40fbf76a8`（逢魔 town↔rwt 重进，本地已是 `page_town`）。
- 战斗退出/瞬结：`aa91067c6`（狭间战斗瞬结）、`57fc173bd` + `e68b0b74d`（退出战斗确认按钮，本地 `exit_battle` 已统一 `I_UI_CONFIRM`）、`100879bbc`（切换确认弹窗，同上）、`b86240120`/`f9e2ec0f8`（GameUi 探索标识测试，本批以 `tests/test_upstream_batch43_fixes.py` 覆盖）。

**不适用（本地无对应模块/结构）**：
- `DraftDuel` 全簇（kongdr418 + lgg686 共约 70 条）—— 本地无 `tasks/DraftDuel`。
- `45b5772dc`（`hyakki_draft` 不存在）、`ea6b92f93`（`tasks/SixRealms/moon_sea/map.py` 不存在）、`692ee2156`（上游 AreaBoss 已重构 `boss_fight(defeated=)`，本地为筛选分类版）。
- ActivityShikigami 旧结构簇：`48ba3280c`/`6084f2100`/`5cf103ea8`/`be8ae17cb` 等 —— 本地 `activities/normal.py` 仅 85 行且已重写，上游 `activities/exploration.py` 不存在。
- MetaDemon 上供/快速装配：`ea8e72f3a`/`4d9100272`/`f41995385` —— 本地 `tasks/MetaDemon` 无 `assistance.py`/`quick_loadout.py`（批次 40 整模块替换后未引入）。
- 悬赏模板簇 `1eeee5ff8`（本地无 `I_WQC_BATTLE_END_TALKS`）、`WeeklyPurchase` 相关（本地无该模块）。

**需立项 / 待决策（不 ignore）**：
- `9df707fb`（棋局买卡点击上限）—— 依赖上游新版 `ui_click_until_disappear`（`guard`/`visible`/`confirm_frames`/`timeout`），本地仍为旧实现；本批已回退其整文件替换（`3d6b59d4`），需立项验证。
- `c1412496b`（DailyTrifles/FrogBoss 资源参数）—— 与本地重构后的资产表冲突且以重排为主，价值低。
- `dd51be244`/`f0c8473d0`（悬赏小字叠背景 OCR 漏识重试 / 2x 重扫放宽）—— 触及 `WantedQuests/script_task.py` 核心循环，延后。
- `5a752388e`（GeneralBattle `battle_wait` 重写链）—— **禁止混进小批**，须单独立项并做启动验证。
- 桌面簇 `92d2dbd83`/`a57891b87`/`d06d9225e`/`fd812e53e` 等 —— 与本批无冲突但涉及设备层，单独立项。
- Costume 主题簇 `ba699f872`/`2d7b85de3`/`ab2b0c008` —— 大资源集，单独立项。

---

### §3.21 批次 44 扫描（nearaura master/dev + kongdr418/mine + lgg686/self，2026-11-13）——本批 11 条新提交

按台账 hash 前缀过滤后 11 条 11-11 之后的新提交，逐条 `show` 核实。已合入项见 §2；其余判定如下（**不要重复分析**）：

**已覆盖 / 不采纳（本地 11-11 商店修复已等价覆盖）**：
- `f1ba2a5c5`（nearaura：`I_CHECK_MALL` ROI 改 1087,413,47,114、阈值 0.8→0.6、新模板）与 `81bb25a7`（kongdr：ROI 改 231,455,86,78、新模板 + 棋局排名页）—— 本地 `page_mall` 已是 `I_CHECK_MALL` + `I_CHECK_MALL_PURPLE` + `I_CHECK_MALL_LANTERN` 三选一，换主模板会覆盖本地 11-11 针对活动装饰的修复；棋局排名页 `I_CHECK_CHESS_RANK` 本地已存在。
- `9eea7c9d5` + `bf893c0d3`（Duel `I_EXIT_WAITING` / `I_DUEL_MAIN_UESLESS_MESSAGE` / `O_D_CELEB`）—— 本地无调用点；`9eea7c9d5` 夹带本地不支持的 `profile="High"` 字段，且其 `goto_page(page_main)` 收尾本地早已存在。
- `7b0da642a` / `ba0d49b7c`（BondlingFairyland 漏邀兜底）—— 本地批次 41 已重构 handoff1/2，文件内无 `battle_state` 分支，等价逻辑已由本地流程覆盖。
- `a34240a55`（设备竖屏时登录截图崩溃）—— 与 §3.20 已判定的 nearaura `01f24bdb` 同族，本地运行时对竖屏帧有拦截。

**不适用（本地无对应模块/结构）**：
- `83b82fd55`（`module/cooperation.py` 协同心跳）、`7478e169f`（`tasks/MetaDemon/assistance.py` 上供召唤顺序）—— 批次 40 整模块替换后本地无这两个文件，上供/协助模式未恢复。
- `3c81120dd`（RealmRaid `I_FRESH_ENSURE` 重截刷新确认）—— 本地无该资产与流程。
- `1ff269b07` / `f7302af26`（WeeklyPurchase 海汐/皮肤券）—— 本地无 `tasks/WeeklyPurchase`。
- `25cc699b1`（自动创建 PR workflow）—— 上游 CI，本地不用。

**需立项（不 ignore）**：
- `547dfba6b`（AutoStory + ExplorationFight + CustomTask 三任务迁移，37 文件）—— 本地无对应任务模块与 `settings_presentation` 配置框架，属新增功能集，须单独立项验证。

---

## §4 待决策

1. ~~**掩码匹配 / 零方差拦截 / nan-inf 清洗**：是否以**服务端**方式补进 `module/image/runtime.py`（思路源自 `51582666`）。**批次 9 新增同源实现 `8753481b`（+152/-30，`module/image/runtime.py` + `module/atom/image.py`）**——与上述议题合并评估。~~ **✅ 已决策并落地（批次 22，手工移植 `8753481b`）**：三项全部按服务端化方式并入本地 —— ① `Masked template matching`：掩码取模板同目录 `xxx_mask.png`，非零参与/零忽略，`match_rule`/`match_all`/`match_all_any` 一并支持，掩码缺失或尺寸不符自动回退普通匹配；② 缓存指纹纳入掩码 `mtime:size`；③ 退化判据改为按「掩码非零区域」判定 + 匹配结果 nan/inf 清成 -1.0。<br>**进展（批次 12）**：其中**与掩码无关**的两项（`_template_is_degenerate` 零方差拦截 + 多尺度 `min_scale + index*step` 浮点漂移修复）已按无掩码方式移植进本地 `module/image/runtime.py`（源 `cf6fa6a5`，见 §2 批次 12）。<br>**同源 runhey 版 `51582666`** 改的是 `RuleImage` 里的 cv2 直调（本地该处已不参与匹配），**判不适用**（见 §3.1）。<br>**实跑证据（本机 cv2 5.0.0）**：合成用例中背景变化的场景下普通匹配 0.669（落榜）→ 掩码匹配 **1.0** 命中于 (60,70)；掩码缺失/11×11 尺寸不符时分数与普通匹配**逐位一致**（0.6693735718727112）；同色源图 + 掩码在 OpenCV 下产生**全 nan**，清洗后按不匹配处理。回归测试 `tests/test_masked_template_match.py` 20 项全绿。
2. **是否标记 ignore**：历史累计 `ignore` **90** 条（§3 + §3.1 中除「延后 / 待决策」项外的全部判定项）。**以后 §3 新增条目应随手 `ignore`**，避免每轮重现。
   - ⚠ **注意（批次 10 发现）**：`dev_tools/upstream_ignored.json`（工具 `DEFAULT_IGNORED`，**不入库**）曾**本地缺失**——此前 90 条 ignore 状态在本地已丢失。**批次 10 已重建该文件但仅含 4 条**（下述），历史 90 条仍未恢复 → `advise` 仍会把它们重新列为待同步。**接手续接时必须按本文件 §3 hash 集在脚本侧过滤**（不能依赖该文件），如需恢复可用 `ignore --hashes <§3 全部 hash,…>` 重建。
   - 批次 10 新增判定 4 条**已 `ignore`**：`19ae288c4`（已覆盖）、`8e62ae47e`（不适用）、`1ebf4f4f0` + `0c7f778c6`（净零对）。批次 17 再 `ignore` 4 条（`990c45900`/`55f51238f` 已覆盖、`f871f3795`/`a27a91fe9` 不适用）。批次 21 再 `ignore` 6 条（`27241886`/`b3d6fe98` 不适用、`efd39e18`/`cf6fa6a5` 已覆盖、`e930e2e1`+`8195cc60` 净零对）。批次 22 再 `ignore` 2 条（`8753481b` 已合并、`51582666` 不适用）。批次 23 再 `ignore` 1 条（`d6c42bee` 不适用）。批次 24 无新增 `ignore`（本地自研、无上游来源）。批次 25 再 `ignore` 9 条（`bedff718`/`985ac267`/`5770f91e` 已合并、`2f5c306e` 不适用、`aaac78b3` 已覆盖、`372ef8f3`+`54803c50`+`614b6b84`+`e56482ca` 净零对）；PR #1905 的 4 条**保留为需立项、不 ignore**。当前 `upstream_ignored.json` 共 **25** 条（`ignore` 命令实测新增 9 条后 total=25，即此前实存 **16** 条——早前台账所记「17 条」差 1，属既有计数误差，此处更正）。**批次 26 再 `ignore` 28 条**（已覆盖 17 + 不适用 10 + 部分采纳 1）→ 当前共 **53** 条（`ignore` 命令实测 total=53）；**批次 27 再 `ignore` 6 条**（`7e506bc3` 已覆盖、`911e996d` 不适用、`60117f17`/`7f0728bf` 已覆盖、`c2023476`+`d8677dc0` 净零）→ **59** 条；**批次 28 再 `ignore` 1 条**（`a70757b1` 不适用）→ **60** 条。**批次 30 再 `ignore` 25 条**（§3.9 中除 `fe98ffef`/`03429729f`/`89e3ad09a` 外全部）→ **85** 条（`ignore` 命令实测 `added=25, total=85`）。**批次 31 再 `ignore` 11 条**（4 组已合并 6 条 + `acbdbf1c`/`73cf2c63` 不适用 + `6141a8ca`/`d34761fe`/`175e1dc5` 已覆盖）→ **96** 条（`ignore` 命令实测 `added=11, total=96`）；§3.10 的 `6029ad08` 新版棋局链 7 条与 `cd284a89` 御灵**不 ignore**（需立项 / 延后）。**批次 32 再 `ignore` 23 条**（13 条已合并 + §3.11 判「已覆盖/不适用/已被取代」10 条）→ **119** 条（`ignore` 命令实测 `added=23, total=119`）；§3.11 的 `31484b10`/`73d4ae84`/`14cbd413`（需立项）与 `c3a88af9`/`c695e50d`/`9a6eb783`（WantedQuests 延后依赖链）**不 ignore**。**批次 33 再 `ignore` 3 条**（§3.12 的 `8b4dc669b`/`ce0e78d64` 已覆盖、`940ba61b3` 不适用）→ `ignore` 命令实测 `added=3, total=93`，即**此前实存仅 90 条**；台账所记「119 条」在本地再次丢失（与批次 10 同因：`upstream_ignored.json` 不入库）。**接手续接仍须以本文件 §3 hash 集在脚本侧过滤，不能依赖该文件**。
3. ~~**GeneralBattle `battle_wait` 链（14 条 + 依赖它的绿标 2 条 = 16 条）**：是否单独立项攻坚。~~ **已决策并收口（批次 8，`7871ed52`）**：判定**本地 mine 系战斗体系更优**，该框架**不引入**（引入即重蹈批次 0）。只做「取其精华」手工移植，已落地 2 项：`RuleClickExclude` 原子（`00888a40f`+`3dca54e1f`）、奖励详情浮窗检测 `I_END_FIX_*`（`eff487272`+`00888a40f`）。另 `4e32d985c`/`5bc3f6e29` 命名绿标经核实**本地早已覆盖**（上游自述移植自 mine）→ 已改判「已覆盖」。14 条框架链在 §3 统一改判「不适用（框架）」。**待实机验证：结算页误点奖励弹出详情浮窗后能被自动关闭、奖励正常收完。**
4. ~~**RichMan `c363395d8`（勋章商店售罄处理）**~~ **已落地（批次 7，`8b5c6fab`，手工移植）**：`medal.py` 加 `appear` 前置判断 + `count_soldout()` 核对，保留本地 `money_ocr`；`navbar.back_mall` 加 15s 超时保护。资产侧 `O_SOLD_OUT` 本地已有，未重复引入；`_enter_medal` 的 `I_SIDE_SURE_MEDAL` 本地无 → 不适用。**待实机验证：勋章商店整店/部分售罄时能正常收尾不卡死。**
5. **下一批候选**：
   - **批次 43（2026-11-12，`870dc9ec`）已落地 4 条上游提交 + 1 条本地修复提交**（4 cherry-pick + 3 自检补正 + 1 回归测试 + 1 台账）：数据源按要求**剔除 `xylolit-mu/self`**（`dev_tools/upstream_sources.json`），保留 nearaura master/dev + kongdr418/mine + lgg686/self。`fetch` 后 `advise` 298 条 → 台账过滤 132 条新候选，逐条 `show` 核实：18 条与同批本地修复提交等价（已覆盖）、约 80 条不适用（DraftDuel 全簇 / ActivityShikigami 旧结构 / MetaDemon 上供 / SixRealms / WeeklyPurchase），4 条落地。落地：① 棋局手牌满出售（`ce9903bf4`）；② 删除重名 `I_CLOSE_RED` + Chess `_burst` 红叉（`476617e0e`，补正 `6fb56aa0`）；③ 狭间暗域确认按钮统一 `I_UI_CONFIRM`（`d38f6e95a`）；④ 未知页关闭顺序 + 种树标识搜索区（`0311c1894`）。**冲突**：3 组；`476617e0e` 的 `Chess/script_task.py` 整文件 `--theirs` 引入本地不存在的 `hyakki_draft` 依赖 → 已回退整文件、仅保留 `_burst`（上游历史无对应修复提交，按本地架构自补）；`9df707fb` 同类整文件替换依赖上游新版 `ui_click_until_disappear` → 整条撤回并记 §3.20 需立项。**影响面**：① 棋局买卡/清理循环（`_buy_shop_slot`/`_free_one_hand_slot_for_purchase`）；② 棋局截图钩子（`_burst` 新增红叉兜底，全棋局流程）；③ 全仓未知页兜底关闭顺序（`DEFAULT_UNKNOWN_CLOSERS`，所有走导航的任务）；④ 狭间暗域 4 处确认点击；⑤ 种树活动关闭标识搜索区（仅 `KekkaiUtilize`）。**回归测试**：新增 `tests/test_upstream_batch43_fixes.py`（25 项全绿）；全量 `unittest discover -s tests` **379 条 372 通过**，7 条为 czr 既有 HeroTest 过期用例（模块已不导入 `Timer`），与本批无关。**未做**真机验证。**待实机验证**：① 棋局手牌满且清理无效时能出售一张阵容卡继续购买、不再卡死；② 棋局浮窗红叉能被顺带点掉；③ 未知页兜底先点确认再返回、种树活动关闭能命中；④ 狭间暗域各确认弹窗正常；⑤ 超鬼王胜利界面/门票/锁队与探索、寮宴会、悬赏按卡去重（同批本地修复提交）在真机正常。**✅ 推送状态：已推送** —— `88510c8a..30c79df0 czr -> czr`（**直连 `https://github.com:443/...` 成功**；`origin` 现为 `gh-proxy.com` 包装地址，推送返回 `No anonymous write access`，且本机 `127.0.0.1:7897` 代理未启动 —— 后续推送优先直连，勿改 git config）。
   - **批次 38（2026-11-09，`2dba211b`）超鬼王六星鬼王上供**（手工移植 `591508f6` 的上供部分，无 cherry-pick；1 回归测试，11 项）：新增 `tasks/MetaDemon/assistance.py`——`GhostOffering` 负责好友列表扫描/按名精确勾选/提交分享/按 `boss_generation` 防重复分享/等待好友击杀；`MetaDemonMode.BOSS_ASSIST` 与 `MetaDemonAssistanceConfig`（`role` / `friend_names` / `poll_interval` 2~60 秒）；`run()` 按 `mode` 分派。**影响面**：① `MetaDemon` 配置新增 `mode`（默认「鬼王战斗」，老配置无感）与 `assistance_config`；② `check_and_switch_ticket` 新增可选 `sequence` 参数，**`cur_boss_type` 改为召唤确认（看到挑战按钮）后才赋值**——正常战斗模式只是赋值时机后移，语义不变，但可避免把残留鬼王误判为刚召唤的六星；③ 上供模式全程不进入战斗，靠 `I_MD_SUMMON_BOSS` 稳定帧判断「已结束」。**未移植**：门票刷取（本地无 `tasks/MetaDemonTicket`）、票池容量预检、上游多模式列表框架。**冲突**：无。**回归测试**：新增 `tests/test_upstream_metademon_assist.py`（11 项，本机全绿）；全仓 `pytest tests` **320 passed / 9 failed**，9 项与 HEAD 基线完全一致。**未做**真机验证。**待实机验证**：① 好友列表能滚到顶并完整扫描、按名精确勾选后提交分享；② 上供后等待好友击杀、结束后自动召唤下一个六星并计数；③ 进场时若有残留非六星鬼王，不分享也不挑战，等其消失后再召唤。**✅ 推送状态：已推送** —— `97855cd9..2dba211b`（经 `127.0.0.1:7897` 代理）；本台账回写为紧随其后的又一次推送。
   - **批次 37（2026-11-09，`8334c797`）已落地 4 组中 3 组 + 1 组部分**（手工移植，无 cherry-pick；1 回归测试，17 项）：`dd96057e` 御魂自选弹窗（新增 `I_GB_CLOSE_RED` + `gb_gb_close_red.png`，`Orochi` 覆写 `_handle_result`/`_handle_missing_battle_page` 并在 `_handle_reward` 首部关弹窗）、`38a8f00d` 活动入口 8 次轮换（`find_activity_entry` 替换单次 `I_TOGGLE_BUTTON` hook；**寄养开关未引入**，本地 `utilize_harvest` 已同义反向覆盖）、`904686c1` 逢魔 boss 页 3 轮失败改 `logger.warning` + `set_next_run(success=False, finish=True, server=True)` + `TaskEnd`、`18ededee` pass/boss 门票 OCR=0 时经 `verify_zero_ticket` 先进战复核（`enter_battle(max_times=1)` fallback 返回 False）。**影响面**：① `tasks/Component/GeneralBattle` 共享资产新增 1 条（仅 Orochi 使用，其他任务无引用）；② `ActivityShikigami` 庭院活动入口导航 hook（找不到入口由「单次点击后放弃」变为「最多 8 次轮换后抛 `GamePageUnknownError`」）；③ 逢魔 `execute_boss` 的失败收尾（不再 `GameStuckError` 触发重启链）；④ 爬塔 pass/boss 门票为 0 时的判定路径（多一次实探点击，正常有票路径逐位不变）。**冲突**：无 cherry-pick，按本地架构手工移植；无需回溯上游修复提交。**回归测试**：新增 `tests/test_upstream_batch37_fixes.py`（17 项，本机全绿）；全仓 `pytest tests` **309 passed / 9 failed**，9 项与 HEAD 基线完全一致（7 项 `test_hero_test_skill_fallback.py` 的 `Timer` + 2 项 `test_switch_onmyoji.py` 环境性 `ScriptError`）。**未做**真机验证。**待实机验证**：① 御魂自选活动期间战斗结算不再被弹窗挡住、能正常收奖励并继续下一轮；② 庭院右侧活动栏目切换后能找到爬塔入口；③ 逢魔 boss 页连 3 轮打不开时本轮正常结束且下次按失败间隔调度；④ pass/boss 门票显示 0 但实际有票时能通过实探进战。**✅ 推送状态：已推送** —— 直连两次失败（21s 连接超时 + `Recv failure`），第 3 次直连成功（`7209999b..8334c797 czr -> czr`）；本台账回写为紧随其后的又一次推送。**下一批建议**：`71c9ab81` 设备层（需评估）与 `3772e03f` 逢魔新实现（需立项）；`3bc2d41d`/`73bcafcb`/`d098e5b9` 三个大合并仍未逐条核实。
   - **批次 36（2026-11-09，从头重评 self，只读不改代码）**：按用户要求以分叉点 `371b4ec9`（2026-08-14）为基线，对 self 独有 **320 条**全量重评。`git cherry` 312 行（`+289/-23`）+ 台账 hash 交叉（已记录 227）+ 本地路径/符号核对：未记录 93 条 → 11 条 patch 已等价（已覆盖）、82 条逐簇判定（Chess 早期链 34 / MartialArts 5 / OCR 实验 3 / TeamScroll 净零 8 等判不适用；驭灵/斗技/鼬乐园/秘闻/爬塔等 14 条判已覆盖）。**发现 4 组此前漏评、可安全落地的小修**：`dd96057e`（御魂自选弹窗）、`38a8f00d`（寄养开关 + 活动入口轮换）、`904686c1`（逢魔 boss 页失败改 `TaskEnd`）、`18ededee`（门票 0 进战复核接入）。详见 §3.15。**未做**代码改动、无推送代码变更，仅本台账回写。**下一批建议**：按 §3.15 短名单做批次 37（4 组，约 12~15 文件 + 回归测试），再评估 `71c9ab81` 设备层与 `3772e03f` 逢魔新实现。
   - **批次 35（2026-11-09，仅扫描、无代码改动）**：按用户要求只同步 `xylolit-mu/OnmyojiAutoScript`。四分支 tips：`mine 1ac78957`（2026-07-15，**已是 czr 祖先**，PR #193/#198 已在本地）、`self 23edaa78`（= 批次 34 已吸收）、`pr 670f194a`（旧）、`test f9d7220c`（旧）。`advise` 125 条 → 台账过滤后 15 条 + `2d396bfa`，全部为 DraftDuel / Chess / SixRealms / desktop 大簇（详见 §3.14），**无「零冲突 + 单模块 + 低定制」小修** → 本轮不产生代码改动、无需回归测试，仅回写本台账。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 一次成功（`9e8b87eb..2a92b07e czr -> czr`），随后推送本条台账补记。**下一批建议**：小批改取 `nearaura/master`+`nearaura/dev` 与 `kongdr418/mine` 的 GlobalGame 3 / annotator 1 / desktop 3；self 剩余四簇（DraftDuel / Chess / MetaDemon / desktop）须单独立项。
   - **批次 34（2026-11-09，`021be78a`）已落地 4 项**（手工移植，无 cherry-pick；1 回归测试）：**上游源迁移** —— `runhey` 账号封禁（API 404），仓库迁到 `nearaura/OnmyojiAutoScript`（master `69b7ca1a` / dev `fd767a1d`），`upstream_sources.json` 已更新；`kongdr418/mine` 本轮直连多次超时未纳入（沿用批次 33 缓存 ref）。11-04 后未记录候选 **23 条**。落地：① **悬赏 #2006** —— `df572d01c`+`181801d1c`+`a3e6e028`（`_parse_location_info` + 数量漏读时收紧 ROI `y+7,h-14` 重试）；② **探索退出状态** —— self `1fd87d347`（`fire` 不清 `need_exit` + `run_on_exp_main` 早退，仅 Exploration 两处）；③ **超鬼王门票阈值** —— self `23edaa78`（1~6 星票 0.85→0.8，assets/json 同步）；④ **登录选服 OCR** —— `5ba75f9b` 附带项（`O_SA_CHECK_SELECT_SVR` 左扩 21px）。**影响面**：① `WantedQuests.build_wq_info` 悬赏详情读取；② `Exploration` 退出链（`fire` / `quit_exp_main` / `run_on_exp_main`）；③ `MetaDemon.can_fire_list` 召唤票识别；④ 全仓登录选服「已有角色」检测。**冲突**：无 cherry-pick、均按本地架构手工移植；无需回溯上游修复（#2006 的后续修复 `a3e6e028` 已随语义吸收）。**回归测试**：新增 `tests/test_upstream_batch34_fixes.py`（10 项，本机全绿）；全仓 `pytest tests` **292 passed / 9 failed**，9 项与 HEAD 基线完全一致（7 项 `test_hero_test_skill_fallback.py` 的 `Timer` + 2 项 `test_switch_onmyoji.py` 环境性 `ScriptError`），本批未触碰 `tasks/HeroTest`/`Component/SwitchOnmyoji`。**未做**真机验证。**待实机验证**：① 悬赏信息 OCR 漏读数量时能重试并正确解析地点；② 退出探索期间回渲染主界面不再重新开战；③ 超鬼王各星召唤票在 0.8 阈值下稳定识别且不误配；④ 长服务器名下登录选服「已有角色」能命中。**下一批建议**：先清 §3.12 余量（GlobalGame 3 / annotator 1 / desktop 3 小批）；nearaura 新源已可直接 `fetch`。**✅ 推送状态：已推送** —— `git push https://github.com/ZH-CZR/OnmyojiAutoScript.git czr` 直连原生一次成功（`e7ebb2f9..e225b5a6 czr -> czr`）；`ls-remote` 复核远端 `refs/heads/czr` = `e225b5a6`；本台账回写为紧随其后的又一次推送。
   - **批次 33（2026-11-06，`c97328d3`）已落地 7 条**（7 cherry-pick + 1 回归测试，§2 批次 33 行）：本轮 `fetch` 后四源 tip = `runhey/master 2211ba5d`（#2022）、`runhey/dev 55c3b151`（#2020）、`xylolit-mu/self 96215a7a`、`kongdr418/mine e53cb30f`（均 2026-11-05）；`advise` 实跑 306 条（跨源去重），台账过滤后 **99 条**未记录候选。落地 5 组：① **花合战任务页签** —— `bf889f02d`（收奖励前先识别「任务」页签）+ `c08fe24f9`（ROI/模板收紧）；② **结界卡跨皮肤** —— `4944b3df8`（8 条收获奖励 roi_back 统一 750,90,250,230）+ `1cc1707bf`（桌面「激活」误判防护）；③ **协作邀请素材** —— `8d499033c`（接受/拒绝/勾玉/忽略 4 条 ROI + 4 张 png）；④ **重新邀请勾选框间隔** —— `4b823fdeb`（1→3）；⑤ **标注器文件夹上传** —— `cf9fe93ca`（分批 20 张 + 去重）。**影响面**：① `tasks/TalismanPass` 收奖励入口（新增 `tp_task_tab.png`，仅该任务）；② `tasks/KekkaiActivation` 的跨皮肤收卡与桌面激活判定（`a/image.json` 与 assets 同步）；③ 全仓共享 `GlobalGameAssets.I_G_ACCEPT`/`I_G_REJECT`/`I_G_JADE`/`I_G_IGNORE`（多任务复用协作邀请）；④ `GeneralInvite.invite_again` 点击节奏；⑤ 标注器上传（纯前端，不改采集链路）。**判退**：`8b4dc669b`（本地 FindJade 已在调度优先级表）、`ce0e78d64`（本地已按命中框动态点击「完成」下方区域）→ 已覆盖；`940ba61b3`（更新源白名单只认 xylolit-mu，会拒绝本 fork origin）→ 不适用；3 条已 `ignore`（total=93，详见 §4.2 计数更正）。**冲突**：7 条 cherry-pick **零冲突**，无需回溯上游修复提交。**回归测试**：新增 `tests/test_upstream_batch33_fixes.py`（9 项，本机全绿）+ 更新批次 32 `GG_NEW_UI_ASSETS` 基线（旧 ROI 已随新素材失效）；全仓 `unittest discover -s tests` **277 项仅 9 项既有失败**（7 项 HeroTest `Timer` + 2 项 rule_click/switch_onmyoji 环境性），与本批无关。**未做**真机验证。**待实机验证**：① 花合战进「任务」页签后能正常收奖励、不再停在默认页签空转；② 不同庭院皮肤下结界卡收获奖励都能识别；③ 桌面版激活按钮不再把灰色禁用态误判为可激活；④ 协作邀请四个按钮新素材命中；⑤ 重新邀请勾选框 3s 节奏不再连点；⑥ 标注器可选文件夹批量上传且不重复。**观察项**：批次 32 的 `I_G_*` 新 UI 在 1 天后再次换素材（`8d499033c`），说明上游协作邀请 UI 仍在调整，后续该组 ROI 需继续跟进。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 一次成功（`1e0597ac..c97328d3 czr -> czr`）；临时分支 `sync/upstream-20261106-222034` 已删除；本台账回写为紧随其后的又一次推送。**下一批建议**：先做 §3.12 余下的 GlobalGame 3 条 + annotator 1 条 + desktop 3 条（小批），再评估 §3.10 的 WantedQuests 延后链；DraftDuel（35 条）/Chess（4）/MetaDemon（4）/Component（6）须单独立项，不要混进小批。
   - **批次 32（2026-10-29，`19008619`）已落地 13 条**（13 cherry-pick + 1 自检补正 + 1 回归测试，§2 批次 32 行）：本轮 `fetch` 后四源 tip = `runhey/dev c6c724a4`（2026-10-28）、`runhey/master 88c3a936`、`xylolit-mu/self 73d4ae84`、`kongdr418/mine 91f7d916`；逐条 `show` 真实 diff + 本地 grep 核实并**按提交时间序手工 cherry-pick**（`upstream_sync.py::apply` 同日退化按 hash 排序的老 bug 仍在）。落地 5 组：① **蓝票按单价买多张（Buy 组件核心改造）** —— `120c881a`（多数量窗口改走 `buy_more`）+ `be5f3c97`（按单价判断、高于 85 勾玉不买，新增 `I_BUY_JADE`/`O_BUY_PRICE` 与 `_buy_with_price`/`_buy_read_price`/`_buy_cancel`）+ `47b9064b`（余额不够买满时逐张买）；② **悬赏封印 / 接受拒绝新 UI** —— `921a2b82`（WantedQuests 23 文件）+ `e68c2d26`（GlobalGame 6 条 `I_G_*`）；③ **永生之海队员开战准备** `329ecfc7`、**海汐一次买完** `2db22cc3`、**道馆每次开馆** `3f085151`、**皮肤模板缓存刷新** `506564c6`；④ **棋局阵容预设搜索区** `d1ad2c09`（+ 自检补正 `4698b48c`：上游只改 `c/image.json` 未同步 `assets.py`）、**Chess 卖卡/上御魂点击记录** `a9597e77`、**`wait_until_disappear` 超时** `094b30b9`、**标注器任务中文名** `91f7d916`。**影响面**：① `tasks/Component/Buy` 的公共购买流程（MysteryShop 神秘商店、RichMan 好友圈/海汐等所有 `buy_one_or_more` 调用点）—— 新增「按单价/按余额」两条分支，默认参数不改变原逐张购买行为；② `BaseTask.wait_until_disappear` 新增可选 `timeout`（默认 `None` 时逐位不变，全仓既有调用不受影响）；③ WantedQuests 列表/详情页几何、`trace_one` 关闭链、`execute_mission` 目标名匹配（改为子串匹配，`any(name in monster_name ...)`）；④ GlobalGame 共享接受/拒绝按钮 ROI（全仓多任务复用）；⑤ EternitySea 队长/队员两条入口；⑥ Dokan 开馆时机（去掉「只在周一」限制）；⑦ `RuleImage.refresh()` 与 `Costume` 换皮流程（缓存模板失效）；⑧ Chess 拖拽前点击记录清理；⑨ 标注器任务下拉文案（纯前端）。**冲突**：13 条 cherry-pick **零冲突**，唯一需自检补正的是 `d1ad2c09`（json/assets 漂移）→ 不需回溯上游历史找修复提交；`6360d6a9`（`3f085151` 的祖先，本地已带 `server=False`）与 `1e18c251`（本地 `found_dokan_cnt` 守卫等价）判已覆盖。**回归测试**：新增 `tests/test_upstream_batch32_fixes.py`（932 行 / 10 类 / 68 项 + 33 subTest，本机全绿）；全仓 `tests` **273 passed / 9 failed**，9 项与 `8c30ac06` 基线**逐一对应**（7 项 `test_hero_test_skill_fallback.py` patch 不存在的 `Timer` + 2 项 `test_switch_onmyoji.py` 环境性 `ScriptError`），本批未触碰 `tasks/HeroTest`/`tasks/Component/SwitchOnmyoji`（`git diff --stat` 为空）。**判退/延后/需立项**：`31484b10`/`73d4ae84`（棋局阵容编辑器）、`14cbd413`（GeneralInvite 邀请组件 + `module/cooperation.py`）→ **需立项**；`c695e50d`→`c3a88af9`→`9a6eb783`（WantedQuests 神秘妖怪/取消追踪超时链）→ **延后，建议下一批优先**；`85632077`/`1f5149f3` → **不适用**；其余 6 条判已覆盖/已被取代（详见 §3.11），其中 `ignore` 共 23 条（total=119）。**未做**真机验证。**待实机验证**：① 神秘商店蓝票：单价 >85 勾玉不买、余额够买满一次买多张、不够逐张买、连 1 张都买不起时取消退出；② 好友圈商店蓝票沿用 `money`/`remain` 分支仍能正确买满；③ 悬赏封印新 UI 的列表几何、前往/追踪按钮与目标名子串匹配（含 `unwanted_boss_name_list` 命中「神秘妖怪」）；④ 接受/拒绝（协作邀请）6 条 `I_G_*` 新 ROI 命中；⑤ 永生之海队员能进本、选层、锁队后再开战；⑥ 道馆非周一也能尝试开馆且只尝试一次；⑦ 皮肤切换后新模板立即生效（不再用旧缓存图）；⑧ 棋局卖卡/上御魂不再触发 `GameTooManyClickError`、标注器下拉显示「中文名（英文名）」。**观察项（非本批引入）**：`tasks/WantedQuests/invite/wq_friend_1..5.png` 在基线 `8c30ac06` 即缺失（这 5 条只被 `self.click()` 用 ROI，不走模板加载，故不影响运行）；本地独有 `I_WQSE_SPECIAL_FIRE`/`O_WQ_LIST_CHECK`/`I_WQ_LIST_TOP_BOTTOM_CHECK` 等未被 `image.json` 登记（同样属 `click` ROI 用法），均留作后续资产整理。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 直连两次失败（`Recv failure: Connection was reset` + 21s `Could not connect to server`；本次本机无本地代理端口可退）→ 第 3 次重试成功（`af376093..19008619 czr -> czr`）；`ls-remote` 复核远端 `refs/heads/czr` = `19008619`，本台账回写为紧随其后的又一次推送。临时分支 `sync/batch32` 已删除。
   - **批次 31（2026-10-23，`9e66d1d7`）已落地 4 组**（2 cherry-pick + 2 手工移植 + 1 回归测试，§2 批次 31 行）：本轮 `fetch` 后四源 tip = `runhey/master 88c3a936`（含 PR #1964 dev→master 合流）、`runhey/dev 4e3528a6`、`xylolit-mu/self 47a3a3bc`、`kongdr418/mine fa7a87e7`；`advise` 实跑 **369 条**（跨源去重），按台账 hash 集过滤后剩 **102 条**未记录候选。逐条语义核实后落地：① **runhey/master PR #1963 道馆馆主修习** —— `4354df46` 换馆主名模板（旧模板失配）+ `8bbf87b8` 阈值 0.8→0.7，两条**零冲突直接 cherry-pick**；② **self `51dbf564`** —— GeneralBuff 加成开关「打开黄/关闭红」被金币、经验、通用三类共用同一 ROI 导致互相覆盖 → 拆为 `I_BUFF_*`/`I_GOLD_*`/`I_EXPERIENCE_*` 三套（threshold 0.6）+ `set_switch_area(area, kind)`；同时新增寮宴会第二种入口旗帜 `I_BANQUET_FLAG_2` 并在入口/循环两处判定兼容（**手工移植，保留本地 `goto_page` 导航**）；③ **mine `1410590f`+`fa7a87e7`+self `47a3a3bc`** —— 棋局商店「买卡 - 刷新 - 再买」的合法重复点击会累计进 `device.click_record` 触发 `GameTooManyClickError` → 买卡前/成功后与刷新变更槽位后清理对应记录（**手工移植**）。**影响面**：① 道馆（Dokan）馆主修习入口识别（`I_CENTER_GUANZHU_XIUXI` 模板 + 阈值）；② `tasks/Component/GeneralBuff` 三类加成开关（金币 50/100、经验 50/100、觉醒/御魂）的 ROI 与识别阈值 —— 全仓所有调用 `open_buff`/`close_buff` 组合的任务；③ `GuildBanquet` 入口判定（两种旗帜任一命中即视为在寮宴会）；④ 棋局商店经济流程的防连点计数（仅清理「合法」点击，未变更槽位仍受阈值保护）。**判退/延后**：`6029ad08` 一带新版棋局链 7 条（frame 框架级重写）→ **需立项**、`cd284a89` 御灵 → **延后（本轮未选）**、`acbdbf1c`（本地 `O_COIN` 布局不同且已双路解析）/`73cf2c63`（本地无 `set_next_run_next_monday`）→ **不适用**、`6141a8ca`/`d34761fe`/`175e1dc5`（本地已为整数 ROI 与正确拼写）→ **已覆盖**（§3.10）。**冲突**：本批无冲突，不需回溯上游历史找修复提交。**回归测试**：新增 `tests/test_upstream_batch31_fixes.py`（17 项，本机全绿）；全仓 `tests` **9 failed / 205 passed**（失败项与基线 9 failed / 188 passed 完全一致：7 项 HeroTest `Timer` AttributeError + 2 项 SwitchOnmyoji 环境失败，与本批无关）。**未做**真机验证。**待实机验证**：① 道馆馆主修习入口在新模板/0.7 阈值下稳定命中；② 金币、经验、觉醒/御魂三类加成开关各自独立开关、互不串位；③ 寮宴会第二种入口旗帜能被识别、任务不再提前结束；④ 棋局商店连续买卡/刷新不再触发 `GameTooManyClickError`，未变更槽位仍受保护。
   - **批次 30（2026-10-21，`4a8bd2f3`）已落地 3 条**（3 cherry-pick + 1 回归测试，§2 批次 30 行）：本轮 `fetch` 后 dev tip `6e425254`（2026-10-21）、master `19cbc452`、self `dd72b786`、mine `a192e085`；`advise` 实跑 251 条（4 源）、按台账 hash 过滤后剩 **28 条未记录候选**，逐条比对后仅 **3 条**对本地有实际修复价值（模块与上游逐字一致或本地确有同缺陷），其余 25 条判已覆盖/不适用（§3.9）。**影响面**：① 标注工具（annotator）停止/断开链路 —— `module/server/tool.py` 的截图子进程收尾（terminate→1s→kill→如实报错）、`_drain_status_queue` 队列局部绑定（消除与其它线程的竞态）、远程截图方法集合决定 8s/2.5s 停止超时；② `module/server/tool_router.py` 停止请求 2s 超时后如实回错，避免 Web 端一直转圈；③ GameUi 导航 `goto_page` —— 「交替换路」时进度计时器不再每步重置（能按 `progress_timeout` 正常超时报 `GPageUnknownError`），失败计数跨边累计（第 3 次失败触发 `close_unknown_pages`），影响**所有走导航的任务**（庭院/活动/副本入口）；④ 新增 `/screen` 路由（`/screen/info`、`/screen/capture`、`/screen/capture/<name>`）为叠加式，既有 home/script/stats/log/tool/income 路由与本地 `NoCacheStaticFiles` 不变。**回归测试**：新增 `tests/test_upstream_batch30_fixes.py`（17 项，本机全绿）——导航 3 项用 `object.__new__(GameUi)` + 假 navigator/`_refresh_current_page`/`_build_path`/`_execute_transition` 驱 `goto_page`；全仓 `test_*.py` **181 项仅 7 项既有 HeroTest 失败**（批次 27/28 已记录，与本批无关）。**未做**真机验证。**待实机验证**：① 标注器点「停止」后 Web 端不卡死、能如实提示超时；② 导航在两条等价路径间来回时能按超时判未知页并兜底返回；③ 服务端 `/screen` 能取到当前模拟器画面（`log/screen/`）。**⚠ 记录（不 ignore、需后续处理）**：**本地爬塔（ActivityShikigami）模块相对当前活动已陈旧** —— 上游 `fe98ffef` 换的是另一活动的模板（竖排「磐长神木」），本地锚点还是「炼石成金」，两边不是同一 UI；如需适配当前活动需另行取图立项。**观察项**：`I_CHECK_MAIN` 阈值 0.95 暂不动（详见 §3.9 `03429729f` 行），若后续日志出现庭院识别失败再评估。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 直连被 `Connection was reset`/21s 连接超时两次，改用 `-c http.proxy=http://127.0.0.1:7897` 成功（`9af26cb4..ae64d9b9 czr -> czr`）；`ls-remote` 复核远端 `refs/heads/czr` = `ae64d9b9`（提交链 `4a8bd2f3` 合并 → `acc7e8c7` 回归测试 → `ae64d9b9` 台账回写）；临时分支 `sync/batch30` 已删除。
   - **批次 29（2026-10-20，`a095e311`）已落地 6 条（6 cherry-pick + 1 回归测试）**：**新增第四比对源 `kongdr418/mine`**（`dev_tools/upstream_sources.json` 末位＝优先级最低；实测其 `dev` 与 `mine` tip 相同（`a192e085`）→ 按用户要求**只保留 `mine`**）。本轮**专项引入「每日收益」功能**：`fetch` 后对该仓库历史提交用 `--ancestry-path` 核实，该功能＝**2026-10-16 同日的 6 条严格线性提交链**（`802643de` → `97575ca7` → `a0fe1e8d` → `f3c61ba4` → `e6b00fbe` → `83377a19`），其后**无再触碰这些文件的提交**（无额外冲突修复提交）。**影响面**：① 新增 `module/log_income.py` 由任务侧（写）与服务端（读）共用；② `tasks/DailyTrifles/script_task.py` 新增 `run_income_stat`（`income_stat` 开关**默认关闭**，不改变既有 DailyTrifles 流程）；③ `config.py` 新增 `IncomeSnapshot` 字段（pydantic 容忍旧配置）；④ `assets.py` 新增 8 条 `O_INCOME_*` 并重排（既有 `O_*` 语义不变）；⑤ `module/server/app.py` 追加 `income_app` 路由，既有 home/script/stats/log/tool 路由与**本地专有 `NoCacheStaticFiles`** 保留。**本地冲突取舍**：`script_task.py` 本地独有的勾协确认弹窗链路（`appear_then_click`/`match_ui_confirm`）与 `app.py` 的 `NoCacheStaticFiles` 全部保留，未被上游覆盖。**⚠ 工具 bug（重要，未改工具源码）**：`dev_tools/upstream_sync.py::apply` 用 `--date=short`（仅日粒度）排序（[upstream_sync.py:1142](../dev_tools/upstream_sync.py#L1142) `key=lambda c: c["date"] + c["hash"]`），**同日提交会退化按 hash 排序** → 本轮 6 条同日提交被排成 `802643de, 83377a19, 97575ca7, a0fe1e8d, e6b00fbe, f3c61ba4`（`83377a19` 提前，缺前置 `INCOME_*` 常量）→ cherry-pick 报冲突；改**手工按时间序** `git cherry-pick 802643de 97575ca7 a0fe1e8d f3c61ba4 e6b00fbe 83377a19` 后 6 条全部干净落地。**验证**：`py_compile` 6 文件通过；全仓无冲突标记（`git grep` 仅命中既有注释分隔线）；`tests/test_upstream_dailytrifles_income.py` **19/19 绿**；全量 `tests/` czr 基线 **9 failed / 148 passed** → 本分支 **9 failed / 167 passed**（9 项均为既有 HeroTest `Timer` AttributeError 与 SwitchOnmyoji 环境性失败，czr 上同样失败，与本次改动无关）。**未做**真机验证。**待实机验证**：① `income_stat` 开关打开后能正确读庭院资源/商城符咒/秘卷屋碎片并写入 `log/income/<配置名>.jsonl`；② 服务端 `/income` 查询、`/history`、按天删除（墓碑）正常；③ 跨天（机器停机数日）基准日查找与做差正确。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 一次成功（`1171a327..e548ecad czr -> czr`）；`ls-remote` 复核远端 `refs/heads/czr` = `e548ecad`（提交链 `a095e311` 合并 → `4540f271` 回归测试 → 台账回写）；临时分支 `sync/income-stat` 已删除。
   - **批次 28（2026-10-20，`137610f0`）已落地 2 条**（2 cherry-pick + 1 回归测试，§2 批次 28 行）：本轮 `fetch` 后 dev tip `b1c7186c`（2026-10-19），master 仍 `19cbc452`、self 仍 `00c083e8`；`6d718fec..dev` 新增 3 个提交。**① `b1c7186c` 邀请确认 ROI**：`I_INVITE_ENSURE` roi_front `710,544,132,60` → `517,553,132,60`、roi_back `486,532,373,84` → `473,505,409,121`，`gi/image.json` 同步；冲突取上游新值（本地旧 roiBack 被新区域完全覆盖）。**② `107e9542` 桌面 Restart**：桌面分支在 `app_is_running()` 为真时先 `app_stop()` 再 `_desktop_start_and_login()`；停在登录页（未运行）直接复用，避免多关一次打断退出导航。**判退**：`a70757b1`（Exploration 退出前误返回）**不适用**——补丁依赖 `I_BACK_YOLLOW` 旧退出循环，本地已改为 `quit_exp_main` + `page_exp_exit` 页面导航，全仓无该资产。**影响面**：① 全仓共享 `GeneralInviteAssets.I_INVITE_ENSURE` 的识别区（WantedQuests/GeneralInvite 等邀请流程），roiBack 扩大、roiFront 左移；② 桌面 `Restart.app_restart` 的关闭/复用时机（模拟器分支不变）。**回归测试**：新增 `tests/test_upstream_batch28_fixes.py`（4 项：ROI/阈值、JSON 同步、roiBack 覆盖 roiFront、WantedQuests 仍走共享确认）+ 更新 `tests/test_upstream_batch27_fixes.py` 桌面重启两分支；全仓 `test_*.py` **141 项，仅 7 项既有 HeroTest 失败**。`py_compile` + JSON 校验通过。**未做**真机验证。**待实机验证**：① 「想做的事」好友邀请确认按钮在新 ROI 下能稳定命中，且不误点其他按钮；② 桌面客户端重启时已登录先停、登录页复用的两条路径；③ 模拟器模式邀请流程不受影响。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr`（第二次重试成功，`fdea0ee6..137610f0 czr -> czr`），随后推送本台账提交。
   - **批次 27（2026-10-19，`a074e599`）已落地 13 条**（8 cherry-pick + 1 手工移植 + 1 回归测试提交，§2 批次 27 行）：本轮 `fetch` 后 dev tip `6d718fec`、master tip `19cbc452`、self 仍 `00c083e8`；`4c688865..dev` 共 25 个提交（19 个非 merge），台账/`git cherry` 过滤后全部为新候选。**① 桌面客户端 PR #1887（9 条中 8 条直合 + `7c5f380b` 服务端化）**：窗口后端/`desktop_impl.py`、Device 生命周期 `DesktopDevice`、配置组 `script.desktop`（`enable`/`game_path`/`profile_dir`/`window_pos`/`window_title`/`launch_instance`）、MPay 登录弹窗、Restart 桌面就地重试、调度器登录态守卫；**② 新 Merge PR 修复**：Delegation 勾玉确认/返回死循环（`84366fc5`，PR #1940）、WantedQuests 邀请已选判定（`9afe3d32`，PR #1939）、GeneralBattle 关 buff 后点准备（`43c84c88`）、WeeklyTrifles 上周存储弹窗（`55b7d957`，PR #1943）。**本地适配**：roi_pad 无法照搬客户端同步匹配 → `module/image/runtime.py::_normalize_rule` 按 `roi_pad` 外扩并在原图坐标回算；MPay 逻辑从旧 `tasks/Restart/login.py` 迁到 `tasks/Component/Login/service.py`，登录成功补 `desktop_mark_logged_in()`；Restart 按本地 `LoginService` 架构重写桌面分支。**影响面**：① 全仓模板匹配（`match_rule`/`match_all`/`match_all_any`）新增可选 `roi_pad`，默认 0 时逐位不变，仅桌面模式置 2；② 设备层新增桌面分支（`is_desktop`/`app_start`/`app_stop`/`screenshot`/`navigator` 掉登录守卫），模拟器路径不变；③ 登录弹窗链与 Restart 重试；④ Delegation/WantedQuests/GeneralBattle/WeeklyTrifles 各任务流程。**回归测试**：新增 `tests/test_upstream_batch27_desktop.py`（13）+ `tests/test_upstream_batch27_fixes.py`（13），本机 **26/26 全绿**；全仓 `test_*.py` **136 项，仅 7 项既有失败**（`test_hero_test_skill_fallback.py` patch 不存在的 `Timer`，与本批无关）。本机环境：Python 3.14 + 安装 `cn2an`/`cached-property`/`filelock`/`inflection`/`onepush`/`requests`/`anytree`/`psutil`/`pywin32` + 外置 `ppocronnx`/`adbutils`/`uiautomator2` stub（`_tmp_dbg/stubs`，不入库）。`py_compile` 全部改动 py 文件通过，i18n/template JSON 可解析，`Config('batch27_smoke')` 可加载。**未做**真机验证（本机无游戏客户端/模拟器）。**待实机验证**：① 桌面客户端单开/多开能启动、绑定 PID、登录并跑任务（`profile_dir` 隔离、窗口标题/位置）；② MPay 弹窗反复出现时 ≤5 次后交 Restart 重建；③ 模拟器模式回归（`roi_pad=0`）识别与点击不变；④ Delegation 勾玉确认/返回、WantedQuests 邀请、GeneralBattle 关 buff 后准备、摸鱼上周存储弹窗。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr`（直连重试一次成功，`c4570b99..a074e599 czr -> czr`），随后推送本台账提交。
   - **批次 26（2026-10-15，`de7e5616`）已落地 3 条**（手工移植 + 3 个回归测试文件/10 项）：**self 积压 triage 第二轮**。三源 tip 与批次 25 **逐字相同**（`git ls-remote` 核对：`master`=`04f3b234`、`dev`=`4c688865`、`self`=`00c083e8`）→ **runhey 两源零新增**；台账 hash 过滤后 **104** 条未逐条记录项**全部来自 `self`**（2026-08-15..10-01）。落地：① `7c850c3ca` GeneralRoom 8 条勾选框阈值 0.8→0.7（`assets.py`+`gr/image.json`）；② `3ee4e53db`（含 `3f45805b7`）RyouToppa 挑战失败判定改为「等待超时才算失败」（上限 4，新增 `TOPPA_CLICK_FAILURE_LIMIT`/`TOPPA_POPUP_WAIT_TIMEOUT`/`TOPPA_BATTLE_WAIT_TIMEOUT`，战斗判据保留本地 `I_TOPPA_RECORD` 实现）；③ `28e8f060b`（仅超时部分）WeeklyTrifles 摸鱼入口 `Timer(15)` 兜底。判退见 §3.8。**影响面**：① 建房私人/公开勾选框（`GeneralRoom.ensure_private`/`ensure_public`，被 BondlingFairyland 等复用）识别阈值放宽；② 寮突 `attack_area` 的放弃时机（不再因「发出点击」误判，真实失败上限降至 4）；③ 每周琐事摸鱼行动入口等待。**回归测试**：`tests/test_general_room_ensure_threshold.py`（4）、`tests/test_ryou_toppa_click_failure.py`（4）、`tests/test_weekly_trifles_fold_timeout.py`（2）——本机 **10/10 全绿**；全仓 `test_*.py` **110 项，仅 7 项既有失败**（`test_hero_test_skill_fallback.py` patch 了该模块不存在的 `Timer`，与本批无关）。`py_compile` + JSON 校验 + 全仓冲突标记检查通过。**未做**真机验证。**待实机验证**：① 建房勾选框在渲染偏差设备上不再「四个资产全不匹配」空转；② 寮突点击后浮窗/战斗正常出现时不产生失败计数、被击破时 ≤4 次超时后跳过不卡死；③ 摸鱼入口被折叠仍能展开进入，入口改版时 15s 后回庭院而不空转。详见 §2 批次 26 三行。<br>**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 一次成功（`33fd50a0..40a1fd38 czr -> czr`）；远端 `refs/heads/czr` = `40a1fd38`（提交链 `de7e5616` 代码+测试 → `40a1fd38` 台账回写）。
   - **批次 25（2026-10-14，`6ec09b31`）已落地 1 条**（手工移植 + 回归测试同提交）：**斗技开战前等待收敛（PR #1934）**。`fetch` 三源后按台账 §2/§3 全部反引号 hash 过滤 → 本轮真实新增仅 dev 2026-10-11~14 的提交（`self` 源 tip `00c083e8` 无新增、`master` 落后 `dev`）。**唯 1 可落地**：`bedff718`/`985ac267`/`5770f91e`（PR #1934，合并 `124acb68`）净变更为 `Duel.wait_battle` 开战前操作 `ui_click(O_BATTLE_HAND, O_BATTLE_AUTO)` 的 `interval=0.8` → `interval=6, timeout=45`。**关键依赖差异（上游↔本地映射，务必保留）**：上游 `ui_click` 自 `13cf4303`（2026-02-15）起才有 `timeout` 参数；**本地 `BaseTask.ui_click`（[base_task.py:847](../tasks/base_task.py#L847)）至今无 `timeout`**，照搬会 `TypeError`。本地等价工具 `ui_click_until_appear_or_timeout(self, click, stop=None, interval=1, timeout=10)`（[base_task.py:895](../tasks/base_task.py#L895)，主体由 `05298287` 引入，本地 6+ 处在用）覆盖同一语义 → 按用户决策「先复用本地的」采用；**未来若上游对该处大改，以 `Duel.wait_battle` 的该调用点为本地落点**（本地同步在 [script_task.py:196-204](../tasks/Duel/script_task.py#L196-L204) 加了注释标注 PR #1934 与该映射）。**影响面**：仅斗技 `wait_battle` 开战前「手动/自动」点击频率与超时上界（`O_BATTLE_HAND`/`O_BATTLE_AUTO` 为本地共享 `GeneralBattleAssets` 的 `RuleOcr`，与上游资产名不同但语义一致）。**回归测试**：新增 `tests/test_duel_setup_wait_timeout.py`（4 项）——① 钉死 `ui_click_until_appear_or_timeout` 契约（stop 出现返回 True / 超时返回 False）；② 断言 `wait_battle` 传入 `(O_BATTLE_HAND, O_BATTLE_AUTO, interval=6, timeout=45)`；③ 断言不再回退旧 `ui_click` 路径。**本机实跑（用 out-of-repo 依赖 stub 打通缺失依赖后）**：本模块 4 项全绿；全仓 `test_*.py` 共 100 项中仅 7 项既有失败（`test_hero_test_skill_fallback.py` 的 `setUp` patch 了该模块并不存在的 `Timer`，属既有问题、与本批无关）。**未做**真机验证。**待实机验证**：① 斗技开战加载期间不再对「手动/自动」连点空转、45s 内未出现自动按钮时能正常继续（不永久阻塞）；② 命中自动按钮后 `green_mark` 与后续战斗流程不变。 <br>**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 首次 `Empty reply from server`、原样重试第二次成功（`f1f555cc..4bd5920a czr -> czr`）；远端 `refs/heads/czr` = `4bd5920a`（提交链 `6ec09b31` 修复+测试 → `254a6230` 台账回写 → `4bd5920a` 行尾规范化）。
   - **批次 25 判退/评估（见 §3.7）**：PR #1905（`af6d1bcb`/`c8f93d1b`/`2bc21f59`/`69a0fc4f`，Exploration `Scene+solo` 自适应滑屏找怪）→ **需立项（已评估）**，依赖本地已废弃的 `Scene`+`solo.py` 运行架构，**不 ignore**；`2f5c306e`（invite 前 `sleep(3)`）→ **不适用**（本地邀请已批量选人重构）；`aaac78b3`（选关滑动反向 UP→DOWN）→ **已覆盖**（本地 `open_expect_level` min/max 自适应已能到 28 章）；`372ef8f3`+`54803c50`+`614b6b84`+`e56482ca`（`S_SWIPE_LEVEL_DOWN_PRO` 增删改回）→ **净零**。无冲突需回溯上游历史（唯一可落地项为 1 行手工移植）。
   - **批次 24（2026-10-13，`0b68a9bc`）已落地 1 条（本地自研，无上游来源）**：修复 `GeneralBattle.exit_battle` 在 `run_task_or_default_general_battle` 兜底对象上的 `AttributeError`（见 §1/§2 批次 24 行）。**触发**：KekkaiUtilize 蹭卡导航途中命中 `page_battle`，`handle_battle_page` 走兜底 `GeneralBattle` + 快速退出（`on_takeover=exit`）→ 判「是否回到结算/奖励页」时 `GameUi.get_current_page(self)` 访问不存在的 `_detect_current_page`（实例 2026-10-13 16:15:49 少时之约）。**上游检索**：`55f51238f`/`990c45900`（§3.6）处理的是 `task.config.general_battle_config` 缺失，**与本缺陷无关**；本机 `origin/mine` 该处调用与修复前一致，无上游修复可移植 → 本地自研最小修。**影响面**：`exit_battle` 被所有「战斗接管=退出」（`on_takeover=exit`，含快速退出 / 退四）链路复用；改法只替换「结算页判定」一处，点击顺序（`I_UI_CONFIRM` → 退出）不变。**回归测试**：`tests/test_general_battle_exit_fallback.py`（9 项；修复前 3 红精确复现）；`tests/test_realm_raid_exit_four.py` 6 项仍绿；重定基于批次 23 后两模块共 15 项本机 `unittest` 全绿。**未做**真机验证。**待实机验证**：① 兜底战斗（无 `run_general_battle` 的任务）快速退出后能正常回到结算 / 奖励页且不报错；② 常规战斗退出（确认弹窗 → 退出）行为不变。<br>**补充（`bb2dd032`）**：该路径**对所有任务通用、属突发触发**（`page_battle*` 为 global 页 + `handle_battle_page` 钩子），已补「直接驱动生产真造兜底对象」的回归用例（本模块 10 项）。<br>**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` = `1b8fde61`（`ls-remote` 核对一致）；提交链 `0b68a9bc`（修复+测试）→ `85cb50c0`（台账回写）→ `bb2dd032`（生产对象用例）→ `1b8fde61`（通用性补记）。
   - **批次 23（2026-10-13，`aa77eb3e`）已落地 4 条**（2 cherry-pick + 1 手工移植 + 1 回归测试提交，§2 批次 23 行）：**runhey master+dev 2026-10-12/13 新增**。`fetch` 得 267 条（跨源去重后）→ 台账 §2/§3 全部反引号 hash（315 个）过滤 → 剩 **116 条**，其中 **111 条为已知 `xylolit-mu/self` 积压**（已在 §3.2/§3.4 判定为大特性/框架级，不属小批次），仅 **5 条 runhey 新提交**。落地：① `92578cd0`（dev，#1926）突破券 OCR 区域修正，零冲突；② `916e6eb8`（master+dev）勾选框素材更新，零冲突（落地 blob 与上游一致）；③④ `5b556e92`（共享 UI 收尾）+ `e8df3ae0`（默认邀请间隔）→ 合并为一个手工移植提交 `7aff707d`（本地登录已迁 `Component/Login`，非 cherry-pick）。**判退 1 条**：`d6c42bee`（`log_battle_start` 装饰器，目标 `battle.py`/`battle_wait.py` 本地不存在）→ **不适用**（见 §3）。**影响面**：全仓共享确认/取消/勾选点击、登录弹窗关闭链（`service.py` 三处 + `default_pages` 钩子）、默认邀请流程、突破券数量识别；`RestartAssets.I_CANCEL_BATTLE` 若不改会 `AttributeError`。**回归测试**：新增 `tests/test_shared_ui_assets_followup.py` + `tests/test_exploration_realm_raid_ocr.py`（共 18 项，本机 `pytest` 全绿）。**未做**运行时/实机验证（本机无 `toolkit\python.exe`、系统 python 缺 `ppocronnx`/`zerorpc`，仅 `py_compile` + JSON 校验 + 全仓冲突标记检查）。**待实机验证**：① 登录各弹窗（继续战斗/视频/绑定手机）能被共享取消按钮正确关闭；② 默认邀请勾选框与确认点击间隔 3s 不再误触；③ 突破券数量 OCR 区域命中正常。**✅ 推送状态：已推送** —— `git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr` 原生 GCM 直连一次成功（`2ccd8210..bcd325ea czr -> czr`）；随后 `ls-remote` 复核因直连间歇抖动连续失败（`Connection reset` ×2 + 21s `connect timeout`，且本地代理未监听），**以 push 输出为准**，远端 `czr` = `bcd325ea`（合并 `aa77eb3e` + 移植 `7aff707d` + 测试 `1bfa8b4a` + 台账 `bcd325ea`）；临时分支 `sync/batch23` 已删除。
   - **批次 21（2026-10-12，`93d94a1f`）已落地 2 条**（2 cherry-pick + 2 回归测试提交，§2 批次 21 行）：**runhey/dev 近两日新增 + Merge PR 同步**。**① `4f0a4856`（PR #1910）绘卷捐献**：滑动改点每行「最大」按钮（各 2 次）+ 捐献轮数上限 `max_rounds=10`（内层等待同限并加超限告警），零冲突；**② `d638c11f`（PR #1923）斗技 MVP 分享页**：新增 `I_D_VICTORY_SHARE` 并接入 `is_battle_win`；上游用 `Masked template matching`（掩码剔除雾化左缘），**本地匹配框架不支持掩码**（`module/image/runtime.py::_match_rule` 未知 method 直接 `raise ValueError`）→ 落地改为**裁剪掉被掩码的雾化左缘**（模板列 `28:72`，90×120→44×120）后走普通 `Template matching`（阈值 0.8 沿用），`roi_front` 随之 `1100,580,90,120`→`1128,580,44,120`，删除未用的 `_mask.png`；冲突取舍：保留本地专有 `I_D_WIN_SHARE`/`I_WHITE_DOG`，不并入上游上下文里的 `I_D_TRY`（本地无 `duel_d_try.png`）。**判退 4 组**：`27241886`（GeneralBattle 完成兜底，依赖本地不存在的 `battle_wait.py`）、`b3d6fe98`（ActivityShikigami，改本地已删的 `fire/`；其 `I_UI_BACK_CIRCLE` 注释化不得套用）→ **不适用**；`efd39e18`（`ui_ui_confirm.png`）→ **已覆盖**（批次 20 `5d546f0b` 已并入最终版）；`e930e2e1`+`8195cc60` → **净零**；self 源 `cf6fa6a5`（图像零方差/多尺度漂移）→ **已覆盖**（批次 12 `179f6dc0`）。**影响面**：绘卷捐献流程、斗技战斗结束判定（`is_battle_win`）。**回归测试**：新增 `tests/test_memory_scrolls_contribute.py`（不再 `swipe` / 每轮 6 次「最大」/ 轮数上限 10 / 已满即返回）、`tests/test_duel_victory_share.py`（method 为本地可用的普通模板匹配 / 模板尺寸与 `roi_front` 一致 / JSON 同步 / 分享页计入 `is_battle_win` / 原胜利判定不受影响），补 `tests/test_realm_raid_exit_four.py`（退四实机延迟弹窗 + 非退四回归）。**未做**运行时验证（本机无 `toolkit\python.exe`、系统 python 缺 `zerorpc`/`ppocronnx`，仅 `py_compile`（7 文件）+ JSON 校验 + 全仓冲突标记检查）。**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` = `58ccdc1a`（合并提交 `93d94a1f` + 2 回归测试提交 `25a4cdeb`/`e39e555b` + 台账 `58ccdc1a`），`ls-remote` 核对一致；临时分支 `sync/batch21` 已删除。**注**：本轮直连 github 失败（`Empty reply`/`Connection reset`），改用本地代理 `-c http.proxy=http://127.0.0.1:7897` 配合 `github.com:443` 端口形式推送成功。**待实机验证**：① 绘卷捐献正常拉满并结算、异常时 ≤10 轮后放弃不卡死；② 斗技胜利 MVP 分享页能被识别为胜利并继续（无假阳性）。
   - **批次 20（2026-10-11，`0ed4fb18`）已落地 7 条**（7 cherry-pick + 1 回归测试提交，§2 批次 20 行）：**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` 已含批次 20 全部改动（合并提交 `0ed4fb18` + 台账 `0f0f5a17`，`ls-remote` 核对 `0f0f5a17` 一致）；本条为推送后的台账补记。**共享 UI 资产统一化** —— `ca7a4189`（GeneralInvite 默认邀请延时 0.8s）、`fda09fde`（奖励图标匹配 / 去重）、`5d546f0b`（确认 / 取消按钮现行 + 历史资产）、`cdde0e49`（退出 / 刷新弹窗改用共享确认）、`71e33265`（SwitchSoul 皮肤流程复用共享确认）、`84eda193`（GeneralInvite 邀请确认改用共享资产 #1915）、`9ce0fd2f`（导航未知页加 `I_UI_BACK_CIRCLE`）；`43c7f334`（ActivityShikigami 通关识别区）判为**不适用**（本地已重构，见 §3）。**本地专有迁移**：`QuickLoadout`（2 处）、`BondlingFairyland`/`EternitySea`/`EvoZone`/`Orochi`/`OtherWorldTwilight` 的 `I_GI_SURE` → 共享 `I_UI_CONFIRM`。**影响面**：全仓所有弹窗「确认 / 取消 / 勾选」点击（`I_UI_CONFIRM` 在 8+ 模块被引用），及皮肤切换 / 御魂切换 / 退四战斗退出链。**回归测试**：更新 `tests/test_realm_raid_exit_four.py`（`I_EXIT_ENSURE`→`I_UI_CONFIRM`）+ 新增 `tests/test_shared_ui_assets.py`（共享资产存在 / 私有资产已删 / MRO 解析 / 未知页兜底）。**未做运行时验证**（本机无 `toolkit\python.exe`、系统 python 缺 `ppocronnx`/`zerorpc`，仅 `py_compile`（26 文件）+ 全仓冲突标记检查）。**待实机验证**：① 皮肤切换 / 御魂切换确认；② 退四与非退四战斗退出确认；③ 邀请「默认邀请」勾选与确认；④ 未知页出现圆形返回按钮时能正常关闭并恢复。
   - **批次 19（2026-10-11，`7654a223`）已落地 1 条（本地自研，无上游来源）**：收紧重连守卫 OCR 判据（`O_UI_CONNECTING` → `mode="Single", keyword="正在连接"`），修复吉闻「一键祝福」弹窗（输入框「欧运连连」）被 `RuleOcr.filter` 单字兜底误判为重连 → 守卫原地等待 → `GameStuckError`（实例 2026-10-11 08:11:53 少时之约 DailyTrifles，见 §2 批次 19 行）。**上游检索**：三源 403 条无该守卫补丁（本地自研）；吉闻候选 `9be90329`（master/dev）/`296dda06`（self）判定**已覆盖**。**回归测试**：`tests/test_reconnect_guard.py` + `tests/test_realm_raid_exit_four.py` 共 8 项，部署版 python `unittest` **全绿**（修复前 3 红，精确复现缺陷）。**待实机验证**：① 吉闻弹窗不再被误判为重连、DailyTrifles 能正常收尾；② 真实「正在连接……」仍能被守卫识别（`keyword` 是否需按真实 OCR 输出微调）。**注**：既存 `tests/test_hero_test_skill_fallback.py` 已失效（patch 不存在的 `Timer`，7 errors），与本次无关，未处理。
   - **批次 18（2026-10-11，`f585d8b2`）已落地 1 条（上游机制移植，无独立补丁提交）**：RealmRaid 退四改走 `run_general_battle_back(exit_four=True)`（见 §2 批次 18 行）。**结论**：上游 dev 没有一条直接补 `fire_again` 的提交（dev 根本没有 `fire_again`）——上游是靠另一套退四机制天然规避；本轮按该机制移植。**待实机验证**：① 退四「退出 → 退出确认 → 失败确认」整链正常、不再卡死；② 非退四流程不受影响。**未做**运行时验证（本机无 `toolkit\python.exe`、系统 python 缺依赖，仅 `py_compile` + 冲突标记检查）。
   - **批次 17（2026-10-10，`9bb8a6ad`）已落地 1 条**（手工移植，非 cherry-pick，§2 批次 17 行 / §3.6）：`4e4e9079f`（逢魔重进地图改走町中 + 搜索/集结重试 2→3 轮）。本轮应「与 `runhey/dev` 合并」请求做了**单源全量比对**：dev 102 条候选 → 台账 hash 过滤后仅剩 5 条 → 1 条可落地（已合并）、2 条已覆盖（`990c45900`/`55f51238f`，本地 `run_task_or_default_general_battle` 更完善）、2 条不适用（`f871f3795`/`a27a91fe9`，workflow 文件本地不存在，已 `ignore`）。**结论：`runhey/dev` 的待同步项已清空**（除本文件 §4 的待决策 / 需立项 / 延后项）。<br>**待实机验证（批次 17）**：① boss 未找到时重进改为「町中 → 现世大地图」可正常到达；② 搜索由 2→3 轮、每轮集结点击由 2→3 次后不误卡、不显著拖长。**注**：本地无 `toolkit\python.exe` 且系统 python 缺 `cached_property` 等依赖，本轮仅做 `py_compile` + 全仓冲突标记检查，**未做 import/真机验证**，需上机确认。
   - **批次 15（2026-10-09，`7e98ce39`）已落地 1 条（本地自研，无上游来源）**：探索候补式神填充重写（§2 批次 15 行）。**触发**：`少时之约`/`一叶禅心` 连续报 `GameStuckError: Alternate number is not enough`（13:27~13:29 三轮，任务被判 3 次失败退出）。**根因**：新版 UI 里**满级式神不能作候补**（游戏明确提示「该式神经验已满」），而两账号 `choose_rarity` 都是 `N卡` → 只试 N 类 → N 全是满级 → 被拒 → 数量恒 0 → 旧逻辑只长按一次即 `raise`。**改法（用户口径：不限定稀有度，按 素材→N→R→SR→SSR→SP 优先）**：逐类尝试、连续 2 轮无进展换类、≥40 收手、全类无果只告警；顺带修掉两处坑——① 必须先点 `C_CLICK_STANDBY_TEAM`（否则列表选卡不生效）；② 共享 `switch_shikigami_class` 在「当前徽标不是『全部』」时会死等而卡死，故自实现带 15s 超时的 `switch_alternate_class`。<br>**真机验证（重要，可复用）**：用部署版 python 起图像/OCR 服务 + 项目自带 adb，把真实 `fill_shikigami` 挂到 adb 驱动的 harness 上跑。**两个关键坑**：① 图像服务使用 **RGB** 帧，传 cv2 的 BGR 会把分数拉低到阈值以下（`I_RS_SP_SELECTED` 0.67 vs **0.92**、`I_E_OPEN_SETTINGS` 0.80 vs **0.99**）→ 必须先 `cv2.cvtColor(..., COLOR_BGR2RGB)`；② 必须像生产那样先 `get_image_client().register_frame(img, name)` 并把 `frame_id` 传进 `rule.match(...)`（帧缓存默认 3s 过期，否则服务端会用旧缓存帧）。实测结果：面板预置 SP → 自动切素材 → 长按 4 卡位 → **47/50**，日志 `Alternate +10 by MATERIAL, current: 10` … `Alternate class MATERIAL finished, current: 47`。<br>**待实机验证（批次 15）**：① 无候补可上时任务不再失败（只告警继续打）；② 有非满级式神时能按优先级自动上候补并填到 40+；③ 面板停在任意稀有度（非「全部」）时都能正确切回素材。<br>**同批观察**：满级卡不可作候补 → 若某账号各类别都满级，候补会恒为 0，这是游戏限制而非脚本问题。
   - **批次 14（2026-10-09，`018a4ad4`）已落地 1 条**（手工移植最小修，§2 批次 14 行）：`c56e2c9b`（探索大地图「主线/玩法」tab）。**触发原因**：部署版 `一叶禅心` 于 **12:23:10 真实卡死** —— 日志 `E_EXPLORATION_LEVEL_NUMBER -> ['御魂','今日掉落','真·八岐大蛇','本周剩余2/22','秘闻','雨女的等位','英杰试炼']` → 7 条 `convert xxx failed` → `GameStuckError: Swiped too many times (25)` → 连续失败 3 次、进程退出、`Request human takeover`；根因是**大地图会记住上次 tab**（实测：切玩法→退出探索→从庭院重进仍落在玩法 tab），玩法 tab 右侧无章节列表 → 选关空转 25 次。<br>**验证方式（可复用）**：用部署版 python 跑仓库/部署代码，`ensure_image_server_started()` + `ensure_ocr_server_started()` 起项目自带服务，配合项目自带 adb（`toolkit\Lib\site-packages\adbutils\binaries\adb.exe`）逐帧真机核对；注意脚本必须有 `if __name__ == '__main__'` 保护，否则 Windows spawn 起不了服务。实测值：主线 tab 锚点 **0.9984** / 玩法 tab **0.6979**（阈值 0.85），章节 OCR 主线 `['第二十六章','第二十七章','第二十八章']`、玩法 `[]`；守卫调用后真实日志 `switch back to mainline tab` → click (1108,188) → 章节命中 3 条。**仓库与部署目录两侧均已同步并各自验证通过**。**✅ 推送状态：已推送** —— 代码提交 `018a4ad4` 已推上 `refs/heads/czr`（`ls-remote` 核对一致），其后为本次台账回写提交（见 `git log`）；推送方式见 §5 注（原生 GCM 直连，不带代理、不带显式 PAT）。<br>**待实机验证（批次 14）**：① 大地图停在玩法 tab 时，探索任务能自动切回主线并正常选关；② 主线 tab 下守卫不产生多余点击（`appear` 命中即返回）。<br>**同批新立项**：**本地真蛇（TrueOrochi）流程整体失效** —— 新版 UI 下 `I_ST_CREATE_ROOM`/`I_ST_FRAME`/`I_ST_FIRE`/`I_FIND_TS`/`O_TIMES` 全数不命中（详见 §3.5 `f7db71b2` 行），需连同战斗流程资产单独立项；`f7db71b2` 本身优先级下调（两账号该任务均 `enable=false`）。<br>源：`runhey/dev`（同源更早见 `xylolit-mu/self` 的 `028ca1f8`）。
   - **批次 13（2026-10-09，`9e6b3b6e`）已落地 1 条**（手工移植，非 cherry-pick，§2 批次 13 行）：`5a2d99bf`（对弈竞猜商店弹窗兜底 + 结束标志二次确认）。用户在批次 12 判退项中要求"排除不适用后评估、合适就合并"；**本轮评估结论：仅 `5a2d99bf` 合适并落地**；`c56e2c9b`/`f7db71b2`（探索 tab 导航，框架级）、`5bc76c7e`/`1f230af2`（IbukiArena/FrogChallenge 新模块，涉及 config 注册共享文件）维持**需立项**；`431e3458`（移除本地町中保底）维持**需评估**；`8753481b`（掩码匹配）维持**待决策**。**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` = `7d13defc` = 本地（移植 `9e6b3b6e` + 台账回写 `7d13defc`）。<br>源：`xylolit-mu/self`。
   - **待实机验证（批次 13）**：① 对弈竞猜意外进入商店页可自动关闭并继续；② "已下注/休息中"结束标志不再因弹窗后方残留画面单帧误判；③ 关闭奖励详情改用右侧固定中心 (1075,452) 后不再误点左侧商店气泡，下注确认可正常完成。
   - **批次 12（2026-10-09，`47f54223`）已落地 4 条**（2 cherry-pick + 2 手工移植合 1 提交，§2 批次 12 行）：`dedfb11b`（Delegation 委派点击位置）、`1c3accdf`（Navigator `accepted_pages`）、`44dd4659`（EvoZone 锁识别区）、`cf6fa6a5`（图像零方差拦截 + 多尺度浮点漂移）。**✅ 推送状态：已推送** —— 远端 `refs/heads/czr` = `dbc630d7` = 本地（合并 `47f54223` + 台账回写 `dbc630d7`）；临时分支 `sync/upstream-20261009-084842` 已删除。推送方式见 §5 注（原生 GCM 直连，不带代理、不带显式 PAT）。<br>源：`runhey/dev`（`dedfb11b`/`1c3accdf`/`44dd4659`）+ `xylolit-mu/self`（`cf6fa6a5`）。
   - **待实机验证（批次 12）**：① 委派任务"完成"卡片按新逻辑点正下方领取区可正常领取；② `goto_page(..., accepted_pages=...)` 旁页可达时不再强转目标页（调用点目前尚无，属预备 API）；③ 阴界之门锁/解锁新识别区命中正常；④ 多尺度规则恢复原尺寸档命中、退化（纯色）模板不再假阳性。
   - **批次 12 判退（见 §3.5）**：需立项 `c56e2c9b`/`f7db71b2`（探索 tab 导航）、`5bc76c7e`/`1f230af2`（IbukiArena/FrogChallenge 新模块）；需评估 `431e3458`（移除本地町中保底）；需实测 `5a2d99bf`（FrogBoss 商店兜底）；不适用 `c2390c2a`；~~待决策 `8753481b`（掩码匹配）~~ **已合并（批次 22）**；已覆盖 `a9cad51c`/`df3ff430`。
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
8. **`solana` 分支移植评估（2026-11-11，结论：不立项、不移植）**：源 `https://gitee.com/runheng/OnmyojiAutoScript` 分支 `solana`（tip `372ccc3d`，2026-11-03，分叉点 `62957654`）。
   - **规模**：相对分叉点 **762 文件 / +120437 行 / -883 行**；其中 **87 条非 merge 提交**把 Alasio 平台整体搬进 `oas/`（backend 68、ext 60、config 44、testing 11、backport 8、base 8、deploy 8）+ `script/`（misc 15、atom 12）+ `tests/oas` 215 个测试文件。
   - **性质**：**纯叠加**，不动现有业务——87 条里只有 3 条触碰 `module/tasks`：`e3edb924`（255 个文件的作者头/编码行清除，其中 229 个在 `module|tasks`）、`1d8d49d1`（同类单文件）、`34f6762a`（inflection 内联）。`oas/base`、`script/atom` 是 `module/base`、`module/atom` 的**逐字副本**，提交里明确写了「`module/` 保持不动、import 重写待办」→ 合进来是**不被任何业务引用的影子代码**。
   - **硬阻断**：① `pyproject.toml` 写死 `requires-python = ">=3.14.6"`，本地部署运行时是 **3.10**（`requirements.txt`：pydantic 2.10 / fastapi 0.104 / anyio 3.7）；② 依赖要求 `pydantic>=2.13.5`、`fastapi>=0.141.1`、`numpy>=2.5.3`、`opencv-python>=5.0.0.93`、`msgspec`、`pyjwt`、`zstandard`；③ 用到 3.12+/3.14 标准库（`itertools.batched`、`tomllib`）并删掉 backport 分支。
   - **与本地架构关系**：`oas/backend`（uvicorn + FastAPI + WS topic 注册表 + JWT + SQLite ConfigTable + Mod facade）与本地 `module/server`（自研 router + 图像/OCR RPC + `NoCacheStaticFiles`）是**两套并存的后端**；接入需替换 `module/server` 全部路由、配置读写（`module/config`）与任务注册表 → 属于平台迁移，不是同步。项目历史教训（GeneralBattle `battle_wait` 框架级重写曾致无法启动、整体回退）同样适用。
   - **可切出的局部**（若将来确有需要）：`oas/ext/algorithm`、`oas/ext/cache`、`oas/ext/file/filelock`、`oas/ext/compress`、`oas/backport`、`oas/testing/preview`、`script/misc/{timer,filter,exception,servertime,op,image}`。但均为**并行副本**，与本地 `module/base/utils` 功能重叠；`0a5c5d62` 里的 `rgb2gray`/`color_similarity` 语义变更还会影响本地已标定的识别阈值 → 单独引入的收益≈0、风险不为 0。
   - **建议**：维持 §3.16 判定（不纳入同步范围）；若用户将来要跟进该方向，走「整平台迁移」独立立项（先升 Python 3.14 + 依赖、再并行跑 `oas/backend` 与 `module/server`、最后切流），**不要按提交批次 cherry-pick**。
9. **新增第五源 `lgg686/self`（2026-11-11，用户确认）**：源 `https://gitee.com/lgg686/OnmyojiAutoScript.git` 分支 `self`，已写入 `dev_tools/upstream_sources.json` 末位（优先级最低，Gitee 直连无需代理）。
   - `fetch` 实跑通过：落 `refs/remotes/lgg686-self/self`，tip `a279ab60`（2026-11-11 14:56），窗口内待同步 **128 条**（feat 26 / fix 63 / refactor 29 / chore 1 / revert 1 / other 8；isolated 72、multi 34、shared 22）。
   - **尚未逐条评估**：本节不构成任何采纳/判退结论，首次 triage 按 §5 流程走 `advise` + 台账 hash 过滤。

---

## §5 续接步骤（开新对话时）

1. 先读本文件 §1 / §3（含 §3.1 / §3.2）/ §4，恢复已做/未做/跳过状态。
2. 拉取上游（**多源，默认五源**：`nearaura/master`、`nearaura/dev`、`xylolit-mu/self`、`kongdr418/mine`、`lgg686/self`，见 `dev_tools/upstream_sources.json`；越靠后优先级越低）：
   `python dev_tools/upstream_sync.py --base czr --since "2 months ago" fetch`
   （`runhey`、`xylolit-mu` 仓库已被删除/封禁，fetch 失败会自动回退本地缓存 ref，属正常）
   备选源：`runhey` 的 Gitee 镜像 `https://gitee.com/runheng/OnmyojiAutoScript` 可直连（内容与
   `nearaura` 同步，`dev`/`master` tip 一致）；`solana` 分支为后端重写线，未纳入同步范围；
   `lgg686` 的 Gitee `self` 已作为第五源入库（直连可用，无需代理）
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