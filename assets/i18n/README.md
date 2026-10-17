# OASX 附加翻译

`zh-CN.json` 通过后端 `/home/additional_translate` 接口提供给 OASX。
菜单、配置组和参数字段按原始键名精确匹配；OASX 参数标签使用 `name`，不使用 Pydantic 的 `title`。
因此在配置模型中写入中文 `title` 不能替代这里的翻译。

2026-10-16 核查修正：标题以主要参考 YYS 仓库的
`6bff084c630e884a0a30a9f870892f6bb430e2fe` 提交为主。
YYS 的词库不在 `i18n/` 目录，而是
[`module/zh-CN.json`](https://gitee.com/pattering-rain/yys/blob/6bff084c630e884a0a30a9f870892f6bb430e2fe/module/zh-CN.json)
和 [`module/zh-CN-Web.json`](https://gitee.com/pattering-rain/yys/blob/6bff084c630e884a0a30a9f870892f6bb430e2fe/module/zh-CN-Web.json)。
两份文件分别含 277 和 824 个词条。YYS 的 `module/server/home_router.py`
还会收集配置标题，其优先级为：显式配置标题 > `zh-CN.json` > `zh-CN-Web.json`。
本项目按该顺序静态核对当前可见标题，只读取 Git 指定提交，不执行参考源码。

本次修正 83 个标题，包含彼世逢魔、绘卷捐赠、活动爬塔、福利寮战斗/切魂配置等。
共享字段 `enable`、`fresh_num`、`check_money` 在 YYS 不同配置中有不同标题；OASX 使用扁平词库，
暂保留适用各处的通用标题，不根据源码文件遍历顺序任意覆盖。
其中 `enable` 固定为“启用”，不能被道馆的“启用QQ群消息检查”等专用标题覆盖；覆盖检查对此单独校验。
YYS 中 `team_flow`、`broker` 等原样英文占位不覆盖本项目已有中文。
本项目独有字段及本地行为的帮助说明继续保留。

此前通用词条选自公开
[runhey/OASX 中文词库](https://github.com/runhey/OASX/blob/master/lib/config/translation/i18n_cn.dart)
及其 [键名定义](https://github.com/runhey/OASX/blob/master/lib/config/translation/i18n_content.dart)，
保留原作者署名与 [GPL-3.0 许可](https://github.com/runhey/OASX/blob/master/LICENSE)。
YYS 未提供的词条继续以公开 OASX 词库、本项目配置和注释补充。
仅同步当前界面使用的词条，不从其他本地项目导入翻译，也不恢复已移除任务的专属入口。

新增任务、配置组或字段后运行：

```powershell
.venv\Scripts\python.exe dev_tools/check_i18n.py
```

检查不依赖前端内置词库或联网，不启动设备或游戏任务。公开词库原有的空帮助文本保留为空；可见标题必须有非空翻译。
OASX 在导航初始化时加载附加词库；修改后退出并重新打开 OASX，让前端重新加载。
`module/config/i18n/` 的 Qt XML/QM 属于旧界面，不用于 OASX。
