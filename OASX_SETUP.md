# OASX 本地连接

> 新机器安装后端请使用根目录 `start.bat`，自动准备独立环境和 OCR 模型，详见 [首次安装说明](docs/FIRST_RUN.md)。此入口不下载 OASX 前端。下文保留本机历史连接及修复记录，其中绝对路径不能直接用于其他机器。

> 已安装仍无法识别根目录时，检查 Git 2.56 的 `ucrt64` 与前端固定检查的 `mingw64` 目录差异。新版首次安装已自动增加目录联接，旧安装的修复命令见 [OASX 根目录识别](docs/FIRST_RUN.md#oasx-无法识别根目录)。配套新版前端可直接使用配置中的 `.venv` Python，无需复制 Python 到 `toolkit`。

当前后端目录：`D:\yys\OnmyojiAutoScript-oYe`。
前端程序：`D:\yys\oasx-oYe\oasx.exe`。
本机前端保存的服务地址为 `127.0.0.1:22288`，后端已使用同一端口。

## 修复内容

- 补充本地 `config/deploy.yaml`，将 Python 指向本项目的 `.venv\Scripts\python.exe`。
- 创建 `toolkit\Git` 目录联接，满足 OASX 的安装目录校验；目标是已有的 `D:\yys\yys-install-yu\toolkit\Git`。
- 重新生成 `config/template.json`，使默认配置符合移植后的任务字段及枚举。原模板的 11 处类型/枚举错误会导致 `/script_menu` 返回 500。
- OCR 初始化失败时记录错误并继续提供 HTTP 管理接口；HTTP 退出和初始化异常时清理已启动的辅助服务。
- 关闭此移植目录的自动 Git 更新、依赖安装和 ADB 安装/替换，避免前端部署时覆盖移植内容。需要更新或安装依赖时手动执行。

本地 `config/oas1.json` 是此次首次启动从旧模板自动生成的默认配置，已用新模板初始化。本次未导入其他项目的账号配置。

## 使用

打开 OASX，根目录选择上述后端目录，服务地址使用 `127.0.0.1:22288`。前端现有的自动部署、部署后自动连接设置可继续使用。

也可在后端根目录手动启动：

```powershell
& .\.venv\Scripts\python.exe server.py
```

`http://127.0.0.1:22288/test` 应返回 `"success"`；这是 API 服务，访问 `/` 返回 404 属于正常行为。

重新生成本机连接配置：

```powershell
& .\dev_tools\setup_oasx.ps1 -GitDirectory 'D:\yys\yys-install-yu\toolkit\Git' -Port 22288
```

此脚本接受 `-PythonPath`，默认使用本项目 `.venv`。它保留其他部署字段，但会设置本地启动所需的 Python、Git、端口及上述自动操作开关。`toolkit\Git` 只联接已有 Git，不复制或修改其内容。

本机 `.venv` 原本使用 `D:\yys\yys-install-yu\toolkit` 作为基础 Python，因此此基础目录与 Git 目标目录仍需保留。迁移到其他机器时应重新准备 Python 环境和 Git，并重新运行配置脚本。

## OCR 状态

2026-10-16 已在本项目 `.venv` 补齐 OCR 运行环境：PaddleOCR 3.7.0、PaddleX 3.7.2、ONNX Runtime 1.18.1、NumPy 1.26.4。保留 FastAPI 所需的 AnyIO 3.7.1 和 Pydantic 2.10.0，并固定下载组件及 chardet 的兼容版本。未修改共享基础 Python 的已安装包。

PP-OCRv6 medium 检测和识别模型已从本机已有缓存复制到以下目录；两份模型共约 132 MiB，6 个必要文件均通过复制前后 SHA-256 校验：

- `toolkit/.paddlex/official_models/PP-OCRv6_medium_det_onnx/`
- `toolkit/.paddlex/official_models/PP-OCRv6_medium_rec_onnx/`

依赖重新安装命令：

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
```

当前模型使用 CPU / ONNX Runtime 推理，不需要安装 CUDA 或 PaddlePaddle 训练框架。模型已能直接使用本地缓存加载；复制/迁移时应同时保留 `toolkit/.paddlex`。

验证已通过：依赖检查无冲突、模型完整性检查无错误、日志出现 `OCR server ready: 127.0.0.1:22268`，以及 HTTP `/home/ocr_server_info`。单行识别得到 `阴阳师测试12345`，置信度约 99.99%；RPC 多行检测分别识别出 `阴阳师测试 12345` 与 `OCR READY 67890`，服务记录 2 次请求成功、0 次失败。本次验证没有运行游戏任务。

## 验证

```powershell
& .\.venv\Scripts\python.exe -B -m unittest dev_tools.test_server_startup dev_tools.test_config_template -v
```

2026-10-16 验证：OASX 界面已显示正确识别根目录，并自动进入首页加载 `oas1` 和任务列表；全部 58 个任务参数接口返回 HTTP 200。

## 任务启动移植修复

2026-10-16 修复任务启动时 `cannot import name 'log_path' from 'module.logger'`，并检查同一启动链上的移植接口：

- 补齐任务截图和日志归档使用的路径、文件名辅助函数及两种异常类型。
- 将残留的旧 OCR `BoxedResult` 导入改为当前 `module.ocr.common`。
- 任务和子任务沿用调度器传入的设备，移除对本版不存在的设备/模拟器管理器的依赖。
- 图片规则兼容现有资源的 `profile` 参数；通知使用当前后端的 `Notifier.push` 接口。
- 旧导航器使用全局页面和任务自身已导入的页面注册表，不再扫描并执行残留的另一版本导航模块。
- ADB 发现支持虚拟环境继承的 adbutils 实际安装目录。
- 六道「椒图」可正常初始化；本移植版原先明确排除的「觉」模块仅在选择该模式时检查，并给出清楚提示，不再阻断其他任务导入。

```powershell
& .\.venv\Scripts\python.exe -B -m unittest dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_config_template -v
```

10 项回归测试通过，覆盖全部 56 个可执行菜单任务的导入、初始化和设备复用。真实 MuMu 设备自动截图测速选中 `ADB_nc`（约 0.107 秒），并成功取得 `(720, 1280, 3)` 截图、注册图像服务帧、初始化每日琐事任务。验证没有运行游戏任务，也没有保存测试中的截图方式修改。当前 Android 15 不支持的 DroidCast/nemu_ipc 等候选在测速时会记录失败，最终选择可用方式。

后续修复：恢复移植时丢失的 `RuleClick.reset_task_points`、任务点击历史、坐标采样及 `functional/profile` 接口，同时保留 `BaseAtom` 兼容。它们由调度器和现有 `RuleScatter` 共同使用；仅增加空的 reset 方法不足以恢复功能。另将旧导航器的应用运行检查改为当前设备提供的 `app_is_running`。

验证扩展为 12 项回归测试：实际调用 `Script.run('RyouToppa')`，执行寮突破任务准备代码，到首次 `ui_goto_page` 时由测试边界中止；截图、导航和异常处理边界均由测试替身承接，没有操作游戏。另验证普通点击、长按、散点点击共享历史，任务切换时历史被清空。日志中的 NemuIpc 候选失败与这次任务终止无关，测速已成功选中 `ADB_nc`。

## 花札幕台资源索引修复

配置已选择 `costume_shikigami_11`，但原 `CostumeShikigami/assets.py` 缺少磁盘上已有的皮肤图片/JSON 定义。换肤代码发现属性不存在后静默跳过，导致仍使用旧灰色预设按钮模板。

已仅重新生成 `tasks/Component/CostumeShikigami/assets.py`，并让换肤同时更新匹配方式、清空已加载图片和特征缓存。也修复了超时诊断引用缺失确认按钮资源而再次抛出 AttributeError 的问题。

对当前游戏截图的只读验证：预设按钮分数由 0.637 提高为 0.978，式神录页面分数为 0.998，均通过 0.8 阈值。没有降低识别阈值或盲点坐标，也没有发送游戏操作。停止并重新启动任务后，新的脚本进程会加载完整资源索引。

新增皮肤 JSON 后，可只重新生成此组件资源：

```powershell
& .\.venv\Scripts\python.exe -B -c "from dev_tools.assets_extract import AssetsExtractor; AssetsExtractor('tasks/Component/CostumeShikigami').extract()"
& .\.venv\Scripts\python.exe -B -m unittest dev_tools.test_costume_assets dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_config_template -v
```

当前 15 项回归测试通过，包含各皮肤 JSON 与生成属性/图片路径逐项一致性检查、已加载模板换肤及诊断兼容性。

## 切魂分组滑动参数兼容

修复 `Control.swipe() got an unexpected keyword argument 'wait_up_time'`。任务层原本会传递此参数，包括默认值 0；设备层现已接受该参数。非零值表示滑到终点后保持触点、等待指定秒数再抬手，已接入 minitouch、scrcpy 和 window_message。ADB/uiautomator2 的普通零等待滑动保留原行为；它们的原生接口没有终点保持能力，非零等待会在发出滑动前给出明确错误。

验证切魂 `switch_soul_one(2, 1)` 的 OCR 分组稳定判断、真实任务滑动包装和设备分发路径，直到分组点击的测试边界；验证 minitouch 的等待命令先于抬手命令。累计 20 项回归测试通过，没有向游戏发送输入。

```powershell
& .\.venv\Scripts\python.exe -B -m unittest dev_tools.test_swipe_compatibility dev_tools.test_costume_assets dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_config_template -v
```

## 任务结束后的重启配置兼容

寮突破完成后，调度器读取 `restart.restart_config.error_restart_limit`，但移植的 Restart 模型丢失了该配置，造成成功结束后仍然崩溃。现已补回次数限制（默认 3，0 表示禁用异常重启）和重启任务调度配置，并同步默认模板。保留移植版本的 harvest_config、task_config 和角色设置；旧用户配置由模型补齐缺失默认值，不覆盖用户配置文件。

`dev_tools.test_restart_compatibility` 使用真实调度循环和恢复入口，验证成功后继续调度、失败计数、显式次数上限、0 次及关闭重启开关。设备和游戏任务由测试替身承接，没有游戏操作。停止并重新启动任务即可让新脚本进程加载修复。
