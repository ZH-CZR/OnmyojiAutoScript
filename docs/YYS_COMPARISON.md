# 当前项目与 YYS 比对

比对日期：2026-10-16。以当前磁盘工作树为准，包含未提交修改。

后续变更：同日按用户要求删除三个 OAS 遗留空壳 OrochiMoans、Component/CooperativeBattle、Component/CustomCourtyardAffair，并清理 OrochiMoans 调度优先级名称。下文统计及 YYS_COMPARISON_FILES.tsv 保留删除前的比对快照；删除依据见 TASK_PORT_STATUS.md 的“OAS 空壳目录清理”。

## 基准和方法

- 当前项目：`D:/yys/OnmyojiAutoScript-oYe`，分支 `self`；origin 为 `https://gitee.com/oYe486/onmyoji-auto-script.git`。
- YYS：`D:/yys/pattering-rain-reference` 的 Git 提交 `6bff084c630e884a0a30a9f870892f6bb430e2fe`，提交时间 2026-10-11 18:12:12 +0800。
- `git ls-remote` 确认该提交为远端 HEAD，也是 `run_now` 分支头；与本项目来源清单记录一致。
- 当前工作树在生成本报告前有 814 项修改、914 项删除、272 项未跟踪路径；未跟踪目录可能包含多个文件。没有切换分支、同步、重置、提交或推送。
- 对任务目录做同路径 Git blob 内容比对，另检测 CRLF→LF 后是否一致。排除缓存、`.pyc` 和 `.pyd`；未执行参考仓库或封装字节码。
- “内容不同”仍可能包含格式、注释和生成方式变化，不等于业务行为不同；“仅YYS”不等于功能遗漏。未读取用户配置或授权值。

## 总体结论

当前项目的任务层已经大量复用本次 YYS 基准，不能简单描述为任务代码版本落后。核心、配置模型和设备接入保留公开 OAS 实现，并做了本地适配。主要待处理事项是功能隔离、更新安全和维护说明与实际文件不一致。

|任务目录同路径比较|文件数|
|---|---:|
|字节完全相同|2374|
|仅换行符不同|637|
|内容不同|56|
|仅当前项目|193|
|仅YYS|167|

忽略换行符后，同路径共有 3067 个文件，其中 3011 个一致（约 98.17%）。这只表示文件内容一致比例，不表示功能完成率。

|类型|字节一致|仅换行符不同|内容不同|仅当前项目|仅YYS|
|---|---:|---:|---:|---:|---:|
|Python|8|274|37|60|13|
|JSON|11|347|19|64|5|
|PNG|2355|0|0|62|148|

当前 2417 张任务 PNG 中，同路径存在于 YYS 的 2355 张全部一致。其余 62 张为本地独有路径，不能仅凭路径判定作者或来源；图片清理原因参见已有 RESOURCE_CLEANUP.md 和 OAS_RESOURCE_CLEANUP.md。

## 任务与配置差异

- YYS 有 61 个 `script_task.py` 入口，当前有 57 个；54 个仅换行符不同，3 个内容不同。
- 当前缺少 YYS 的四个入口：`SwitchAccountLoop`、`SwitchAccountMany`、`SwitchAccountOnce`、`TongXinTeam`，与来源清单排除项一致。不能宣称这些功能已移植。
- 三个修改入口：`DailyTrifles` 调整 OCR 类型导入并向 LoginHandler 传共享设备；`SixRealms` 向椒图/觉子任务传共享设备并延迟导入觉实现；`SixRealms_jue` 把不存在的 `_run_moon_sea()` 改为 `one()`。
- 基类从 YYS 的 DeviceManager/EmulatorManager 获取方式改成构造参数注入设备，调度器实际调用 `ScriptTask(config=self.config, device=self.device)`。与 AGENTS.md 所述 DeviceManager 架构不同；共享设备目的相同，具体接口不同。
- GameUi 去掉扫描所有目录动态加载 page.py 的行为，使用显式导入注册页面；设备状态方法适配为公开核心的 `app_is_running()`。
- 通用战斗、重启登录、探索构造等同步适配设备参数；通知接口从 `send_push` 改为 `push`。
- 配置基础类型使用 Pydantic 2 的校验/序列化接口；YYS 参考配置仍使用旧接口。调度配置、本地全局战斗/OCR设置、异常重启次数和空闲行为也有差异。
- 设备配置未保留 YYS 的 `device_2`、`window_win32` 等设置，不应按 YYS 的桌面后端能力使用。当前独立公开替代是否可用未做设备验证。
- 皮肤切换增加图片、特征与匹配标志缓存失效；资源索引/JSON 删除了已有清理文档记录的无用定义。
- 仅当前存在的一级任务目录为 `OrochiMoans`，只有两个文件，并不在菜单中；不能视为新增可运行任务。
- 已删除的十二个旧 OAS 任务目录在本次 YYS 参考版本中也没有对应一级目录，因此不是相对该基准的缺失任务。

