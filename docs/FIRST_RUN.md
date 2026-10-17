# 新机器首次安装

支持 Windows 10 1809 / Windows 11 x64。把源码完整解压到普通用户可写目录后，双击根目录的 `start.bat`。不需要预先安装 Python 或 Git，不需要管理员权限。第一次必须联网，磁盘需留出数 GB 空间。

入口先准备后端环境，全部成功后执行 `server.py`；后续双击同一个文件即可启动。控制台需要保持打开。当前只准备后端，**不下载或启动 OASX 前端，也不安装模拟器或游戏**。服务默认地址为 `127.0.0.1:22267`，`/test` 返回 `"success"`；根地址 `/` 返回 404 是正常的 API 服务行为。

安装步骤：

1. 下载独立 Python 3.10 x64 到 `toolkit/python/`，创建本项目 `.venv`。不修改系统 Python、PATH 或注册表。
2. 下载 MinGit 到 `toolkit/Git/`。两个下载包均核对仓库固定的 SHA-256。
3. 同时安装 `requirements.txt` 与 `requirements-ocr.txt`，检查依赖及关键模块导入。ADB 由 adbutils 提供，不替换其他软件或模拟器的 ADB。
4. 生成 `config/deploy.yaml`，写入本项目的 Python、Git 和 ADB 路径。已有显式配置保留。首次配置只监听本机；新安装默认在每次后端启动时自动更新源码，已有配置开关保留。
5. 下载两份 PP-OCRv6 medium ONNX 模型到 `toolkit/.paddlex/official_models/`，检查文件并实际初始化 OCR 推理管线。
6. 启动后端服务。安装过程不会连接模拟器、点击游戏或运行任务。

### OASX 无法识别根目录

本项目配套新版 OASX 从 `config/deploy.yaml` 读取 Python 路径，但仍检查 `toolkit/Git/mingw64/bin/git.exe`。MinGit 2.56 的目录改为 `ucrt64`，首次安装现在通过 `deploy/git_layout.ps1` 自动创建 `mingw64 → ucrt64` 的目录联接，使现有前端可识别，实际 Git 文件不复制。已有有效旧目录保持原样；冲突目录或指向外部安装的 Git 不会被自动覆盖。

已经运行过旧安装脚本的机器可以先退出后端，再在包含 `server.py` 和 `start.bat` 的后端根目录打开 PowerShell，执行以下命令，然后在前端重新选择该根目录：

```powershell
New-Item -ItemType Junction -Path .\toolkit\Git\mingw64 -Target (Resolve-Path .\toolkit\Git\ucrt64).Path
```

此命令仅适用于 `ucrt64/bin/git.exe` 已存在且 `mingw64` 尚不存在的情况，不会覆盖现有目录。也可取得新版后端后运行 `start.bat -InstallOnly` 自动处理。前端根目录应选择后端项目最外层，不选择前端目录、`toolkit` 或 `.venv`。前端连接地址需与 `config/deploy.yaml` 的端口一致，新安装默认 `127.0.0.1:22267`。

2026-10-17 使用本机配套 OASX 源码提交 `2226ae84907a0e4f1e2d9379306a17b681a4ec7b` 的实际校验条件核对独立安装目录：部署配置、配置指向的 Python、旧 Git 路径和安装器四项均通过，旧路径执行 `git --version` 成功；未修改前端仓库，未在另一台机器操作前端界面。

## 重试与诊断

网络失败、依赖安装失败或 OCR 初始化失败会中止，不会显示安装完成。修复网络后重新运行，下载成功的校验包可复用，已完成的依赖安装按清单指纹复用并重新检查。Python 或 Git 的目标目录存在但损坏时不会覆盖，控制台会说明需要先将该目录移开。下载暂存、模型和依赖均不提交到仓库。安装阶段与后端共用运行锁；后端正在使用时会拒绝安装，请先正常退出服务。

可只安装而不启动服务：

```powershell
.\start.bat -InstallOnly
```

默认 Python 包镜像为清华 PyPI 镜像，安装命令设置 60 秒网络超时和 5 次请求重试，不修改系统 pip 配置。已有部署配置中的显式源继续使用；也可以仅对本次安装指定其他镜像，新建部署配置会记录所选源：

```powershell
.\start.bat -InstallOnly -PypiMirror https://pypi.org/simple
```

诊断依赖时可以使用 `-SkipModels`，此模式不代表游戏运行环境就绪。正常使用请不带此参数。

