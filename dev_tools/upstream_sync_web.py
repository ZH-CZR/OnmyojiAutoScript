# This Python file uses the following encoding: utf-8
"""上游提交同步 —— 本地网页选单界面

仅使用标准库，在本机 127.0.0.1 起一个 http.server，用浏览器勾选要同步的上游提交，
并在界面内一键执行 cherry-pick（调用 dev_tools/upstream_sync.py apply）。

启动：
    python dev_tools/upstream_sync_web.py
"""
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_SCRIPT = os.path.join(REPO_ROOT, "dev_tools", "upstream_sync.py")
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_SINCE = "2 months ago"
BASE_BRANCH = "mine"
JSON_MARK = "@@SYNC@@"  # 与 upstream_sync.py 约定的机器可读行前缀

# ---------------------------------------------------------------------------
# 中英术语词表（可自行增删）：用于把英文提交标题汉化
# ---------------------------------------------------------------------------
TYPE_ZH = {
    "feat": "新功能", "feature": "新功能", "fix": "修复", "bugfix": "修复",
    "refactor": "重构", "perf": "性能优化", "chore": "杂务", "docs": "文档",
    "doc": "文档", "style": "格式", "test": "测试", "build": "构建",
    "ci": "持续集成", "revert": "回退", "optimize": "优化", "wip": "进行中",
}

MODULE_ZH = {
    "GeneralBattle": "通用战斗", "RichMan": "大富翁", "GameUi": "游戏界面",
    "Component": "通用组件", "Restart": "重启", "workflow": "工作流",
    "ActivityShikigami": "活动式神", "Costume": "皮肤", "DemonEncounter": "逢魔之时",
    "FrogBoss": "青蛙首领", "BondlingFairyland": "契灵之境", "BudokaiTournament": "斗技赛",
    "GeneralInvite": "通用组队", "HeroTest": "百鬼夜行", "atom": "原子任务",
    "DailyTrifles": "日常杂项", "EternitySea": "永生之海", "Exploration": "探索",
    "FallenSun": "堕落之阳", "Orochi": "八岐大蛇", "WeeklyTrifles": "周常杂项",
    "base_task": "基础任务", "Dokan": "道馆", "Duel_Try": "斗技尝试",
    "GuildActivityMonitor": "寮活动监控", "KekkaiActivation": "结界激活", "Nian": "年兽",
    "README": "说明文档", "RyouToppa": "突破", "ScriptTask": "脚本任务",
    "SwitchAccount": "切换账号", "SwitchOnmyoji": "切换阴阳师", "TouchFish": "摸鱼",
    "config": "配置", "device": "设备", "emulator": "模拟器", "i18": "国际化",
    "image": "图像", "ocr": "文字识别",
}

# 常见英文词（小写键）；按词边界整体替换，不会破坏 CamelCase / 下划线标识符
WORD_ZH = {
    "add": "新增", "adds": "新增", "added": "新增", "adding": "新增",
    "update": "更新", "updates": "更新", "updated": "更新", "upd": "更新",
    "remove": "删除", "removed": "删除", "removes": "删除",
    "delete": "删除", "deleted": "删除", "fix": "修复", "fixes": "修复",
    "fixed": "修复", "fixing": "修复", "optimize": "优化", "optimized": "优化",
    "improve": "改进", "improved": "改进", "adjust": "调整", "adjusted": "调整",
    "refactor": "重构", "renamed": "重命名", "rename": "重命名", "move": "移动",
    "merge": "合并", "revert": "回退", "split": "拆分", "implement": "实现",
    "support": "支持", "supports": "支持", "allow": "允许", "avoid": "避免",
    "ensure": "确保", "check": "检查", "checks": "检查", "handle": "处理",
    "task": "任务", "tasks": "任务", "click": "点击", "clicks": "点击",
    "image": "图片", "images": "图片", "config": "配置", "configuration": "配置",
    "battle": "战斗", "wait": "等待", "waiting": "等待", "fallback": "兜底",
    "random": "随机", "expectation": "预期", "model": "模型", "reward": "奖励",
    "rewards": "奖励", "explore": "探索", "exploration": "探索", "invite": "邀请",
    "guild": "寮", "boss": "首领", "area": "区域", "team": "队伍",
    "preset": "预设", "timeline": "时间轴", "shikigami": "式神", "soul": "御魂",
    "souls": "御魂", "summon": "召唤", "awake": "觉醒", "evolve": "升星",
    "duel": "斗技", "kekkai": "结界", "realm": "境界", "raid": "突袭",
    "friend": "好友", "friends": "好友", "mail": "邮件", "login": "登录",
    "account": "账号", "server": "服务器", "device": "设备", "emulator": "模拟器",
    "screenshot": "截图", "button": "按钮", "page": "页面", "menu": "菜单",
    "error": "错误", "exception": "异常", "timeout": "超时", "retry": "重试",
    "loop": "循环", "logic": "逻辑", "condition": "条件", "default": "默认",
    "option": "选项", "switch": "切换", "missing": "缺失", "invalid": "无效",
    "empty": "空", "limit": "限制", "count": "数量", "memory": "内存",
    "performance": "性能", "slow": "慢", "fast": "快", "bug": "缺陷",
    "issue": "问题", "crash": "崩溃", "freeze": "卡死", "stuck": "卡住",
    "state": "状态", "status": "状态", "progress": "进度", "auto": "自动",
    "manual": "手动", "enable": "启用", "disable": "禁用", "show": "显示",
    "hide": "隐藏", "open": "打开", "close": "关闭", "start": "开始",
    "stop": "停止", "reset": "重置", "save": "保存", "load": "加载",
    "create": "创建", "buy": "购买", "sell": "出售", "level": "等级",
    "slot": "槽位", "equip": "装备", "weapon": "武器", "skill": "技能",
    "buff": "增益", "debuff": "减益", "daily": "每日", "weekly": "每周",
    "test": "测试", "debug": "调试", "log": "日志", "file": "文件",
    "files": "文件", "path": "路径", "name": "名称", "value": "值",
    "type": "类型", "size": "大小", "total": "总计", "sort": "排序",
    "filter": "筛选", "search": "搜索", "select": "选择", "scroll": "滚动",
    "input": "输入", "output": "输出", "new": "新", "old": "旧",
    "all": "全部", "more": "更多", "only": "仅", "before": "之前",
    "after": "之后", "again": "再次", "now": "现在", "first": "首次",
    "last": "最后", "next": "下一个", "previous": "上一个", "time": "时间",
    "times": "次数", "region": "区域", "activity": "活动", "entry": "入口",
    "proxy": "代理", "network": "网络", "restart": "重启", "startup": "启动",
}

_WORD_RE = re.compile(
    "|".join(rf"\b{re.escape(k)}\b" for k in sorted(WORD_ZH, key=len, reverse=True)),
    re.IGNORECASE,
)


def translate_phrase(text):
    """按词表整体替换英文单词（不改动 CamelCase / 下划线标识符）"""
    if not text:
        return text
    return _WORD_RE.sub(lambda m: WORD_ZH[m.group(0).lower()], text)


def translate_module(name):
    """模块名汉化；未知模块退化为词表翻译，保留原名便于对照"""
    return ",".join(MODULE_ZH.get(p.strip(), p.strip()) for p in name.split(","))


_SUBJ_RE = re.compile(r"^([A-Za-z]+)(\(([^)]*)\))?(!?):\s*(.*)$", re.S)


def split_subject(subject):
    """拆出 (中文类型/范围前缀, 英文描述)；非 conventional 风格时前缀为空"""
    m = _SUBJ_RE.match(subject)
    if not m:
        return "", subject
    typ, scope, bang, desc = m.group(1), m.group(3), m.group(4) or "", m.group(5)
    head = TYPE_ZH.get(typ.lower(), typ)
    if scope:
        head += f"({translate_module(scope)})"
    return head + bang, desc


def translate_subject(subject):
    """离线汉化标题（提交列表首屏立即展示，无需联网）"""
    head, desc = split_subject(subject)
    if not head:
        return translate_phrase(desc)
    return f"{head}: {translate_phrase(desc)}"


# ---------------------------------------------------------------------------
# 联网翻译（可选，可关闭）：百度（首选，需 appid+密钥）→ 有道 demo → MyMemory 兜底。
# 凭据优先取环境变量 BAIDU_TRANSLATE_APPID / BAIDU_TRANSLATE_KEY，
# 其次读 dev_tools/baidu_translate.json（形如 {"appid": "...", "key": "..."}，勿提交到仓库）。
# 均无 key 时自动退回离线词表；仅翻译标题里的自由描述部分。
# ---------------------------------------------------------------------------
BAIDU_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
BAIDU_CONFIG = os.path.join(REPO_ROOT, "dev_tools", "baidu_translate.json")
BAIDU_APPID = os.environ.get("BAIDU_TRANSLATE_APPID", "")
BAIDU_KEY = os.environ.get("BAIDU_TRANSLATE_KEY", "")
YOUDAO_URL = "https://aidemo.youdao.com/trans"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
TR_CHUNK = 450          # 单条文本上限，超出则按词边界切块
TR_BATCH_CHARS = 900    # 多条短文本拼成一次请求的字符上限（大幅减少请求数）
TR_MAX_ITEM = 400       # 超过此长度的单条不参与拼接，单独翻译
TR_SLEEP = 0.3          # 批次间隔，避免触发免费接口的“请求频率过快”
_TR_CACHE = {}          # 原文描述 -> 中文（进程内缓存，不落盘）
_TR_LOCK = threading.Lock()
_MM_DISABLED_UNTIL = 0.0  # MyMemory 被限流后的冷却截止时间


