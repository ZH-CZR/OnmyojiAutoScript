# 立项书：标注器自定义流程编排（Custom Flow）（2026-11）

## 1. 基本信息

| 项 | 内容 |
| --- | --- |
| 项目名称 | 标注器自定义流程编排（Custom Flow） |
| 立项日期 | 2026-11-19 |
| 本地基准 | `czr` @ `61637819`（2026-11-19） |
| 功能提交 | `4f53ebe0` feat(flow): 标注器自定义流程编排、单步调试与生成可调度任务（2026-11-17） |
| 状态 | **开发已完成、离线单测通过；未实机联调，未做端到端验收** |
| 代码位置 | [module/flow](../../../module/flow) · [flow_router.py](../../../module/server/flow_router.py) · [tasks/CustomFlow](../../../tasks/CustomFlow) · [flow.html](../../../module/server/web/annotator/static/flow.html) |
| 回归用例 | [tests/test_flow_schema.py](../../../tests/test_flow_schema.py) 等 5 个文件，共 26 例 |

## 2. 背景

历次新增小玩法/周常任务，都要单独写一套 `tasks/<Task>/script_task.py`，把「等图 → 点图 → OCR 读次数 → 条件分支」重复实现一遍；标注器虽然能标注图片/OCR/点击/长按/滑动/列表规则，但只能产出素材与规则，无法把规则串成可执行流程。

因此新增一层轻量流程编排：标注器里拖步骤、实时画面上单步调试，验证通过后一键生成可被调度器直接运行的任务代码。刻意不引入上游 `RuleScatter` / 有状态点击框架（耦合高、CPU 开销大，见项目记忆），保持「线性 steps + 嵌套 block」的简单模型。

## 3. 已完成内容（当前实现盘点）

**流程模型与运行时**（`module/flow`）

- `schema.py`：flow.json 为唯一事实源，14 个 op —— `wait_image`、`click_image`、`click_point`、`long_click`、`swipe`、`ocr_read`、`wait_ocr`、`if`、`loop`、`sleep`、`goto_page`、`call`、`log`、`end`；条件支持 `== != > >= < <= contains not_contains truthy falsy`，操作数可用 `var:名字` 取流程变量；前端表单、运行时、代码生成三处共用同一份 `OP_SPECS`。
- `runtime.py`：`FlowRunner` 解释执行，`FlowAbort` 中止 / `FlowEnd` 正常结束，`MAX_FLOW_STEPS=5000` 防死循环，逐步产出 `StepResult`（供单步调试回显）。
- `host.py`：`TaskFlowHost`（真实设备，转调 `BaseTask` / Device）与 `PreviewFlowHost`（单帧预览，只匹配识别、不点真机）。
- `rules.py`：读 `tasks/<Task>/res/*.json`，把规则名解析成 `RuleImage` / `RuleOcr` / `RuleSwipe` / `RuleClick`。
- `store.py`：`flows/<name>.json` 读写与命名校验。
- `codegen.py`：把 steps 展开成可读可改的真实调用（`wait_until_appear` / `wait_until_appear_then_click` / `swipe` / `ocr` 等），复制引用规则与图片，生成 `script_task.py`、`assets.py`，自动写入 `config.py` 与 `config_model.py`，并打 `.flow_auto` 标记。

**标注器页面与接口**

- `GET /tool/flow` 三栏页面（步骤树 · 实时画面 · 属性/单步测试），标注器顶栏新增「流程编排」入口。
- API：`ops`、`list`、`flow/{name}`、`save`、`delete`、`duplicate`、`rules`、`tasks`、`pages`、`test`、`generate`。
- 截图进程支持 `click` / `long_click` / `swipe` 命令，可在实时画面上真实执行，不再依赖远端 zerorpc 做单帧匹配。

**通用任务与调度接入**

- `tasks/CustomFlow`：通用跑道，按 `config/custom_flow.flow.flow_name` 读 `flows/<name>.json` 解释执行；`stop_after_end` 控制结束后是否继续排期。
- `config_menu.py` 新增「Custom Flow」分组，并自动发现带 `.flow_auto` 标记的生成任务；`config_model.py` 与 `config/template.json` 同步登记。

