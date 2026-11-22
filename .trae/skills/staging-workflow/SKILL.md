---
name: "staging-workflow"
description: "项目开工与批次闸门：新会话开始、开工、开始一个新批次、继续上次工作、把 czr 同步/合并进当前 staging 分支、查看有哪些未完成批次、合并闸门与台账登记、收尾回写立项。Invoke at the start of any work session on this repo, or when the user says 开工 / 继续 / 新批次 / 同步 czr / 合批 / 收尾。"
---

# 项目开工与批次闸门（staging-workflow）

> 这是**操作入口**，不是规则副本。规则唯一来源：`dev_tools/projects/2026-11-upstream-gap/README.md` §10（R1~R15）。
> 详细的上游同步工具用法见 `upstream-sync` 技能。

## 何时使用

- 任何一次新会话开工、换机器接手、继续上次未完成的批次
- 用户说「开工」「继续」「开一个新批次」「同步 czr」「合批」「收尾」
- 不确定当前有哪些未完成批次，或分支落后 czr 多少

## 第一步（必做）

```powershell
python dev_tools/session_start.py
```

输出约 30 行，代替通读 README / SKILL / 台账：

1. 未完成批次（`dev_tools/staging_pending.md` §2）与最近同步批次；
2. 当前分支是 `staging/*` 时自动 `git merge czr`（冲突自动 abort；工作区脏只报告不合并）；
3. 规则与总账的索引路径。

只要简报不改工作区加 `--check`；工作区有未提交改动时先让用户决定提交或 stash，再重跑。

## 三条硬约束

| 约束 | 内容 |
| --- | --- |
| 只在 staging 改 | 改动进 `staging/YYYYMMDD-主题`，从 `czr` 最新提交拉出；`czr` 验收前保持干净 |
| 合并闸门 | 自动化全绿 + 实机通过 + 用户明确确认，三者齐备才 `git merge --no-ff`；任缺其一停在「待测试 / 待合并」并等确认 |
| 三处同步 | 代码 / `dev_tools/upstream_sync_log.md` / 立项（README、backlog、总账）保持一致 |

批次状态机：`进行中 → 待测试 → 待合并 → 已合并 / 已废弃`；建批在 §2 登记，合并或废弃后迁到 §3。

## 按需读取（不要每次全读）

| 需要什么 | 读哪里 |
| --- | --- |
| 规则细则 R1~R15 | `dev_tools/projects/2026-11-upstream-gap/README.md` §10 |
| 上游差异总账（活文档） | `dev_tools/projects/2026-11-upstream-gap/upstream-full-compare-20261122/` |
| 待办与优先级 | `dev_tools/projects/2026-11-upstream-gap/backlog.md` |
| 上游同步命令与取舍规则 | `upstream-sync` 技能 + `dev_tools/upstream_sync_doc.md` |

## 收尾定义

合并 → 推送（`git push https://github.com:443/ZH-CZR/OnmyojiAutoScript.git czr`）→ 台账 → 立项，四步做完才算一批结束。
