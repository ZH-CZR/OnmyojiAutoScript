# 百鬼棋局（Chess）本地可用性与上游比对（2026-11-22）

- 本地基准：`czr` @ `76757c8d`（2026-11-21）
- 比对范围：`dev_tools/upstream_sources.json` 配置的 5 个数据源 + 本地历史分支 `origin/chess`、`xylolit-mu/self`
- 工具口径：`dev_tools/upstream_sync.py fetch` 后，`list --json` 共 320 条待同步提交，再按 `tasks/Chess` 文件集与标题关键字筛出棋局相关 20 条（跨源语义去重后 14 组）
- 证据：本地导入冒烟 + 110 个棋局相关测试通过；实机未验证（未启动游戏跑任务）

## 1. 结论

1. **本地已存在百鬼棋局**：`tasks/Chess` 完整存在，已注册到配置模型、周任务菜单与 i18n，素材齐全。
2. **代码层面可正常使用**：`PageRegistry` 105 页加载成功、`tasks.Chess.script_task` 导入成功、棋局相关 110 个测试全部通过；7 套阵容、57 个手牌模板、56 个商店模板、20 个御魂模板。
3. **实机可用性尚未验证**：本次未启动游戏执行任务，且百鬼棋局为限时活动，需开放后补实机验证（adb 当前有 5 台设备在线）。
4. **上游确实有棋局相关提交**，但绝大多数内容本地已用等价补丁落地；真正缺口集中在 3 个低风险补丁、2 类架构/行为差异、2 项增强。
5. **不建议整链替换**为上游新版 frame 架构：本地自有状态机已适配本地素材与修复，整链替换会丢掉本地 10 余处修复，须单独立项。

## 2. 本地现状与验证证据

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 任务目录 | 存在 | `tasks/Chess`、`tasks/GameUi/chess_battle.py`、`tasks/GameUi/page/image_chess.json` |
| 配置注册 | 已注册 | `module/config/config_model.py:91,165`；`config_menu.py:43` 周任务含 `Chess` |
| i18n | 已注册 | `assets/i18n/zh-CN.json`：`"Chess": "百鬼棋局"`、`chess_config`、`coin_full_exit_help` |
| 导入冒烟 | 通过 | `PageRegistry.load_all_pages()` → 105 页；`from tasks.Chess.script_task import ScriptTask` 成功 |
| 单元/回归测试 | 通过 | 批次 31/32/43 共 `110 passed, 33 subtests passed` |
| 阵容 | 7 套 | 七角山、海国、大江山、狐妖、冥府、流火、荒川（默认荒川） |
| 素材 | 齐全 | `shikigami/card` 57、`shikigami/store` 56、`soul` 20 |
| 默认配置 | 正常 | `run_count=1`、`matchmaking_timeout_seconds=60`、`limit_time=00:30:00`、`rank_protection=False` |
| 实机 | 待验证 | `adb devices` 有 5 台在线；未启动游戏执行任务 |
| 未提交改动 | 与本任务无关 | `tasks/base_task.py`、`tests/test_reconnect_guard.py`（重连守卫修复） |

**可用性判断**：本地实现是自有状态机版本（`runtime/recognition|hand_operations|round_state|economy|settings|board_positions|press_and_drag`），不是上游新版 frame 架构；代码与测试层面可运行，但已知 4 处行为差异（见 §4 P1/P2），建议补实机确认。

## 3. 上游各源状态

`fetch` 本次结果：Gitee `lgg686/self` 成功；4 个 GitHub 源连接被重置，使用本地缓存（日期见下表）。

