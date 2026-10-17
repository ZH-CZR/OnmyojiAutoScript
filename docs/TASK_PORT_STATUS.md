# 六道觉移植与旧任务清理

## OAS 空壳目录清理

2026-10-16，按用户要求核对来源后删除三个 OAS 遗留空壳的五个剩余文件：`tasks/OrochiMoans/` 的 assets.py、config.py，`tasks/Component/CooperativeBattle/` 的 assets.py，以及 `tasks/Component/CustomCourtyardAffair/` 的 assets.py、ca1/image.json。

来源核对使用清单指定的 OAS 提交 `00c083e83a6ad8a258b05536dab8454a77e20325` 和 YYS 提交 `6bff084c630e884a0a30a9f870892f6bb430e2fe`。前两个目录的文件忽略换行符后与 OAS 一致；CustomCourtyardAffair 是此前清除四张 OAS 图片及无调用定义后留下的空类和空数组，清理历史见 OAS_RESOURCE_CLEANUP.md。三个目录在 YYS 指定提交中均不存在，五个文件均未纳入来源清单，因此未修改清单或哈希。

删除前未发现业务导入或调用；同步移除 config_manual.py 调度优先级字符串中的 OrochiMoans。御魂悲鸣仍由 tasks/Orochi 的悲鸣模式承接。历史词库名称和既有比对快照保留，比对报告已标注后续删除；AGENTS.md 同步记录该边界。

删除后静态检查未发现三个名称的 Python 残留引用，三个目录均已不存在。任务启动、服务启动、配置模板、皮肤资源及滑动兼容共 24 项离线 unittest 通过，pip check 通过；未运行游戏、设备或 OCR 实测。AGENTS.md 指定的 tests 测试及 verify_port.py 当前缺失，使用现有离线检查验证。

2026-10-16，六道之门“觉”从 `pattering-rain/yys` 的提交
`6bff084c630e884a0a30a9f870892f6bb430e2fe` 导入。

## 六道之门“觉”

- 导入 `tasks/SixRealms_jue/` 的 90 个公开源码、JSON 和图片文件，原始文件哈希记录于 `upstream/manifest.json`。
- 通过现有 `SixRealms` 菜单的模式选择接入，共用设备、次数限制、时间限制和进度记录，不新增单独菜单入口。
- 修复参考仓库独立入口调用不存在的 `_run_moon_sea` 方法，改为 `one()`。
- 清除资源索引和 JSON 中五条没有图片、也没有被任务代码使用的定义：`I_SKILL103`、`I_SKILL104`、`I_COIN2`、`I_TEAM_SWIPE_UP`、`I_FENGHUANG`。
- 清单中的哈希保留参考提交原始值，未改写为本地适配后的哈希。

## 旧任务清理状态

用户要求删除以下十二个未接入菜单的任务目录：

`ActivityShikigami`、`AutoCheckinBigGod`、`DyeTrials`、`FindJade`、
`FrogChallenge`、`GotoMain`、`GuguArtStudio`、`GuildActivityMonitor`、
`IbukiArena`、`MartialArts`、`OtherWorldTwilight`、`WeeklyPurchase`。

用户已手动删除上述十二个目录，2026-10-16 复查确认全部不存在。
`SixRealms`、`SixRealms_jue` 和 `RichMan` 目录均完整保留。
已清理外围的导航导入、调度优先级、翻译及废弃账号字段屏蔽规则。
返回庭院改为调度器的 `prepare_main_page()` 调用通用导航，保持设备复用、异常恢复和停服延后行为。
保留旧 `WeeklyPurchase` 配置到 `RichMan` 的迁移兼容。

## 未引用图片清理

2026-10-16 核验当前代码、资源索引、JSON、目录加载及隐式蒙版后，删除 344 张未找到引用的任务图片，保留 2612 张。
其中删除仅匹配 OAS 的图片 211 张；另有 199 张因存在引用或动态加载保留。完整删除清单、保留规则和来源同步注意事项见 [RESOURCE_CLEANUP.md](RESOURCE_CLEANUP.md)。
图片清理未增加缺失引用。随后已删除原有 27 条缺图定义中无业务调用的 22 条及对应 JSON 源定义；剩余 5 条为悬赏封印的坐标点击对象，不读取图片。24 项离线 unittest 和 `pip check` 通过，未运行游戏。

继续追踪此前保守保留的 OAS 图片后，又删除 195 张未被当前任务读取的图片、189 条对应 JSON 记录及 5 个无调用资源定义。
当前任务图片为 2417 张，仅匹配 OAS 的剩余 4 张，均属正常调度尚未接入的旧账号切换模块。完整清单见 [OAS_RESOURCE_CLEANUP.md](OAS_RESOURCE_CLEANUP.md)。

## 验证范围

使用 `dev_tools` 中的任务启动、服务启动、配置模板、皮肤资源及滑动兼容 unittest；
新增椒图/觉模式、觉资源完整性、Boss 分支及空闲庭院导航与异常处理的离线测试。
删除后重新运行上述检查，24 项 unittest 全部通过，`pip check` 通过。没有运行游戏任务。
残留名称仅用于旧配置迁移、通用返回庭院设置和历史记录，没有发现对已删除任务模块的运行时导入或调用。

项目协作说明指定的 `tests/test_upstream_sync.py`、`tests/test_port_runtime.py`、
`tests/test_project_update.py` 和 `dev_tools/verify_port.py` 在当前工作区不存在，无法执行。

## OASX 配套翻译

2026-10-16 补齐当前任务菜单、配置组、字段及帮助键的中文翻译。
标题已重新按 YYS 指定提交的 `module/zh-CN.json`、`module/zh-CN-Web.json`
及显式配置标题核对，修正 83 个标题；YYS 中显式配置标题优先于两份词库。
YYS 未覆盖的字段以公开 OASX 词库和本项目配置补充。来源与加载方式见
[翻译维护说明](../assets/i18n/README.md)。
OASX 按字段 `name` 查找翻译，不采用后端模型的中文 `title`。
更新词库后重新打开 OASX 即可重新加载，不需要启动游戏任务。

新增 `dev_tools/check_i18n.py` 离线检查当前模型生成的菜单、配置组、字段和帮助键，
覆盖检查不依赖前端版本的内置翻译。空帮助文本沿用公开词库行为。
翻译补齐不改变任务可用性或闭源功能边界。

## 删除购买寮包

2026-10-17 按用户要求删除 `tasks/GuildGift/` 的实现与专用素材，同时移除日常菜单、配置模型、默认模板、调度顺序与中文翻译中的任务入口。旧用户配置文件保持原样；旧 `guild_gift` 字段由配置模型忽略，不再进入任务总览或调度。重启后端并刷新前端后生效。

`upstream/manifest.json` 与 YYS 比对报告保留原始来源和历史快照，不代表当前任务仍然存在。当前工作树没有 `dev_tools/upstream_policy.py` 或 `dev_tools/upstream_sync.py`；以后恢复同步工具时须落实排除规则，避免重新导入此任务。

删除后验证：任务调度、总览 API、配置模板、任务启动与服务启动共 28 项 unittest 通过；720 个中文翻译键覆盖检查及 `pip check` 通过。内存验证旧配置即使启用 `guild_gift` 也不进入模型或调度，任务目录与菜单入口均已移除。未运行设备、OCR 或游戏流程。