## 需要优先处理的偏差

### 1. 百鬼夜行仍暴露且入口执行封装代码

`module/config/config_menu.py` 的 other 菜单仍含 Hyakkiyakou，`module/config/config_model.py` 也保留其配置。
`tasks/Hyakkiyakou/script_task.py` 与 YYS 入口仅换行符不同，顶层会调用 `load_module()`，其内部 `marshal.loads()` 后执行代码对象。
这与项目“百鬼先跳过”和不导入 marshal 字节码封装的约束不一致。此次未导入或执行该入口，也没有解包封装内容。
应优先在菜单、调度及直接任务加载路径隔离该任务并明确不可用原因，后续另做公开实现。

### 2. 更新器存在覆盖本地改动的路径

`deploy/project_update.py` 不存在。现有 `deploy/config.py` 默认 Repository 为 GitCode OAS 地址，AutoUpdate=True、KeepLocalChanges=False；这些是源码默认值，未读取实际用户部署配置。
`deploy/git.py` 会设置 origin，默认更新路径执行 `reset --hard` 后再 `pull --ff-only`；keep_changes=True 时 stash 失败也会走硬重置。
因此仅有 pull 的 ff-only 不构成完整保护，与 AGENTS.md 要求的本项目 master 来源及保留现场后停止更新不一致。此次没有运行更新器。
应先修复来源、工作树/未跟踪文件/额外提交/分叉检查，再开放安装端自动更新。

### 3. 维护工具及文档缺失

AGENTS.md 引用的以下文件当前均不存在：
`docs/REFACTOR.md`、`module/compat/capabilities.py`、`dev_tools/upstream_policy.py`、`dev_tools/upstream_sync.py`、`dev_tools/verify_port.py`、`deploy/project_update.py`，以及指定的三个 tests 测试文件。
现有 `dev_tools/bootstrap_port.py` 是一次性导入脚本，清单已存在时要求使用当前缺失的 upstream_sync.py，不能代替后续维护入口。
应让操作文档与实际架构对齐，并为长期保留的适配和图片排除建立可重复执行策略。

### 4. 来源清单不能直接代表当前安装状态

`upstream/manifest.json` 记录 3240 个文件，按其原始 SHA256 检查：3068 个字节一致、42 个不同、130 个已不存在。
清单保留原始来源哈希符合已有清理记录；这不应通过伪造哈希解决。缺少同步策略时，未来直接覆盖可能恢复已删除图片或丢失适配。
该统计覆盖清单所有路径，口径与上面的 tasks Git blob 比较不同；前者也没有归一化换行符。

## 验证范围

- 完成远端引用核对、当前文件/Git blob/来源清单哈希比对、主要 Python 差异静态审查和菜单/更新入口检查。
- 当前项目独立虚拟环境执行 `python -m pip check` 通过：No broken requirements found。
- 本次没有修改业务代码，也未运行单元测试、安装更新、OCR、设备操作或游戏流程；既有文档记录的测试结果不作为此次执行结果。
- 当前参考提交与远端 HEAD 相同，仅说明该基准可获取且一致，不代表未来上游不再更新，也不证明全部功能可运行。

## 逐目录统计

