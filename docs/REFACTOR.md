# YYS 公开源码重构与维护

本分支从第一仓库的远端最新提交建立，保留其公开调度、设备、截图、输入、OCR 和服务端核心；任务、任务配置、导航及素材以第二仓库的最新提交为主。本次没有使用其他本地项目的修改，也没有使用旧迁移目录中的代码。

本项目的维护与发布仓库为 [oYe486/onmyoji-auto-script](https://gitee.com/oYe486/onmyoji-auto-script)，更新分支为 `master`。其他仓库仅作为源码参考，由维护者先合并、适配和验证，再发布到本项目仓库；本地安装只从本项目仓库更新。

| 来源 | 分支 | 固定提交 |
| --- | --- | --- |
| [公开核心](https://github.com/xylolit-mu/OnmyojiAutoScript) | `self` | `00c083e83a6ad8a258b05536dab8454a77e20325` |
| [主要任务上游](https://gitee.com/pattering-rain/yys) | `run_now` | `6bff084c630e884a0a30a9f870892f6bb430e2fe` |

完整来源与每个受管理文件的上游哈希、安装哈希保存在 `upstream/manifest.json`。本次管理 3242 个文件，包括来自第一仓库的百鬼公开配置/素材回退文件；文件数量不代表已完成游戏实测的功能数量。

## 实现边界

| 部分 | 实现方式 |
| --- | --- |
| 调度入口、进程与 HTTP 服务 | 第一仓库的 `.py` 实现；不加载第二仓库的 `script.pyd`、`script_process.pyd` 或授权入口 |
| 截图、控制、模拟器启停 | 第一仓库的公开设备实现，增加第二仓库所需的方法与超时接口 |
| 任务构造 | 调度器绑定当前设备；第二仓库的任务及其子任务仍使用 `ScriptTask(config)`，共享同一个设备 |
| 任务、通用战斗、庭院、导航与图像规则 | 第二仓库公开源码和素材；适配集中在 `dev_tools/upstream_policy.py` |
| 配置与 GUI 接口 | 第二仓库任务字段，第一仓库的序列化、配置 API 与核心运行参数；显式迁移旧字段 |
| 新任务调度 | 保留原过滤顺序，将过滤表中没有的新任务加入队列，避免加载成功却永不执行 |
| 进度保存 | 通过 `safe_save` 重新读取最新配置再保存计数，保留其他刚修改的设置 |
| OCR | 第一仓库公开 PaddleOCR/ONNX 实现，不使用第二仓库私有 OCR/设备封装 |

消息通知沿用公开核心的 OnePush 文本接口；第二仓库的截图附件通知尚未迁移。

未迁移并隔离的功能：`SwitchAccountMany`、`SwitchAccountOnce`、`SwitchAccountLoop`、`TongXinTeam`、百鬼夜行及 `window_win32` 桌面后端。账号任务有闭源依赖；百鬼夜行的第二仓库版本包含 `marshal` 字节码封装，第一仓库版本又依赖 `oashya` 的二进制跟踪器，按用户要求先跳过，后续独立完善。
z
上述任务不进入可用菜单或调度队列，直接调用会返回明确原因。第一仓库的百鬼公开代码/素材保留用于后续独立重写，当前主程序依赖中已移除 `oashya`。六道之门的 `SixRealms_jue` 有公开源码，已经保留。

本分支不读取、验证或持久化第二仓库的 `card_key`。不提供伪造授权、反编译或闭源模块的成功占位实现。NumPy、OpenCV、ONNX Runtime 等正常第三方库仍有原生扩展，这与上游私有业务模块的隔离范围不同。

## 安装与启动

Windows / Python 3.10，运行命令前切换到本分支的项目根目录。使用全新虚拟环境；不要复制另一个项目的 `module`、`tasks` 或 `site-packages`。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe server.py --host 127.0.0.1
```

继续使用第一仓库的前端连接方式。模拟器连接和启停设置采用第一仓库的设备配置；第二仓库仅填写端口号的 `serial`（例如 `16384`）会迁移为 `127.0.0.1:16384`。`device_2` 的专有启停、等待关闭及窗口管理行为尚未整体实现，不能宣称与第二仓库完全等价。桌面 `window_win32` 配置会明确报错，需要换为已支持的模拟器后端。

旧 `weekly_purchase` 商店配置迁移到第二仓库的 `rich_man`；旧活动同名字段不作为商店设置载入。旧全局悬赏邀请设置迁移到 `wanted_quests.emergency`，已有第二仓库设置优先。第二仓库的重启任务补充公开核心要求的调度和异常重启配置。

默认关闭大神签到。如需使用该公开可选功能，再安装 `requirements-biggod.txt` 并配置相应环境。

## 本地项目更新

`origin` 指向 `https://gitee.com/oYe486/onmyoji-auto-script.git`，跟踪 `master`。原始公开核心远端保留为 `core-base`，只用于参考，不作为更新来源。

```powershell
git remote -v
git fetch origin master
git merge --ff-only origin/master
```

启动器和 GUI 更新使用相同项目仓库与分支。更新器先检查 `origin`，再检查工作区和提交历史：有未提交/未跟踪文件时停止，有本地额外提交或分叉时停止，只允许快进更新。不会自动暂存、强制重置或丢弃本地修改。已有旧部署配置中的仓库/分支会切换到本项目的固定来源，`AutoUpdate` 开关仍可按需关闭。

仓库未初始化或远端还没有 `master` 时，会明确报告无法获取分支，保留本地代码。首次发布时需要将本项目完整版本上传到该仓库的 `master`；不要把两个参考仓库的 `.pyd`、授权模块或不透明字节码直接发布到可运行分支。

## 维护者合并参考源码

以下工具仅用于维护者准备合并第二仓库更新；普通本地安装不执行这一流程。先新建或更新独立参考仓库，再预览。同步程序读取指定 Git 提交的归档，不读取参考仓库未提交的工作文件，不导入或执行参考仓库代码。

```powershell
git clone --depth 1 --branch run_now https://gitee.com/pattering-rain/yys.git .codex/upstream/yys
# 以后更新同一参考仓库：
git -C .codex/upstream/yys fetch origin run_now

# 克隆后使用 HEAD；后续 fetch 后用 origin/run_now。
.venv\Scripts\python.exe dev_tools/upstream_sync.py --source .codex/upstream/yys --ref origin/run_now --verbose
.venv\Scripts\python.exe dev_tools/upstream_sync.py --source .codex/upstream/yys --ref origin/run_now --apply
git diff --stat
```

预览默认不写入任何文件。出现 `CONFLICT` 时返回码为 2，整批更新不会开始写入；手工修改、删除受管理文件或新增文件发生名称碰撞都会报告冲突。上游删除的受管理文件仅在本地内容仍符合记录时删除。Git 的正常 CRLF/LF 转换不会造成误报。

需要本地调整上游代码时，将调整写入 `dev_tools/upstream_policy.py`；本地核心适配放在 `module/compat` 或公开核心模块中。不要直接改完受管理文件后期待下一次同步覆盖它。适配锚点变化或新出现不透明字节码时，同步会停止，需先审查接口变化。添加新任务后，仍需审查菜单、配置字段、依赖和游戏表现。

审查差异并完成下方验证后，由维护者提交并推送到本项目仓库的 `master`，本地安装随后从本项目仓库获取该完整版本。直接覆盖为两个参考仓库的旧更新路径不会用于本分支。

## 验证

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests/test_upstream_sync.py tests/test_port_runtime.py tests/test_project_update.py -q
.venv\Scripts\python.exe dev_tools/verify_port.py
.venv\Scripts\python.exe -m pip check
```

本次已验证任务与服务端导入、55 个可用任务的离线构造及共享设备、配置 schema/序列化往返、静态素材路径、调度遗漏修复、进度保存、受管理更新冲突和重复同步。OCR 在全新环境、独立模型缓存下实际识别了“阴阳寮礼包 12345”，返回“阴阳寮礼包12345”。

没有启动游戏或执行游戏任务。这些检查不能代替模拟器截图/控制、庭院导航、战斗结算及任务连续运行的实测；升级后需要按实际使用任务逐项验证。当前可交付的是公开核心与第二仓库任务的集成分支，隔离功能和游戏实测范围如上所列。