def baidu_ready():
    """百度凭据是否可用（首次调用时尝试从配置文件加载）"""
    global BAIDU_APPID, BAIDU_KEY
    if BAIDU_APPID and BAIDU_KEY:
        return True
    try:
        with open(BAIDU_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        BAIDU_APPID = BAIDU_APPID or str(cfg.get("appid") or "").strip()
        BAIDU_KEY = BAIDU_KEY or str(cfg.get("key") or "").strip()
    except (OSError, ValueError):
        return False
    return bool(BAIDU_APPID and BAIDU_KEY)


def _has_cjk(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _baidu_batch(texts):
    """百度翻译（首选）；多条换行拼接，按行返回 [(原文, 中文)]，失败返回 None"""
    if not baidu_ready():
        return None
    q = "\n".join(texts)
    salt = str(random.randint(100000, 999999))
    sign = hashlib.md5(
        (BAIDU_APPID + q + salt + BAIDU_KEY).encode("utf-8")).hexdigest()
    body = urllib.parse.urlencode({
        "q": q, "from": "en", "to": "zh",
        "appid": BAIDU_APPID, "salt": salt, "sign": sign,
    }).encode("utf-8")
    req = urllib.request.Request(
        BAIDU_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if data.get("error_code"):
        return None
    lines = [x.get("dst", "") for x in (data.get("trans_result") or [])]
    if len(lines) != len(texts):
        return None
    return list(zip(texts, lines))


def _split_chunks(text):
    words, out, cur = text.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > TR_CHUNK:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        out.append(cur)
    return out


def _get_json(url, timeout=12):
    req = urllib.request.Request(
        url, headers={"User-Agent": "OnmyojiAutoScript/dev_tools"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _youdao(text):
    """有道（主）：返回中文，失败返回 None；遇 411 限流重试一次"""
    params = urllib.parse.urlencode({"q": text, "from": "en", "to": "zh-CHS"})
    url = f"{YOUDAO_URL}?{params}"
    for attempt in (0, 1):
        try:
            data = _get_json(url)
        except Exception:  # noqa: BLE001
            return None
        if str(data.get("errorCode")) == "0":
            parts = data.get("translation") or []
            zh = "".join(parts) if isinstance(parts, list) else str(parts)
            return zh if _has_cjk(zh) else None
        if str(data.get("errorCode")) == "411" and attempt == 0:
            time.sleep(1.5)  # 请求频率过快，短暂等待后重试
            continue
        return None
    return None


def _youdao_batch(texts):
    """多条短文本用换行拼接成一次请求；返回 [(原文, 中文)]，行数对不上返回 None"""
    zh = _youdao("\n".join(texts))
    if zh is None:
        return None
    lines = zh.split("\n")
    if len(lines) != len(texts):
        return None  # 行数与输入不一致，放弃拼接结果，逐条重试
    return list(zip(texts, lines))


def _mymemory(text):
    """MyMemory（兜底）：被限流时进入冷却，返回中文，失败返回 None"""
    global _MM_DISABLED_UNTIL
    if time.time() < _MM_DISABLED_UNTIL:
        return None
    params = urllib.parse.urlencode({"q": text, "langpair": "en|zh-CN"})
    try:
        data = _get_json(f"{MYMEMORY_URL}?{params}")
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            _MM_DISABLED_UNTIL = time.time() + 300  # 冷却 5 分钟
        return None
    except Exception:  # noqa: BLE001
        return None
    if str(data.get("responseStatus")) != "200":
        return None
    zh = (data.get("responseData") or {}).get("translatedText") or ""
    return zh if _has_cjk(zh) else None


def _translate_chunk(text):
    """单段文本：百度 → 有道 → MyMemory，全部失败返回 None"""
    pairs = _baidu_batch([text])
    if pairs:
        return pairs[0][1]
    return _youdao(text) or _mymemory(text)


def translate_desc(desc):
    """翻译一段英文描述；命中缓存直接返回，全失败返回 None"""
    with _TR_LOCK:
        if desc in _TR_CACHE:
            return _TR_CACHE[desc]
    outs = []
    for part in _split_chunks(desc):
        zh = _translate_chunk(part)
        if zh is None:
            return None
        outs.append(zh)
    result = "".join(outs)
    with _TR_LOCK:
        _TR_CACHE[desc] = result
    return result


def _take_batch(items):
    """按字符上限取一批可拼接的短文本；过长的一条单独成批"""
    batch, total = [], 0
    for t in items:
        if len(t) > TR_MAX_ITEM:
            return [t] if not batch else batch
        if batch and total + len(t) + 1 > TR_BATCH_CHARS:
            break
        batch.append(t)
        total += len(t) + 1
    return batch


def translate_texts(texts):
    """批量翻译；返回 {原文: 中文}，未成功的键不返回

    多条短文本拼成一次请求（换行分隔），把请求数从“条数”降到“批次”级别，
    避免触发免费接口的频率限制；拼接失败则逐条兜底。
    """
    out, todo = {}, []
    with _TR_LOCK:
        for t in texts:
            if not t:
                continue
            if t in _TR_CACHE:
                out[t] = _TR_CACHE[t]
            elif t not in todo:
                todo.append(t)

    i = 0
    while i < len(todo):
        batch = _take_batch(todo[i:])
        i += len(batch)
        pairs = None
        if len(batch) > 1:
            pairs = _baidu_batch(batch) or _youdao_batch(batch)
        if pairs is None:
            pairs = [(t, translate_desc(t)) for t in batch]
        for t, zh in pairs:
            if zh:
                with _TR_LOCK:
                    _TR_CACHE[t] = zh
                out[t] = zh
        if i < len(todo):
            time.sleep(TR_SLEEP)
    return {"translations": out, "provider": "百度" if baidu_ready() else "有道"}


def parse_sync_json(output):
    """从脚本输出里取出最后一行 @@SYNC@@{...}"""
    for line in reversed((output or "").splitlines()):
        if line.startswith(JSON_MARK):
            try:
                return json.loads(line[len(JSON_MARK):])
            except json.JSONDecodeError:
                return None
    return None

PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>上游提交同步</title>
<style>
  :root {
    --bg: #0e1220; --bg2: #151b2e; --card: #1a2136; --card2: #212a44;
    --line: #2b3555; --txt: #e8ecf8; --dim: #9aa6c9; --accent: #5b8cff;
    --accent2: #22d3ee; --warn: #f7b955; --ok: #4ade80; --err: #ff6b81;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif;
    background: radial-gradient(1200px 600px at 15% -10%, #1b2547 0%, var(--bg) 55%);
    color: var(--txt); font-size: 15px; line-height: 1.5;
  }
  header { padding: 20px 24px 12px; }
  h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: .5px; }
  h1 .sub { font-size: 13px; color: var(--dim); font-weight: 400; margin-left: 10px; }
  .stats { margin-top: 6px; color: var(--dim); font-size: 13px; }
  .stats b { color: var(--txt); }
  .toolbar { padding: 0 24px 12px; display: flex; flex-direction: column; gap: 10px; }
  .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  input, select, button {
    font-family: inherit; font-size: 14px; color: var(--txt);
    background: var(--card); border: 1px solid var(--line); border-radius: 9px;
    padding: 8px 12px; outline: none;
  }
  input:focus, select:focus { border-color: var(--accent); }
  input#q { flex: 1; min-width: 220px; }
  input#since { width: 150px; }
  input#repoUrl { flex: 1; min-width: 260px; }
  button { cursor: pointer; transition: .15s; }
  button:hover { border-color: var(--accent); }
  button.primary { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #06101f; font-weight: 700; border: none; }
  button.primary:disabled { opacity: .5; cursor: not-allowed; }
  button.ghost { background: transparent; }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    padding: 6px 12px; border-radius: 999px; border: 1px solid var(--line);
    background: var(--card); font-size: 13px; cursor: pointer; user-select: none; color: var(--dim);
  }
  .chip.on { background: var(--accent); border-color: var(--accent); color: #06101f; font-weight: 700; }
  .sel-count { margin-left: auto; color: var(--dim); }
  .sel-count b { color: var(--accent2); font-size: 17px; }
  main { padding: 4px 24px 16px; display: flex; flex-direction: column; gap: 12px; }
  .module { background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
  .module > .mhead {
    display: flex; align-items: center; gap: 12px; padding: 10px 14px;
    background: var(--card2); cursor: pointer;
  }
  .mhead .mtitle { font-weight: 700; font-size: 15px; }
  .mhead .mcount { color: var(--dim); font-size: 13px; }
  .mhead .caret { margin-left: auto; color: var(--dim); transition: .2s; }
  .module.collapsed .caret { transform: rotate(-90deg); }
  .module.collapsed .rows { display: none; }
  .rows { display: flex; flex-direction: column; }
  .item { display: flex; align-items: flex-start; gap: 10px; padding: 9px 14px; border-top: 1px solid #232c47; }
  .item:hover { background: #1e2740; }
  .item input[type=checkbox] { width: 17px; height: 17px; margin-top: 3px; accent-color: var(--accent); cursor: pointer; }
  .item .hash { font-family: Consolas, monospace; color: var(--accent2); font-size: 13px; min-width: 76px; }
  .item .subject { flex: 1; }
  .item .date { color: var(--dim); font-size: 12px; min-width: 84px; text-align: right; }
  .cwrap { border-top: 1px solid #232c47; }
  .cwrap:first-child { border-top: none; }
  .cwrap .item { border-top: none; }
  .files { padding: 0 14px 9px 44px; }
  .files .ftoggle { cursor: pointer; color: var(--accent2); font-size: 12.5px; user-select: none; }
  .files .ftoggle:hover { text-decoration: underline; }
  .files .flist { margin-top: 4px; font-family: Consolas, monospace; font-size: 12px; color: var(--dim); }
  .files.collapsed .flist { display: none; }
  .files .fpath { padding: 1px 0; }
  .files .fpath.cf { color: #ff8a9b; font-weight: 700; }
  .badge { display: inline-block; padding: 1px 8px; border-radius: 6px; font-size: 12px; font-weight: 700; margin-right: 4px; }
  .b-feat { background: #24406b; color: #8fc0ff; }
  .b-fix { background: #123f2e; color: #6ee7a8; }
  .b-refactor { background: #3d2b57; color: #c9a6ff; }
  .b-perf { background: #4a3a10; color: #ffd86b; }
  .b-other { background: #2c3352; color: #b6c1e0; }
  .b-warn { background: #4a3410; color: var(--warn); }
  footer { padding: 8px 24px; display: flex; gap: 10px; align-items: center; position: sticky; bottom: 0;
           background: linear-gradient(180deg, rgba(14,18,32,.6), var(--bg2)); backdrop-filter: blur(6px); border-top: 1px solid var(--line); }
  footer input { flex: 1; }
  .logwrap { padding: 0 24px 24px; }
  pre#log {
    margin: 0; padding: 14px; background: #0a0e1a; border: 1px solid var(--line);
    border-radius: 12px; max-height: 260px; overflow: auto; white-space: pre-wrap;
    font-family: Consolas, monospace; font-size: 13px; color: #cfe0ff;
  }
  .empty { color: var(--dim); padding: 40px; text-align: center; }
  .loading { color: var(--accent2); }
  .pc-ok { background: #123f2e; color: #6ee7a8; }
  .pc-conflict { background: #4a1a22; color: #ff8a9b; }
  .mhint { margin-left: auto; font-size: 12px; color: var(--dim); cursor: pointer; padding: 2px 8px; border-radius: 6px; }
  .mhint:hover { background: #2b3555; color: var(--accent2); }
  .banner { margin: 0 24px 10px; padding: 11px 15px; border-radius: 10px; font-size: 14px; display: none; }
  .banner.show { display: block; }
  .banner.warn { background: #3a2a0d; border: 1px solid #6b4d12; color: #ffd88a; }
  .banner.ok { background: #0f3324; border: 1px solid #1d6b45; color: #8ff0b8; }
  .toggle { display: flex; align-items: center; gap: 6px; color: var(--dim); font-size: 13px; cursor: pointer; }
  .toggle input { width: 16px; height: 16px; accent-color: var(--accent); }
  .cpanel { margin: 0 24px 12px; background: var(--card); border: 1px solid #6b4d12; border-radius: 12px; padding: 14px 16px; }
  .cpanel h2 { margin: 0 0 4px; font-size: 18px; }
  .cpanel .csub { color: var(--dim); font-size: 13px; margin-bottom: 8px; }
  .cfile { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: #161d31; }
  .cfile .cpath { font-family: Consolas, monospace; font-size: 13px; color: var(--accent2); word-break: break-all; }
  .cfile .crow { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
  .cbtn { padding: 6px 14px; border-radius: 8px; border: 1px solid var(--line); background: transparent; color: var(--dim); font-size: 13px; cursor: pointer; }
  .cbtn.on { background: var(--accent); border-color: var(--accent); color: #06101f; font-weight: 700; }
  .cbtn.theirs.on { background: var(--ok); border-color: var(--ok); }
  .cbtn.link { border: none; color: var(--accent2); text-decoration: underline; padding: 6px 4px; }
  .tips { margin: 8px 0 0; padding-left: 18px; color: #ffd88a; font-size: 13px; }
  .tips li { margin: 2px 0; }
  .hunks { margin-top: 10px; }
  .hunk { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; margin-bottom: 8px; }
  .hunk .cols { display: grid; grid-template-columns: 1fr 1fr; }
  .hunk .colhead { font-size: 12px; color: var(--dim); padding: 4px 10px; background: var(--card2); }
  .hunk pre.col { margin: 0; padding: 8px 10px; font-family: Consolas, monospace; font-size: 12.5px; white-space: pre-wrap; max-height: 240px; overflow: auto; }
  .hunk pre.ours { background: #131f38; color: #bcd4ff; border-right: 1px solid var(--line); }
  .hunk pre.theirs { background: #0f2a20; color: #b6f0cd; }
  .cpanel .cfoot { display: flex; gap: 10px; align-items: center; margin-top: 6px; }
  .size { color: var(--dim); font-size: 12px; margin-left: 6px; white-space: nowrap; }
  .j-adopt { background: #123f2e; color: #6ee7a8; }
  .j-caution { background: #4a3410; color: var(--warn); }
  .j-review { background: #4a1a22; color: #ff8a9b; }
  .diffbox { margin-top: 4px; }
  pre.diffstat {
    margin: 0 0 6px; padding: 8px 10px; background: #0f1420; border: 1px solid var(--line);
    border-radius: 8px; font-family: Consolas, monospace; font-size: 12px; color: #9fb4e0;
    white-space: pre-wrap; max-height: 170px; overflow: auto;
  }
  pre.diffpatch {
    margin: 0; padding: 10px; background: #0a0e1a; border: 1px solid var(--line);
    border-radius: 8px; font-family: Consolas, monospace; font-size: 12.5px; color: #cfe0ff;
    white-space: pre; overflow: auto; max-height: 440px;
  }
  .diffsum { font-size: 13px; color: var(--dim); margin-bottom: 6px; }
  .diffsum .p { color: #6ee7a8; } .diffsum .m { color: #ff8a9b; }
  .diffpatch .dline { display: block; }
  .diffpatch .add { background: rgba(74,222,128,.13); color: #9ff0bb; }
  .diffpatch .del { background: rgba(255,107,129,.13); color: #ff9aab; }
  .diffpatch .hunk { background: #1b2440; color: #8fb0ff; }
  .diffpatch .fhead { color: #ffd86b; font-weight: 700; margin-top: 4px; }
  .diffpatch .meta { color: #6b7aa3; }
  .tabs { display: flex; gap: 8px; padding: 0 24px 10px; }
  .tabs button { background: var(--card); border: 1px solid var(--line); color: var(--dim); font-weight: 700; }
  .tabs button.on { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #06101f; border: none; }
  .tabs button b { margin-left: 6px; opacity: .85; }
  body.view-ign .pend-only { display: none !important; }
  .skipbtn, .restorebtn {
    padding: 3px 10px; font-size: 12px; border-radius: 7px; background: transparent;
    border: 1px solid var(--line); color: var(--dim); white-space: nowrap;
  }
  .skipbtn:hover { border-color: var(--warn); color: var(--warn); }
  .restorebtn { border-color: var(--accent); color: var(--accent2); }
  .orphan { color: #ff8a9b; font-weight: 700; }
  .item.ign .hash { color: var(--dim); }
  .ign-src { color: var(--dim); font-size: 12px; white-space: nowrap; }
</style>
</head>
<body>
<header>
  <h1>上游提交同步<span class="sub" id="rangeSub">runhey/OnmyojiAutoScript · dev → mine</span></h1>
  <div class="stats" id="stats">加载中…</div>
</header>

<section class="toolbar">
  <div class="row">
    <label>数据源 <input id="repoUrl" placeholder="仓库地址（留空 = runhey 默认）"></label>
    <select id="repoBranch" title="数据源分支"><option value="dev">dev</option></select>
    <button id="btnLoadBranches" class="ghost">加载分支</button>
    <button id="btnConnect">连接并比对</button>
    <span class="csub" id="srcStatus"></span>
  </div>
  <div class="row">
    <label>时间范围 <input id="since" value="2 months ago"></label>
    <button id="btnRefresh">重新生成清单</button>
    <button id="btnFetch" class="ghost">拉取上游最新 (fetch)</button>
  </div>
  <div class="row pend-only">
    <input id="q" placeholder="搜索：关键字 / hash / 模块">
    <div class="chips" id="typeChips"></div>
    <select id="risk">
      <option value="all">全部风险</option>
      <option value="hide-shared">隐藏 ⚠ 高风险</option>
      <option value="isolated">仅 isolated</option>
    </select>
    <select id="level" title="按取舍建议筛选">
      <option value="all">全部建议</option>
      <option value="adopt">✓ 仅建议采用</option>
      <option value="hide-review">隐藏 🛑 建议评估</option>
    </select>
    <select id="module"><option value="">全部模块</option></select>
    <label class="toggle"><input type="checkbox" id="orig"> 显示英文原文</label>
    <label class="toggle"><input type="checkbox" id="online" checked> 联网翻译</label>
    <span class="csub" id="trStatus"></span>
  </div>
  <div class="row pend-only">
    <button id="btnSelAll" class="ghost">全选(当前筛选)</button>
    <button id="btnClear" class="ghost">清空选择</button>
    <button id="btnPrecheck">冲突预检(已选)</button>
    <button id="btnAdvise" class="ghost" title="逐条模拟 cherry-pick 预判冲突 + 统计本地定制度，全量分析较慢">AI 顾问(全量分析)</button>
    <button id="btnSkipSel" class="ghost" title="把已勾选的提交标记为「跳过」，移入「已排除·跳过」页">跳过所选</button>
    <span class="csub" id="adviseStatus"></span>
    <span class="sel-count">已选 <b id="selCount">0</b> 条</span>
  </div>
</section>

<div class="tabs">
  <button id="tabPend" class="on">待同步 <b id="tabPendN">0</b></button>
  <button id="tabIgn">已排除·跳过 <b id="tabIgnN">0</b></button>
</div>

<div class="banner" id="banner"></div>

<section class="cpanel pend-only" id="cpanel" style="display:none"></section>

<main id="list"><div class="empty">加载中…</div></main>

<footer class="pend-only">
  <input id="branch" placeholder="sync 分支名（留空自动生成）">
  <button id="btnApply" class="primary">执行同步 (apply)</button>
</footer>
<section class="logwrap"><pre id="log">就绪。</pre></section>

<script>
const TYPES = ["feat", "fix", "refactor", "perf", "chore", "docs", "style", "test", "build", "ci", "revert", "other"];
let commits = [];
let applied = [];       // 「已并入本地」（patch-id 等价，只读）
let ignored = [];       // 「已跳过」（持久化，可恢复）
let view = "pend";      // "pend" = 待同步；"ign" = 已排除·跳过
let selected = new Set();
let chosenTypes = new Set();
let collapsed = new Set();
let pc = {};          // 冲突预检结果: hash -> "ok" | "conflict" | "error"
let pcBusy = false;
let adviseBusy = false; // AI 顾问（全量 advise）进行中
let showOriginal = false;
let onlineTr = true;            // 联网翻译开关
let trCache = {};               // 英文描述 -> 联网中文
let trFail = new Set();         // 联网翻译失败的描述，避免重复请求
let trBusy = false;
let conflict = null;  // {commit, subject, branch, files, choices, details}
let diffCache = {};   // hash -> 改动预览结果（按需加载后缓存）

const $ = id => document.getElementById(id);
const logEl = $("log");
function log(msg) { logEl.textContent += "\n" + msg; logEl.scrollTop = logEl.scrollHeight; }
function setLog(msg) { logEl.textContent = msg; }
function esc(s) { return (s || "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

// 数据源：留空地址 = 默认 runhey/dev（后端不传自定义参数）
function srcUrl() { return ($("repoUrl").value || "").trim(); }
function srcBranch() { return ($("repoBranch").value || "").trim(); }
function sourceParams() {
  return { since: $("since").value.trim() || "2 months ago",
           remote_url: srcUrl(), remote_branch: srcBranch() };
}
function setSrcStatus(s) { const el = $("srcStatus"); if (el) el.textContent = s || ""; }

// 通过后端 git ls-remote 拉取该仓库的分支列表，填充下拉
async function loadBranches() {
  const url = srcUrl();
  if (!url) { setLog("请先填写仓库地址（留空即用默认 runhey）。"); return; }
  setSrcStatus("加载分支中…");
  try {
    const r = await fetch("/api/branches", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await r.json();
    if (data.error) { setSrcStatus("加载失败"); setLog("分支加载失败：\n" + data.error); return; }
    const list = data.branches || [];
    const sel = $("repoBranch");
    const keep = sel.value;
    sel.innerHTML = "";
    list.forEach(b => {
      const o = document.createElement("option");
      o.value = b; o.textContent = b;
      sel.appendChild(o);
    });
    if (keep && list.includes(keep)) sel.value = keep;
    else if (data.default && list.includes(data.default)) sel.value = data.default;
    setSrcStatus(`已加载 ${list.length} 个分支`);
    log(`分支列表（${list.length}）：${list.join(", ")}`);
  } catch (e) {
    setSrcStatus("加载异常");
    setLog("分支加载异常：" + e);
  }
}

// 标题显示文本：优先联网译文，其次离线词表，最后原文
function subjectText(c) {
  if (showOriginal) return c.subject;
  const zh = trCache[c.desc];
  if (c.head_zh) return zh ? `${c.head_zh}: ${zh}` : (c.subject_zh || c.subject);
  return zh || c.subject_zh || c.subject;
}

function setTrStatus(s) { const el = $("trStatus"); if (el) el.textContent = s || ""; }

// 异步联网补全译文：首屏先用离线结果渲染，翻译好一批就刷新一批
async function translateMissing() {
  if (!onlineTr || trBusy) return;
  trBusy = true;
  const BATCH = 24;
  try {
    while (true) {
      const pending = [...new Set(commits.map(c => c.desc).filter(d => d && !(d in trCache) && !trFail.has(d)))];
      if (!pending.length) break;
      const batch = pending.slice(0, BATCH);
      setTrStatus(`联网翻译中… 剩余 ${pending.length} 条`);
      let tr = {};
      try {
        const r = await fetch("/api/translate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texts: batch })
        });
        tr = (await r.json()).translations || {};
      } catch (e) { break; }  // 网络异常：保留离线结果，不再重试
      for (const [k, v] of Object.entries(tr)) trCache[k] = v;
      // 本批未译出的标记为失败，避免下一轮重复请求（也保证循环一定会结束）
      batch.filter(d => !(d in tr)).forEach(d => trFail.add(d));
      render();
    }
  } finally {
    trBusy = false;
    setTrStatus("");
  }
  render();
}
function showBanner(text, kind) {
  const b = $("banner");
  if (!text) { b.className = "banner"; b.textContent = ""; return; }
  b.textContent = text; b.className = "banner show " + kind;
}
function pcState(hash) { const v = pc[hash]; return v ? (v.status || v) : null; }
function pcFiles(hash) { const v = pc[hash]; return (v && v.files) || []; }
function pcBadge(hash) {
  const s = pcState(hash);
  if (s === "ok") return '<span class="badge pc-ok">✓ 可应用</span>';
  if (s === "conflict") {
    const files = pcFiles(hash);
    const tip = files.length ? "冲突文件：\n" + files.join("\n") : "会与本地冲突";
    return `<span class="badge pc-conflict" title="${esc(tip)}">⛔ 冲突${files.length ? " " + files.length + " 文件" : ""}</span>`;
  }
  if (s === "error") return '<span class="badge pc-conflict">? 未知</span>';
  return "";
}

// 取舍建议徽章：中文结论 + 悬停理由；改动规模文本
const JUDGE_LABEL = { adopt: "✓ 建议采用", caution: "⚠ 采用但需实测", review: "🛑 建议单独评估" };
function judgeBadge(c) {
  if (!c.level) return "";
  const tip = (c.reasons || []).join("\n");
  const label = c.judge || JUDGE_LABEL[c.level] || c.level;
  return `<span class="badge j-${c.level}" title="${esc(tip)}">${esc(label)}</span>`;
}
function sizeText(c) {
  if (c.changed == null) return "";
  return `<span class="size">+${c.adds}/-${c.dels} · ${c.changed}文件</span>`;
}

// 把 patch 按行着色：新增绿、删除红、hunk 头灰蓝、文件头加粗，比裸 ++/-- 更直观
function renderDiff(patch) {
  return (patch || "").split("\n").map(ln => {
    let cls = "dctx";
    if (/^(diff --git|new file|deleted file|rename |copy )/.test(ln)) cls = "fhead";
    else if (ln.startsWith("@@")) cls = "hunk";
    else if (/^(index |similarity|\+\+\+|---|\\ )/.test(ln)) cls = "meta";
    else if (ln.startsWith("+")) cls = "add";
    else if (ln.startsWith("-")) cls = "del";
    return `<span class="dline ${cls}">${esc(ln) || "&nbsp;"}</span>`;
  }).join("");
}

function buildTypeChips() {
  const box = $("typeChips");
  box.innerHTML = "";
  TYPES.forEach(t => {
    const counts = commits.filter(c => c.type === t).length;
    if (!counts) return;
    const el = document.createElement("span");
    el.className = "chip";
    el.dataset.type = t;
    el.textContent = t + " " + counts;
    el.onclick = () => {
      if (chosenTypes.has(t)) chosenTypes.delete(t); else chosenTypes.add(t);
      el.classList.toggle("on");
      render();
    };
    box.appendChild(el);
  });
}

function buildModuleSelect() {
  const mods = [...new Set(commits.map(c => c.module))].sort((a, b) => a.localeCompare(b, "zh"));
  const zhOf = m => (commits.find(c => c.module === m) || {}).module_zh || m;
  const sel = $("module");
  sel.innerHTML = '<option value="">全部模块</option>' + mods.map(m => {
    const label = showOriginal ? m : `${zhOf(m)} (${m})`;
    return `<option value="${esc(m)}">${esc(label)}</option>`;
  }).join("");
}

function filtered() {
  const q = $("q").value.trim().toLowerCase();
  const risk = $("risk").value;
  const mod = $("module").value;
  const lvl = $("level").value;
  return commits.filter(c => {
    if (q && !(String(subjectText(c)).toLowerCase().includes(q)
               || c.subject.toLowerCase().includes(q)
               || c.hash.includes(q) || c.module.toLowerCase().includes(q)
               || (c.module_zh || "").toLowerCase().includes(q))) return false;
    if (chosenTypes.size && !chosenTypes.has(c.type)) return false;
    if (risk === "hide-shared" && c.risk === "shared") return false;
    if (risk === "isolated" && c.risk !== "isolated") return false;
    if (lvl === "adopt" && c.level !== "adopt") return false;
    if (lvl === "hide-review" && c.level === "review") return false;
    if (mod && c.module !== mod) return false;
    return true;
  }).sort((a, b) => b.date.localeCompare(a.date) || b.hash.localeCompare(a.hash));
}

function render() {
  if (view === "ign") { renderIgnored(); return; }
  const list = filtered();
  const host = $("list");
  if (!list.length) { host.innerHTML = '<div class="empty">没有匹配的提交</div>'; updateCount(); return; }
  const groups = {};
  list.forEach(c => (groups[c.module] = groups[c.module] || []).push(c));
  const names = Object.keys(groups).sort((a, b) => groups[b].length - groups[a].length || a.localeCompare(b, "zh"));
  host.innerHTML = "";
  names.forEach(name => {
    const items = groups[name];
    const selNum = items.filter(c => selected.has(c.hash)).length;
    const allSel = selNum === items.length;
    const div = document.createElement("div");
    div.className = "module" + (collapsed.has(name) ? " collapsed" : "");
    div.innerHTML = `
      <div class="mhead">
        <input type="checkbox" title="全选本模块" data-mod="${esc(name)}" ${allSel ? "checked" : ""}>
        <span class="mtitle" title="${esc(name)}">${esc(showOriginal ? name : (items[0].module_zh || name))}</span>
        <span class="mcount">${items.length} 条 · 已选 ${selNum}</span>
        <span class="mhint">${allSel ? "取消本模块" : "全选本模块"}</span>
        <span class="caret">▾</span>
      </div>
      <div class="rows"></div>`;
    const headBox = div.querySelector(".mhead input");
    headBox.indeterminate = selNum > 0 && !allSel;
    const rows = div.querySelector(".rows");
    items.forEach(c => {
      const wrap = document.createElement("div");
      wrap.className = "cwrap";
      const row = document.createElement("div");
      row.className = "item";
      const warn = c.risk === "shared" ? '<span class="badge b-warn" title="涉及共享基础设施文件，冲突风险高">⚠ 高风险</span>' : "";
      row.innerHTML = `
        <input type="checkbox" ${selected.has(c.hash) ? "checked" : ""}>
        <span class="hash">${c.hash.slice(0, 8)}</span>
        <span class="subject" title="${esc(c.subject)}"><span class="badge b-${TYPES.includes(c.type) ? c.type : "other"}">${c.type}</span>${warn}${judgeBadge(c)}${pcBadge(c.hash)}${esc(subjectText(c))}${sizeText(c)}</span>
        <span class="date">${c.date}</span>
        <button class="skipbtn" title="跳过此提交（移入「已排除·跳过」页，不再出现在待同步列表）">跳过</button>`;
      row.querySelector("input").onchange = e => {
        if (e.target.checked) selected.add(c.hash); else selected.delete(c.hash);
        syncModuleHead(div, items); updateCount();
      };
      row.querySelector(".skipbtn").onclick = () => doIgnore([c.hash]);
      wrap.appendChild(row);

      // 改动文件清单（可展开）；冲突文件标红并默认展开
      const files = c.files || [];
      const cf = pcFiles(c.hash);
      if (files.length || cf.length) {
        const cfset = new Set(cf);
        const list = files.map(f =>
          `<div class="fpath${cfset.has(f) ? " cf" : ""}">${cfset.has(f) ? "⛔ " : ""}${esc(f)}</div>`).join("");
        const extra = cf.filter(f => !files.includes(f))
          .map(f => `<div class="fpath cf">⛔ ${esc(f)}</div>`).join("");
        const open = cf.length > 0;
        const fdiv = document.createElement("div");
        fdiv.className = "files" + (open ? "" : " collapsed");
        fdiv.innerHTML =
          `<span class="ftoggle"><span class="arrow">${open ? "▾" : "▸"}</span> 更新文件 ${files.length} 个` +
          (cf.length ? ` · <span style="color:#ff8a9b">⛔ 冲突 ${cf.length}</span>` : "") +
          `</span><div class="flist">${list}${extra}</div>`;
        fdiv.querySelector(".ftoggle").onclick = () => {
          fdiv.classList.toggle("collapsed");
          fdiv.querySelector(".arrow").textContent =
            fdiv.classList.contains("collapsed") ? "▸" : "▾";
        };
        wrap.appendChild(fdiv);
      }

      // 改动预览：点击「查看改动」按需拉取 diff，无需切到终端
      const ddiv = document.createElement("div");
      ddiv.className = "files";
      ddiv.innerHTML = `<span class="ftoggle diffToggle"><span class="arrow">▸</span> 查看改动</span>`
        + `<div class="diffbox" style="display:none"></div>`;
      const dbox = ddiv.querySelector(".diffbox");
      const dtog = ddiv.querySelector(".diffToggle");
      dtog.onclick = async () => {
        if (dbox.style.display !== "none") {
          dbox.style.display = "none";
          dtog.querySelector(".arrow").textContent = "▸";
          return;
        }
        dbox.style.display = "block";
        dtog.querySelector(".arrow").textContent = "▾";
        if (diffCache[c.hash] === undefined) {
          dbox.innerHTML = '<div class="csub loading">加载中…</div>';
          try {
            const r = await fetch("/api/show", {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ commit: c.hash })
            });
            diffCache[c.hash] = (await r.json()).result || {};
          } catch (e) {
            diffCache[c.hash] = { status: "error", message: String(e) };
          }
        }
        const d = diffCache[c.hash];
        if (!d || d.status === "error") {
          dbox.innerHTML = `<div class="csub">加载失败：${esc((d && d.message) || "未知错误")}</div>`;
          return;
        }
        const summary = `<div class="diffsum">共改动 <b>${c.changed}</b> 个文件 · ` +
          `新增 <b class="p">+${c.adds}</b> 行 · 删除 <b class="m">-${c.dels}</b> 行</div>`;
        const stat = d.stat ? `<pre class="diffstat">${esc(d.stat)}</pre>` : "";
        const patch = d.patch ? `<pre class="diffpatch">${renderDiff(d.patch)}</pre>`
                              : '<div class="csub">无差异内容</div>';
        const more = d.truncated ? '<div class="csub">（差异过大，已截断显示）</div>' : "";
        dbox.innerHTML = summary + stat + patch + more;
      };
      wrap.appendChild(ddiv);
      rows.appendChild(wrap);
    });
    const setModule = on => {
      items.forEach(c => on ? selected.add(c.hash) : selected.delete(c.hash));
      rows.querySelectorAll("input").forEach(b => b.checked = on);
      syncModuleHead(div, items);
      updateCount();
    };
    headBox.onchange = e => setModule(e.target.checked);
    const hint = div.querySelector(".mhint");
    hint.onclick = e => { e.stopPropagation(); setModule(!items.every(c => selected.has(c.hash))); };
    div.querySelector(".mhead").addEventListener("click", e => {
      if (e.target === headBox || e.target === hint) return;
      if (e.target.classList.contains("mcount") || e.target.classList.contains("mtitle")) {
        $("module").value = name; render(); return;
      }
      collapsed.has(name) ? collapsed.delete(name) : collapsed.add(name);
      div.classList.toggle("collapsed");
    });
    host.appendChild(div);
  });
  updateCount();
}

function syncModuleHead(div, items) {
  const selNum = items.filter(c => selected.has(c.hash)).length;
  const box = div.querySelector(".mhead input");
  box.checked = selNum === items.length;
  box.indeterminate = selNum > 0 && selNum < items.length;
  div.querySelector(".mcount").textContent = `${items.length} 条 · 已选 ${selNum}`;
  div.querySelector(".mhint").textContent = selNum === items.length ? "取消本模块" : "全选本模块";
}

function updateCount() {
  $("selCount").textContent = selected.size;
  const list = filtered();
  const shared = commits.filter(c => c.risk === "shared").length;
  const lv = k => commits.filter(c => c.level === k).length;
  $("stats").innerHTML = `待同步 <b>${commits.length}</b> 条 · 当前筛选 <b>${list.length}</b> 条 · ` +
    `建议采用 <b>${lv("adopt")}</b> · 需实测 <b>${lv("caution")}</b> · 建议评估 <b>${lv("review")}</b> · ` +
    `⚠ 高风险 <b>${shared}</b> 条 · 模块 <b>${new Set(commits.map(c => c.module)).size}</b> 个`;
}

// ---------------------------------------------------------------------------
// 「已排除·跳过」视图（与待同步列表共用 <main>，按 view 分派渲染）
// ---------------------------------------------------------------------------
function appliedSet() { return new Set(applied.map(c => c.hash)); }
// 已跳过清单里若同时是「已并入本地」，以只读的后者为准，避免重复展示
function ignoredView() { const a = appliedSet(); return ignored.filter(c => !a.has(c.hash)); }

function updateTabCounts() {
  $("tabPendN").textContent = commits.length;
  $("tabIgnN").textContent = ignoredView().length + applied.length;
}

function setView(v) {
  view = v;
  document.body.classList.toggle("view-ign", v === "ign");
  $("tabPend").classList.toggle("on", v === "pend");
  $("tabIgn").classList.toggle("on", v === "ign");
  if (v === "ign") $("cpanel").style.display = "none";
  else if (conflict) renderConflict();
  render();
}

// 跳过：移入「已排除·跳过」。成功后就地更新（不整页重载，保留勾选与预检状态）
async function doIgnore(hashes) {
  if (!hashes || !hashes.length) return;
  const p = sourceParams();
  setLog(`正在跳过 ${hashes.length} 个提交…`);
  try {
    const r = await fetch("/api/ignore", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hashes, remote_url: p.remote_url, remote_branch: p.remote_branch })
    });
    const data = await r.json();
    if ((data.result || {}).status !== "ok") {
      setLog("跳过失败：\n" + (data.output || JSON.stringify(data)));
      return;
    }
    const set = new Set(hashes);
    const moved = commits.filter(c => set.has(c.hash));
    commits = commits.filter(c => !set.has(c.hash));
    moved.forEach(c => ignored.push({
      hash: c.hash, subject: c.subject, date: c.date, module: c.module, type: c.type,
      source: "手动跳过", ignored_at: "", reason: "manual", present: true,
      head_zh: c.head_zh, desc: c.desc, subject_zh: c.subject_zh, module_zh: c.module_zh
    }));
    set.forEach(h => { selected.delete(h); delete pc[h]; });
    buildTypeChips(); buildModuleSelect(); updateTabCounts(); render();
    log(`已跳过 ${moved.length} 条，可在「已排除·跳过」页恢复。`);
  } catch (e) {
    setLog("跳过异常：" + e);
  }
}

// 恢复：从「已跳过」移回待同步（重新加载清单后回到列表）
async function doUnignore(hash) {
  setLog("正在恢复…");
  try {
    const r = await fetch("/api/unignore", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hashes: [hash] })
    });
    const data = await r.json();
    if ((data.result || {}).status !== "ok") {
      setLog("恢复失败：\n" + (data.output || JSON.stringify(data)));
      return;
    }
    ignored = ignored.filter(c => c.hash !== hash);
    updateTabCounts(); render();
    log("已恢复 1 条，重新加载清单后回到待同步列表。");
  } catch (e) {
    setLog("恢复异常：" + e);
  }
}

// 扁平分组渲染（不做勾选/折叠 diff）；「我跳过的」可逐条恢复，「已并入本地」默认折叠
function renderIgnored() {
  const host = $("list");
  host.innerHTML = "";
  const igs = ignoredView();
  if (!igs.length && !applied.length) {
    host.innerHTML = '<div class="empty">没有已排除 / 已并入的提交</div>';
    return;
  }
  const section = (title, items, restore, startCollapsed) => {
    const div = document.createElement("div");
    div.className = "module" + (startCollapsed ? " collapsed" : "");
    div.innerHTML = `<div class="mhead"><span class="mtitle">${title}</span>` +
      `<span class="mcount">${items.length} 条${startCollapsed ? " · 点击展开" : ""}</span>` +
      `<span class="caret">▾</span></div><div class="rows"></div>`;
    const rows = div.querySelector(".rows");
    if (!items.length) rows.innerHTML = '<div class="empty">（无）</div>';
    items.forEach(c => {
      const row = document.createElement("div");
      row.className = "item ign";
      const orphan = c.present === false
        ? '<span class="badge b-warn" title="该 hash 已不在当前上游窗口（可能被 rebase 或移除）">哈希已不存在</span>'
        : "";
      const src = `<span class="ign-src" title="来源">${esc(c.source || "")}</span>`;
      const act = restore
        ? '<button class="restorebtn" title="恢复（重新出现在待同步列表）">恢复</button>' : "";
      row.innerHTML = `<span class="hash">${(c.hash || "").slice(0, 8)}</span>` +
        `<span class="subject"><span class="badge b-${TYPES.includes(c.type) ? c.type : "other"}">${c.type || "other"}</span>${orphan}${esc(subjectText(c))}</span>` +
        src + `<span class="date">${c.date || ""}</span>` + act;
      if (restore) row.querySelector(".restorebtn").onclick = () => doUnignore(c.hash);
      rows.appendChild(row);
    });
    div.querySelector(".mhead").onclick = () => div.classList.toggle("collapsed");
    host.appendChild(div);
  };
  section("我跳过的", igs, true, false);
  section("已并入本地（内容等价，只读）", applied, false, true);
}

async function loadCommits(refresh) {
  setLog(refresh ? "正在拉取上游并生成清单…" : "正在生成清单…");
  $("list").innerHTML = '<div class="empty loading">加载中…</div>';
  try {
    const p = sourceParams();
    const q = new URLSearchParams({ since: p.since, refresh: refresh ? 1 : 0 });
    if (p.remote_url) { q.set("remote_url", p.remote_url); q.set("remote_branch", p.remote_branch); }
    const r = await fetch(`/api/commits?${q.toString()}`);
    const data = await r.json();
    if (data.error) { setLog("加载失败：\n" + data.error); $("list").innerHTML = '<div class="empty">加载失败</div>'; return; }
    setSrcStatus(p.remote_url ? "已连接自定义源" : "");
    commits = data.commits || [];
    applied = data.applied || [];
    ignored = data.ignored || [];
    $("rangeSub").textContent = data.range || "runhey/OnmyojiAutoScript · dev → mine";
    selected.clear();
    pc = {};
    diffCache = {};
    conflict = null; renderConflict();
    showBanner("", "");
    buildTypeChips(); buildModuleSelect(); updateTabCounts(); render();
    setLog(`加载完成：${commits.length} 条待同步提交。\n勾选后点「冲突预检」可预判冲突，或直接「执行同步」。`);
    translateMissing();
  } catch (e) {
    setLog("加载异常：" + e);
    $("list").innerHTML = '<div class="empty">加载异常</div>';
  }
}

async function runPrecheck() {
  if (pcBusy) return;
  if (!selected.size) { setLog("未选择任何提交。"); return; }
  pcBusy = true; $("btnPrecheck").disabled = true;
  const hashes = [...selected];
  setLog(`冲突预检中… 共 ${hashes.length} 个提交（仅模拟，不改动工作区）`);
  try {
    const r = await fetch("/api/precheck", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hashes })
    });
    const data = await r.json();
    const results = data.results || {};
    pc = Object.assign({}, pc, results);
    const vals = Object.values(results);
    const bad = vals.filter(v => (v.status || v) === "conflict").length;
    const ok = vals.filter(v => (v.status || v) === "ok").length;
    const cf = [...new Set(vals.filter(v => (v.status || v) === "conflict")
      .flatMap(v => v.files || []))];
    render();
    if (bad > 0) {
      showBanner(`⚠ 预检：${bad} 个提交会冲突（涉及 ${cf.length} 个文件），${ok} 个可干净应用。建议剔除冲突项，或执行后按日志手工解决。`, "warn");
      if (cf.length) log("冲突文件：\n  " + cf.join("\n  "));
    } else {
      showBanner(`✓ 预检：${ok} 个提交均可干净应用，可以执行同步。`, "ok");
    }
    log(`预检完成：冲突 ${bad} 个，可应用 ${ok} 个。`);
  } catch (e) {
    setLog("预检异常：" + e);
  } finally {
    pcBusy = false; $("btnPrecheck").disabled = false;
  }
}

// AI 顾问：全量分析（逐条模拟 cherry-pick 预判冲突 + 统计本地定制度），
// 用返回结果就地刷新列表的冲突徽章与取舍建议；已勾选的提交保持不变。
async function runAdvise() {
  if (adviseBusy) return;
  const p = sourceParams();
  const since = p.since;
  adviseBusy = true; $("btnAdvise").disabled = true;
  const t0 = Date.now();
  const elapsed = () => ((Date.now() - t0) / 1000).toFixed(1);
  $("adviseStatus").textContent = `AI 顾问分析中… 已耗时 ${elapsed()}s`;
  const timer = setInterval(() => {
    $("adviseStatus").textContent = `AI 顾问分析中… 已耗时 ${elapsed()}s`;
  }, 500);
  showBanner("", "");
  setLog("AI 顾问分析中…（逐条模拟 cherry-pick + 统计本地定制度，全量较慢，请勿关闭页面）");
  try {
    const r = await fetch("/api/advise", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ since, remote_url: p.remote_url, remote_branch: p.remote_branch })
    });
    const data = await r.json();
    if (data.error) {
      $("adviseStatus").textContent = "分析失败";
      setLog("AI 顾问分析失败：\n" + data.error +
        "\n提示：若上游数据未拉取，请先点「拉取上游最新 (fetch)」。");
      return;
    }
    commits = data.commits || [];
    if (data.range) $("rangeSub").textContent = data.range;
    // 用顾问结论覆盖冲突预检状态（advise 已含逐条 conflict 结果）
    pc = {};
    commits.forEach(c => { if (c.conflict) pc[c.hash] = c.conflict; });
    diffCache = {};
    buildTypeChips(); buildModuleSelect(); updateTabCounts(); render();
    const cf = commits.filter(c => pcState(c.hash) === "conflict").length;
    const lv = k => commits.filter(c => c.level === k).length;
    showBanner(`✓ AI 顾问完成：${commits.length} 条 · 预判冲突 ${cf} 条 · ` +
      `建议采用 ${lv("adopt")} · 需实测 ${lv("caution")} · 建议评估 ${lv("review")}。`,
      cf ? "warn" : "ok");
    setLog(`AI 顾问分析完成，用时 ${elapsed()}s。\n` +
      `  预判冲突 ${cf} 条，建议采用 ${lv("adopt")} / 需实测 ${lv("caution")} / 建议评估 ${lv("review")}。\n` +
      `列表已按顾问结论刷新（冲突徽章 + 取舍建议），已勾选的提交保持不变。`);
    $("adviseStatus").textContent = `完成（${elapsed()}s）`;
  } catch (e) {
    $("adviseStatus").textContent = "异常";
    setLog("AI 顾问异常：" + e);
  } finally {
    clearInterval(timer);
    adviseBusy = false; $("btnAdvise").disabled = false;
  }
}

async function doApply() {
  if (conflict) { log("当前有未解决的冲突：请先在上方「冲突处理」面板中选择「继续」或「放弃」。"); return; }
  if (!selected.size) { log("未选择任何提交。"); return; }
  const hashes = [...selected];
  const branch = $("branch").value.trim();
  const p = sourceParams();
  const pre = hashes.filter(h => pcState(h) === "conflict").length;
  if (pre > 0) {
    showBanner(`注意：已选中有 ${pre} 个预检会冲突的提交，执行时会暂停并让你逐文件决定。`, "warn");
  }
  $("btnApply").disabled = true;
  setLog(`正在执行同步，共 ${hashes.length} 个提交…\n（cherry-pick 期间请勿关闭本页）`);
  try {
    const r = await fetch("/api/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hashes, branch, remote_url: p.remote_url, remote_branch: p.remote_branch })
    });
    const data = await r.json();
    const out = data.output || "(无输出)";
    const res = data.result || {};
    setLog(out + "\n\n[退出码] " + data.code);
    if (res.status === "conflict") {
      showConflict(res);
    } else if (res.status === "done" || data.code === 0) {
      conflict = null; renderConflict();
      showBanner("✓ 同步完成，请在 sync 分支上测试无误后合并回 mine。", "ok");
    } else {
      showBanner("⛔ 同步中止，详见下方日志。", "warn");
    }
  } catch (e) {
    setLog("执行异常：" + e);
  } finally {
    $("btnApply").disabled = !!conflict;
  }
}

function showConflict(res) {
  conflict = {
    commit: res.commit || "", subject: res.subject || "",
    branch: res.branch || "", files: res.files || [], choices: {}, details: {}
  };
  renderConflict();
  showBanner("⛔ 发生冲突：请在下方逐文件选择「保留本地」或「采用上游」，并可查看差异与中文分析。", "warn");
}

function renderConflict() {
  const el = $("cpanel");
  $("btnApply").disabled = !!conflict;
  if (!conflict) { el.style.display = "none"; el.innerHTML = ""; return; }
  el.style.display = "block";
  const files = conflict.files;
  let html = `<h2>冲突处理</h2>
    <div class="csub">提交 <b>${esc(conflict.commit)}</b> ${esc(conflict.subject)} · 共 <b>${files.length}</b> 个文件冲突 · 分支 <b>${esc(conflict.branch)}</b></div>`;
  files.forEach(f => {
    const ch = conflict.choices[f];
    const d = conflict.details[f];
    html += `<div class="cfile">
      <div class="cpath">${esc(f)}</div>
      <div class="crow">
        <button class="cbtn ${ch === "ours" ? "on" : ""}" data-f="${esc(f)}" data-c="ours">保留本地 (mine)</button>
        <button class="cbtn theirs ${ch === "theirs" ? "on" : ""}" data-f="${esc(f)}" data-c="theirs">采用上游 (dev)</button>
        <button class="cbtn link" data-detail="${esc(f)}">查看差异与中文分析</button>
      </div>`;
    if (d) {
      if (d.analysis && d.analysis.length) {
        html += `<ul class="tips">${d.analysis.map(t => `<li>${esc(t)}</li>`).join("")}</ul>`;
      }
      if (d.binary) {
        html += `<div class="csub">该文件为二进制，无法显示行级差异。</div>`;
      } else if (d.hunks && d.hunks.length) {
        html += `<div class="hunks">`;
        d.hunks.forEach(h => {
          html += `<div class="hunk"><div class="cols">
            <div class="colhead">本地 (mine)</div><div class="colhead">上游 (dev)</div>
            <pre class="col ours">${esc(h.ours.join("\n"))}</pre>
            <pre class="col theirs">${esc(h.theirs.join("\n"))}</pre>
          </div></div>`;
        });
        html += `</div>`;
      } else {
        html += `<div class="csub">无行级冲突标记（可能是删除/修改冲突）。</div>`;
      }
    }
    html += `</div>`;
  });
  const missing = files.filter(f => !conflict.choices[f]);
  html += `<div class="cfoot">
    <button class="primary" id="btnContinue">继续 (resolve)</button>
    <button class="cbtn" id="btnAbort">放弃本次同步 (abort)</button>
    <span class="csub">${missing.length ? `还有 ${missing.length} 个文件未选择` : "已全部选择，可继续"}</span>
  </div>`;
  el.innerHTML = html;

  el.querySelectorAll(".cbtn[data-c]").forEach(b => b.onclick = () => {
    conflict.choices[b.dataset.f] = b.dataset.c;
    renderConflict();
  });
  el.querySelectorAll(".cbtn[data-detail]").forEach(b => b.onclick = async () => {
    const f = b.dataset.detail;
    b.textContent = "加载中…"; b.disabled = true;
    try {
      const r = await fetch("/api/conflict-detail", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file: f })
      });
      const data = await r.json();
      conflict.details[f] = data.result || {};
    } catch (e) {
      conflict.details[f] = { analysis: ["加载失败：" + e] };
    }
    renderConflict();
  });
  const cont = $("btnContinue");
  cont.disabled = missing.length > 0;
  cont.onclick = doResolve;
  $("btnAbort").onclick = doAbort;
}

async function doResolve() {
  if (!conflict) return;
  $("btnContinue").disabled = true;
  setLog("正在按你的选择处理冲突并继续 cherry-pick…");
  try {
    const r = await fetch("/api/resolve", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choices: conflict.choices })
    });
    const data = await r.json();
    const res = data.result || {};
    log(data.output || "");
    if (res.status === "done") {
      conflict = null; renderConflict();
      showBanner("✓ 冲突已全部处理，同步完成。请在 sync 分支测试无误后合并回 mine。", "ok");
    } else if (res.status === "conflict") {
      const branch = res.branch || conflict.branch;
      conflict = {
        commit: res.commit || "", subject: res.subject || "", branch,
        files: res.files || [], choices: {}, details: {}
      };
      renderConflict();
      showBanner("⛔ 又遇到新的冲突，请继续选择。", "warn");
    } else {
      showBanner("⛔ 处理失败：" + (res.message || data.output || ""), "warn");
    }
  } catch (e) {
    setLog("异常：" + e);
  }
}

async function doAbort() {
  if (!confirm("确定放弃本次同步？将中止 cherry-pick 并删除该 sync 分支。")) return;
  setLog("正在放弃本次同步…");
  try {
    const r = await fetch("/api/abort", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}"
    });
    const data = await r.json();
    log(data.output || "");
    conflict = null; renderConflict();
    showBanner("已放弃本次同步，分支已删除，回到 mine。", "ok");
  } catch (e) {
    setLog("异常：" + e);
  }
}

$("btnRefresh").onclick = () => loadCommits(false);
$("btnFetch").onclick = () => loadCommits(true);
$("btnLoadBranches").onclick = loadBranches;
$("btnConnect").onclick = () => loadCommits(true);
$("q").oninput = render;
$("risk").onchange = render;
$("level").onchange = render;
$("module").onchange = render;
$("btnSelAll").onclick = () => { filtered().forEach(c => selected.add(c.hash)); render(); };
$("btnClear").onclick = () => { selected.clear(); pc = {}; showBanner("", ""); render(); };
$("btnPrecheck").onclick = runPrecheck;
$("btnAdvise").onclick = runAdvise;
$("btnApply").onclick = doApply;
$("btnSkipSel").onclick = () => { if (!selected.size) { log("未选择任何提交。"); return; } doIgnore([...selected]); };
$("tabPend").onclick = () => setView("pend");
$("tabIgn").onclick = () => setView("ign");
$("orig").onchange = e => {
  showOriginal = e.target.checked;
  const v = $("module").value;
  buildModuleSelect();
  $("module").value = v;
  render();
};
$("online").onchange = e => {
  onlineTr = e.target.checked;
  if (onlineTr) { trFail.clear(); translateMissing(); }
  else { setTrStatus(""); render(); }
};

loadCommits(false);
</script>
</body>
</html>
"""


def run_sync(args, timeout=600):
    """调用 upstream_sync.py，返回 (returncode, output)"""
    # 子进程 stdout 是管道，Windows 中文环境默认 GBK；不强制 UTF-8 时
    # 打印 ⚠/✓/🛑 等符号会抛 UnicodeEncodeError，导致 fetch/emit 直接崩溃。
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, SYNC_SCRIPT, *args],
        cwd=REPO_ROOT, capture_output=True, encoding="utf-8",
        errors="replace", timeout=timeout, env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


# AI 顾问（advise）结果缓存：逐条 merge-tree 预检较慢，同一份上游数据重复点击应即时返回
# 键为 (since, remote_url, remote_branch)，换数据源后自动失效
_ADVISE_CACHE = {"key": None, "data": None}


def source_args(remote_url=None, remote_branch=None):
    """把自定义数据源参数拼成 run_sync 的前置参数（须放在子命令之前）。

    留空 remote_url 时不产出任何参数 → 走默认 upstream/dev，保持向后兼容。
    """
    args = []
    url = (remote_url or "").strip()
    if url:
        args += ["--remote-url", url]
        branch = (remote_branch or "").strip()
        if branch:
            args += ["--remote-branch", branch]
    return args


def _decorate_commits(commits):
    """补中文显示字段（标题拆分 + 离线词表），list / advise 两条路径共用。"""
    for c in commits:
        head, desc = split_subject(c["subject"])
        c["head_zh"] = head
        c["desc"] = desc
        c["subject_zh"] = translate_subject(c["subject"])
        c["module_zh"] = translate_module(c["module"])
    return commits


def _src_label(remote_url=None, remote_branch=None):
    """对比源的显示名：自定义源用「地址 · 分支」，默认仍显示 runhey/dev。"""
    url = (remote_url or "").strip()
    if url:
        return f"{url} · {(remote_branch or '').strip() or 'dev'}"
    return "runhey/OnmyojiAutoScript · upstream/dev"


def get_commits(since, refresh, remote_url=None, remote_branch=None):
    src = source_args(remote_url, remote_branch)
    if refresh:
        code, out = run_sync([*src, "--since", since, "fetch"])
        if code != 0:
            return {"error": out or f"fetch 失败（{code}）"}
        # 上游数据已更新，顾问结果作废
        _ADVISE_CACHE["key"] = None
        _ADVISE_CACHE["data"] = None
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        code, out = run_sync([*src, "--since", since, "list", "--json", "--out", tmp])
        if code != 0:
            return {"error": out or f"list 失败（{code}）"}
        with open(tmp, "r", encoding="utf-8") as f:
            data = json.load(f)
        commits = _decorate_commits(
            (data.get("commits") if isinstance(data, dict) else data) or [])
        # 「已并入本地」（patch-id 等价，只读）与「已跳过」（持久化，可恢复）
        applied = _decorate_commits(
            (data.get("applied") if isinstance(data, dict) else None) or [])
        ignored = _decorate_commits(
            (data.get("ignored") if isinstance(data, dict) else None) or [])
        base = data.get("base", BASE_BRANCH) if isinstance(data, dict) else BASE_BRANCH
        since_used = data.get("since", since) if isinstance(data, dict) else since
        return {"commits": commits, "applied": applied, "ignored": ignored,
                "range": f"{_src_label(remote_url, remote_branch)} → {base}"
                         f"（自 {since_used} 起）"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{e}"}
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def get_advise(since, force=False, remote_url=None, remote_branch=None):
    """AI 顾问：逐条做冲突预判（merge-tree）与本地定制度统计，并修正取舍建议。

    与 get_commits 同构，但 advise 很慢，故带模块级缓存（键含 since 与数据源）。
    注意 advise --json 走 --out 文件（或 stdout），**不打** @@SYNC@@ 标记，
    因此不能用 parse_sync_json() 解析。
    """
    cache_key = (since, (remote_url or "").strip(), (remote_branch or "").strip())
    if not force and _ADVISE_CACHE["key"] == cache_key and _ADVISE_CACHE["data"]:
        return _ADVISE_CACHE["data"]
    src = source_args(remote_url, remote_branch)
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        try:
            code, out = run_sync(
                [*src, "--since", since, "advise", "--json", "--out", tmp],
                timeout=1800)
        except subprocess.TimeoutExpired:
            return {"error": "AI 顾问分析超时（30 分钟）。可缩短 since 范围后重试。"}
        if code != 0:
            return {"error": out or f"advise 失败（{code}）"}
        with open(tmp, "r", encoding="utf-8") as f:
            data = json.load(f)
        commits = _decorate_commits(
            (data.get("commits") if isinstance(data, dict) else data) or [])
        base = data.get("base", BASE_BRANCH) if isinstance(data, dict) else BASE_BRANCH
        since_used = data.get("since", since) if isinstance(data, dict) else since
        result = {"commits": commits,
                  "range": f"{_src_label(remote_url, remote_branch)} → {base}"
                           f"（自 {since_used} 起 · AI 顾问）"}
        _ADVISE_CACHE["key"] = cache_key
        _ADVISE_CACHE["data"] = result
        return result
    except Exception as e:  # noqa: BLE001
        return {"error": f"{e}"}
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def apply_hashes(hashes, branch, remote_url=None, remote_branch=None):
    fd, tmp = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("# UI 选择（临时）\n")
            for h in hashes:
                f.write(f"- [x] `{h[:8]}`\n")
        args = [*source_args(remote_url, remote_branch),
                "apply", "--manifest", tmp, "--pause"]
        if branch:
            args += ["--branch", branch]
        code, out = run_sync(args)
        return {"code": code, "output": out, "result": parse_sync_json(out)}
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def get_branches(url):
    """列出任意仓库的远程分支（供界面数据源选择）。"""
    url = (url or "").strip()
    if not url:
        return {"error": "未提供仓库地址"}
    code, out = run_sync(["branches", "--url", url], timeout=180)
    if code != 0:
        return {"error": out or f"branches 失败（{code}）"}
    data = parse_sync_json(out)
    if not data or "branches" not in data:
        return {"error": out or "未取到分支列表"}
    return data


def run_sync_json(args):
    code, out = run_sync(args)
    return {"code": code, "output": out, "result": parse_sync_json(out)}


def do_ignore(hashes, remote_url=None, remote_branch=None):
    """把提交标记为「跳过」（写入 upstream_ignored.json，不再出现在待同步列表）"""
    if not hashes:
        return {"error": "未传入提交"}
    result = run_sync_json([*source_args(remote_url, remote_branch),
                            "ignore", "--hashes", ",".join(hashes)])
    if (result.get("result") or {}).get("status") == "ok":
        _ADVISE_CACHE["key"] = None  # 待同步集合变了，顾问缓存作废
        _ADVISE_CACHE["data"] = None
    return result


def do_unignore(hashes):
    """恢复被跳过的提交"""
    if not hashes:
        return {"error": "未传入提交"}
    result = run_sync_json(["unignore", "--hashes", ",".join(hashes)])
    if (result.get("result") or {}).get("status") == "ok":
        _ADVISE_CACHE["key"] = None
        _ADVISE_CACHE["data"] = None
    return result


def get_conflicts():
    return run_sync_json(["conflicts"])


def get_conflict_detail(path):
    return run_sync_json(["conflict-detail", "--file", path])


def get_commit_detail(commit):
    return run_sync_json(["show", "--commit", commit])


def do_resolve(choices):
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(choices, f, ensure_ascii=False)
        return run_sync_json(["resolve", "--choices-file", tmp])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def do_abort():
    return run_sync_json(["abort"])


def _merge_tree_files(out):
    """解析 merge-tree --name-only 输出：第 1 行是 tree OID，其后到空行为冲突文件"""
    files = []
    for i, line in enumerate((out or "").splitlines()):
        if i == 0:
            continue
        if not line.strip():
            break
        files.append(line.strip())
    return files


def precheck(hashes, base=BASE_BRANCH):
    """用 git merge-tree 模拟 cherry-pick，预判每个提交是否会冲突（不改动工作区）"""
    results = {}
    for h in hashes:
        proc = subprocess.run(
            ["git", "merge-tree", "--write-tree", "--name-only",
             f"--merge-base={h}^", base, h],
            cwd=REPO_ROOT, capture_output=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode == 0:
            results[h] = {"status": "ok", "files": []}
        elif proc.returncode == 1:
            results[h] = {"status": "conflict",
                          "files": _merge_tree_files(proc.stdout)}
        else:
            results[h] = {"status": "error", "files": []}
    return results


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # 禁用缓存：避免浏览器沿用旧版页面（改动后刷新即可生效）
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/commits":
            qs = parse_qs(parsed.query)
            since = (qs.get("since") or [DEFAULT_SINCE])[0]
            refresh = (qs.get("refresh") or ["0"])[0] == "1"
            remote_url = (qs.get("remote_url") or [""])[0]
            remote_branch = (qs.get("remote_branch") or [""])[0]
            self._send(200, json.dumps(
                get_commits(since, refresh, remote_url, remote_branch),
                ensure_ascii=False))
            return
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path
        routes = {"/api/apply", "/api/precheck", "/api/conflicts",
                  "/api/conflict-detail", "/api/resolve", "/api/abort",
                  "/api/translate", "/api/show", "/api/advise", "/api/branches",
                  "/api/ignore", "/api/unignore"}
        if path not in routes:
            self._send(404, json.dumps({"error": "not found"}))
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/precheck":
                result = {"results": precheck(payload.get("hashes") or [])}
            elif path == "/api/conflicts":
                result = get_conflicts()
            elif path == "/api/conflict-detail":
                result = get_conflict_detail(payload.get("file") or "")
            elif path == "/api/show":
                result = get_commit_detail(payload.get("commit") or "")
            elif path == "/api/resolve":
                result = do_resolve(payload.get("choices") or {})
            elif path == "/api/abort":
                result = do_abort()
            elif path == "/api/translate":
                result = translate_texts(payload.get("texts") or [])
            elif path == "/api/advise":
                result = get_advise((payload.get("since") or DEFAULT_SINCE).strip(),
                                    bool(payload.get("force")),
                                    payload.get("remote_url"),
                                    payload.get("remote_branch"))
            elif path == "/api/branches":
                result = get_branches(payload.get("url") or "")
            elif path == "/api/ignore":
                result = do_ignore(payload.get("hashes") or [],
                                   payload.get("remote_url"),
                                   payload.get("remote_branch"))
            elif path == "/api/unignore":
                result = do_unignore(payload.get("hashes") or [])
            else:  # /api/apply
                hashes = payload.get("hashes") or []
                if not hashes:
                    self._send(400, json.dumps({"code": 1, "output": "未传入提交"}, ensure_ascii=False))
                    return
                result = apply_hashes(hashes, (payload.get("branch") or "").strip(),
                                      payload.get("remote_url"),
                                      payload.get("remote_branch"))
            self._send(200, json.dumps(result, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"code": 1, "output": f"异常：{e}"}, ensure_ascii=False))

    def log_message(self, fmt, *a):  # 静默默认访问日志
        pass


def pick_port():
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        try:
            srv = ThreadingHTTPServer((HOST, port), Handler)
            return srv, port
        except OSError:
            continue
    raise SystemExit(f"端口 {DEFAULT_PORT}~{DEFAULT_PORT + 19} 均被占用")


def main():
    if not os.path.exists(SYNC_SCRIPT):
        raise SystemExit(f"找不到 {SYNC_SCRIPT}")
    srv, port = pick_port()
    url = f"http://{HOST}:{port}/"
    print(f"[ui] 上游提交同步界面已启动: {url}")
    print("[ui] 按 Ctrl+C 退出")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[ui] 已退出")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()