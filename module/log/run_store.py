# This Python file uses the following encoding: utf-8
"""run 结构化日志的落盘与查询。

目录约定：
- log/runs/YYYY-MM-DD/<run_id>.jsonl：单个 run 的事件流，保留 3 天；
- log/runs/index.jsonl：每个 run 一行摘要，保留 7 天。

索引采用“后写覆盖”的方式：开跑时先写一行 status=running，结束时再写一行完整状态；
进程被杀导致没有结束行时，列表里仍能看到这个 run（状态为 running），不会丢。
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "log" / "runs"
INDEX_FILE_NAME = "index.jsonl"

RUN_KEEP_DAYS = 3
INDEX_KEEP_DAYS = 7
STATS_WINDOW_HOURS = 24
MAX_RUN_LIMIT = 200

RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
_UNSAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_write_lock = threading.Lock()


class RunStoreError(Exception):
    """run 存储层业务异常，由服务端翻译成统一响应包络。"""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def normalize_name(name: Any) -> str:
    """把配置名规范成日志使用的脚本名。

    与 module/logger.py::normalize_log_name 保持一致：第一个下划线之后视为运行时后缀。
    """
    text = str(name or "").strip()
    if "_" in text:
        text = text.split("_", 1)[0]
    text = _UNSAFE_NAME_RE.sub("_", text).replace("..", "_").strip(" .")
    return text or "script"


def runs_root(root: Path | None = None) -> Path:
    """返回 runs 根目录；测试可以通过传 root 或改 RUNS_DIR 隔离。"""
    return Path(root) if root is not None else RUNS_DIR


def index_path(root: Path | None = None) -> Path:
    """返回索引文件路径。"""
    return runs_root(root) / INDEX_FILE_NAME


def day_dir(day: date, root: Path | None = None) -> Path:
    """返回某天的 run 目录。"""
    return runs_root(root) / day.isoformat()


def validate_run_id(run_id: str) -> str:
    """校验 run_id 格式，避免路径注入。"""
    text = str(run_id or "").strip()
    if not RUN_ID_RE.match(text):
        raise RunStoreError(400, "LOG_RUN_ID_INVALID", "run_id 格式不正确")
    return text


def run_day(run_id: str) -> date:
    """从 run_id 前缀解析出运行日期。"""
    text = validate_run_id(run_id)
    return date(int(text[0:4]), int(text[4:6]), int(text[6:8]))


def run_file_path(run_id: str, root: Path | None = None) -> Path:
    """返回单个 run 的 JSONL 文件路径。"""
    text = validate_run_id(run_id)
    return day_dir(run_day(text), root) / f"{text}.jsonl"


def append_json_line(path: Path, payload: dict[str, Any]) -> bool:
    """原子追加一行 JSON，失败只返回 False，不影响主流程。"""
    try:
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            with open(path, "a", encoding="utf-8", newline="\n") as file:
                file.write(line + "\n")
                file.flush()
        return True
    except OSError:
        return False


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    """读取 JSONL，坏行直接跳过，不让一条坏数据毁掉整份日志。"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    result: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            result.append(item)
    return result


def append_index(record: dict[str, Any], root: Path | None = None) -> bool:
    """追加一条索引摘要。"""
    return append_json_line(index_path(root), record)


def load_index(root: Path | None = None) -> list[dict[str, Any]]:
    """读取全部索引，按 run_id 合并后写覆盖，返回列表。"""
    merged: dict[str, dict[str, Any]] = {}
    for item in read_json_lines(index_path(root)):
        run_id = str(item.get("run_id") or "").strip()
        if not run_id:
            continue
        if run_id in merged:
            merged[run_id].update(item)
        else:
            merged[run_id] = dict(item)
    return list(merged.values())


def parse_dt(value: Any) -> datetime | None:
    """把 ISO 字符串解析成 datetime，失败返回 None。"""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def pick_run_item(record: dict[str, Any]) -> dict[str, Any]:
    """裁剪索引记录，只保留前端需要的字段。"""
    return {
        "run_id": record.get("run_id"),
        "config_name": record.get("config_name"),
        "script_name": record.get("script_name"),
        "task": record.get("task"),
        "attempt": record.get("attempt", 1),
        "parent_run_id": record.get("parent_run_id"),
        "status": record.get("status", "running"),
        "started_at": record.get("started_at"),
        "finished_at": record.get("finished_at"),
        "duration_seconds": record.get("duration_seconds"),
        "error_code": record.get("error_code"),
        "error_summary": record.get("error_summary"),
        "diagnosis_dir": record.get("diagnosis_dir"),
    }


def list_runs(
    script_name: str,
    day: date | None = None,
    limit: int = 50,
    offset: int = 0,
    root: Path | None = None,
) -> dict[str, Any]:
    """按脚本名（可选日期）分页列出 run。"""
    if limit < 1 or limit > MAX_RUN_LIMIT:
        raise RunStoreError(422, "LOG_LIMIT_INVALID", f"limit 必须在 1..{MAX_RUN_LIMIT} 之间")
    normalized = normalize_name(script_name)
    items = [
        record for record in load_index(root)
        if record.get("script_name") == normalized
        and (day is None or str(record.get("started_at") or "")[:10] == day.isoformat())
    ]
    items.sort(key=lambda item: (str(item.get("started_at") or ""), str(item.get("run_id") or "")), reverse=True)
    page = items[offset:offset + limit]
    next_offset = offset + len(page)
    return {
        "script_name": normalized,
        "date": day.isoformat() if day else None,
        "items": [pick_run_item(record) for record in page],
        "next_cursor": str(next_offset) if next_offset < len(items) else None,
        "has_more": next_offset < len(items),
    }


