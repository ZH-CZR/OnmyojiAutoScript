# 超鬼王入口适配与运行边界

当前阵容与进攻配置已重构为统一模块，最新使用方式及兼容规则见 [META_DEMON_LINEUPS.md](META_DEMON_LINEUPS.md)。下文保留此前移植记录。

## 2026-11-11：合入 YYS 超鬼王更新

来源为 `pattering-rain/yys` 的 `run_now` 分支，提交
`09ebf899efea0f54bca29e4b75df84036cfd94bf`（2026-11-09）。从独立参考库
`D:\yys\SourceCodes\pattering-rain-reference` 的 Git 对象读取；未切换参考工作树。
本次在现有独立 MetaDemon 任务上适配，不导入 ActivityCommon 的活动模式、其他任务更新或二进制设备扩展。
完整基准 `upstream/manifest.json` 保持原值；本次源码来源哈希和素材哈希另记
`upstream/meta_demon_update_20261109.json`。下方历史章节说明的是第一次入口移植。

### 超鬼王任务

- 更新选票、挑战、合成和双入口模板，保留本地 `current/` 私有入口。
- 场上六个星级勾玉按上游区域检测，需间隔至少0.35秒的两张新截图一致。
  已有鬼王也重新检测；星级未知不猜测预设。选中票按标记附近的实际模板分类，
  要求最高分至少0.90且领先至少0.03，与计划星级不同即停止；不按旧固定列猜测票型。
- 新增 `preset_switch`：1—4星共用 `common_stars`，5/6星分别配置，
  `name_map` 支持 `名字:组名,队名;名字:组名,队名`，兼容中文标点。
  名字、组名和队名精确匹配，避免短名误命中。竖排名字只拼接连续文字块，排除下方技能标签。
  星级变化或同星鬼王名字变化时重置对应预设状态；一次性全切按攻击序列去重。
- 预设面板应用后处理御魂装配确认，再检查面板关闭及当前队名。
  同组同队仅在本轮已确认应用且命令条仍一致时跳过。最多3轮，75秒总限时；失败清理面板并报错。
- 保留旧 `switch_soul` 及战斗内数字预设配置，不迁移或覆盖用户已设置字段。
  开启新 `preset_switch` 时优先走挑战页预设，并跳过旧式神录切御魂和战斗内切队。
- 新增 `synthesize_sequence`，**本地默认留空关闭**；填写如 `1 2` 才按顺序合成。
  1星免费，2—5星每次还需一张合成券；每次3张同星材料合成。
  数量必须完整识别为非负整数，动态行位置使用任务内 OCR 副本。
  每星最多20次、90秒，每次点击合成后必须确认材料恰好减少3才允许下一次。
  未确认扣除立即报错，不续点；退出最多3次且不得盲点固定关闭坐标。
- 保留本地入口60秒、选票/开战各15秒、战斗/稳定结算300秒总超时，
  点击不延长总时限。确认进入战斗才计数；失败回挑战页后按原次数/时间上限重试。
  正常结束、异常及 TaskEnd 均恢复导航和设备等待标记，不关闭卡死检测。

### 探索与觉醒刷票

- 新增公共 `BossNumCheck`，通过当前 `RuleOcr.detect_and_ocr()` 读取完整截图，
  只接受合法 `当前/总数`，`0 <= 当前 <= 总数`，只把 `50/50` 视为满票。
  `5050`、负值、越界、非50总数或无法识别都不推断为满票。
- 通用战斗增加默认关闭的 `boss_num_enable`，节流读取、每场有效读数一次，
  奖励末帧最多额外等3秒。按实际签名调用任务重写的 `battle_wait`，兼容旧单参数实现，
  不吞掉函数体内部的 TypeError。
- 觉醒新增 `evo_zone_config.check_boss_num`，默认关闭；单人、队长、队员与中途接管均传递开关，
  结算确认满票后结束本轮，保留原有加成关闭和下次调度流程。
- 探索开放已有 `scrolls.check_boss_num`；战斗结算满票只记录运行时标志，
  回到章节详情才结束，不在战斗中强退。大世界按新版坐标严格读取满票，单人/队长/队员统一走原加成关闭和调度收尾；任务重用时清除上次满票标志。
- 新增 `scrolls.check_realm_raid` 和 `realm_raid_threshold`（默认关闭/27，范围1—30），
  只在章节详情检测突破券，达到阈值安排个突，探索延后1分钟；不额外安排绘卷捐赠。
  原绘卷模式继续保留捐赠流程。识别结果必须满足30总数及计数一致性。
- 保留本地探索章节公共 OCR 与 BoxedResult.box 点击坐标适配，未导入上游旧 after_box 调用。

### 离线验证

新增 `dev_tools.test_meta_demon_updates`，覆盖配置兼容、星级双帧、名字分块、票型真实模板匹配、
预设路由/失败清理/OCR偏移、合成未确认扣除禁止重试、严格票数、旧 battle_wait 签名、
探索安全退出及突破券边界、觉醒队员与接管、节流和素材哈希。
验证命令：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_meta_demon dev_tools.test_meta_demon_updates dev_tools.test_exploration_chapters dev_tools.test_wanted_invitation dev_tools.test_dokan_runtime_safety dev_tools.test_manual_schedule dev_tools.test_immediate_preemption dev_tools.test_schedule_api dev_tools.test_task_schedule dev_tools.test_idle_schedule dev_tools.test_activity_guard dev_tools.test_config_consistency dev_tools.test_config_template dev_tools.test_team_task_entrypoints dev_tools.test_team_room_occupancy dev_tools.test_team_scene dev_tools.test_task_startup dev_tools.test_server_startup -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