Python/Git 下载优先国内镜像，镜像失败时回退到固定的官方地址。每个来源尝试两次；curl 设置连接超时及低速检测，避免长时间没有下载进展。所有来源共用同一份官方 SHA-256，镜像内容不一致时拒绝安装并尝试下一来源。下载支持当前进程的 HTTPS_PROXY 环境变量（Windows 自带 curl 下载器）。全部来源失败时保留清楚的下载地址及错误，不能用其他来源的未知文件绕过 SHA-256 校验。

| 内容 | 首选来源 | 后备来源 |
| --- | --- | --- |
| Python 包和 ADB 依赖 | [清华 PyPI](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/) | 可用 `-PypiMirror` 指定其他源 |
| MinGit 安装包 | [清华 GitHub Releases 镜像](https://mirrors.tuna.tsinghua.edu.cn/github-release/git-for-windows/git/) | Git for Windows 官方 GitHub Releases |
| 独立 Python 安装包 | 阿里云 GitHub Releases 镜像 | Astral 官方 GitHub Releases |
| OCR 模型 | 百度 BOS 国内官方来源 | 失败后重新运行安装入口 |

清华目前未提供此版本独立 Python 的对应镜像，因此不构造不存在的清华下载地址。模型文件不属于 PyPI 包，不能通过修改 pip 源改为清华下载。

2026-10-17 网络策略验证：实际从阿里云下载独立 Python、从清华下载 MinGit，两份文件均匹配固定官方 SHA-256；安装入口在独立环境中复用已准备的依赖及模型成功。60 项相关离线测试和 `pip check` 通过，包含坏哈希拒绝、来源失败切换、缓存复用及用户源配置保留。未在另一台物理机器或游戏中验证。

已有部署配置如果仍指向另一台机器的路径，需要用户自行修正；首次入口不会悄悄改写显式字段。迁移项目目录后，原虚拟环境也可能失效，应重新创建独立环境。

## ZIP 与 Git 安装

新安装默认启用 `AutoUpdate`，每次后端启动时检查一次。Git 安装发现云端版本不同时完整替换受管理源码；ZIP 安装或被旧前端初始化成空 Git 的目录，会先准备真实 Git 元数据，再获取版本并更新。不要求手动提交 ZIP 源码。

用户配置、日志、`.venv` 和 `toolkit` 环境、模型缓存保留。源码上的本地修改可能被覆盖，开发机请在 `config/deploy.yaml` 中明确关闭 `AutoUpdate` 与 `AutoCheckUpdate`。开关和更新范围详见 [PROJECT_UPDATE.md](PROJECT_UPDATE.md)。

运行中没有定时更新，网络失败在下一次后端启动时再尝试。旧 `CheckUpdateInterval` 与 `AutoRestartTime` 字段不再参与行为。

## 参考与下载来源

复用 OAS 核心 `xylolit-mu/OnmyojiAutoScript` 提交 `00c083e83a6ad8a258b05536dab8454a77e20325` 的 `deploy/template`、配置读写和安装分层。该版本 `deploy/installer.py` 在 Python 已可运行后才执行 Git、pip、ADB 安装，故增加 PowerShell 引导阶段，保留来源校验和运行锁，并按当前用户要求在启动时完整更新受管理源码。

- [Astral python-build-standalone 20261003](https://github.com/astral-sh/python-build-standalone/releases/tag/20261003)：CPython 3.10.22 的 install_only 发行包，哈希来自该发布的 SHA256SUMS。
- [Git for Windows v2.56.0.windows.2](https://github.com/git-for-windows/git/releases/tag/v2.56.0.windows.2)：MinGit x64 ZIP，哈希来自发布页。
- 固定地址及哈希统一记录在 `deploy/runtime-downloads.json`。维护者升级运行时应先审查来源并重新进行独立安装验证，不在客户端动态选择“最新版本”。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_first_run dev_tools.test_project_update dev_tools.test_server_startup dev_tools.test_schedule_api dev_tools.test_task_startup dev_tools.test_config_template -q
.venv\Scripts\python.exe -m pip check
```

离线测试与首次安装验证均不能代表真实新机器、模拟器连接和游戏流程已通过。

2026-10-17 在不含 `.venv`、`toolkit` 和本地部署配置的独立源码目录中，实际下载校验 Python/MinGit、创建独立虚拟环境、安装依赖并下载官方 OCR 模型。150 项离线测试及 `pip check` 通过；重复安装复用环境；实际后端的 OCR、图像、任务菜单与 ZIP 更新接口返回 HTTP 200，随后正常退出。合成图片 `ENV READY 12345` 识别正确，置信度约 99.4%。本次仍在同一台 Windows 主机上验证，未进行另一台物理新机器、前端、模拟器或游戏流程实测。