|任务/组件目录|字节一致|仅换行符不同|内容不同|仅当前项目|仅YYS|
|---|---:|---:|---:|---:|---:|
|AbyssShadows|31|5|2|3|2|
|ActivityCommon|2|7|0|47|0|
|ActivityCommon2|0|2|0|0|0|
|ActivitySimple|0|2|0|0|0|
|AreaBoss|22|8|0|2|2|
|AutoCake|4|4|0|0|0|
|BondlingFairyland|48|12|0|2|3|
|Chess|366|29|0|5|0|
|CollectiveMissions|17|14|0|1|0|
|Component|555|116|18|31|43|
|DailyTrifles|82|23|1|1|3|
|Delegation|16|8|0|0|1|
|DemonEncounter|43|22|0|1|0|
|DemonRetreat|11|5|0|0|1|
|Dokan|48|8|2|5|35|
|Duel|28|7|0|0|3|
|EternitySea|1|5|0|0|0|
|EvoZone|9|6|0|0|1|
|ExperienceYoukai|1|4|0|0|0|
|Exploration|50|12|1|1|0|
|FallenSun|5|6|0|0|1|
|FloatParade|15|5|0|0|0|
|FrogBoss|17|6|0|5|0|
|GameUi|158|20|1|20|1|
|GlobalGame|14|5|1|0|14|
|GoldYoukai|1|4|0|0|0|
|GoryouRealm|3|6|0|0|0|
|GuildBanquet|9|5|0|2|0|
|GuildGift|4|6|0|0|0|
|HeroTest|48|7|0|0|2|
|Hunt|8|7|0|0|0|
|Hyakkiyakou|69|30|0|3|1|
|KekkaiActivation|38|8|2|0|0|
|KekkaiUtilize|54|12|0|2|0|
|KittyShop|15|6|0|0|2|
|LBS|9|2|2|2|0|
|MainStory|18|5|0|11|0|
|MemoryScrolls|16|5|2|0|0|
|MetaDemon|21|5|2|2|0|
|MysteryShop|16|4|2|0|1|
|Netherworld|5|4|0|0|0|
|Nian|3|6|0|0|0|
|NianTrue|10|5|0|0|2|
|Orochi|6|6|0|1|2|
|OrochiMoans|0|0|0|2|0|
|Pets|5|5|0|0|0|
|Quiz|5|6|0|1|0|
|RealmRaid|23|7|0|1|1|
|Restart|48|7|4|2|7|
|RichMan|132|45|0|0|2|
|RyouToppa|15|10|0|0|0|
|Script|0|0|5|1|1|
|Secret|7|7|0|0|0|
|SixRealms|59|23|4|30|1|
|SixRealms_jue|83|0|5|0|2|
|Sougenbi|7|7|0|0|4|
|SoulsTidy|15|7|0|0|0|
|SwitchAccountConfig|0|1|0|0|0|
|SwitchAccountLoop|0|0|0|0|2|
|SwitchAccountMany|0|0|0|0|2|
|SwitchAccountOnce|0|0|0|0|4|
|Tako|0|2|0|1|0|
|TalismanPass|21|10|0|0|1|
|TongXinTeam|0|0|0|0|18|
|TrueOrochi|13|5|0|0|1|
|Utils|0|1|0|2|0|
|WantedQuests|27|11|0|1|1|
|WeeklyTrifles|18|8|0|5|0|
|base_task.py|0|0|1|0|0|
|base_task_parent.py|0|0|1|0|0|
|base_task_progress.py|0|1|0|0|0|

## 内容不同的56个任务文件

- `tasks/AbyssShadows/assets.py`
- `tasks/AbyssShadows/res/image.json`
- `tasks/Component/Costume/costume_base.py`
- `tasks/Component/CostumeShikigami/assets.py`
- `tasks/Component/GeneralBattle/assets.py`
- `tasks/Component/GeneralBattle/gb/image.json`
- `tasks/Component/GeneralBattle/general_battle.py`
- `tasks/Component/GeneralInvite/assets.py`
- `tasks/Component/GeneralInvite/gi/image.json`
- `tasks/Component/SwitchAccount/assets.py`
- `tasks/Component/SwitchAccount/exit_game.py`
- `tasks/Component/SwitchAccount/login_account.py`
- `tasks/Component/SwitchAccount/res/click.json`
- `tasks/Component/SwitchAccount/res/image.json`
- `tasks/Component/SwitchAccount/res/ocr.json`
- `tasks/Component/SwitchAccount/res/swipe.json`
- `tasks/Component/SwitchAccount/switch_account.py`
- `tasks/Component/SwitchAccount/switch_account_config.py`
- `tasks/Component/config_base.py`
- `tasks/Component/config_scheduler.py`
- `tasks/DailyTrifles/script_task.py`
- `tasks/Dokan/assets.py`
- `tasks/Dokan/res/image.json`
- `tasks/Exploration/base.py`
- `tasks/GameUi/game_ui.py`
- `tasks/GlobalGame/config.py`
- `tasks/KekkaiActivation/a/image.json`
- `tasks/KekkaiActivation/assets.py`
- `tasks/LBS/assets.py`
- `tasks/LBS/res/image.json`
- `tasks/MemoryScrolls/assets.py`
- `tasks/MemoryScrolls/ms/image.json`
- `tasks/MetaDemon/assets.py`
- `tasks/MetaDemon/md/image.json`
- `tasks/MysteryShop/assets.py`
- `tasks/MysteryShop/ms/things.json`
- `tasks/Restart/assets.py`
- `tasks/Restart/config.py`
- `tasks/Restart/courtyard_affairs/image.json`
- `tasks/Restart/login.py`
- `tasks/Script/config.py`
- `tasks/Script/config_antiban.py`
- `tasks/Script/config_device.py`
- `tasks/Script/config_error.py`
- `tasks/Script/config_optimization.py`
- `tasks/SixRealms/assets.py`
- `tasks/SixRealms/gate1/skills.json`
- `tasks/SixRealms/l104/image.json`
- `tasks/SixRealms/script_task.py`
- `tasks/SixRealms_jue/assets.py`
- `tasks/SixRealms_jue/gate1/skills.json`
- `tasks/SixRealms_jue/gate1/swipe.json`
- `tasks/SixRealms_jue/l104/image.json`
- `tasks/SixRealms_jue/script_task.py`
- `tasks/base_task.py`
- `tasks/base_task_parent.py`

完整逐文件结果见同目录 `YYS_COMPARISON_FILES.tsv`。
