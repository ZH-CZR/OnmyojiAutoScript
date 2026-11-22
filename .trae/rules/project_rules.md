# 项目开工规则（精简版）

> 这里是**操作入口**，不是规则副本。规则权威来源：`dev_tools/projects/2026-11-upstream-gap/README.md` §10（R1~R15）。
> 改动规则时只改 README §10 与 `.trae/skills/upstream-sync/SKILL.md`，本文件只同步「入口命令」与「三条硬约束」。

## 开工第一步

```powershell
python dev_tools/session_start.py
```

一次调用完成三件事，替代通读 README / SKILL / 台账：

1. 打印未完成批次（`staging_pending.md` §2）与最近同步批次；
2. 当前分支是 `staging/*` 时，自动把 `czr` 合并进来（冲突自动回滚）；
3. 打印规则和总账的索引路径，需要细则时再定向读取。

工作区有未提交改动时脚本只报告不合并；只想要简报、不改工作区时加 `--check`。

在 Trae 里直接说「开工 / 继续 / 新批次 / 收尾」，会命中项目技能 `.trae/skills/staging-workflow`，效果与上面的命令相同。

## 三条硬约束

| 约束 | 内容 |
| --- | --- |
| 只在 staging 改 | 改动进 `staging/YYYYMMDD-主题`，`czr` 验收前保持干净 |
| 合并闸门 | 自动化全绿 + 实机通过 + 用户明确确认，三者齐备才 `git merge --no-ff`；否则停下等确认 |
| 三处同步 | 代码 / `upstream_sync_log.md` / 立项（README、backlog、总账）保持一致 |

## 按需读取

| 需要什么 | 读哪里 |
| --- | --- |
| 规则细则（R1~R15） | 立项 README §10 |
| 上游差异总账 | `dev_tools/projects/2026-11-upstream-gap/upstream-full-compare-20261122/` |
| 待办与优先级 | `dev_tools/projects/2026-11-upstream-gap/backlog.md` |
| 同步工具与命令 | `.trae/skills/upstream-sync/SKILL.md` |
