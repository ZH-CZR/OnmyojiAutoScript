# 项目自动更新

本次按用户要求重新移植 OAS 更新功能。参考核心提交 `00c083e83a6ad8a258b05536dab8454a77e20325` 的 `module/server/updater.py`、`home_router.py` 与 `deploy/config.py`；代码从本地 Git 对象读取，未使用清理备份或其他项目的改动。来源记录见 `upstream/auto_update_oas_port.json`。

## 开启

在 `config/deploy.yaml` 中设置以下字段，然后用 `start.bat` 启动后端：

```yaml
AutoUpdate: true
CheckUpdateInterval: 5
AutoRestartTime: null
```

新配置默认关闭自动更新；已有配置若明确写了 `AutoUpdate: true` 会继续生效。读取配置不自动改写文件。检查间隔以分钟计，最少 1 分钟。`AutoRestartTime` 可填 `03:50`，表示每天北京时间到该时刻后，检查到更新且任务空闲时应用；`null` 表示每次检查均可应用。手动更新不受该时间约束。配置会在每轮检查时重新读取。

需要系统 PATH 中现有的 `git`。仅支持本项目 `https://gitee.com/oYe486/onmyoji-auto-script.git` 的 `origin/master`；旧 `Repository`、`Branch`、`GitExecutable`、`KeepLocalChanges` 不控制更新来源。不会把本项目更新成原 OAS 或 YYS。

## 更新行为

后台在服务启动后检查，之后按配置间隔重试。检查只 fetch 与查询提交；应用更新使用锁和 `merge --ff-only`，锁文件在已忽略的 `config/project-update.lock`。本地领先/分叉、错误分支、游离 HEAD、外来仓库、网络失败以及任意已跟踪修改或未跟踪文件都会阻止应用。忽略的用户配置、环境和日志不参与脏工作区判断；Git 合并使用 `--no-overwrite-ignore`，避免新跟踪文件覆盖已有忽略文件。

游戏任务运行或正在启动时延后更新；空闲时更新期间阻止新任务启动。不会停止正在运行的战斗，不做 reset、clean、stash、自动提交、改远端或清除 Git 锁。失败原因可通过接口查询。

更新成功后，`server.py` 先通过 Uvicorn 正常退出 HTTP，再关闭本次图像/OCR RPC，最后用相同 Python 和原启动参数替换后端进程。原 `--run`/`Run` 配置仍有效。其他入口若没有注册重启回调，会保留 `restart_required` 并阻止新任务启动，需手动重启后端。外部 OASX 前端本身不更新。

更新本身保留现有 Python 环境和 ADB，不执行依赖安装、便携构建或启动前更新。新增依赖可停止后端后使用前端显式部署安装，见 [FRONTEND_DEPLOY.md](FRONTEND_DEPLOY.md)。

## 接口

Home 菜单恢复 `Updater`，供已有外部前端使用；本次没有恢复旧 Qt 更新页。

| 接口 | 行为 |
| --- | --- |
| `GET /home/version_info` | 查询本地版本，不 fetch |
| `GET /home/update_info` | 手动查询远端，即使 AutoUpdate 关闭也可使用 |
| `GET /home/update_status` | 返回缓存状态，不执行 Git |
| `POST /home/execute_update` | 手动检查并应用；GET 同名接口兼容 OAS 前端 |

保留 OAS 的 `branch/current_commit/latest_commit/commit/is_update` 返回字段；新增 `update_available`、`dirty`、`ahead`、`behind`、`reason`、`error`、`updated` 与 `restart_required` 等状态。提交为 SHA、作者、ISO 时间、主题组成的数组。调用方应检查 `updated/success/error/reason`，失败不伪报成功。

## 离线验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_project_update dev_tools.test_runtime_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe -m unittest discover -s dev_tools -p "test_*.py" -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

Git 测试使用临时裸仓库与两个临时检出，覆盖查询不更改工作树、快进、无更新、本地修改/未跟踪、未推送/分叉、错误来源/分支、游离 HEAD 与 fetch 失败。服务测试覆盖任务繁忙保护、后台启停、自动更新开关和重启请求。真实项目不执行 fetch/merge；离线验证不代表真实远端更新、OASX 或游戏流程实测通过。

2026-10-17 验证结果：全量 138 项 unittest 通过；719 个中文翻译键覆盖检查通过；pip check 无依赖冲突；本次修改范围的 git diff --check 通过。补充回归覆盖忽略文件防覆盖、更新时段、请求取消后仍等待 Git 完成、任务启动保护及 HTTP/RPC 清理后重启顺序。未提交或推送，未对真实项目执行更新。
