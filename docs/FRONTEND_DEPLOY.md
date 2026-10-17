# OASX 前端部署后端

目标前端为 `D:\yys\oasx-oYe`，对应源码 `D:\yys\oasx-monitor-source`。适配前两个目录的 `data/app.so` SHA256 均为 `5e2670415c317ade7edd9938f10d43ab5db9de8bce78a6d02cad18a2c3a4c8e82`。

在前端选择本项目目录 `D:\yys\OnmyojiAutoScript-oYe`，使用部署按钮即可安装依赖并启动后端；开启“部署后自动登录”时就绪后连接本机配置端口。部署前需先停止本项目服务，端口占用会中止部署，避免改动正在使用的环境。

参考 OAS 核心提交 `00c083e83a6ad8a258b05536dab8454a77e20325` 的 `deploy/installer.py`，保留 `python -m deploy.installer` 的调用约定，重新实现为独立安装入口。安装器仅使用标准库，使用当前 Python 3.10 执行 `pip install -r requirements.txt` 和 `pip check`，失败返回非零退出码。前端优先选项目 `.venv/Scripts/python.exe`，没有时使用前端部署配置中的现有 Python（默认 toolkit）。安装与服务使用同一解释器。

需要已有 Python、pip、本项目源码和 config/deploy.yaml；安装依赖可能访问网络。本次不提供空目录下载、Python 安装、便携包或模型下载。不恢复旧 OAS 的进程批量终止、ADB 替换和 Git 强制同步。部署不读取旧 InstallDependencies 开关，每次点击部署均安装锁定依赖；仅检查可执行 `python -m deploy.installer --check`。正常 server.py 启动继续不安装依赖。

前端移除部署前 prefetch（旧实现会重写 origin），代码更新使用后端 Home/Updater，仍固定为本项目 origin/master 并保留工作区保护。未提交或未推送代码不会因部署而被覆盖。前端不再执行 taskkill，也不主动停止其他服务。服务使用 python.exe 保留启动日志；就绪检查通过 `/test`，失败或超时明确报错。

验证命令：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_frontend_deploy dev_tools.test_runtime_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe -m deploy.installer --check
```

前端在对应源码目录运行 flutter analyze、部署相关 flutter test 和 flutter build windows --release。离线测试不等于从界面执行联网安装或设备、OCR、游戏实测。

## 2026-10-17 交付记录

按用户要求将源码原有未提交的配置集合排序等改动一同构建，更新至 `D:\yys\oasx-oYe`，保留目标 logs 和其他非构建文件。前端源码基于 `a0a29d6`，没有提交或推送。

- `oasx.exe` SHA256：`d463b2041094606b801932e7310e3e41759ec13ea40b275033f8cb3e82cb0c11`。
- `data/app.so` SHA256：`e2e75f7435840b2d079e0560b23ddc1c41a867f81aba0daa9951a8d70b509c27`，与源码 Release 产物一致。
- 后端全量 141 项 unittest 通过，719 个中文翻译键检查通过，安装器 `--check` / pip check 通过。
- 前端部署相关 11 项测试通过，部署代码静态分析通过，Windows Release 构建成功。
- 扩展运行整个前端测试目录：46 项通过、1 项跳过、1 项失败。失败为原有 `test/widget_test.dart` 的 Flutter 计数器模板（未初始化 LocaleService，且界面没有计数器）；相同提交的独立检出也复现，不将其报告为全量通过。
- 未实际点击前端部署执行联网 pip install，未进行 OCR、设备或游戏流程实测。

## 本机 Python 路径迁移

当前前端源码目录为 `D:\yys\SourceCodes\oasx-monitor-source`。本机 Python 3.10.11 已随旧目录移动至 `D:\yys\oas-old\yys-install-yu\toolkit`；项目 `.venv/pyvenv.cfg` 的 `home` 已同步修正，前端继续使用项目 `.venv/Scripts/python.exe`。该虚拟环境仍依赖此基础 Python 目录，后续移动或删除前应先处理环境依赖。

若部署报 `No Python at ...`，应先核对虚拟环境的 `home` 与基础解释器实际位置；仅存在 `.venv/Scripts/python.exe` 文件不代表环境可运行。此次修复后安装器 `--check`（含 pip check）及部署/运行入口/服务启动共 14 项离线测试通过；未执行联网安装或从前端界面启动服务。
