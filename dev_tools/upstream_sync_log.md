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



---

## §4 待决策

1. ~~**掩码匹配 / 零方差拦截 / nan-inf 清洗**：是否以**服务端**方式补进 `module/image/runtime.py`（思路源自 `51582666`）。**批次 9 新增同源实现 `8753481b`（+152/-30，`module/image/runtime.py` + `module/atom/image.py`）**——与上述议题合并评估。~~ **✅ 已决策并落地（批次 22，手工移植 `8753481b`）**：三项全部按服务端化方式并入本地 —— ① `Masked template matching`：掩码取模板同目录 `xxx_mask.png`，非零参与/零忽略，`match_rule`/`match_all`/`match_all_any` 一并支持，掩码缺失或尺寸不符自动回退普通匹配；② 缓存指纹纳入掩码 `mtime:size`；③ 退化判据改为按「掩码非零区域」判定 + 匹配结果 nan/inf 清成 -1.0。<br>**进展（批次 12）**：其中**与掩码无关**的两项（`_template_is_degenerate` 零方差拦截 + 多尺度 `min_scale + index*step` 浮点漂移修复）已按无掩码方式移植进本地 `module/image/runtime.py`（源 `cf6fa6a5`，见 §2 批次 12）。<br>**同源 runhey 版 `51582666`** 改的是 `RuleImage` 里的 cv2 直调（本地该处已不参与匹配），**判不适用**（见 §3.1）。<br>**实跑证据（本机 cv2 5.0.0）**：合成用例中背景变化的场景下普通匹配 0.669（落榜）→ 掩码匹配 **1.0** 命中于 (60,70)；掩码缺失/11×11 尺寸不符时分数与普通匹配**逐位一致**（0.6693735718727112）；同色源图 + 掩码在 OpenCV 下产生**全 nan**，清洗后按不匹配处理。回归测试 `tests/test_masked_template_match.py` 20 项全绿。
2. **是否标记 ignore**：历史累计 `ignore` **90** 条（§3 + §3.1 中除「延后 / 待决策」项外的全部判定项）。**以后 §3 新增条目应随手 `ignore`**，避免每轮重现。
   - ⚠ **注意（批次 10 发现）**：`dev_tools/upstream_ignored.json`（工具 `DEFAULT_IGNORED`，**不入库**）曾**本地缺失**——此前 90 条 ignore 状态在本地已丢失。**批次 10 已重建该文件但仅含 4 条**（下述），历史 90 条仍未恢复 → `advise` 仍会把它们重新列为待同步。**接手续接时必须按本文件 §3 hash 集在脚本侧过滤**（不能依赖该文件），如需恢复可用 `ignore --hashes <§3 全部 hash,…>` 重建。
   - 批次 10 新增判定 4 条**已 `ignore`**：`19ae288c4`（已覆盖）、`8e62ae47e`（不适用）、`1ebf4f4f0` + `0c7f778c6`（净零对）。批次 17 再 `ignore` 4 条（`990c45900`/`55f51238f` 已覆盖、`f871f3795`/`a27a91fe9` 不适用）。批次 21 再 `ignore` 6 条（`27241886`/`b3d6fe98` 不适用、`efd39e18`/`cf6fa6a5` 已覆盖、`e930e2e1`+`8195cc60` 净零对）。批次 22 再 `ignore` 2 条（`8753481b` 已合并、`51582666` 不适用）。批次 23 再 `ignore` 1 条（`d6c42bee` 不适用）。批次 24 无新增 `ignore`（本地自研、无上游来源）。批次 25 再 `ignore` 9 条（`bedff718`/`985ac267`/`5770f91e` 已合并、`2f5c306e` 不适用、`aaac78b3` 已覆盖、`372ef8f3`+`54803c50`+`614b6b84`+`e56482ca` 净零对）；PR #1905 的 4 条**保留为需立项、不 ignore**。当前 `upstream_ignored.json` 共 **25** 条（`ignore` 命令实测新增 9 条后 total=25，即此前实存 **16** 条——早前台账所记「17 条」差 1，属既有计数误差，此处更正）。**批次 26 再 `ignore` 28 条**（已覆盖 17 + 不适用 10 + 部分采纳 1）→ 当前共 **53** 条（`ignore` 命令实测 total=53）；**批次 27 再 `ignore` 6 条**（`7e506bc3` 已覆盖、`911e996d` 不适用、`60117f17`/`7f0728bf` 已覆盖、`c2023476`+`d8677dc0` 净零）→ **59** 条；**批次 28 再 `ignore` 1 条**（`a70757b1` 不适用）→ **60** 条。**批次 30 再 `ignore` 25 条**（§3.9 中除 `fe98ffef`/`03429729f`/`89e3ad09a` 外全部）→ **85** 条（`ignore` 命令实测 `added=25, total=85`）。
