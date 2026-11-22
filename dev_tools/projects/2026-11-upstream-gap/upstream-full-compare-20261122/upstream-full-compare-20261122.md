# 上游全量变更对比（2026-09-18 → 2026-11-22）

- 生成日期：2026-11-22　本地基线：`czr` @ `76757c8d`（2026-11-21）
- 数据源：`dev_tools/upstream_sources.json` 中 5 源（nearaura/master、nearaura/dev、kongdr418/mine、lgg686/self、pinkpig-Peppa/master）
- 采集口径：各源 `git log --since 2026-09-18`，跨源按 `patch-id` 去重；合并提交按「标题+日期」去重后单列
- 判定口径：patch-id 精确命中 → 已完整同步；台账记录已合入/已覆盖 → 已完整同步；本地模块存在但补丁未落地 → 部分实现；本地无对应模块 → 完全缺失

> **本报告自 2026-11-22 起为「上游差异总账」（活文档）**，按立项 README R15 原地维护：新提交追加、状态变更改写、不引入保留可追溯；每次更新在文末「更新记录」追加一行，不得另起新报告替代。HTML 为同结论呈现层。

## 0. 结论摘要（项目经理视角）

- 本轮窗口内上游共 **483 条独立变更**（另 98 条含内容的合并提交、1 条空合并），去重后覆盖 **59 个模块**。
- 本地状态：**已完整同步 180**、**部分实现 257**、**完全缺失 46**。
- 变更类型：核心模块大改 87、可直接复用优化 239、适配风险 144、格式/文档 13。
- 同步建议：P0 优先合并 0、P1 可排期 95、P2 单独评估 83、P3 谨慎评估 85、P4 低优先 7、不引入 33、已处理 180。
- **判断**：本地与上游已形成结构性分叉（本地独有 flow / 超鬼王 / Chess / RichMan），直接 cherry-pick 冲突率高，必须继续按「模块分批 + staging 预演 + 实机验收」推进；新功能缺口（DraftDuel、起号套件）应单独立项。

## 1. 统计总览

### 1.1 本地状态

| 状态 | 条数 | 占比 | 说明 |
| --- | ---: | ---: | --- |
| 已完整同步 | 180 | 36.4% | patch-id 命中或台账记录已合入/已覆盖 |
| 部分实现 | 257 | 54.0% | 本地模块存在，补丁未落地或实现有差异 |
| 完全缺失 | 46 | 9.5% | 本地无对应模块/目录 |

### 1.2 变更类型

