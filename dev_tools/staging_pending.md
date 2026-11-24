# 预演批次台账（staging pending log）

> 用途：所有改动先在 `staging/YYYYMMDD-主题` 分支上攒成一个完整批次，自动化测试 + 实机验证通过、经确认后，才合并回 `czr`。
> 维护方式：建批次 → 在 §2 追加一行；状态变化就地更新；合并或废弃后移到 §3。
>
> ⚠ **开工自检**：每次新任务开始前先读本文件 §2。若存在 `进行中` / `待测试` / `待合并` 的批次，先提示用户「有未完成批次」，再决定继续、合并还是废弃。

---

## §1 约定

| 环节 | 规则 |
|---|---|
| 分支命名 | `staging/YYYYMMDD-主题`，从 `czr` 最新提交拉出 |
| 批次命名 | 主题由 AI 按改动内容自动生成英文短横线形式（如 `staging/20261120-metademon-fatigue`）；改动跨多模块或无法归类时用 `misc`，并在台账「改动范围」里写清具体内容 |
| 提交范围 | 批次内所有改动只提交到 staging 分支，`czr` 保持干净 |
| 自动化测试 | `$env:PYTHONIOENCODING="utf-8"; python -m pytest tests/ -q`（无 `toolkit\python.exe` 时用系统 Python）+ 导入冒烟 `python -c "from tasks.GameUi.registry import PageRegistry; PageRegistry.load_all_pages(); print(len(PageRegistry.all()))"`（当前基线 105 个页面），防 `AttributeError` 类启动失败 |
| 实机验证 | 用 adb 在线设备启动相关任务模块跑通，抓截图与日志判定；产生截图放 `.screenshots/`，不入库 |
| 通过标准 | 自动化全绿 + 实机通过 + 用户确认，三者缺一不可 |
| 合并方式 | `git merge --no-ff staging/...` 合入 `czr`，随后按标准推送命令推送并更新本台账 |
| 废弃方式 | 不合并不删代码，分支保留并在 §3 标记 `已废弃`，注明原因 |

状态取值：`进行中` → `待测试` → `待合并` → `已合并` / `已废弃` / `暂缓合并`（分支已备好，暂不入 `czr`，需要时直接合并）

---

## §2 进行中的批次

| 批次 | 分支 | 建立日期 | 改动范围 | 自动化测试 | 实机验证 | 状态 |
|---|---|---|---|---|---|---|
| p0-1-mt-boss | `staging/20261120-mt-boss` | 2026-11-20 | `tasks/MartialTournament/config.py`（新增 `boss_limit`）、`tasks/MartialTournament/script_task.py`（`current_limit` / `current_climb_page`）、`assets/i18n/zh-CN.json`（sequence 帮助文本）、`tests/test_martial_tournament_boss_stage.py`（新增） | 新增 5 passed；全量 520 passed / 10 failed（均为既有失败） | 未完成：武道大会未开放（活动总览当前为「祸至无日」），开放后补测 | 待测试 |
| ocr-paddle | `staging/20261123-ocr-paddle` | 2026-11-23 | `module/ocr`（`ppocr.py` 换 PaddleOCR PP-OCRv6-medium、新增 `common.py`、`rpc.py` 加 warmup/模型规格/OCR 日志/内置模型缓存）、`base_ocr.py` 空 ROI 守卫、`GlobalGame` 新增 `ocr.save_ocr_log`、`script.py` 接线、`requirements*.txt` 依赖替换（12 文件，+540/-85，commit `5d60b803`） | 全量 542 passed / 10 failed（与 czr 基线一致）；`py_compile` + 导入冒烟通过 | 未做；A/B 见 `projects/2026-11-upstream-gap/ocr-engine-ab/`（精度上游优、速度/体积本地优） | 暂缓合并 |

---

## §3 已合并 / 已废弃

