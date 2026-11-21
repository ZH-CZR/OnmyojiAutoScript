# 上游增量同步比对（2026-11-21）

- 比对基线：本地 `czr` @ `3a0237c8`
- 数据源：`dev_tools/upstream_sources.json` 5 源，`fetch` 全部成功
- 工具口径：`--since "2 months ago"`，跨源 patch-id 去重并剔除本地已有内容后候选 **316 条**
- 本轮新增：**12 条提交**，全部来自 `lgg686/self`（含 **2 条合并提交**、1 组同 patch 重复 `9d9a6fbd`/`e7ca7b1a`）
- 结论：**可落地 2 条（P3），已按确认落进 `staging/20261121-p3` 并通过自动化 + 启动验证，待合并**；不适用 / 不做 10 条

## 1. 各源 tip 变化

| 源 | 11-20 tip | 11-21 tip | 新增 |
| --- | --- | --- | --- |
| nearaura/master | `48f34cb0` | `48f34cb0` | 0 |
| nearaura/dev | `bb6f2103` | `bb6f2103` | 0 |
| kongdr418/mine | `f4bf42bc` | `f4bf42bc` | 0 |
| lgg686/self | `0f99fd02` | `8b06fd35` | 12（含 2 合并） |
| pinkpig-Peppa/master | `aff78b2c` | `aff78b2c` | 0 |

新增的 2 条合并提交：`bb5a54a7`（合并 Android 端适配改动到 self）、`12e61d99`（合并 Android 适配批次到 self），内容即其 first-parent diff，已被下列逐条覆盖，不单独移植。

## 2. 逐条判定

| 提交 | 时间 | 摘要 | 规模 | 判定 | 理由 |
| --- | --- | --- | --- | --- | --- |
| `db601816` | 11-18 | 新增 oasaos 设备后端与原生面板兼容 | 15 文件 +889/−18 | 不做 | 本地设备后端为 adb/scrcpy/droidcast/minitouch 等桌面链路，无 APK 运行时；oasaos 帧 socket 与 Android 面板强绑定 |
| `adfa6e84` | 11-18 | Android 热更新（Git 原地更新） | 2 文件 +462/−14 | 不做 | 依赖 `module/server/hot_update.py` 与 `android_router.py`，本地均不存在；桌面更新走 `module/server/updater.py`，机制不同 |
| `7b2f2492` | 11-19 | uvicorn keep-alive 拉长到 75 秒 | 1 文件 +5/−1 | **可落地（P3）** | 本地 `server.py` 的 `uvicorn.run` 未设 `timeout_keep_alive`，默认 5 秒；属一行防御性修复 |
| `52f23c56` | 11-19 | 局域网口令可选 + Cookie 会话 | 1 文件 +71/−19 | 不做 | 目标是 Android 运行时 `module/server/auth.py`，本地无该文件、无对应鉴权链路 |
| `9d9a6fbd` / `e7ca7b1a` | 11-19 | OCR 档位改由环境变量决定（同 patch 重复） | `script.py` +3/−1 | 不做 | 本地 `script.py` 未调用 `set_ocr_model_size`，OCR 走 `ppocr-onnx` 自有链路；该变量只对 APK NPU 白名单有意义 |
| `ea13a4c6` | 11-19 | 移除未实现的 OrochiMoans 占位 | 5 文件 +1/−38 | **可落地（P3）** | 本地 `tasks/OrochiMoans` 与上游删除前完全一致（仅空 `assets.py` + 只有 `scheduler` 的 `config.py`），且未出现在配置菜单与 i18n 中 |
| `17bb2993` | 11-20 | Android 适配批次（SemiAuto / tool_process / log_stats 事件） | 8 文件 +518/−160 | 不做 | `tasks/SemiAuto` 运行时依赖 `/android/tool/start?name=`，本地 `tool_router.py` 无此路由；`log_stats` 事件列表无本地消费端；`deploy/template` 指向其 OASA 分支 |
| `f7a3f643` | 11-20 | 补齐提交历史接口并输出作者 | 2 文件 +91/−7 | 不做 | 仅服务 Android 热更新链路（`hot_update.py` + `android_router.py`），本地无对应模块 |
| `8b06fd35` | 11-21 | 修复提交历史拉不到与首次为空 | 1 文件 +30/−3 | 不做 | 同上，依附 `hot_update.py` |
| `bb5a54a7` | 11-20 | 合并 Android 端适配改动到 self | 22 文件 +1395/−57 | 合并提交 | 内容即上述 `db601816`/`adfa6e84`/`52f23c56`/`9d9a6fbd`/`ea13a4c6` 等，不重复评估 |
| `12e61d99` | 11-20 | 合并 Android 适配批次到 self | 8 文件 +518/−160 | 合并提交 | 内容即 `17bb2993` 等，不重复评估 |

