# 新机器首次安装

支持 Windows 10 1809 / Windows 11 x64。把源码完整解压到普通用户可写目录后，双击根目录的 `start.bat`。不需要预先安装 Python 或 Git，不需要管理员权限。第一次必须联网，磁盘需留出数 GB 空间。

入口先准备后端环境，全部成功后执行 `server.py`；后续双击同一个文件即可启动。控制台需要保持打开。当前只准备后端，**不下载或启动 OASX 前端，也不安装模拟器或游戏**。服务默认地址为 `127.0.0.1:22267`，`/test` 返回 `"success"`；根地址 `/` 返回 404 是正常的 API 服务行为。

安装步骤：

1. 下载独立 Python 3.10 x64 到 `toolkit/python/`，创建本项目 `.venv`。不修改系统 Python、PATH 或注册表。
2. 下载 MinGit 到 `toolkit/Git/`。两个下载包均核对仓库固定的 SHA-256。
3. 同时安装 `requirements.txt` 与 `requirements-ocr.txt`，检查依赖及关键模块导入。ADB 由 adbutils 提供，不替换其他软件或模拟器的 ADB。
4. 生成 `config/deploy.yaml`，写入本项目的 Python、Git 和 ADB 路径。已有显式配置保留。首次配置只监听本机，自动安装更新默认关闭。
5. 下载两份 PP-OCRv6 medium ONNX 模型到 `toolkit/.paddlex/official_models/`，检查文件并实际初始化 OCR 推理管线。
6. 启动后端服务。安装过程不会连接模拟器、点击游戏或运行任务。

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

ZIP 源码没有 Git 历史：可以正常运行服务和任务，更新接口明确返回 `source_archive`，需要手动重新下载源码或改用 Git 克隆。不会执行 `git init`、伪造历史或将 ZIP 自动覆盖为远端代码。ZIP 模式仍使用独占运行锁，防止同一目录启动两个后端。

Git 克隆保留既有快进更新行为，来源为本项目仓库的 `master`；首次安装不切换分支、不拉取覆盖当前代码。更新时 OCR 依赖清单变更同样触发依赖安装，两份约束同时传给 pip。

## 参考与下载来源

复用 OAS 核心 `xylolit-mu/OnmyojiAutoScript` 提交 `00c083e83a6ad8a258b05536dab8454a77e20325` 的 `deploy/template`、配置读写和安装分层。该版本 `deploy/installer.py` 在 Python 已可运行后才执行 Git、pip、ADB 安装，故增加 PowerShell 引导阶段，而不恢复其旧的强制 Git 更新行为。

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
