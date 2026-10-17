# 现有环境运行

本项目使用现有环境直接运行。前端显式部署可安装依赖并启动后端，见 [FRONTEND_DEPLOY.md](FRONTEND_DEPLOY.md)；空目录首次安装和便携包构建仍未提供；按用户新要求已移植项目版本检查及手动/自动更新，配置和保护规则见 [PROJECT_UPDATE.md](PROJECT_UPDATE.md)。

## 启动

在项目目录使用可用的 Python 环境执行，例如：

```powershell
.venv\Scripts\python.exe server.py
```

根目录批处理启动器已移除。上述命令需要项目虚拟环境可用；也可使用已有的 Python 3.10 环境直接运行 `server.py`。普通启动不下载、安装或修复依赖。

HTTP 地址继续读取 `config/deploy.yaml` 的 WebuiHost/WebuiPort，也可以通过 `--host`、`--port` 指定。当前本地配置和所有任务配置保留。可用 `.venv\Scripts\python.exe server.py --help` 查看参数而不启动 RPC 或任务。

服务仍启动图像和 OCR RPC，OCR 初始化失败时控制面板仍可用；运行游戏任务前仍需现有依赖和模型可用。正常关闭控制台可以停止本次后端，启动不会杀死其他服务；端口占用会如实报错。

## OASX

可在适配后的 OASX 部署页选择本项目目录，安装依赖并启动后端；也可先用上面的入口启动后端，再在 OASX 中连接 `config/deploy.yaml` 指定的地址；本机原配置端口为 22288。适配的外部前端及源码路径见前端部署说明。

OASX 可部署启动或连接已运行的后端。后端恢复版本查询、检查更新和手动更新 API，以及 Home 的 Updater 菜单；前端部署链路已适配，尚未从界面执行联网安装验证。任务菜单、配置、调度和日志 API 保留。

## 配置和维护

`deploy/` 名称保留以兼容运行代码引用，包含配置、模板、日志和设备枚举工具。AutoUpdate、CheckUpdateInterval、AutoRestartTime 参与后台更新；旧 Repository、InstallDependencies、EnableReload 等字段不参与运行。读取配置不会自动重写用户文件；未来显式保存运行配置时才按当前模板写出。

保留现有 `.venv`、`toolkit`、OCR 模型和设备支持文件，不自动安装依赖，不替换 ADB；仅显式开启自动更新或调用更新接口时才检查并更新本项目 Git 仓库。任务自身的配置迁移、模拟器启动、游戏任务重试/重启和调度逻辑继续保留。