| 源 | tip | tip 日期 | 棋局相关待同步 | 说明 |
| --- | --- | --- | --- | --- |
| nearaura/master | `48f34cb0` | 2026-11-12 | 0 | 与本地同源早期版本 |
| nearaura/dev | `bb6f2103` | 2026-11-18 | 0 | 缓存 |
| kongdr418/mine | `f4bf42bc` | 2026-11-18 | 10 | 缓存；含新版棋局、OCR v6-small、11-12 商店/排名页 |
| lgg686/self（Gitee） | `43339741` | 2026-11-21 | 10 | fetch 成功；棋局代码最新提交为 11-02 |
| pinkpig-Peppa/master | `aff78b2c` | 2026-11-15 | 0 | 缓存；与 nearaura 同源 |

> 另：本地 `origin/chess`（33 条）与 `xylolit-mu/self`（75 条）历史分支含大量 7–10 月棋局提交，均早于本地 11-12 基线，绝大多数已在本地以等价提交落地，不单独列出。

## 4. 逐条判定

### P1 可落地（低风险单点补丁，建议进 staging）

| 项 | 上游提交 | 上游值 | 本地值 | 建议 |
| --- | --- | --- | --- | --- |
| 结算未知页红叉恢复 | `cd7b6045`（lgg686）/ `1019131f`（xylolit） | `chess_battle.py` 新增 `_close_unknown_chess_result_page()`，在分享推进与返回大厅两处调用；`back_red` 的 `roiBack` 扩为 `954,37,266,182`；`script_task` 返回流程先尝试红叉 | `chess_battle.py` 无该方法；`back_red` 的 `roiBack` 仍为 `972,62,51,56`；`script_task` 无调用 | 移植；可修复结算页停在未知过渡页导致的卡住 |
| 荒川之主羁绊修正 | `a12c4e42`（lgg686）/ `bbb7f1d0`（xylolit） | `ShikigamiEntry(5, 2, 'arakawa_no_nushi', ...)` 第 5 项由「分裂」改为「回响」 | `tasks/Chess/strategy/shikigami_catalog.py:106` 仍为「分裂」 | 移植（1 行）；同时上游删除预设阵容里重复的 `huixiang` 纹章，本地无该重复项，无需处理 |
| 匹配成功后加载页/提前结算恢复 | `fe7aff53`（xylolit，lgg686 历史同源） | 新增 `MATCHED_LOADING_TIMEOUT=600`；匹配到 8/8 后取消等待按钮消失、加载页单独放宽超时；加载落到结算页时返回大厅重开 | `settings.py` 无 `MATCHED_LOADING_TIMEOUT`；`_wait_until_in_chess_game` 仅按 `matchmaking_timeout=60` 计三次超时后结束任务 | 移植；需实机验证慢加载场景，避免误判「等待过多」 |

### P2 需立项 / 待实机

| 项 | 上游提交 | 差异 | 建议 |
| --- | --- | --- | --- |
| 百鬼阶段主动投掷与特殊回合 | `74425d03` `d856707a` `521e1a8d` `45b5772d`（kongdr/lgg686/xylolit） | 上游新增 `runtime/hyakki_draft.py`：按所需御魂选目标，全员锁消失后随机投掷，并识别特殊回合；本地鬼阶段只等待系统自动选择 | 单独立项新增模块，不照搬整套 frame 链路 |
| 新版 frame 架构整链 | `6029ad08` `d3e81d3a` `5001c0bc` `ab9ea08e` `b94dc89c`（kongdr/lgg686） | 上游有 `decision.py`、`state_loop.py`、`frame_cards.py`、`custom_lineups.py`、`lineup_loader.py`、`activity_watchdog.py` 等；本地为自有状态机 | 维持现状，只挑补丁；整链替换会丢失本地 10 余处修复（台账已判「需立项」） |
| 阵容集合差异 | `lgg686/self` 当前 `lineup_strategy.json` | 上游 4 套：七角山、冥火、平安京、黄泉；本地 7 套：七角山、海国、大江山、狐妖、冥府、流火、荒川。本地缺平安京/冥火/黄泉，上游缺本地 6 套 | 按当前赛季核对；如需补新羁绊，走阵容注册流程并实机 |
| 商店页识别区收窄 | `81bb25a7`（kongdr，11-12） | `check_mall.roiFront` 上游 `231,455,86,78`，本地 `231,455,131,78`；该提交的棋局排名页规则本地已有 | 待实机；属 GameUi 通用商店识别，非棋局专有 |

