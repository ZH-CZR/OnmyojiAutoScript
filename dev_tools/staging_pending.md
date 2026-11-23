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
| gameui-review | `staging/20261123-gameui-review` | 2026-11-23 | 纯文档：`projects/2026-11-upstream-gap/gameui-merge-20261123/`（md + HTML，15 条冲突簇）；同步总账 §9 与 backlog D5。结论：不整体整合，仅建议移植 1 条 P1 | 不涉及代码，无 pytest | 不涉及 | 待合并（纯文档，用户已确认提交） |

---

## §3 已合并 / 已废弃

| 批次 | 分支 | 处理日期 | 结果 |
|---|---|---|---|
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