3. ~~**GeneralBattle `battle_wait` 链（14 条 + 依赖它的绿标 2 条 = 16 条）**：是否单独立项攻坚。~~ **已决策并收口（批次 8，`7871ed52`）**：判定**本地 mine 系战斗体系更优**，该框架**不引入**（引入即重蹈批次 0）。只做「取其精华」手工移植，已落地 2 项：`RuleClickExclude` 原子（`00888a40f`+`3dca54e1f`）、奖励详情浮窗检测 `I_END_FIX_*`（`eff487272`+`00888a40f`）。另 `4e32d985c`/`5bc3f6e29` 命名绿标经核实**本地早已覆盖**（上游自述移植自 mine）→ 已改判「已覆盖」。14 条框架链在 §3 统一改判「不适用（框架）」。**待实机验证：结算页误点奖励弹出详情浮窗后能被自动关闭、奖励正常收完。**
4. ~~**RichMan `c363395d8`（勋章商店售罄处理）**~~ **已落地（批次 7，`8b5c6fab`，手工移植）**：`medal.py` 加 `appear` 前置判断 + `count_soldout()` 核对，保留本地 `money_ocr`；`navbar.back_mall` 加 15s 超时保护。资产侧 `O_SOLD_OUT` 本地已有，未重复引入；`_enter_medal` 的 `I_SIDE_SURE_MEDAL` 本地无 → 不适用。**待实机验证：勋章商店整店/部分售罄时能正常收尾不卡死。**
5. **下一批候选**：
   - **批次 30（2026-10-21，`4a8bd2f3`）已落地 3 条**（3 cherry-pick + 1 回归测试，§2 批次 30 行）：本轮 `fetch` 后 dev tip `6e425254`（2026-10-21）、master `19cbc452`、self `dd72b786`、mine `a192e085`；`advise` 实跑 251 条（4 源）、按台账 hash 过滤后剩 **28 条未记录候选**，逐条比对后仅 **3 条**对本地有实际修复价值（模块与上游逐字一致或本地确有同缺陷），其余 25 条判已覆盖/不适用（§3.9）。**影响面**：① 标注工具（annotator）停止/断开链路 —— `module/server/tool.py` 的截图子进程收尾（terminate→1s→kill→如实报错）、`_drain_status_queue` 队列局部绑定（消除与其它线程的竞态）、远程截图方法集合决定 8s/2.5s 停止超时；② `module/server/tool_router.py` 停止请求 2s 超时后如实回错，避免 Web 端一直转圈；③ GameUi 导航 `goto_page` —— 「交替换路」时进度计时器不再每步重置（能按 `progress_timeout` 正常超时报 `GPageUnknownError`），失败计数跨边累计（第 3 次失败触发 `close_unknown_pages`），影响**所有走导航的任务**（庭院/活动/副本入口）；④ 新增 `/screen` 路由（`/screen/info`、`/screen/capture`、`/screen/capture/<name>`）为叠加式，既有 home/script/stats/log/tool/income 路由与本地 `NoCacheStaticFiles` 不变。**回归测试**：新增 `tests/test_upstream_batch30_fixes.py`（17 项，本机全绿）——导航 3 项用 `object.__new__(GameUi)` + 假 navigator/`_refresh_current_page`/`_build_path`/`_execute_transition` 驱 `goto_page`；全仓 `test_*.py` **181 项仅 7 项既有 HeroTest 失败**（批次 27/28 已记录，与本批无关）。**未做**真机验证。**待实机验证**：① 标注器点「停止」后 Web 端不卡死、能如实提示超时；② 导航在两条等价路径间来回时能按超时判未知页并兜底返回；③ 服务端 `/screen` 能取到当前模拟器画面（`log/screen/`）。**⚠ 记录（不 ignore、需后续处理）**：**本地爬塔（ActivityShikigami）模块相对当前活动已陈旧** —— 上游 `fe98ffef` 换的是另一活动的模板（竖排「磐长神木」），本地锚点还是「炼石成金」，两边不是同一 UI；如需适配当前活动需另行取图立项。**观察项**：`I_CHECK_MAIN` 阈值 0.95 暂不动（详见 §3.9 `03429729f` 行），若后续日志出现庭院识别失败再评估。
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

---

## §5 续接步骤（开新对话时）

1. 先读本文件 §1 / §3（含 §3.1 / §3.2）/ §4，恢复已做/未做/跳过状态。
2. 拉取上游（**多源，默认四源**：`runhey/dev`、`runhey/master`、`xylolit-mu/self`、`kongdr418/mine`，见 `dev_tools/upstream_sources.json`；越靠后优先级越低）：
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