### P3 增强（不影响当前使用）

| 项 | 上游提交 | 内容 | 建议 |
| --- | --- | --- | --- |
| 阵容编辑 Web 工具 + JSON 配置 | `09c1802d` / `73d4ae84` | 新增 `module/server/chesslineup_router.py`、`web/chesslineup/*`、`strategy/lineup_strategy.json` + loader | 暂缓；当前用 Python 阵容配置即可 |
| OCR v6-small | `5a8f7385` | 新增 `runtime/ocr_v6.py`，依赖新版 frame runtime 与专用模型 | 不做；本地 OCR 走 ppocr-onnx 链路 |

### 不做 / 已在本地评估撤回

| 项 | 上游提交 | 理由 |
| --- | --- | --- |
| 买卡单轮点击上限 | `9df707fb` / `8d64b1e4` | 本地曾有 `7fd5caac`，随后 `3d6b59d4` 撤回整文件替换并留待立项；现为「循环点击直到原头像消失 + 紧急腾位 + 最多卖一张阵容卡」的保护策略 |
| 资产格式/点击 profile 统一 | `f130ab3f` `d43d8b56` | 大规模通用重构，与本项目 assets 生成链路不同，收益低 |

### 已覆盖（无需再处理）

| 上游内容 | 上游提交 | 本地对应 |
| --- | --- | --- |
| 手牌满且无可操作时出售阵容卡 | `ce9903bf` | `23a8b8a4` |
| 卖卡/上御魂前清理点击记录 | `8f945012` `47a3a3bc` `a9597e77` | `be3a3790` |
| 商店合法重复点击不触发防连点 | `d3284573` | `d3284573` |
| 买卡前清理槽位点击记录 | `1410590f` `fa7a87e7` | `d3284573` / `be3a3790` |
| 打开阵容预设搜索区放宽 | `d1ad2c09` `d68467e5` | `d68467e5` `4698b48c` |
| 符咒选取优化 | `77b84efe` `e88f4e2f` | `77b84efe` |
| 删除与 GeneralBuff 重名 `I_CLOSE_RED` | `476617e0` | `28aed3e1` |
| 棋局排名页规则 | `81bb25a7` 的 `check_chess_rank` 部分 | `tasks/GameUi/page/image_chess.json` 已含 |
| 按住拖动拟人化 | `fdf26b96` `ee18af9f` | `fdf26b96` + `runtime/press_and_drag.py` |
| 删除结算 Scatter 点击 | `1aacf5a5` | 本地结算走随机点击，无 scatter |

## 5. 建议执行顺序

1. **批次 A（P1，建议立即）**：结算红叉恢复 + 荒川羁绊 + 匹配加载超时，进 `staging/20261122-chess-p1`，跑全量 pytest + 导入冒烟 + 实机（活动开放后）。
2. **批次 B（P2，单独立项）**：鬼阶段主动投掷模块、阵容赛季核对（平安京/冥火/黄泉）。
3. **P3/P4 暂缓**：阵容编辑工具、OCR v6-small、买卡点击上限。
4. 提醒：`staging/20261120-mt-boss` 仍为「待测试」，武道大会开放后需补实机。

## 6. 风险与说明

- 本次 `fetch` 有 4 个 GitHub 源连接被重置，使用 11-15/11-18 缓存；Gitee 源为 11-21 最新。若需更严格结论，可在网络恢复后重跑 `fetch`。
- 上游 `lgg686/self` 与 `xylolit-mu/self` 的棋局代码最新提交均为 11-02，之后无棋局改动；本地 11-12 基线之后也没有新的上游棋局提交。
- 实机验证缺口：未启动游戏，不能宣称「实机可用」；当前结论为「代码与测试层面可用，实机待验证」。
