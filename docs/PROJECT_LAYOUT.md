# 项目目录与清理记录

2026-10-17，根据用户要求撤除首次安装与项目更新，保留当前环境运行。清理前分支为 master，存在未提交/未跟踪部署改动；未执行 reset、checkout、pull 或推送，按实际文件备份后处理。

后续变更：已按用户新要求独立移植 OAS 自动更新，新增 module/server/updater.py、update_service.py 和 dev_tools/test_project_update.py，恢复 Home 更新 API。以下移除范围和验证结果是清理时的历史记录，当前更新边界以 [PROJECT_UPDATE.md](PROJECT_UPDATE.md) 为准。首次安装与便携构建仍未恢复。

## 目录边界

| 类别 | 目录/文件 | 处理 |
| --- | --- | --- |
| 运行入口 | server.py、script.py、gui.py | 保留；根目录批处理启动器已按用户要求移除，启动方式见 RUNNING.md |
| 业务与核心 | tasks/、module/ | 保留任务/配置/设备/服务与 GUI，删除项目更新实现和界面 |
| 配置与素材 | config/、configs/、assets/、bin/ | 保留用户配置、模板、翻译及设备 APK/JAR |
| 环境与模型 | .venv/、toolkit/ | 原样保留，不安装、不迁移、不删除目录联接 |
| 运行辅助 | deploy/ | 只保留 config.py、template、utils.py、logger.py、emulator.py |
| 维护材料 | dev_tools/、docs/、upstream/ | 保留离线测试、素材工具、技术说明与任务来源哈希 |
| 许可证 | LICENSE、docs/licenses/FluentUI.txt | 保留本项目及现有 FluentUI 插件许可证 |
| 用户数据 | log/、.codex/、.git/ | 保留日志/截图、参考检出、协作记录及 Git 历史 |

维护工具和来源材料虽非运行依赖，仍用于任务回归、素材维护和来源追溯，因此留在各自专用目录。

## 移除范围

- 首次安装、Git/Pip/ADB 安装、启动前进程停止与更新、便携包下载/构建/启动器和对应专用测试。
- Web 更新实现与 update_info/version_info/execute_update API、Home 的 Updater 菜单、Qt 更新页和未使用的 QML 生成副本。
- 旧首次安装/更新说明、部署来源记录及本机历史 OASX_SETUP.md，替换为 [RUNNING.md](RUNNING.md)。
- 一次性 bootstrap_port.py、人工安装配置脚本 setup_oasx.ps1、旧 Docker 安装材料及过时的 GitHub dev→master 自动 PR 工作流。
- 根目录 fluentui/ 构建源码、示例、文档；保留 module/gui/FluentUI/ 运行插件及许可证。
- dist/ 下旧整合包、下载物、失败构建和迁移验证副本整体移出，避免以后误用仍带更新功能的旧包。
- 项目源码目录中的 __pycache__/、.pytest_cache/ 为可再生缓存；清理时避开环境、模型、用户数据和目录联接。

## 可恢复备份

备份目录：`D:\yys\OnmyojiAutoScript-oYe-cleanup-backup-20261017-173049`。

before.patch 保存清理前已跟踪文件的工作区差异；各移除/主要修改文件保留清理前副本，另有完整 dist/ 与 fluentui/。本次改动的详细 Git 差异可在当前工作区查看。备份不参与项目导入和运行。

没有删除用户配置、游戏素材、OCR 模型或 Python/Git 工具环境。外部 OASX 安装/更新按钮不再作为支持入口，连接已有后端的方式见运行说明。离线验证不等于游戏/设备实测。

## 验证结果

- 清理前 138 项离线 unittest 通过；移除安装/便携专用测试、增加 5 项运行回归后，现存 117 项全部通过。完整日志位于备份目录 after-tests.log。
- 新回归覆盖真实 __main__ 入口（RPC/HTTP 启动使用替身）、从含空格/中文工作目录直接调用 server.py --help（批处理启动器移除后调整）、旧配置字段忽略且文件不改写、ASGI 生命周期/正常 HTTP/已移除更新路由返回 404，以及运行时模拟器类型构造。
- 中文菜单/字段/帮助共 719 个键覆盖检查通过；pip check 通过。变更 Python AST 语法检查及 QML 资源清单检查通过。
- 移出 fluentui/ 共 306 个文件（13,583,912 字节）；dist/ 整体移入备份；118 个源码缓存目录移入备份 caches/，不遍历环境、用户数据或目录联接。
- Qt 基础 QGuiApplication 可创建，但本机现有 FluentUI 最小控件检查原生崩溃（0xC0000005），在保留原 fluentui 构建源码的备份工作目录下同样复现；不能将本次检查视为 Qt GUI 通过。运行插件文件未修改。
- 未进行游戏任务、设备操作、OCR 识别或外部 OASX 连接实测；未安装依赖、更新仓库、提交或推送。

当前补充：按用户要求恢复 deploy/installer.py 作为前端显式依赖安装入口；普通启动不安装。前端自动部署说明见 [FRONTEND_DEPLOY.md](FRONTEND_DEPLOY.md)，以上清理范围为历史记录。
