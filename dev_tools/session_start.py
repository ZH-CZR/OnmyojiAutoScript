"""开工简报 + 自动把 czr 合并进当前 staging 分支。

用法（仓库根目录）：
    python dev_tools/session_start.py           # 打印简报，并把 czr 自动合并进当前 staging 分支
    python dev_tools/session_start.py --check   # 只打印简报与落后数量，不改工作区

行为：
- 当前分支是 staging/* 且落后 czr 时自动 `git merge czr`；冲突则自动 abort 并报告。
- 工作区有未提交的已跟踪改动时**不合并**，只提示，避免把半成品卷进合并提交。
- 输出控制在 30 行左右，替代“每次通读 README / SKILL / 台账”。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_LOG = ROOT / "dev_tools" / "staging_pending.md"
SYNC_LOG = ROOT / "dev_tools" / "upstream_sync_log.md"
MASTER_LEDGER = (
    ROOT
    / "dev_tools"
    / "projects"
    / "2026-11-upstream-gap"
    / "upstream-full-compare-20261122"
    / "upstream-full-compare-20261122.md"
)
RULE_DOC = ROOT / "dev_tools" / "projects" / "2026-11-upstream-gap" / "README.md"

OPEN_STATES = ("进行中", "待测试", "待合并")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def out(text: str = "") -> None:
    print(text)


def section_lines(path: Path, start: str, end: str | None = None) -> list[str]:
    """取出 markdown 两个标题之间的行；文件缺失时返回空列表。"""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    collected: list[str] = []
    inside = False
    for line in lines:
        if line.startswith(start):
            inside = True
            continue
        if inside and end and line.startswith(end):
            break
        if inside:
            collected.append(line)
    return collected


def table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= set("|- "):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append(cells)
    return rows


def clip(text: str, width: int = 56) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def current_branch() -> str:
    proc = git("rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip() or "(detached)"


def divergence(branch: str) -> tuple[int, int]:
    """返回 (领先 czr 的提交数, 落后 czr 的提交数)。"""
    ahead = git("rev-list", "--count", f"czr..{branch}")
    behind = git("rev-list", "--count", f"{branch}..czr")
    try:
        return int(ahead.stdout.strip()), int(behind.stdout.strip())
    except ValueError:
        return 0, 0


def tracked_changes() -> list[str]:
    proc = git("status", "--porcelain")
    return [line for line in proc.stdout.splitlines() if line.strip() and not line.startswith("??")]


def merge_in_progress() -> bool:
    return git("rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0


def sync_with_czr(branch: str, check_only: bool) -> None:
    ahead, behind = divergence(branch)
    out(f"分支        {branch}（相对 czr：领先 {ahead} / 落后 {behind}）")

    if not branch.startswith("staging/"):
        out("同步       跳过：当前不在 staging/ 分支")
        return
    if behind == 0:
        out("同步       已是最新，无需合并 czr")
        return
    if merge_in_progress():
        out("同步       跳过：存在未完成的 merge，请先解决或 git merge --abort")
        return
    dirty = tracked_changes()
    if dirty:
        out(f"同步       跳过：工作区有 {len(dirty)} 个未提交改动，先提交或 stash 后重跑")
        for line in dirty[:5]:
            out(f"           {clip(line, 60)}")
        return
    if check_only:
        out(f"同步       落后 {behind} 个提交（--check 模式未合并）")
        return

    out(f"同步       正在合并 czr → {branch} ...")
    proc = git("merge", "czr", "--no-edit", "-m", f"chore(staging): 自动同步 czr 到 {branch}")
    if proc.returncode != 0:
        git("merge", "--abort")
        out("同步       冲突，已回滚到合并前。请手动 git merge czr 处理冲突")
        for line in proc.stdout.splitlines()[-6:]:
            out(f"           {clip(line, 60)}")
        return
    _, remaining = divergence(branch)
    out("同步       完成" if remaining == 0 else f"同步       完成，但仍落后 {remaining} 个提交")


def print_brief() -> None:
    out("\n未完成批次（staging_pending §2）")
    rows = table_rows(section_lines(STAGING_LOG, "## §2", "## §3"))
    pending = [row for row in rows if len(row) >= 7 and any(state in row[-1] for state in OPEN_STATES)]
    if not pending:
        out("  （无）")
    for row in pending:
        out(f"  {row[0]}  {row[-1]}  {row[1]}")
        out(f"    范围：{clip(row[3])}")

    out("\n最近同步批次（upstream_sync_log §1）")
    rows = table_rows(section_lines(SYNC_LOG, "## §1", "## §2"))
    data_rows = [row for row in rows if len(row) >= 6 and row[0].isdigit()]
    if not data_rows:
        out("  （无）")
    for row in data_rows[:1]:
        out(f"  批次 {row[0]}  {row[1]}  {row[3]}  {row[4]}")
        out(f"  主题：{clip(row[5], 72)}")

    out("\n索引（按需读取，不必每次通读）")
    out(f"  规则细则   {RULE_DOC.relative_to(ROOT)} §10（R1~R15）")
    out(f"  上游总账   {MASTER_LEDGER.relative_to(ROOT)}（R15 活文档）")
    out(f"  待办清单   dev_tools/projects/2026-11-upstream-gap/backlog.md")
    out("  硬约束     改动只进 staging/*；自动化全绿 + 实机通过 + 用户确认才合 czr")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="开工简报 + 自动把 czr 合并进当前 staging 分支")
    parser.add_argument("--check", action="store_true", help="只报告，不执行合并")
    args = parser.parse_args()

    if git("rev-parse", "--git-dir").returncode != 0:
        out("当前目录不是 git 仓库")
        return 1

    branch = current_branch()
    out(f"czr        {git('rev-parse', '--short', 'czr').stdout.strip()}")
    sync_with_czr(branch, args.check)
    print_brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