2026-11-11：244项测试，1项跳过，其余通过；712个翻译键覆盖检查、pip check通过；
本次改动范围的diff空白检查通过。所有测试离线执行；未连接设备、启动游戏、消耗门票或合成券。
当前活动完整截图的 OCR 和实际游戏流程仍待实测。

## 历史：第一次入口适配


2026-11-09，将 YYS `run_now` 提交
`4f3d570ed479b06d7c67123b3565bb333616d463` 的超鬼王入口素材适配到本地独立的
`tasks/MetaDemon/`，继续使用菜单中的“超鬼王”，无需新增活动通用配置。

## 来源与范围

- 来源仓库：`https://gitee.com/pattering-rain/yys.git`。
- 独立参考检出：`D:\yys\SourceCodes\pattering-rain-reference`，读取上述提交的对象，未切换参考工作树。
- `ActivityCommon/A-超鬼王/a1.png`、`a2.png` 分别保存为任务私有的
  `current/md_entry.png`、`md_enter.png`，按实际模板命中位置点击。
- `ActivityCommon/挑战/召唤鬼王.png` 保存为 `current/md_summon.png`，使用来源任务相同的右下搜索范围。
  上游“临时”目录中的同名图片内容相同，不重复导入。
- 图片原始 SHA-256、来源和目标路径记录在 `upstream/meta_demon_port.json`。
  `upstream/manifest.json` 继续保留原始整体来源基准，不能据此认为其他任务已同步到新版本。
- 新图片和规则均仅供 MetaDemon 使用，未加入活动通用的动态加载目录。
  `current/image.json` 与 `assets.py` 同步，使用现有 `ImageExtractor` 生成新增定义。

## 执行行为

保留星级顺序、强力追击、自动喝茶、疲劳等待间隔、分星御魂、一次切换全部御魂和战斗内预设配置。
原有可识别的超鬼王主界面、活动列表和挑战入口继续支持。新增入口在任务内识别，确认鬼王页面后才更新当前页面。
启动时已经处于战斗则调用现有模型生成的通用战斗配置；不再引用不存在的页面对象、随机点击函数或 `meta_demon.general_battle` 字段。

- 入口总等待 60 秒，门票面板打开、选票召唤和进入战斗各 15 秒；点击不重置该阶段期限。
- 新版“召唤鬼王”仅作为打开召唤流程的入口，不因识别到它就推断已选门票或已进入战斗。
  按配置顺序选择实际识别的门票，确认选择标记的中心位于目标星级列后才点击立即召唤。
- 只有确认进入战斗才增加总战斗次数。已召唤鬼王星级未知时不猜测分星御魂；未开启换御魂时不进入式神录。
- 疲劳度通过现有 `RuleOcr.ocr()` 数字计数接口读取；读数不明时报错，达到上限且禁用喝茶时按配置等待。
- 战斗及结算固定上限 300 秒；胜败和普通奖励继续处理。
  必须在结算提示消失、战斗状态消失后，确认挑战或召唤相关按钮连续稳定至少 1 秒才退出结算等待。
  单独的旧页面标题不能证明结算完成。
- 战斗等待保留设备卡死检测，点击后只补回长等待标记，不逐帧重置设备计时器。
  正常或异常退出恢复进入前的等待标记。
- 每次运行使用独立状态并清零本次计数。临时式神录导航在整个 `run()` 的 `finally` 中按原快照恢复；
  公共关闭按钮列表不被任务永久修改。换魂、入口或截图异常同样执行清理。

## 验证

新增 `dev_tools.test_meta_demon`，23 项离线用例覆盖新入口与实际模板匹配位置、源哈希与规则一致性、
星级选择、错误选择禁止召唤、固定超时、疲劳与喝茶策略、换魂开关、已有战斗、计数、稳定结算、异常清理和重复运行。
图像用例将原模板放入合成的 1280×720 图像中验证命中与点击位置，不代表完整游戏截图的识别准确率。

执行回归：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_meta_demon dev_tools.test_task_startup dev_tools.test_server_startup dev_tools.test_config_template dev_tools.test_wanted_invitation dev_tools.test_dokan_runtime_safety -q
.venv\Scripts\python.exe -m unittest dev_tools.test_manual_schedule dev_tools.test_immediate_preemption dev_tools.test_schedule_api dev_tools.test_courtyard_navigation -q
.venv\Scripts\python.exe dev_tools/check_i18n.py
.venv\Scripts\python.exe -m pip check
```

两组共 168 项，1 项跳过，其余通过；中文翻译覆盖检查与依赖检查通过。
未连接设备、启动游戏、消耗门票或执行喝茶。上游仅提供局部入口素材，未提供当前活动完整截图；
新版门票列表、疲劳度、强力追击、御魂入口及实际战斗/结算仍需游戏截图或实机验证，不能视为整项活动已实测通过。
