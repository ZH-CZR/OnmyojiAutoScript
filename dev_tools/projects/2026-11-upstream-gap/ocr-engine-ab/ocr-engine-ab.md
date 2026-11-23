# OCR 引擎 A/B 对比（本地 ppocr-onnx vs 上游 lgg686 PaddleOCR）

配套：[backlog E4](../backlog.md) · [全量对比](../upstream-full-compare-20261122/upstream-full-compare-20261122.md) · [呈现页](ocr-engine-ab.html)

- 日期：2026-11-23 · 设备：16416（少时之约）· 用例：40 条真实截图裁片
- 分支：`staging/20261123-ocr-paddle`（commit `5d60b803`）
- 状态：**暂缓合并**（分支保留，需要时直接合并；`czr` 未改动）

> 本文件为权威数据源；`ocr-engine-ab.html` 是同一结论的呈现层，两者数据一致。

## 1. 结论

| 维度 | 本地 `ppocr-onnx 0.0.3.9` | 上游 `paddleocr 3.7.0` | 优势方 |
| --- | --- | --- | --- |
| 全对率（40 例） | 32/40 = **80.0%** | 38/40 = **95.0%** | 上游 |
| 平均 CER（逐例归一化后取均值） | **7.52%** | **3.33%** | 上游 |
| 单行中位耗时 | **3.2 ms** | 118.5 ms | 本地（约 37×） |
| 单行最慢 | **176.8 ms**（2 次调用回落） | 1243.4 ms | 本地 |
| 模型体积 | **10.9 MB**（det v3 2.32 + rec v2 7.97 + cls 0.56） | 132.9 MB（v6-medium det 59.5 + rec 73.4） | 本地（约 12×） |
| 初始化 | **0.31 s** | 3.08 s（热启动；首次含下载约 72 s） | 本地 |
| 常驻内存 RSS | **105 MB** | 327 MB | 本地 |

**判定**：

1. **精度**上游明显更好，且优势集中在「点名类」字段（形近字：兵俑/碎片/图鉴 全对）；
2. **开销**本地全面更好，单行延迟差约 37 倍、模型体积差约 12 倍、内存差约 3 倍；
3. 本仓每条任务循环里 OCR 调用频繁（导航、悬赏扫描、战斗状态），37 倍延迟会直接拖慢任务节奏，而本地 8 个错例里 6 个是形近字/多字，已有模板或关键字兜底；
4. 因此按「性价比」当前不值得合并 → 代码留在单独分支，**暂缓合并**；将来若出现大范围精度问题（新 UI、低分辨率、更多点名类字段）再直接合并该分支。

## 2. 方法

- **用例**：同一批 40 条裁片，全部来自 16416 实机截图：
  - `p1_16416_wq_traced.png`（封印悬赏追踪页）21 条：标题、货币、卡片标题、任务描述、进度、奖励、刷新倒计时、按钮、竖排标签、邀请；
  - `chess_16416_now.png`（庭院）19 条：时间、金币/勾玉/体力、昵称、聊天、竖排入口、底部菜单。
- **链路**：两套引擎走**相同**的 `Single` 语义——先单行识别，失败再检测+识别回落；上游额外启用其自带的竖排识别兜底（`text_recognizer`）。
- **计时**：每例预热后跑 3 次取中位数；`ms_median` 为该 ROI 的端到端识别耗时。
- **CER**：Levenshtein 编辑距离 ÷ 期望文本长度；先归一化（全角冒号/斜杠、去空白），再对 40 例的 CER 取算术平均。
- **环境**：隔离 venv（Python 3.14），`numpy 2.3.5`；上游侧另装 `paddleocr 3.7.0` + `paddlex 3.7.1 --no-deps` 并手动补齐依赖。计时为同机同进程量级对比，不追求绝对基准值。
- **口径说明**：仓库运行时为 Python 3.10，A/B 在 3.14 隔离环境跑；两套引擎的相对关系（精度/延迟/体积）不受解释器小版本影响，但绝对毫秒数仅作横向比较。

## 3. 逐例明细