## 3. 已落地候选（`staging/20261121-p3`，待合并）

### 3.1 `7b2f2492` uvicorn keep-alive 75 秒（P3）

- 上游值：`uvicorn.run(..., timeout_keep_alive=75)`；默认 5 秒空闲即断连，客户端复用旧连接会读到 `unexpected end of stream`。
- 本地值：`server.py` 未设置该参数（默认 5 秒）。
- 本地影响面：标注器状态轮询间隔为 2.5 秒（`app.js:2969`），当前不会长期空闲；但其它面板/SSE 客户端存在 5 秒边界复用风险，属低风险防御。
- 落地：`server.py` 增加 `timeout_keep_alive=75`（1 处）。
- 验证：启动本分支服务后，同一 HTTP 连接空闲 8 秒再发请求成功；同应用默认 keep-alive 对照在 8 秒后 `WinError 10053` 断连；全量 pytest 无新增失败。

### 3.2 `ea13a4c6` 移除 OrochiMoans 占位（P3）

- 本地现状（与上游删除前一致）：
  - `tasks/OrochiMoans/` 仅 `assets.py`（空类）与 `config.py`（只有 `Scheduler` 字段）；
  - 引用点：`module/config/config_model.py:45,127`、`module/config/config_manual.py:15`、`config/template.json` 的 `orochi_moans` 段；
  - 不在 `config_menu.py`、`assets/i18n/zh-CN.json` 中，界面上不会显示为可运行任务。
- 兼容性：本地用户配置 `config/oas1.json` 含 `orochi_moans` 键；`ConfigBase` 未开启 `Extra.forbid`，pydantic 默认忽略多余字段，删除后不影响配置导入。
- 落地：按上游删除 5 处（`tasks/OrochiMoans` 目录、`config_model` 字段与 import、`config_manual` 优先级串、`template.json` 段）；`config_manual` 同时去掉同样没有任务目录的 `OrochiJudgement`。保留 `module/config/i18n/zh_CN.xml` 与标注器 `app.js` 的同名映射（上游未删）。
- 验证：全量 `524 passed / 10 failed`（失败项与基线一致）+ `PageRegistry` 105 页 + 含旧键配置可加载 + 模板键与模型字段零差集。

## 4. 立项里程碑现状（2026-11-21）

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| M1 起号套件 | 未开始 | `A1` 需新账号验收；`A2` 改为并入 `Exploration`（章节区间 + 稀有度筛选未补）；`A3` 依赖 A1/A2；`A4` 不采纳 |
| M2 活动任务三件套 | 代码完成、待实机 | `tasks/LBS`(21 文件)、`tasks/IbukiArena`(18)、`tasks/FrogChallenge`(15) 均已存在；活动未开放，离线回归已过 |
| M3 现有任务补齐 | 部分完成 | `B1` 鼬金币商店已移植（`itachi_shop.py`，待实机）；`B2` 武道大会首领战在 `staging/20261120-mt-boss`，活动未开放待实机 |
| M4 协同对弈 | 未开始 | 单独立项，不混入本批 |
| M5 稳定性 + 框架评估 | 部分完成 | D3 悬赏（`78d95b2a`）与突破券 ROI（`33cc7e06`）已合入；D1/D2/D4/D5/D6 剩余项未做；E1/E3/E4 不采纳、E5 搁置、E2 待办 |

已完成（可验收口径）：突破券 OCR、封印悬赏新 UI、Chess 手牌满出售、SixRealms 月之海、突破券上限。
已完成代码但未验收：A5/A6/A7/B1/B2（均卡活动开放实机）。
未完成：M1 全部、M4 全部、D1/D2/D4/D5/D6 剩余项、E2。

## 5. 下一步

1. 两条 P3 已在 `staging/20261121-p3` 完成自动化与启动验证，等用户确认后 `git merge --no-ff` 合入 `czr` 并推送。
2. 提醒：`staging/20261120-mt-boss`（B2）仍为 `待测试`，活动开放后补实机。
3. 提醒：当前 `czr` 工作区有未提交的重连守卫修复（`tasks/base_task.py`、`tests/test_reconnect_guard.py`），需确认走 staging 还是直接提交。