def load_run_detail(script_name: str, run_id: str, root: Path | None = None) -> dict[str, Any] | None:
    """读取单个 run 的摘要与事件流；不存在或不属于该脚本时返回 None。"""
    text = validate_run_id(run_id)
    normalized = normalize_name(script_name)
    record = None
    for item in load_index(root):
        if item.get("run_id") == text:
            record = item
            break
    if record is None or record.get("script_name") != normalized:
        return None
    events = read_json_lines(run_file_path(text, root))
    return {"run": pick_run_item(record), "events": events}


def compute_stats_24h(records: Iterable[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    """按 run 开始时间滚动统计最近 24 小时。

    口径：
    - 成功率只分母“已结束”的 run（success + failed），aborted / running 不计入；
    - 平均耗时只统计已结束且有 duration 的 run；
    - 卡点 Top3 按 error_code，缺失时退回 failed_rule，再退回 E_UNKNOWN。
    """
    now = now or datetime.now()
    window_start = now - timedelta(hours=STATS_WINDOW_HOURS)
    window: list[dict[str, Any]] = []
    for record in records:
        started = parse_dt(record.get("started_at"))
        if started is None or started < window_start or started > now:
            continue
        window.append(record)

    success = [item for item in window if item.get("status") == "success"]
    failed = [item for item in window if item.get("status") == "failed"]
    aborted = [item for item in window if item.get("status") == "aborted"]
    running = [item for item in window if item.get("status") not in ("success", "failed", "aborted")]
    finished = success + failed

    durations = [
        float(item["duration_seconds"]) for item in finished
        if isinstance(item.get("duration_seconds"), (int, float))
    ]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else None
    success_rate = round(len(success) / len(finished), 4) if finished else None

    by_task: dict[str, dict[str, Any]] = {}
    for item in window:
        task = str(item.get("task") or "")
        bucket = by_task.setdefault(task, {"task": task, "total": 0, "success": 0, "failed": 0})
        bucket["total"] += 1
        if item.get("status") == "success":
            bucket["success"] += 1
        elif item.get("status") == "failed":
            bucket["failed"] += 1

    counter: Counter[str] = Counter()
    for item in failed:
        key = str(item.get("error_code") or item.get("failed_rule") or "E_UNKNOWN")
        counter[key] += 1
    top_blockers = [
        {"key": key, "count": count}
        for key, count in counter.most_common(3)
    ]

    window.sort(key=lambda item: (str(item.get("started_at") or ""), str(item.get("run_id") or "")), reverse=True)
    return {
        "script_name": window[0].get("script_name") if window else None,
        "window_hours": STATS_WINDOW_HOURS,
        "window_start": _iso(window_start),
        "window_end": _iso(now),
        "total": len(window),
        "success": len(success),
        "failed": len(failed),
        "aborted": len(aborted),
        "running": len(running),
        "success_rate": success_rate,
        "avg_duration_seconds": avg_duration,
        "top_blockers": top_blockers,
        "by_task": sorted(by_task.values(), key=lambda item: item["total"], reverse=True),
        "recent": [pick_run_item(item) for item in window[:10]],
    }


def cleanup_runs(
    root: Path | None = None,
    keep_run_days: int = RUN_KEEP_DAYS,
    keep_index_days: int = INDEX_KEEP_DAYS,
    now: datetime | None = None,
) -> None:
    """删除过期的 run 目录并裁剪索引，静默失败。"""
    now = now or datetime.now()
    base = runs_root(root)
    if not base.is_dir():
        return

    run_cutoff = now.date() - timedelta(days=max(0, keep_run_days - 1))
    for path in base.iterdir():
        if not path.is_dir():
            continue
        try:
            day = date.fromisoformat(path.name)
        except ValueError:
            continue
        if day < run_cutoff:
            _remove_tree(path)

    _trim_index(base / INDEX_FILE_NAME, now.date() - timedelta(days=keep_index_days - 1))


def _trim_index(path: Path, keep_from: date) -> None:
    """索引按开始日期裁剪，保留最近 keep_index_days 天。"""
    if not path.is_file():
        return
    kept: list[str] = []
    for item in read_json_lines(path):
        started = parse_dt(item.get("started_at"))
        if started is not None and started.date() < keep_from:
            continue
        kept.append(json.dumps(item, ensure_ascii=False, separators=(",", ":"), default=str))
    _replace_text(path, "\n".join(kept) + ("\n" if kept else ""))


def _replace_text(path: Path, text: str) -> None:
    """写临时文件再替换，避免服务端读到半截索引。"""
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def _remove_tree(path: Path) -> None:
    """递归删除目录，单文件失败不影响其他文件。"""
    import shutil
    try:
        shutil.rmtree(path)
    except OSError:
        pass