## 4. 测试现状（关键结论）

**已做：**

- 5 个离线单测文件、26 个用例，覆盖 schema 校验与条件求值、runtime 解释执行（StubHost）、codegen 生成、store 读写、任务注册。
- 2026-11-19 实测：`26 passed`。

**未做（本立项的缺口）：**

1. **无实机/模拟器联调**：`TaskFlowHost` 只经过 StubHost 语义验证，未在真机上跑过任何一步。
2. **无端到端流程**：仓库内 `flows/` 为空，尚无一条真实流程从标注 → 保存 → 单步调试 → 运行跑通。
3. **生成任务的调度链路未验证**：`generate` 产物启用后 `set_next_run` / `TaskEnd` / 失败重试 / OASX 战斗统计均未在真机确认。
4. **前端只有人工点验**：`flow.js`（约 900 行）无 UI 自动化或回归脚本。
5. **PreviewFlowHost 与真实执行的差异未标定**：单帧预览通过的流程不代表真机可用。

## 5. 待办与里程碑

| 阶段 | 内容 | 验收 |
| --- | --- | --- |
| M1 冒烟 | 真机执行 `wait_image`、`click_image`、`ocr_read` 三个基础 op | 每步 `StepResult.ok=true`，动作落点正确 |
| M2 样例流程 | 用一条真实日常（优先低风险、无战斗）编排出 `flows/*.json` 并跑通 | 连续 3 轮成功，含一次超时 `continue` 分支 |
| M3 单步调试 | 页面 `execute=true` 在实时画面验证点击/长按/滑动，含 `abort` 中断分支 | 中断后前端正确显示失败步骤，流程不卡死 |
| M4 生成任务 | `generate` 出新任务，配置启用后由调度器运行 | 日志、`set_next_run`、失败重试行为正确 |
| M5 边界 | `MAX_FLOW_STEPS`、`stop_after_end`、规则缺失、OCR 为空 | 各分支有可复现结论，异常不吞错 |

## 6. 验收标准

- M1~M3 通过后，至少一条真实流程入库（`flows/<name>.json`）并在 `config` 中可调度。
- 生成代码与解释执行语义一致（同一 flow 两条路径结果相同）。
- 失败路径不静默：`FlowAbort` 必须体现在任务状态与日志中。
- 不新增 `requirements-in.txt` 之外的依赖。
- 实机结论回填到本文档「测试现状」，并把剩余风险转为已知问题或关闭。

## 7. 风险与约束

| 风险 | 说明 | 应对 |
| --- | --- | --- |
| 坐标基准固定 | `click_point` 以 720x1280 为基准 | 实机确认分辨率适配逻辑；优先用规则点击 |
| 规则/素材依赖标注质量 | 生成任务会复制规则与图片 | 先跑单步调试，再生成任务 |
| 单帧预览与真机不等价 | PreviewFlowHost 不执行动作 | 以 M1/M2 真机结果为准 |
| 生成任务污染配置 | 自动写 `config.py` / `config_model.py` | 生成后立即启动自检，确认菜单与配置可加载 |
| 无自动化 UI 测试 | `flow.js` 无回归 | 关键操作列入 M3 手工验收清单 |

## 8. 决策记录

| 日期 | 决策 | 理由 |
| --- | --- | --- |
| 2026-11-17 | 采用线性 steps + 嵌套 block，不做 goto | 降低解释与代码生成的复杂度，便于阅读生成代码 |
| 2026-11-17 | 不引入上游 `RuleScatter` / 有状态点击框架 | 耦合高、CPU 开销大，对当前需求收益有限 |
| 2026-11-17 | 流程既可解释执行也可生成真代码 | 试错阶段免写 Python，稳定后固化为可维护任务 |
| 2026-11-19 | 立项补测，不重构现有实现 | 功能已落地且离线用例通过，缺口只在实机与端到端验证 |
