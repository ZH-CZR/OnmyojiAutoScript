# 本项目安全更新

首次环境安装见 [FIRST_RUN.md](FIRST_RUN.md)，使用 `start.bat`。环境安装与服务共用运行锁，服务运行时不能安装依赖。ZIP 源码安装没有 Git 历史，允许正常运行任务，更新接口返回 `source_archive` 并禁用自动更新；不伪造或初始化历史。Git 克隆继续遵循下述更新约束。`requirements-ocr.txt` 变化同样触发待安装状态，安装时与主依赖一起传给 pip。

更新实现位于 `deploy/project_update.py`。旧启动安装器与 Web API 共用此实现，默认跟随 `https://gitee.com/oYe486/onmyoji-auto-script.git` 的 `master`；Fork 维护者可配置自己的仓库与发布分支。检查版本不修改工作树；安装只执行 `fetch` 后的 `merge --ff-only`，不使用 reset、stash、清理、自动切分支或改写远端。

## 配置与迁移

`config/deploy.yaml` 中的开关互相独立：

| 字段 | 新安装默认值 | 行为 |
| --- | --- | --- |
| Repository | 本项目 Gitee 地址 | 可指定 Fork 仓库，必须与 origin 地址完全一致 |
| Branch | master | 可指定发布分支，支持 release/stable 等名称；安装时必须与当前分支一致 |
| AutoCheckUpdate | true | Web 服务启动后检查一次，之后按间隔检查 |
| CheckUpdateInterval | 60 | 分钟；0 关闭后台检查，保留手动检查 |
| AutoUpdate | false | 启动安装器自动安装、Web 定时安装的开关；不限制手动安装 |
| AutoRestartTime | null | 北京时间 HH:MM；null 关闭 Web 定时安装 |
| EnableReload | true | 成功安装后，允许受管理的 `server.py` 重启 |
| InstallDependencies | true | 依赖清单变化时允许安装依赖；关闭时留下明确的待处理状态 |
| KeepLocalChanges | true | 旧字段兼容保留，已不控制更新行为；始终保护本地改动 |

读取部署配置时，将已知旧 OAS Coding、GitCode、GitHub 地址迁移为本项目地址，不改写实际 Git origin。自定义 Fork 地址与分支保持原值，不会在升级或重复读取时改回默认。已有自动安装开关、检查间隔、维护时间均保留，默认值只对缺少字段的配置生效。

实际 `origin` 与 `Repository` 配置不一致时明确停止。仅与 `Branch` 配置同名的工作树分支允许安装；其他开发分支可以查询版本。未提交（含暂存、删除）、未跟踪文件、本地额外提交、分叉及未完成的 Git 操作均阻止安装。被 Git 忽略的配置、日志、缓存不会计为未跟踪文件；若新版本新增文件与这些本地文件重名，仍停止安装以保护原文件。检查与安装有跨进程互斥锁；不会删除 Git 自己的锁文件。Web 服务还持有运行锁，阻止另一个启动安装器在服务仍运行时安装更新。

## Fork 配置

Fork 安装在 `config/deploy.yaml` 中设置，例如：

```yaml
Deploy:
  Git:
    Repository: https://github.com/your-name/your-fork.git
    Branch: release/stable
```

此处仅展示需要修改的两个字段，保留文件内的其他配置。仓库支持 HTTP(S)、SSH（含 `git@host:owner/repo.git`）、Git 协议、file 地址和本地仓库路径。分支必须是明确的合法名称，不支持标签、提交号、通配符或 `@{-1}` 等动态表达式。

建议从 Fork 的发布分支新建独立检出，再设置上述字段。已有安装切换来源前先停止服务，保留本地修改；由维护者明确设置 `origin` 并检出目标分支。更新器不会代做这两步。目标必须包含本地提交历史，历史分叉或不相关时拒绝安装，不以强制覆盖完成切换。检查失败时不将原仓库残留的远端历史作为新来源最新版本返回。

## 任务与定时行为

后台每分钟检查配置是否到达维护时间。指定时间之后，当天首次具备安装条件且没有任务进程运行时尝试安装；任务运行中每分钟重新判断空闲状态，跨日后等待新一天的维护时间。网络错误逐步延长重试间隔。版本检查失败也采用退避，下一次成功检查恢复正常间隔。

手动安装先检查是否可更新；本地改动等阻碍存在时不停止任务。确认可更新后阻止新的任务启动，停止运行中的任务并等待进程退出，再由安全更新器重新检查并安装。进程未退出则拒绝安装。若停任务之后的二次检查或安装失败，任务保持停止，用户可根据结果处理并重新启动。

`server.py` 直接启动的服务能在更新成功后依次关闭 HTTP、任务、OCR 和图像服务，再替换解释器，加载新代码。手动更新前运行的实例名称通过进程环境传给重启后的服务；不保存用户配置或凭据。自动安装要求空闲，不启动此前已停止的实例。若 `EnableReload=false`，或外部 OASX 启动服务时没有提供受管理的重启事件，则返回 `restart_required=true`，需手动重启；重启前拒绝启动任务。

Web 生命周期中的任务协调不涵盖独立启动的旧 Qt GUI 或直接运行的游戏脚本；使用旧启动安装器前应先退出这些独立进程。旧 Qt 更新页当前只是占位页，没有后台更新循环。

## 依赖与失败恢复

普通代码更新不重复安装依赖。`requirements.txt` 或 `requirements-in.txt` 改变时，在 Git 元数据目录写入待处理状态；安装依赖并通过 `pip check` 后清除。服务使用当前解释器安装依赖；旧安装器使用其部署配置指定的解释器。旧安装器首次运行且允许安装依赖时执行一次安装。

如果依赖安装失败或被关闭，代码可能已经快进，但结果明确报告 `dependency_error` 或 `dependencies_pending`。不自动回滚代码或环境，不恢复游戏任务。重启 Web 服务时，若 `InstallDependencies=true` 会重试待处理依赖；关闭时保持控制面板可访问、任务启动被阻止。可以先人工安装当前项目依赖，再启用此选项重启，让检查完成并清除待处理状态。

## API

- `GET /home/update_info`：手动检查，保留 `is_update`、`branch`、`current_commit`、`latest_commit`、`commit` 字段，并返回 `status`、`message`、本地差异与领先/落后数量。自动安装关闭不阻止查询。
- `POST /home/execute_update`：手动安装。兼容保留旧 GET 路由；返回结构化结果，旧前端若只支持字符串提示，需要适配 `message`。
- `GET /home/update_status`：查询最近结果、安装中、需要重启与依赖待处理标记。

典型状态为 `up_to_date`、`available`、`updated`、`local_changes`、`local_commits`、`wrong_branch`、`wrong_remote`、`wrong_source`、`busy`、`deferred`、`network_error`、`git_error`、`dependencies_pending`、`dependency_error`、`restart_required`。只有 `updated` 表示此次安装成功；不能仅凭 HTTP 200 判断成功。

## 离线验证

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_project_update dev_tools.test_server_startup dev_tools.test_schedule_api dev_tools.test_task_startup dev_tools.test_config_template -q
.venv\Scripts\python.exe -m pip check
```

更新测试仅使用临时本地 Git 仓库和模拟进程，验证快进、本地修改保留、分叉、来源/分支、网络错误、更新锁、运行锁、依赖失败与恢复、任务协调和定时退避。不会获取或更新当前工作树，不启动设备或游戏。离线测试不代表 Gitee 网络、外部 OASX 前端、真实进程重启或游戏恢复已经实测。