| 批次 | 分支 | 处理日期 | 结果 |
|---|---|---|---|
| loadout-partial | `staging/20261124-loadout-partial` | 2026-11-24 | 已合并，merge commit `90c43ce20`（代码 `f853ce69`、台账 `a1eb91ab0`；32 文件，+218/-48）。Shu_Li_x `c95d4e7e`（统一队伍预设与御魂切换，115 文件 / +1844−929）的 A+B 档局部移植：`GeneralBattle._apply_prepare_preset` 钩子、`GeneralInvite._invite_again_popup`（续邀标题命中即续邀，标题失配用 `I_GB_CHECK_TEAM_EXIT` 兜底排除退队确认）、六副本锁定/解锁模板统一为通用图标（ROI `689,643,52,52`、阈值 0.8）。C 档（`QuickLoadout` `dungeon`/`activity` + 13 任务接入 + 废弃 `switch_soul_config`）见 backlog `E6`。新增 `tests/test_loadout_partial_sync.py` 11 项；staging 与 czr 合并后均为 `601 passed / 10 failed`（既有失败不变）。16416 实机（1280x720）六副本全绿，最佳匹配点均在 ROI 内：八岐大蛇锁 0.9638、业原火（Sougenbi）解锁 0.9878、卑弥呼（FallenSun）锁 0.9776、永生之海锁 0.9774、御灵之境（GoryouRealm）解锁 0.9871、觉醒之塔（EvoZone）锁 0.9761；锁/解锁互不误判（反向最高 0.41）。续邀弹窗未测（需两名玩家组队打完一场），2026-11-24 经用户确认免测 |
| chess-exit-dialog-guard | `staging/20261124-chess-exit-dialog-guard` | 2026-11-24 | 已合并，merge commit `b4fc311a6`（修复提交 `7fe93acb6`）。针对 2026-11-24 08:56 `一叶禅心(笔记本)` 的 `GameTooManyClickError: Too many click for a button: grigri_option_3`：误触返回键弹出的「是否确定离开游戏？」覆盖在符咒选择/商店界面上，标题「选择一个符咒」仍在弹窗上方可见，`I_SELECT_GRIGRI` 持续命中，点击全被模态框吞掉；商店同样反复 `failed to close before timeout`。修复：`chess_battle.py` 新增 `dismiss_chess_exit_dialog()`（退出流程内点「确定」，其余场景点「取消」），`exit_chess_battle` 拆出 `_run_exit_chess_battle` 并以 `_chess_exit_flow_active` 区分上下文；`select_grigri` 与 `_ensure_shop_closed` 每轮先过守卫；新增 `tests/test_chess_exit_dialog_guard.py` 6 项（含 AST 断言防止守卫被后续合并删除）。全量 `590 passed / 10 failed`（均为既有失败）、页面注册 105。**用户选择先合并再验证**（部署目录启动 `reset --hard origin/czr`，机制上唯一生效路径），待启动器拉取 `b4fc311a6` 后实机复核 |
| chess-exit-confirm | `staging/20261124-chess-exit-confirm` | 2026-11-24 | 已合并，merge commit `a884711bd`（修复提交 `bca447ed8`，已 rebase 到 `3dcd34716`）。针对实例 2026-11-24 00:27 `少时之约(笔记本)` 与 08:45 `一叶禅心(笔记本)` 的 `GameTooManyClickError: PAGE_CHESS_EXIT`：退出确认弹窗已显示，但 `I_CHESS_EXIT_CONFIRM` 旧素材相对当前渲染偏移 5~7px，固化 ROI 内仅 0.155，且两规则 `roi_back == roi_front`（模拟器 `ROI_MATCH_PAD=0` 零容差），导致弹窗识别始终失败、19s 内连点退出键 10 次。修复：换用上游 oYe486 `725baa1a0` 新素材（blob `aeab60f`，离线复核 0.9995）、confirm/cancel 的 `roi_back` 各扩 16px、同步 `image_chess.json`、新增 `tests/test_chess_exit_confirm_asset.py` 3 项。rebase 后全量 `584 passed / 10 failed`（均为既有失败）。**用户选择先合并再实机验证**：部署目录 `deploy/git.py` 启动执行 `git reset --hard origin/czr`（`config/deploy.yaml`：AutoUpdate=true、KeepLocalChanges=false），本地同步的修复文件会被清空，08:45 复现实为旧代码；待启动器自动拉取 czr 后复核棋局退出流程 |
| logging-runs | `staging/20261123-logging` | 2026-11-23 | 已合并，merge commit `68ea4c31`（15 文件，+4263/-16）。新增 `module/log/`（run 上下文 / JSONL 存储 / 错误码 / 诊断包）、`module/logger.py`（RunLogHandler + 文本 7 天、错误 3 天、run 3 天、索引 7 天分级清理）、`script.py`（run 生命周期与 attempt/parent_run_id 重试链、异常记录、save_error_log 追加 diagnosis.json）、`module/server/log_run_router.py` 6 个接口（runs 列表/详情、stats24h、diagnosis、error/files、error/file，统一 `{code,error,data}` + no-cache）并在 `app.py` 注册、`docs/logging-api.md`（OASX 接口说明）、`docs/开发文档.md` §10.1/§10.5、`docs/使用手册.md` §14、`.gitignore` 放行 `module/log/`。新增 `tests/test_log_runs.py` 10 passed；合并前后全量 583 passed / 8 failed（既有失败：HeroTest 7 条 Timer 导入缺失、收入测试 1 条硬编码日期超窗）；`py_compile` 与 OpenAPI 冒烟（99 paths）通过；czr 上复跑日志测试 10 passed。实机未做（用户选择以自动化验证代替） |
| duel-gain-popup | `staging/20261123-duel-gain-popup` | 2026-11-23 | 已合并，merge commit `23f43056e`（其后又合并远端 `e074e515e`，当前 `czr` 同时包含两批斗技弹窗修复）。针对「可兑换增益道具 / 开心收下」弹窗：模态遮挡返回键但 `I_CHECK_DUEL` 仍命中，导航 penalty 递增至 7 后 `GameTooManyClickError`。上游 `7114d0cf3` 模板与本弹窗实测仅 0.47；远端 duel-white-dog 的 `I_WHITE_DOG` 对本截图实测仅 0.30，均未覆盖该变体。新增 `O_D_GAIN_POPUP_CLOSE`（Full 子串「开心收下」，ROI `735,490,220,60`）、`dismiss_duel_gain_popup()` 并在 `run` / `prepare_duel` / `switch_all_soul` 调用、`page_duel` 进入成功与离开失败 hook；`tests/test_duel_gain_popup.py` 7 项。斗技相关 17 passed；合并远端后全量 `571 passed / 10 failed`（既有失败不变）、页面注册 105。16416 实机（1280x720）：OCR 命中 `(776,505,117,32)`，点击 `(868,523)` 后弹窗关闭、斗技主界面恢复，随后返回键成功进入町中，未再触发 `GameTooManyClickError` |
| duel-white-dog | `staging/20261123-duel-white-dog-popup` | 2026-11-23 | 已合并，merge commit `9bd263a9`。`tasks/GameUi/default_pages.py` 新增 `close_duel_buff_popup` 并挂到 `page_duel` 进入成功 / 离开失败 hook（条件 `DuelAssets.I_WHITE_DOG`）：斗技「寻龙逐奕」增益道具弹窗吞掉返回键，导致 `page_duel->page_town` penalty 递增到 7 后 `GameTooManyClickError`（实例 2026-11-23 19:26 一叶禅心）。新增 `tests/test_duel_white_dog_popup.py` 6 项；全量 `567 passed / 8 failed`（stash 对照一致，均为既有失败）、页面注册 105。**用户确认环境不在本机，先合并推送后自行实机验证**（弹窗出现时斗技页能否正常回庭院待补验） |
| observability | `staging/20261123-observability` | 2026-11-23 | 已合并，merge commit `7d81c327c`。P1+P2：`/tool/doctor` 主动体检、进程级看门狗（意外退出两轮确认 + 心跳中断）、轻量指标（任务/战斗/RPC 延迟/RSS/CPU）与 `/stats/{script}/metrics`；指标经 multiprocessing 队列上报、仅内存不落盘。新增测试 17 passed，全量 `559 passed / 10 failed`（既有失败不变），页面注册 105。实机：`run_doctor()` 11/11 pass；真实子进程端到端 0.9s 收到快照，心跳新鲜静默、过期正确告警 |
| gameui-review | `staging/20261123-gameui-review` | 2026-11-23 | 已合并，merge commit `3f97021e7`。纯文档：GameUi 专项评估（7 源 15 条冲突簇），结论不整体整合；P1 1 条（`script.py` 强制 Restart）、P2 1 条（棋局退出确认 alt）、P3 2 条（商店第 4 候选、町中保底）待后续按点处理，其余 11 条不采纳/已覆盖。不涉及 pytest 与实机 |
| p0-2-realm-raid-roi | `staging/20261120-realm-raid-roi` | 2026-11-20 | 已合并，merge commit `33cc7e06`。突破券 ROI 收窄至 `928,16,69,25`（未照搬上游 `923,16,74,25`，本机该区域仍读成 18/30） |
| p0-3-wq-mystery | `staging/20261120-wq-mystery` | 2026-11-20 | 已合并，merge commit `78d95b2a`。13 条上游修复去重后只补 3 条缺失语义（详情页前往判断、神秘悬赏跳过、仅剩不支持任务退出）；其余等价实现已在 czr，`d296406e` 等资产重构与本地 `I_TRACE_TRUE` 流程冲突故未引入 |
| 合并后校验 | `czr` | 2026-11-20 | 全量 `523 passed / 10 failed`（均为既有失败），页面注册 105 |
| p3-keepalive-cleanup | `staging/20261121-p3` | 2026-11-21 | 已合并，merge commit `997dab48`。`server.py` keep-alive 75s（8s 空闲同连接复用成功，默认 5s 对照断连）；删除 `tasks/OrochiMoans` 占位（旧配置兼容、模板零差集）。合并后全量 `524 passed / 10 failed`（均为既有失败），页面注册 105 |
| workflow-autosync | `staging/20261122-workflow-autosync` | 2026-11-22 | 已合并，merge commit `c9b0322e`。新增 `dev_tools/session_start.py`（开工简报 + 自动 merge czr，冲突自动 abort，脏工作区只报告）与 `.trae/rules/project_rules.md`（IDE 自动加载的开工卡）；README §10 与 SKILL 补开工条目。无运行代码改动，不涉及 pytest 与实机 |
| p0-frog-finish | `staging/20261122-p0-frog` | 2026-11-23 | 已合并，merge commit `afba9fa4`。`tasks/FrogBoss/script_task.py` 的 `confirmed_finish_marker` 排除商城/日志/30 勾玉/左右投注入口，`run` 与 `confirm_bet` 统一 0.2s 二次确认（源 lgg686 `f67e5a80`）；P0 其余 10 条复核后无需改码。合并后全量 `523 passed / 10 failed`（既有失败不变）、任务内策略测试 15 OK、页面注册 105。用户确认接受无实机风险先合入，**对弈竞猜实机待活动开放后补验** |
| staging-skill | `staging/20261122-staging-skill` | 2026-11-22 | 已合并，merge commit `487ce896`。新增 `.trae/skills/staging-workflow/SKILL.md`（开工与批次闸门技能，触发词「开工/继续/新批次/收尾/同步 czr」，随仓库分发）；`.trae/rules/project_rules.md` 补触发词说明。无运行代码改动 |
| p1-sync-95 | `staging/20261123-p1-sync` | 2026-11-23 | 已合并，merge commit `79fa6925`。P1 95 条逐条取舍（已覆盖 41 / 不适用 30 / 需实机 8 / 可落地 15 / 已落地 1），移植 9 条：`17474206`（Login 10s）、`ba0d49b7`（契灵补邀 8s）、`31a853a9`（协作忽略退化）、`fcd496de`（青蛙零权重回退）、`6084f210`（爬塔弹窗重试）、`1c646ce5`（GB ROI）、`dd51be24`+`f0c8473d`（悬赏 2x 重扫）、`3ad3ff86`（MetaDemon 遗留奖励页）。6 条待补（`69a0fc4f`/`f3f62f43`/`252c6701`/`9eea7c9d`+`bf893c0d`/`d7d98690`）。16416 实机：页面识别/庭院↔探索导航通过，悬赏 `_scan_wq_text` 1x/2x/2x+0.5 与 `find_wq` 在追踪列表实测通过；活动/战斗类项待活动开放补验。合并后全量 `528 passed / 10 failed`（既有失败不变）、页面注册 105 |
| feature-gap-refresh | `staging/20261123-feature-gap-refresh` | 2026-11-23 | 已合并，merge commit `0e87a5e3`。纯文档：差距报告刷新至 11-23 基准（czr `e9703b9a`、64 任务、候选 324 条），并补登记此前漏记的 chess-sync 批次。不涉及 pytest 与实机 |
| itachi-shop | `staging/20261123-itachi-shop` | 2026-11-23 | 已合并，merge commit `200c0afd`。上游 lgg686 `05fca68a` 逐项比对一致（逻辑/ROI/关键词/PNG 哈希）；本地修复实机暴露的两点：礼盒名称容忍 OCR「鼬→融/丢字」，余额读数不可信（current>total）时跳过校验。`tests/test_richman_itachi_coin_shop.py` 14 passed；全量 `542 passed / 10 failed`（既有失败不变）、页面注册 105。16416 两次运行买齐大/中/小三个礼盒 |
| chess-sync | `staging/20261122-chess-sync` | 2026-11-23 | 已合并，merge commit `43a56be5`（冲突仅台账，已按合并处理；`base_task.py` 自动合并）。Chess 阵容工坊与运行时、百鬼主动投掷、冥火/平安京阵容、结算未知页恢复、重连横幅修复。合并后全量 `537 passed / 10 failed`（既有失败名单不变）、页面注册 105。用户确认直接合入；**百鬼投掷/新增阵容/工坊实机待补验** |