| # | 位置 | 期望 | 本地 | 上游 | 本地 ms | 上游 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | wq-title | 悬赏封印 | 悬赏封印 | 悬赏封印 | 4.4 | 107.4 |
| 2 | wq-currency | 4.7万 | 4.7万 | 4.7万 | 3.7 | 134.6 |
| 3 | wq-card-title | 软萌甜心美少女 | 软萌甜心美少女 | 软萌甜心美少女 | 3.2 | 149.0 |
| 4 | wq-desc | 自己击败唐纸伞妖 | 自己击败唐纸伞妖 | 自己击败唐纸伞妖 | 4.2 | 144.5 |
| 5 | wq-count | 0/8 | 0/8 | 0/8 | 3.2 | 93.8 |
| 6 | wq-count | 12/12 | 12/12 | 12/12 | 3.2 | 110.0 |
| 7 | wq-desc | 击败3个鬼女红叶 | 击败3个鬼女红叶 | 击败3个鬼女红叶 | 4.2 | 141.7 |
| 8 | wq-desc | 击败10个天邪鬼绿 | 击败10个天邪鬼绿 | 击败10个天邪鬼绿 | 4.5 | 136.9 |
| 9 | wq-desc | 击败12个兵俑 | **击败12个兵通** ❌ | 击败12个兵俑 | 5.1 | 141.6 |
| 10 | wq-count | 0/3 | 0/3 | 0/3 | 2.0 | 112.2 |
| 11 | wq-count | 0/10 | 0/10 | 0/10 | 2.3 | 85.4 |
| 12 | wq-count | 0/12 | 0/12 | 0/12 | 2.8 | 118.5 |
| 13 | wq-reward | 30 | 30 | 30 | 2.4 | 92.5 |
| 14 | wq-reward | 30000 | 30000 | 30000 | 3.3 | 772.3 |
| 15 | wq-timer | 下次刷新: 09:19:32 | 下次刷新：09:19：32 | 下次刷新：09:19：32 | 4.3 | 1207.7 |
| 16 | wq-button | 前往探索 | 前往探索 | 前往探索 | 3.2 | 843.4 |
| 17 | wq-vertical | 现世妖怪 | 现世妖怪 | 现世妖怪 | 3.9 | 739.8 |
| 18 | wq-vertical | 天邪鬼绿 | 天邪鬼绿 | 天邪鬼绿 | 3.1 | 795.9 |
| 19 | wq-vertical | 扫把与伞 | 扫把与伞 | 扫把与伞 | 2.8 | 1062.8 |
| 20 | wq-invite | 邀请好友 | 邀请好友 | 邀请好友 | 3.2 | 1243.4 |
| 21 | wq-reward | 碎片 | **碑片** ❌ | 碎片 | 2.4 | 113.1 |
| 22 | cy-time | 14:13 | **014:13** ❌ | 14:13 | 3.7 | 134.0 |
| 23 | cy-gold | 3281万 | 3281万 | 3281万 | 2.7 | 165.5 |
| 24 | cy-jade | 23647 | 23647 | 23647 | 3.5 | 102.5 |
| 25 | cy-ap | 4.6万 | 4.6万 | 4.6万 | 3.7 | 100.4 |
| 26 | cy-name | 软萌甜心美少女 | 软萌甜心美少女 | 软萌甜心美少女 | 4.0 | 116.5 |
| 27 | cy-photo | [饺er] [照片] | **[饺e[照片】** ❌ | [饺er][照片] | 4.2 | 120.3 |
| 28 | cy-vertical | 探索 | 探索 | 探索 | 2.2 | 124.1 |
| 29 | cy-vertical | 召唤 | 召唤 | 召唤 | 1.8 | 94.8 |
| 30 | cy-vertical | 加成 | 加成 | 加成 | 1.8 | 98.2 |
| 31 | cy-menu | 图鉴 | **图姿** ❌ | 图鉴 | 1.9 | 83.7 |
| 32 | cy-menu | 珍旅居 | 珍旅居 | 珍旅居 | 2.1 | 104.8 |
| 33 | cy-menu | 纳物库 | 纳物库 | 纳物库 | 2.3 | 99.0 |
| 34 | cy-menu | 组队 | 组队 | 组队 | 1.8 | 102.7 |
| 35 | cy-menu | 阴阳寮 | 阴阳寮 | 阴阳寮 | 2.1 | 110.4 |
| 36 | cy-menu | 花合战 | 花合战 | 花合战 | 2.2 | 113.7 |
| 37 | cy-menu | 阴阳术 | **阴阳** ❌ | **阴阳朮** ❌ | 2.0 | 129.4 |
| 38 | cy-menu | 式神录 | 式神录 | 式神录 | 2.2 | 114.7 |
| 39 | cy-vertical | 町中 | **町** ❌ | **（空）** ❌ | 176.8 | 149.6 |
| 40 | wq-vertical | 取消追踪 | **取消** ❌ | 取消追踪 | 140.5 | 142.9 |

> 第 15 例两套引擎都输出全角冒号与空格，归一化后判对；第 39/40 例 `calls=2`（单行失败后走检测回落），所以本地耗时抬到 140~177ms。

## 4. 错例分析

**本地 8 例**：

| 类型 | 用例 | 实际影响 |
| --- | --- | --- |
| 形近字 | 兵俑→兵通、碎片→碑片、图鉴→图姿 | **真影响**：悬赏按子串匹配怪物名（`any(name in monster_name ...)`），`兵通`/`碑片` 会失配该卡；`图鉴` 属菜单，多由模板匹配承担，影响小 |
| 多字/脏字 | 14:13→014:13 | 时间解析出错风险 |
| 符号/丢字 | `[饺er] [照片]`→`[饺e[照片】` | 昵称展示类，影响小 |
| 截断 | 阴阳术→阴阳、町中→町、取消追踪→取消 | 关键字可用（`阴阳`、`町`、`取消`），实际多能兜底 |

**上游 2 例**：

| 用例 | 现象 | 实际影响 |
| --- | --- | --- |
| 阴阳术→阴阳朮 | 异体字 | 关键字 `阴阳` 可命中，影响小 |
| 竖排「町中」→ 空 | 检测+识别两轮都空 | 若按关键字 `町` 判定会**失配**，本地反而略好 |

**归纳**：上游的精度优势几乎全部来自「形近字」，而这类恰好是悬赏目标名、奖励名等**严格匹配字段**；本地优势在开销与竖排兜底。两者不是简单的「谁全面更好」。

## 5. 分支内容（`staging/20261123-ocr-paddle`，`5d60b803`）

| 文件 | 改动 |
| --- | --- |
| `module/ocr/common.py` | 新增：`OcrLogger`（按 `log/ocr/images/<date>/`、`log/ocr/text/<date>.txt` 落盘）+ `BoxedResult` |
| `module/ocr/ppocr.py` | 重写为 PaddleOCR `TextSystem`（`medium`/`small` 档位、`use_angle_cls=False`、`box_thresh=0.8`、`unclip_ratio=1.6`、竖排 `text_recognizer` 兜底、`recognize_batch`） |
| `module/ocr/rpc.py` | `warmup()`、模型规格与日志开关 RPC、内置模型缓存目录配置、启动/请求超时 |
| `module/ocr/base_ocr.py` | 空 ROI 守卫、去掉 `enlarge_canvas`、`logger.attr` 降为 `debug` |
| `module/atom/list.py`、`tasks/DailyTrifles/script_task.py` | `BoxedResult` 改从 `module.ocr.common` 导入 |
| `tasks/GlobalGame/config.py`、`config/template.json`、`assets/i18n/zh-CN.json` | 新增 `global_game.ocr.save_ocr_log`（默认关闭，调试用） |
| `script.py` | 接线日志开关；`__main__` 启动 OCR 服务后 `warmup()` |
| `requirements-in.txt`、`requirements.txt` | `ppocr-onnx==0.0.3.9` → `paddleocr>=3.0,<4.0`（锁 `3.7.0`）+ `pyyaml==6.0.2`；`numpy` 约束调整 |

**验证**：`py_compile` 全部改动文件通过；导入冒烟通过（`module.ocr.rpc/base_ocr/ppocr`、`module.atom.list`、`tasks.GlobalGame.config`）；`python -m pytest -q tests` = **542 passed / 10 failed**，10 个失败与 `czr` 基线完全一致（7×HeroTest `Timer`、2×SwitchOnmyoji `ScriptError`、1×DailyTrifles income）。**实机未做**。

**未移植**（发布打包时再补）：内置模型损坏自检与自动补全（`_download_bundled_ocr_models` / `_repair_bundled_ocr_models`）；`deploy/docker/requirements.txt` 仍含 `ppocr-onnx`（上游同样未更新）。

**依赖风险**：`paddleocr 3.7.0` 在 Python 3.14 下需要两处补丁才能初始化（`paddlex` 的 extras 检查放行 + `opencv-contrib-python` dist-info shim），依赖约束比本地 `ppocr-onnx` 严格；合并前需在仓库运行时（Python 3.10）重新验证安装与模型分发。

## 6. 复跑方式

A/B 工具在仓库外（`%TEMP%\ocr-ab\`，不入库，临时目录可能被清理）：

```powershell
# 隔离 venv 内
python bench.py local       # 产出 engine_local.json
python bench.py upstream    # 产出 engine_upstream.json
python summarize.py         # 汇总精确率/CER/耗时/差异明细
```

需要复核时按 `bench.py` 里的 `BOX_CASES`（依赖 `boxes.json` 的 ROI 索引）与 `MANUAL_CASES` 重建即可，用例裁片来自 `p1_16416_wq_traced.png` 与 `chess_16416_now.png`。
