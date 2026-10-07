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
| `78083db2e` | OtherWorldTwilight | 新增御魂副本任务彼世逢魔 | 已覆盖 | 本地已含 |
| `1c0a01f23` | OtherWorldTwilight | 修复绿标默认值绕过与队长建房失败死循环 | 已覆盖 | 本地已含 |
| `4e32d985c` | GeneralBattle | 支持按式神名点击绿标 | 延后 | 依赖 czr 已回退的 GeneralBattle 新框架（`battle_wait.py` / `battle.py`） |
| `5bc3f6e29` | GeneralBattle | Support named green marks in battle wait | 延后 | 同上 |

---

## §4 待决策

1. **掩码匹配 / 零方差拦截 / nan-inf 清洗**：是否以**服务端**方式补进 `module/image/runtime.py`（思路源自 `51582666`）。
2. **是否标记 ignore**：已于 2026-10-07 标记 §3 中 16 条（已覆盖 / 不适用 / 跳过）。**以后 §3 新增条目应随手 `ignore`**，避免每轮重现。
3. **GeneralBattle `battle_wait` 链（13 条）**：是否单独立项攻坚。本地曾因该框架整体回退（`fc1fc355` → `a85dabdc`），重做需逐条重建并重新验证启动。
4. **RichMan `c363395d8`（勋章商店售罄处理）**：本地 `medal.py` 无该逻辑（结构相近但 `money_ocr` 取值不同），需按本地结构手工移植「`appear` 前置判断 + `count_soldout()` 核对」；其 `navbar.py` 部分不适用（本地无 `I_SIDE_SURE_MEDAL`）。
5. **下一批候选**：base_task 竖屏防护 2 条 / DemonEncounter 逢魔 5 条 / FrogBoss 对弈竞猜 3 条。
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