| 类型 | 条数 | 说明 |
| --- | ---: | --- |
| 核心模块大改 | 87 | ≥5 文件或 ≥200 行，或中等规模的核心逻辑改动 |
| 可直接复用优化 | 239 | 小范围、模块内聚的修复/优化 |
| 适配风险 | 144 | 触及 module/*、入口脚本、共享资产或配置结构 |
| 格式/文档 | 13 | 仅文档、注释、CI、格式 |

### 1.3 月份分布

| 月份 | 条数 |
| --- | ---: |
| 2026-09 | 94 |
| 2026-10 | 228 |
| 2026-11 | 161 |

### 1.4 模块 Top 15

| 模块 | 条数 | 已同步 | 部分实现 | 完全缺失 |
| --- | ---: | ---: | ---: | ---: |
| Component | 60 | 21 | 39 | 0 |
| DraftDuel | 39 | 2 | 0 | 37 |
| MetaDemon | 33 | 9 | 24 | 0 |
| Chess | 24 | 8 | 16 | 0 |
| GameUi | 23 | 14 | 9 | 0 |
| WantedQuests | 23 | 6 | 17 | 0 |
| module/server | 22 | 4 | 18 | 0 |
| FrogBoss | 21 | 11 | 10 | 0 |
| Exploration | 19 | 9 | 10 | 0 |
| ActivityShikigami | 14 | 0 | 14 | 0 |
| module/device | 14 | 5 | 9 | 0 |
| GlobalGame | 13 | 5 | 8 | 0 |
| 根目录 | 12 | 2 | 10 | 0 |
| 文档/CI | 11 | 1 | 10 | 0 |
| DemonEncounter | 10 | 6 | 4 | 0 |

## 2. 变更时间线总览

### 2026-09（94 条）

| 日期 | 提交 | 来源 | 提交人 | 摘要 | 状态 | 类型 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-18 | `9236651f` | pinkpig-Peppa | User | feat(GameUi): 移植 mine 新版页面导航模块到 dev | 已完整同步 | 适配风险 |
| 2026-09-19 | `d2f98590` | pinkpig-Peppa | neptine | feat(GeneralBattle): Add prepare/preset/green/echo/randomclick hooks and config-driven loadout - add per-task/ | 部分实现 | 核心模块大改 |
| 2026-09-19 | `0e711238` | pinkpig-Peppa | neptine | feat(GeneralBattle): Add completion fallback click and randomclick expectation model | 部分实现 | 可直接复用优化 |
| 2026-09-19 | `d54042b5` | pinkpig-Peppa | neptine | feat(GeneralBattle): Add battle count and state reset helpers, restore climb counting | 部分实现 | 可直接复用优化 |
| 2026-09-19 | `3a6e56c2` | pinkpig-Peppa | User | fix(GameUi): 修复导航超时不抛异常及 registry 遍历 bug | 已完整同步 | 可直接复用优化 |
| 2026-09-19 | `36e1a822` | pinkpig-Peppa | neptine | feat(Costume): Support time-variant courtyard skin 玉岚狐庭 #1824 | 部分实现 | 适配风险 |
| 2026-09-20 | `3f15a981` | lgg686 | User | 修复(契灵)：建房过渡时识别已进入房间 | 已完整同步 | 可直接复用优化 |
| 2026-09-20 | `9f8841f1` | lgg686 | User | 修复(狭间)：切换御魂前关闭残留分布弹窗 | 部分实现 | 可直接复用优化 |
| 2026-09-20 | `225c7a13` | lgg686 | yuyuyuyuyu | 增强(寮活动监控)：修复通知漏检并增加OCR模式 | 已完整同步 | 可直接复用优化 |
| 2026-09-20 | `ef0f8d11` | lgg686 | User | 适配(大神福利)：新版领取界面并修复空按钮等待 | 已完整同步 | 核心模块大改 |
| 2026-09-20 | `05560e29` | lgg686 | User | 新增(换装战斗)：接入灵狐寄愿主题与识别资源 | 已完整同步 | 适配风险 |
| 2026-09-20 | `28e8f060` | lgg686 | Hurry2 | 新增(每周琐事)：接入摸鱼行动并补充超时保护 | 已完整同步 | 适配风险 |
| 2026-09-20 | `52b91fe9` | lgg686 | Hurry2 | 修复(战斗预设)：缩小前三队点击区域避免误滑 | 已完整同步 | 可直接复用优化 |
| 2026-09-20 | `18b0394e` | lgg686 | AzurTian | 修复(战斗预设)：确认点击后等待弹窗关闭 | 已完整同步 | 可直接复用优化 |
| 2026-09-20 | `ef48a3fd` | lgg686 | User | 适配(式神活动)：按本期Boss入口更新页面与识别资源 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `407544fe` | lgg686 | xylolit-mu | 调整(全局奖励)：保留本地验证的关闭点击范围 | 已完整同步 | 可直接复用优化 |
| 2026-09-20 | `24010e18` | lgg686 | xylolit-mu | 重构(点击规则)：统一图像与OCR点击并支持Scatter密度模型 | 部分实现 | 适配风险 |
| 2026-09-20 | `6c3d2927` | lgg686 | xylolit-mu | 调整(通用战斗)：更新探索与活动Scatter安全区域 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `30d05824` | lgg686 | xylolit-mu | 调整(通用页面)：统一奖励识别并注册误触页面与结算策略 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `d9c877a4` | lgg686 | xylolit-mu | 调整(式神活动探索)：取消滑动与模式筛选并统一奖励处理 | 部分实现 | 适配风险 |
| 2026-09-20 | `1f9e14d4` | lgg686 | xylolit-mu | 优化(式神活动爬塔)：修正票数追踪并清理旧战斗资源 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `36cdcc74` | lgg686 | xylolit-mu | 优化(斗技)：匹配超时竞态保护与周目标调度 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `1a9a1f61` | lgg686 | xylolit-mu | 优化(百鬼棋局)：匹配竞态保护与阵容核对及周目标调度 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `1d67a992` | lgg686 | xylolit-mu | 新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程 | 已完整同步 | 适配风险 |
| 2026-09-20 | `69ded977` | lgg686 | xylolit-mu | 拆分(结界蹭卡)：独立控制体力食盒与经验酒壶 | 部分实现 | 适配风险 |
| 2026-09-20 | `4f0b246b` | lgg686 | xylolit-mu | 修正(庭院主题)：更新第13期主页与宠物屋识别资源 | 部分实现 | 可直接复用优化 |
| 2026-09-20 | `602730c6` | lgg686 | xylolit-mu | 修正(式神委派)：收窄完成状态OCR识别区域 | 部分实现 | 可直接复用优化 |
| 2026-09-20 | `8ec6ae47` | lgg686 | xylolit-mu | 清理(生成资源)：统一注释空白与文件结尾 | 已完整同步 | 核心模块大改 |
| 2026-09-20 | `3b161aba` | lgg686 | xylolit-mu | Revert "新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程" | 部分实现 | 适配风险 |
| 2026-09-20 | `51115b4a` | kongdr418 | kongdr | fix(annotator): 修复标注工具停止连接导致 Web 服务卡死 | 已完整同步 | 适配风险 |
| 2026-09-20 | `b94dc89c` | lgg686 | xylolit-mu | 整合(百鬼棋局)：将状态决策流程迁入正式版本 | 部分实现 | 核心模块大改 |
| 2026-09-20 | `cf9eba73` | lgg686 | xylolit-mu | 修复(斗技)：达到名士星数目标后延至下周一运行 | 部分实现 | 可直接复用优化 |
| 2026-09-20 | `395fef27` | lgg686 | xylolit-mu | 修复(全局页面)：识别闲庭并关闭战斗奖励详情 | 已完整同步 | 核心模块大改 |
| 2026-09-20 | `014ffa84` | lgg686 | xylolit-mu | 优化(狭间)：跳过重复御魂装配并识别已击破目标 | 部分实现 | 核心模块大改 |
| 2026-09-21 | `bb808e1b` | pinkpig-Peppa | neptine | feat(Costume): Attach GIF multi-frame behavior in-place so page routing works  #1824 - add RuleGif.attach_to t | 部分实现 | 核心模块大改 |
| 2026-09-21 | `37a884ef` | pinkpig-Peppa | neptine | fix(Costume): Skip missing assets when attaching GIF frames | 已完整同步 | 可直接复用优化 |
| 2026-09-21 | `627ba339` | pinkpig-Peppa | Hurry2 | feat(TouchFish):修复摸鱼行动逻辑问题 | 已完整同步 | 可直接复用优化 |
| 2026-09-22 | `64199898` | lgg686 | User | feat(GeneralInvite): 等待好友列表加载完成并简化房间锁定判定 | 部分实现 | 核心模块大改 |
| 2026-09-22 | `1c5c57ff` | lgg686 | User | fix(DemonEncounter): 跳过宝箱购买后确认弹窗已关闭再进入boss阶段 | 已完整同步 | 可直接复用优化 |
| 2026-09-24 | `a04d51da` | lgg686 | User | fix(DemonEncounter): 优化boss搜索容错并处理中央宝箱遮挡 | 部分实现 | 核心模块大改 |
| 2026-09-25 | `028ca1f8` | lgg686 | User | feat(Exploration): 主线/玩法tab接入导航系统 | 已完整同步 | 核心模块大改 |
| 2026-09-25 | `aaede1db` | lgg686 | User | feat(TrueOrochi): 玩法tab模块检测替代本地次数记账 | 完全缺失 | 核心模块大改 |
| 2026-09-25 | `ad15a023` | lgg686 | User | feat(LBS): 新增LBS鬼王限时活动任务 | 已完整同步 | 适配风险 |
| 2026-09-25 | `19ae288c` | lgg686 | User | fix(DemonEncounter): 信件答题结束后补点获得奖励弹窗 | 已完整同步 | 可直接复用优化 |
| 2026-09-26 | `929c6a11` | pinkpig-Peppa | Enough1122 | fix(SwitchOnmyoji): give both switch_role loops a bounded exit | 已完整同步 | 可直接复用优化 |
| 2026-09-26 | `d5837031` | lgg686 | User | fix(DemonEncounter): 收缩灯笼点击区域并分离类型识别搜索区 | 已完整同步 | 可直接复用优化 |
| 2026-09-27 | `188dee7c` | lgg686 | User | feat(LBS): 新增开车模式（挣点赛博功德） 顺便还能搞点点赞(bushi 运行模式改为三选一枚举（单人挑战/组队匹配/开车模式）。 - 开车模式：创建公开房间，有人上车即退房重开，结束条件为开车次数或运行时间 - | 已完整同步 | 适配风险 |
| 2026-09-27 | `7c850c3c` | lgg686 | User | refactor(GeneralRoom): ensure 类方法移除硬编码阈值，改用资产自带阈值 | 已完整同步 | 可直接复用优化 |
| 2026-09-27 | `33c40a65` | lgg686 | User | refactor(GeneralInvite): click_fire 移除硬编码阈值，改用资产自带阈值 | 已完整同步 | 可直接复用优化 |
| 2026-09-27 | `d814b589` | lgg686 | xylolit-mu | 修复(委派)：补充领奖对话验证并更新出战识别资源 | 部分实现 | 核心模块大改 |
| 2026-09-27 | `e4935560` | lgg686 | xylolit-mu | 优化(式神活动)：门票选项为空时跳过门票爬塔 | 部分实现 | 可直接复用优化 |
| 2026-09-27 | `1cda0166` | lgg686 | xylolit-mu | 修复(悬赏封印)：秘闻结算后点击返回已知挑战界面 | 已完整同步 | 可直接复用优化 |
| 2026-09-27 | `f3f62f43` | lgg686 | xylolit-mu | 修复(逢魔之时)：确认弹窗关闭与首领识别并限制三轮召集尝试 | 部分实现 | 可直接复用优化 |
| 2026-09-27 | `0c3b971a` | lgg686 | xylolit-mu | 优化(重启)：支持配置异常重启容忍次数并优先执行恢复 | 部分实现 | 适配风险 |
| 2026-09-27 | `93cdaf2b` | lgg686 | xylolit-mu | 修复(登录)：调整进入游戏文字识别区域与关键词 | 部分实现 | 可直接复用优化 |
| 2026-09-27 | `1c646ce5` | lgg686 | xylolit-mu | 优化(通用战斗)：调整随机点击区域与风险档位 | 部分实现 | 可直接复用优化 |
| 2026-09-27 | `a1fb24a6` | lgg686 | User | fix(LBS): 开车模式等进房渲染完成后再等客 | 已完整同步 | 可直接复用优化 |
| 2026-09-27 | `f01a83f0` | lgg686 | User | fix(LBS): 修复挑战次数判断，登记调度优先级 | 已完整同步 | 适配风险 |
| 2026-09-28 | `b4168071` | lgg686 | xylolit-mu | 调整(对弈竞猜):更新十周年对弈竞猜相关素材，新增非等权策略。 | 已完整同步 | 适配风险 |
| 2026-09-29 | `d7d98690` | pinkpig-Peppa | neptine | fix(Exploration): Restore I_FLAG_2_ON ROI to unblock friend tab switching  #1844 | 部分实现 | 可直接复用优化 |
| 2026-09-29 | `1aacf5a5` | lgg686 | xylolit-mu | 调整(百鬼棋局):删除结算Scatter点击，回调至随机点击区域。 | 部分实现 | 适配风险 |
| 2026-09-29 | `fd46e065` | pinkpig-Peppa | Johnnylov | test(HeroTest): cover skill selection timeout fallback | 已完整同步 | 可直接复用优化 |
| 2026-09-30 | `885ea02c` | kongdr418 | kongdr | fix(Restart): 调整登录界面「进入游戏」OCR 识别区域 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `17474206` | kongdr418 | kongdr | fix(Login): 延长等待角色选择页的超时时间，避免登录卡死 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `03429729` | kongdr418 | kongdr | fix(GameUi): 下调庭院标志识别阈值，修复游戏更新后登录卡死 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `8f0ebc1c` | lgg686 | xylolit-mu | 优化(全局):调整默认庭院检查资源，新增登陆保底点击。 | 部分实现 | 核心模块大改 |
| 2026-09-30 | `48164d4e` | kongdr418 | kongdr | feat(FrogBoss): 适配十周年素材并新增非等权预测策略 frog_oas | 部分实现 | 适配风险 |
| 2026-09-30 | `9b3c9b67` | pinkpig-Peppa | xylolit-mu | 新增(对弈竞猜)：移植OAS胜率策略与赛果记录 | 已完整同步 | 核心模块大改 |
| 2026-09-30 | `86b2a7ef` | pinkpig-Peppa | xylolit-mu | 调整(对弈竞猜)：更新活动素材与识别区域 | 已完整同步 | 适配风险 |
| 2026-09-30 | `bcb27d7f` | lgg686 | xylolit-mu | 修复(对弈竞猜)：通过可见记录页补结算并启用胜率权重 | 部分实现 | 核心模块大改 |
| 2026-09-30 | `9d39f0c0` | lgg686 | xylolit-mu | 修复(庭院导航)：增加进入町中的保底点击 | 已完整同步 | 可直接复用优化 |
| 2026-09-30 | `f130ab3f` | lgg686 | xylolit-mu | 调整(图像点击)：统一Image规则为High并更新默认值 | 部分实现 | 适配风险 |
| 2026-09-30 | `8dcf5b59` | kongdr418 | kongdr | fix(FrogBoss): 全部图片规则阈值下调为 0.7 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `414d42df` | lgg686 | xylolit-mu | 调整(对弈竞猜):调整竞猜对应素材。 | 部分实现 | 适配风险 |
| 2026-09-30 | `fb06df05` | kongdr418 | kongdr | fix(FrogBoss): 重截 bet_failure 模板并修正 ROI | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `1f1fdbef` | lgg686 | xylolit-mu | 调整(对弈竞猜):调整竞猜对应素材。 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `27dc33a4` | kongdr418 | kongdr | fix(FrogBoss): 调整对弈竞猜策略逻辑 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `d0bc419a` | pinkpig-Peppa | User | feat(DesktopClient): 新增桌面客户端窗口后端（后台截图/窗口消息输入/PID 绑定） | 已完整同步 | 适配风险 |
| 2026-09-30 | `1bc92584` | lgg686 | User | feat(DesktopClient): 新增桌面客户端窗口后端（后台截图/窗口消息输入/PID 绑定） | 已完整同步 | 适配风险 |
| 2026-09-30 | `cafe832b` | pinkpig-Peppa | User | feat(DesktopClient): 设备层接入桌面模式（免 adb、无模拟器生命周期） | 已完整同步 | 适配风险 |
| 2026-09-30 | `fd812e53` | lgg686 | User | feat(DesktopClient): 设备层接入桌面模式（免 adb、无模拟器生命周期） | 部分实现 | 适配风险 |
| 2026-09-30 | `72d44a6b` | lgg686 | User | feat(Image): 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差 | 部分实现 | 适配风险 |
| 2026-09-30 | `0e7edcc8` | pinkpig-Peppa | User | feat(DesktopClient): Device 层桌面生命周期（DesktopDevice mixin） | 已完整同步 | 适配风险 |
| 2026-09-30 | `e2cdbe92` | lgg686 | User | feat(DesktopClient): Device 层桌面生命周期（DesktopDevice mixin） | 部分实现 | 适配风险 |
| 2026-09-30 | `3d85565f` | lgg686 | User | fix(Login): 桌面登录期处理 MPay 弹窗，避免误判未知页面 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `2a82f6da` | lgg686 | User | fix(Restart): 桌面客户端启动/登录失败时就地重试，避免无限重启循环 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `f80c3a6d` | pinkpig-Peppa | User | feat(Config): 桌面模式配置项与界面说明 | 已完整同步 | 适配风险 |
| 2026-09-30 | `60b09a8e` | lgg686 | User | feat(Config): 桌面模式配置项与界面说明 | 部分实现 | 适配风险 |
| 2026-09-30 | `7c5f380b` | pinkpig-Peppa | User | feat(Image): 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差 | 部分实现 | 可直接复用优化 |
| 2026-09-30 | `3252b071` | pinkpig-Peppa | User | fix(Login): 桌面登录期处理 MPay 弹窗，避免误判未知页面 | 已完整同步 | 可直接复用优化 |
| 2026-09-30 | `6ea67658` | pinkpig-Peppa | User | fix(Restart): 桌面客户端启动/登录失败时就地重试，避免无限重启循环 | 已完整同步 | 可直接复用优化 |
| 2026-09-30 | `40e4aa6f` | lgg686 | xylolit-mu | 修复(悬赏协作)：优先处理连续弹窗后恢复任务 | 已完整同步 | 可直接复用优化 |
| 2026-09-30 | `1ad34a78` | lgg686 | xylolit-mu | 修复(对弈竞猜)：无操作五秒时保底点击下一局 | 已完整同步 | 可直接复用优化 |
| 2026-09-30 | `16d1205d` | lgg686 | xylolit-mu | 修复(对弈竞猜)：更新失败结果识别素材 | 部分实现 | 可直接复用优化 |

### 2026-10（228 条）

| 日期 | 提交 | 来源 | 提交人 | 摘要 | 状态 | 类型 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-01 | `a8afe598` | lgg686 | xylolit-mu | 修复(闲庭导航)：优先识别闲庭并排除庭院误判 | 已完整同步 | 可直接复用优化 |
| 2026-10-01 | `1eb9fe3f` | lgg686 | xylolit-mu | 修复(对弈竞猜)：处理下一局后的休息状态并更新资源说明 | 已完整同步 | 可直接复用优化 |
| 2026-10-01 | `5f408cd4` | lgg686 | xylolit-mu | 修复(对弈竞猜)：优先处理下注弹窗并限制重复点击 | 已完整同步 | 可直接复用优化 |
| 2026-10-01 | `fcd496de` | kongdr418 | kongdr | fix(FrogBoss): 修正全员零权重时随机下注 | 部分实现 | 可直接复用优化 |
| 2026-10-01 | `98ce82bb` | pinkpig-Peppa | xylolit-mu | 调整(对弈竞猜)：同步记录页面与最新识别素材 | 已完整同步 | 适配风险 |
| 2026-10-01 | `670f194a` | pinkpig-Peppa | xylolit-mu | 修复(对弈竞猜)：移植记录补结算、下注恢复与负权重策略 | 已完整同步 | 核心模块大改 |
| 2026-10-01 | `e13fbc4a` | kongdr418 | kongdr | refactor(FrogBoss): 精简自检脚本注释 | 部分实现 | 可直接复用优化 |
| 2026-10-01 | `92223c5b` | pinkpig-Peppa | neptine | fix(GameUi): Restore I_CHECK_FRIENDS image and ROI for friend page detection | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `c426b982` | pinkpig-Peppa | neptine | fix(RichMan): Improve shrine shop purchase detection and retry handling | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `9ec6101e` | pinkpig-Peppa | neptine | fix(RichMan): Handle bulk purchase failures in special shop | 部分实现 | 可直接复用优化 |
| 2026-10-02 | `606517be` | pinkpig-Peppa | User | fix(GameUi): 适配庭院下移后的庭院标志识别区域 | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `62f488b3` | pinkpig-Peppa | User | fix(Dokan,FallenSun): replace removed I_BACK_BL with I_UI_BACK_BLUE | 部分实现 | 可直接复用优化 |
| 2026-10-02 | `af5fcf05` | pinkpig-Peppa | User | feat(Orochi): 改用 page_orochi 进行御魂页导航 | 已完整同步 | 核心模块大改 |
| 2026-10-02 | `7b522c94` | pinkpig-Peppa | User | refactor(EternitySea): 清理无用的导航包装与死代码 | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `a9cad51c` | lgg686 | xylolit-mu | 调整(对弈竞猜)：引入负向胜率权重 | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `431e3458` | lgg686 | xylolit-mu | 回退(页面导航)：移除町中固定位置点击保底 | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `3a2b74a3` | lgg686 | xylolit-mu | 修复(道馆)：退出战斗返回道馆后结束连战调用 | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `5a2d99bf` | lgg686 | xylolit-mu | 修复(对弈竞猜)：处理商店弹窗并二次确认任务结束 | 已完整同步 | 核心模块大改 |
| 2026-10-02 | `194a3eda` | pinkpig-Peppa | User | fix(DemonEncounter): 优化boss搜索容错、收缩灯笼点击区、补信件答谢 | 已完整同步 | 核心模块大改 |
| 2026-10-02 | `7738d5d5` | pinkpig-Peppa | User | fix(DemonEncounter): 挑战次数OCR改为DigitCounter 模式 | 已完整同步 | 可直接复用优化 |
| 2026-10-02 | `8753481b` | lgg686 | LGG686 | feat(image)：新增掩码模板匹配 | 已完整同步 | 适配风险 |
| 2026-10-02 | `cf6fa6a5` | lgg686 | LGG686 | fix(image)：拦截零方差模板并修正多尺度浮点漂移 | 已完整同步 | 适配风险 |
| 2026-10-03 | `5bc76c7e` | lgg686 | Hurry2 | feat(IbukiArena)：移植狭间幻境活动任务 | 已完整同步 | 适配风险 |
| 2026-10-03 | `1f230af2` | lgg686 | Hurry2 | feat(FrogChallenge)：移植青蛙瓷器挑战赛并重命名狭间幻境资产 | 已完整同步 | 适配风险 |
| 2026-10-03 | `c2390c2a` | lgg686 | Hurry2 | fix(IbukiArena)：修复挑战判定可能提前命中 exit_matcher | 已完整同步 | 可直接复用优化 |
| 2026-10-03 | `df3ff430` | lgg686 | Hurry2 | fix(WeeklyTrifles)：修正摸鱼行动御守数量读取与存储判断 | 已完整同步 | 可直接复用优化 |
| 2026-10-03 | `52608081` | pinkpig-Peppa | neptine | fix(GameUi): Restore touch fish page navigation - register the touch fish page in the shared page definitions  | 已完整同步 | 可直接复用优化 |
| 2026-10-03 | `1589899a` | pinkpig-Peppa | neptine | chore(workflow): Update automation workflows to gpt-6-luna | 部分实现 | 格式/文档 |
| 2026-10-03 | `08079eaf` | pinkpig-Peppa | neptine | feat(Costume): Add task-scoped battle scene skin support #1843 | 部分实现 | 适配风险 |
| 2026-10-03 | `c1dc5059` | pinkpig-Peppa | neptine | feat(Costume): Add Chinese names to costume switch logs | 部分实现 | 可直接复用优化 |
| 2026-10-03 | `4e32d985` | pinkpig-Peppa | User | feat(GeneralBattle): 支持按式神名点击绿标 | 已完整同步 | 适配风险 |
| 2026-10-03 | `78083db2` | pinkpig-Peppa | User | feat(OtherWorldTwilight): 新增御魂副本任务彼世逢魔 | 已完整同步 | 适配风险 |
| 2026-10-03 | `51582666` | pinkpig-Peppa | User | feat(image): 新增掩码模板匹配与多尺度方法分发 - 可用于处理受背景影响较大的模板，比如送的一整套周年庆庭院+主题的阴阳寮图标(暂未处理) - 新增 "Masked template matching"：掩码 | 已完整同步 | 适配风险 |
| 2026-10-03 | `f4767278` | pinkpig-Peppa | User | fix(server): annotator 静态资源加 Cache-Control no-cache | 已完整同步 | 适配风险 |
| 2026-10-03 | `1c0a01f2` | pinkpig-Peppa | User | fix(OtherWorldTwilight): 修复绿标默认值绕过与队长建房失败死循环 - OWTBattleConfig 重声明 green_mark_type 默认为 NAME，pydantic v2 默认值不触发 | 已完整同步 | 可直接复用优化 |
| 2026-10-04 | `5d89c37c` | kongdr418 | Hurry2 | feat(WantedQuests): 适配部分秘闻奖励结算后的一次性对话 | 部分实现 | 核心模块大改 |
| 2026-10-04 | `c1412496` | lgg686 | LGG686 | chore(image)：更新 DailyTrifles/FrogBoss 资产模板参数 | 部分实现 | 可直接复用优化 |
| 2026-10-04 | `afdc0318` | pinkpig-Peppa | neptine | fix(HeroTest): Attach HeroTest dynamic page edges to session page copies  #1861 | 已完整同步 | 可直接复用优化 |
| 2026-10-04 | `5bc3f6e2` | pinkpig-Peppa | neptine | fix(GeneralBattle): Support named green marks in battle wait | 已完整同步 | 可直接复用优化 |
| 2026-10-05 | `dd51be24` | lgg686 | LGG686 | fix(WantedQuests)：悬赏卡位小字叠背景导致 OCR 漏识时不重试 | 部分实现 | 可直接复用优化 |
| 2026-10-05 | `23ce874b` | lgg686 | LGG686 | fix(AutoCheckinBigGod)：手动UI简化，修复清理后游戏被二次重启与横竖屏状态未还原 | 部分实现 | 核心模块大改 |
| 2026-10-05 | `9ec93a44` | kongdr418 | kongdr | fix(FrogBoss): 修复下注确认被弹窗遮挡导致的死循环 | 已完整同步 | 可直接复用优化 |
| 2026-10-05 | `1c3accdf` | pinkpig-Peppa | User | feat(Navigator)：goto_page 到达判定支持 accepted_pages | 已完整同步 | 可直接复用优化 |
| 2026-10-05 | `c56e2c9b` | pinkpig-Peppa | User | feat(Exploration)：选关改为在主线 tab 下进行，新增 tab 页导航 | 已完整同步 | 核心模块大改 |
| 2026-10-05 | `f7db71b2` | pinkpig-Peppa | User | feat(TrueOrochi)：用玩法 tab 模块在场检测替代本地次数记账 | 完全缺失 | 核心模块大改 |
| 2026-10-05 | `1ff269b0` | lgg686 | LGG686 | fix(weekly_purchase)：修复皮肤券未购买 | 部分实现 | 核心模块大改 |
| 2026-10-06 | `dedfb11b` | pinkpig-Peppa | m123711 | fix(Delegation): 修正式神委派任务点击位置 | 已完整同步 | 可直接复用优化 |
| 2026-10-06 | `40fbf76a` | lgg686 | LGG686 | fix(demon_encounter)：修复逢魔重进地图 town↔rwt 死循环 | 部分实现 | 可直接复用优化 |
| 2026-10-06 | `4e4e9079` | pinkpig-Peppa | User | fix(DemonEncounter): 修正重进地图导航 | 已完整同步 | 可直接复用优化 |
| 2026-10-08 | `7b0da642` | lgg686 | LGG686 | fix(bondling)：删除漏邀分支，队员退回主界面即判房间销毁 | 部分实现 | 可直接复用优化 |
| 2026-10-09 | `44dd4659` | pinkpig-Peppa | neptine | fix(EvoZone): Expand lock button detection regions #1876 | 已完整同步 | 可直接复用优化 |
| 2026-10-09 | `f871f379` | pinkpig-Peppa | neptine | chore(workflow): Upgrade GitHub Agentic Workflow runtime | 部分实现 | 格式/文档 |
| 2026-10-09 | `a27a91fe` | pinkpig-Peppa | neptine | fix(workflow): Restore supported AI model pricing #1879 | 部分实现 | 格式/文档 |
| 2026-10-09 | `be8ae17c` | lgg686 | LGG686 | fix(image)：适配当期活动式神爬塔界面布局与导航 | 部分实现 | 核心模块大改 |
| 2026-10-09 | `990c4590` | pinkpig-Peppa | allesgutefy | fix: add missing run_task_or_default_general_battle function | 已完整同步 | 可直接复用优化 |
| 2026-10-09 | `a67309e7` | lgg686 | yuyuyuyuyu | refactor(assets): 清理冗余资产并将确认类调用收敛至通用模板 | 部分实现 | 适配风险 |
| 2026-10-09 | `55f51238` | pinkpig-Peppa | allesgutefy | fix: handle AttributeError for tasks without general_battle_config | 已完整同步 | 可直接复用优化 |
| 2026-10-09 | `251cb1cd` | pinkpig-Peppa | User | fix(Scheduler): ensure desktop client logged in before gameplay tasks | 已完整同步 | 适配风险 |
| 2026-10-09 | `ca7a4189` | pinkpig-Peppa | allesgutefy | fix: add 0.8s delay after clicking I_I_NO_DEFAULT to wait for UI update | 已完整同步 | 可直接复用优化 |
| 2026-10-10 | `100879bb` | kongdr418 | kongdr | fix(SwitchSoul): 重截切换确认弹窗按钮并修正ROI | 部分实现 | 可直接复用优化 |
| 2026-10-10 | `3c81120d` | kongdr418 | kongdr | fix(RealmRaid): 重截刷新确认按钮并调整ROI | 部分实现 | 可直接复用优化 |
| 2026-10-10 | `57fc173b` | kongdr418 | kongdr | fix(GeneralBattle): 重截退出战斗确认按钮并改用新素材 | 部分实现 | 可直接复用优化 |
| 2026-10-10 | `e68b0b74` | kongdr418 | kongdr | fix(GeneralBattle): 退出战斗确认按钮兼容新旧两套UI | 部分实现 | 可直接复用优化 |
| 2026-10-10 | `d43d8b56` | lgg686 | LGG686 | refactor(assets)：按钮类调用收敛至通用模板并清理废弃资产 | 部分实现 | 适配风险 |
| 2026-10-10 | `c4ce0ab1` | lgg686 | LGG686 | fix(image)：更新活动式神爬塔与通用邀请的资产模板及 ROI | 部分实现 | 适配风险 |
| 2026-10-10 | `2f503b4b` | lgg686 | LGG686 | fix(GeneralBattle)：重画 Act 结算页安全点击区域 | 部分实现 | 核心模块大改 |
| 2026-10-10 | `59657b71` | kongdr418 | kongdr418 | fix(GlobalGame): 通用确认按钮兼容新旧两套UI | 部分实现 | 核心模块大改 |
| 2026-10-10 | `7ad6278e` | kongdr418 | kongdr418 | fix(GlobalGame): 重截获得奖励素材并调整ROI | 部分实现 | 可直接复用优化 |
| 2026-10-10 | `e930e2e1` | pinkpig-Peppa | allesgutefy | fix: use interval=3 instead of sleep(0.8) per developer suggestion | 已完整同步 | 可直接复用优化 |
| 2026-10-10 | `8195cc60` | pinkpig-Peppa | allesgutefy | Revert "fix: use interval=3 instead of sleep(0.8) per developer suggestion" | 部分实现 | 可直接复用优化 |
| 2026-10-10 | `efd39e18` | pinkpig-Peppa | m123711 | fix(GlobalGame): 更新通用确认按钮素材 | 已完整同步 | 可直接复用优化 |
| 2026-10-10 | `a34240a5` | lgg686 | LGG686 | fix(device)：修复竖屏 splash 帧导致登录 OCR 崩溃 | 部分实现 | 适配风险 |
| 2026-10-10 | `fda09fde` | pinkpig-Peppa | neptine | fix(GlobalGame): Improve reward image matching and remove duplicate assets | 部分实现 | 核心模块大改 |
| 2026-10-10 | `5d546f0b` | pinkpig-Peppa | neptine | fix(GlobalGame): Preserve current and historical confirm/cancel button assets | 部分实现 | 核心模块大改 |
| 2026-10-10 | `cdde0e49` | pinkpig-Peppa | neptine | refactor(GlobalGame): Reuse shared confirm button for exit and refresh dialogs - replace task-specific confirm | 部分实现 | 核心模块大改 |
| 2026-10-10 | `71e33265` | pinkpig-Peppa | neptine | refactor(SwitchSoul): Reuse shared confirm button across costume flows - replace dedicated soul switch confirm | 部分实现 | 核心模块大改 |
| 2026-10-11 | `af6d1bcb` | pinkpig-Peppa | Vanity | fix(Exploration): 修复特定UP类型找怪提前退出及滑屏边缘检测问题 | 部分实现 | 可直接复用优化 |
| 2026-10-11 | `c8f93d1b` | pinkpig-Peppa | Vanity | fix(Exploration): address review feedback on timer reset and swipe edge check | 部分实现 | 可直接复用优化 |
| 2026-10-11 | `b3d6fe98` | pinkpig-Peppa | neptine | fix(ActivityShikigami): Update | 部分实现 | 核心模块大改 |
| 2026-10-11 | `4f0a4856` | pinkpig-Peppa | m123711 | fix(MemoryScrolls): 用最大按钮代替滑动并限制捐献轮数 | 已完整同步 | 可直接复用优化 |
| 2026-10-11 | `2bc21f59` | pinkpig-Peppa | Vanity | refactor(Exploration): 根据Review建议抽取滑屏与重置辅助方法，消除重复代码 | 部分实现 | 可直接复用优化 |
| 2026-10-11 | `84eda193` | pinkpig-Peppa | neptine | fix(GeneralInvite): Use shared UI assets for invite confirmation #1915 - replace invite-specific checkbox, can | 部分实现 | 核心模块大改 |
| 2026-10-11 | `27241886` | pinkpig-Peppa | neptine | fix(GeneralBattle): Avoid reward popup during completion fallback #1913 | 部分实现 | 可直接复用优化 |
| 2026-10-11 | `43c7f334` | pinkpig-Peppa | neptine | fix(ActivityShikigami): Broaden pass screen detection area | 部分实现 | 可直接复用优化 |
| 2026-10-11 | `9ce0fd2f` | pinkpig-Peppa | neptine | fix(GameUi): Add circular back button to unknown page recovery | 已完整同步 | 可直接复用优化 |
| 2026-10-11 | `7f0728bf` | pinkpig-Peppa | davidyangkunlong | 点击御魂溢出的提示 | 已完整同步 | 可直接复用优化 |
| 2026-10-11 | `a9eb4843` | kongdr418 | kongdr | fix(GameUi): 修复导航交替换路时空转不报错 | 已完整同步 | 可直接复用优化 |
| 2026-10-11 | `69a0fc4f` | pinkpig-Peppa | Vanity | perf(Exploration): 按UP类型自适应滑屏找怪策略与死代码精简 | 部分实现 | 可直接复用优化 |
| 2026-10-11 | `d638c11f` | pinkpig-Peppa | Enough1122 | fix(Duel): detect MVP share page via share-button image rule | 部分实现 | 核心模块大改 |
| 2026-10-12 | `2f5c306e` | pinkpig-Peppa | llBai | fix(invite_friends)：sleep(3) before invite_friend | 部分实现 | 可直接复用优化 |
| 2026-10-12 | `aaac78b3` | pinkpig-Peppa | llBai | change(open_expect_level): reverse swipe | 已完整同步 | 可直接复用优化 |
| 2026-10-12 | `f7302af2` | lgg686 | LGG686 | fix(weekly_purchase)：海汐御魂开启自动选择时一次买完 | 部分实现 | 可直接复用优化 |
| 2026-10-12 | `f0c8473d` | lgg686 | LGG686 | fix(WantedQuests)：2x 重扫未命中进度时放宽检测框阈值再扫一次 | 部分实现 | 可直接复用优化 |
| 2026-10-12 | `ba0d49b7` | lgg686 | LGG686 | fix(bondling)：调整建房逻辑，调整补邀时间间隔 | 部分实现 | 可直接复用优化 |
| 2026-10-12 | `372ef8f3` | pinkpig-Peppa | llBai | add S_SWIPE_LEVEL_DOWN_PRO | 已完整同步 | 可直接复用优化 |
| 2026-10-12 | `e8df3ae0` | pinkpig-Peppa | allesgutefy | fix: update interval=3 for I_UI_UNCHECK and I_UI_CONFIRM in check_and_invite | 已完整同步 | 可直接复用优化 |
| 2026-10-12 | `916e6eb8` | pinkpig-Peppa | allesgutefy | fix: update ui_ui_check and ui_ui_uncheck assets for new UI | 已完整同步 | 可直接复用优化 |
| 2026-10-12 | `5cf103ea` | lgg686 | LGG686 | feat(activity)：适配当期爬塔分家布局并统一挑战按钮为 OCR 引导 | 部分实现 | 核心模块大改 |
| 2026-10-12 | `d6c42bee` | pinkpig-Peppa | neptine | fix(GeneralBattle): Log battle start in strategy-based wait | 部分实现 | 可直接复用优化 |
| 2026-10-13 | `5b556e92` | pinkpig-Peppa | neptine | fix(Restart): Reuse global UI assets for login and mail dialogs - replace login cancel and mail confirmation a | 已完整同步 | 核心模块大改 |
| 2026-10-13 | `92578cd0` | pinkpig-Peppa | neptine | fix(Exploration): Correct realm raid ticket OCR region #1926 | 已完整同步 | 可直接复用优化 |
| 2026-10-13 | `54803c50` | pinkpig-Peppa | llBai | delete  S_SWIPE_LEVEL_DOWN_PRO | 已完整同步 | 可直接复用优化 |
| 2026-10-13 | `614b6b84` | pinkpig-Peppa | llBai | Revert "delete  S_SWIPE_LEVEL_DOWN_PRO" | 部分实现 | 可直接复用优化 |
| 2026-10-13 | `e56482ca` | pinkpig-Peppa | llBai | Revert "add S_SWIPE_LEVEL_DOWN_PRO" | 部分实现 | 可直接复用优化 |
| 2026-10-13 | `55b7d957` | pinkpig-Peppa | Hurry2 | fix(WeeklyTrifles):修复每周琐事摸鱼行动问题 | 已完整同步 | 可直接复用优化 |
| 2026-10-13 | `bedff718` | pinkpig-Peppa | Enough1122 | fix(Duel): 开战前等待增加超时与点击上限 | 已完整同步 | 可直接复用优化 |
| 2026-10-13 | `985ac267` | pinkpig-Peppa | Enough1122 | refactor(Duel): reuse ui_click for pre-battle setup wait | 已完整同步 | 可直接复用优化 |
| 2026-10-14 | `5770f91e` | pinkpig-Peppa | huangrunheng | Refactor script_task.py by cleaning up comments | 已完整同步 | 可直接复用优化 |
| 2026-10-14 | `0311c189` | lgg686 | LGG686 | fix(GameUi)：补充种树关闭按钮，调整未知页关闭动作顺序 | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `60117f17` | pinkpig-Peppa | davidyangkunlong | 处理御魂溢出 | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `1eeee5ff` | kongdr418 | kongdr | fix(WantedQuests): 下调秘闻剧情对话模板阈值 | 部分实现 | 可直接复用优化 |
| 2026-10-15 | `84366fc5` | pinkpig-Peppa | kunkun008 | fix(Delegation): avoid jade confirm misclick and back-button dead loop | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `9afe3d32` | pinkpig-Peppa | neptine | fix(WantedQuests): Detect selected friends when inviting #1939 | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `7e506bc3` | pinkpig-Peppa | neptine | fix(BaseTask): Skip task name mismatch validation | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `43c84c88` | pinkpig-Peppa | neptine | fix(GeneralBattle): Close buff panel and start battle preparation | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `c2023476` | pinkpig-Peppa | neptine | fix(GeneralBattle): Close buff panel and start battle preparation | 已完整同步 | 可直接复用优化 |
| 2026-10-15 | `911e996d` | pinkpig-Peppa | neptine | fix(workflow): Correct auto-merge schedule comment | 已完整同步 | 格式/文档 |
| 2026-10-15 | `d8677dc0` | pinkpig-Peppa | neptine | Revert "fix(GeneralBattle): Close buff panel and start battle preparation" | 已完整同步 | 可直接复用优化 |
| 2026-10-16 | `802643de` | kongdr418 | kongdr | feat(DailyTrifles): 新增每日收益统计 | 已完整同步 | 适配风险 |
| 2026-10-16 | `97575ca7` | kongdr418 | kongdr | refactor(DailyTrifles): 每日收益改为从日志读取 | 已完整同步 | 可直接复用优化 |
| 2026-10-16 | `a0fe1e8d` | kongdr418 | kongdr | feat(DailyTrifles): 新增每日收益查询接口 | 已完整同步 | 适配风险 |
| 2026-10-16 | `f3c61ba4` | kongdr418 | kongdr | feat(DailyTrifles): 收益快照另存日汇总，突破日志 7 天限制 | 已完整同步 | 可直接复用优化 |
| 2026-10-16 | `e6b00fbe` | kongdr418 | kongdr | feat(DailyTrifles): 收益支持历史查询与按天删除 | 已完整同步 | 适配风险 |
| 2026-10-16 | `83377a19` | kongdr418 | kongdr | fix(DailyTrifles): 修复统计每日收益缺少分组常量导致的 NameError | 已完整同步 | 可直接复用优化 |
| 2026-10-16 | `cc131ec5` | lgg686 | LGG686 | fix(WantedQuests)：悬赏去重集合改为按卡清零 | 部分实现 | 可直接复用优化 |
| 2026-10-17 | `9f07623b` | kongdr418 | kongdr | feat(Server): 新增模拟器画面截取接口 | 已完整同步 | 适配风险 |
| 2026-10-17 | `89e3ad09` | kongdr418 | kongdr | fix(Server): 画面截图改用 adb 直抓，不再干扰运行中的任务 | 部分实现 | 适配风险 |
| 2026-10-17 | `1d990fce` | pinkpig-Peppa | LGG686 | feat(script)：桌面客户端独立配置组与多开账号隔离 | 已完整同步 | 适配风险 |
| 2026-10-17 | `d97598d6` | lgg686 | LGG686 | feat(script)：桌面客户端独立配置组与多开账号隔离 | 部分实现 | 适配风险 |
| 2026-10-18 | `65c5b127` | kongdr418 | kongdr | fix(Deploy): 默认仓库指向本仓库 mine 分支 | 部分实现 | 可直接复用优化 |
| 2026-10-18 | `b9f33b8b` | kongdr418 | kongdr | feat(doc): 新增变更日志 | 部分实现 | 格式/文档 |
| 2026-10-18 | `a192e085` | kongdr418 | kongdr | chore(doc): 删除变更日志 | 部分实现 | 格式/文档 |
| 2026-10-19 | `252c6701` | lgg686 | LGG686 | fix(demon_encounter)：调整enter_boss逻辑，增加次数复检 | 部分实现 | 可直接复用优化 |
| 2026-10-19 | `107e9542` | pinkpig-Peppa | neptine | fix(Exploration): Prevent premature back navigation during exit #1935 | 已完整同步 | 可直接复用优化 |
| 2026-10-19 | `a70757b1` | pinkpig-Peppa | neptine | fix(Exploration): Prevent premature back navigation during exit #1935 | 部分实现 | 可直接复用优化 |
| 2026-10-19 | `b1c7186c` | pinkpig-Peppa | neptine | fix(GeneralInvite): Update invite confirmation ROI for wanted quests #1939 | 已完整同步 | 可直接复用优化 |
| 2026-10-20 | `77bd7fd7` | pinkpig-Peppa | weirj2016-ai | fix(Restart): 延长邮件领取确认等待时间 | 部分实现 | 可直接复用优化 |
| 2026-10-20 | `fe98ffef` | pinkpig-Peppa | davidyangkunlong | UpdateClimbBossResources | 部分实现 | 可直接复用优化 |
| 2026-10-20 | `6084f210` | lgg686 | LGG686 | fix(ActivityShikigami)：爬塔挑战遇弹窗改为关闭后重试 | 部分实现 | 可直接复用优化 |
| 2026-10-21 | `6029ad08` | kongdr418 | kongdr | feat(Chess): 移植新版百鬼棋局（含帧规则与识别能力） | 部分实现 | 适配风险 |
| 2026-10-21 | `4c5d633a` | kongdr418 | kongdr | feat(Chess): 同步百鬼投掷、黄金复制术与平安京阵容 | 部分实现 | 核心模块大改 |
| 2026-10-21 | `acbdbf1c` | kongdr418 | kongdr | fix(Chess): 加宽鼬乐币 OCR 区域，修复刷满不停止 | 部分实现 | 可直接复用优化 |
| 2026-10-21 | `73cf2c63` | kongdr418 | kongdr | fix(base_task): 补 clock_time 导入，修复百鬼棋局 set_next_run_next_monday 报 NameError | 部分实现 | 可直接复用优化 |
| 2026-10-21 | `1410590f` | kongdr418 | kongdr | fix(Chess): 清理商店槽位点击记录，修复买卡触发 GameTooManyClickError | 已完整同步 | 可直接复用优化 |
| 2026-10-21 | `ce9903bf` | kongdr418 | xylolit-mu | fix(Chess): 手牌满且无可操作时出售一张阵容卡腾位 | 已完整同步 | 可直接复用优化 |
| 2026-10-21 | `74425d03` | kongdr418 | xylolit-mu | fix(Chess): 同步上游百鬼主动投掷与特殊回合识别修复 | 部分实现 | 适配风险 |
| 2026-10-21 | `45b5772d` | kongdr418 | xylolit-mu | fix(Chess): 百鬼无需御魂时等全员解锁后随机投掷 | 部分实现 | 可直接复用优化 |
| 2026-10-21 | `92bb2f2e` | lgg686 | LGG686 | feat(core)：引入 RuleFrame 识别与灰度匹配，支持网络异常恢复 | 部分实现 | 适配风险 |
| 2026-10-21 | `f67e5a80` | lgg686 | LGG686 | fix(task)：Delegation、RyouToppa、FallenSun、FrogBoss 同步上游修复 | 部分实现 | 核心模块大改 |
| 2026-10-21 | `40e2f527` | lgg686 | LGG686 | feat(chess)：同步上游百鬼棋局实现 | 部分实现 | 适配风险 |
| 2026-10-21 | `f339b5a6` | lgg686 | LGG686 | feat(ActivityShikigami)：适配 OASX v0.3.16 式神活动配置契约 | 部分实现 | 适配风险 |
| 2026-10-21 | `fa7a87e7` | kongdr418 | kongdr | fix(Chess): 买卡前清理槽位点击记录，修复 GameTooManyClickError | 已完整同步 | 可直接复用优化 |
| 2026-10-22 | `476617e0` | lgg686 | LGG686 | fix(GameUi)：删除与 GeneralBuff 重名的 I_CLOSE_RED | 已完整同步 | 适配风险 |
| 2026-10-22 | `4354df46` | pinkpig-Peppa | weirj2016-ai | fix(Dokan): correct dojo leader name template | 已完整同步 | 可直接复用优化 |
| 2026-10-22 | `8bbf87b8` | pinkpig-Peppa | weirj2016-ai | fix(Dokan): lower leader template threshold | 已完整同步 | 可直接复用优化 |
| 2026-10-23 | `76490d67` | kongdr418 | kongdr418 | fix(GuildBanquet): 兼容第二种寮宴会旗帜并修复加成开关资产重名 | 部分实现 | 适配风险 |
| 2026-10-23 | `8f945012` | kongdr418 | kongdr418 | fix(Chess): 买卡成功与商店换卡后清理格子点击记录 | 已完整同步 | 可直接复用优化 |
| 2026-10-23 | `9df707fb` | kongdr418 | kongdr418 | fix(Chess): 限制每轮买卡点击次数，重试失败后取消购买 | 已完整同步 | 可直接复用优化 |
| 2026-10-24 | `120c881a` | pinkpig-Peppa | kunkun008 | fix(MysteryShop): 蓝票多数量购买窗口改用 buy_more | 部分实现 | 可直接复用优化 |
| 2026-10-24 | `be5f3c97` | pinkpig-Peppa | kunkun008 | fix(MysteryShop): 蓝票按单价判断，高于 85 勾玉不买 | 已完整同步 | 核心模块大改 |
| 2026-10-24 | `47b9064b` | pinkpig-Peppa | kunkun008 | fix(MysteryShop): 蓝票余额不够买满时逐张购买 | 已完整同步 | 可直接复用优化 |
| 2026-10-24 | `85632077` | pinkpig-Peppa | neptine | fix(AreaBoss): Handle fox battle scene settlement #1967 | 部分实现 | 适配风险 |
| 2026-10-24 | `6360d6a9` | pinkpig-Peppa | weirj2016-ai | 修复道馆首次攻击后的任务间隔 | 已完整同步 | 可直接复用优化 |
| 2026-10-24 | `cacc2af3` | pinkpig-Peppa | davidyangkunlong | 御魂溢出处理升级 | 部分实现 | 可直接复用优化 |
| 2026-10-25 | `14cbd413` | kongdr418 | kongdr | feat(GeneralInvite): 同步上游邀请组件，适配新界面并等待好友列表加载 | 部分实现 | 核心模块大改 |
| 2026-10-25 | `8d64b1e4` | lgg686 | LGG686 | fix(chess)：购买点击加单轮上限并在成功后清理记录 | 部分实现 | 可直接复用优化 |
| 2026-10-25 | `cc83b1a2` | lgg686 | LGG686 | fix(GuildBanquet)：调整集结标志识别区并同步资产参数顺序 | 部分实现 | 可直接复用优化 |
| 2026-10-25 | `82fae57e` | lgg686 | LGG686 | fix(WantedQuests)：悬赏目标改用子串匹配避漏判 | 部分实现 | 可直接复用优化 |
| 2026-10-25 | `d38f6e95` | lgg686 | LGG686 | fix(AbyssShadows)：确认按钮改用通用资产 I_UI_CONFIRM | 已完整同步 | 适配风险 |
| 2026-10-25 | `09c1802d` | lgg686 | xylolit-mu | 新增棋局阵容编辑工具与JSON配置，完善站位检测及任务协同 | 部分实现 | 适配风险 |
| 2026-10-25 | `094b30b9` | kongdr418 | kongdr | fix(base_task): wait_until_disappear 支持 timeout 参数，修复邀请组件报错 | 已完整同步 | 可直接复用优化 |
| 2026-10-26 | `31484b10` | kongdr418 | kongdr | feat(Chess): 同步上游阵容编辑器与 JSON 配置，斗技补充 ban 检测 | 部分实现 | 适配风险 |
| 2026-10-26 | `a9597e77` | kongdr418 | kongdr | fix(Chess): 卖卡与上御魂前清理点击记录，修复 GameTooManyClickError | 已完整同步 | 可直接复用优化 |
| 2026-10-27 | `0b7ee83e` | lgg686 | LGG686 | feat(ActivityShikigami)：探索新增委派模式并重裁活动识别模板 | 部分实现 | 核心模块大改 |
| 2026-10-27 | `b37b56d2` | lgg686 | LGG686 | fix(WantedQuests)：适配新 UI 的悬赏封印界面 | 部分实现 | 核心模块大改 |
| 2026-10-28 | `c4d40686` | kongdr418 | kongdr | fix(WantedQuests): 适配封印悬赏新UI，更新追踪按钮图标与坐标并补协作弹窗新图标 | 部分实现 | 核心模块大改 |
| 2026-10-28 | `7b8155d9` | kongdr418 | kongdr | fix(WantedQuests): 重截前往按钮图标，适配悬赏列表新布局 | 部分实现 | 核心模块大改 |
| 2026-10-28 | `c3a88af9` | kongdr418 | kongdr | fix(WantedQuests): 详情页改用前往按钮判断，修复新UI下无法进入悬赏详情 | 部分实现 | 可直接复用优化 |
| 2026-10-28 | `ac482cf2` | kongdr418 | kongdr | fix(WantedQuests): 调整悬赏列表 OCR 区域，适配新UI排版 | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `d296406e` | lgg686 | LGG686 | fix(WantedQuests)：适配新版界面神秘悬赏跳过并合并重复追踪资产 | 部分实现 | 适配风险 |
| 2026-10-28 | `329ecfc7` | pinkpig-Peppa | weirj2016-ai | 修复永生之海队员锁定阵容检查 | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `c695e50d` | kongdr418 | kongdr418 | fix(WantedQuests): 识别神秘妖怪悬赏后关闭面板并跳过 | 部分实现 | 核心模块大改 |
| 2026-10-28 | `57c3f701` | kongdr418 | kongdr418 | fix(GlobalGame): 放宽协作图标识别区域 | 部分实现 | 可直接复用优化 |
| 2026-10-28 | `9a6eb783` | kongdr418 | kongdr418 | fix(WantedQuests): 修复取消追踪卡死与数量识别 | 部分实现 | 可直接复用优化 |
| 2026-10-28 | `91010725` | kongdr418 | kongdr418 | fix(GlobalGame): 放宽忽略按钮识别区域 | 部分实现 | 可直接复用优化 |
| 2026-10-28 | `2db22cc3` | pinkpig-Peppa | User | fix(RichMan): 海汐御魂开启自动选择时一次买完 | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `e68c2d26` | pinkpig-Peppa | User | fix(GlobalGame): 适配接受/拒绝按钮新 UI | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `921a2b82` | pinkpig-Peppa | User | fix(WantedQuests): 适配悬赏封印新 UI 并清理孤立资产 | 已完整同步 | 适配风险 |
| 2026-10-28 | `3f085151` | pinkpig-Peppa | weirj2016-ai | 道馆任务每次运行尝试开启道馆 | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `506564c6` | pinkpig-Peppa | neptine | fix(Costume): Refresh cached template image when replacing costume assets  #1972 | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `1e18c251` | pinkpig-Peppa | weirj2016-ai | 道馆开启尝试移出查找循环 | 已完整同步 | 可直接复用优化 |
| 2026-10-28 | `d1ad2c09` | kongdr418 | kongdr | fix(Chess): 调整棋局规则搜索范围 | 已完整同步 | 可直接复用优化 |
| 2026-10-29 | `1f5149f3` | kongdr418 | kongdr | fix(screen): 截图前自动重连 adb，避免设备掉线导致截图失败 | 部分实现 | 适配风险 |
| 2026-10-29 | `91f7d916` | kongdr418 | kongdr | feat(annotator): 目录下拉显示任务中文名，中文名取自 OASX | 已完整同步 | 适配风险 |
| 2026-10-29 | `eddc6171` | pinkpig-Peppa | leovefy | fix(GameUi): 兼容商店两种招牌图片，修复反复进出商店的问题 | 部分实现 | 核心模块大改 |
| 2026-10-29 | `ce0e78d6` | kongdr418 | kongdr | fix(Delegation): 「完成」改用独立点击区，规避游戏对文字正中点击不响应 | 已完整同步 | 可直接复用优化 |
| 2026-10-29 | `4b823fde` | pinkpig-Peppa | 微凉徒眸 | fix(GeneralInvite): use interval=3 for I_UI_UNCHECK in invite_again | 已完整同步 | 可直接复用优化 |
| 2026-10-29 | `ba699f87` | pinkpig-Peppa | Msrtria | feat(Costume): 新增幕间主题梦隙闲花 | 部分实现 | 适配风险 |
| 2026-10-30 | `bf889f02` | pinkpig-Peppa | weirj2016-ai | fix: recognize Flower Pass task tab before claiming | 已完整同步 | 可直接复用优化 |
| 2026-10-30 | `287d59f0` | kongdr418 | kongdr | feat(DraftDuel): 新增协同对弈任务骨架与大厅消耗识别 | 完全缺失 | 适配风险 |
| 2026-10-30 | `1012030e` | kongdr418 | kongdr | feat(DraftDuel): 接入邀请好友与队长/队员模式 | 完全缺失 | 适配风险 |
| 2026-10-30 | `65a3ebfb` | kongdr418 | kongdr | fix(DraftDuel): 修正金币消耗识别范围 | 完全缺失 | 可直接复用优化 |
| 2026-10-30 | `c78b436f` | kongdr418 | kongdr | fix(DraftDuel): 免费次数按关键字识别 | 完全缺失 | 可直接复用优化 |
| 2026-10-30 | `05fca68a` | lgg686 | LGG686 | feat(task)：鼬商店OCR识别礼盒购买，委派完成判定改模板点任务卡，阵容工坊卡图缓存穿透 | 已完整同步 | 适配风险 |
| 2026-10-30 | `fe1c0881` | kongdr418 | kongdr | feat(DraftDuel): 组队后点「战」进入选式神 | 完全缺失 | 适配风险 |
| 2026-10-30 | `cf9fe93c` | kongdr418 | kongdr | feat(annotator): 上传支持选择文件夹 | 已完整同步 | 适配风险 |
| 2026-10-30 | `613a32d0` | kongdr418 | kongdr | feat(DraftDuel): 接入选式神与推荐选择 | 完全缺失 | 核心模块大改 |
| 2026-10-30 | `8e483e5c` | kongdr418 | kongdr | fix(DraftDuel): 队员接受邀请后保持等待 | 完全缺失 | 可直接复用优化 |
| 2026-10-30 | `2013a89d` | kongdr418 | kongdr | feat(DraftDuel): 队员接入选式神 | 完全缺失 | 可直接复用优化 |
| 2026-10-30 | `5da8bbb5` | kongdr418 | kongdr | fix(DraftDuel): 推荐检查窗口延长到15秒 | 完全缺失 | 可直接复用优化 |
| 2026-10-30 | `d1de2080` | lgg686 | LGG686 | refactor(Login)：登录界面按钮改用通用UI资产并新增引擎更新跳过 | 部分实现 | 适配风险 |
| 2026-10-30 | `5dd027bf` | kongdr418 | kongdr | feat(DraftDuel): 记录选中的式神并兼容自动选 | 完全缺失 | 可直接复用优化 |
| 2026-10-30 | `aa91067c` | lgg686 | LGG686 | fix(AbyssShadows)：修复狭间暗域战斗瞬间结算导致 attack_enemy 卡死 | 部分实现 | 可直接复用优化 |
| 2026-10-30 | `b68f1a68` | kongdr418 | kongdr | feat(annotator): 支持用协同 v6 模型测试 OCR | 部分实现 | 适配风险 |
| 2026-10-30 | `11ab2343` | kongdr418 | kongdr | feat(DraftDuel): 任务内使用 PP-OCRv6-small 识别 | 完全缺失 | 核心模块大改 |
| 2026-10-30 | `1f7b10b1` | kongdr418 | kongdr | feat(DraftDuel): 接入选卡策略与五轮选人 | 完全缺失 | 核心模块大改 |
| 2026-10-30 | `d06d9225` | pinkpig-Peppa | Hurry2 | feat(Restart):桌面版支持杀进程重启，用于挽救卡死的未知界面 | 部分实现 | 适配风险 |
| 2026-10-30 | `31a853a9` | kongdr418 | kongdr | fix(GlobalGame): 协作邀请改用新UI图标识别 | 部分实现 | 可直接复用优化 |
| 2026-10-30 | `8d499033` | pinkpig-Peppa | weirj2016-ai | fix(GlobalGame): 更新协作邀请识别素材与坐标 | 已完整同步 | 适配风险 |
| 2026-10-31 | `48ba3280` | lgg686 | LGG686 | fix(ActivityShikigami)：探索剧情结束改为奖励面板或主界面二者其一 | 部分实现 | 可直接复用优化 |
| 2026-10-31 | `9073e4d1` | lgg686 | LGG686 | feat(Device)：桌面客户端登录与重启解耦 | 部分实现 | 适配风险 |
| 2026-10-31 | `92d2dbd8` | pinkpig-Peppa | Hurry2 | feat(desktop_device):适配桌面版空闲策略关闭游戏 | 部分实现 | 适配风险 |
| 2026-10-31 | `5001c0bc` | lgg686 | xylolit-mu | feat(Chess)：同步百鬼棋局策略、资源与标注器改动，Device 新增按住拖动 | 部分实现 | 适配风险 |
| 2026-10-31 | `a57891b8` | pinkpig-Peppa | Hurry2 | fix(script):修复桌面版关闭游戏后重启 | 部分实现 | 适配风险 |
| 2026-10-31 | `8b4dc669` | pinkpig-Peppa | neptine | fix(FindJade): Add task to scheduler priority list #1979 | 已完整同步 | 适配风险 |
| 2026-10-31 | `dac21615` | lgg686 | xylolit-mu | feat(DraftDuel)：新增协同对弈任务与双实例协同框架 | 完全缺失 | 适配风险 |
| 2026-10-31 | `371bdb89` | lgg686 | LGG686 | feat(Device)：press_and_drag 支持 window_message 通道 | 部分实现 | 适配风险 |
| 2026-10-31 | `d3e81d3a` | kongdr418 | kongdr | feat(Chess): 同步新版百鬼棋局 | 部分实现 | 适配风险 |

### 2026-11（161 条）

| 日期 | 提交 | 来源 | 提交人 | 摘要 | 状态 | 类型 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-01 | `c08fe24f` | pinkpig-Peppa | weirj2016-ai | fix(TalismanPass): update task tab template and ROI | 已完整同步 | 可直接复用优化 |
| 2026-11-01 | `b46be8a6` | pinkpig-Peppa | Ghostuel | feat: support Xinyu Mingxiao scroll and shared masked guild entrance | 部分实现 | 适配风险 |
| 2026-11-01 | `cfcdad39` | pinkpig-Peppa | Ghostuel | feat: support Yuehai Youxing realm with shared template search regions | 部分实现 | 适配风险 |
| 2026-11-01 | `2d7b85de` | pinkpig-Peppa | Ghostuel | fix: resolve theme log translation and strengthen invalid-theme regression tests | 部分实现 | 可直接复用优化 |
| 2026-11-01 | `ab2b0c00` | pinkpig-Peppa | Ghostuel | fix: update manual realm tool enum and add offline regression check | 部分实现 | 可直接复用优化 |
| 2026-11-01 | `5a8f7385` | kongdr418 | kongdr | feat(Chess): OCR 接入 v6-small | 部分实现 | 核心模块大改 |
| 2026-11-01 | `19e5a562` | kongdr418 | kongdr | fix(DraftDuel): V6 解码补空格类 | 完全缺失 | 可直接复用优化 |
| 2026-11-01 | `fc6b5070` | lgg686 | LGG686 | fix(DraftDuel)：清理大轮结算浮窗并正确回到下一大轮 | 完全缺失 | 核心模块大改 |
| 2026-11-01 | `a12c4e42` | lgg686 | xylolit-mu | 修复协斗识别与上阵、MuMu启动及棋局羁绊，完善契灵身份交换 | 完全缺失 | 适配风险 |
| 2026-11-01 | `d06f9672` | kongdr418 | kongdr418 | feat(DraftDuel): 整合协同选人、上阵及双端自动上阵流程 | 完全缺失 | 适配风险 |
| 2026-11-01 | `0aba58d5` | lgg686 | xylolit-mu | fix(DraftDuel): 校准式神头像裁切、缩放与阈值序列 | 完全缺失 | 核心模块大改 |
| 2026-11-01 | `68fe3245` | lgg686 | xylolit-mu | fix(DesktopClient)：补齐桌面客户端加固，修复 PID 复用误杀与多开竞态 | 部分实现 | 适配风险 |
| 2026-11-01 | `f428bbec` | kongdr418 | kongdr418 | feat(DraftDuel): 添加队友推荐开关并拆分任务运行模块 | 完全缺失 | 适配风险 |
| 2026-11-01 | `ea6b92f9` | pinkpig-Peppa | leovefy | fix(SixRealms): 限制选岛连续点击并增加超时退出 | 部分实现 | 可直接复用优化 |
| 2026-11-02 | `bd2acfa3` | lgg686 | xylolit-mu | fix(draft-duel): 按五张手牌中段验证上阵并限制开放时段 | 完全缺失 | 核心模块大改 |
| 2026-11-02 | `b08d8e2a` | lgg686 | xylolit-mu | fix(draft-duel): 稳定采集手牌并在首局后释放模板 | 完全缺失 | 核心模块大改 |
| 2026-11-02 | `a1a73b85` | kongdr418 | kongdr418 | fix(DraftDuel): 优化大厅头像匹配与上阵识别 | 完全缺失 | 核心模块大改 |
| 2026-11-02 | `2ccacdee` | kongdr418 | kongdr418 | fix(DraftDuel): 补齐头像识别规则源与资源生成流程 | 完全缺失 | 核心模块大改 |
| 2026-11-02 | `b491ac7a` | lgg686 | xylolit-mu | fix(draft-duel): 按倒计时采集手牌并区分工作日开放时间 | 完全缺失 | 可直接复用优化 |
| 2026-11-02 | `e0ea96ae` | lgg686 | xylolit-mu | fix(draft-duel): 补测低阈值并回查未验证上阵槽位 | 完全缺失 | 可直接复用优化 |
| 2026-11-02 | `88e71d47` | kongdr418 | kongdr418 | fix(DraftDuel): 重拖时逐次上移起点与终点 | 完全缺失 | 可直接复用优化 |
| 2026-11-02 | `df43725c` | lgg686 | LGG686 | fix(ActivityShikigami)：重写探索剧情跳过流程，更新委派入口模板 | 部分实现 | 适配风险 |
| 2026-11-02 | `6466034f` | kongdr418 | kongdr418 | fix(DraftDuel): 取消队友就绪等待并在首局后等待三秒 | 完全缺失 | 可直接复用优化 |
| 2026-11-02 | `255b2b25` | kongdr418 | kongdr418 | feat(DraftDuel): 完善离队结算与自动上阵判定 | 完全缺失 | 适配风险 |
| 2026-11-02 | `7bfb6fa3` | kongdr418 | kongdr418 | fix(DraftDuel): 区分新大轮大厅与待匹配页 | 完全缺失 | 可直接复用优化 |
| 2026-11-02 | `37049935` | lgg686 | xylolit-mu | fix(draft-duel): 保留自动上阵名单并持久化本地加权数据 | 完全缺失 | 核心模块大改 |
| 2026-11-02 | `cd7b6045` | lgg686 | xylolit-mu | fix: 完善协斗大轮切换和棋局结算恢复 | 完全缺失 | 核心模块大改 |
| 2026-11-02 | `180d238a` | lgg686 | xylolit-mu | fix(draft-duel): 清理大厅结算遮罩并重试邀请 | 完全缺失 | 可直接复用优化 |
| 2026-11-03 | `9636b724` | pinkpig-Peppa | Ghostuel | fix: share cross-skin realm search regions and replace EXP bottle template | 部分实现 | 适配风险 |
| 2026-11-03 | `4410d52e` | kongdr418 | kongdr418 | fix(DraftDuel): 手牌匹配逐级降阈值至0.5 | 完全缺失 | 可直接复用优化 |
| 2026-11-03 | `91f19356` | kongdr418 | kongdr418 | feat(DraftDuel): 统一阵容矩阵评分并同步队友选卡进度 | 完全缺失 | 适配风险 |
| 2026-11-03 | `1c7552f5` | kongdr418 | kongdr418 | feat(DraftDuel): 补充火系名单与核心阵容条件评分 | 完全缺失 | 可直接复用优化 |
| 2026-11-03 | `7112d251` | kongdr418 | kongdr418 | feat(DraftDuel): 联合队友候选选卡并移除错误式神条目 | 完全缺失 | 适配风险 |
| 2026-11-03 | `692ee215` | pinkpig-Peppa | leovefy | fix(AreaBoss): 跳过与悬赏鬼王重名的目标，避免重复挑战导致少打一只 | 部分实现 | 可直接复用优化 |
| 2026-11-03 | `df572d01` | pinkpig-Peppa | leovefy | fix(WantedQuests): 悬赏地点数量识别失败时收紧区域重试 | 部分实现 | 可直接复用优化 |
| 2026-11-04 | `f636e9d9` | pinkpig-Peppa | leovefy | fix(SixRealms): 修复月之海岛屿漏识别和点击偏移 | 部分实现 | 核心模块大改 |
| 2026-11-04 | `043d3aa9` | pinkpig-Peppa | leovefy | fix(SixRealms): 保留 OCR 已选中的岛屿 | 部分实现 | 可直接复用优化 |
| 2026-11-04 | `09bdec66` | kongdr418 | kongdr418 | fix(WantedQuests): 更新悬赏邀请模板及协作任务识别区域 | 部分实现 | 核心模块大改 |
| 2026-11-04 | `5ac08e11` | kongdr418 | kongdr418 | fix(WantedQuests): 扩大追踪按钮识别范围 | 部分实现 | 可直接复用优化 |
| 2026-11-04 | `657bb1b3` | pinkpig-Peppa | Ghostuel | fix: update main16 town entrance template and generated rule | 部分实现 | 可直接复用优化 |
| 2026-11-04 | `4944b3df` | pinkpig-Peppa | Ghostuel | fix: expand KekkaiActivation reward collection regions across realm skins | 已完整同步 | 可直接复用优化 |
| 2026-11-04 | `181801d1` | pinkpig-Peppa | huangrunheng | Update script_task.py | 已完整同步 | 可直接复用优化 |
| 2026-11-04 | `bf71e3a5` | lgg686 | LGG686 | fix(WantedQuests)：重做协斗协作类型模板并放宽好友邀请筛选 | 已完整同步 | 核心模块大改 |
| 2026-11-04 | `9cfb4d29` | pinkpig-Peppa | neptine | feat(workflow): Schedule Monday automated PR creation and merge | 部分实现 | 格式/文档 |
| 2026-11-05 | `4a6ad558` | pinkpig-Peppa | neptine | fix(GeneralBattle): Add soul overflow cleanup click rule #1979 | 部分实现 | 可直接复用优化 |
| 2026-11-05 | `5ba75f9b` | pinkpig-Peppa | neptine | fix(GeneralBattle): Add soul overflow cleanup click rule #1979 | 已完整同步 | 核心模块大改 |
| 2026-11-05 | `d9c28f51` | pinkpig-Peppa | neptine | chore(workflow): Upgrade GitHub Agentic Workflows to v1.0.1 | 部分实现 | 格式/文档 |
| 2026-11-05 | `9d7eb7e2` | kongdr418 | kongdr418 | feat: 移植超鬼王与活动控制并适配设置布局 | 部分实现 | 适配风险 |
| 2026-11-05 | `a3e6e028` | pinkpig-Peppa | neptine | fix(WantedQuests): remove invalid characters | 部分实现 | 可直接复用优化 |
| 2026-11-05 | `e53cb30f` | kongdr418 | kongdr418 | feat(MetaDemon): 接入六星上供并修复刷票配置与探索退出 | 已完整同步 | 适配风险 |
| 2026-11-05 | `1cc1707b` | pinkpig-Peppa | neptine | fix(KekkaiActivation): Prevent desktop activation button false positives #2013 | 已完整同步 | 可直接复用优化 |
| 2026-11-06 | `a80e1931` | pinkpig-Peppa | pinkpig-Peppa | chore: rebase onto upstream master and reapply cleanup changes | 部分实现 | 适配风险 |
| 2026-11-06 | `2dd53a9e` | pinkpig-Peppa | niuma-workwork | fix(core): release screen DCs, correct click offsets, harden device/config paths | 部分实现 | 适配风险 |
| 2026-11-06 | `e0773898` | pinkpig-Peppa | niuma-workwork | fix(tasks): initialize state, guard OCR results, bound loops in task scripts | 部分实现 | 核心模块大改 |
| 2026-11-06 | `41a2b209` | pinkpig-Peppa | niuma-workwork | fix(server/gui): await async handlers, add webui key check, harden config paths | 部分实现 | 适配风险 |
| 2026-11-06 | `a04e4dcc` | pinkpig-Peppa | niuma-workwork | fix(infra): restore TLS verification, guard QML/C++ nulls, harden deploy scripts | 部分实现 | 核心模块大改 |
| 2026-11-08 | `efcc78ad` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 适配新版超鬼王“祸至无日/祸主降临”活动界面 | 部分实现 | 适配风险 |
| 2026-11-08 | `c2943b5e` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): harden new-UI flow against click/stuck loops | 部分实现 | 核心模块大改 |
| 2026-11-08 | `4597cbe2` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 修复复审问题并补齐战斗路径单测 | 部分实现 | 核心模块大改 |
| 2026-11-08 | `eebc4c4f` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 修正兜底点击计数与结算领奖顺序 | 部分实现 | 可直接复用优化 |
| 2026-11-08 | `6d1277d3` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 结算领奖改为按奖励存在性判定结束 | 部分实现 | 可直接复用优化 |
| 2026-11-08 | `e2a97257` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 修复活动栏翻页入口、胜利结算与退出卡死 | 部分实现 | 核心模块大改 |
| 2026-11-08 | `419d0445` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 新增活动总览入口兜底，修复活动栏展开状态入口卡死 | 部分实现 | 核心模块大改 |
| 2026-11-08 | `02b4e18c` | pinkpig-Peppa | niuma-workwork | fix(MetaDemon): 战斗结算中等待，避免重复点击鬼王槽位 | 部分实现 | 核心模块大改 |
| 2026-11-08 | `a8bd3bc8` | pinkpig-Peppa | niuma-workwork | docs: 上游删库后整理仓库文档与 README | 部分实现 | 格式/文档 |
| 2026-11-08 | `8ff9806e` | kongdr418 | kongdr418 | feat: 对齐上游超鬼王并拆出刷票任务 | 部分实现 | 适配风险 |
| 2026-11-09 | `cf7e8a50` | pinkpig-Peppa | niuma-workwork | fix: 庭院镜头偏移导致页面识别全灭 + 失败后 Restart 被过期任务抢占 | 部分实现 | 适配风险 |
| 2026-11-09 | `fd767a1d` | nearaura | blylana | docs(README): Add temporary repository links after account suspension | 部分实现 | 格式/文档 |
| 2026-11-09 | `d7e7f2bf` | pinkpig-Peppa | pinkpig-Peppa | fix(deploy): keep template indentation when writing deploy.yaml | 部分实现 | 可直接复用优化 |
| 2026-11-09 | `c7e0c7bd` | kongdr418 | kongdr418 | feat(DraftDuel): 协同接入训练模型 | 已完整同步 | 核心模块大改 |
| 2026-11-09 | `363d676b` | kongdr418 | kongdr418 | fix(DraftDuel): 缩短首次邀请超时 | 已完整同步 | 可直接复用优化 |
| 2026-11-09 | `3ede58e1` | nearaura | blylana | fix(Image): Expand template search regions at initialization | 已完整同步 | 适配风险 |
| 2026-11-10 | `305defd0` | nearaura | blylana | fix(workflow): use current repository owner for mirroring | 部分实现 | 格式/文档 |
| 2026-11-10 | `fb3c10a0` | kongdr418 | kongdr | fix(Exploration): 突破票 OCR 改用超鬼王时期 ROI | 已完整同步 | 可直接复用优化 |
| 2026-11-10 | `844d3bec` | lgg686 | LGG686 | fix(bondling)：恢复交换身份在单次任务内按半量切换 | 已完整同步 | 可直接复用优化 |
| 2026-11-10 | `446e869e` | kongdr418 | kongdr418 | feat(DraftDuel): 记录真实协同对局 | 完全缺失 | 适配风险 |
| 2026-11-10 | `835338cb` | nearaura | blylana | fix(MetaDemon): Update demon encounter image matching | 已完整同步 | 核心模块大改 |
| 2026-11-10 | `a787a58a` | nearaura | kristin0512 | Fix minitouch pressure range for low max_pressure | 已完整同步 | 适配风险 |
| 2026-11-10 | `8d48055c` | nearaura | blylana | chore(MetaDemon): Remove unused image assets | 已完整同步 | 核心模块大改 |
| 2026-11-10 | `411ef6d3` | nearaura | blylana | fix(MetaDemon): Recognize publicly shared demon bosses - add an image rule for the public status - include pub | 已完整同步 | 可直接复用优化 |
| 2026-11-11 | `bc2211da` | nearaura | blylana | docs(Docs): Update documentation links to the new domain | 部分实现 | 格式/文档 |
| 2026-11-11 | `4d75666a` | kongdr418 | kongdr418 | fix(MetaDemon): 更新鬼王页识别图 | 已完整同步 | 可直接复用优化 |
| 2026-11-11 | `61d3f8cf` | kongdr418 | kongdr418 | fix(MetaDemon): 恢复一键配置 frame 并更新入口图标 | 已完整同步 | 可直接复用优化 |
| 2026-11-11 | `ec8ef406` | nearaura | 微凉徒眸 | fix(MetaDemon): update UI assets and add auto_shared_boss config | 部分实现 | 核心模块大改 |
| 2026-11-11 | `36dde020` | kongdr418 | kongdr418 | fix(MetaDemon): 礼包窗口优先点右上角亮叉 | 已完整同步 | 可直接复用优化 |
| 2026-11-11 | `f99d75c2` | kongdr418 | kongdr418 | fix(server): 修复配置导入时对泛型注解的误判 | 已完整同步 | 适配风险 |
| 2026-11-11 | `a279ab60` | lgg686 | LGG686 | feat(sync)：同步上游新增任务、超鬼王快速预设与协斗模板权重 | 已完整同步 | 适配风险 |
| 2026-11-11 | `4d910027` | lgg686 | LGG686 | feat(MetaDemon)：超鬼王上供分享星级可配置 | 部分实现 | 核心模块大改 |
| 2026-11-11 | `fd7e20a5` | nearaura | LLLLLUO | fix(GameUi): tolerate exploration marker horizontal shifts | 部分实现 | 可直接复用优化 |
| 2026-11-11 | `0b8ef1cb` | nearaura | LLLLLUO | fix(GameUi): sync generated exploration marker rule | 部分实现 | 可直接复用优化 |
| 2026-11-11 | `b8624012` | nearaura | LLLLLUO | test(GameUi): cover shifted exploration markers | 部分实现 | 可直接复用优化 |
| 2026-11-11 | `f9e2ec0f` | nearaura | LLLLLUO | test(GameUi): add exploration marker regression cases | 部分实现 | 可直接复用优化 |
| 2026-11-11 | `484337f5` | nearaura | 微凉徒眸 | fix(MetaDemon): Use recognition loop to close victory screen reliably | 已完整同步 | 可直接复用优化 |
| 2026-11-11 | `d2feec52` | kongdr418 | kongdr418 | fix(scheduler): 调度白名单补上超鬼王门票任务 | 部分实现 | 适配风险 |
| 2026-11-11 | `209f8fad` | kongdr418 | kongdr418 | fix(GeneralBattle): 校准超鬼王门票 OCR 区域 | 部分实现 | 可直接复用优化 |
| 2026-11-11 | `c8c9c648` | kongdr418 | kongdr418 | feat(MetaDemonTicket): 探索模式支持选择章节 | 部分实现 | 适配风险 |
| 2026-11-11 | `ad778fba` | nearaura | blylana | fix(DailyTrifles): Improve store sign navigation and mall detection | 已完整同步 | 可直接复用优化 |
| 2026-11-11 | `429b8570` | kongdr418 | kongdr418 | fix(MetaDemonTicket): 门票计数越界时按识别错误处理 | 部分实现 | 可直接复用优化 |
| 2026-11-11 | `ea8e72f3` | kongdr418 | kongdr418 | feat(MetaDemon): 上供支持自定义星级鬼王 | 部分实现 | 适配风险 |
| 2026-11-11 | `ed25cc79` | kongdr418 | kongdr418 | feat(cooperation): 协同心跳接入调度进程 | 部分实现 | 适配风险 |
| 2026-11-12 | `f4199538` | kongdr418 | kongdr418 | refactor(MetaDemon): 修复快速上阵 | 部分实现 | 可直接复用优化 |
| 2026-11-12 | `5a752388` | nearaura | blylana | refactor(MetaDemon): Migrate battle_boss to battle_wait strategy hooks | 部分实现 | 适配风险 |
| 2026-11-12 | `09571eb4` | nearaura | blylana | fix(MetaDemon): Ensure team unlock state before boss battle | 部分实现 | 核心模块大改 |
| 2026-11-12 | `81bb25a7` | kongdr418 | kongdr418 | fix(GameUi): 更新商店识别模板并补全棋局排名页规则 | 部分实现 | 核心模块大改 |
| 2026-11-12 | `83b82fd5` | kongdr418 | kongdr418 | fix(MetaDemon): 增加协同心跳等待并修复退出时截图过期 | 部分实现 | 可直接复用优化 |
| 2026-11-12 | `eb156b16` | kongdr418 | kongdr418 | fix(RealmRaid): 校验突破券数量上限并忽略无效识别 | 部分实现 | 可直接复用优化 |
| 2026-11-12 | `9eea7c9d` | kongdr418 | jl5250 | feat(Duel): 增加斗技识别的资源以及更正返回庭院的函数 | 部分实现 | 可直接复用优化 |
| 2026-11-12 | `27b9f534` | kongdr418 | kongdr418 | fix(annotator): 隔离预览截图缓存避免干扰运行任务 | 已完整同步 | 适配风险 |
| 2026-11-12 | `bf893c0d` | kongdr418 | kongdr418 | fix(Duel): 补齐斗技识别资源标注并同步生成配置 | 部分实现 | 可直接复用优化 |
| 2026-11-12 | `0ca19ebc` | lgg686 | LGG686 | fix(MetaDemon)：协同等待对端启动而非固定 30 秒，导航前重新截图 | 部分实现 | 核心模块大改 |
| 2026-11-12 | `25cc699b` | nearaura | blylana | feat(workflow): Create and merge sync PR on schedule | 部分实现 | 格式/文档 |
| 2026-11-12 | `f1ba2a5c` | nearaura | blylana | fix(GameUi): Update mall page detection image | 部分实现 | 可直接复用优化 |
| 2026-11-13 | `7478e169` | kongdr418 | kongdr418 | feat(MetaDemon): 支持选择上供召唤顺序并补齐中文显示 | 部分实现 | 适配风险 |
| 2026-11-13 | `80751206` | lgg686 | LGG686 | feat(AutoStory)：完善剧情结束判定与视频加速处理 | 完全缺失 | 核心模块大改 |
| 2026-11-13 | `78234f6d` | lgg686 | LGG686 | perf(deploy): speed up startup and isolate annotator preview frames | 部分实现 | 适配风险 |
| 2026-11-13 | `547dfba6` | kongdr418 | kongdr418 | feat(游戏辅助): 迁移自动剧情、探索推进和自定义任务 | 完全缺失 | 适配风险 |
| 2026-11-13 | `3a8ba22f` | kongdr418 | kongdr418 | feat(游戏辅助): 新增15级起号流程并适配新手引导 | 完全缺失 | 适配风险 |
| 2026-11-13 | `fe19476d` | kongdr418 | kongdr418 | feat(MetaDemon): 支持选择双端协同或独立好友上供 | 部分实现 | 适配风险 |
| 2026-11-13 | `057628b1` | kongdr418 | kongdr418 | fix(EvoZone): 兼容缺少头像标志的组队页面 | 已完整同步 | 可直接复用优化 |
| 2026-11-13 | `fc45a500` | kongdr418 | kongdr418 | fix(BorrowShikigami): 调整15级起号流程并补齐新手弹窗处理 | 完全缺失 | 核心模块大改 |
| 2026-11-13 | `991016cf` | kongdr418 | kongdr418 | feat(MetaDemonTicket): 支持三人觉醒刷票协同 | 部分实现 | 适配风险 |
| 2026-11-14 | `cc12900f` | kongdr418 | kongdr418 | fix(MetaDemonTicket): 满票退出时补点关闭奖励页面 | 已完整同步 | 可直接复用优化 |
| 2026-11-14 | `628c0cfb` | kongdr418 | kongdr418 | fix(BorrowShikigami): 通过自动标识兼容新手战斗页面 | 完全缺失 | 可直接复用优化 |
| 2026-11-14 | `a67366d1` | lgg686 | LGG686 | fix(DailyTrifles)：Add cancel button for summon animation popup in courtyard affairs | 部分实现 | 核心模块大改 |
| 2026-11-14 | `50dec6ce` | pinkpig-Peppa | pinkpig-Peppa | 移植统计/日志模块, 新增看门狗与 Apprise 通知 | 部分实现 | 适配风险 |
| 2026-11-14 | `d389f83a` | pinkpig-Peppa | pinkpig-Peppa | requirements: 新增 apprise==2.2.0 依赖 | 部分实现 | 适配风险 |
| 2026-11-14 | `56529f78` | pinkpig-Peppa | pinkpig-Peppa | OCR 引擎升级: ppocr-onnx 迁移至 paddleocr 3.7.0 (PP-OCRv5 + ONNX Runtime) | 部分实现 | 适配风险 |
| 2026-11-14 | `26e67b73` | pinkpig-Peppa | pinkpig-Peppa | 移植 nearaura/OnmyojiAutoScript 修复包 (4 项) | 部分实现 | 适配风险 |
| 2026-11-14 | `64f1ee7d` | pinkpig-Peppa | pinkpig-Peppa | 移植 nearaura 二期任务修复与更新 (MetaDemon/SixRealms 月海/DailyTrifles/GameUi) | 部分实现 | 适配风险 |
| 2026-11-14 | `3ad3ff86` | kongdr418 | kongdr418 | fix(MetaDemonTicket): 修复短战斗提前退出和奖励页面卡住 | 部分实现 | 可直接复用优化 |
| 2026-11-14 | `5db01e76` | pinkpig-Peppa | pinkpig-Peppa | 新增 /tool/doctor 一键体检接口 | 部分实现 | 适配风险 |
| 2026-11-14 | `761614dc` | lgg686 | LGG686 | fix(MetaDemon)：Retry friend share once and select recipients while scanning | 部分实现 | 可直接复用优化 |
| 2026-11-15 | `13221d2c` | nearaura | blylana | fix(CollectiveMissions): Handle reward claims and timeout after donation  #7 | 已完整同步 | 可直接复用优化 |
| 2026-11-15 | `f449cb35` | nearaura | 微凉徒眸 | feat(MetaDemon): summon demon first when fatigue >= 61 (configurable) | 部分实现 | 适配风险 |
| 2026-11-15 | `838d4b7c` | kongdr418 | kongdr418 | fix(MetaDemon): 适配超鬼王新UI | 部分实现 | 可直接复用优化 |
| 2026-11-15 | `b615ec97` | nearaura | blylana | fix(MetaDemon): Update enter2 detection image and ROI | 已完整同步 | 可直接复用优化 |
| 2026-11-15 | `aff78b2c` | pinkpig-Peppa | niuma-workwork | 修复 OCR 服务未启动与 exact 匹配参数回归 | 部分实现 | 适配风险 |
| 2026-11-16 | `95b75dd8` | kongdr418 | kongdr418 | feat(scrolls): 完善绘卷查询 | 完全缺失 | 适配风险 |
| 2026-11-16 | `92ada2c7` | kongdr418 | kongdr418 | feat(scrolls): 适配 Linux 和 redroid 绘卷查询 | 完全缺失 | 核心模块大改 |
| 2026-11-16 | `041e8686` | nearaura | blylana | fix(MetaDemon): Update detection images and ROIs | 部分实现 | 可直接复用优化 |
| 2026-11-18 | `f4bf42bc` | kongdr418 | kongdr418 | fix(Exploration): 恢复常规突破券 OCR 区域 | 部分实现 | 可直接复用优化 |
| 2026-11-18 | `0f99fd02` | lgg686 | LGG686 | fix(Exploration)：Restore realm raid ticket OCR after MetaDemon event | 部分实现 | 可直接复用优化 |
| 2026-11-18 | `bb6f2103` | nearaura | blylana | fix(Exploration): Narrow realm raid ticket OCR region to drop extra leading digit  #7 | 已完整同步 | 可直接复用优化 |
| 2026-11-18 | `db601816` | lgg686 | LGG686 | feat(Android)：Add oasaos device backend and native panel compatibility | 部分实现 | 适配风险 |
| 2026-11-18 | `adfa6e84` | lgg686 | LGG686 | feat(Android)：Hot-update OAS source from a Git repository | 部分实现 | 适配风险 |
| 2026-11-19 | `7b2f2492` | lgg686 | LGG686 | fix(server)：keep-alive 超时拉长到 75 秒 | 已完整同步 | 适配风险 |
| 2026-11-19 | `52f23c56` | lgg686 | LGG686 | fix(server)：局域网口令改为可选并支持 Cookie 会话 | 部分实现 | 适配风险 |
| 2026-11-19 | `03b5f1ef` | nearaura | 2263075977 | fix(SixRealms): 月之海选岛自愈重读 + 宁息岛兜底 | 部分实现 | 可直接复用优化 |
| 2026-11-19 | `9d9a6fbd` | lgg686 | LGG686 | feat(ocr)：OCR 档位改由环境变量决定 | 部分实现 | 适配风险 |
| 2026-11-19 | `ea13a4c6` | lgg686 | LGG686 | refactor(config)：移除未实现的 OrochiMoans 占位 | 已完整同步 | 适配风险 |
| 2026-11-20 | `17bb2993` | lgg686 | LGG686 | feat(android)：同步适配批次到 OASA | 部分实现 | 适配风险 |
| 2026-11-20 | `f7a3f643` | lgg686 | LGG686 | fix(server)：补齐提交历史接口并输出作者 | 部分实现 | 适配风险 |
| 2026-11-21 | `8b06fd35` | lgg686 | LGG686 | fix(server)：修复提交历史拉不到与首次为空 | 部分实现 | 适配风险 |
| 2026-11-21 | `bd4614ac` | lgg686 | LGG686 | feat(server)：条件挂载 /gui 网页控制台 | 部分实现 | 适配风险 |
| 2026-11-21 | `4bf1a8b7` | lgg686 | LGG686 | fix(server)：git 残留锁自动清理重试 | 部分实现 | 适配风险 |
| 2026-11-21 | `4785e4bf` | nearaura | Tyrion | fix(Hyakkiyakou): Ignore an off-screen track when the heatmap has no match | 部分实现 | 可直接复用优化 |
| 2026-11-21 | `3051c38c` | lgg686 | LGG686 | fix(server)：热更首拉超时残留锁与历史面板空转 | 部分实现 | 适配风险 |
| 2026-11-21 | `c4f533ab` | lgg686 | LGG686 | fix(server)：提交历史优先返回已拉到的远端列表 | 部分实现 | 适配风险 |
| 2026-11-21 | `96a34f39` | lgg686 | LGG686 | feat(server)：提交历史返回描述正文并支持仅重启 OAS | 部分实现 | 适配风险 |
| 2026-11-21 | `43339741` | lgg686 | LGG686 | feat(server)：网页控制台 /gui 支持自动更新 | 部分实现 | 适配风险 |
| 2026-11-22 | `fe65e54b` | nearaura | blylana | fix(GeneralInvite): Shrink I_FLAG_1_ON ROI to keep the selected friend tab detected  #20 | 部分实现 | 可直接复用优化 |

## 3. 分模块差异对照

| 模块 | 条数 | 已同步 | 部分实现 | 完全缺失 | 主要类型 | 建议 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Component | 60 | 21 | 39 | 0 | 可直接复用优化 | 可排期 |
| DraftDuel | 39 | 2 | 0 | 37 | 可直接复用优化 | 单独评估 |
| MetaDemon | 33 | 9 | 24 | 0 | 可直接复用优化 | 可排期 |
| Chess | 24 | 8 | 16 | 0 | 适配风险 | 优先合并 |
| GameUi | 23 | 14 | 9 | 0 | 可直接复用优化 | 可排期 |
| WantedQuests | 23 | 6 | 17 | 0 | 可直接复用优化 | 优先合并 |
| module/server | 22 | 4 | 18 | 0 | 适配风险 | 谨慎评估 |
| FrogBoss | 21 | 11 | 10 | 0 | 可直接复用优化 | 优先合并 |
| Exploration | 19 | 9 | 10 | 0 | 可直接复用优化 | 优先合并 |
| ActivityShikigami | 14 | 0 | 14 | 0 | 核心模块大改 | 可排期 |
| module/device | 14 | 5 | 9 | 0 | 适配风险 | 谨慎评估 |
| GlobalGame | 13 | 5 | 8 | 0 | 可直接复用优化 | 优先合并 |
| 根目录 | 12 | 2 | 10 | 0 | 适配风险 | 单独评估 |
| 文档/CI | 11 | 1 | 10 | 0 | 格式/文档 | 低优先 |
| DemonEncounter | 10 | 6 | 4 | 0 | 可直接复用优化 | 可排期 |
| module/image | 10 | 4 | 6 | 0 | 适配风险 | 可排期 |
| DailyTrifles | 8 | 7 | 1 | 0 | 可直接复用优化 | 单独评估 |
| Duel | 8 | 3 | 5 | 0 | 可直接复用优化 | 可排期 |
| Restart | 8 | 2 | 6 | 0 | 可直接复用优化 | 优先合并 |
| Dokan | 7 | 6 | 1 | 0 | 可直接复用优化 | 可排期 |
| Delegation | 6 | 4 | 2 | 0 | 可直接复用优化 | 可排期 |
| module/gui | 6 | 4 | 2 | 0 | 适配风险 | 谨慎评估 |
| AbyssShadows | 5 | 1 | 4 | 0 | 可直接复用优化 | 可排期 |
| BondlingFairyland | 5 | 3 | 2 | 0 | 可直接复用优化 | 可排期 |
| MetaDemonTicket | 5 | 1 | 4 | 0 | 可直接复用优化 | 可排期 |
| RichMan | 5 | 2 | 3 | 0 | 可直接复用优化 | 可排期 |
| EvoZone | 4 | 4 | 0 | 0 | 可直接复用优化 | 已处理 |
| LBS | 4 | 4 | 0 | 0 | 适配风险 | 已处理 |
| SixRealms | 4 | 0 | 4 | 0 | 可直接复用优化 | 可排期 |
| WeeklyTrifles | 4 | 4 | 0 | 0 | 可直接复用优化 | 已处理 |
| base_task.py | 4 | 3 | 1 | 0 | 可直接复用优化 | 优先合并 |
| module/config | 4 | 2 | 2 | 0 | 适配风险 | 谨慎评估 |
| BorrowShikigami | 3 | 0 | 0 | 3 | 适配风险 | 单独评估 |
| MysteryShop | 3 | 2 | 1 | 0 | 可直接复用优化 | 可排期 |
| Script | 3 | 1 | 2 | 0 | 适配风险 | 谨慎评估 |
| module/atom | 3 | 1 | 2 | 0 | 适配风险 | 谨慎评估 |
| AreaBoss | 2 | 0 | 2 | 0 | 适配风险 | 可排期 |
| AutoCheckinBigGod | 2 | 1 | 1 | 0 | 核心模块大改 | 单独评估 |
| AutoStory | 2 | 0 | 0 | 2 | 核心模块大改 | 谨慎评估 |
| EternitySea | 2 | 2 | 0 | 0 | 可直接复用优化 | 已处理 |
| GuildBanquet | 2 | 0 | 2 | 0 | 适配风险 | 可排期 |
| HeroTest | 2 | 2 | 0 | 0 | 可直接复用优化 | 已处理 |
| IbukiArena | 2 | 2 | 0 | 0 | 适配风险 | 已处理 |
| KekkaiActivation | 2 | 2 | 0 | 0 | 可直接复用优化 | 已处理 |
| OtherWorldTwilight | 2 | 2 | 0 | 0 | 适配风险 | 已处理 |
| RealmRaid | 2 | 0 | 2 | 0 | 可直接复用优化 | 可排期 |
| TalismanPass | 2 | 2 | 0 | 0 | 可直接复用优化 | 已处理 |
| TrueOrochi | 2 | 0 | 0 | 2 | 核心模块大改 | 不引入 |
| module/scrolls | 2 | 0 | 0 | 2 | 适配风险 | 单独评估 |
| CollectiveMissions | 1 | 1 | 0 | 0 | 可直接复用优化 | 已处理 |
| FallenSun | 1 | 0 | 1 | 0 | 核心模块大改 | 单独评估 |
| FindJade | 1 | 1 | 0 | 0 | 适配风险 | 已处理 |
| FrogChallenge | 1 | 1 | 0 | 0 | 适配风险 | 已处理 |
| GuildActivityMonitor | 1 | 1 | 0 | 0 | 可直接复用优化 | 已处理 |
| Hyakkiyakou | 1 | 0 | 1 | 0 | 可直接复用优化 | 可排期 |
| KekkaiUtilize | 1 | 0 | 1 | 0 | 适配风险 | 谨慎评估 |
| MemoryScrolls | 1 | 1 | 0 | 0 | 可直接复用优化 | 已处理 |
| Orochi | 1 | 1 | 0 | 0 | 核心模块大改 | 已处理 |
| module/ocr | 1 | 0 | 1 | 0 | 适配风险 | 谨慎评估 |

### 3.1 逐条明细

#### Component（60 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `d2f98590` | 2026-09-19 | neptine | feat(GeneralBattle): Add prepare/preset/green/echo/randomclick hooks and config-driven loadout - add | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/script_task.py、tasks/Component/GeneralBattle/battle.py、tasks/Component/GeneralBattle/battle_wait.py、tasks/Component/GeneralBattle/general_battle.py 等 5 个 | 本地模块存在，文件命中 2/5 |
| `0e711238` | 2026-09-19 | neptine | feat(GeneralBattle): Add completion fallback click and randomclick expectation model | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/battle_wait.py | 本地模块存在，文件命中 0/1 |
| `d54042b5` | 2026-09-19 | neptine | feat(GeneralBattle): Add battle count and state reset helpers, restore climb counting | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/script_task.py、tasks/Component/GeneralBattle/battle.py、tasks/Component/GeneralBattle/battle_wait.py | 本地模块存在，文件命中 1/3 |
| `36e1a822` | 2026-09-19 | neptine | feat(Costume): Support time-variant courtyard skin 玉岚狐庭 #1824 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、module/atom/gif.py、tasks/Component/Costume/assets.py、tasks/Component/Costume/config.py 等 22 个 | 本地模块存在，文件命中 7/22 |
| `05560e29` | 2026-09-20 | User | 新增(换装战斗)：接入灵狐寄愿主题与识别资源 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/CostumeBattle/assets.py 等 12 个 | 台账已覆盖 |
| `52b91fe9` | 2026-09-20 | Hurry2 | 修复(战斗预设)：缩小前三队点击区域避免误滑 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/click.json | 等价补丁 aa080034 |
| `18b0394e` | 2026-09-20 | AzurTian | 修复(战斗预设)：确认点击后等待弹窗关闭 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/general_battle.py | 等价补丁 d9a0c86c |
| `6c3d2927` | 2026-09-20 | xylolit-mu | 调整(通用战斗)：更新探索与活动Scatter安全区域 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/scatter.json | 本地模块存在，文件命中 1/2 |
| `4f0b246b` | 2026-09-20 | xylolit-mu | 修正(庭院主题)：更新第13期主页与宠物屋识别资源 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Costume/assets.py、tasks/Component/Costume/main13/image.json、tasks/Component/Costume/main13/main13_check_main_13.png、tasks/Component/Costume/main13/main13_pet_house_13.png | 本地模块存在，文件命中 4/4 |
| `8ec6ae47` | 2026-09-20 | xylolit-mu | 清理(生成资源)：统一注释空白与文件结尾 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/Component/GeneralBattle/assets.py、tasks/Delegation/assets.py、tasks/Duel/assets.py | 台账已覆盖 |
| `395fef27` | 2026-09-20 | xylolit-mu | 修复(全局页面)：识别闲庭并关闭战斗奖励详情 | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/gb_reward_particulars.png、tasks/Component/GeneralBattle/gb/gb_reward_particulars_orchi.png、tasks/Component/GeneralBattle/gb/image.json 等 10 个 | 本地提交信息引用（已移植/合入） |
| `bb808e1b` | 2026-09-21 | neptine | feat(Costume): Attach GIF multi-frame behavior in-place so page routing works  #1824 - add RuleGif.a | 中 | 部分实现 | 核心模块大改 | 单独评估 | module/atom/gif.py、tasks/Component/Costume/assets.py、tasks/Component/Costume/costume_base.py、tasks/Component/Costume/costume_test.py 等 8 个 | 本地模块存在，文件命中 5/8 |
| `37a884ef` | 2026-09-21 | neptine | fix(Costume): Skip missing assets when attaching GIF frames | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/Costume/costume_base.py | 本地提交信息引用（已移植/合入） |
| `64199898` | 2026-09-22 | User | feat(GeneralInvite): 等待好友列表加载完成并简化房间锁定判定 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/BondlingFairyland/script_task.py、tasks/Component/GeneralInvite/assets.py、tasks/Component/GeneralInvite/general_invite.py、tasks/Component/GeneralInvite/gi/gi_i_load.png 等 6 个 | 本地模块存在，文件命中 5/6 |
| `929c6a11` | 2026-09-26 | Enough1122 | fix(SwitchOnmyoji): give both switch_role loops a bounded exit | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/SwitchOnmyoji/switch_onmyoji.py、tests/test_switch_onmyoji.py | 等价补丁 cc09f936 |
| `7c850c3c` | 2026-09-27 | User | refactor(GeneralRoom): ensure 类方法移除硬编码阈值，改用资产自带阈值 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralRoom/assets.py、tasks/Component/GeneralRoom/general_room.py、tasks/Component/GeneralRoom/gr/image.json | 本地提交信息引用（已移植/合入） |
| `33c40a65` | 2026-09-27 | User | refactor(GeneralInvite): click_fire 移除硬编码阈值，改用资产自带阈值 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralInvite/assets.py、tasks/Component/GeneralInvite/general_invite.py、tasks/Component/GeneralInvite/gi/image.json | 本地提交信息引用（已移植/合入） |
| `1c646ce5` | 2026-09-27 | xylolit-mu | 优化(通用战斗)：调整随机点击区域与风险档位 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/click.json | 本地模块存在，文件命中 2/2 |
| `17474206` | 2026-09-30 | kongdr | fix(Login): 延长等待角色选择页的超时时间，避免登录卡死 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Login/service.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核） |
| `8f0ebc1c` | 2026-09-30 | xylolit-mu | 优化(全局):调整默认庭院检查资源，新增登陆保底点击。 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Component/Costume/main11/image.json、tasks/Component/Costume/main11/main11_check_main_11.png、tasks/Component/Costume/main11/main11_main_goto_exploration_11.png、tasks/Component/Costume/main11/main11_main_goto_summon_11.png 等 13 个 | 本地模块存在，文件命中 13/13 |
| `f130ab3f` | 2026-09-30 | xylolit-mu | 调整(图像点击)：统一Image规则为High并更新默认值 | 大 | 部分实现 | 适配风险 | 谨慎评估 | dev_tools/assets_extract.py、module/atom/image.py、module/server/annotator_rule_schema.py、module/server/tool.py 等 282 个 | 本地模块存在，文件命中 253/282 |
| `3d85565f` | 2026-09-30 | User | fix(Login): 桌面登录期处理 MPay 弹窗，避免误判未知页面 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Login/service.py、tasks/GameUi/navigator.py | 本地模块存在，文件命中 2/2 |
| `08079eaf` | 2026-10-03 | neptine | feat(Costume): Add task-scoped battle scene skin support #1843 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py 等 8 个 | 本地模块存在，文件命中 5/8 |
| `c1dc5059` | 2026-10-03 | neptine | feat(Costume): Add Chinese names to costume switch logs | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Costume/costume_base.py | 本地模块存在，文件命中 1/1 |
| `4e32d985` | 2026-10-03 | User | feat(GeneralBattle): 支持按式神名点击绿标 | 中 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/config_general_battle.py、tasks/Component/GeneralBattle/gb/click.json 等 6 个 | 台账已覆盖 |
| `5bc3f6e2` | 2026-10-04 | neptine | fix(GeneralBattle): Support named green marks in battle wait | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/battle.py、tasks/Component/GeneralBattle/battle_wait.py | 台账已覆盖 |
| `990c4590` | 2026-10-09 | allesgutefy | fix: add missing run_task_or_default_general_battle function | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/general_battle.py | 台账已覆盖 |
| `a67309e7` | 2026-10-09 | yuyuyuyuyu | refactor(assets): 清理冗余资产并将确认类调用收敛至通用模板 | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/AbyssShadows/script_task.py、tasks/BondlingFairyland/script_task.py、tasks/Component/Costume/costume_base.py、tasks/Component/Costume/costume_test_shikigami.py 等 66 个 | 本地模块存在，文件命中 49/66 |
| `55f51238` | 2026-10-09 | allesgutefy | fix: handle AttributeError for tasks without general_battle_config | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/general_battle.py | 台账已覆盖 |
| `ca7a4189` | 2026-10-09 | allesgutefy | fix: add 0.8s delay after clicking I_I_NO_DEFAULT to wait for UI update | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralInvite/general_invite.py | 等价补丁 d99afd22 |
| `100879bb` | 2026-10-10 | kongdr | fix(SwitchSoul): 重截切换确认弹窗按钮并修正ROI | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/SwitchSoul/assets.py、tasks/Component/SwitchSoul/ss/image.json、tasks/Component/SwitchSoul/ss/ss_sou_switch_sure.png | 本地模块存在，文件命中 2/3 |
| `57fc173b` | 2026-10-10 | kongdr | fix(GeneralBattle): 重截退出战斗确认按钮并改用新素材 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/gb_new_exit_ensure.png、tasks/Component/GeneralBattle/gb/image.json、tasks/Component/GeneralBattle/general_battle.py | 本地模块存在，文件命中 3/4 |
| `2f503b4b` | 2026-10-10 | LGG686 | fix(GeneralBattle)：重画 Act 结算页安全点击区域 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/scatter.json | 本地模块存在，文件命中 1/2 |
| `e930e2e1` | 2026-10-10 | allesgutefy | fix: use interval=3 instead of sleep(0.8) per developer suggestion | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralInvite/general_invite.py | 本地提交信息引用（已移植/合入） |
| `8195cc60` | 2026-10-10 | allesgutefy | Revert "fix: use interval=3 instead of sleep(0.8) per developer suggestion" | 小 | 部分实现 | 可直接复用优化 | 低优先 | tasks/Component/GeneralInvite/general_invite.py | 本地模块存在，文件命中 1/1 |
| `71e33265` | 2026-10-10 | neptine | refactor(SwitchSoul): Reuse shared confirm button across costume flows - replace dedicated soul swit | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/AbyssShadows/script_task.py、tasks/Component/Costume/costume_base.py、tasks/Component/Costume/costume_test_shikigami.py、tasks/Component/CostumeShikigami/assets.py 等 35 个 | 本地模块存在，文件命中 22/35 |
| `84eda193` | 2026-10-11 | neptine | fix(GeneralInvite): Use shared UI assets for invite confirmation #1915 - replace invite-specific che | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/BondlingFairyland/general_invite.py、tasks/BondlingFairyland/script_task.py、tasks/Component/GeneralInvite/assets.py、tasks/Component/GeneralInvite/general_invite.py 等 12 个 | 本地模块存在，文件命中 5/12 |
| `27241886` | 2026-10-11 | neptine | fix(GeneralBattle): Avoid reward popup during completion fallback #1913 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/script_task.py、tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/battle_wait.py、tasks/Component/GeneralBattle/gw/click2.json | 本地模块存在，文件命中 2/4（台账曾判不采纳，需复核） |
| `7f0728bf` | 2026-10-11 | davidyangkunlong | 点击御魂溢出的提示 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/battle_wait.py | 本地提交信息引用（已移植/合入） |
| `2f5c306e` | 2026-10-12 | llBai | fix(invite_friends)：sleep(3) before invite_friend | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralInvite/general_invite.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核） |
| `d6c42bee` | 2026-10-12 | neptine | fix(GeneralBattle): Log battle start in strategy-based wait | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/battle.py | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `60117f17` | 2026-10-15 | davidyangkunlong | 处理御魂溢出 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/battle_wait.py、tasks/Orochi/script_task.py | 本地提交信息引用（已移植/合入） |
| `43c84c88` | 2026-10-15 | neptine | fix(GeneralBattle): Close buff panel and start battle preparation | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralBattle/general_battle.py | 本地提交信息引用（已移植/合入） |
| `b1c7186c` | 2026-10-19 | neptine | fix(GeneralInvite): Update invite confirmation ROI for wanted quests #1939 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralInvite/assets.py、tasks/Component/GeneralInvite/gi/image.json | 本地提交信息引用（已移植/合入） |
| `cacc2af3` | 2026-10-24 | davidyangkunlong | 御魂溢出处理升级 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/battle_wait.py、tasks/Component/GeneralBattle/general_battle.py | 本地模块存在，文件命中 1/2（台账曾判不采纳，需复核） |
| `14cbd413` | 2026-10-25 | kongdr | feat(GeneralInvite): 同步上游邀请组件，适配新界面并等待好友列表加载 | 大 | 部分实现 | 核心模块大改 | 单独评估 | module/cooperation.py、tasks/Component/GeneralInvite/assets.py、tasks/Component/GeneralInvite/config_invite.py、tasks/Component/GeneralInvite/general_invite.py 等 11 个 | 本地模块存在，文件命中 5/11 |
| `4b823fde` | 2026-10-29 | 微凉徒眸 | fix(GeneralInvite): use interval=3 for I_UI_UNCHECK in invite_again | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralInvite/general_invite.py | 等价补丁 a3698bc6 |
| `ba699f87` | 2026-10-29 | Msrtria | feat(Costume): 新增幕间主题梦隙闲花 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/CostumeShikigami/assets.py 等 24 个 | 本地模块存在，文件命中 4/24 |
| `b46be8a6` | 2026-11-01 | Ghostuel | feat: support Xinyu Mingxiao scroll and shared masked guild entrance | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/CostumeTheme/assets.py 等 14 个 | 本地模块存在，文件命中 5/14 |
| `cfcdad39` | 2026-11-01 | Ghostuel | feat: support Yuehai Youxing realm with shared template search regions | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/CostumeRealm/assets.py 等 6 个 | 本地模块存在，文件命中 3/6 |
| `2d7b85de` | 2026-11-01 | Ghostuel | fix: resolve theme log translation and strengthen invalid-theme regression tests | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Costume/costume_base.py、tests/tasks/Component/CostumeTheme/test_theme.py | 本地模块存在，文件命中 1/2 |
| `ab2b0c00` | 2026-11-01 | Ghostuel | fix: update manual realm tool enum and add offline regression check | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Costume/costume_test_realm.py、tests/tasks/Component/CostumeRealm/test_realm.py | 本地模块存在，文件命中 0/2 |
| `9636b724` | 2026-11-03 | Ghostuel | fix: share cross-skin realm search regions and replace EXP bottle template | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/Costume/costume_test_realm.py 等 17 个 | 本地模块存在，文件命中 6/17 |
| `657bb1b3` | 2026-11-04 | Ghostuel | fix: update main16 town entrance template and generated rule | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Costume/assets.py、tasks/Component/Costume/main16/image.json、tasks/Component/Costume/main16/main16_main_goto_town_16.png | 本地模块存在，文件命中 3/3（台账曾判不采纳，需复核） |
| `4a6ad558` | 2026-11-05 | neptine | fix(GeneralBattle): Add soul overflow cleanup click rule #1979 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/gw/click.json | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `5ba75f9b` | 2026-11-05 | neptine | fix(GeneralBattle): Add soul overflow cleanup click rule #1979 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/ActivityShikigami/assets.py、tasks/Component/CostumeShikigami/assets.py、tasks/Component/GeneralBattle/assets.py、tasks/Component/SwitchAccount/assets.py 等 6 个 | 本地提交信息引用（已移植/合入） |
| `a80e1931` | 2026-11-06 | pinkpig-Peppa | chore: rebase onto upstream master and reapply cleanup changes | 大 | 部分实现 | 适配风险 | 谨慎评估 | deploy/adb.py、deploy/config.py、deploy/emulator.py、deploy/git.py 等 90 个 | 本地模块存在，文件命中 82/90 |
| `e0773898` | 2026-11-06 | niuma-workwork | fix(tasks): initialize state, guard OCR results, bound loops in task scripts | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/AbyssShadows/script_task.py、tasks/ActivityShikigami/script_task.py、tasks/AutoCheckinBigGod/script_task.py、tasks/BondlingFairyland/script_task.py 等 26 个 | 本地模块存在，文件命中 24/26 |
| `209f8fad` | 2026-11-11 | kongdr418 | fix(GeneralBattle): 校准超鬼王门票 OCR 区域 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/ocr.json | 本地模块存在，文件命中 2/2 |
| `fe65e54b` | 2026-11-22 | blylana | fix(GeneralInvite): Shrink I_FLAG_1_ON ROI to keep the selected friend tab detected  #20 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/GeneralInvite/assets.py、tasks/Component/GeneralInvite/gi/gi_flag_1_on.png、tasks/Component/GeneralInvite/gi/image.json | 本地模块存在，文件命中 3/3 |

#### DraftDuel（39 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `287d59f0` | 2026-10-30 | kongdr | feat(DraftDuel): 新增协同对弈任务骨架与大厅消耗识别 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、module/config/config_manual.py、module/config/config_menu.py、module/config/config_model.py 等 10 个 | 本地无对应模块 |
| `1012030e` | 2026-10-30 | kongdr | feat(DraftDuel): 接入邀请好友与队长/队员模式 | 中 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/DraftDuel/assets.py、tasks/DraftDuel/config.py、tasks/DraftDuel/draft_duel/draft_duel_invitation.png 等 6 个 | 本地无对应模块 |
| `65a3ebfb` | 2026-10-30 | kongdr | fix(DraftDuel): 修正金币消耗识别范围 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/assets.py、tasks/DraftDuel/draft_duel/ocr.json | 本地无对应模块 |
| `c78b436f` | 2026-10-30 | kongdr | fix(DraftDuel): 免费次数按关键字识别 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/script_task.py | 本地无对应模块 |
| `fe1c0881` | 2026-10-30 | kongdr | feat(DraftDuel): 组队后点「战」进入选式神 | 中 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/DraftDuel/assets.py、tasks/DraftDuel/config.py、tasks/DraftDuel/draft_duel/draft_duel_start.png 等 6 个 | 本地无对应模块 |
| `613a32d0` | 2026-10-30 | kongdr | feat(DraftDuel): 接入选式神与推荐选择 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/DraftDuel/assets.py、tasks/DraftDuel/draft_duel/click.json、tasks/DraftDuel/draft_duel/dd.json、tasks/DraftDuel/draft_duel/draft_duel_0-4_settlement_page.png 等 16 个 | 本地无对应模块 |
| `8e483e5c` | 2026-10-30 | kongdr | fix(DraftDuel): 队员接受邀请后保持等待 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/script_task.py | 本地无对应模块 |
| `2013a89d` | 2026-10-30 | kongdr | feat(DraftDuel): 队员接入选式神 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/script_task.py | 本地无对应模块 |
| `5da8bbb5` | 2026-10-30 | kongdr | fix(DraftDuel): 推荐检查窗口延长到15秒 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/script_task.py | 本地无对应模块 |
| `5dd027bf` | 2026-10-30 | kongdr | feat(DraftDuel): 记录选中的式神并兼容自动选 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/script_task.py | 本地无对应模块 |
| `11ab2343` | 2026-10-30 | kongdr | feat(DraftDuel): 任务内使用 PP-OCRv6-small 识别 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | .gitignore、tasks/DraftDuel/model/NOTICE.txt、tasks/DraftDuel/model/rec_small_dict.txt、tasks/DraftDuel/script_task.py 等 5 个 | 本地无对应模块 |
| `1f7b10b1` | 2026-10-30 | kongdr | feat(DraftDuel): 接入选卡策略与五轮选人 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/DraftDuel/catalog.json、tasks/DraftDuel/duel_stats.py、tasks/DraftDuel/encyclopedia.json、tasks/DraftDuel/script_task.py 等 6 个 | 本地无对应模块 |
| `dac21615` | 2026-10-31 | xylolit-mu | feat(DraftDuel)：新增协同对弈任务与双实例协同框架 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | .gitignore、assets/i18n/zh-CN.json、config/template.json、module/config/config_manual.py 等 77 个 | 本地无对应模块 |
| `19e5a562` | 2026-11-01 | kongdr | fix(DraftDuel): V6 解码补空格类 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/v6_rec.py | 本地无对应模块 |
| `fc6b5070` | 2026-11-01 | LGG686 | fix(DraftDuel)：清理大轮结算浮窗并正确回到下一大轮 | 中 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/DraftDuel/assets.py、tasks/DraftDuel/draft/click.json、tasks/DraftDuel/draft/draft_win_fan.png、tasks/DraftDuel/draft/image.json 等 8 个 | 本地无对应模块 |
| `a12c4e42` | 2026-11-01 | xylolit-mu | 修复协斗识别与上阵、MuMu启动及棋局羁绊，完善契灵身份交换 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、module/cooperation.py、module/device/platform2/handlers/base.py、module/device/platform2/handlers/mumu12.py 等 17 个 | 本地无对应模块 |
| `d06f9672` | 2026-11-01 | kongdr418 | feat(DraftDuel): 整合协同选人、上阵及双端自动上阵流程 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | .gitignore、assets/DraftDuel/catalog.json、assets/DraftDuel/encyclopedia.json、assets/DraftDuel/strength_scores.json 等 36 个 | 本地无对应模块 |
| `0aba58d5` | 2026-11-01 | xylolit-mu | fix(DraftDuel): 校准式神头像裁切、缩放与阈值序列 | 中 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/DraftDuel/assets.py、tasks/DraftDuel/draft/frame.json、tasks/DraftDuel/draft/image.json、tasks/DraftDuel/runtime/deployment.py 等 5 个 | 本地无对应模块 |
| `f428bbec` | 2026-11-01 | kongdr418 | feat(DraftDuel): 添加队友推荐开关并拆分任务运行模块 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、tasks/DraftDuel/config.py、tasks/DraftDuel/runtime/__init__.py 等 14 个 | 本地无对应模块 |
| `bd2acfa3` | 2026-11-02 | xylolit-mu | fix(draft-duel): 按五张手牌中段验证上阵并限制开放时段 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | module/cooperation.py、module/draft_duel_schedule.py、tasks/DraftDuel/assets.py、tasks/DraftDuel/draft/frame.json 等 10 个 | 本地无对应模块 |
| `b08d8e2a` | 2026-11-02 | xylolit-mu | fix(draft-duel): 稳定采集手牌并在首局后释放模板 | 中 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/DraftDuel/assets.py、tasks/DraftDuel/draft/image.json、tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/matchmaking.py 等 6 个 | 本地无对应模块 |
| `a1a73b85` | 2026-11-02 | kongdr418 | fix(DraftDuel): 优化大厅头像匹配与上阵识别 | 中 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/DraftDuel/draft_duel/shikigami_head_badge_1.png、tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/portrait_match.py、tasks/DraftDuel/runtime/recognition.py 等 6 个 | 本地无对应模块 |
| `2ccacdee` | 2026-11-02 | kongdr418 | fix(DraftDuel): 补齐头像识别规则源与资源生成流程 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | dev_tools/assets_extract.py、tasks/DraftDuel/assets.py、tasks/DraftDuel/draft_duel/frame.json、tasks/DraftDuel/runtime/settings.py | 本地无对应模块 |
| `b491ac7a` | 2026-11-02 | xylolit-mu | fix(draft-duel): 按倒计时采集手牌并区分工作日开放时间 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | module/draft_duel_schedule.py、tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/round_state.py | 本地无对应模块 |
| `e0ea96ae` | 2026-11-02 | xylolit-mu | fix(draft-duel): 补测低阈值并回查未验证上阵槽位 | 中 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/runtime/cooperation.py、tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/portrait_match.py | 本地无对应模块 |
| `88e71d47` | 2026-11-02 | kongdr418 | fix(DraftDuel): 重拖时逐次上移起点与终点 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/runtime/deployment.py | 本地无对应模块 |
| `6466034f` | 2026-11-02 | kongdr418 | fix(DraftDuel): 取消队友就绪等待并在首局后等待三秒 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/runtime/battle.py、tasks/DraftDuel/runtime/cooperation.py | 本地无对应模块 |
| `255b2b25` | 2026-11-02 | kongdr418 | feat(DraftDuel): 完善离队结算与自动上阵判定 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | script.py、tasks/DraftDuel/assets.py、tasks/DraftDuel/draft_duel/draft_draft_share.png、tasks/DraftDuel/draft_duel/draft_duel_lobby_title.png 等 18 个 | 本地无对应模块 |
| `7bfb6fa3` | 2026-11-02 | kongdr418 | fix(DraftDuel): 区分新大轮大厅与待匹配页 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/runtime/battle.py、tasks/DraftDuel/runtime/cooperation.py、tasks/DraftDuel/runtime/invitation.py | 本地无对应模块 |
| `37049935` | 2026-11-02 | xylolit-mu | fix(draft-duel): 保留自动上阵名单并持久化本地加权数据 | 中 | 完全缺失 | 核心模块大改 | 单独评估 | .gitignore、tasks/DraftDuel/duel_stats.template.json、tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/round_state.py 等 6 个 | 本地无对应模块 |
| `cd7b6045` | 2026-11-02 | xylolit-mu | fix: 完善协斗大轮切换和棋局结算恢复 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | module/logger.py、tasks/Chess/assets.py、tasks/Chess/c/image.json、tasks/Chess/script_task.py 等 10 个 | 本地无对应模块 |
| `180d238a` | 2026-11-02 | xylolit-mu | fix(draft-duel): 清理大厅结算遮罩并重试邀请 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/runtime/invitation.py、tasks/DraftDuel/runtime/matchmaking.py | 本地无对应模块 |
| `4410d52e` | 2026-11-03 | kongdr418 | fix(DraftDuel): 手牌匹配逐级降阈值至0.5 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/portrait_match.py | 本地无对应模块 |
| `91f19356` | 2026-11-03 | kongdr418 | feat(DraftDuel): 统一阵容矩阵评分并同步队友选卡进度 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | dev_tools/draft_duel_matrix_checks.py、dev_tools/draft_duel_matrix_preview.py、tasks/DraftDuel/matrix.py、tasks/DraftDuel/runtime/cooperation.py 等 7 个 | 本地无对应模块 |
| `1c7552f5` | 2026-11-03 | kongdr418 | feat(DraftDuel): 补充火系名单与核心阵容条件评分 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | dev_tools/draft_duel_matrix_checks.py、tasks/DraftDuel/matrix.py、tasks/DraftDuel/strategy.py | 本地无对应模块 |
| `7112d251` | 2026-11-03 | kongdr418 | feat(DraftDuel): 联合队友候选选卡并移除错误式神条目 | 中 | 完全缺失 | 适配风险 | 谨慎评估 | assets/DraftDuel/catalog.json、assets/DraftDuel/strength_scores.json、dev_tools/draft_duel_matrix_checks.py、tasks/DraftDuel/matrix.py 等 6 个 | 本地无对应模块 |
| `c7e0c7bd` | 2026-11-09 | kongdr418 | feat(DraftDuel): 协同接入训练模型 | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/DraftDuel/config.py、tasks/DraftDuel/models/recommended-model.json、tasks/DraftDuel/runtime/deployment.py、tasks/DraftDuel/runtime/invitation.py 等 6 个 | 本地提交信息引用（已移植/合入） |
| `363d676b` | 2026-11-09 | kongdr418 | fix(DraftDuel): 缩短首次邀请超时 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DraftDuel/runtime/lifecycle.py | 本地提交信息引用（已移植/合入） |
| `446e869e` | 2026-11-10 | kongdr418 | feat(DraftDuel): 记录真实协同对局 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、tasks/DraftDuel/config.py、tasks/DraftDuel/runtime/battle.py 等 10 个 | 本地无对应模块 |

#### MetaDemon（33 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `e53cb30f` | 2026-11-05 | kongdr418 | feat(MetaDemon): 接入六星上供并修复刷票配置与探索退出 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、dev_tools/meta_demon_assistance_checks.py、dev_tools/meta_demon_checks.py 等 20 个 | 本地提交信息引用（已移植/合入） |
| `efcc78ad` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 适配新版超鬼王“祸至无日/祸主降临”活动界面 | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/MetaDemon/README.md、tasks/MetaDemon/assets.py、tasks/MetaDemon/config.py、tasks/MetaDemon/md/Screenshots_a2.png 等 47 个 | 本地模块存在，文件命中 22/47 |
| `c2943b5e` | 2026-11-08 | niuma-workwork | fix(MetaDemon): harden new-UI flow against click/stuck loops | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/MetaDemon/README.md、tasks/MetaDemon/script_task.py、tests/tasks/MetaDemon/test_meta_demon_flow.py | 本地模块存在，文件命中 1/3 |
| `4597cbe2` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 修复复审问题并补齐战斗路径单测 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/MetaDemon/README.md、tasks/MetaDemon/script_task.py、tests/tasks/MetaDemon/test_meta_demon_flow.py | 本地模块存在，文件命中 1/3 |
| `eebc4c4f` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 修正兜底点击计数与结算领奖顺序 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/MetaDemon/script_task.py、tests/tasks/MetaDemon/test_meta_demon_flow.py | 本地模块存在，文件命中 1/2 |
| `6d1277d3` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 结算领奖改为按奖励存在性判定结束 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/MetaDemon/script_task.py、tests/tasks/MetaDemon/test_meta_demon_flow.py | 本地模块存在，文件命中 1/2 |
| `e2a97257` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 修复活动栏翻页入口、胜利结算与退出卡死 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/MetaDemon/README.md、tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image.json、tasks/MetaDemon/script_task.py 等 5 个 | 本地模块存在，文件命中 3/5 |
| `419d0445` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 新增活动总览入口兜底，修复活动栏展开状态入口卡死 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/MetaDemon/README.md、tasks/MetaDemon/assets.py、tasks/MetaDemon/md/click.json、tasks/MetaDemon/md/ocr.json 等 6 个 | 本地模块存在，文件命中 3/6 |
| `02b4e18c` | 2026-11-08 | niuma-workwork | fix(MetaDemon): 战斗结算中等待，避免重复点击鬼王槽位 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/MetaDemon/README.md、tasks/MetaDemon/assets.py、tasks/MetaDemon/md/ocr.json、tasks/MetaDemon/script_task.py 等 5 个 | 本地模块存在，文件命中 3/5 |
| `8ff9806e` | 2026-11-08 | kongdr418 | feat: 对齐上游超鬼王并拆出刷票任务 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、config/template.json、dev_tools/activity_mode_selection_checks.py 等 29 个 | 本地模块存在，文件命中 16/29 |
| `835338cb` | 2026-11-10 | blylana | fix(MetaDemon): Update demon encounter image matching | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image.json、tasks/MetaDemon/md/image_2025.json、tasks/MetaDemon/md/md_battle_demon.png 等 14 个 | 台账已合入 |
| `8d48055c` | 2026-11-10 | blylana | chore(MetaDemon): Remove unused image assets | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/Screenshots_a2.png、tasks/MetaDemon/md/Screenshots_a3.png、tasks/MetaDemon/md/Screenshots_a4.png 等 18 个 | 台账已合入 |
| `411ef6d3` | 2026-11-10 | blylana | fix(MetaDemon): Recognize publicly shared demon bosses - add an image rule for the public status - i | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image_2025.json、tasks/MetaDemon/md/md_boos_public.png、tasks/MetaDemon/script_task.py | 台账已合入 |
| `4d75666a` | 2026-11-11 | kongdr418 | fix(MetaDemon): 更新鬼王页识别图 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image.json、tasks/MetaDemon/md/md_check_boss_page.png | 本地提交信息引用（已移植/合入） |
| `61d3f8cf` | 2026-11-11 | kongdr418 | fix(MetaDemon): 恢复一键配置 frame 并更新入口图标 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/frame.json、tasks/MetaDemon/md/quick_loadout_frame_badge_1.png | 本地提交信息引用（已移植/合入） |
| `ec8ef406` | 2026-11-11 | 微凉徒眸 | fix(MetaDemon): update UI assets and add auto_shared_boss config | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/MetaDemon/assets.py、tasks/MetaDemon/config.py、tasks/MetaDemon/md/md_enter2.png、tasks/MetaDemon/md/md_md_win.png 等 6 个 | 本地模块存在，文件命中 6/6 |
| `36dde020` | 2026-11-11 | kongdr418 | fix(MetaDemon): 礼包窗口优先点右上角亮叉 | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/boss_battle.py、tasks/MetaDemon/md/image.json、tasks/MetaDemon/md/md_shop_close.png | 本地提交信息引用（已移植/合入） |
| `4d910027` | 2026-11-11 | LGG686 | feat(MetaDemon)：超鬼王上供分享星级可配置 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Component/Costume/assets.py、tasks/Component/Costume/main4/image.json、tasks/Component/Costume/main4/main4_main_goto_town_4.png、tasks/MetaDemon/assistance.py 等 5 个 | 本地模块存在，文件命中 4/5 |
| `484337f5` | 2026-11-11 | 微凉徒眸 | fix(MetaDemon): Use recognition loop to close victory screen reliably | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MetaDemon/script_task.py | 本地提交信息引用（已移植/合入） |
| `ea8e72f3` | 2026-11-11 | kongdr418 | feat(MetaDemon): 上供支持自定义星级鬼王 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、config/template.json、tasks/MetaDemon/assistance.py 等 5 个 | 本地模块存在，文件命中 4/5 |
| `f4199538` | 2026-11-12 | kongdr418 | refactor(MetaDemon): 修复快速上阵 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/MetaDemon/quick_loadout.py | 本地模块存在，文件命中 0/1 |
| `5a752388` | 2026-11-12 | blylana | refactor(MetaDemon): Migrate battle_boss to battle_wait strategy hooks | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Component/GeneralBattle/battle_wait.py、tasks/MetaDemon/assets.py、tasks/MetaDemon/config.py 等 7 个 | 本地模块存在，文件命中 6/7 |
| `09571eb4` | 2026-11-12 | blylana | fix(MetaDemon): Ensure team unlock state before boss battle | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/lock/image.json、tasks/Component/GeneralBattle/lock/lock_team_lock.png、tasks/Component/GeneralBattle/lock/lock_team_unlock.png 等 5 个 | 本地模块存在，文件命中 5/5 |
| `83b82fd5` | 2026-11-12 | kongdr418 | fix(MetaDemon): 增加协同心跳等待并修复退出时截图过期 | 中 | 部分实现 | 可直接复用优化 | 可排期 | dev_tools/meta_demon_checks.py、dev_tools/meta_demon_cooperation_checks.py、module/cooperation.py、tasks/MetaDemon/boss_battle.py | 本地模块存在，文件命中 0/4 |
| `0ca19ebc` | 2026-11-12 | LGG686 | fix(MetaDemon)：协同等待对端启动而非固定 30 秒，导航前重新截图 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/DraftDuel/assets.py、tasks/DraftDuel/draft/frame.json、tasks/MetaDemon/assistance.py、tasks/MetaDemon/boss_battle.py 等 5 个 | 本地模块存在，文件命中 1/5 |
| `7478e169` | 2026-11-13 | kongdr418 | feat(MetaDemon): 支持选择上供召唤顺序并补齐中文显示 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、dev_tools/meta_demon_checks.py、tasks/MetaDemon/assistance.py 等 5 个 | 本地模块存在，文件命中 3/5 |
| `fe19476d` | 2026-11-13 | kongdr418 | feat(MetaDemon): 支持选择双端协同或独立好友上供 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、dev_tools/meta_demon_assistance_checks.py、dev_tools/meta_demon_cooperation_checks.py 等 7 个 | 本地模块存在，文件命中 3/7 |
| `64f1ee7d` | 2026-11-14 | pinkpig-Peppa | 移植 nearaura 二期任务修复与更新 (MetaDemon/SixRealms 月海/DailyTrifles/GameUi) | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/battle_wait.py、tasks/Component/GeneralBattle/lock/image.json、tasks/Component/GeneralBattle/lock/lock_team_lock.png 等 41 个 | 本地模块存在，文件命中 33/41 |
| `761614dc` | 2026-11-14 | LGG686 | fix(MetaDemon)：Retry friend share once and select recipients while scanning | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/MetaDemon/assets.py、tasks/MetaDemon/assistance.py、tasks/MetaDemon/md/image.json | 本地模块存在，文件命中 2/3 |
| `f449cb35` | 2026-11-15 | 微凉徒眸 | feat(MetaDemon): summon demon first when fatigue >= 61 (configurable) | 小 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/MetaDemon/config.py、tasks/MetaDemon/script_task.py | 本地模块存在，文件命中 3/3 |
| `838d4b7c` | 2026-11-15 | kongdr418 | fix(MetaDemon): 适配超鬼王新UI | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image.json、tasks/MetaDemon/md/md_md_check_main_page.png | 本地模块存在，文件命中 2/3 |
| `b615ec97` | 2026-11-15 | blylana | fix(MetaDemon): Update enter2 detection image and ROI | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image_2025.json、tasks/MetaDemon/md/md_enter2.png | 本地提交信息引用（已移植/合入） |
| `041e8686` | 2026-11-16 | blylana | fix(MetaDemon): Update detection images and ROIs | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/MetaDemon/assets.py、tasks/MetaDemon/md/image_2025.json、tasks/MetaDemon/md/md_enter2.png、tasks/MetaDemon/md/md_right_enter.png | 本地模块存在，文件命中 4/4 |

#### Chess（24 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1a9a1f61` | 2026-09-20 | xylolit-mu | 优化(百鬼棋局)：匹配竞态保护与阵容核对及周目标调度 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Chess/assets.py、tasks/Chess/c/scatter.json、tasks/Chess/runtime/round_state.py、tasks/Chess/script_task.py | 本地模块存在，文件命中 3/4 |
| `1d67a992` | 2026-09-20 | xylolit-mu | 新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程 | 大 | 已完整同步 | 适配风险 | 已处理 | script.py、tasks/Chess/test_branch/README.md、tasks/Chess/test_branch/__init__.py、tasks/Chess/test_branch/decision.py 等 10 个 | 本地提交信息引用（已移植/合入） |
| `3b161aba` | 2026-09-20 | xylolit-mu | Revert "新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程" | 大 | 部分实现 | 适配风险 | 低优先 | script.py、tasks/Chess/test_branch/README.md、tasks/Chess/test_branch/__init__.py、tasks/Chess/test_branch/decision.py 等 10 个 | 本地模块存在，文件命中 1/10（台账曾判不采纳，需复核） |
| `b94dc89c` | 2026-09-20 | xylolit-mu | 整合(百鬼棋局)：将状态决策流程迁入正式版本 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Chess/runtime/decision.py、tasks/Chess/runtime/events.py、tasks/Chess/runtime/state.py、tasks/Chess/runtime/state_loop.py 等 5 个 | 本地模块存在，文件命中 1/5 |
| `1aacf5a5` | 2026-09-29 | xylolit-mu | 调整(百鬼棋局):删除结算Scatter点击，回调至随机点击区域。 | 中 | 部分实现 | 适配风险 | 谨慎评估 | tasks/Chess/assets.py、tasks/Chess/c/scatter.json、tasks/Chess/script_task.py、tasks/GameUi/chess_battle.py 等 5 个 | 本地模块存在，文件命中 4/5 |
| `d43d8b56` | 2026-10-10 | LGG686 | refactor(assets)：按钮类调用收敛至通用模板并清理废弃资产 | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/Chess/assets.py、tasks/Chess/c/c_check_rank.png、tasks/Chess/c/c_chess_exit.png、tasks/Chess/c/c_chess_exit_cancel.png 等 38 个 | 本地模块存在，文件命中 37/38 |
| `6029ad08` | 2026-10-21 | kongdr | feat(Chess): 移植新版百鬼棋局（含帧规则与识别能力） | 大 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/click.py、module/atom/frame.py、module/atom/image.py、module/atom/scatter.py 等 412 个 | 本地模块存在，文件命中 22/412 |
| `4c5d633a` | 2026-10-21 | kongdr | feat(Chess): 同步百鬼投掷、黄金复制术与平安京阵容 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Chess/assets.py、tasks/Chess/c/c_hyakki_wait.png、tasks/Chess/c/click.json、tasks/Chess/c/image.json 等 39 个 | 本地模块存在，文件命中 12/39 |
| `acbdbf1c` | 2026-10-21 | kongdr | fix(Chess): 加宽鼬乐币 OCR 区域，修复刷满不停止 | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/Chess/assets.py、tasks/Chess/c/ocr.json | 本地模块存在，文件命中 2/2（台账曾判不采纳，需复核）P0 复核：本地 O_COIN 布局为 (141,659,87,25) 且走 DigitCounter+文本双路，上游 ROI 不适用 |
| `1410590f` | 2026-10-21 | kongdr | fix(Chess): 清理商店槽位点击记录，修复买卡触发 GameTooManyClickError | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/runtime/economy.py | 本地提交信息引用（已移植/合入） |
| `ce9903bf` | 2026-10-21 | xylolit-mu | fix(Chess): 手牌满且无可操作时出售一张阵容卡腾位 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/runtime/economy.py、tasks/Chess/runtime/hand_operations.py | 本地提交信息引用（已移植/合入） |
| `74425d03` | 2026-10-21 | xylolit-mu | fix(Chess): 同步上游百鬼主动投掷与特殊回合识别修复 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Chess/assets.py、tasks/Chess/c/c_stage_demon.png、tasks/Chess/c/c_stage_hyakki.png 等 17 个 | 本地模块存在，文件命中 10/17 |
| `45b5772d` | 2026-10-21 | xylolit-mu | fix(Chess): 百鬼无需御魂时等全员解锁后随机投掷 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Chess/runtime/hyakki_draft.py | 本地模块存在，文件命中 0/1 |
| `40e2f527` | 2026-10-21 | LGG686 | feat(chess)：同步上游百鬼棋局实现 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/Chess/README.md、tasks/Chess/assets.py、tasks/Chess/c/c_hyakki_wait.png 等 548 个 | 本地模块存在，文件命中 138/548 |
| `fa7a87e7` | 2026-10-21 | kongdr | fix(Chess): 买卡前清理槽位点击记录，修复 GameTooManyClickError | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/runtime/economy.py | 本地提交信息引用（已移植/合入） |
| `8f945012` | 2026-10-23 | kongdr418 | fix(Chess): 买卡成功与商店换卡后清理格子点击记录 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/runtime/economy.py | 本地模块存在，文件命中 1/1P0 复核：economy.py 购买确认与商店刷新后均已 click_record_remove |
| `9df707fb` | 2026-10-23 | kongdr418 | fix(Chess): 限制每轮买卡点击次数，重试失败后取消购买 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/runtime/economy.py、tasks/base_task.py | 本地提交信息引用（已移植/合入） |
| `8d64b1e4` | 2026-10-25 | LGG686 | fix(chess)：购买点击加单轮上限并在成功后清理记录 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Chess/runtime/economy.py、tasks/base_task.py | 本地模块存在，文件命中 2/2 |
| `31484b10` | 2026-10-26 | kongdr | feat(Chess): 同步上游阵容编辑器与 JSON 配置，斗技补充 ban 检测 | 大 | 部分实现 | 适配风险 | 谨慎评估 | .gitignore、assets/i18n/zh-CN.json、config/template.json、module/config/config_model.py 等 142 个 | 本地模块存在，文件命中 23/142 |
| `a9597e77` | 2026-10-26 | kongdr | fix(Chess): 卖卡与上御魂前清理点击记录，修复 GameTooManyClickError | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/runtime/hand_operations.py | 本地模块存在，文件命中 1/1P0 复核：be3a3790 已移植，hand_operations.py 卖卡/上御魂后清点击记录 |
| `d1ad2c09` | 2026-10-28 | kongdr | fix(Chess): 调整棋局规则搜索范围 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Chess/c/image.json | 本地提交信息引用（已移植/合入） |
| `5001c0bc` | 2026-10-31 | xylolit-mu | feat(Chess)：同步百鬼棋局策略、资源与标注器改动，Device 新增按住拖动 | 大 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/frame.py、module/device/control.py、module/device/press_and_drag.py、module/server/web/annotator/index.html 等 35 个 | 本地模块存在，文件命中 17/35 |
| `d3e81d3a` | 2026-10-31 | kongdr | feat(Chess): 同步新版百鬼棋局 | 大 | 部分实现 | 适配风险 | 谨慎评估 | config/template.json、module/atom/frame.py、module/device/control.py、module/device/press_and_drag.py 等 37 个 | 本地模块存在，文件命中 14/37 |
| `5a8f7385` | 2026-11-01 | kongdr | feat(Chess): OCR 接入 v6-small | 中 | 部分实现 | 核心模块大改 | 单独评估 | module/atom/frame.py、tasks/Chess/runtime/economy.py、tasks/Chess/runtime/frame_cards.py、tasks/Chess/runtime/ocr_v6.py 等 7 个 | 本地模块存在，文件命中 3/7 |

#### GameUi（23 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `9236651f` | 2026-09-18 | User | feat(GameUi): 移植 mine 新版页面导航模块到 dev | 大 | 已完整同步 | 适配风险 | 已处理 | tasks/AbyssShadows/script_task.py、tasks/ActivityShikigami/page.py、tasks/ActivityShikigami/script_task.py、tasks/ActivityShikigami/script_test.py 等 169 个 | 台账已覆盖 |
| `3a6e56c2` | 2026-09-19 | User | fix(GameUi): 修复导航超时不抛异常及 registry 遍历 bug | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py、tasks/GameUi/registry.py | 等价补丁 ecb5dbaa |
| `30d05824` | 2026-09-20 | xylolit-mu | 调整(通用页面)：统一奖励识别并注册误触页面与结算策略 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/GameUi/assets.py、tasks/GameUi/default_pages.py、tasks/GameUi/page.py、tasks/GameUi/page/image_activity.json 等 9 个 | 本地模块存在，文件命中 4/9 |
| `03429729` | 2026-09-30 | kongdr | fix(GameUi): 下调庭院标志识别阈值，修复游戏更新后登录卡死 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Login/service.py、tasks/GameUi/assets.py、tasks/GameUi/page/image_main.json | 本地模块存在，文件命中 3/3（台账曾判不采纳，需复核） |
| `9d39f0c0` | 2026-09-30 | xylolit-mu | 修复(庭院导航)：增加进入町中的保底点击 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py | 台账已覆盖 |
| `3252b071` | 2026-09-30 | User | fix(Login): 桌面登录期处理 MPay 弹窗，避免误判未知页面 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py、tasks/Restart/login.py | 本地提交信息引用（已移植/合入） |
| `a8afe598` | 2026-10-01 | xylolit-mu | 修复(闲庭导航)：优先识别闲庭并排除庭院误判 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/default_pages.py | 本地提交信息引用（已移植/合入） |
| `92223c5b` | 2026-10-01 | neptine | fix(GameUi): Restore I_CHECK_FRIENDS image and ROI for friend page detection | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/assets.py、tasks/GameUi/game_ui.py、tasks/GameUi/page/image_main.json、tasks/GameUi/page/page_check_friends.png | 等价补丁 e6f10c8a |
| `606517be` | 2026-10-02 | User | fix(GameUi): 适配庭院下移后的庭院标志识别区域 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/assets.py、tasks/GameUi/page/image_main.json | 本地提交信息引用（已移植/合入） |
| `431e3458` | 2026-10-02 | xylolit-mu | 回退(页面导航)：移除町中固定位置点击保底 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py | 本地提交信息引用（已移植/合入） |
| `52608081` | 2026-10-03 | neptine | fix(GameUi): Restore touch fish page navigation - register the touch fish page in the shared page de | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/default_pages.py、tasks/GameUi/page.py、tasks/WeeklyTrifles/script_task.py | 本地提交信息引用（已移植/合入） |
| `1c3accdf` | 2026-10-05 | User | feat(Navigator)：goto_page 到达判定支持 accepted_pages | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py | 等价补丁 ff3e23ce |
| `9ce0fd2f` | 2026-10-11 | neptine | fix(GameUi): Add circular back button to unknown page recovery | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py | 等价补丁 317f3170 |
| `a9eb4843` | 2026-10-11 | kongdr | fix(GameUi): 修复导航交替换路时空转不报错 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py | 等价补丁 f078e039 |
| `0311c189` | 2026-10-14 | LGG686 | fix(GameUi)：补充种树关闭按钮，调整未知页关闭动作顺序 | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GameUi/navigator.py、tasks/KekkaiUtilize/assets.py、tasks/KekkaiUtilize/realm/image.json | 本地提交信息引用（已移植/合入） |
| `476617e0` | 2026-10-22 | LGG686 | fix(GameUi)：删除与 GeneralBuff 重名的 I_CLOSE_RED | 中 | 已完整同步 | 适配风险 | 已处理 | tasks/AreaBoss/assets.py、tasks/AreaBoss/res/image.json、tasks/AreaBoss/res/res_close_red.png、tasks/Chess/script_task.py 等 7 个 | 本地提交信息引用（已移植/合入） |
| `eddc6171` | 2026-10-29 | leovefy | fix(GameUi): 兼容商店两种招牌图片，修复反复进出商店的问题 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/DailyTrifles/script_task.py、tasks/GameUi/assets.py、tasks/GameUi/default_pages.py、tasks/GameUi/page/image_main.json 等 7 个 | 本地模块存在，文件命中 6/7 |
| `fd7e20a5` | 2026-11-11 | LLLLLUO | fix(GameUi): tolerate exploration marker horizontal shifts | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/GameUi/page/image_exploration.json | 本地模块存在，文件命中 1/1 |
| `0b8ef1cb` | 2026-11-11 | LLLLLUO | fix(GameUi): sync generated exploration marker rule | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/GameUi/assets.py | 本地模块存在，文件命中 1/1 |
| `b8624012` | 2026-11-11 | LLLLLUO | test(GameUi): cover shifted exploration markers | 小 | 部分实现 | 可直接复用优化 | 可排期 | tests/tasks/GameUi/test_exploration_marker.py | 本地模块存在，文件命中 0/1 |
| `f9e2ec0f` | 2026-11-11 | LLLLLUO | test(GameUi): add exploration marker regression cases | 小 | 部分实现 | 可直接复用优化 | 可排期 | tests/tasks/GameUi/test_exploration_marker.py | 本地模块存在，文件命中 0/1 |
| `81bb25a7` | 2026-11-12 | kongdr418 | fix(GameUi): 更新商店识别模板并补全棋局排名页规则 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/GameUi/assets.py、tasks/GameUi/page/image_chess.json、tasks/GameUi/page/image_main.json、tasks/GameUi/page/page_check_mall.png | 本地模块存在，文件命中 4/4 |
| `f1ba2a5c` | 2026-11-12 | blylana | fix(GameUi): Update mall page detection image | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/GameUi/assets.py、tasks/GameUi/page/image_main.json、tasks/GameUi/page/page_check_mall.png | 本地模块存在，文件命中 3/3 |

#### WantedQuests（23 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1cda0166` | 2026-09-27 | xylolit-mu | 修复(悬赏封印)：秘闻结算后点击返回已知挑战界面 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WantedQuests/script_task.py | 等价补丁 dbb24038 |
| `5d89c37c` | 2026-10-04 | Hurry2 | feat(WantedQuests): 适配部分秘闻奖励结算后的一次性对话 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/WantedQuests/assets.py、tasks/WantedQuests/chanllenge/chanllenge_wqc_battle_end_talks.png、tasks/WantedQuests/chanllenge/image.json、tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 3/4 |
| `dd51be24` | 2026-10-05 | LGG686 | fix(WantedQuests)：悬赏卡位小字叠背景导致 OCR 漏识时不重试 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `f0c8473d` | 2026-10-12 | LGG686 | fix(WantedQuests)：2x 重扫未命中进度时放宽检测框阈值再扫一次 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `1eeee5ff` | 2026-10-15 | kongdr | fix(WantedQuests): 下调秘闻剧情对话模板阈值 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/assets.py、tasks/WantedQuests/chanllenge/image.json | 本地模块存在，文件命中 2/2 |
| `9afe3d32` | 2026-10-15 | neptine | fix(WantedQuests): Detect selected friends when inviting #1939 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WantedQuests/script_task.py | 等价补丁 1422d173 |
| `cc131ec5` | 2026-10-16 | LGG686 | fix(WantedQuests)：悬赏去重集合改为按卡清零 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `82fae57e` | 2026-10-25 | LGG686 | fix(WantedQuests)：悬赏目标改用子串匹配避漏判 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `b37b56d2` | 2026-10-27 | LGG686 | fix(WantedQuests)：适配新 UI 的悬赏封印界面 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/gg_g_accept.png、tasks/GlobalGame/gg/gg_g_reject.png、tasks/GlobalGame/gg/image.json 等 28 个 | 本地模块存在，文件命中 26/28 |
| `c4d40686` | 2026-10-28 | kongdr | fix(WantedQuests): 适配封印悬赏新UI，更新追踪按钮图标与坐标并补协作弹窗新图标 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/gg_ng_accept.png、tasks/GlobalGame/gg/gg_ng_ignore.png、tasks/GlobalGame/gg/gg_ng_reject.png 等 15 个 | 本地模块存在，文件命中 12/15 |
| `7b8155d9` | 2026-10-28 | kongdr | fix(WantedQuests): 重截前往按钮图标，适配悬赏列表新布局 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/WantedQuests/assets.py、tasks/WantedQuests/wq/image.json、tasks/WantedQuests/wq/wq_goto_1.png、tasks/WantedQuests/wq/wq_goto_2.png 等 6 个 | 本地模块存在，文件命中 6/6 |
| `c3a88af9` | 2026-10-28 | kongdr | fix(WantedQuests): 详情页改用前往按钮判断，修复新UI下无法进入悬赏详情 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `ac482cf2` | 2026-10-28 | kongdr | fix(WantedQuests): 调整悬赏列表 OCR 区域，适配新UI排版 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WantedQuests/assets.py、tasks/WantedQuests/wq/ocr.json | 本地模块存在，文件命中 2/2P0 复核：本地已换成 921a2b82 的新 UI OCR 值 |
| `d296406e` | 2026-10-28 | LGG686 | fix(WantedQuests)：适配新版界面神秘悬赏跳过并合并重复追踪资产 | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/image.json、tasks/WantedQuests/assets.py、tasks/WantedQuests/script_task.py 等 10 个 | 本地模块存在，文件命中 10/10 |
| `c695e50d` | 2026-10-28 | kongdr418 | fix(WantedQuests): 识别神秘妖怪悬赏后关闭面板并跳过 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/WantedQuests/assets.py、tasks/WantedQuests/script_task.py、tasks/WantedQuests/wq/image.json、tasks/WantedQuests/wq/wq_exit.png | 本地模块存在，文件命中 4/4（台账曾判不采纳，需复核） |
| `9a6eb783` | 2026-10-28 | kongdr418 | fix(WantedQuests): 修复取消追踪卡死与数量识别 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `921a2b82` | 2026-10-28 | User | fix(WantedQuests): 适配悬赏封印新 UI 并清理孤立资产 | 大 | 已完整同步 | 适配风险 | 已处理 | tasks/WantedQuests/assets.py、tasks/WantedQuests/invite/image.json、tasks/WantedQuests/invite/invite_wq_invite_1.png、tasks/WantedQuests/invite/invite_wq_invite_2.png 等 23 个 | 本地提交信息引用（已移植/合入） |
| `df572d01` | 2026-11-03 | leovefy | fix(WantedQuests): 悬赏地点数量识别失败时收紧区域重试 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |
| `09bdec66` | 2026-11-04 | kongdr418 | fix(WantedQuests): 更新悬赏邀请模板及协作任务识别区域 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/WantedQuests/assets.py、tasks/WantedQuests/invite/image.json、tasks/WantedQuests/invite/invite_wq_invite_1.png、tasks/WantedQuests/invite/invite_wq_invite_2.png 等 5 个 | 本地模块存在，文件命中 5/5 |
| `5ac08e11` | 2026-11-04 | kongdr418 | fix(WantedQuests): 扩大追踪按钮识别范围 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/assets.py、tasks/WantedQuests/wq/image.json | 本地模块存在，文件命中 2/2 |
| `181801d1` | 2026-11-04 | huangrunheng | Update script_task.py | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WantedQuests/script_task.py | 台账已合入 |
| `bf71e3a5` | 2026-11-04 | LGG686 | fix(WantedQuests)：重做协斗协作类型模板并放宽好友邀请筛选 | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/BondlingFairyland/assets.py、tasks/BondlingFairyland/bf/ocr.json、tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/image.json 等 14 个 | 本地提交信息引用（已移植/合入） |
| `a3e6e028` | 2026-11-05 | neptine | fix(WantedQuests): remove invalid characters | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WantedQuests/script_task.py | 本地模块存在，文件命中 1/1 |

#### module/server（22 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `f4767278` | 2026-10-03 | User | fix(server): annotator 静态资源加 Cache-Control no-cache | 小 | 已完整同步 | 适配风险 | 已处理 | module/server/app.py | 等价补丁 79269844 |
| `9f07623b` | 2026-10-17 | kongdr | feat(Server): 新增模拟器画面截取接口 | 中 | 已完整同步 | 适配风险 | 已处理 | module/server/app.py、module/server/screen_capture_worker.py、module/server/screen_router.py | 等价补丁 112de0e4 |
| `89e3ad09` | 2026-10-17 | kongdr | fix(Server): 画面截图改用 adb 直抓，不再干扰运行中的任务 | 中 | 部分实现 | 适配风险 | 谨慎评估 | module/server/screen_capture_worker.py、module/server/screen_router.py | 本地模块存在，文件命中 2/2（台账曾判不采纳，需复核） |
| `92bb2f2e` | 2026-10-21 | LGG686 | feat(core)：引入 RuleFrame 识别与灰度匹配，支持网络异常恢复 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、dev_tools/assets_extract.py、dev_tools/assets_test.py 等 19 个 | 本地模块存在，文件命中 18/19 |
| `09c1802d` | 2026-10-25 | xylolit-mu | 新增棋局阵容编辑工具与JSON配置，完善站位检测及任务协同 | 大 | 部分实现 | 适配风险 | 谨慎评估 | .gitignore、assets/i18n/zh-CN.json、config/template.json、module/config/config_model.py 等 139 个 | 本地模块存在，文件命中 21/139 |
| `1f5149f3` | 2026-10-29 | kongdr | fix(screen): 截图前自动重连 adb，避免设备掉线导致截图失败 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/server/screen_capture_worker.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核） |
| `f99d75c2` | 2026-11-11 | kongdr418 | fix(server): 修复配置导入时对泛型注解的误判 | 小 | 已完整同步 | 适配风险 | 已处理 | module/server/config_manager.py | 等价补丁 9a2ae877 |
| `78234f6d` | 2026-11-13 | LGG686 | perf(deploy): speed up startup and isolate annotator preview frames | 中 | 部分实现 | 适配风险 | 谨慎评估 | deploy/git.py、deploy/pip.py、module/device/screenshot.py、module/server/home_router.py 等 6 个 | 本地模块存在，文件命中 6/6 |
| `50dec6ce` | 2026-11-14 | pinkpig-Peppa | 移植统计/日志模块, 新增看门狗与 Apprise 通知 | 大 | 部分实现 | 适配风险 | 不引入 | module/notify/notify.py、module/server/api_logger.py、module/server/app.py、module/server/log_router.py 等 8 个 | 本地模块存在，文件命中 7/8 |
| `5db01e76` | 2026-11-14 | pinkpig-Peppa | 新增 /tool/doctor 一键体检接口 | 大 | 部分实现 | 适配风险 | 谨慎评估 | module/server/doctor.py、module/server/tool_router.py | 本地模块存在，文件命中 1/2 |
| `adfa6e84` | 2026-11-18 | LGG686 | feat(Android)：Hot-update OAS source from a Git repository | 大 | 部分实现 | 适配风险 | 不引入 | module/server/android_router.py、module/server/hot_update.py | 本地模块存在，文件命中 0/2（台账曾判不采纳，需复核） |
| `7b2f2492` | 2026-11-19 | LGG686 | fix(server)：keep-alive 超时拉长到 75 秒 | 小 | 已完整同步 | 适配风险 | 已处理 | server.py | 本地提交信息引用（已移植/合入） |
| `52f23c56` | 2026-11-19 | LGG686 | fix(server)：局域网口令改为可选并支持 Cookie 会话 | 小 | 部分实现 | 适配风险 | 不引入 | module/server/auth.py | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `17bb2993` | 2026-11-20 | LGG686 | feat(android)：同步适配批次到 OASA | 大 | 部分实现 | 适配风险 | 不引入 | deploy/template、module/device/method/oasaos.py、module/server/android_router.py、module/server/hot_update.py 等 8 个 | 本地模块存在，文件命中 3/8（台账曾判不采纳，需复核） |
| `f7a3f643` | 2026-11-20 | LGG686 | fix(server)：补齐提交历史接口并输出作者 | 小 | 部分实现 | 适配风险 | 不引入 | module/server/android_router.py、module/server/hot_update.py | 本地模块存在，文件命中 0/2（台账曾判不采纳，需复核） |
| `8b06fd35` | 2026-11-21 | LGG686 | fix(server)：修复提交历史拉不到与首次为空 | 小 | 部分实现 | 适配风险 | 不引入 | module/server/hot_update.py | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `bd4614ac` | 2026-11-21 | LGG686 | feat(server)：条件挂载 /gui 网页控制台 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/server/app.py | 本地模块存在，文件命中 1/1 |
| `4bf1a8b7` | 2026-11-21 | LGG686 | fix(server)：git 残留锁自动清理重试 | 小 | 部分实现 | 适配风险 | 不引入 | module/server/hot_update.py | 本地模块存在，文件命中 0/1 |
| `3051c38c` | 2026-11-21 | LGG686 | fix(server)：热更首拉超时残留锁与历史面板空转 | 小 | 部分实现 | 适配风险 | 不引入 | module/server/hot_update.py | 本地模块存在，文件命中 0/1 |
| `c4f533ab` | 2026-11-21 | LGG686 | fix(server)：提交历史优先返回已拉到的远端列表 | 小 | 部分实现 | 适配风险 | 不引入 | module/server/hot_update.py | 本地模块存在，文件命中 0/1 |
| `96a34f39` | 2026-11-21 | LGG686 | feat(server)：提交历史返回描述正文并支持仅重启 OAS | 小 | 部分实现 | 适配风险 | 不引入 | module/server/android_router.py、module/server/hot_update.py | 本地模块存在，文件命中 0/2 |
| `43339741` | 2026-11-21 | LGG686 | feat(server)：网页控制台 /gui 支持自动更新 | 中 | 部分实现 | 适配风险 | 谨慎评估 | module/server/app.py、module/server/home_router.py、module/server/web_gui_updater.py | 本地模块存在，文件命中 2/3 |

#### FrogBoss（21 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `b4168071` | 2026-09-28 | xylolit-mu | 调整(对弈竞猜):更新十周年对弈竞猜相关素材，新增非等权策略。 | 大 | 已完整同步 | 适配风险 | 已处理 | .gitignore、configs/customer_config.json、script.py、tasks/Component/GeneralInvite/assets.py 等 29 个 | 本地提交信息引用（已移植/合入） |
| `48164d4e` | 2026-09-30 | kongdr | feat(FrogBoss): 适配十周年素材并新增非等权预测策略 frog_oas | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/FrogBoss/assets.py、tasks/FrogBoss/config.py、tasks/FrogBoss/fb/fb_bet_left.png、tasks/FrogBoss/fb/fb_bet_right.png 等 18 个 | 本地模块存在，文件命中 18/18 |
| `9b3c9b67` | 2026-09-30 | xylolit-mu | 新增(对弈竞猜)：移植OAS胜率策略与赛果记录 | 中 | 已完整同步 | 核心模块大改 | 已处理 | .gitignore、tasks/FrogBoss/config.py、tasks/FrogBoss/frog_oas.py、tasks/FrogBoss/oas_sources.py 等 6 个 | 等价补丁 3c37f65c |
| `86b2a7ef` | 2026-09-30 | xylolit-mu | 调整(对弈竞猜)：更新活动素材与识别区域 | 大 | 已完整同步 | 适配风险 | 已处理 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_bet_left.png、tasks/FrogBoss/fb/fb_bet_right.png、tasks/FrogBoss/fb/fb_bet_success.png 等 14 个 | 等价补丁 0aa81e9f |
| `bcb27d7f` | 2026-09-30 | xylolit-mu | 修复(对弈竞猜)：通过可见记录页补结算并启用胜率权重 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_frog_last_lose.png、tasks/FrogBoss/fb/fb_frog_last_select_blue.png、tasks/FrogBoss/fb/fb_frog_last_select_red.png 等 16 个 | 本地模块存在，文件命中 16/16 |
| `8dcf5b59` | 2026-09-30 | kongdr | fix(FrogBoss): 全部图片规则阈值下调为 0.7 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/image.json、tasks/FrogBoss/fb/image2.json | 本地模块存在，文件命中 3/3 |
| `414d42df` | 2026-09-30 | xylolit-mu | 调整(对弈竞猜):调整竞猜对应素材。 | 中 | 部分实现 | 适配风险 | 谨慎评估 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_bet_left.png、tasks/FrogBoss/fb/fb_bet_right.png、tasks/FrogBoss/fb/fb_bet_success_box.png 等 8 个 | 本地模块存在，文件命中 8/8 |
| `fb06df05` | 2026-09-30 | kongdr | fix(FrogBoss): 重截 bet_failure 模板并修正 ROI | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_bet_failure.png、tasks/FrogBoss/fb/image.json | 本地模块存在，文件命中 3/3 |
| `1f1fdbef` | 2026-09-30 | xylolit-mu | 调整(对弈竞猜):调整竞猜对应素材。 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_frog_boss_rest.png、tasks/FrogBoss/fb/image2.json | 本地模块存在，文件命中 3/3 |
| `27dc33a4` | 2026-09-30 | kongdr | fix(FrogBoss): 调整对弈竞猜策略逻辑 | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/FrogBoss/frog_oas.py | 本地模块存在，文件命中 1/1P0 复核：本地为带符号权重+负共识设计（a9cad51c/670f194a），test_frog_oas.py 固化冷启动等票 |
| `1ad34a78` | 2026-09-30 | xylolit-mu | 修复(对弈竞猜)：无操作五秒时保底点击下一局 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/FrogBoss/script_task.py | 台账已覆盖 |
| `16d1205d` | 2026-09-30 | xylolit-mu | 修复(对弈竞猜)：更新失败结果识别素材 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_bet_failure.png、tasks/FrogBoss/fb/image.json | 本地模块存在，文件命中 3/3 |
| `1eb9fe3f` | 2026-10-01 | xylolit-mu | 修复(对弈竞猜)：处理下一局后的休息状态并更新资源说明 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/image.json、tasks/FrogBoss/script_task.py | 台账已覆盖 |
| `5f408cd4` | 2026-10-01 | xylolit-mu | 修复(对弈竞猜)：优先处理下注弹窗并限制重复点击 | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/image.json、tasks/FrogBoss/script_task.py、tasks/FrogBoss/test_betting_flow.py | 台账已覆盖 |
| `fcd496de` | 2026-10-01 | kongdr | fix(FrogBoss): 修正全员零权重时随机下注 | 中 | 部分实现 | 可直接复用优化 | 可排期 | dev_tools/frog_oas_check.py、tasks/FrogBoss/frog_oas.py | 本地模块存在，文件命中 1/2 |
| `98ce82bb` | 2026-10-01 | xylolit-mu | 调整(对弈竞猜)：同步记录页面与最新识别素材 | 大 | 已完整同步 | 适配风险 | 已处理 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_bet_failure.png、tasks/FrogBoss/fb/fb_bet_left.png、tasks/FrogBoss/fb/fb_bet_right.png 等 19 个 | 等价补丁 6f9b99eb |
| `670f194a` | 2026-10-01 | xylolit-mu | 修复(对弈竞猜)：移植记录补结算、下注恢复与负权重策略 | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/FrogBoss/frog_oas.py、tasks/FrogBoss/record_reader.py、tasks/FrogBoss/script_task.py、tasks/FrogBoss/test_betting_flow.py 等 5 个 | 等价补丁 2d1dbac0 |
| `e13fbc4a` | 2026-10-01 | kongdr | refactor(FrogBoss): 精简自检脚本注释 | 小 | 部分实现 | 可直接复用优化 | 可排期 | dev_tools/frog_oas_check.py | 本地模块存在，文件命中 0/1 |
| `a9cad51c` | 2026-10-02 | xylolit-mu | 调整(对弈竞猜)：引入负向胜率权重 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/FrogBoss/frog_oas.py、tasks/FrogBoss/test_frog_oas.py | 台账已覆盖 |
| `5a2d99bf` | 2026-10-02 | xylolit-mu | 修复(对弈竞猜)：处理商店弹窗并二次确认任务结束 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_forg_mall_close.png、tasks/FrogBoss/fb/fb_frog_mall.png、tasks/FrogBoss/fb/image2.json 等 6 个 | 本地提交信息引用（已移植/合入） |
| `9ec93a44` | 2026-10-05 | kongdr | fix(FrogBoss): 修复下注确认被弹窗遮挡导致的死循环 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/FrogBoss/script_task.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核）P0 复核：本地 I_GOLD_30_CHECK 关弹窗 + submit_attempts<3 等价；另并 f67e5a80 结束标志加固 7aa7e23d |

#### Exploration（19 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `028ca1f8` | 2026-09-25 | User | feat(Exploration): 主线/玩法tab接入导航系统 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/base.py、tasks/Exploration/page.py、tasks/Exploration/res/click.json 等 8 个 | 本地提交信息引用（已移植/合入） |
| `d7d98690` | 2026-09-29 | neptine | fix(Exploration): Restore I_FLAG_2_ON ROI to unblock friend tab switching  #1844 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/solo.py | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `c56e2c9b` | 2026-10-05 | User | feat(Exploration)：选关改为在主线 tab 下进行，新增 tab 页导航 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/base.py、tasks/Exploration/page.py、tasks/Exploration/res/click.json 等 7 个 | 本地提交信息引用（已移植/合入） |
| `af6d1bcb` | 2026-10-11 | Vanity | fix(Exploration): 修复特定UP类型找怪提前退出及滑屏边缘检测问题 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/base.py、tasks/Exploration/solo.py | 本地模块存在，文件命中 1/2 |
| `c8f93d1b` | 2026-10-11 | Vanity | fix(Exploration): address review feedback on timer reset and swipe edge check | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/solo.py | 本地模块存在，文件命中 0/1 |
| `2bc21f59` | 2026-10-11 | Vanity | refactor(Exploration): 根据Review建议抽取滑屏与重置辅助方法，消除重复代码 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/solo.py | 本地模块存在，文件命中 0/1 |
| `69a0fc4f` | 2026-10-11 | Vanity | perf(Exploration): 按UP类型自适应滑屏找怪策略与死代码精简 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/solo.py | 本地模块存在，文件命中 0/1 |
| `aaac78b3` | 2026-10-12 | llBai | change(open_expect_level): reverse swipe | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Exploration/base.py | 台账已覆盖 |
| `372ef8f3` | 2026-10-12 | llBai | add S_SWIPE_LEVEL_DOWN_PRO | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/base.py | 本地提交信息引用（已移植/合入） |
| `92578cd0` | 2026-10-13 | neptine | fix(Exploration): Correct realm raid ticket OCR region #1926 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/res/ocr.json | 等价补丁 95cfcb47 |
| `54803c50` | 2026-10-13 | llBai | delete  S_SWIPE_LEVEL_DOWN_PRO | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/base.py | 本地提交信息引用（已移植/合入） |
| `614b6b84` | 2026-10-13 | llBai | Revert "delete  S_SWIPE_LEVEL_DOWN_PRO" | 小 | 部分实现 | 可直接复用优化 | 低优先 | tasks/Exploration/assets.py、tasks/Exploration/base.py | 本地模块存在，文件命中 2/2 |
| `e56482ca` | 2026-10-13 | llBai | Revert "add S_SWIPE_LEVEL_DOWN_PRO" | 小 | 部分实现 | 可直接复用优化 | 低优先 | tasks/Exploration/assets.py、tasks/Exploration/base.py | 本地模块存在，文件命中 2/2 |
| `107e9542` | 2026-10-19 | neptine | fix(Exploration): Prevent premature back navigation during exit #1935 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Restart/script_task.py | 本地提交信息引用（已移植/合入） |
| `a70757b1` | 2026-10-19 | neptine | fix(Exploration): Prevent premature back navigation during exit #1935 | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/Exploration/base.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核）P0 复核：本地无 I_BACK_YOLLOW，退出走页面导航，补丁前提不存在 |
| `fb3c10a0` | 2026-11-10 | kongdr | fix(Exploration): 突破票 OCR 改用超鬼王时期 ROI | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/res/ocr.json | 本地提交信息引用（已移植/合入） |
| `f4bf42bc` | 2026-11-18 | kongdr418 | fix(Exploration): 恢复常规突破券 OCR 区域 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/base.py | 本地模块存在，文件命中 1/1 |
| `0f99fd02` | 2026-11-18 | LGG686 | fix(Exploration)：Restore realm raid ticket OCR after MetaDemon event | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Exploration/assets.py、tasks/Exploration/base.py、tasks/Exploration/res/ocr.json、tasks/MetaDemon/md/md_main_goto_metademon.png | 本地模块存在，文件命中 3/4 |
| `bb6f2103` | 2026-11-18 | blylana | fix(Exploration): Narrow realm raid ticket OCR region to drop extra leading digit  #7 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Exploration/assets.py、tasks/Exploration/res/ocr.json | 本地提交信息引用（已移植/合入） |

#### ActivityShikigami（14 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ef48a3fd` | 2026-09-20 | User | 适配(式神活动)：按本期Boss入口更新页面与识别资源 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/activities/normal.py、tasks/ActivityShikigami/as/climb/as_lock.png、tasks/ActivityShikigami/as/climb/as_unlock.png、tasks/ActivityShikigami/as/climb/image.json 等 7 个 | 本地模块存在，文件命中 3/7 |
| `d9c877a4` | 2026-09-20 | xylolit-mu | 调整(式神活动探索)：取消滑动与模式筛选并统一奖励处理 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、tasks/ActivityShikigami/activities/exploration.py、tasks/ActivityShikigami/as/exploration/exploration_event_reward_reward.png 等 9 个 | 本地模块存在，文件命中 4/9 |
| `1f9e14d4` | 2026-09-20 | xylolit-mu | 优化(式神活动爬塔)：修正票数追踪并清理旧战斗资源 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/activities/normal.py、tasks/ActivityShikigami/as/climb/image.json、tasks/ActivityShikigami/as/climb/ocr.json、tasks/ActivityShikigami/as/climb/scatter.json 等 8 个 | 本地模块存在，文件命中 3/8 |
| `e4935560` | 2026-09-27 | xylolit-mu | 优化(式神活动)：门票选项为空时跳过门票爬塔 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/activities/normal.py、tasks/ActivityShikigami/as/climb/climb_orchi_select_none.png、tasks/ActivityShikigami/as/climb/image.json、tasks/ActivityShikigami/assets.py | 本地模块存在，文件命中 2/4 |
| `b3d6fe98` | 2026-10-11 | neptine | fix(ActivityShikigami): Update | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/as/as_lock.png、tasks/ActivityShikigami/as/as_shi.png、tasks/ActivityShikigami/as/as_to_battle_main.png、tasks/ActivityShikigami/as/as_to_battle_main_2.png 等 15 个 | 本地模块存在，文件命中 9/15（台账曾判不采纳，需复核） |
| `43c7f334` | 2026-10-11 | neptine | fix(ActivityShikigami): Broaden pass screen detection area | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/assets.py、tasks/ActivityShikigami/fire/image.json | 本地模块存在，文件命中 1/2（台账曾判不采纳，需复核） |
| `5cf103ea` | 2026-10-12 | LGG686 | feat(activity)：适配当期爬塔分家布局并统一挑战按钮为 OCR 引导 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/activities/normal.py、tasks/ActivityShikigami/as/climb/as_act_fire.png、tasks/ActivityShikigami/as/climb/as_ap_lock.png、tasks/ActivityShikigami/as/climb/as_ap_unlock.png 等 20 个 | 本地模块存在，文件命中 4/20 |
| `fe98ffef` | 2026-10-20 | davidyangkunlong | UpdateClimbBossResources | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/as/as_check_battle_boss.png、tasks/ActivityShikigami/as/as_to_battle_boss.png、tasks/ActivityShikigami/assets.py、tasks/ActivityShikigami/script_task.py | 本地模块存在，文件命中 4/4（台账曾判不采纳，需复核） |
| `6084f210` | 2026-10-20 | LGG686 | fix(ActivityShikigami)：爬塔挑战遇弹窗改为关闭后重试 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/activities/normal.py | 本地模块存在，文件命中 1/1 |
| `f339b5a6` | 2026-10-21 | LGG686 | feat(ActivityShikigami)：适配 OASX v0.3.16 式神活动配置契约 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/ActivityShikigami/activities/normal.py、tasks/ActivityShikigami/config.py、tasks/ActivityShikigami/script_task.py | 本地模块存在，文件命中 4/4 |
| `0b7ee83e` | 2026-10-27 | LGG686 | feat(ActivityShikigami)：探索新增委派模式并重裁活动识别模板 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/activities/exploration.py、tasks/ActivityShikigami/as/climb/as_climb_mode_ap.png、tasks/ActivityShikigami/as/climb/climb_to_battle_ap.png、tasks/ActivityShikigami/as/climb/image.json 等 25 个 | 本地模块存在，文件命中 2/25 |
| `48ba3280` | 2026-10-31 | LGG686 | fix(ActivityShikigami)：探索剧情结束改为奖励面板或主界面二者其一 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/ActivityShikigami/activities/exploration.py | 本地模块存在，文件命中 0/1 |
| `df43725c` | 2026-11-02 | LGG686 | fix(ActivityShikigami)：重写探索剧情跳过流程，更新委派入口模板 | 中 | 部分实现 | 适配风险 | 谨慎评估 | tasks/ActivityShikigami/activities/exploration.py、tasks/ActivityShikigami/as/exploration/exploration_exp_delegate.png、tasks/ActivityShikigami/as/exploration/image.json、tasks/ActivityShikigami/assets.py 等 5 个 | 本地模块存在，文件命中 1/5 |
| `9d7eb7e2` | 2026-11-05 | kongdr418 | feat: 移植超鬼王与活动控制并适配设置布局 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、dev_tools/activity_mode_selection_checks.py、dev_tools/assets_extract.py 等 184 个 | 本地模块存在，文件命中 32/184 |

#### module/device（14 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `d0bc419a` | 2026-09-30 | User | feat(DesktopClient): 新增桌面客户端窗口后端（后台截图/窗口消息输入/PID 绑定） | 大 | 已完整同步 | 适配风险 | 已处理 | dev_tools/bind_desktop_window.py、module/base/cBezier.py、module/device/connection_attr.py、module/device/handle.py 等 6 个 | 本地提交信息引用（已移植/合入） |
| `1bc92584` | 2026-09-30 | User | feat(DesktopClient): 新增桌面客户端窗口后端（后台截图/窗口消息输入/PID 绑定） | 大 | 已完整同步 | 适配风险 | 已处理 | dev_tools/bind_desktop_window.py、module/base/cBezier.py、module/device/connection_attr.py、module/device/handle.py 等 6 个 | 等价补丁 beebb926 |
| `cafe832b` | 2026-09-30 | User | feat(DesktopClient): 设备层接入桌面模式（免 adb、无模拟器生命周期） | 中 | 已完整同步 | 适配风险 | 已处理 | module/device/app_control.py、module/device/connection.py、module/device/method/adb.py、module/device/platform2/platform_windows.py 等 5 个 | 本地提交信息引用（已移植/合入） |
| `fd812e53` | 2026-09-30 | User | feat(DesktopClient): 设备层接入桌面模式（免 adb、无模拟器生命周期） | 中 | 部分实现 | 适配风险 | 谨慎评估 | module/device/app_control.py、module/device/connection.py、module/device/method/adb.py、module/device/platform2/platform_windows.py 等 5 个 | 本地模块存在，文件命中 5/5 |
| `0e7edcc8` | 2026-09-30 | User | feat(DesktopClient): Device 层桌面生命周期（DesktopDevice mixin） | 中 | 已完整同步 | 适配风险 | 已处理 | module/device/desktop_device.py、module/device/device.py | 等价补丁 d9b7220f |
| `e2cdbe92` | 2026-09-30 | User | feat(DesktopClient): Device 层桌面生命周期（DesktopDevice mixin） | 中 | 部分实现 | 适配风险 | 谨慎评估 | module/device/desktop_device.py、module/device/device.py | 本地模块存在，文件命中 2/2 |
| `a34240a5` | 2026-10-10 | LGG686 | fix(device)：修复竖屏 splash 帧导致登录 OCR 崩溃 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/device/device.py、module/ocr/base_ocr.py | 本地模块存在，文件命中 2/2 |
| `9073e4d1` | 2026-10-31 | LGG686 | feat(Device)：桌面客户端登录与重启解耦 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、module/device/desktop_device.py、module/device/handle.py 等 9 个 | 本地模块存在，文件命中 9/9 |
| `92d2dbd8` | 2026-10-31 | Hurry2 | feat(desktop_device):适配桌面版空闲策略关闭游戏 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/device/desktop_device.py、module/device/handle.py、module/device/method/desktop_impl.py | 本地模块存在，文件命中 3/3 |
| `371bdb89` | 2026-10-31 | LGG686 | feat(Device)：press_and_drag 支持 window_message 通道 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/device/control.py、module/device/method/windows_impl.py、module/device/press_and_drag.py | 本地模块存在，文件命中 2/3 |
| `68fe3245` | 2026-11-01 | xylolit-mu | fix(DesktopClient)：补齐桌面客户端加固，修复 PID 复用误杀与多开竞态 | 大 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/image.py、module/config/config_model.py、module/device/desktop_device.py、module/device/desktop_launch.py 等 10 个 | 本地模块存在，文件命中 9/10 |
| `2dd53a9e` | 2026-11-06 | niuma-workwork | fix(core): release screen DCs, correct click offsets, harden device/config paths | 大 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/cBezier.py、module/atom/click.py、module/atom/list.py、module/atom/swipe.py 等 27 个 | 本地模块存在，文件命中 26/27 |
| `a787a58a` | 2026-11-10 | kristin0512 | Fix minitouch pressure range for low max_pressure | 小 | 已完整同步 | 适配风险 | 已处理 | module/device/method/minitouch.py | 本地提交信息引用（已移植/合入） |
| `db601816` | 2026-11-18 | LGG686 | feat(Android)：Add oasaos device backend and native panel compatibility | 大 | 部分实现 | 适配风险 | 不引入 | module/device/app_control.py、module/device/connection.py、module/device/connection_attr.py、module/device/control.py 等 15 个 | 本地模块存在，文件命中 11/15（台账曾判不采纳，需复核） |

#### GlobalGame（13 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `407544fe` | 2026-09-20 | xylolit-mu | 调整(全局奖励)：保留本地验证的关闭点击范围 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GlobalGame/assets.py、tasks/GlobalGame/ui/click.json | 等价补丁 6661c82b |
| `59657b71` | 2026-10-10 | kongdr418 | fix(GlobalGame): 通用确认按钮兼容新旧两套UI | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/activities/rich_man.py、tasks/ActivityShikigami/base_act.py、tasks/BondlingFairyland/script_task.py、tasks/DailyTrifles/script_task.py 等 26 个 | 本地模块存在，文件命中 25/26 |
| `7ad6278e` | 2026-10-10 | kongdr418 | fix(GlobalGame): 重截获得奖励素材并调整ROI | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/GlobalGame/assets.py、tasks/GlobalGame/ui/image.json、tasks/GlobalGame/ui/ui_ui_reward.png | 本地模块存在，文件命中 3/3 |
| `efd39e18` | 2026-10-10 | m123711 | fix(GlobalGame): 更新通用确认按钮素材 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GlobalGame/ui/ui_ui_confirm.png | 台账已覆盖 |
| `fda09fde` | 2026-10-10 | neptine | fix(GlobalGame): Improve reward image matching and remove duplicate assets | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/DemonEncounter/assets.py、tasks/Exploration/assets.py、tasks/Exploration/res/image.json、tasks/Exploration/res/res_get_reward.png 等 10 个 | 本地模块存在，文件命中 8/10 |
| `5d546f0b` | 2026-10-10 | neptine | fix(GlobalGame): Preserve current and historical confirm/cancel button assets | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/GlobalGame/assets.py、tasks/GlobalGame/ui/image.json、tasks/GlobalGame/ui/ui_ui_cancel.png、tasks/GlobalGame/ui/ui_ui_cancel_old.png 等 6 个 | 本地模块存在，文件命中 6/6 |
| `cdde0e49` | 2026-10-10 | neptine | refactor(GlobalGame): Reuse shared confirm button for exit and refresh dialogs - replace task-specif | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/AbyssShadows/script_task.py、tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/gb/gb_exit_ensure.png、tasks/Component/GeneralBattle/gb/image.json 等 10 个 | 本地模块存在，文件命中 8/10 |
| `916e6eb8` | 2026-10-12 | allesgutefy | fix: update ui_ui_check and ui_ui_uncheck assets for new UI | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GlobalGame/ui/ui_ui_check.png、tasks/GlobalGame/ui/ui_ui_uncheck.png | 等价补丁 44881fa6 |
| `57c3f701` | 2026-10-28 | kongdr418 | fix(GlobalGame): 放宽协作图标识别区域 | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/image.json | 本地模块存在，文件命中 2/2P0 复核：本地协作图标 roi_back=(810,448,120,192) 更宽，已被 e68c2d26 取代 |
| `91010725` | 2026-10-28 | kongdr418 | fix(GlobalGame): 放宽忽略按钮识别区域 | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/image.json | 本地模块存在，文件命中 2/2P0 复核：本地忽略按钮 roi_back=(725,40,197,142) 更宽，已覆盖 |
| `e68c2d26` | 2026-10-28 | User | fix(GlobalGame): 适配接受/拒绝按钮新 UI | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/gg_g_accept.png、tasks/GlobalGame/gg/gg_g_reject.png、tasks/GlobalGame/gg/image.json | 等价补丁 5e991f0d |
| `31a853a9` | 2026-10-30 | kongdr | fix(GlobalGame): 协作邀请改用新UI图标识别 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/image.json、tasks/base_task.py | 本地模块存在，文件命中 3/3 |
| `8d499033` | 2026-10-30 | weirj2016-ai | fix(GlobalGame): 更新协作邀请识别素材与坐标 | 中 | 已完整同步 | 适配风险 | 已处理 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/gg_g_accept.png、tasks/GlobalGame/gg/gg_g_ignore.png、tasks/GlobalGame/gg/gg_g_jade.png 等 6 个 | 等价补丁 cff18d6c |

#### 根目录（12 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0c3b971a` | 2026-09-27 | xylolit-mu | 优化(重启)：支持配置异常重启容忍次数并优先执行恢复 | 小 | 部分实现 | 适配风险 | 谨慎评估 | config/template.json、script.py、tasks/Restart/config.py | 本地模块存在，文件命中 3/3 |
| `251cb1cd` | 2026-10-09 | User | fix(Scheduler): ensure desktop client logged in before gameplay tasks | 小 | 已完整同步 | 适配风险 | 已处理 | script.py | 本地提交信息引用（已移植/合入） |
| `65c5b127` | 2026-10-18 | kongdr | fix(Deploy): 默认仓库指向本仓库 mine 分支 | 小 | 部分实现 | 可直接复用优化 | 不引入 | deploy/config.py、deploy/template | 本地模块存在，文件命中 2/2（台账曾判不采纳，需复核） |
| `a04e4dcc` | 2026-11-06 | niuma-workwork | fix(infra): restore TLS verification, guard QML/C++ nulls, harden deploy scripts | 大 | 部分实现 | 核心模块大改 | 单独评估 | deploy/adb.py、deploy/config.py、deploy/docker/Dockerfile、deploy/emulator.py 等 25 个 | 本地模块存在，文件命中 25/25 |
| `a8bd3bc8` | 2026-11-08 | niuma-workwork | docs: 上游删库后整理仓库文档与 README | 大 | 部分实现 | 格式/文档 | 低优先 | README.md、docs/development.md | 本地模块存在，文件命中 1/2 |
| `cf7e8a50` | 2026-11-09 | niuma-workwork | fix: 庭院镜头偏移导致页面识别全灭 + 失败后 Restart 被过期任务抢占 | 小 | 部分实现 | 适配风险 | 谨慎评估 | script.py、tasks/GameUi/default_pages.py | 本地模块存在，文件命中 2/2 |
| `fd767a1d` | 2026-11-09 | blylana | docs(README): Add temporary repository links after account suspension | 小 | 部分实现 | 格式/文档 | 低优先 | README.md | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核） |
| `d7e7f2bf` | 2026-11-09 | pinkpig-Peppa | fix(deploy): keep template indentation when writing deploy.yaml | 小 | 部分实现 | 可直接复用优化 | 不引入 | deploy/utils.py | 本地模块存在，文件命中 1/1 |
| `a279ab60` | 2026-11-11 | LGG686 | feat(sync)：同步上游新增任务、超鬼王快速预设与协斗模板权重 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、module/config/config_manual.py、module/config/config_menu.py 等 225 个 | 本地提交信息引用（已移植/合入） |
| `ed25cc79` | 2026-11-11 | kongdr418 | feat(cooperation): 协同心跳接入调度进程 | 小 | 部分实现 | 适配风险 | 谨慎评估 | script.py | 本地模块存在，文件命中 1/1 |
| `d389f83a` | 2026-11-14 | pinkpig-Peppa | requirements: 新增 apprise==2.2.0 依赖 | 小 | 部分实现 | 适配风险 | 谨慎评估 | requirements-in.txt、requirements.txt | 本地模块存在，文件命中 2/2 |
| `aff78b2c` | 2026-11-15 | niuma-workwork | 修复 OCR 服务未启动与 exact 匹配参数回归 | 中 | 部分实现 | 适配风险 | 谨慎评估 | deploy/config.py、deploy/template、gui.py、module/atom/ocr.py 等 8 个 | 本地模块存在，文件命中 8/8 |

#### 文档/CI（11 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1589899a` | 2026-10-03 | neptine | chore(workflow): Update automation workflows to gpt-6-luna | 中 | 部分实现 | 格式/文档 | 不引入 | .github/workflows/issue-handle-bug.lock.yml、.github/workflows/issue-handle-enhancement.lock.yml、.github/workflows/issue-handle-other.lock.yml、.github/workflows/issue-handle-question.lock.yml 等 9 个 | 本地模块存在，文件命中 0/9 |
| `f871f379` | 2026-10-09 | neptine | chore(workflow): Upgrade GitHub Agentic Workflow runtime | 大 | 部分实现 | 格式/文档 | 不引入 | .github/aw/actions-lock.json、.github/aw/logs/.gitignore、.github/workflows/agentics-maintenance.yml、.github/workflows/issue-handle-bug.lock.yml 等 11 个 | 本地模块存在，文件命中 0/11（台账曾判不采纳，需复核） |
| `a27a91fe` | 2026-10-09 | neptine | fix(workflow): Restore supported AI model pricing #1879 | 中 | 部分实现 | 格式/文档 | 不引入 | .github/workflows/issue-handle-bug.lock.yml、.github/workflows/issue-handle-enhancement.lock.yml、.github/workflows/issue-handle-other.lock.yml、.github/workflows/issue-handle-question.lock.yml 等 9 个 | 本地模块存在，文件命中 0/9（台账曾判不采纳，需复核） |
| `911e996d` | 2026-10-15 | neptine | fix(workflow): Correct auto-merge schedule comment | 小 | 已完整同步 | 格式/文档 | 已处理 | .github/workflows/auto-merge-pr.yaml | 本地提交信息引用（已移植/合入） |
| `b9f33b8b` | 2026-10-18 | kongdr | feat(doc): 新增变更日志 | 小 | 部分实现 | 格式/文档 | 不引入 | CHANGELOG.md | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `a192e085` | 2026-10-18 | kongdr | chore(doc): 删除变更日志 | 小 | 部分实现 | 格式/文档 | 不引入 | CHANGELOG.md | 本地模块存在，文件命中 0/1 |
| `9cfb4d29` | 2026-11-04 | neptine | feat(workflow): Schedule Monday automated PR creation and merge | 小 | 部分实现 | 格式/文档 | 不引入 | .github/workflows/auto-create-pr.yaml、.github/workflows/auto-merge-pr.yaml | 本地模块存在，文件命中 1/2（台账曾判不采纳，需复核） |
| `d9c28f51` | 2026-11-05 | neptine | chore(workflow): Upgrade GitHub Agentic Workflows to v1.0.1 | 大 | 部分实现 | 格式/文档 | 不引入 | .github/agents/agentic-workflows.md、.github/aw/actions-lock.json、.github/skills/agentic-workflows/SKILL.md、.github/workflows/agentics-maintenance.yml 等 15 个 | 本地模块存在，文件命中 0/15 |
| `305defd0` | 2026-11-10 | blylana | fix(workflow): use current repository owner for mirroring | 小 | 部分实现 | 格式/文档 | 不引入 | .github/workflows/github-mirror.yml | 本地模块存在，文件命中 0/1（台账曾判不采纳，需复核） |
| `bc2211da` | 2026-11-11 | blylana | docs(Docs): Update documentation links to the new domain | 小 | 部分实现 | 格式/文档 | 低优先 | README.md、dev_tools/README.md、tasks/Component/Costume/README.md | 本地模块存在，文件命中 3/3（台账曾判不采纳，需复核） |
| `25cc699b` | 2026-11-12 | blylana | feat(workflow): Create and merge sync PR on schedule | 中 | 部分实现 | 格式/文档 | 不引入 | .github/workflows/auto-create-pr.yaml、.github/workflows/auto-merge-pr.yaml | 本地模块存在，文件命中 1/2 |

#### DemonEncounter（10 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1c5c57ff` | 2026-09-22 | User | fix(DemonEncounter): 跳过宝箱购买后确认弹窗已关闭再进入boss阶段 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DemonEncounter/script_task.py | 等价补丁 dbb54de0 |
| `a04d51da` | 2026-09-24 | User | fix(DemonEncounter): 优化boss搜索容错并处理中央宝箱遮挡 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/DemonEncounter/assets.py、tasks/DemonEncounter/demon/demon_de_box_center.png、tasks/DemonEncounter/demon/image.json、tasks/DemonEncounter/demon/image_side.json 等 6 个 | 本地模块存在，文件命中 6/6 |
| `19ae288c` | 2026-09-25 | User | fix(DemonEncounter): 信件答题结束后补点获得奖励弹窗 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DemonEncounter/script_task.py | 台账已覆盖 |
| `d5837031` | 2026-09-26 | User | fix(DemonEncounter): 收缩灯笼点击区域并分离类型识别搜索区 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DemonEncounter/assets.py、tasks/DemonEncounter/demon/click.json、tasks/DemonEncounter/script_task.py | 台账已覆盖 |
| `f3f62f43` | 2026-09-27 | xylolit-mu | 修复(逢魔之时)：确认弹窗关闭与首领识别并限制三轮召集尝试 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/DemonEncounter/script_task.py | 本地模块存在，文件命中 1/1 |
| `194a3eda` | 2026-10-02 | User | fix(DemonEncounter): 优化boss搜索容错、收缩灯笼点击区、补信件答谢 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/DemonEncounter/assets.py、tasks/DemonEncounter/demon/click.json、tasks/DemonEncounter/demon/demon_de_box_center.png、tasks/DemonEncounter/demon/image.json 等 5 个 | 本地提交信息引用（已移植/合入） |
| `7738d5d5` | 2026-10-02 | User | fix(DemonEncounter): 挑战次数OCR改为DigitCounter 模式 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DemonEncounter/assets.py、tasks/DemonEncounter/demon/ocr.json、tasks/DemonEncounter/script_task.py | 等价补丁 a39c73cb |
| `40fbf76a` | 2026-10-06 | LGG686 | fix(demon_encounter)：修复逢魔重进地图 town↔rwt 死循环 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/DemonEncounter/script_task.py | 本地模块存在，文件命中 1/1 |
| `4e4e9079` | 2026-10-06 | User | fix(DemonEncounter): 修正重进地图导航 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DemonEncounter/script_task.py | 本地提交信息引用（已移植/合入） |
| `252c6701` | 2026-10-19 | LGG686 | fix(demon_encounter)：调整enter_boss逻辑，增加次数复检 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/DemonEncounter/script_task.py、tasks/LBS/assets.py、tasks/LBS/res/image.json | 本地模块存在，文件命中 3/3 |

#### module/image（10 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `72d44a6b` | 2026-09-30 | User | feat(Image): 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/image.py、module/image/runtime.py | 本地模块存在，文件命中 2/2 |
| `7c5f380b` | 2026-09-30 | User | feat(Image): 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差 | 小 | 部分实现 | 可直接复用优化 | 可排期 | module/atom/image.py | 本地模块存在，文件命中 1/1 |
| `8753481b` | 2026-10-02 | LGG686 | feat(image)：新增掩码模板匹配 | 中 | 已完整同步 | 适配风险 | 已处理 | dev_tools/assets_test.py、module/atom/image.py、module/image/runtime.py、module/server/annotator_rule_schema.py | 本地提交信息引用（已移植/合入） |
| `cf6fa6a5` | 2026-10-02 | LGG686 | fix(image)：拦截零方差模板并修正多尺度浮点漂移 | 小 | 已完整同步 | 适配风险 | 已处理 | module/atom/image.py、module/image/runtime.py | 本地提交信息引用（已移植/合入） |
| `51582666` | 2026-10-03 | User | feat(image): 新增掩码模板匹配与多尺度方法分发 - 可用于处理受背景影响较大的模板，比如送的一整套周年庆庭院+主题的阴阳寮图标(暂未处理) - 新增 "Masked template ma | 中 | 已完整同步 | 适配风险 | 已处理 | dev_tools/assets_test.py、module/atom/image.py、module/server/annotator_rule_schema.py | 本地提交信息引用（已移植/合入） |
| `c1412496` | 2026-10-04 | LGG686 | chore(image)：更新 DailyTrifles/FrogBoss 资产模板参数 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/DailyTrifles/assets.py、tasks/DailyTrifles/dt/image_courtyard_affairs.json、tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/image2.json | 本地模块存在，文件命中 4/4 |
| `be8ae17c` | 2026-10-09 | LGG686 | fix(image)：适配当期活动式神爬塔界面布局与导航 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/ActivityShikigami/activities/normal.py、tasks/ActivityShikigami/as/climb/as_act_fire.png、tasks/ActivityShikigami/as/climb/as_ap_lock.png、tasks/ActivityShikigami/as/climb/as_ap_unlock.png 等 22 个 | 本地模块存在，文件命中 3/22 |
| `c4ce0ab1` | 2026-10-10 | LGG686 | fix(image)：更新活动式神爬塔与通用邀请的资产模板及 ROI | 中 | 部分实现 | 适配风险 | 谨慎评估 | tasks/ActivityShikigami/as/climb/climb_to_battle_climb.png、tasks/ActivityShikigami/as/climb/pages.json、tasks/ActivityShikigami/assets.py、tasks/Component/GeneralInvite/assets.py 等 7 个 | 本地模块存在，文件命中 3/7 |
| `3ede58e1` | 2026-11-09 | blylana | fix(Image): Expand template search regions at initialization | 中 | 已完整同步 | 适配风险 | 已处理 | module/atom/animate.py、module/atom/image.py、module/base/utils/utils.py、module/device/desktop_device.py | 本地提交信息引用（已移植/合入） |
| `56529f78` | 2026-11-14 | pinkpig-Peppa | OCR 引擎升级: ppocr-onnx 迁移至 paddleocr 3.7.0 (PP-OCRv5 + ONNX Runtime) | 大 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/list.py、module/atom/ocr.py、module/base/worker_metrics.py、module/image/__init__.py 等 21 个 | 本地模块存在，文件命中 17/21 |

#### DailyTrifles（8 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `802643de` | 2026-10-16 | kongdr | feat(DailyTrifles): 新增每日收益统计 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、tasks/DailyTrifles/assets.py、tasks/DailyTrifles/config.py、tasks/DailyTrifles/income/ocr.json 等 5 个 | 等价补丁 78cc37ff |
| `97575ca7` | 2026-10-16 | kongdr | refactor(DailyTrifles): 每日收益改为从日志读取 | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DailyTrifles/config.py、tasks/DailyTrifles/script_task.py | 等价补丁 da0cb2c8 |
| `a0fe1e8d` | 2026-10-16 | kongdr | feat(DailyTrifles): 新增每日收益查询接口 | 大 | 已完整同步 | 适配风险 | 已处理 | module/log_income.py、module/server/app.py、module/server/income_router.py、tasks/DailyTrifles/script_task.py | 等价补丁 3cef793a |
| `f3c61ba4` | 2026-10-16 | kongdr | feat(DailyTrifles): 收益快照另存日汇总，突破日志 7 天限制 | 中 | 已完整同步 | 可直接复用优化 | 已处理 | module/log_income.py、tasks/DailyTrifles/script_task.py | 等价补丁 b2fcf4ac |
| `e6b00fbe` | 2026-10-16 | kongdr | feat(DailyTrifles): 收益支持历史查询与按天删除 | 中 | 已完整同步 | 适配风险 | 已处理 | module/log_income.py、module/server/income_router.py | 等价补丁 fd0fdbf2 |
| `83377a19` | 2026-10-16 | kongdr | fix(DailyTrifles): 修复统计每日收益缺少分组常量导致的 NameError | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DailyTrifles/script_task.py | 等价补丁 26045955 |
| `ad778fba` | 2026-11-11 | blylana | fix(DailyTrifles): Improve store sign navigation and mall detection | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/DailyTrifles/script_task.py、tasks/GameUi/assets.py、tasks/GameUi/page/image_main.json、tasks/GameUi/page/page_check_mall.png | 本地提交信息引用（已移植/合入） |
| `a67366d1` | 2026-11-14 | LGG686 | fix(DailyTrifles)：Add cancel button for summon animation popup in courtyard affairs | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/DailyTrifles/assets.py、tasks/DailyTrifles/dt/dt_cancel_large.png、tasks/DailyTrifles/dt/image_courtyard_affairs.json、tasks/GameUi/default_pages.py 等 5 个 | 本地模块存在，文件命中 4/5 |

#### Duel（8 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `36cdcc74` | 2026-09-20 | xylolit-mu | 优化(斗技)：匹配超时竞态保护与周目标调度 | 中 | 部分实现 | 核心模块大改 | 单独评估 | config/template.json、tasks/Duel/assets.py、tasks/Duel/config.py、tasks/Duel/duel/duel_exit_waiting.png 等 7 个 | 本地模块存在，文件命中 6/7 |
| `cf9eba73` | 2026-09-20 | xylolit-mu | 修复(斗技)：达到名士星数目标后延至下周一运行 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Duel/script_task.py | 本地模块存在，文件命中 1/1 |
| `d638c11f` | 2026-10-11 | Enough1122 | fix(Duel): detect MVP share page via share-button image rule | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Duel/assets.py、tasks/Duel/duel/duel_d_victory_share.png、tasks/Duel/duel/duel_d_victory_share_mask.png、tasks/Duel/duel/image.json 等 5 个 | 本地模块存在，文件命中 4/5 |
| `bedff718` | 2026-10-13 | Enough1122 | fix(Duel): 开战前等待增加超时与点击上限 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Duel/script_task.py | 本地提交信息引用（已移植/合入） |
| `985ac267` | 2026-10-13 | Enough1122 | refactor(Duel): reuse ui_click for pre-battle setup wait | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Duel/script_task.py | 本地提交信息引用（已移植/合入） |
| `5770f91e` | 2026-10-14 | huangrunheng | Refactor script_task.py by cleaning up comments | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Duel/script_task.py | 本地提交信息引用（已移植/合入） |
| `9eea7c9d` | 2026-11-12 | jl5250 | feat(Duel): 增加斗技识别的资源以及更正返回庭院的函数 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Duel/assets.py、tasks/Duel/duel/duel_duel_main_uesless_message.png、tasks/Duel/duel/duel_exit_waiting.png、tasks/Duel/script_task.py | 本地模块存在，文件命中 2/4 |
| `bf893c0d` | 2026-11-12 | kongdr418 | fix(Duel): 补齐斗技识别资源标注并同步生成配置 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Duel/assets.py、tasks/Duel/duel/image.json、tasks/Duel/duel/ocr.json | 本地模块存在，文件命中 3/3 |

#### Restart（8 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `93cdaf2b` | 2026-09-27 | xylolit-mu | 修复(登录)：调整进入游戏文字识别区域与关键词 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Restart/assets.py、tasks/Restart/login/ocr.json | 本地模块存在，文件命中 2/2 |
| `885ea02c` | 2026-09-30 | kongdr | fix(Restart): 调整登录界面「进入游戏」OCR 识别区域 | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/Restart/assets.py、tasks/Restart/login/ocr.json | 本地模块存在，文件命中 2/2（台账曾判不采纳，需复核）P0 复核：本地 O_LOGIN_ENTER_GAME roi_back=(460,460,360,180) 已覆盖上游区域 |
| `2a82f6da` | 2026-09-30 | User | fix(Restart): 桌面客户端启动/登录失败时就地重试，避免无限重启循环 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Restart/script_task.py | 本地模块存在，文件命中 1/1 |
| `6ea67658` | 2026-09-30 | User | fix(Restart): 桌面客户端启动/登录失败时就地重试，避免无限重启循环 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Restart/script_task.py | 本地提交信息引用（已移植/合入） |
| `5b556e92` | 2026-10-13 | neptine | fix(Restart): Reuse global UI assets for login and mail dialogs - replace login cancel and mail conf | 大 | 已完整同步 | 核心模块大改 | 已处理 | tasks/ActivityShikigami/script_task.py、tasks/GameUi/default_pages.py、tasks/GlobalGame/assets.py、tasks/GlobalGame/ui/image.json 等 12 个 | 本地提交信息引用（已移植/合入） |
| `77bd7fd7` | 2026-10-20 | weirj2016-ai | fix(Restart): 延长邮件领取确认等待时间 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Restart/login.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核） |
| `d1de2080` | 2026-10-30 | LGG686 | refactor(Login)：登录界面按钮改用通用UI资产并新增引擎更新跳过 | 大 | 部分实现 | 适配风险 | 不引入 | module/server/log_stats.py、tasks/Chess/assets.py、tasks/Chess/c/image.json、tasks/Component/Login/service.py 等 13 个 | 本地模块存在，文件命中 11/13 |
| `d06d9225` | 2026-10-30 | Hurry2 | feat(Restart):桌面版支持杀进程重启，用于挽救卡死的未知界面 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、module/device/method/desktop_impl.py、tasks/Restart/script_task.py 等 5 个 | 本地模块存在，文件命中 5/5 |

#### Dokan（7 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `62f488b3` | 2026-10-02 | User | fix(Dokan,FallenSun): replace removed I_BACK_BL with I_UI_BACK_BLUE | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Dokan/script_task.py、tasks/FallenSun/script_task.py | 本地模块存在，文件命中 2/2（台账曾判不采纳，需复核） |
| `3a2b74a3` | 2026-10-02 | xylolit-mu | 修复(道馆)：退出战斗返回道馆后结束连战调用 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Dokan/script_task.py、tasks/Dokan/test_battle_exit.py | 等价补丁 e00d55fe |
| `4354df46` | 2026-10-22 | weirj2016-ai | fix(Dokan): correct dojo leader name template | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Dokan/res/res_ryou_dokan_center_guanzhu_xiuxi.png | 等价补丁 02dff57b |
| `8bbf87b8` | 2026-10-22 | weirj2016-ai | fix(Dokan): lower leader template threshold | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Dokan/assets.py、tasks/Dokan/res/image.json | 等价补丁 091eeb02 |
| `6360d6a9` | 2026-10-24 | weirj2016-ai | 修复道馆首次攻击后的任务间隔 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Dokan/script_task.py | 台账已覆盖 |
| `3f085151` | 2026-10-28 | weirj2016-ai | 道馆任务每次运行尝试开启道馆 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Dokan/script_task.py | 本地提交信息引用（已移植/合入） |
| `1e18c251` | 2026-10-28 | weirj2016-ai | 道馆开启尝试移出查找循环 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Dokan/script_task.py | 台账已覆盖 |

#### Delegation（6 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `602730c6` | 2026-09-20 | xylolit-mu | 修正(式神委派)：收窄完成状态OCR识别区域 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Delegation/assets.py、tasks/Delegation/rewards/ocr.json | 本地模块存在，文件命中 2/2 |
| `d814b589` | 2026-09-27 | xylolit-mu | 修复(委派)：补充领奖对话验证并更新出战识别资源 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Delegation/assets.py、tasks/Delegation/d/click.json、tasks/Delegation/d/d_d_select_1.png、tasks/Delegation/d/d_d_select_2.png 等 13 个 | 本地模块存在，文件命中 12/13 |
| `dedfb11b` | 2026-10-06 | m123711 | fix(Delegation): 修正式神委派任务点击位置 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Delegation/script_task.py | 等价补丁 28bf7a37 |
| `84366fc5` | 2026-10-15 | kunkun008 | fix(Delegation): avoid jade confirm misclick and back-button dead loop | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Delegation/script_task.py | 等价补丁 7113513c |
| `ce0e78d6` | 2026-10-29 | kongdr | fix(Delegation): 「完成」改用独立点击区，规避游戏对文字正中点击不响应 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Delegation/assets.py、tasks/Delegation/rewards/click.json、tasks/Delegation/script_task.py | 台账已覆盖 |
| `05fca68a` | 2026-10-30 | LGG686 | feat(task)：鼬商店OCR识别礼盒购买，委派完成判定改模板点任务卡，阵容工坊卡图缓存穿透 | 大 | 已完整同步 | 适配风险 | 已处理 | module/server/web/chesslineup/index.html、module/server/web/chesslineup/static/app.js、module/server/web/chesslineup/static/cards/special_hakuzosu_protect.webp、tasks/Delegation/assets.py 等 13 个 | B1 鼬金币商店已移植（待实机） |

#### module/gui（6 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `51115b4a` | 2026-09-20 | kongdr | fix(annotator): 修复标注工具停止连接导致 Web 服务卡死 | 大 | 已完整同步 | 适配风险 | 已处理 | module/server/tool.py、module/server/tool_capture_worker.py、module/server/tool_router.py、module/server/web/annotator/static/js/app.js | 等价补丁 21ce6c13 |
| `91f7d916` | 2026-10-29 | kongdr | feat(annotator): 目录下拉显示任务中文名，中文名取自 OASX | 小 | 已完整同步 | 适配风险 | 已处理 | module/server/web/annotator/static/js/app.js | 等价补丁 2b9092d3 |
| `cf9fe93c` | 2026-10-30 | kongdr | feat(annotator): 上传支持选择文件夹 | 小 | 已完整同步 | 适配风险 | 已处理 | module/server/web/annotator/static/js/app.js、module/server/web/annotator/static/widget/left-window.html | 等价补丁 bae0645f |
| `b68f1a68` | 2026-10-30 | kongdr | feat(annotator): 支持用协同 v6 模型测试 OCR | 中 | 部分实现 | 适配风险 | 谨慎评估 | module/server/tool.py、module/server/tool_router.py、module/server/web/annotator/static/css/right-window.css、module/server/web/annotator/static/js/app.js 等 5 个 | 本地模块存在，文件命中 5/5 |
| `41a2b209` | 2026-11-06 | niuma-workwork | fix(server/gui): await async handlers, add webui key check, harden config paths | 大 | 部分实现 | 适配风险 | 谨慎评估 | gui.py、module/gui/context/add.py、module/gui/context/process_manager.py、module/gui/context/settings.py 等 35 个 | 本地模块存在，文件命中 35/35 |
| `27b9f534` | 2026-11-12 | kongdr418 | fix(annotator): 隔离预览截图缓存避免干扰运行任务 | 小 | 已完整同步 | 适配风险 | 已处理 | module/device/screenshot.py、module/server/tool_capture_worker.py | 等价补丁 ca19f878 |

#### AbyssShadows（5 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `9f8841f1` | 2026-09-20 | User | 修复(狭间)：切换御魂前关闭残留分布弹窗 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/AbyssShadows/script_task.py | 本地模块存在，文件命中 1/1 |
| `014ffa84` | 2026-09-20 | xylolit-mu | 优化(狭间)：跳过重复御魂装配并识别已击破目标 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/AbyssShadows/assets.py、tasks/AbyssShadows/res/ocr.json、tasks/AbyssShadows/script_task.py | 本地模块存在，文件命中 3/3 |
| `e68b0b74` | 2026-10-10 | kongdr | fix(GeneralBattle): 退出战斗确认按钮兼容新旧两套UI | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/AbyssShadows/script_task.py、tasks/Component/GeneralBattle/general_battle.py、tasks/Duel/script_task.py | 本地模块存在，文件命中 3/3 |
| `d38f6e95` | 2026-10-25 | LGG686 | fix(AbyssShadows)：确认按钮改用通用资产 I_UI_CONFIRM | 中 | 已完整同步 | 适配风险 | 已处理 | tasks/AbyssShadows/assets.py、tasks/AbyssShadows/res/image.json、tasks/AbyssShadows/res/res_ensure_button.png、tasks/AbyssShadows/res/res_start_ensure.png 等 5 个 | 本地提交信息引用（已移植/合入） |
| `aa91067c` | 2026-10-30 | LGG686 | fix(AbyssShadows)：修复狭间暗域战斗瞬间结算导致 attack_enemy 卡死 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/AbyssShadows/script_task.py | 本地模块存在，文件命中 1/1 |

#### BondlingFairyland（5 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `3f15a981` | 2026-09-20 | User | 修复(契灵)：建房过渡时识别已进入房间 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/BondlingFairyland/script_task.py、tasks/Component/GeneralRoom/general_room.py | 台账已覆盖 |
| `7b0da642` | 2026-10-08 | LGG686 | fix(bondling)：删除漏邀分支，队员退回主界面即判房间销毁 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/BondlingFairyland/script_task.py | 本地模块存在，文件命中 1/1 |
| `ba0d49b7` | 2026-10-12 | LGG686 | fix(bondling)：调整建房逻辑，调整补邀时间间隔 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/BondlingFairyland/script_task.py、tasks/Component/GeneralInvite/general_invite.py | 本地模块存在，文件命中 2/2 |
| `e8df3ae0` | 2026-10-12 | allesgutefy | fix: update interval=3 for I_UI_UNCHECK and I_UI_CONFIRM in check_and_invite | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/BondlingFairyland/general_invite.py、tasks/Component/GeneralInvite/general_invite.py | 本地提交信息引用（已移植/合入） |
| `844d3bec` | 2026-11-10 | LGG686 | fix(bondling)：恢复交换身份在单次任务内按半量切换 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/BondlingFairyland/config.py、tasks/BondlingFairyland/script_task.py | 本地提交信息引用（已移植/合入） |

#### MetaDemonTicket（5 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `c8c9c648` | 2026-11-11 | kongdr418 | feat(MetaDemonTicket): 探索模式支持选择章节 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、config/template.json、tasks/MetaDemonTicket/config.py 等 5 个 | 本地模块存在，文件命中 5/5 |
| `429b8570` | 2026-11-11 | kongdr418 | fix(MetaDemonTicket): 门票计数越界时按识别错误处理 | 小 | 部分实现 | 可直接复用优化 | 可排期 | dev_tools/meta_demon_ticket_checks.py、tasks/MetaDemonTicket/ticket_farming.py | 本地模块存在，文件命中 1/2 |
| `991016cf` | 2026-11-13 | kongdr418 | feat(MetaDemonTicket): 支持三人觉醒刷票协同 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、dev_tools/meta_demon_cooperation_checks.py、dev_tools/meta_demon_ticket_checks.py 等 9 个 | 本地模块存在，文件命中 6/9 |
| `cc12900f` | 2026-11-14 | kongdr418 | fix(MetaDemonTicket): 满票退出时补点关闭奖励页面 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | dev_tools/meta_demon_ticket_checks.py、tasks/MetaDemonTicket/ticket_farming.py | 本地提交信息引用（已移植/合入） |
| `3ad3ff86` | 2026-11-14 | kongdr418 | fix(MetaDemonTicket): 修复短战斗提前退出和奖励页面卡住 | 小 | 部分实现 | 可直接复用优化 | 可排期 | dev_tools/meta_demon_ticket_checks.py、tasks/MetaDemonTicket/ticket_farming.py | 本地模块存在，文件命中 1/2 |

#### RichMan（5 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `c426b982` | 2026-10-02 | neptine | fix(RichMan): Improve shrine shop purchase detection and retry handling | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/RichMan/assets.py、tasks/RichMan/script_task.py、tasks/RichMan/shrine.py、tasks/RichMan/shrine/image.json | 台账已覆盖 |
| `9ec6101e` | 2026-10-02 | neptine | fix(RichMan): Handle bulk purchase failures in special shop | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Buy/buy.py、tasks/RichMan/mall/special.py | 本地模块存在，文件命中 2/2 |
| `1ff269b0` | 2026-10-05 | LGG686 | fix(weekly_purchase)：修复皮肤券未购买 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/WeeklyPurchase/assets.py、tasks/WeeklyPurchase/guild.py、tasks/WeeklyPurchase/mall/bondlings.py、tasks/WeeklyPurchase/mall/scales.py 等 7 个 | 本地模块存在，文件命中 0/7 |
| `f7302af2` | 2026-10-12 | LGG686 | fix(weekly_purchase)：海汐御魂开启自动选择时一次买完 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/WeeklyPurchase/mall/scales.py | 本地模块存在，文件命中 0/1 |
| `2db22cc3` | 2026-10-28 | User | fix(RichMan): 海汐御魂开启自动选择时一次买完 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/RichMan/mall/scales.py | 等价补丁 1b5c2590 |

#### EvoZone（4 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `44dd4659` | 2026-10-09 | neptine | fix(EvoZone): Expand lock button detection regions #1876 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/EvoZone/assets.py、tasks/EvoZone/o/image.json | 本地提交信息引用（已移植/合入） |
| `c2023476` | 2026-10-15 | neptine | fix(GeneralBattle): Close buff panel and start battle preparation | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/EvoZone/script_task.py | 本地提交信息引用（已移植/合入） |
| `d8677dc0` | 2026-10-15 | neptine | Revert "fix(GeneralBattle): Close buff panel and start battle preparation" | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/EvoZone/script_task.py | 本地提交信息引用（已移植/合入） |
| `057628b1` | 2026-11-13 | kongdr418 | fix(EvoZone): 兼容缺少头像标志的组队页面 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/EvoZone/script_task.py | 等价补丁 5b7b21a9 |

#### LBS（4 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ad15a023` | 2026-09-25 | User | feat(LBS): 新增LBS鬼王限时活动任务 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、module/config/config_menu.py、module/config/config_model.py、tasks/Component/GeneralRoom/general_room.py 等 20 个 | A5 LBS 已移植（待实机） |
| `188dee7c` | 2026-09-27 | User | feat(LBS): 新增开车模式（挣点赛博功德） 顺便还能搞点点赞(bushi 运行模式改为三选一枚举（单人挑战/组队匹配/开车模式）。 - 开车模式：创建公开房间，有人上车即退房重开，结束条件为开 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、tasks/Component/GeneralRoom/general_room.py、tasks/LBS/assets.py、tasks/LBS/config.py 等 10 个 | A5 LBS 已移植（待实机） |
| `a1fb24a6` | 2026-09-27 | User | fix(LBS): 开车模式等进房渲染完成后再等客 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/GeneralInvite/general_invite.py、tasks/LBS/script_task.py | A5 LBS 已移植（待实机） |
| `f01a83f0` | 2026-09-27 | User | fix(LBS): 修复挑战次数判断，登记调度优先级 | 小 | 已完整同步 | 适配风险 | 已处理 | module/config/config_manual.py、tasks/LBS/script_task.py | A5 LBS 已移植（待实机） |

#### SixRealms（4 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ea6b92f9` | 2026-11-01 | leovefy | fix(SixRealms): 限制选岛连续点击并增加超时退出 | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/SixRealms/moon_sea/map.py、tests/test_six_realms_island_entry.py | 本地模块存在，文件命中 0/2 |
| `f636e9d9` | 2026-11-04 | leovefy | fix(SixRealms): 修复月之海岛屿漏识别和点击偏移 | 大 | 部分实现 | 核心模块大改 | 单独评估 | tasks/SixRealms/assets.py、tasks/SixRealms/gate1/gate1_island_marker_101.png、tasks/SixRealms/gate1/gate1_island_marker_102.png、tasks/SixRealms/gate1/gate1_island_marker_103.png 等 10 个 | 本地模块存在，文件命中 2/10（台账曾判不采纳，需复核） |
| `043d3aa9` | 2026-11-04 | leovefy | fix(SixRealms): 保留 OCR 已选中的岛屿 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/SixRealms/moon_sea/map.py、tests/test_six_realms_island_entry.py | 本地模块存在，文件命中 0/2 |
| `03b5f1ef` | 2026-11-19 | 2263075977 | fix(SixRealms): 月之海选岛自愈重读 + 宁息岛兜底 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/SixRealms/moon_sea/map.py、tasks/SixRealms/moon_sea/moon_sea.py、tests/test_six_realms_island_entry.py | 本地模块存在，文件命中 1/3 |

#### WeeklyTrifles（4 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `28e8f060` | 2026-09-20 | Hurry2 | 新增(每周琐事)：接入摸鱼行动并补充超时保护 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、tasks/WeeklyTrifles/assets.py、tasks/WeeklyTrifles/config.py、tasks/WeeklyTrifles/page.py 等 17 个 | 本地提交信息引用（已移植/合入） |
| `627ba339` | 2026-09-21 | Hurry2 | feat(TouchFish):修复摸鱼行动逻辑问题 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WeeklyTrifles/script_task.py | 本地提交信息引用（已移植/合入） |
| `df3ff430` | 2026-10-03 | Hurry2 | fix(WeeklyTrifles)：修正摸鱼行动御守数量读取与存储判断 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WeeklyTrifles/script_task.py | 本地提交信息引用（已移植/合入） |
| `55b7d957` | 2026-10-13 | Hurry2 | fix(WeeklyTrifles):修复每周琐事摸鱼行动问题 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/WeeklyTrifles/script_task.py | 本地提交信息引用（已移植/合入） |

#### base_task.py（4 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `40e4aa6f` | 2026-09-30 | xylolit-mu | 修复(悬赏协作)：优先处理连续弹窗后恢复任务 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/base_task.py | 等价补丁 f58172ba |
| `7e506bc3` | 2026-10-15 | neptine | fix(BaseTask): Skip task name mismatch validation | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/base_task.py | 本地提交信息引用（已移植/合入） |
| `73cf2c63` | 2026-10-21 | kongdr | fix(base_task): 补 clock_time 导入，修复百鬼棋局 set_next_run_next_monday 报 NameError | 小 | 部分实现 | 可直接复用优化 | 不引入 | tasks/base_task.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核）P0 复核：全仓无 set_next_run_next_mon 调用点 |
| `094b30b9` | 2026-10-25 | kongdr | fix(base_task): wait_until_disappear 支持 timeout 参数，修复邀请组件报错 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/base_task.py | 等价补丁 81681f0c |

#### module/config（4 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `f80c3a6d` | 2026-09-30 | User | feat(Config): 桌面模式配置项与界面说明 | 中 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、dev_tools/bind_desktop_window.py、module/config/config_model.py、tasks/Script/config_device.py | 本地提交信息引用（已移植/合入） |
| `60b09a8e` | 2026-09-30 | User | feat(Config): 桌面模式配置项与界面说明 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、dev_tools/bind_desktop_window.py、module/config/config_model.py、tasks/Script/config_device.py | 本地模块存在，文件命中 4/4 |
| `d2feec52` | 2026-11-11 | kongdr418 | fix(scheduler): 调度白名单补上超鬼王门票任务 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/config/config_manual.py | 本地模块存在，文件命中 1/1 |
| `ea13a4c6` | 2026-11-19 | LGG686 | refactor(config)：移除未实现的 OrochiMoans 占位 | 中 | 已完整同步 | 适配风险 | 已处理 | config/template.json、module/config/config_manual.py、module/config/config_model.py、tasks/OrochiMoans/assets.py 等 5 个 | 本地提交信息引用（已移植/合入） |

#### BorrowShikigami（3 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `3a8ba22f` | 2026-11-13 | kongdr418 | feat(游戏辅助): 新增15级起号流程并适配新手引导 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、module/config/config_manual.py、module/config/config_menu.py 等 41 个 | 本地无对应模块 |
| `fc45a500` | 2026-11-13 | kongdr418 | fix(BorrowShikigami): 调整15级起号流程并补齐新手弹窗处理 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | tasks/AutoStory/assets.py、tasks/AutoStory/res/ocr.json、tasks/AutoStory/script_task.py、tasks/BorrowShikigami/assets.py 等 14 个 | 本地无对应模块 |
| `628c0cfb` | 2026-11-14 | kongdr418 | fix(BorrowShikigami): 通过自动标识兼容新手战斗页面 | 小 | 完全缺失 | 可直接复用优化 | 单独评估 | tasks/BorrowShikigami/child_tasks.py、tasks/BorrowShikigami/script_task.py | 本地无对应模块 |

#### MysteryShop（3 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `120c881a` | 2026-10-24 | kunkun008 | fix(MysteryShop): 蓝票多数量购买窗口改用 buy_more | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Component/Buy/buy.py、tasks/MysteryShop/script_task.py、tasks/RichMan/mall/friendship_points.py | 本地模块存在，文件命中 3/3 |
| `be5f3c97` | 2026-10-24 | kunkun008 | fix(MysteryShop): 蓝票按单价判断，高于 85 勾玉不买 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/Component/Buy/assets.py、tasks/Component/Buy/buy.py、tasks/Component/Buy/buy/buy_buy_jade.png、tasks/Component/Buy/buy/image.json 等 7 个 | 等价补丁 2bb9f4a9 |
| `47b9064b` | 2026-10-24 | kunkun008 | fix(MysteryShop): 蓝票余额不够买满时逐张购买 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/Component/Buy/buy.py | 等价补丁 d00f88b2 |

#### Script（3 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1d990fce` | 2026-10-17 | LGG686 | feat(script)：桌面客户端独立配置组与多开账号隔离 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、config/template.json、dev_tools/bind_desktop_window.py、module/config/config_model.py 等 14 个 | 本地提交信息引用（已移植/合入） |
| `d97598d6` | 2026-10-17 | LGG686 | feat(script)：桌面客户端独立配置组与多开账号隔离 | 大 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、config/template.json、dev_tools/bind_desktop_window.py、module/config/config_model.py 等 15 个 | 本地模块存在，文件命中 15/15 |
| `a57891b8` | 2026-10-31 | Hurry2 | fix(script):修复桌面版关闭游戏后重启 | 小 | 部分实现 | 适配风险 | 谨慎评估 | script.py | 本地模块存在，文件命中 1/1 |

#### module/atom（3 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `24010e18` | 2026-09-20 | xylolit-mu | 重构(点击规则)：统一图像与OCR点击并支持Scatter密度模型 | 大 | 部分实现 | 适配风险 | 谨慎评估 | dev_tools/assets_extract.py、module/atom/click.py、module/atom/image.py、module/atom/ocr.py 等 8 个 | 本地模块存在，文件命中 7/8 |
| `506564c6` | 2026-10-28 | neptine | fix(Costume): Refresh cached template image when replacing costume assets  #1972 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | module/atom/image.py、tasks/Component/Costume/costume_base.py | 本地提交信息引用（已移植/合入） |
| `26e67b73` | 2026-11-14 | pinkpig-Peppa | 移植 nearaura/OnmyojiAutoScript 修复包 (4 项) | 中 | 部分实现 | 适配风险 | 谨慎评估 | module/atom/animate.py、module/atom/image.py、module/base/utils/utils.py、module/device/desktop_device.py 等 7 个 | 本地模块存在，文件命中 7/7 |

#### AreaBoss（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `85632077` | 2026-10-24 | neptine | fix(AreaBoss): Handle fox battle scene settlement #1967 | 小 | 部分实现 | 适配风险 | 谨慎评估 | module/device/device.py、tasks/AreaBoss/script_task.py、tasks/Component/GeneralBattle/battle_wait.py | 本地模块存在，文件命中 2/3（台账曾判不采纳，需复核） |
| `692ee215` | 2026-11-03 | leovefy | fix(AreaBoss): 跳过与悬赏鬼王重名的目标，避免重复挑战导致少打一只 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/AreaBoss/script_task.py | 本地模块存在，文件命中 1/1 |

#### AutoCheckinBigGod（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ef0f8d11` | 2026-09-20 | User | 适配(大神福利)：新版领取界面并修复空按钮等待 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/AutoCheckinBigGod/assets.py、tasks/AutoCheckinBigGod/manual_claim.py、tasks/AutoCheckinBigGod/portrait_ui.py、tasks/AutoCheckinBigGod/res/image.json 等 8 个 | 台账已覆盖 |
| `23ce874b` | 2026-10-05 | LGG686 | fix(AutoCheckinBigGod)：手动UI简化，修复清理后游戏被二次重启与横竖屏状态未还原 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/AutoCheckinBigGod/manual_claim.py、tasks/AutoCheckinBigGod/portrait_ui.py | 本地模块存在，文件命中 2/2 |

#### AutoStory（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `80751206` | 2026-11-13 | LGG686 | feat(AutoStory)：完善剧情结束判定与视频加速处理 | 中 | 完全缺失 | 核心模块大改 | 不引入 | tasks/AutoStory/README.md、tasks/AutoStory/assets.py、tasks/AutoStory/res/image.json、tasks/AutoStory/res/res_page_heian_hyakumonogatali.png 等 8 个 | A4 CustomTask 不采纳（与本地 flow 重复） |
| `547dfba6` | 2026-11-13 | kongdr418 | feat(游戏辅助): 迁移自动剧情、探索推进和自定义任务 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | assets/i18n/en-US.json、assets/i18n/zh-CN.json、module/config/config_manual.py、module/config/config_menu.py 等 37 个 | 本地无对应模块 |

#### EternitySea（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `7b522c94` | 2026-10-02 | User | refactor(EternitySea): 清理无用的导航包装与死代码 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/EternitySea/script_task.py | 台账已覆盖 |
| `329ecfc7` | 2026-10-28 | weirj2016-ai | 修复永生之海队员锁定阵容检查 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/EternitySea/script_task.py | 本地提交信息引用（已移植/合入） |

#### GuildBanquet（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `76490d67` | 2026-10-23 | kongdr418 | fix(GuildBanquet): 兼容第二种寮宴会旗帜并修复加成开关资产重名 | 大 | 部分实现 | 适配风险 | 谨慎评估 | tasks/Component/GeneralBuff/assets.py、tasks/Component/GeneralBuff/gb/gb_experience_close_red.png、tasks/Component/GeneralBuff/gb/gb_experience_open_yellow.png、tasks/Component/GeneralBuff/gb/gb_gold_close_red.png 等 11 个 | 本地模块存在，文件命中 11/11 |
| `cc83b1a2` | 2026-10-25 | LGG686 | fix(GuildBanquet)：调整集结标志识别区并同步资产参数顺序 | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/GuildBanquet/assets.py、tasks/GuildBanquet/res/image.json | 本地模块存在，文件命中 2/2 |

#### HeroTest（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `fd46e065` | 2026-09-29 | Johnnylov | test(HeroTest): cover skill selection timeout fallback | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tests/test_hero_test_skill_fallback.py | 等价补丁 26986ce8 |
| `afdc0318` | 2026-10-04 | neptine | fix(HeroTest): Attach HeroTest dynamic page edges to session page copies  #1861 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/HeroTest/script_task.py | 本地提交信息引用（已移植/合入） |

#### IbukiArena（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `5bc76c7e` | 2026-10-03 | Hurry2 | feat(IbukiArena)：移植狭间幻境活动任务 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、config/template.json、module/config/config_manual.py、module/config/config_menu.py 等 19 个 | A6 狭间幻境已移植（待实机） |
| `c2390c2a` | 2026-10-03 | Hurry2 | fix(IbukiArena)：修复挑战判定可能提前命中 exit_matcher | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/IbukiArena/page.py、tasks/IbukiArena/script_task.py | A6 狭间幻境已移植（待实机） |

#### KekkaiActivation（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `4944b3df` | 2026-11-04 | Ghostuel | fix: expand KekkaiActivation reward collection regions across realm skins | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/KekkaiActivation/a/image.json、tasks/KekkaiActivation/assets.py | 等价补丁 90930fa5 |
| `1cc1707b` | 2026-11-05 | neptine | fix(KekkaiActivation): Prevent desktop activation button false positives #2013 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/KekkaiActivation/script_task.py | 等价补丁 d93c35ad |

#### OtherWorldTwilight（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `78083db2` | 2026-10-03 | User | feat(OtherWorldTwilight): 新增御魂副本任务彼世逢魔 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、module/config/config_manual.py、module/config/config_menu.py、module/config/config_model.py 等 15 个 | 台账已覆盖 |
| `1c0a01f2` | 2026-10-03 | User | fix(OtherWorldTwilight): 修复绿标默认值绕过与队长建房失败死循环 - OWTBattleConfig 重声明 green_mark_type 默认为 NAME，pydantic | 小 | 已完整同步 | 可直接复用优化 | 已处理 | module/atom/image.py、tasks/OtherWorldTwilight/config.py、tasks/OtherWorldTwilight/script_task.py | 台账已覆盖 |

#### RealmRaid（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `3c81120d` | 2026-10-10 | kongdr | fix(RealmRaid): 重截刷新确认按钮并调整ROI | 中 | 部分实现 | 可直接复用优化 | 可排期 | tasks/RealmRaid/assets.py、tasks/RealmRaid/res/image.json、tasks/RealmRaid/res/res_fresh_ensure.png | 本地模块存在，文件命中 2/3 |
| `eb156b16` | 2026-11-12 | kongdr418 | fix(RealmRaid): 校验突破券数量上限并忽略无效识别 | 中 | 部分实现 | 可直接复用优化 | 可排期 | dev_tools/realm_raid_ticket_checks.py、tasks/Exploration/base.py、tasks/RealmRaid/script_task.py | 本地模块存在，文件命中 2/3 |

#### TalismanPass（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `bf889f02` | 2026-10-30 | weirj2016-ai | fix: recognize Flower Pass task tab before claiming | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/TalismanPass/script_task.py、tasks/TalismanPass/tp/tp_task_tab.png | 本地提交信息引用（已移植/合入） |
| `c08fe24f` | 2026-11-01 | weirj2016-ai | fix(TalismanPass): update task tab template and ROI | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/TalismanPass/script_task.py、tasks/TalismanPass/tp/tp_task_tab.png | 等价补丁 3ec1bc99 |

#### TrueOrochi（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `aaede1db` | 2026-09-25 | User | feat(TrueOrochi): 玩法tab模块检测替代本地次数记账 | 中 | 完全缺失 | 核心模块大改 | 不引入 | tasks/TrueOrochi/assets.py、tasks/TrueOrochi/config.py、tasks/TrueOrochi/script_task.py、tasks/TrueOrochi/st/image.json 等 6 个 | 精度优先：同 f7db71b2，用启发式 tab 检测替代精确计数，不采纳 |
| `f7db71b2` | 2026-10-05 | User | feat(TrueOrochi)：用玩法 tab 模块在场检测替代本地次数记账 | 中 | 完全缺失 | 核心模块大改 | 不引入 | tasks/TrueOrochi/assets.py、tasks/TrueOrochi/config.py、tasks/TrueOrochi/script_task.py、tasks/TrueOrochi/st/image.json 等 6 个 | 精度优先：用启发式 tab 检测替代本地精确次数记账，不采纳 |

#### module/scrolls（2 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `95b75dd8` | 2026-11-16 | kongdr418 | feat(scrolls): 完善绘卷查询 | 大 | 完全缺失 | 适配风险 | 谨慎评估 | .gitignore、module/device/app_control.py、module/scrolls/__init__.py、module/scrolls/activity.py 等 23 个 | 本地无对应模块 |
| `92ada2c7` | 2026-11-16 | kongdr418 | feat(scrolls): 适配 Linux 和 redroid 绘卷查询 | 大 | 完全缺失 | 核心模块大改 | 单独评估 | module/scrolls/device.py、module/scrolls/live_objects.py、module/scrolls/process_memory.py、module/scrolls/redroid.py 等 6 个 | 本地无对应模块 |

#### CollectiveMissions（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `13221d2c` | 2026-11-15 | blylana | fix(CollectiveMissions): Handle reward claims and timeout after donation  #7 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/CollectiveMissions/script_task.py | 本地提交信息引用（已移植/合入） |

#### FallenSun（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `f67e5a80` | 2026-10-21 | LGG686 | fix(task)：Delegation、RyouToppa、FallenSun、FrogBoss 同步上游修复 | 中 | 部分实现 | 核心模块大改 | 单独评估 | tasks/Delegation/script_task.py、tasks/FallenSun/assets.py、tasks/FallenSun/f/click.json、tasks/FallenSun/f/f_fallen_sun_lock.png 等 8 个 | 本地模块存在，文件命中 7/8 |

#### FindJade（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `8b4dc669` | 2026-10-31 | neptine | fix(FindJade): Add task to scheduler priority list #1979 | 小 | 已完整同步 | 适配风险 | 已处理 | module/config/config_manual.py | 台账已覆盖 |

#### FrogChallenge（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1f230af2` | 2026-10-03 | Hurry2 | feat(FrogChallenge)：移植青蛙瓷器挑战赛并重命名狭间幻境资产 | 大 | 已完整同步 | 适配风险 | 已处理 | assets/i18n/zh-CN.json、config/template.json、module/config/config_manual.py、module/config/config_menu.py 等 23 个 | A7 青蛙挑战已移植（待实机） |

#### GuildActivityMonitor（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `225c7a13` | 2026-09-20 | yuyuyuyuyu | 增强(寮活动监控)：修复通知漏检并增加OCR模式 | 中 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/GuildActivityMonitor/assets.py、tasks/GuildActivityMonitor/config.py、tasks/GuildActivityMonitor/res/ocr.json、tasks/GuildActivityMonitor/script_task.py | 台账已覆盖 |

#### Hyakkiyakou（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `4785e4bf` | 2026-11-21 | Tyrion | fix(Hyakkiyakou): Ignore an off-screen track when the heatmap has no match | 小 | 部分实现 | 可直接复用优化 | 可排期 | tasks/Hyakkiyakou/agent/agent.py、tasks/Hyakkiyakou/agent/focus.py、tests/tasks/Hyakkiyakou/test_agent_focus.py | 本地模块存在，文件命中 2/3 |

#### KekkaiUtilize（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `69ded977` | 2026-09-20 | xylolit-mu | 拆分(结界蹭卡)：独立控制体力食盒与经验酒壶 | 中 | 部分实现 | 适配风险 | 谨慎评估 | assets/i18n/zh-CN.json、tasks/KekkaiUtilize/config.py、tasks/KekkaiUtilize/script_task.py | 本地模块存在，文件命中 3/3 |

#### MemoryScrolls（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `4f0a4856` | 2026-10-11 | m123711 | fix(MemoryScrolls): 用最大按钮代替滑动并限制捐献轮数 | 小 | 已完整同步 | 可直接复用优化 | 已处理 | tasks/MemoryScrolls/assets.py、tasks/MemoryScrolls/ms/click.json、tasks/MemoryScrolls/script_task.py | 等价补丁 56ff7902 |

#### Orochi（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `af5fcf05` | 2026-10-02 | User | feat(Orochi): 改用 page_orochi 进行御魂页导航 | 中 | 已完整同步 | 核心模块大改 | 已处理 | tasks/Orochi/assets.py、tasks/Orochi/o/image.json、tasks/Orochi/o/o_orochi_check_10.png、tasks/Orochi/o/o_orochi_check_11.png 等 9 个 | 台账已覆盖 |

#### module/ocr（1 条）

| 提交 | 日期 | 作者 | 摘要 | 规模 | 状态 | 类型 | 建议 | 文件范围 | 本地依据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `9d9a6fbd` | 2026-11-19 | LGG686 | feat(ocr)：OCR 档位改由环境变量决定 | 小 | 部分实现 | 适配风险 | 谨慎评估 | script.py | 本地模块存在，文件命中 1/1（台账曾判不采纳，需复核） |

## 4. Merge PR / 合并提交清单

| 提交 | 日期 | 来源 | 作者 | 标题 | 首父差异文件数 | 文件范围 |
| --- | --- | --- | --- | --- | ---: | --- |
| `34df7b17` | 2026-09-19 | pinkpig-Peppa | yuyuyuyuyu | Merge branch 'dev' into m2d | 29 | assets/i18n/zh-CN.json、module/atom/gif.py、tasks/ActivityShikigami/script_task.py、tasks/Component/Costume/assets.py 等 29 个 |
| `3654aa30` | 2026-09-20 | pinkpig-Peppa | huangrunheng | Merge pull request #1822 from m123711/fix/main-goto-summon-template | 1 | tasks/GameUi/page/page_main_goto_summon.png |
| `5735e092` | 2026-09-20 | pinkpig-Peppa | huangrunheng | Merge pull request #1833 from Hurry2/dev-pr | 17 | assets/i18n/zh-CN.json、tasks/GameUi/page.py、tasks/WeeklyTrifles/assets.py、tasks/WeeklyTrifles/config.py 等 17 个 |
| `71fa432a` | 2026-09-25 | pinkpig-Peppa | github-actions[bot] | Merge pull request #1839 from runhey/dev | 47 | assets/i18n/zh-CN.json、module/atom/gif.py、tasks/ActivityShikigami/script_task.py、tasks/Component/Costume/assets.py 等 47 个 |
| `3772e03f` | 2026-09-27 | lgg686 | xylolit-mu | 合并(任务优化)：整合PR #3并采用其逢魔实现 | 50 | assets/i18n/zh-CN.json、module/config/config_menu.py、module/config/config_model.py、tasks/BondlingFairyland/script_task.py 等 50 个 |
| `84a1fae6` | 2026-09-27 | lgg686 | xylolit-mu | Merge pull request #4 from LGG686/self | 2 | module/config/config_manual.py、tasks/LBS/script_task.py |
| `344c6390` | 2026-09-28 | lgg686 | xylolit-mu | Merge remote-tracking branch 'origin/self' into self | 2 | module/config/config_manual.py、tasks/LBS/script_task.py |
| `f9d9fd94` | 2026-09-29 | pinkpig-Peppa | huangrunheng | Merge pull request #1837 from Hurry2/dev-pr | 1 | tasks/WeeklyTrifles/script_task.py |
| `c5cf688d` | 2026-09-29 | pinkpig-Peppa | huangrunheng | Merge pull request #1842 from Enough1122/fix-switch-onmyoji-timeout | 2 | tasks/Component/SwitchOnmyoji/switch_onmyoji.py、tests/test_switch_onmyoji.py |
| `b881e353` | 2026-09-29 | pinkpig-Peppa | huangrunheng | Merge branch 'dev' into m2d | 27 | assets/i18n/zh-CN.json、module/atom/gif.py、tasks/Component/Costume/assets.py、tasks/Component/Costume/costume_base.py 等 27 个 |
| `d1c1b85a` | 2026-09-30 | pinkpig-Peppa | huangrunheng | Merge pull request #1848 from xylolit-mu/pr | 20 | .gitignore、tasks/FrogBoss/assets.py、tasks/FrogBoss/config.py、tasks/FrogBoss/fb/fb_bet_left.png 等 20 个 |
| `0d8518ee` | 2026-09-30 | kongdr418 | kongdr | Merge branch 'dev' into mine | 4 | module/server/tool.py、module/server/tool_capture_worker.py、module/server/tool_router.py、module/server/web/annotator/static/js/app.js |
| `f870b43a` | 2026-10-01 | pinkpig-Peppa | huangrunheng | Merge pull request #1850 from xylolit-mu/pr | 24 | tasks/FrogBoss/assets.py、tasks/FrogBoss/fb/fb_bet_failure.png、tasks/FrogBoss/fb/fb_bet_left.png、tasks/FrogBoss/fb/fb_bet_right.png 等 24 个 |
| `3d243745` | 2026-10-01 | pinkpig-Peppa | huangrunheng | Merge pull request #1847 from Johnnylov/herotest-skill-fallback | 2 | tasks/HeroTest/script_task.py、tests/test_hero_test_skill_fallback.py |
| `967a0120` | 2026-10-01 | pinkpig-Peppa | huangrunheng | Merge pull request #1851 from runhey/dev | 39 | .gitignore、tasks/Component/SwitchOnmyoji/switch_onmyoji.py、tasks/Exploration/solo.py、tasks/FrogBoss/assets.py 等 39 个 |
| `d93fd1bb` | 2026-10-01 | pinkpig-Peppa | huangrunheng | Merge pull request #1852 from runhey/pr1834 | 168 | tasks/AbyssShadows/script_task.py、tasks/ActivityShikigami/page.py、tasks/ActivityShikigami/script_task.py、tasks/ActivityShikigami/script_test.py 等 168 个 |
| `73275edb` | 2026-10-02 | pinkpig-Peppa | github-actions[bot] | Merge pull request #1854 from runhey/dev | 173 | tasks/AbyssShadows/script_task.py、tasks/ActivityShikigami/page.py、tasks/ActivityShikigami/script_task.py、tasks/ActivityShikigami/script_test.py 等 173 个 |
| `a62a6c92` | 2026-10-02 | pinkpig-Peppa | huangrunheng | Merge pull request #1857 from LGG686/dev-f | 20 | tasks/DemonEncounter/assets.py、tasks/DemonEncounter/demon/click.json、tasks/DemonEncounter/demon/demon_de_box_center.png、tasks/DemonEncounter/demon/image.json 等 20 个 |
| `00c083e8` | 2026-10-03 | lgg686 | xylolit-mu | Merge pull request #5 from LGG686/self | 35 | assets/i18n/zh-CN.json、config/template.json、dev_tools/assets_test.py、module/atom/image.py 等 35 个 |
| `9d9df4e5` | 2026-10-04 | pinkpig-Peppa | huangrunheng | Merge pull request #1859 from runhey/dev | 40 | .github/workflows/issue-handle-bug.lock.yml、.github/workflows/issue-handle-enhancement.lock.yml、.github/workflows/issue-handle-other.lock.yml、.github/workflows/issue-handle-question.lock.yml 等 40 个 |
| `85accd8a` | 2026-10-04 | pinkpig-Peppa | huangrunheng | Merge pull request #1862 from LGG686/dev-f | 24 | assets/i18n/zh-CN.json、dev_tools/assets_test.py、module/atom/image.py、module/config/config_manual.py 等 24 个 |
| `947e51e1` | 2026-10-04 | pinkpig-Peppa | neptine | Merge remote-tracking branch 'origin/dev' into dev | 24 | assets/i18n/zh-CN.json、dev_tools/assets_test.py、module/atom/image.py、module/config/config_manual.py 等 24 个 |
| `17e7a3d3` | 2026-10-09 | pinkpig-Peppa | huangrunheng | Merge pull request #1872 from LGG686/dev-f | 15 | tasks/DemonEncounter/script_task.py、tasks/Exploration/assets.py、tasks/Exploration/base.py、tasks/Exploration/page.py 等 15 个 |
| `564e58a1` | 2026-10-09 | pinkpig-Peppa | huangrunheng | Merge pull request #1870 from m123711/fix/delegation-click-position | 1 | tasks/Delegation/script_task.py |
| `62340f37` | 2026-10-09 | pinkpig-Peppa | github-actions[bot] | Merge pull request #1882 from runhey/dev | 45 | assets/i18n/zh-CN.json、dev_tools/assets_test.py、module/atom/image.py、module/config/config_manual.py 等 45 个 |
| `c496ea55` | 2026-10-10 | pinkpig-Peppa | huangrunheng | Merge pull request #1885 from allesgutefy/fix/run-task-or-default-general-battle | 1 | tasks/Component/GeneralBattle/general_battle.py |
| `ff594d1c` | 2026-10-10 | pinkpig-Peppa | huangrunheng | Merge pull request #1889 from runhey/master | 13 | .github/aw/actions-lock.json、.github/aw/logs/.gitignore、.github/workflows/agentics-maintenance.yml、.github/workflows/issue-handle-bug.lock.yml 等 13 个 |
| `5a5d5dba` | 2026-10-10 | pinkpig-Peppa | huangrunheng | Merge pull request #1898 from m123711/fix/global-confirm-button | 1 | tasks/GlobalGame/ui/ui_ui_confirm.png |
| `3ffe7d30` | 2026-10-10 | pinkpig-Peppa | huangrunheng | Merge pull request #1886 from allesgutefy/fix/invite-default-checkbox-timing | 1 | tasks/Component/GeneralInvite/general_invite.py |
| `fc68a2af` | 2026-10-11 | pinkpig-Peppa | huangrunheng | Merge pull request #1916 from runhey/dev | 69 | tasks/AbyssShadows/script_task.py、tasks/ActivityShikigami/as/as_lock.png、tasks/ActivityShikigami/as/as_shi.png、tasks/ActivityShikigami/as/as_to_battle_main.png 等 69 个 |
| `a39e7375` | 2026-10-11 | pinkpig-Peppa | huangrunheng | Merge pull request #1923 from Enough1122/duel-share-image | 5 | tasks/Duel/assets.py、tasks/Duel/duel/duel_d_victory_share.png、tasks/Duel/duel/duel_d_victory_share_mask.png、tasks/Duel/duel/image.json 等 5 个 |
| `582d8f5b` | 2026-10-11 | pinkpig-Peppa | huangrunheng | Merge pull request #1910 from m123711/fix/memoryscrolls-contribute | 3 | tasks/MemoryScrolls/assets.py、tasks/MemoryScrolls/ms/click.json、tasks/MemoryScrolls/script_task.py |
| `7ce0bb4d` | 2026-10-12 | pinkpig-Peppa | llBai | Merge branch 'dev' into master | 27 | tasks/ActivityShikigami/assets.py、tasks/ActivityShikigami/fire/image.json、tasks/ActivityShikigami/script_task.py、tasks/BondlingFairyland/general_invite.py 等 27 个 |
| `83534e56` | 2026-10-12 | pinkpig-Peppa | huangrunheng | Merge pull request #1931 from allesgutefy/fix/ui-check-assets | 2 | tasks/GlobalGame/ui/ui_ui_check.png、tasks/GlobalGame/ui/ui_ui_uncheck.png |
| `169fe6d6` | 2026-10-12 | pinkpig-Peppa | huangrunheng | Merge pull request #1930 from allesgutefy/fix/invite-default-checkbox-v5 | 2 | tasks/BondlingFairyland/general_invite.py、tasks/Component/GeneralInvite/general_invite.py |
| `04f3b234` | 2026-10-12 | pinkpig-Peppa | huangrunheng | Merge pull request #1932 from runhey/dev | 29 | tasks/ActivityShikigami/assets.py、tasks/ActivityShikigami/fire/image.json、tasks/ActivityShikigami/script_task.py、tasks/BondlingFairyland/general_invite.py 等 29 个 |
| `b4258efb` | 2026-10-13 | pinkpig-Peppa | davidyangkunlong | Merge branch 'dev' of https://github.com/davidyangkunlong/OnmyojiAutoScript into dev | 27 | tasks/ActivityShikigami/script_task.py、tasks/BondlingFairyland/general_invite.py、tasks/Component/GeneralBattle/battle.py、tasks/Component/GeneralInvite/general_invite.py 等 27 个 |
| `c291deb5` | 2026-10-13 | pinkpig-Peppa | huangrunheng | Merge pull request #1933 from llbai/master | 2 | tasks/Component/GeneralInvite/general_invite.py、tasks/Exploration/base.py |
| `124acb68` | 2026-10-14 | pinkpig-Peppa | huangrunheng | Merge pull request #1934 from Enough1122/fix/duel-setup-spin | 1 | tasks/Duel/script_task.py |
| `4c688865` | 2026-10-14 | pinkpig-Peppa | huangrunheng | Merge pull request #1905 from VanityHuang/fix/exploration-up-search | 2 | tasks/Exploration/base.py、tasks/Exploration/solo.py |
| `12048cad` | 2026-10-15 | pinkpig-Peppa | huangrunheng | Merge pull request #1937 from davidyangkunlong/YuhunOverflow | 3 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/battle_wait.py、tasks/Orochi/script_task.py |
| `68122b33` | 2026-10-15 | pinkpig-Peppa | huangrunheng | Merge pull request #1940 from kunkun008/fix/delegation-dead-loop | 1 | tasks/Delegation/script_task.py |
| `4e039cfb` | 2026-10-15 | pinkpig-Peppa | neptine | Merge remote-tracking branch 'origin/dev' into dev | 4 | tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/battle_wait.py、tasks/Delegation/script_task.py、tasks/Orochi/script_task.py |
| `19cbc452` | 2026-10-16 | pinkpig-Peppa | github-actions[bot] | Merge pull request #1941 from runhey/dev | 27 | .github/workflows/auto-merge-pr.yaml、tasks/ActivityShikigami/script_task.py、tasks/Component/GeneralBattle/assets.py、tasks/Component/GeneralBattle/battle.py 等 27 个 |
| `79c6a917` | 2026-10-18 | pinkpig-Peppa | huangrunheng | Merge pull request #1887 from LGG686/feat/desktop-client | 25 | assets/i18n/zh-CN.json、config/template.json、dev_tools/bind_desktop_window.py、module/atom/image.py 等 25 个 |
| `6d718fec` | 2026-10-18 | pinkpig-Peppa | huangrunheng | Merge pull request #1943 from Hurry2/dev | 1 | tasks/WeeklyTrifles/script_task.py |
| `dcfc6de6` | 2026-10-21 | pinkpig-Peppa | huangrunheng | Merge pull request #1959 from davidyangkunlong/UpdateClimbBossResources | 4 | tasks/ActivityShikigami/as/as_check_battle_boss.png、tasks/ActivityShikigami/as/as_to_battle_boss.png、tasks/ActivityShikigami/assets.py、tasks/ActivityShikigami/script_task.py |
| `6e425254` | 2026-10-21 | pinkpig-Peppa | huangrunheng | Merge pull request #1956 from weirj2016-ai/fix/restart-mail-harvest-timeout-dev | 1 | tasks/Restart/login.py |
| `88c3a936` | 2026-10-22 | pinkpig-Peppa | github-actions[bot] | Merge pull request #1964 from runhey/dev | 36 | assets/i18n/zh-CN.json、config/template.json、dev_tools/bind_desktop_window.py、module/atom/image.py 等 36 个 |
| `4e3528a6` | 2026-10-23 | pinkpig-Peppa | huangrunheng | Merge pull request #1963 from weirj2016-ai/fix/dokan-guanzhu-xiuxi-dev | 3 | tasks/Dokan/assets.py、tasks/Dokan/res/image.json、tasks/Dokan/res/res_ryou_dokan_center_guanzhu_xiuxi.png |
| `cc65d55d` | 2026-10-24 | pinkpig-Peppa | huangrunheng | Merge pull request #1966 from kunkun008/fix/mysteryshop-blue-buy-more | 7 | tasks/Component/Buy/assets.py、tasks/Component/Buy/buy.py、tasks/Component/Buy/buy/buy_buy_jade.png、tasks/Component/Buy/buy/image.json 等 7 个 |
| `0b1c1a02` | 2026-10-25 | pinkpig-Peppa | huangrunheng | Merge pull request #1969 from weirj2016-ai/fix/dokan-first-attack-failure-interval-dev | 1 | tasks/Dokan/script_task.py |
| `62957654` | 2026-10-25 | pinkpig-Peppa | huangrunheng | Merge pull request #1970 from davidyangkunlong/SoulOverflowOnOldGeneralBattle | 2 | tasks/Component/GeneralBattle/battle_wait.py、tasks/Component/GeneralBattle/general_battle.py |
| `f77f4fe1` | 2026-10-28 | pinkpig-Peppa | huangrunheng | Merge pull request #1973 from LGG686/WantedQuests | 28 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/gg_g_accept.png、tasks/GlobalGame/gg/gg_g_reject.png、tasks/GlobalGame/gg/image.json 等 28 个 |
| `dd860e03` | 2026-10-28 | pinkpig-Peppa | huangrunheng | Merge pull request #1974 from weirj2016-ai/fix/eternity-sea-member-lock-dev | 1 | tasks/EternitySea/script_task.py |
| `d345e96b` | 2026-10-28 | pinkpig-Peppa | huangrunheng | Merge pull request #1975 from weirj2016-ai/fix/dokan-create-every-run-dev | 1 | tasks/Dokan/script_task.py |
| `63b0d6d3` | 2026-10-28 | pinkpig-Peppa | neptine | Merge remote-tracking branch 'origin/dev' into dev | 1 | tasks/Dokan/script_task.py |
| `c6c724a4` | 2026-10-28 | pinkpig-Peppa | huangrunheng | Merge pull request #1976 from weirj2016-ai/fix/dokan-create-on-entry-dev | 1 | tasks/Dokan/script_task.py |
| `65311c50` | 2026-10-29 | pinkpig-Peppa | huangrunheng | Merge pull request #1977 from leovefy/dev | 7 | tasks/DailyTrifles/script_task.py、tasks/GameUi/assets.py、tasks/GameUi/default_pages.py、tasks/GameUi/page/image_main.json 等 7 个 |
| `2d2f6d89` | 2026-10-29 | pinkpig-Peppa | github-actions[bot] | Merge pull request #1985 from runhey/dev | 50 | module/atom/image.py、module/device/device.py、tasks/AreaBoss/script_task.py、tasks/Component/Buy/assets.py 等 50 个 |
| `17c42439` | 2026-10-31 | pinkpig-Peppa | huangrunheng | Merge pull request #1980 from allesgutefy/fix/invite-again-interval | 1 | tasks/Component/GeneralInvite/general_invite.py |
| `6f85146b` | 2026-10-31 | pinkpig-Peppa | huangrunheng | Merge pull request #1983 from Maratrain/feat-costume-shikigami-13 | 24 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/CostumeShikigami/assets.py 等 24 个 |
| `8bb2ee48` | 2026-10-31 | pinkpig-Peppa | huangrunheng | Merge pull request #1991 from weirj2016-ai/fix/global-invite-assets-dev | 6 | tasks/GlobalGame/assets.py、tasks/GlobalGame/gg/gg_g_accept.png、tasks/GlobalGame/gg/gg_g_ignore.png、tasks/GlobalGame/gg/gg_g_jade.png 等 6 个 |
| `cec45c30` | 2026-10-31 | pinkpig-Peppa | huangrunheng | Merge pull request #1993 from Hurry2/dev | 5 | assets/i18n/zh-CN.json、config/template.json、module/device/method/desktop_impl.py、tasks/Restart/script_task.py 等 5 个 |
| `8307b20a` | 2026-10-31 | pinkpig-Peppa | huangrunheng | Merge pull request #1994 from Hurry2/dev | 4 | module/device/desktop_device.py、module/device/handle.py、module/device/method/desktop_impl.py、script.py |
| `f1eff7f3` | 2026-11-02 | pinkpig-Peppa | huangrunheng | Merge pull request #1984 from weirj2016-ai/fix/talisman-pass-task-tab-dev | 2 | tasks/TalismanPass/script_task.py、tasks/TalismanPass/tp/tp_task_tab.png |
| `d1881b82` | 2026-11-02 | pinkpig-Peppa | huangrunheng | Merge pull request #1998 from Ghostuel/feat/xinyu-mingxiao-scroll | 14 | assets/i18n/zh-CN.json、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py、tasks/Component/CostumeTheme/assets.py 等 14 个 |
| `de497a3f` | 2026-11-02 | pinkpig-Peppa | huangrunheng | Merge pull request #2000 from leovefy/dev | 2 | tasks/SixRealms/moon_sea/map.py、tests/test_six_realms_island_entry.py |
| `969433f0` | 2026-11-04 | pinkpig-Peppa | huangrunheng | Merge pull request #1999 from Ghostuel/feat/yuehai-youxing-realm | 14 | tasks/Component/Costume/costume_base.py、tasks/Component/Costume/costume_test_realm.py、tasks/Component/CostumeCarpBanner/assets.py、tasks/Component/CostumeCarpBanner/cb1/image.json 等 14 个 |
| `41bf487f` | 2026-11-04 | pinkpig-Peppa | huangrunheng | Merge pull request #2004 from leovefy/dev | 1 | tasks/AreaBoss/script_task.py |
| `358aaa68` | 2026-11-04 | pinkpig-Peppa | huangrunheng | Merge pull request #2006 from leovefy/fix/wanted-quests-ocr | 1 | tasks/WantedQuests/script_task.py |
| `7854d54b` | 2026-11-04 | pinkpig-Peppa | huangrunheng | Merge pull request #2007 from leovefy/fix/six-realms-island-entry | 10 | tasks/SixRealms/assets.py、tasks/SixRealms/gate1/gate1_island_marker_101.png、tasks/SixRealms/gate1/gate1_island_marker_102.png、tasks/SixRealms/gate1/gate1_island_marker_103.png 等 10 个 |
| `c37eabcd` | 2026-11-04 | pinkpig-Peppa | huangrunheng | Merge pull request #2008 from Ghostuel/fix/main16-town-template | 3 | tasks/Component/Costume/assets.py、tasks/Component/Costume/main16/image.json、tasks/Component/Costume/main16/main16_main_goto_town_16.png |
| `55c3b151` | 2026-11-05 | pinkpig-Peppa | huangrunheng | Merge pull request #2020 from runhey/master | 30 | assets/i18n/zh-CN.json、tasks/Component/Costume/assets.py、tasks/Component/Costume/config.py、tasks/Component/Costume/costume_base.py 等 30 个 |
| `2211ba5d` | 2026-11-05 | pinkpig-Peppa | github-actions[bot] | Merge pull request #2022 from runhey/dev | 77 | .github/agents/agentic-workflows.md、.github/aw/actions-lock.json、.github/skills/agentic-workflows/SKILL.md、.github/workflows/agentics-maintenance.yml 等 77 个 |
| `2acad733` | 2026-11-06 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #2 from pinkpig-Peppa/trae/agent-pNZZr9 | 90 | deploy/adb.py、deploy/config.py、deploy/emulator.py、deploy/git.py 等 90 个 |
| `7b9ca9b0` | 2026-11-06 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #3 from pinkpig-Peppa/fix/core-review | 27 | module/atom/cBezier.py、module/atom/click.py、module/atom/list.py、module/atom/swipe.py 等 27 个 |
| `744702cf` | 2026-11-06 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #4 from pinkpig-Peppa/fix/tasks-review | 26 | tasks/AbyssShadows/script_task.py、tasks/ActivityShikigami/script_task.py、tasks/AutoCheckinBigGod/script_task.py、tasks/BondlingFairyland/script_task.py 等 26 个 |
| `05e4e9a2` | 2026-11-06 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #5 from pinkpig-Peppa/fix/gui-server-review | 35 | gui.py、module/gui/context/add.py、module/gui/context/process_manager.py、module/gui/context/settings.py 等 35 个 |
| `e940ad05` | 2026-11-06 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #6 from pinkpig-Peppa/fix/infra-review | 25 | deploy/adb.py、deploy/config.py、deploy/docker/Dockerfile、deploy/emulator.py 等 25 个 |
| `af846a0d` | 2026-11-08 | pinkpig-Peppa | niuma-workwork | Merge pull request #8 from pinkpig-Peppa/fix/metademon-new-ui | 47 | tasks/MetaDemon/README.md、tasks/MetaDemon/assets.py、tasks/MetaDemon/config.py、tasks/MetaDemon/md/Screenshots_a2.png 等 47 个 |
| `69b7ca1a` | 2026-11-09 | nearaura | blylana | Merge pull request #1 from nearaura/dev | 294 | .github/agents/agentic-workflows.md、.github/aw/actions-lock.json、.github/skills/agentic-workflows/SKILL.md、.github/workflows/agentics-maintenance.yml 等 294 个 |
| `41753016` | 2026-11-11 | nearaura | blylana | Merge pull request #2 from kristin0512/fix-minitouch-pressure-range | 1 | module/device/method/minitouch.py |
| `8fb6f834` | 2026-11-11 | nearaura | blylana | Merge pull request #4 from LLLLLUOTJ/fix-exploration-marker-roi | 3 | tasks/GameUi/assets.py、tasks/GameUi/page/image_exploration.json、tests/tasks/GameUi/test_exploration_marker.py |
| `27d0531f` | 2026-11-11 | nearaura | blylana | Merge remote-tracking branch 'origin/dev' into dev | 3 | tasks/GameUi/assets.py、tasks/GameUi/page/image_exploration.json、tests/tasks/GameUi/test_exploration_marker.py |
| `b066ad8c` | 2026-11-11 | nearaura | blylana | Merge commit '484337f5' into dev | 6 | tasks/MetaDemon/assets.py、tasks/MetaDemon/config.py、tasks/MetaDemon/md/md_enter2.png、tasks/MetaDemon/md/md_md_win.png 等 6 个 |
| `a6e22e0a` | 2026-11-12 | kongdr418 | kongdr418 | Merge pull request #1 from jl5250/mine | 4 | tasks/Duel/assets.py、tasks/Duel/duel/duel_duel_main_uesless_message.png、tasks/Duel/duel/duel_exit_waiting.png、tasks/Duel/script_task.py |
| `48f34cb0` | 2026-11-12 | nearaura | blylana | Merge pull request #8 from nearaura/dev | 55 | .github/workflows/auto-create-pr.yaml、.github/workflows/auto-merge-pr.yaml、.github/workflows/github-mirror.yml、README.md 等 55 个 |
| `3f579393` | 2026-11-14 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #9 from pinkpig-Peppa/feature/stats-watchdog-apprise | 10 | module/notify/notify.py、module/server/api_logger.py、module/server/app.py、module/server/log_router.py 等 10 个 |
| `699ec79d` | 2026-11-14 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #10 from pinkpig-Peppa/feature/paddleocr-engine | 21 | module/atom/list.py、module/atom/ocr.py、module/base/worker_metrics.py、module/image/__init__.py 等 21 个 |
| `6382117a` | 2026-11-14 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #11 from pinkpig-Peppa/feature/nearaura-fixes | 47 | module/atom/animate.py、module/atom/image.py、module/base/utils/utils.py、module/device/desktop_device.py 等 47 个 |
| `f73072c8` | 2026-11-15 | nearaura | blylana | Merge pull request #11 from allesgutefy/fix/md-fatigue-summon-first | 3 | assets/i18n/zh-CN.json、tasks/MetaDemon/config.py、tasks/MetaDemon/script_task.py |
| `17ce61a0` | 2026-11-15 | pinkpig-Peppa | pinkpig-Peppa | Merge pull request #12 from pinkpig-Peppa/feature/oas-doctor | 2 | module/server/doctor.py、module/server/tool_router.py |
| `ac712acc` | 2026-11-16 | nearaura | blylana | Merge remote-tracking branch 'origin/dev' into dev | 3 | assets/i18n/zh-CN.json、tasks/MetaDemon/config.py、tasks/MetaDemon/script_task.py |
| `bb5a54a7` | 2026-11-20 | lgg686 | LGG686 | 合并 Android 端适配改动到 self | 22 | config/template.json、module/config/config_manual.py、module/config/config_model.py、module/device/app_control.py 等 22 个 |
| `12e61d99` | 2026-11-20 | lgg686 | LGG686 | 合并 Android 适配批次到 self | 8 | deploy/template、module/device/method/oasaos.py、module/server/android_router.py、module/server/hot_update.py 等 8 个 |
| `93883894` | 2026-11-22 | nearaura | blylana | Merge pull request #18 from Tyrion-hao/fix/hyakkiyakou-offscreen-focus | 3 | tasks/Hyakkiyakou/agent/agent.py、tasks/Hyakkiyakou/agent/focus.py、tests/tasks/Hyakkiyakou/test_agent_focus.py |
| `2111c938` | 2026-11-22 | nearaura | blylana | Merge pull request #14 from 2263075977/fix/six-realms-island-entry-reread | 3 | tasks/SixRealms/moon_sea/map.py、tasks/SixRealms/moon_sea/moon_sea.py、tests/test_six_realms_island_entry.py |

空合并：
- `26ae37a1` 2026-10-12 Merge branch 'master' into dev

## 5. 同步优先级建议

### P0 优先合并（11 条）

小范围、模块内聚、本地定制低的修复，可优先进 staging 验证（冲突以 apply 预检为准）

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `acbdbf1c` | Chess | fix(Chess): 加宽鼬乐币 OCR 区域，修复刷满不停止 | 部分实现 | 小 | 未预判 |
| `8f945012` | Chess | fix(Chess): 买卡成功与商店换卡后清理格子点击记录 | 部分实现 | 小 | 未预判 |
| `a9597e77` | Chess | fix(Chess): 卖卡与上御魂前清理点击记录，修复 GameTooManyClickError | 部分实现 | 小 | 未预判 |
| `a70757b1` | Exploration | fix(Exploration): Prevent premature back navigation during exit #1935 | 部分实现 | 小 | 未预判 |
| `27dc33a4` | FrogBoss | fix(FrogBoss): 调整对弈竞猜策略逻辑 | 部分实现 | 小 | 未预判 |
| `9ec93a44` | FrogBoss | fix(FrogBoss): 修复下注确认被弹窗遮挡导致的死循环 | 部分实现 | 小 | 未预判 |
| `57c3f701` | GlobalGame | fix(GlobalGame): 放宽协作图标识别区域 | 部分实现 | 小 | 未预判 |
| `91010725` | GlobalGame | fix(GlobalGame): 放宽忽略按钮识别区域 | 部分实现 | 小 | 未预判 |
| `885ea02c` | Restart | fix(Restart): 调整登录界面「进入游戏」OCR 识别区域 | 部分实现 | 小 | 未预判 |
| `ac482cf2` | WantedQuests | fix(WantedQuests): 调整悬赏列表 OCR 区域，适配新UI排版 | 部分实现 | 小 | 未预判 |
| `73cf2c63` | base_task.py | fix(base_task): 补 clock_time 导入，修复百鬼棋局 set_next_run_next_monday 报 NameError | 部分实现 | 小 | 未预判 |

### P1 可排期（95 条）

可复用优化或修复，但预计冲突/需实测，按模块排期

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `9f8841f1` | AbyssShadows | 修复(狭间)：切换御魂前关闭残留分布弹窗 | 部分实现 | 小 | 1 文件 |
| `e68b0b74` | AbyssShadows | fix(GeneralBattle): 退出战斗确认按钮兼容新旧两套UI | 部分实现 | 小 | 3 文件 |
| `aa91067c` | AbyssShadows | fix(AbyssShadows)：修复狭间暗域战斗瞬间结算导致 attack_enemy 卡死 | 部分实现 | 小 | 1 文件 |
| `e4935560` | ActivityShikigami | 优化(式神活动)：门票选项为空时跳过门票爬塔 | 部分实现 | 中 | 4 文件 |
| `43c7f334` | ActivityShikigami | fix(ActivityShikigami): Broaden pass screen detection area | 部分实现 | 小 | 2 文件 |
| `fe98ffef` | ActivityShikigami | UpdateClimbBossResources | 部分实现 | 中 | 4 文件 |
| `6084f210` | ActivityShikigami | fix(ActivityShikigami)：爬塔挑战遇弹窗改为关闭后重试 | 部分实现 | 小 | 1 文件 |
| `48ba3280` | ActivityShikigami | fix(ActivityShikigami)：探索剧情结束改为奖励面板或主界面二者其一 | 部分实现 | 小 | 1 文件 |
| `692ee215` | AreaBoss | fix(AreaBoss): 跳过与悬赏鬼王重名的目标，避免重复挑战导致少打一只 | 部分实现 | 小 | 1 文件 |
| `7b0da642` | BondlingFairyland | fix(bondling)：删除漏邀分支，队员退回主界面即判房间销毁 | 部分实现 | 小 | 1 文件 |
| `ba0d49b7` | BondlingFairyland | fix(bondling)：调整建房逻辑，调整补邀时间间隔 | 部分实现 | 小 | 无冲突 |
| `45b5772d` | Chess | fix(Chess): 百鬼无需御魂时等全员解锁后随机投掷 | 部分实现 | 小 | 1 文件 |
| `8d64b1e4` | Chess | fix(chess)：购买点击加单轮上限并在成功后清理记录 | 部分实现 | 小 | 2 文件 |
| `0e711238` | Component | feat(GeneralBattle): Add completion fallback click and randomclick expectation model | 部分实现 | 小 | 1 文件 |
| `d54042b5` | Component | feat(GeneralBattle): Add battle count and state reset helpers, restore climb counting | 部分实现 | 小 | 3 文件 |
| `4f0b246b` | Component | 修正(庭院主题)：更新第13期主页与宠物屋识别资源 | 部分实现 | 中 | 3 文件 |
| `1c646ce5` | Component | 优化(通用战斗)：调整随机点击区域与风险档位 | 部分实现 | 中 | 2 文件 |
| `17474206` | Component | fix(Login): 延长等待角色选择页的超时时间，避免登录卡死 | 部分实现 | 小 | 未预判 |
| `3d85565f` | Component | fix(Login): 桌面登录期处理 MPay 弹窗，避免误判未知页面 | 部分实现 | 小 | 1 文件 |
| `c1dc5059` | Component | feat(Costume): Add Chinese names to costume switch logs | 部分实现 | 小 | 1 文件 |
| `100879bb` | Component | fix(SwitchSoul): 重截切换确认弹窗按钮并修正ROI | 部分实现 | 小 | 3 文件 |
| `57fc173b` | Component | fix(GeneralBattle): 重截退出战斗确认按钮并改用新素材 | 部分实现 | 中 | 2 文件 |
| `27241886` | Component | fix(GeneralBattle): Avoid reward popup during completion fallback #1913 | 部分实现 | 中 | 未预判 |
| `2f5c306e` | Component | fix(invite_friends)：sleep(3) before invite_friend | 部分实现 | 小 | 未预判 |
| `d6c42bee` | Component | fix(GeneralBattle): Log battle start in strategy-based wait | 部分实现 | 小 | 1 文件 |
| `cacc2af3` | Component | 御魂溢出处理升级 | 部分实现 | 小 | 未预判 |
| `2d7b85de` | Component | fix: resolve theme log translation and strengthen invalid-theme regression tests | 部分实现 | 小 | 2 文件 |
| `ab2b0c00` | Component | fix: update manual realm tool enum and add offline regression check | 部分实现 | 小 | 2 文件 |
| `657bb1b3` | Component | fix: update main16 town entrance template and generated rule | 部分实现 | 小 | 3 文件 |
| `4a6ad558` | Component | fix(GeneralBattle): Add soul overflow cleanup click rule #1979 | 部分实现 | 小 | 1 文件 |
| `209f8fad` | Component | fix(GeneralBattle): 校准超鬼王门票 OCR 区域 | 部分实现 | 小 | 1 文件 |
| `fe65e54b` | Component | fix(GeneralInvite): Shrink I_FLAG_1_ON ROI to keep the selected friend tab detected  #20 | 部分实现 | 小 | 3 文件 |
| `602730c6` | Delegation | 修正(式神委派)：收窄完成状态OCR识别区域 | 部分实现 | 小 | 1 文件 |
| `f3f62f43` | DemonEncounter | 修复(逢魔之时)：确认弹窗关闭与首领识别并限制三轮召集尝试 | 部分实现 | 小 | 1 文件 |
| `40fbf76a` | DemonEncounter | fix(demon_encounter)：修复逢魔重进地图 town↔rwt 死循环 | 部分实现 | 小 | 1 文件 |
| `252c6701` | DemonEncounter | fix(demon_encounter)：调整enter_boss逻辑，增加次数复检 | 部分实现 | 小 | 2 文件 |
| `62f488b3` | Dokan | fix(Dokan,FallenSun): replace removed I_BACK_BL with I_UI_BACK_BLUE | 部分实现 | 小 | 2 文件 |
| `cf9eba73` | Duel | 修复(斗技)：达到名士星数目标后延至下周一运行 | 部分实现 | 小 | 1 文件 |
| `9eea7c9d` | Duel | feat(Duel): 增加斗技识别的资源以及更正返回庭院的函数 | 部分实现 | 中 | 1 文件 |
| `bf893c0d` | Duel | fix(Duel): 补齐斗技识别资源标注并同步生成配置 | 部分实现 | 小 | 1 文件 |

> 其余 55 条见 §3.1 逐条明细。


### P2 单独评估（83 条）

核心模块大改或本地完全缺失的功能，需单独立项评估

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `014ffa84` | AbyssShadows | 优化(狭间)：跳过重复御魂装配并识别已击破目标 | 部分实现 | 中 | 2 文件 |
| `ef48a3fd` | ActivityShikigami | 适配(式神活动)：按本期Boss入口更新页面与识别资源 | 部分实现 | 中 | 7 文件 |
| `1f9e14d4` | ActivityShikigami | 优化(式神活动爬塔)：修正票数追踪并清理旧战斗资源 | 部分实现 | 中 | 6 文件 |
| `b3d6fe98` | ActivityShikigami | fix(ActivityShikigami): Update | 部分实现 | 大 | 未预判 |
| `5cf103ea` | ActivityShikigami | feat(activity)：适配当期爬塔分家布局并统一挑战按钮为 OCR 引导 | 部分实现 | 大 | 18 文件 |
| `0b7ee83e` | ActivityShikigami | feat(ActivityShikigami)：探索新增委派模式并重裁活动识别模板 | 部分实现 | 大 | 19 文件 |
| `23ce874b` | AutoCheckinBigGod | fix(AutoCheckinBigGod)：手动UI简化，修复清理后游戏被二次重启与横竖屏状态未还原 | 部分实现 | 中 | 1 文件 |
| `fc45a500` | BorrowShikigami | fix(BorrowShikigami): 调整15级起号流程并补齐新手弹窗处理 | 完全缺失 | 大 | 10 文件 |
| `628c0cfb` | BorrowShikigami | fix(BorrowShikigami): 通过自动标识兼容新手战斗页面 | 完全缺失 | 小 | 2 文件 |
| `1a9a1f61` | Chess | 优化(百鬼棋局)：匹配竞态保护与阵容核对及周目标调度 | 部分实现 | 中 | 3 文件 |
| `b94dc89c` | Chess | 整合(百鬼棋局)：将状态决策流程迁入正式版本 | 部分实现 | 大 | 无冲突 |
| `4c5d633a` | Chess | feat(Chess): 同步百鬼投掷、黄金复制术与平安京阵容 | 部分实现 | 大 | 10 文件 |
| `5a8f7385` | Chess | feat(Chess): OCR 接入 v6-small | 部分实现 | 中 | 4 文件 |
| `d2f98590` | Component | feat(GeneralBattle): Add prepare/preset/green/echo/randomclick hooks and config-driven loa | 部分实现 | 大 | 4 文件 |
| `6c3d2927` | Component | 调整(通用战斗)：更新探索与活动Scatter安全区域 | 部分实现 | 大 | 2 文件 |
| `bb808e1b` | Component | feat(Costume): Attach GIF multi-frame behavior in-place so page routing works  #1824 - add | 部分实现 | 中 | 6 文件 |
| `64199898` | Component | feat(GeneralInvite): 等待好友列表加载完成并简化房间锁定判定 | 部分实现 | 中 | 3 文件 |
| `8f0ebc1c` | Component | 优化(全局):调整默认庭院检查资源，新增登陆保底点击。 | 部分实现 | 大 | 3 文件 |
| `2f503b4b` | Component | fix(GeneralBattle)：重画 Act 结算页安全点击区域 | 部分实现 | 大 | 2 文件 |
| `71e33265` | Component | refactor(SwitchSoul): Reuse shared confirm button across costume flows - replace dedicated | 部分实现 | 大 | 3 文件 |
| `84eda193` | Component | fix(GeneralInvite): Use shared UI assets for invite confirmation #1915 - replace invite-sp | 部分实现 | 大 | 4 文件 |
| `14cbd413` | Component | feat(GeneralInvite): 同步上游邀请组件，适配新界面并等待好友列表加载 | 部分实现 | 大 | 7 文件 |
| `e0773898` | Component | fix(tasks): initialize state, guard OCR results, bound loops in task scripts | 部分实现 | 大 | 18 文件 |
| `a67366d1` | DailyTrifles | fix(DailyTrifles)：Add cancel button for summon animation popup in courtyard affairs | 部分实现 | 中 | 2 文件 |
| `d814b589` | Delegation | 修复(委派)：补充领奖对话验证并更新出战识别资源 | 部分实现 | 大 | 3 文件 |
| `a04d51da` | DemonEncounter | fix(DemonEncounter): 优化boss搜索容错并处理中央宝箱遮挡 | 部分实现 | 中 | 4 文件 |
| `65a3ebfb` | DraftDuel | fix(DraftDuel): 修正金币消耗识别范围 | 完全缺失 | 小 | 2 文件 |
| `c78b436f` | DraftDuel | fix(DraftDuel): 免费次数按关键字识别 | 完全缺失 | 小 | 1 文件 |
| `613a32d0` | DraftDuel | feat(DraftDuel): 接入选式神与推荐选择 | 完全缺失 | 大 | 4 文件 |
| `8e483e5c` | DraftDuel | fix(DraftDuel): 队员接受邀请后保持等待 | 完全缺失 | 小 | 1 文件 |
| `2013a89d` | DraftDuel | feat(DraftDuel): 队员接入选式神 | 完全缺失 | 小 | 1 文件 |
| `5da8bbb5` | DraftDuel | fix(DraftDuel): 推荐检查窗口延长到15秒 | 完全缺失 | 小 | 1 文件 |
| `5dd027bf` | DraftDuel | feat(DraftDuel): 记录选中的式神并兼容自动选 | 完全缺失 | 小 | 1 文件 |
| `11ab2343` | DraftDuel | feat(DraftDuel): 任务内使用 PP-OCRv6-small 识别 | 完全缺失 | 大 | 2 文件 |
| `1f7b10b1` | DraftDuel | feat(DraftDuel): 接入选卡策略与五轮选人 | 完全缺失 | 大 | 1 文件 |
| `19e5a562` | DraftDuel | fix(DraftDuel): V6 解码补空格类 | 完全缺失 | 小 | 1 文件 |
| `fc6b5070` | DraftDuel | fix(DraftDuel)：清理大轮结算浮窗并正确回到下一大轮 | 完全缺失 | 中 | 7 文件 |
| `0aba58d5` | DraftDuel | fix(DraftDuel): 校准式神头像裁切、缩放与阈值序列 | 完全缺失 | 中 | 5 文件 |
| `bd2acfa3` | DraftDuel | fix(draft-duel): 按五张手牌中段验证上阵并限制开放时段 | 完全缺失 | 大 | 9 文件 |
| `b08d8e2a` | DraftDuel | fix(draft-duel): 稳定采集手牌并在首局后释放模板 | 完全缺失 | 中 | 6 文件 |

> 其余 43 条见 §3.1 逐条明细。


### P3 谨慎评估（85 条）

触及 module/*、入口脚本、共享资产或配置结构，谨慎评估、隔离批次

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `d9c877a4` | ActivityShikigami | 调整(式神活动探索)：取消滑动与模式筛选并统一奖励处理 | 部分实现 | 中 | 7 文件 |
| `f339b5a6` | ActivityShikigami | feat(ActivityShikigami)：适配 OASX v0.3.16 式神活动配置契约 | 部分实现 | 中 | 4 文件 |
| `df43725c` | ActivityShikigami | fix(ActivityShikigami)：重写探索剧情跳过流程，更新委派入口模板 | 部分实现 | 中 | 5 文件 |
| `9d7eb7e2` | ActivityShikigami | feat: 移植超鬼王与活动控制并适配设置布局 | 部分实现 | 大 | 39 文件 |
| `85632077` | AreaBoss | fix(AreaBoss): Handle fox battle scene settlement #1967 | 部分实现 | 小 | 未预判 |
| `547dfba6` | AutoStory | feat(游戏辅助): 迁移自动剧情、探索推进和自定义任务 | 完全缺失 | 大 | 5 文件 |
| `3a8ba22f` | BorrowShikigami | feat(游戏辅助): 新增15级起号流程并适配新手引导 | 完全缺失 | 大 | 15 文件 |
| `1aacf5a5` | Chess | 调整(百鬼棋局):删除结算Scatter点击，回调至随机点击区域。 | 部分实现 | 中 | 4 文件 |
| `d43d8b56` | Chess | refactor(assets)：按钮类调用收敛至通用模板并清理废弃资产 | 部分实现 | 大 | 16 文件 |
| `6029ad08` | Chess | feat(Chess): 移植新版百鬼棋局（含帧规则与识别能力） | 部分实现 | 大 | 6 文件 |
| `74425d03` | Chess | fix(Chess): 同步上游百鬼主动投掷与特殊回合识别修复 | 部分实现 | 大 | 11 文件 |
| `40e2f527` | Chess | feat(chess)：同步上游百鬼棋局实现 | 部分实现 | 大 | 16 文件 |
| `31484b10` | Chess | feat(Chess): 同步上游阵容编辑器与 JSON 配置，斗技补充 ban 检测 | 部分实现 | 大 | 19 文件 |
| `5001c0bc` | Chess | feat(Chess)：同步百鬼棋局策略、资源与标注器改动，Device 新增按住拖动 | 部分实现 | 大 | 26 文件 |
| `d3e81d3a` | Chess | feat(Chess): 同步新版百鬼棋局 | 部分实现 | 大 | 21 文件 |
| `36e1a822` | Component | feat(Costume): Support time-variant courtyard skin 玉岚狐庭 #1824 | 部分实现 | 大 | 6 文件 |
| `f130ab3f` | Component | 调整(图像点击)：统一Image规则为High并更新默认值 | 部分实现 | 大 | 95 文件 |
| `08079eaf` | Component | feat(Costume): Add task-scoped battle scene skin support #1843 | 部分实现 | 中 | 4 文件 |
| `a67309e7` | Component | refactor(assets): 清理冗余资产并将确认类调用收敛至通用模板 | 部分实现 | 大 | 18 文件 |
| `ba699f87` | Component | feat(Costume): 新增幕间主题梦隙闲花 | 部分实现 | 大 | 1 文件 |
| `b46be8a6` | Component | feat: support Xinyu Mingxiao scroll and shared masked guild entrance | 部分实现 | 大 | 3 文件 |
| `cfcdad39` | Component | feat: support Yuehai Youxing realm with shared template search regions | 部分实现 | 中 | 5 文件 |
| `9636b724` | Component | fix: share cross-skin realm search regions and replace EXP bottle template | 部分实现 | 大 | 11 文件 |
| `a80e1931` | Component | chore: rebase onto upstream master and reapply cleanup changes | 部分实现 | 大 | 38 文件 |
| `287d59f0` | DraftDuel | feat(DraftDuel): 新增协同对弈任务骨架与大厅消耗识别 | 完全缺失 | 大 | 1 文件 |
| `1012030e` | DraftDuel | feat(DraftDuel): 接入邀请好友与队长/队员模式 | 完全缺失 | 中 | 5 文件 |
| `fe1c0881` | DraftDuel | feat(DraftDuel): 组队后点「战」进入选式神 | 完全缺失 | 中 | 5 文件 |
| `dac21615` | DraftDuel | feat(DraftDuel)：新增协同对弈任务与双实例协同框架 | 完全缺失 | 大 | 9 文件 |
| `a12c4e42` | DraftDuel | 修复协斗识别与上阵、MuMu启动及棋局羁绊，完善契灵身份交换 | 完全缺失 | 大 | 12 文件 |
| `d06f9672` | DraftDuel | feat(DraftDuel): 整合协同选人、上阵及双端自动上阵流程 | 完全缺失 | 大 | 15 文件 |
| `f428bbec` | DraftDuel | feat(DraftDuel): 添加队友推荐开关并拆分任务运行模块 | 完全缺失 | 大 | 4 文件 |
| `255b2b25` | DraftDuel | feat(DraftDuel): 完善离队结算与自动上阵判定 | 完全缺失 | 大 | 7 文件 |
| `91f19356` | DraftDuel | feat(DraftDuel): 统一阵容矩阵评分并同步队友选卡进度 | 完全缺失 | 大 | 4 文件 |
| `7112d251` | DraftDuel | feat(DraftDuel): 联合队友候选选卡并移除错误式神条目 | 完全缺失 | 中 | 6 文件 |
| `446e869e` | DraftDuel | feat(DraftDuel): 记录真实协同对局 | 完全缺失 | 大 | 未预判 |
| `48164d4e` | FrogBoss | feat(FrogBoss): 适配十周年素材并新增非等权预测策略 frog_oas | 部分实现 | 大 | 9 文件 |
| `414d42df` | FrogBoss | 调整(对弈竞猜):调整竞猜对应素材。 | 部分实现 | 中 | 1 文件 |
| `76490d67` | GuildBanquet | fix(GuildBanquet): 兼容第二种寮宴会旗帜并修复加成开关资产重名 | 部分实现 | 大 | 未预判 |
| `69ded977` | KekkaiUtilize | 拆分(结界蹭卡)：独立控制体力食盒与经验酒壶 | 部分实现 | 中 | 1 文件 |
| `efcc78ad` | MetaDemon | fix(MetaDemon): 适配新版超鬼王“祸至无日/祸主降临”活动界面 | 部分实现 | 大 | 14 文件 |

> 其余 45 条见 §3.1 逐条明细。


### P4 低优先（7 条）

文档/CI/格式类，随时可做但收益低

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `3b161aba` | Chess | Revert "新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程" | 部分实现 | 大 | 无冲突 |
| `8195cc60` | Component | Revert "fix: use interval=3 instead of sleep(0.8) per developer suggestion" | 部分实现 | 小 | 未预判 |
| `614b6b84` | Exploration | Revert "delete  S_SWIPE_LEVEL_DOWN_PRO" | 部分实现 | 小 | 未预判 |
| `e56482ca` | Exploration | Revert "add S_SWIPE_LEVEL_DOWN_PRO" | 部分实现 | 小 | 未预判 |
| `bc2211da` | 文档/CI | docs(Docs): Update documentation links to the new domain | 部分实现 | 小 | 未预判 |
| `a8bd3bc8` | 根目录 | docs: 上游删库后整理仓库文档与 README | 部分实现 | 大 | 1 文件 |
| `fd767a1d` | 根目录 | docs(README): Add temporary repository links after account suspension | 部分实现 | 小 | 无冲突 |

### skip 不引入（26 条）

Android/OASA 运行时或 CI 专属，本地无对应运行时，不引入

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `80751206` | AutoStory | feat(AutoStory)：完善剧情结束判定与视频加速处理 | 完全缺失 | 中 | 3 文件 |
| `d1de2080` | Restart | refactor(Login)：登录界面按钮改用通用UI资产并新增引擎更新跳过 | 部分实现 | 大 | 6 文件 |
| `aaede1db` | TrueOrochi | feat(TrueOrochi): 玩法tab模块检测替代本地次数记账 | 完全缺失 | 中 | 无冲突 |
| `f7db71b2` | TrueOrochi | feat(TrueOrochi)：用玩法 tab 模块在场检测替代本地次数记账 | 完全缺失 | 中 | 2 文件 |
| `db601816` | module/device | feat(Android)：Add oasaos device backend and native panel compatibility | 部分实现 | 大 | 5 文件 |
| `50dec6ce` | module/server | 移植统计/日志模块, 新增看门狗与 Apprise 通知 | 部分实现 | 大 | 4 文件 |
| `adfa6e84` | module/server | feat(Android)：Hot-update OAS source from a Git repository | 部分实现 | 大 | 1 文件 |
| `52f23c56` | module/server | fix(server)：局域网口令改为可选并支持 Cookie 会话 | 部分实现 | 小 | 1 文件 |
| `17bb2993` | module/server | feat(android)：同步适配批次到 OASA | 部分实现 | 大 | 3 文件 |
| `f7a3f643` | module/server | fix(server)：补齐提交历史接口并输出作者 | 部分实现 | 小 | 2 文件 |
| `8b06fd35` | module/server | fix(server)：修复提交历史拉不到与首次为空 | 部分实现 | 小 | 1 文件 |
| `4bf1a8b7` | module/server | fix(server)：git 残留锁自动清理重试 | 部分实现 | 小 | 1 文件 |
| `3051c38c` | module/server | fix(server)：热更首拉超时残留锁与历史面板空转 | 部分实现 | 小 | 1 文件 |
| `c4f533ab` | module/server | fix(server)：提交历史优先返回已拉到的远端列表 | 部分实现 | 小 | 1 文件 |
| `96a34f39` | module/server | feat(server)：提交历史返回描述正文并支持仅重启 OAS | 部分实现 | 小 | 2 文件 |
| `1589899a` | 文档/CI | chore(workflow): Update automation workflows to gpt-6-luna | 部分实现 | 中 | 9 文件 |
| `f871f379` | 文档/CI | chore(workflow): Upgrade GitHub Agentic Workflow runtime | 部分实现 | 大 | 未预判 |
| `a27a91fe` | 文档/CI | fix(workflow): Restore supported AI model pricing #1879 | 部分实现 | 中 | 未预判 |
| `b9f33b8b` | 文档/CI | feat(doc): 新增变更日志 | 部分实现 | 小 | 未预判 |
| `a192e085` | 文档/CI | chore(doc): 删除变更日志 | 部分实现 | 小 | 无冲突 |
| `9cfb4d29` | 文档/CI | feat(workflow): Schedule Monday automated PR creation and merge | 部分实现 | 小 | 2 文件 |
| `d9c28f51` | 文档/CI | chore(workflow): Upgrade GitHub Agentic Workflows to v1.0.1 | 部分实现 | 大 | 15 文件 |
| `305defd0` | 文档/CI | fix(workflow): use current repository owner for mirroring | 部分实现 | 小 | 未预判 |
| `25cc699b` | 文档/CI | feat(workflow): Create and merge sync PR on schedule | 部分实现 | 中 | 1 文件 |
| `65c5b127` | 根目录 | fix(Deploy): 默认仓库指向本仓库 mine 分支 | 部分实现 | 小 | 未预判 |
| `d7e7f2bf` | 根目录 | fix(deploy): keep template indentation when writing deploy.yaml | 部分实现 | 小 | 1 文件 |

### done 已处理（176 条）

本地已同步或台账已记录，无需重复处理

| 提交 | 模块 | 摘要 | 状态 | 规模 | 冲突预判 |
| --- | --- | --- | --- | --- | --- |
| `d38f6e95` | AbyssShadows | fix(AbyssShadows)：确认按钮改用通用资产 I_UI_CONFIRM | 已完整同步 | 中 | 1 文件 |
| `ef0f8d11` | AutoCheckinBigGod | 适配(大神福利)：新版领取界面并修复空按钮等待 | 已完整同步 | 中 | 未预判 |
| `3f15a981` | BondlingFairyland | 修复(契灵)：建房过渡时识别已进入房间 | 已完整同步 | 小 | 未预判 |
| `e8df3ae0` | BondlingFairyland | fix: update interval=3 for I_UI_UNCHECK and I_UI_CONFIRM in check_and_invite | 已完整同步 | 小 | 2 文件 |
| `844d3bec` | BondlingFairyland | fix(bondling)：恢复交换身份在单次任务内按半量切换 | 已完整同步 | 小 | 1 文件 |
| `1d67a992` | Chess | 新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程 | 已完整同步 | 大 | 无冲突 |
| `1410590f` | Chess | fix(Chess): 清理商店槽位点击记录，修复买卡触发 GameTooManyClickError | 已完整同步 | 小 | 未预判 |
| `ce9903bf` | Chess | fix(Chess): 手牌满且无可操作时出售一张阵容卡腾位 | 已完整同步 | 小 | 无冲突 |
| `fa7a87e7` | Chess | fix(Chess): 买卡前清理槽位点击记录，修复 GameTooManyClickError | 已完整同步 | 小 | 未预判 |
| `9df707fb` | Chess | fix(Chess): 限制每轮买卡点击次数，重试失败后取消购买 | 已完整同步 | 小 | 2 文件 |
| `d1ad2c09` | Chess | fix(Chess): 调整棋局规则搜索范围 | 已完整同步 | 小 | 未预判 |
| `13221d2c` | CollectiveMissions | fix(CollectiveMissions): Handle reward claims and timeout after donation  #7 | 已完整同步 | 小 | 1 文件 |
| `05560e29` | Component | 新增(换装战斗)：接入灵狐寄愿主题与识别资源 | 已完整同步 | 大 | 未预判 |
| `52b91fe9` | Component | 修复(战斗预设)：缩小前三队点击区域避免误滑 | 已完整同步 | 小 | 未预判 |
| `18b0394e` | Component | 修复(战斗预设)：确认点击后等待弹窗关闭 | 已完整同步 | 小 | 未预判 |
| `8ec6ae47` | Component | 清理(生成资源)：统一注释空白与文件结尾 | 已完整同步 | 中 | 未预判 |
| `395fef27` | Component | 修复(全局页面)：识别闲庭并关闭战斗奖励详情 | 已完整同步 | 大 | 7 文件 |
| `37a884ef` | Component | fix(Costume): Skip missing assets when attaching GIF frames | 已完整同步 | 小 | 1 文件 |
| `929c6a11` | Component | fix(SwitchOnmyoji): give both switch_role loops a bounded exit | 已完整同步 | 中 | 未预判 |
| `7c850c3c` | Component | refactor(GeneralRoom): ensure 类方法移除硬编码阈值，改用资产自带阈值 | 已完整同步 | 小 | 1 文件 |
| `33c40a65` | Component | refactor(GeneralInvite): click_fire 移除硬编码阈值，改用资产自带阈值 | 已完整同步 | 小 | 1 文件 |
| `4e32d985` | Component | feat(GeneralBattle): 支持按式神名点击绿标 | 已完整同步 | 中 | 5 文件 |
| `5bc3f6e2` | Component | fix(GeneralBattle): Support named green marks in battle wait | 已完整同步 | 中 | 2 文件 |
| `990c4590` | Component | fix: add missing run_task_or_default_general_battle function | 已完整同步 | 小 | 未预判 |
| `55f51238` | Component | fix: handle AttributeError for tasks without general_battle_config | 已完整同步 | 小 | 未预判 |
| `ca7a4189` | Component | fix: add 0.8s delay after clicking I_I_NO_DEFAULT to wait for UI update | 已完整同步 | 小 | 未预判 |
| `e930e2e1` | Component | fix: use interval=3 instead of sleep(0.8) per developer suggestion | 已完整同步 | 小 | 未预判 |
| `7f0728bf` | Component | 点击御魂溢出的提示 | 已完整同步 | 小 | 未预判 |
| `60117f17` | Component | 处理御魂溢出 | 已完整同步 | 小 | 未预判 |
| `43c84c88` | Component | fix(GeneralBattle): Close buff panel and start battle preparation | 已完整同步 | 小 | 无冲突 |
| `b1c7186c` | Component | fix(GeneralInvite): Update invite confirmation ROI for wanted quests #1939 | 已完整同步 | 小 | 无冲突 |
| `4b823fde` | Component | fix(GeneralInvite): use interval=3 for I_UI_UNCHECK in invite_again | 已完整同步 | 小 | 未预判 |
| `5ba75f9b` | Component | fix(GeneralBattle): Add soul overflow cleanup click rule #1979 | 已完整同步 | 中 | 3 文件 |
| `802643de` | DailyTrifles | feat(DailyTrifles): 新增每日收益统计 | 已完整同步 | 大 | 未预判 |
| `97575ca7` | DailyTrifles | refactor(DailyTrifles): 每日收益改为从日志读取 | 已完整同步 | 中 | 未预判 |
| `a0fe1e8d` | DailyTrifles | feat(DailyTrifles): 新增每日收益查询接口 | 已完整同步 | 大 | 未预判 |
| `f3c61ba4` | DailyTrifles | feat(DailyTrifles): 收益快照另存日汇总，突破日志 7 天限制 | 已完整同步 | 中 | 未预判 |
| `e6b00fbe` | DailyTrifles | feat(DailyTrifles): 收益支持历史查询与按天删除 | 已完整同步 | 中 | 未预判 |
| `83377a19` | DailyTrifles | fix(DailyTrifles): 修复统计每日收益缺少分组常量导致的 NameError | 已完整同步 | 小 | 未预判 |
| `ad778fba` | DailyTrifles | fix(DailyTrifles): Improve store sign navigation and mall detection | 已完整同步 | 中 | 1 文件 |

> 其余 136 条见 §3.1 逐条明细。


## 6. 三类差异清单

### 6.1 完全缺失（本地无对应模块）

| 模块 | 提交数 | 代表提交 | 建议 |
| --- | ---: | --- | --- |
| DraftDuel | 37 | `287d59f0`、`1012030e`、`65a3ebfb`、`c78b436f`、`fe1c0881` | 单独评估 |
| BorrowShikigami | 3 | `3a8ba22f`、`fc45a500`、`628c0cfb` | 单独评估 |
| TrueOrochi | 2 | `aaede1db`、`f7db71b2` | 不引入 |
| AutoStory | 2 | `80751206`、`547dfba6` | 不引入 |
| module/scrolls | 2 | `95b75dd8`、`92ada2c7` | 谨慎评估 |

### 6.2 部分实现（本地模块存在但有差异）

| 模块 | 提交数 | 其中 P0/P1 | 代表缺口 |
| --- | ---: | ---: | --- |
| Component | 39 | 19 | feat(GeneralBattle): Add prepare/preset/；feat(GeneralBattle): Add completion fall |
| MetaDemon | 24 | 7 | fix(MetaDemon): 适配新版超鬼王“祸至无日/祸主降临”活动界面；fix(MetaDemon): harden new-UI flow again |
| Chess | 18 | 5 | 优化(百鬼棋局)：匹配竞态保护与阵容核对及周目标调度；Revert "新增(百鬼棋局)：仅MUMU-2启用测试状态决策流程" |
| WantedQuests | 18 | 11 | feat(WantedQuests): 适配部分秘闻奖励结算后的一次性对话；fix(WantedQuests)：悬赏卡位小字叠背景导致 OCR 漏识时不重试 |
| module/server | 18 | 0 | fix(Server): 画面截图改用 adb 直抓，不再干扰运行中的任务；feat(core)：引入 RuleFrame 识别与灰度匹配，支持网络异常恢复 |
| ActivityShikigami | 14 | 5 | 适配(式神活动)：按本期Boss入口更新页面与识别资源；调整(式神活动探索)：取消滑动与模式筛选并统一奖励处理 |
| FrogBoss | 11 | 8 | feat(FrogBoss): 适配十周年素材并新增非等权预测策略 frog_o；修复(对弈竞猜)：通过可见记录页补结算并启用胜率权重 |
| 根目录 | 10 | 0 | 优化(重启)：支持配置异常重启容忍次数并优先执行恢复；fix(Deploy): 默认仓库指向本仓库 mine 分支 |
| Exploration | 10 | 8 | fix(Exploration): Restore I_FLAG_2_ON RO；fix(Exploration): 修复特定UP类型找怪提前退出及滑屏边缘检测问 |
| 文档/CI | 10 | 0 | chore(workflow): Update automation workf；chore(workflow): Upgrade GitHub Agentic  |
| GameUi | 9 | 6 | 调整(通用页面)：统一奖励识别并注册误触页面与结算策略；fix(GameUi): 下调庭院标志识别阈值，修复游戏更新后登录卡死 |
| module/device | 9 | 0 | feat(DesktopClient): 设备层接入桌面模式（免 adb、无模拟；feat(DesktopClient): Device 层桌面生命周期（Desk |
| GlobalGame | 8 | 4 | fix(GlobalGame): 通用确认按钮兼容新旧两套UI；fix(GlobalGame): 重截获得奖励素材并调整ROI |
| Restart | 6 | 4 | 修复(登录)：调整进入游戏文字识别区域与关键词；fix(Restart): 调整登录界面「进入游戏」OCR 识别区域 |
| module/image | 6 | 2 | feat(Image): 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差；feat(Image): 模板匹配新增 roi_pad 容差，吸收桌面渲染相位差 |
| Duel | 5 | 3 | 优化(斗技)：匹配超时竞态保护与周目标调度；修复(斗技)：达到名士星数目标后延至下周一运行 |
| AbyssShadows | 4 | 3 | 修复(狭间)：切换御魂前关闭残留分布弹窗；优化(狭间)：跳过重复御魂装配并识别已击破目标 |
| DemonEncounter | 4 | 3 | fix(DemonEncounter): 优化boss搜索容错并处理中央宝箱遮挡；修复(逢魔之时)：确认弹窗关闭与首领识别并限制三轮召集尝试 |
| SixRealms | 4 | 3 | fix(SixRealms): 限制选岛连续点击并增加超时退出；fix(SixRealms): 修复月之海岛屿漏识别和点击偏移 |
| MetaDemonTicket | 4 | 2 | feat(MetaDemonTicket): 探索模式支持选择章节；fix(MetaDemonTicket): 门票计数越界时按识别错误处理 |
| RichMan | 3 | 2 | fix(RichMan): Handle bulk purchase failu；fix(weekly_purchase)：修复皮肤券未购买 |
| module/atom | 2 | 0 | 重构(点击规则)：统一图像与OCR点击并支持Scatter密度模型；移植 nearaura/OnmyojiAutoScript 修复包 (4 项) |
| Delegation | 2 | 1 | 修正(式神委派)：收窄完成状态OCR识别区域；修复(委派)：补充领奖对话验证并更新出战识别资源 |
| module/config | 2 | 0 | feat(Config): 桌面模式配置项与界面说明；fix(scheduler): 调度白名单补上超鬼王门票任务 |
| BondlingFairyland | 2 | 2 | fix(bondling)：删除漏邀分支，队员退回主界面即判房间销毁；fix(bondling)：调整建房逻辑，调整补邀时间间隔 |

### 6.3 已完整同步

共 **176** 条：其中 patch-id 精确命中 54 条，其余为台账记录的「已合入 / 已覆盖」等价实现。

| 模块 | 已同步条数 |
| --- | ---: |
| Component | 21 |
| GameUi | 14 |
| FrogBoss | 10 |
| Exploration | 9 |
| MetaDemon | 9 |
| DailyTrifles | 7 |
| Chess | 6 |
| DemonEncounter | 6 |
| Dokan | 6 |
| GlobalGame | 5 |
| WantedQuests | 5 |
| module/device | 5 |
| WeeklyTrifles | 4 |
| module/gui | 4 |
| LBS | 4 |
| module/image | 4 |
| module/server | 4 |
| Delegation | 4 |
| EvoZone | 4 |
| BondlingFairyland | 3 |
| base_task.py | 3 |
| Duel | 3 |
| HeroTest | 2 |
| module/config | 2 |
| Restart | 2 |
| RichMan | 2 |
| EternitySea | 2 |
| IbukiArena | 2 |
| OtherWorldTwilight | 2 |
| 根目录 | 2 |
| MysteryShop | 2 |
| TalismanPass | 2 |
| KekkaiActivation | 2 |
| DraftDuel | 2 |
| GuildActivityMonitor | 1 |
| AutoCheckinBigGod | 1 |
| Orochi | 1 |
| FrogChallenge | 1 |
| MemoryScrolls | 1 |
| 文档/CI | 1 |
| Script | 1 |
| AbyssShadows | 1 |
| module/atom | 1 |
| FindJade | 1 |
| MetaDemonTicket | 1 |
| CollectiveMissions | 1 |

## 7. 风险与建议

| # | 风险/建议 | 说明 |
| --- | --- | --- |
| 1 | 结构性分叉，冲突率高 | 本地独有 flow/超鬼王/Chess/RichMan，上游补丁大量落在 `tasks/Component`、`tasks/GameUi`、`module/*`，直接 cherry-pick 预计冲突 |
| 2 | 新功能缺口需单独立项 | DraftDuel（协同对弈）、起号套件（AutoStory/BorrowShikigami）体量大、依赖双端协同，不宜混入小批次 |
| 3 | 活动类任务卡实机窗口 | LBS/IbukiArena/FrogChallenge/B1/B2 均需活动开放才能验收，当前只能标「待实机」 |
| 4 | 上游 Android/OASA 分叉 | lgg686 自 11 月起转向 APK/热更新/OASA 设备后端，本地桌面链路不适用，应持续判定为不引入 |
| 5 | 台账为唯一权威 | patch-id 因冲突取舍而漂移，工具 `applied` 不可靠，必须以 `upstream_sync_log.md` 为准 |
| 6 | 精度优先 | 上游以启发式替代本地精确计数的改动不采纳；资产/ROI 改动需实机读数校准后落地 |

## 8. 方法与复现

```powershell
$env:PYTHONIOENCODING="utf-8"
python dev_tools/upstream_sync.py --since "2026-09-18" fetch
python dev_tools/upstream_sync.py --since "2026-09-18" advise --json --out advise.json
```

`patch-id` 去重与本地比对脚本为临时分析脚本（不入库），判定规则见本文 §1 与 §8。所有结论以 `czr` 为基线，不含 `staging/20261122-chess-sync` 未合并改动。

## 9. 更新记录

| 日期 | 版本 | 变更 | 来源 |
| --- | --- | --- | --- |
| 2026-11-22 | v1 | 首次建立 9-18 起全量基线：483 条独立变更 + 99 条合并提交，三分类与 P0~P4 建议 | 只读分析，无代码改动 |
| 2026-11-22 | v2 | P0 逐条复核：11 条全部有结论（4 条本地已覆盖标已处理，7 条不适用标不引入），P0 剩余 0；69c93a44 关联的 f67e5a80 结束标志加固落在 `staging/20261122-p0-frog`（7aa7e23d，待实机） | 本地代码核对 |

> 维护规则：每次 `fetch` / 同步 / 判定后原地增删改本文件，并同步 HTML；状态变化只改对应行，不删除历史条目，保证可追溯。
