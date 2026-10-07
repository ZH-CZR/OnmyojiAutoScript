# This Python file uses the following encoding: utf-8
"""上游提交同步工具

按需从 runhey/OnmyojiAutoScript 的 dev 分支挑选提交，同步到本地 czr 分支。
（czr 是开发/暂存分支；测试一段时间无误后，再自行把 czr 合并到 mine。）

标准流程：
  1. python dev_tools/upstream_sync.py fetch
       配置 upstream remote 并拉取上游 dev 分支
  2. python dev_tools/upstream_sync.py list
       生成待选清单 dev_tools/upstream_manifest.md
       （默认只对比最近两个月，已过滤内容已在本地的提交；可用 --since 调整）
  3. 手工编辑清单，把要同步的提交从 [ ] 勾成 [x]
  4. python dev_tools/upstream_sync.py apply
       新建 sync 分支并 cherry-pick 所选提交；遇到冲突会中止并给出手工处理方案
  5. 测试无误后合并回 czr：
       git switch czr && git merge --no-ff <sync 分支>

说明：本地 czr / mine 相对上游已高度定制，凡涉及共享基础设施文件（i18n、config 等）
的提交大概率与本地改动冲突，清单里以 ⚠ 标注，建议优先挑选 isolated 的提交。
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
from collections import Counter
from datetime import datetime

UPSTREAM_REMOTE = "upstream"
UPSTREAM_URL = "https://github.com/runhey/OnmyojiAutoScript.git"
UPSTREAM_BRANCH = "dev"
SOURCE_REMOTE = "syncsrc"  # 自定义数据源（--remote-url）专用的 remote 名，避免与默认 upstream 混淆
DEFAULT_BASE = "czr"
DEFAULT_MANIFEST = os.path.join("dev_tools", "upstream_manifest.md")
DEFAULT_IGNORED = os.path.join("dev_tools", "upstream_ignored.json")  # 已跳过提交的持久化，不入库
DEFAULT_SINCE = "2 months ago"  # 默认只对比最近两个月的提交
DEP_CAP = 30  # --deps 模式下自动附带提交的数量上限
MAX_DEP_ROUNDS = 2  # --deps 模式下冲突回溯前置提交的最大轮数

# 提交前缀 -> 归类。用于清单里标注类型
TYPE_MAP = {
    "feat": "feat", "feature": "feat",
    "fix": "fix", "hotfix": "fix", "bugfix": "fix",
    "refactor": "refactor", "perf": "perf", "optimize": "refactor",
    "chore": "chore", "docs": "docs", "doc": "docs",
    "style": "style", "test": "test", "build": "build", "ci": "ci",
    "revert": "revert",
    "add": "feat", "update": "feat", "handle": "fix",
}
# 中文提交前缀
TYPE_MAP_ZH = [
    ("修复", "fix"), ("新增", "feat"), ("添加", "feat"), ("优化", "refactor"),
    ("调整", "refactor"), ("更新", "feat"), ("重构", "refactor"), ("适配", "fix"),
]
TYPE_ORDER = ["feat", "fix", "refactor", "perf", "chore", "docs", "style",
              "test", "build", "ci", "revert", "other"]

# 共享基础设施文件：被大量提交改动，本地通常已定制，冲突风险高
SHARED_PREFIXES = ("assets/i18n/", "module/config/", "config/")
SHARED_FILES = {
    "module/config/config_manual.py",
    "module/config/config_menu.py",
    "gui.py", "script.py", "server.py",
}

# 框架/公共设施：改动这类文件会波及全局，本地定制多，取舍需谨慎
FRAMEWORK_PREFIXES = ("module/", "assets/i18n/")
FRAMEWORK_FILES = {"gui.py", "script.py", "server.py"}

# 改动规模的判断阈值（文件数, 增删总行数）
SIZE_SMALL = (3, 60)
SIZE_MEDIUM = (10, 300)
MULTI_REVIEW_CHURN = 150  # 横跨多个模块且增删超过此值才升级为「建议单独评估」

# 本地在「上游提交所涉及文件」上的改动量阈值（行）：改动越多，越可能覆盖本地定制
LOCAL_CHURN_MEDIUM = 80
LOCAL_CHURN_HIGH = 300

# 取舍等级排序与中文结论（advise 用；与 judge() 的结论文案保持一致）
LEVEL_RANK = {"adopt": 0, "caution": 1, "review": 2}
LEVEL_TEXT = {"adopt": "✓ 建议采用", "caution": "⚠ 采用但需实测",
              "review": "🛑 建议单独评估"}

MAX_PATCH_CHARS = 200000  # show 子命令返回的 diff 上限，超出截断


def git(args, check=True):
    """执行 git 命令，返回 (returncode, stdout, stderr)"""
    proc = subprocess.run(
        ["git", *args],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    if check and proc.returncode != 0:
        print(f"[git] 命令失败: git {' '.join(args)}", file=sys.stderr)
        print(proc.stderr.strip(), file=sys.stderr)
        sys.exit(proc.returncode)
    return proc.returncode, proc.stdout, proc.stderr


def git_out(args):
    return git(args)[1]


JSON_MARK = "@@SYNC@@"  # 机器可读行前缀，供界面解析最后一个 JSON 结果


def emit(obj):
    """输出一行带标记的 JSON，供界面解析（放在最后一行）"""
    print(JSON_MARK + json.dumps(obj, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 提交信息解析
# ---------------------------------------------------------------------------
def classify_type(subject):
    m = re.match(r"^([A-Za-z]+)", subject)
    if m:
        return TYPE_MAP.get(m.group(1).lower(), "other")
    for zh, t in TYPE_MAP_ZH:
        if subject.startswith(zh):
            return t
    return "other"


def parse_scope(subject):
    """取 conventional commit 里的 scope，如 feat(AreaBoss): / fix[hunt]:"""
    m = re.match(r"^[A-Za-z]+[\(\[（]([^\)\]）]+)[\)\]）]", subject)
    return m.group(1).strip() if m else ""


def module_of(commit):
    """确定提交归属的模块：优先用 scope，否则取改动文件里出现最多的模块目录"""
    scope = parse_scope(commit["subject"])
    if scope:
        return scope
    votes = Counter()
    for f in commit["files"]:
        parts = f.replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[0] in ("tasks", "module"):
            votes[parts[1]] += 1
        elif parts and parts[0]:
            votes[parts[0]] += 1
    if votes:
        return votes.most_common(1)[0][0]
    return "其他"


def risk_of(files):
    """评估 cherry-pick 冲突风险：触及共享基础设施文件的风险最高"""
    norm = [f.replace("\\", "/") for f in files]
    if any(f.startswith(SHARED_PREFIXES) or f in SHARED_FILES for f in norm):
        return "shared"
    roots = set()
    for f in norm:
        parts = f.split("/")
        if len(parts) >= 2 and parts[0] in ("tasks", "module"):
            roots.add("/".join(parts[:2]))
        elif parts and parts[0]:
            roots.add(parts[0])
    return "isolated" if len(roots) == 1 else "multi"


def framework_hit(files):
    """提交是否触及框架/公共设施（module 核心、入口脚本或语言包）"""
    for f in files:
        n = f.replace("\\", "/")
        if n in FRAMEWORK_FILES or n.startswith(FRAMEWORK_PREFIXES):
            return True
    return False


def touched_roots(files):
    """提交涉及的顶层范围；tasks/XX、module/XX 归并为同一 XX"""
    roots = set()
    for f in files:
        parts = f.replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[0] in ("tasks", "module"):
            roots.add(f"{parts[0]}/{parts[1]}")
        elif parts and parts[0]:
            roots.add(parts[0])
    return roots


def size_of(changed, churn):
    """按文件数与增删总行数粗分改动规模"""
    if changed <= SIZE_SMALL[0] and churn <= SIZE_SMALL[1]:
        return "small"
    if changed <= SIZE_MEDIUM[0] and churn <= SIZE_MEDIUM[1]:
        return "medium"
    return "large"


def judge(commit):
    """把规模 + 范围 + 风险合成一句中文取舍建议，返回 (等级, 结论, 理由列表)"""
    files = commit["files"]
    roots = touched_roots(files)
    changed, churn = commit["changed"], commit["adds"] + commit["dels"]
    reasons, level = [], "adopt"
    if framework_hit(files):
        level = "caution"
        reasons.append("触及框架/公共文件（module、入口脚本或语言包），"
                       "本地定制较多，合并后需实测。")
    if commit["size"] == "large":
        level = "review"
        reasons.append(f"改动很大（{changed} 个文件、+{commit['adds']}/-{commit['dels']} 行），"
                       "可能是功能重写或框架调整，建议单独评估，不要盲目 cherry-pick。")
    elif commit["size"] == "medium":
        if level == "adopt":
            level = "caution"
        reasons.append(f"中等改动（{changed} 个文件、+{commit['adds']}/-{commit['dels']} 行），"
                       "建议合并后测试。")
    if len(roots) >= 3:
        if churn >= MULTI_REVIEW_CHURN:
            level = "review"
        elif level == "adopt":
            level = "caution"
        reasons.append(f"横跨 {len(roots)} 个模块/目录，影响面较大，合并后建议抽查。")
    if level == "adopt":
        reasons.append(f"改动集中（{changed} 个文件、+{commit['adds']}/-{commit['dels']} 行），"
                       "范围独立，通常可直接采用。")
    text = {"adopt": "✓ 建议采用",
            "caution": "⚠ 采用但需实测",
            "review": "🛑 建议单独评估"}[level]
    return level, text, reasons


def _numstat_path(path):
    """归一化 --numstat 的重命名路径，取新路径（去掉 {old => new} 形式）"""
    if "=>" not in path:
        return path
    path = re.sub(r"\{[^{}]*?=>\s*([^{}]*?)\}", r"\1", path)
    path = re.sub(r"^.*?=>\s*", "", path)
    return path.strip()


def already_applied(base, ref):
    """用 patch-id 等价性找出本地已包含（但 hash 不同，多为合并 PR 带入）的提交"""
    _, out, _ = git(["cherry", base, ref], check=False)
    applied = set()
    for line in out.splitlines():
        if line.startswith("- "):
            applied.add(line[2:].strip())
    return applied


# ---------------------------------------------------------------------------
# 已跳过（ignored）持久化
# ---------------------------------------------------------------------------
def load_ignored(path=None):
    """读取已跳过清单；文件缺失或损坏时返回空列表（容错）"""
    path = path or DEFAULT_IGNORED
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    items = data.get("items") if isinstance(data, dict) else data
    return items if isinstance(items, list) else []


def save_ignored(items, path=None):
    path = path or DEFAULT_IGNORED
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "items": items}, f, ensure_ascii=False, indent=2)


def ignored_hashes(path=None):
    """已跳过提交的完整 hash 集合（供 list / advise / apply 过滤复用）"""
    return {it["hash"] for it in load_ignored(path) if it.get("hash")}


def match_ignored(items, prefix):
    """按 hash 前缀（至少 8 位）匹配已跳过项，返回命中的项列表"""
    p = (prefix or "").strip().lower()
    if len(p) < 8:
        return []
    return [it for it in items if (it.get("hash") or "").lower().startswith(p)]


def parse_hashes(raw):
    """解析逗号分隔的 hash 参数为小写列表"""
    return [h.strip().lower() for h in (raw or "").split(",") if h.strip()]


def merge_tree_conflict_files(out):
    """解析 `git merge-tree --write-tree --name-only` 输出中的冲突文件列表

    首行是生成的 tree OID（无冲突时输出为空，返回空列表），其后到空行为冲突文件。
    """
    files = []
    for i, line in enumerate((out or "").splitlines()):
        if i == 0:
            continue
        if not line.strip():
            break
        files.append(line.strip())
    return files


def precheck_commit(commit_hash, base):
    """用 merge-tree 模拟对该提交的 cherry-pick，预判是否冲突（不改动工作区）"""
    proc = subprocess.run(
        ["git", "merge-tree", "--write-tree", "--name-only",
         f"--merge-base={commit_hash}^", base, commit_hash],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode == 0:
        return {"status": "ok", "files": []}
    if proc.returncode == 1:
        return {"status": "conflict", "files": merge_tree_conflict_files(proc.stdout)}
    return {"status": "error", "files": []}


def local_churn(base, ref):
    """统计本地 base 相对「与 ref 的共同祖先」在每个文件上的改动行数。

    返回 {路径: 改动行数}。数值越大说明本地对该文件的定制越多，
    上游提交触及它时越可能与本地改动冲突、或覆盖本地定制。
    """
    code, out, _ = git(["merge-base", base, ref], check=False)
    if code != 0 or not out.strip():
        return {}
    _, out, _ = git(["diff", "--numstat", f"{out.strip()}..{base}"], check=False)
    churn = {}
    for line in out.splitlines():
        cols = line.split("\t")
        if len(cols) < 3:
            continue
        adds = int(cols[0]) if cols[0].isdigit() else 0
        dels = int(cols[1]) if cols[1].isdigit() else 0
        churn[_numstat_path(cols[2])] = adds + dels
    return churn


def churn_level(lines):
    """按本地改动行数粗分定制程度 low/medium/high"""
    if lines >= LOCAL_CHURN_HIGH:
        return "high"
    if lines >= LOCAL_CHURN_MEDIUM:
        return "medium"
    return "low"


def collect_commits(base, ref, since=None, exclude_applied=True):
    """收集 base..ref 范围内、排除 merge 的提交（按时间从旧到新）

    用 --numstat 一次性拿到每个提交的改动文件与增删行数，据此评估规模与取舍建议。
    """
    fmt = "\x1e%H\x1f%ad\x1f%an\x1f%s"
    args = ["-c", "core.quotepath=false", "log", "--no-merges", "--reverse",
            "--date=short", f"--pretty=format:{fmt}", "--numstat"]
    if since:
        args.append(f"--since={since}")
    args.append(f"{base}..{ref}")
    out = git_out(args)
    commits = []
    for chunk in out.split("\x1e"):
        lines = chunk.strip("\n").split("\n")
        if not lines or not lines[0].strip():
            continue
        parts = lines[0].split("\x1f")
        if len(parts) < 4:
            continue
        adds = dels = 0
        files = []
        for ln in lines[1:]:
            ln = ln.strip()
            cols = ln.split("\t")
            if len(cols) < 3:
                continue
            files.append(_numstat_path(cols[2]))
            if cols[0].isdigit():
                adds += int(cols[0])
            if cols[1].isdigit():
                dels += int(cols[1])
        commits.append({
            "hash": parts[0],
            "date": parts[1],
            "author": parts[2],
            "subject": "\x1f".join(parts[3:]),
            "files": files,
            "adds": adds,
            "dels": dels,
            "changed": len(files),
        })

    if exclude_applied:
        applied = already_applied(base, ref)
        commits = [c for c in commits if c["hash"] not in applied]

    for c in commits:
        c["type"] = classify_type(c["subject"])
        c["module"] = module_of(c)
        c["risk"] = risk_of(c["files"])
        c["size"] = size_of(c["changed"], c["adds"] + c["dels"])
        c["framework"] = framework_hit(c["files"])
        c["level"], c["judge"], c["reasons"] = judge(c)
    return commits


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------
def remote_url_of(name):
    """返回已配置 remote 的 URL；不存在返回 None"""
    code, out, _ = git(["remote", "get-url", name], check=False)
    return out.strip() if code == 0 and out.strip() else None


def ensure_source(remote, url):
    """确保自定义数据源 remote 存在且指向给定 URL（只改 remote 配置，不动其它 git config）"""
    cur = remote_url_of(remote)
    if cur is None:
        print(f"[setup] 添加数据源 remote: {remote} -> {url}")
        git(["remote", "add", remote, url])
    elif cur != url:
        print(f"[setup] 数据源 remote {remote} 改指向: {url}")
        git(["remote", "set-url", remote, url])
    else:
        print(f"[setup] 数据源 remote {remote} 已存在，跳过")


def ensure_upstream():
    _, out, _ = git(["remote"], check=False)
    if UPSTREAM_REMOTE not in out.split():
        print(f"[setup] 添加 upstream remote: {UPSTREAM_URL}")
        git(["remote", "add", UPSTREAM_REMOTE, UPSTREAM_URL])
    else:
        print("[setup] upstream remote 已存在，跳过")


def resolve_source(args):
    """解析数据源，返回 (remote, branch, ref)。

    未指定 --remote-url 时沿用默认 upstream/dev（向后兼容）；
    指定时使用专用 remote（SOURCE_REMOTE）并指向该 URL。
    """
    url = (getattr(args, "remote_url", None) or "").strip()
    if not url:
        return UPSTREAM_REMOTE, UPSTREAM_BRANCH, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
    branch = (getattr(args, "remote_branch", None) or "").strip() or UPSTREAM_BRANCH
    return SOURCE_REMOTE, branch, f"{SOURCE_REMOTE}/{branch}"


def detect_local_proxy():
    """探测本机可用的 HTTP 代理，返回 URL 或 None。

    优先取环境变量 OAS_GIT_PROXY；否则依次试探常见本地代理端口（Clash/v2ray 等）。
    仅作为直连 github 失败时的回退手段，不修改 git config。
    """
    env_proxy = os.environ.get("OAS_GIT_PROXY")
    if env_proxy:
        return env_proxy
    for url in ("http://127.0.0.1:7897", "http://127.0.0.1:10809"):
        host, _, port = url.rpartition("//")[2].partition(":")
        try:
            with socket.create_connection((host, int(port)), timeout=0.3):
                return url
        except OSError:
            continue
    return None


def git_net(git_args, proxy=None):
    """联网 git（fetch / ls-remote）：禁止终端交互（私有库直接报错而非挂起），可选 http 代理。

    代理通过 GIT_CONFIG_* 环境变量注入，不改 git config。
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if proxy:
        base = int(env.get("GIT_CONFIG_COUNT", "0") or "0")
        env["GIT_CONFIG_COUNT"] = str(base + 1)
        env[f"GIT_CONFIG_KEY_{base}"] = "http.proxy"
        env[f"GIT_CONFIG_VALUE_{base}"] = proxy
    proc = subprocess.run(
        ["git", *git_args],
        capture_output=True, encoding="utf-8", errors="replace", env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def cmd_fetch(args):
    url = (getattr(args, "remote_url", None) or "").strip()
    remote, branch, ref = resolve_source(args)
    if url:
        ensure_source(remote, url)
    else:
        ensure_upstream()
    print(f"[fetch] 拉取 {remote}/{branch} ...")
    code, _, err = git_net(["fetch", remote, branch])
    if code != 0:
        # 直连 github 常被超时阻断；探测到本机代理则回退重试一次
        proxy = detect_local_proxy()
        if proxy:
            print(f"[fetch] 直连失败，改用本机代理 {proxy} 重试 ...")
            code, _, err = git_net(["fetch", remote, branch], proxy)
    if code != 0:
        print(f"[fetch] 拉取失败：{err.strip()}", file=sys.stderr)
        print("[fetch] 提示：可设置环境变量 OAS_GIT_PROXY=http://127.0.0.1:端口 "
              "指定代理后重试", file=sys.stderr)
        sys.exit(code)
    commits = collect_commits(args.base, ref, since=args.since)
    stats = Counter(c["type"] for c in commits)
    risks = Counter(c["risk"] for c in commits)
    print(f"[fetch] 完成。{args.base}..{ref} 自 {args.since} 起的待同步提交共 "
          f"{len(commits)} 条（已过滤内容已在本地者）")
    print("        类型分布: " + "  ".join(
        f"{t}={stats[t]}" for t in TYPE_ORDER if stats.get(t)))
    print(f"        风险分布: isolated={risks.get('isolated', 0)}  "
          f"multi={risks.get('multi', 0)}  "
          f"shared(⚠高冲突)={risks.get('shared', 0)}")


# ---------------------------------------------------------------------------
# branches：列出任意仓库的远程分支（供界面选择数据源分支）
# ---------------------------------------------------------------------------
def cmd_branches(args):
    url = (args.url or "").strip()
    if not url:
        print("[branches] 缺少 --url", file=sys.stderr)
        sys.exit(1)
    code, out, err = git_net(["ls-remote", "--heads", url])
    if code != 0:
        # 直连失败时回退本机代理重试一次（与 fetch 一致），不改 git config
        proxy = detect_local_proxy()
        if proxy:
            print(f"[branches] 直连失败，改用本机代理 {proxy} 重试 ...", file=sys.stderr)
            code, out, err = git_net(["ls-remote", "--heads", url], proxy)
    if code != 0:
        print(f"[branches] 获取分支失败：{err.strip()}", file=sys.stderr)
        print("[branches] 提示：私有仓库需凭据，可设置 OAS_GIT_PROXY 指定代理后重试",
              file=sys.stderr)
        sys.exit(code)
    branches = []
    for line in out.splitlines():
        _, _, refname = line.partition("\t")
        refname = refname.strip()
        if refname.startswith("refs/heads/"):
            branches.append(refname[len("refs/heads/"):])
    branches.sort()
    emit({"url": url, "branches": branches,
          "default": UPSTREAM_BRANCH if UPSTREAM_BRANCH in branches else
                     (branches[0] if branches else "")})


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------
def cmd_list(args):
    _, _, ref = resolve_source(args)
    git(["rev-parse", "--verify", ref], check=True)
    all_commits = collect_commits(args.base, ref, since=args.since, exclude_applied=False)
    # git cherry 的「已应用」覆盖全历史，必须与本次 --since 窗口求交，否则该组会膨胀
    applied_set = already_applied(args.base, ref)
    applied = [c for c in all_commits if c["hash"] in applied_set]
    window = {c["hash"] for c in all_commits}
    ignored = [{**it, "present": it.get("hash") in window} for it in load_ignored()]
    ignored_set = {it["hash"] for it in ignored if it.get("hash")}
    commits = [c for c in all_commits
               if c["hash"] not in applied_set and c["hash"] not in ignored_set]
    if not commits and not args.json:
        print(f"[list] {args.base}..{ref} 自 {args.since} 起没有待同步的提交")
        return

    if args.json:
        fields = ("hash", "date", "author", "subject", "type", "module",
                  "risk", "files", "adds", "dels", "changed", "size",
                  "framework", "level", "judge", "reasons")
        payload = {
            "base": args.base,
            "ref": ref,
            "since": args.since,
            "commits": [{k: c[k] for k in fields} for c in commits],
            "applied": [{k: c[k] for k in fields} for c in applied],
            "ignored": ignored,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            print(text)
        return

    groups = {}
    for c in commits:
        groups.setdefault(c["module"], []).append(c)
    ordered_groups = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    stats = Counter(c["type"] for c in commits)
    risks = Counter(c["risk"] for c in commits)
    lines = [
        "# 上游待同步提交清单",
        "",
        f"> 生成时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"> 范围: `{args.base}..{ref}`（自 {args.since} 起），已排除 merge 提交，"
        f"并过滤掉内容已在本地者",
        f"> 共 {len(commits)} 条 | 类型: " + "  ".join(
            f"{t}={stats[t]}" for t in TYPE_ORDER if stats.get(t)),
        f"> 风险: isolated={risks.get('isolated', 0)}  multi={risks.get('multi', 0)}  "
        f"shared(⚠)={risks.get('shared', 0)}",
        f"> 另有已跳过 {len(ignored)} 条 / 已并入本地 {len(applied)} 条"
        f"（网页「已排除·跳过」页查看）",
        ">",
        "> 图例：`⚠` = 触及共享基础设施文件（i18n/config 等），与本地定制冲突概率高，",
        ">       建议优先挑选无 ⚠ 的提交。",
        ">",
        "> 用法：把要同步的提交勾成 `[x]`（保持缩进），保存后运行：",
        ">   `python dev_tools/upstream_sync.py apply`",
        "",
    ]
    for module, items in ordered_groups:
        lines.append(f"## {module} ({len(items)})")
        lines.append("")
        for c in sorted(items, key=lambda x: x["date"], reverse=True):
            flag = "⚠ " if c["risk"] == "shared" else ""
            meta = f"+{c['adds']}/-{c['dels']} · {c['changed']}文件 · {c['judge']}"
            lines.append(
                f"- [ ] `{c['hash'][:8]}` [{c['type']}] {flag}{c['subject']}"
                f"　—　{meta}")
        lines.append("")

    path = args.out or DEFAULT_MANIFEST
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[list] 清单已生成: {path}")
    print(f"       共 {len(commits)} 条，分 {len(ordered_groups)} 个模块"
          f"（其中 ⚠ 高风险 {risks.get('shared', 0)} 条）")
    print(f"       请编辑清单勾选后运行: python dev_tools/upstream_sync.py apply")


# ---------------------------------------------------------------------------
# ignore / unignore / ignored（已跳过清单）
# ---------------------------------------------------------------------------
def cmd_ignore(args):
    """把若干提交标记为「跳过」，写入 DEFAULT_IGNORED，之后不再出现在待同步列表"""
    hashes = parse_hashes(args.hashes)
    if not hashes:
        print("[ignore] 未提供 --hashes", file=sys.stderr)
        sys.exit(1)
    short = [h for h in hashes if len(h) < 8]
    if short:
        print(f"[ignore] hash 至少 8 位: {', '.join(short)}", file=sys.stderr)
        sys.exit(1)

    url = (getattr(args, "remote_url", None) or "").strip()
    remote, branch, ref = resolve_source(args)
    source = f"{url} · {branch}" if url else f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"

    # 反查元数据，使记录在提交失效（rebase/移除）后仍能显示它是什么
    meta = {}
    if git(["rev-parse", "--verify", ref], check=False)[0] == 0:
        for c in collect_commits(args.base, ref, since=args.since, exclude_applied=False):
            meta[c["hash"][:8]] = c

    items = load_ignored()
    by_hash = {it.get("hash") for it in items}
    now = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    added = 0
    for h in hashes:
        c = meta.get(h[:8])
        full = c["hash"] if c else h
        if full in by_hash:
            continue
        items.append({
            "hash": full,
            "subject": c["subject"] if c else "(未知提交，可能已不在当前上游范围)",
            "date": c["date"] if c else "",
            "module": c["module"] if c else "",
            "type": c["type"] if c else "other",
            "source": source,
            "ignored_at": now,
            "reason": "manual",
        })
        by_hash.add(full)
        added += 1
    save_ignored(items)
    print(f"[ignore] 新增 {added} 条，已跳过共 {len(items)} 条（{DEFAULT_IGNORED}）")
    emit({"status": "ok", "added": added, "total": len(items)})


def cmd_unignore(args):
    """恢复若干被跳过的提交（按 hash 前缀匹配，至少 8 位；歧义则报错）"""
    hashes = parse_hashes(args.hashes)
    if not hashes:
        print("[unignore] 未提供 --hashes", file=sys.stderr)
        sys.exit(1)
    short = [h for h in hashes if len(h) < 8]
    if short:
        print(f"[unignore] hash 前缀至少 8 位: {', '.join(short)}", file=sys.stderr)
        sys.exit(1)

    items = load_ignored()
    resolved, ambiguous = [], []
    for h in hashes:
        hit = match_ignored(items, h)
        if len(hit) > 1:
            ambiguous.append(h)
        elif hit:
            resolved.append(hit[0])
    if ambiguous:
        print(f"[unignore] 前缀歧义，请补全 hash: {', '.join(ambiguous)}", file=sys.stderr)
        sys.exit(1)

    drop = {id(it) for it in resolved}
    items = [it for it in items if id(it) not in drop]
    save_ignored(items)
    print(f"[unignore] 恢复 {len(resolved)} 条，剩余已跳过 {len(items)} 条")
    emit({"status": "ok", "removed": len(resolved), "total": len(items)})


def cmd_ignored(args):
    """列出已跳过的提交"""
    items = load_ignored()
    if args.json:
        emit({"items": items})
        return
    if not items:
        print("[ignored] 暂无已跳过的提交")
        return
    print(f"[ignored] 共 {len(items)} 条：")
    for it in items:
        print(f"  {(it.get('hash') or '')[:8]} [{it.get('type', 'other')}] "
              f"{it.get('subject', '')}　—　{it.get('ignored_at', '')}")


# ---------------------------------------------------------------------------
# advise
# ---------------------------------------------------------------------------
def cmd_advise(args):
    """在 list 之上叠加「冲突预判 + 本地定制度」，并据此修正取舍建议。

    给 AI 顾问消费的信号：
      - conflict：merge-tree 模拟 cherry-pick，给出会不会冲突、冲突哪些文件
      - local_churn：本地 base 在涉及文件上的改动行数，越大越可能覆盖本地定制
    AI 读本结果（必要时再用 show 看 diff）产出人话建议，交由用户确认后再 apply。
    """
    _, _, ref = resolve_source(args)
    git(["rev-parse", "--verify", ref], check=True)
    commits = collect_commits(args.base, ref, since=args.since)
    ignored = ignored_hashes()
    if ignored:
        commits = [c for c in commits if c["hash"] not in ignored]
    churn = local_churn(args.base, ref)

    for c in commits:
        c["conflict"] = precheck_commit(c["hash"], args.base)
        touched = sum(churn.get(f, 0) for f in c["files"])
        cl = churn_level(touched)
        c["local_churn"] = {"lines": touched, "level": cl}

        level = c["level"]
        if c["conflict"]["status"] == "conflict":
            if LEVEL_RANK[level] < LEVEL_RANK["caution"]:
                level = "caution"
            c["reasons"].append(
                f"cherry-pick 预计冲突（{len(c['conflict']['files'])} 个文件），需人工取舍。")
        if cl == "high":
            level = "review"
            c["reasons"].append(
                f"本地已大幅定制涉及文件（相对共同祖先约 {touched} 行改动），"
                "直接合并易覆盖本地改动，建议单独评估。")
        elif cl == "medium":
            if LEVEL_RANK[level] < LEVEL_RANK["caution"]:
                level = "caution"
            c["reasons"].append(
                f"本地对涉及文件有一定定制（约 {touched} 行改动），合并后需实测。")
        c["level"] = level
        c["judge"] = LEVEL_TEXT[level]

    if args.json:
        stats = Counter(c["level"] for c in commits)
        payload = {
            "base": args.base, "ref": ref, "since": args.since,
            "summary": {
                "total": len(commits),
                "adopt": stats.get("adopt", 0),
                "caution": stats.get("caution", 0),
                "review": stats.get("review", 0),
                "conflict": sum(1 for c in commits
                                if c["conflict"]["status"] == "conflict"),
            },
            "commits": [
                {k: c[k] for k in
                 ("hash", "date", "author", "subject", "type", "module",
                  "risk", "files", "adds", "dels", "changed", "size",
                  "framework", "level", "judge", "reasons",
                  "conflict", "local_churn")}
                for c in commits
            ],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            print(text)
        return

    stats = Counter(c["level"] for c in commits)
    conflicts = sum(1 for c in commits if c["conflict"]["status"] == "conflict")
    print(f"[advise] 待同步 {len(commits)} 条 | 建议采用 {stats.get('adopt', 0)} · "
          f"需实测 {stats.get('caution', 0)} · 建议评估 {stats.get('review', 0)} | "
          f"预计冲突 {conflicts} 条")
    for c in commits:
        cf = "冲突" if c["conflict"]["status"] == "conflict" else "无冲突"
        print(f"  {c['hash'][:8]} [{c['type']}] {c['judge']} | {cf} | "
              f"本地定制{c['local_churn']['lines']}行 | {c['subject']}")


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------
def parse_manifest(path):
    """从清单里解析被勾选的提交 hash（按 [x] 标记）"""
    if not os.path.exists(path):
        print(f"[apply] 清单不存在: {path}，请先运行 list", file=sys.stderr)
        sys.exit(1)
    selected = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*-\s*\[([xX])\]\s*`([0-9a-fA-F]{7,40})`", line)
            if m:
                selected.append(m.group(2))
    return selected


def is_empty_commit(text):
    s = text.lower()
    return "nothing to commit" in s or "empty" in s or "previously applied" in s


def conflicted_files():
    _, out, _ = git(["diff", "--name-only", "--diff-filter=U"], check=False)
    return [l.strip() for l in out.split("\n") if l.strip()]


def cmd_apply(args):
    _, _, ref = resolve_source(args)
    git(["rev-parse", "--verify", ref], check=True)

    selected_hashes = parse_manifest(args.manifest)
    if not selected_hashes:
        print("[apply] 清单中没有任何勾选项（[x]），请先勾选", file=sys.stderr)
        sys.exit(1)

    # 只关心已跟踪文件的改动；未跟踪文件（如清单本身）不影响 cherry-pick
    _, dirty, _ = git(["status", "--porcelain", "--untracked-files=no"], check=False)
    if dirty.strip():
        print("[apply] 已跟踪文件有未提交改动，请先提交或暂存", file=sys.stderr)
        sys.exit(1)

    all_commits = collect_commits(args.base, ref, since=args.since)
    ignored = ignored_hashes()
    if ignored:
        all_commits = [c for c in all_commits if c["hash"] not in ignored]
    ignored_prefix = {h[:8].lower() for h in ignored}
    index = {c["hash"][:8]: i for i, c in enumerate(all_commits)}

    chosen = {}
    missing, skipped = [], []
    for h in selected_hashes:
        h = h[:8].lower()
        if h in index:
            chosen[h] = all_commits[index[h]]
        elif h in ignored_prefix:
            skipped.append(h)
        else:
            missing.append(h)
    if skipped:
        print(f"[apply] 以下勾选项已被跳过（ignored），本次不处理；"
              f"如需同步请先 unignore: {', '.join(skipped)}")
    if missing:
        print(f"[apply] 以下勾选项不在待同步范围内（可能内容已同步），已忽略: "
              f"{', '.join(missing)}")

    if not chosen:
        print("[apply] 没有有效的待同步提交", file=sys.stderr)
        sys.exit(1)

    base_sha = git_out(["rev-parse", args.base]).strip()
    branch = args.branch or f"sync/upstream-{datetime.now():%Y%m%d-%H%M%S}"

    if git(["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)[0] == 0:
        print(f"[apply] 分支已存在: {branch}，请指定其他 --branch 或先删除该分支",
              file=sys.stderr)
        sys.exit(1)

    def cleanup_branch():
        """失败中止时删除刚创建的同步分支，避免残留影响下次运行"""
        git(["cherry-pick", "--abort"], check=False)
        git(["switch", args.base], check=False)
        git(["branch", "-D", branch], check=False)

    print(f"[apply] 基线: {args.base} ({base_sha[:8]})")
    print(f"[apply] 新建分支: {branch}")
    git(["switch", "-c", branch, base_sha])

    deps = {}  # short hash -> commit，--deps 模式下自动附带的前置提交
    for attempt in range(MAX_DEP_ROUNDS + 1 if args.deps else 1):
        sequence = sorted(
            {**chosen, **deps}.values(), key=lambda c: c["date"] + c["hash"])
        # 整条序列一次性交给 git：git 会用 sequencer 记住尚未处理的提交，
        # 之后在界面里解决冲突时 --continue 才能把剩下的提交接着跑完
        code, out, err = git(["cherry-pick", *[c["hash"] for c in sequence]], check=False)
        status, msg = advance_pick(out + err, code)
        if status == "error":
            cleanup_branch()
            print(f"[apply] cherry-pick 失败：{msg}", file=sys.stderr)
            sys.exit(1)
        conflict = pick_head() if status == "conflict" else None

        if conflict is None:
            print(f"\n[apply] 完成，共应用 {len(sequence)} 个提交"
                  + (f"（其中自动附带 {len(deps)} 个依赖）" if deps else ""))
            if deps:
                print("[apply] 自动附带的依赖提交:")
                for c in sorted(deps.values(), key=lambda x: x["date"]):
                    print(f"         {c['hash'][:8]} {c['subject']}")
            print(f"\n下一步：在 {branch} 上测试，无误后合并回 {args.base}：")
            print(f"  git switch {args.base} && git merge --no-ff {branch}")
            emit({"status": "done", "branch": branch})
            return

        files = conflicted_files()

        if args.pause:
            print(f"\n[apply] 提交 {conflict['hash'][:8]} {conflict['subject']} 冲突，已暂停等待处理")
            print(f"        冲突文件: {', '.join(files) if files else '(未知)'}")
            emit({"status": "conflict", "branch": branch,
                  "commit": conflict["hash"][:8], "subject": conflict["subject"],
                  "files": files})
            sys.exit(2)

        git(["cherry-pick", "--abort"], check=False)
        git(["reset", "--hard", base_sha], check=False)

        print(f"\n[apply] 提交 {conflict['hash'][:8]} {conflict['subject']} 冲突")
        print(f"        冲突文件: {', '.join(files) if files else '(未知)'}")

        if not args.deps or attempt >= MAX_DEP_ROUNDS:
            cleanup_branch()
            print("[apply] 已中止（未自动处理冲突）。可选方案：", file=sys.stderr)
            print(f"        1) 手工 cherry-pick 后解决冲突：git cherry-pick {conflict['hash']}",
                  file=sys.stderr)
            if files:
                print(f"        2) 整体采用上游某个文件：git checkout {ref} -- <文件>",
                      file=sys.stderr)
            print("        3) 若该提交依赖前置提交，请在清单中一并勾选后重试",
                  file=sys.stderr)
            print("        4) 或加 --deps 让脚本尝试自动附带前置提交（可能拉入较多提交）",
                  file=sys.stderr)
            sys.exit(2)

        # --deps 模式：每个冲突文件只回溯“最近一个”未选中的前置提交，避免连锁膨胀
        ci = index[conflict["hash"][:8]]
        new_deps = {}
        for f in files:
            for c in reversed(all_commits[:ci]):
                sh = c["hash"][:8]
                if sh in chosen or sh in deps or sh in new_deps:
                    continue
                if f in c["files"]:
                    new_deps[sh] = c
                    break

        if not new_deps:
            cleanup_branch()
            print("[apply] 未找到可自动附带的前置提交，已中止。", file=sys.stderr)
            print(f"        请手工处理：git cherry-pick {conflict['hash']}", file=sys.stderr)
            sys.exit(2)
        if len(deps) + len(new_deps) > DEP_CAP:
            cleanup_branch()
            print(f"[apply] 自动附带的依赖将超过上限 {DEP_CAP}，已中止。", file=sys.stderr)
            sys.exit(2)

        deps.update(new_deps)
        print(f"[apply] 自动附带 {len(new_deps)} 个前置提交，重试整个序列:")
        for c in sorted(new_deps.values(), key=lambda x: x["date"]):
            print(f"         {c['hash'][:8]} {c['subject']}")

    cleanup_branch()
    print("[apply] 重试次数过多，已中止", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# 交互式冲突处理
# ---------------------------------------------------------------------------
def in_cherry_pick():
    return git(["rev-parse", "--verify", "--quiet", "CHERRY_PICK_HEAD"], check=False)[0] == 0


def current_branch():
    return git_out(["rev-parse", "--abbrev-ref", "HEAD"]).strip()


def current_pick_subject():
    code, out, _ = git(["log", "-1", "--pretty=%h %s", "CHERRY_PICK_HEAD"], check=False)
    return out.strip() if code == 0 else ""


def pick_head():
    """当前被 cherry-pick 的提交（冲突暂停时用来显示），返回 {"hash","subject"}；无则 None"""
    if not in_cherry_pick():
        return None
    return {"hash": git_out(["rev-parse", "CHERRY_PICK_HEAD"]).strip(),
            "subject": git_out(["log", "-1", "--pretty=%s", "CHERRY_PICK_HEAD"]).strip()}


def repo_root():
    return git_out(["rev-parse", "--show-toplevel"]).strip()


def cmd_conflicts(args):
    emit({"status": "conflict" if in_cherry_pick() else "idle",
          "branch": current_branch(),
          "commit": current_pick_subject(),
          "files": conflicted_files()})


def skip_empty_pick():
    """跳过“空”的 cherry-pick。

    多提交序列有 sequencer，用 --skip 前进到下一个；单提交没有 sequencer，
    --skip 会报 “no cherry-pick or revert in progress”，此时用 --quit 清除状态。
    """
    if git(["cherry-pick", "--skip"], check=False)[0] != 0:
        git(["cherry-pick", "--quit"], check=False)


def advance_pick(text, code):
    """根据一次 cherry-pick 调用的结果推进序列，直到跑完或遇到下一个冲突。

    text / code 来自刚才那次调用（首次批量 cherry-pick，或之后的 --continue）。
    返回 ("done", "") / ("conflict", "") / ("error", 错误信息)。
    遇到冲突时保持暂停态（CHERRY_PICK_HEAD 与冲突文件都留在工作区），
    由调用方决定是 emit 还是清理分支。
    """
    while True:
        if code == 0:
            return "done", ""
        if is_empty_commit(text):
            # 空提交：--skip 会让 sequencer 直接继续处理后面的提交
            skip_empty_pick()
            if conflicted_files():
                return "conflict", ""
            if not in_cherry_pick():
                return "done", ""
            code, out, err = git(["-c", "core.editor=true", "cherry-pick", "--continue"],
                                 check=False)
            text = out + err
            continue
        if conflicted_files():
            return "conflict", ""
        return "error", text.strip() or f"cherry-pick 失败（{code}）"


def continue_pick():
    """继续 cherry-pick 序列；若遇到下一个冲突则再次暂停"""
    code, out, err = git(["-c", "core.editor=true", "cherry-pick", "--continue"], check=False)
    status, msg = advance_pick(out + err, code)
    if status == "conflict":
        pick = pick_head() or {}
        emit({"status": "conflict", "branch": current_branch(),
              "commit": (pick.get("hash") or "")[:8], "subject": pick.get("subject", ""),
              "files": conflicted_files()})
        sys.exit(2)
    if status == "done":
        emit({"status": "done", "branch": current_branch()})
        return
    emit({"status": "error", "message": msg})
    sys.exit(1)


def resolve_one(path, choice):
    """处理单个冲突文件；返回错误信息，成功返回 None

    ours = 保留本地，theirs = 采用上游。对「删除/修改」冲突，缺少的一侧
    用 git rm 表达“保留删除”，避免 checkout 因 stage 缺失而失败。
    """
    _, out, _ = git(["ls-files", "-u", "--", path], check=False)
    stages = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            stages.add(parts[2])
    if choice == "ours":
        if "2" in stages:
            code, o, e = git(["checkout", "--ours", "--", path], check=False)
        else:
            code, o, e = git(["rm", "-f", "--", path], check=False)
    else:
        if "3" in stages:
            code, o, e = git(["checkout", "--theirs", "--", path], check=False)
        else:
            code, o, e = git(["rm", "-f", "--", path], check=False)
    if code != 0:
        return (e or o).strip()
    if os.path.exists(os.path.join(repo_root(), path)):
        git(["add", "-A", "--", path], check=False)
    return None


def cmd_resolve(args):
    if not in_cherry_pick():
        emit({"status": "error", "message": "当前没有正在进行的 cherry-pick"})
        sys.exit(1)
    choices = {}
    if args.choices_file:
        with open(args.choices_file, "r", encoding="utf-8") as f:
            choices = json.load(f)
    elif args.choices:
        choices = json.loads(args.choices)
    for f, c in choices.items():
        if c not in ("ours", "theirs"):
            emit({"status": "error", "message": f"未知选择: {c}"})
            sys.exit(1)
        err = resolve_one(f, c)
        if err:
            emit({"status": "error", "message": f"{f}: {err}"})
            sys.exit(1)

    remaining = conflicted_files()
    if remaining:
        emit({"status": "conflict", "branch": current_branch(),
              "commit": current_pick_subject(), "files": remaining,
              "message": "仍有未处理的冲突文件"})
        sys.exit(2)
    continue_pick()


def cmd_abort(args):
    branch = current_branch()
    git(["cherry-pick", "--abort"], check=False)
    if branch and branch != args.base:
        git(["switch", args.base], check=False)
        git(["branch", "-D", branch], check=False)
    emit({"status": "aborted", "branch": branch})


def _stage_content(stage, path):
    code, out, _ = git(["show", f":{stage}:{path}"], check=False)
    return out if code == 0 else None


def parse_conflict_hunks(text):
    """解析工作区文件中的冲突标记，返回 [{ours:[行], theirs:[行]}]"""
    hunks = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].startswith("<<<<<<<"):
            ours, theirs = [], []
            i += 1
            while (i < len(lines) and not lines[i].startswith("|||||||")
                   and not lines[i].startswith("=======")):
                ours.append(lines[i]); i += 1
            if i < len(lines) and lines[i].startswith("|||||||"):
                while i < len(lines) and not lines[i].startswith("======="):
                    i += 1
            i += 1  # 跳过 =======
            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i]); i += 1
            i += 1  # 跳过 >>>>>>>
            hunks.append({"ours": ours, "theirs": theirs})
        else:
            i += 1
    return hunks


def analyze_conflict(path, hunks, base, ours, theirs):
    """启发式生成中文冲突原因提示（推断，非绝对准确）"""
    tips = []
    if path.startswith(SHARED_PREFIXES) or path in SHARED_FILES:
        tips.append("该文件属于共享基础设施（配置/i18n），本地通常已定制，冲突多由此产生。")
    if ours is None and theirs is not None:
        tips.append("本地已删除该文件，而上游有改动（删除/修改冲突）。"
                    "「保留本地」= 保持删除；「采用上游」= 恢复上游版本。")
    elif theirs is None and ours is not None:
        tips.append("上游删除了该文件，而本地有改动（修改/删除冲突）。"
                    "「保留本地」= 保留本地版本；「采用上游」= 接受上游删除。")
    for idx, h in enumerate(hunks, 1):
        o, t = h["ours"], h["theirs"]
        if not o and t:
            tips.append(f"第 {idx} 处：本地为空、上游有内容 —— 上游新增了内容。")
        elif o and not t:
            tips.append(f"第 {idx} 处：上游为空、本地有内容 —— 上游删除了内容。")
        else:
            tips.append(f"第 {idx} 处：双方都改了同一处（本地 {len(o)} 行 / 上游 {len(t)} 行）。")
    if not tips:
        tips.append("无法自动分析该文件，请查看下方差异后自行决定。")
    return tips


def cmd_conflict_detail(args):
    path = args.file
    base = _stage_content(1, path)
    ours = _stage_content(2, path)
    theirs = _stage_content(3, path)
    wt = None
    full = os.path.join(repo_root(), path)
    if os.path.exists(full):
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                wt = f.read()
        except OSError:
            wt = None
    binary = wt is not None and "\x00" in wt
    hunks = [] if (wt is None or binary) else parse_conflict_hunks(wt)
    emit({"status": "ok", "file": path, "binary": binary,
          "has_base": base is not None, "has_ours": ours is not None,
          "has_theirs": theirs is not None,
          "hunks": hunks, "analysis": analyze_conflict(path, hunks, base, ours, theirs),
          "ours_text": (ours or "")[:20000], "theirs_text": (theirs or "")[:20000]})


def cmd_show(args):
    """查看某个上游提交的改动摘要与 diff（供界面预览，不改动工作区）"""
    commit = args.commit
    code, _, _ = git(["rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"],
                     check=False)
    if code != 0:
        emit({"status": "error", "message": f"找不到提交: {commit}"})
        sys.exit(1)
    _, stat, _ = git(["show", "--stat", "--format=", "--no-color", commit],
                     check=False)
    _, patch, _ = git(["show", "--format=", "--no-color", "--unified=3", commit],
                      check=False)
    truncated = len(patch) > MAX_PATCH_CHARS
    emit({"status": "ok", "commit": commit, "stat": stat.strip(),
          "patch": patch[:MAX_PATCH_CHARS], "truncated": truncated})


def build_parser():
    p = argparse.ArgumentParser(
        description="从上游 runhey/OnmyojiAutoScript dev 分支按需挑选提交同步到本地")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"本地基线分支（默认 {DEFAULT_BASE}）")
    p.add_argument("--since", default=DEFAULT_SINCE,
                   help=f'只对比该时间之后的提交，git 时间表达式（默认 "{DEFAULT_SINCE}"）')
    p.add_argument("--remote-url", default=None,
                   help="自定义数据源仓库地址（如另一个 fork）；留空则用默认 "
                        f"{UPSTREAM_URL}")
    p.add_argument("--remote-branch", default=None,
                   help=f"自定义数据源分支（默认 {UPSTREAM_BRANCH}）；仅在 --remote-url 时生效")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="配置 upstream 并拉取上游 dev 分支")

    p_branches = sub.add_parser("branches", help="列出任意仓库的远程分支（JSON）")
    p_branches.add_argument("--url", required=True, help="仓库地址（https 或 git@）")

    p_list = sub.add_parser("list", help="生成待选提交清单（Markdown）")
    p_list.add_argument("--out", default=None,
                        help=f"清单输出路径（默认 {DEFAULT_MANIFEST}）")
    p_list.add_argument("--json", action="store_true",
                        help="以 JSON 输出提交数据（供界面读取），而非 Markdown")

    p_apply = sub.add_parser("apply", help="按清单勾选新建分支并 cherry-pick")
    p_apply.add_argument("--manifest", default=DEFAULT_MANIFEST,
                         help=f"清单路径（默认 {DEFAULT_MANIFEST}）")
    p_apply.add_argument("--branch", default=None,
                         help="同步分支名（默认 sync/upstream-时间戳）")
    p_apply.add_argument("--deps", action="store_true",
                         help="冲突时尝试自动附带前置提交（谨慎，可能拉入较多提交）")
    p_apply.add_argument("--pause", action="store_true",
                         help="冲突时暂停（不中止、不清理分支），供界面逐文件处理后再继续")

    sub.add_parser("conflicts", help="查看当前未解决的冲突文件（JSON）")

    p_res = sub.add_parser("resolve", help="按选择处理冲突文件并继续 cherry-pick")
    p_res.add_argument("--choices", default=None,
                       help='JSON: {"文件路径": "ours"|"theirs"}，ours=保留本地，theirs=采用上游')
    p_res.add_argument("--choices-file", default=None,
                       help="从文件读取选择 JSON（避免命令行转义问题）")

    sub.add_parser("abort", help="中止当前 cherry-pick 并删除同步分支")

    p_cd = sub.add_parser("conflict-detail", help="查看单个冲突文件的差异与中文分析（JSON）")
    p_cd.add_argument("--file", required=True, help="冲突文件路径")

    p_show = sub.add_parser("show", help="查看某个上游提交的改动（stat + diff，JSON）")
    p_show.add_argument("--commit", required=True, help="提交 hash（完整或短 hash）")

    p_adv = sub.add_parser(
        "advise", help="逐条给出冲突预判 + 本地定制度并修正取舍建议（供 AI 顾问）")
    p_adv.add_argument("--json", action="store_true", help="以 JSON 输出（供 AI/界面消费）")
    p_adv.add_argument("--out", default=None, help="JSON 输出路径（默认打印到 stdout）")

    p_ign = sub.add_parser(
        "ignore", help="把提交标记为「跳过」（写入 upstream_ignored.json，不再出现在待同步列表）")
    p_ign.add_argument("--hashes", required=True, help="逗号分隔的提交 hash（完整或 >=8 位前缀）")

    p_unign = sub.add_parser("unignore", help="恢复被跳过的提交（按 hash 前缀匹配）")
    p_unign.add_argument("--hashes", required=True, help="逗号分隔的提交 hash（完整或 >=8 位前缀）")

    p_ignored = sub.add_parser("ignored", help="列出已跳过的提交")
    p_ignored.add_argument("--json", action="store_true", help="以 JSON 输出")
    return p


def main():
    args = build_parser().parse_args()

    code, _, _ = git(["rev-parse", "--show-toplevel"], check=False)
    if code != 0:
        print("当前目录不是 git 仓库", file=sys.stderr)
        sys.exit(1)

    if args.cmd == "fetch":
        cmd_fetch(args)
    elif args.cmd == "branches":
        cmd_branches(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "apply":
        cmd_apply(args)
    elif args.cmd == "conflicts":
        cmd_conflicts(args)
    elif args.cmd == "resolve":
        cmd_resolve(args)
    elif args.cmd == "abort":
        cmd_abort(args)
    elif args.cmd == "conflict-detail":
        cmd_conflict_detail(args)
    elif args.cmd == "show":
        cmd_show(args)
    elif args.cmd == "advise":
        cmd_advise(args)
    elif args.cmd == "ignore":
        cmd_ignore(args)
    elif args.cmd == "unignore":
        cmd_unignore(args)
    elif args.cmd == "ignored":
        cmd_ignored(args)


if __name__ == "__main__":
    main()