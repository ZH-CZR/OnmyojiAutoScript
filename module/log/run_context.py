# This Python file uses the following encoding: utf-8
"""run 上下文：把一次任务执行尝试的元信息挂在 contextvars 上。

调用点零改动即可拿到当前 run：日志 handler、诊断包、服务端都从这里读。
同一进程内还有一个模块级兜底引用，保证设备线程里打的 WARNING 也能落到当前 run。
"""

from __future__ import annotations

import contextvars
import secrets
import threading
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from module.log import error_codes, run_store

_current_run: contextvars.ContextVar["RunContext | None"] = contextvars.ContextVar(
    "oas_run_context", default=None
)
_active_run: "RunContext | None" = None
_active_lock = threading.Lock()

TIMELINE_MAX = 200


def _now_text(now: datetime | None = None) -> str:
    return (now or datetime.now()).isoformat(timespec="milliseconds")


def new_run_id(now: datetime | None = None) -> str:
    """生成形如 20261123-153012-a1b2c3 的 run_id。"""
    now = now or datetime.now()
    return f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


@dataclass
class RunContext:
    """一次任务执行尝试的全部状态。"""

    run_id: str
    config_name: str
    script_name: str
    task: str
    attempt: int = 1
    parent_run_id: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    status: str = "running"
    timeline: deque = field(default_factory=lambda: deque(maxlen=TIMELINE_MAX))
    error_code: str | None = None
    error_summary: str | None = None
    suggestion: str | None = None
    exception_type: str | None = None
    stack: str | None = None
    failed_rule: str | None = None
    failed_page: str | None = None
    diagnosis_dir: str | None = None
    finished_at: datetime | None = None
    ended: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ------------------------------------------------------------------ 写事件
    def record_event(self, level: str, message: str, **extra: Any) -> None:
        """向 run 的 JSONL 追加一条事件，并保留到内存时间线。"""
        if self.ended:
            return
        ts = _now_text()
        text = str(message)
        event = {
            "type": "event",
            "run_id": self.run_id,
            "ts": ts,
            "level": level,
            "message": text,
        }
        event.update({key: value for key, value in extra.items() if value is not None})
        run_store.append_json_line(run_store.run_file_path(self.run_id), event)
        with self._lock:
            self.timeline.append({"ts": ts, "level": level, "message": text})

    def mark_error(self, exc: BaseException, *, failed_rule: str | None = None,
                   failed_page: str | None = None, stack: str | None = None) -> str:
        """记录一次错误，返回错误码。"""
        diagnosis = error_codes.classify_exception(exc)
        self.error_code = diagnosis.code
        self.error_summary = diagnosis.summary
        self.suggestion = diagnosis.suggestion
        self.exception_type = diagnosis.exception_type
        self.stack = stack or "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        self.failed_rule = failed_rule or getattr(exc, "failed_rule", None)
        self.failed_page = failed_page or getattr(exc, "failed_page", None)
        self.record_event(
            "error",
            f"{diagnosis.summary}（{diagnosis.exception_type}）: {exc}",
            error_code=diagnosis.code,
        )
        return diagnosis.code

    def attach_diagnosis(self, folder_name: str) -> None:
        """绑定诊断包目录名，结束时写进索引。"""
        self.diagnosis_dir = str(folder_name or "").strip() or None

    # ------------------------------------------------------------------ 收尾
    def finish(self, status: str = "success") -> dict[str, Any] | None:
        """结束 run：写结束事件与完整索引行；重复调用无副作用。"""
        with self._lock:
            if self.ended:
                return None
            self.ended = True
        self.status = status if status in ("success", "failed", "aborted") else "failed"
        self.finished_at = datetime.now()
        duration = max(0.0, (self.finished_at - self.started_at).total_seconds())
        record = self.index_record()
        record.update(
            {
                "status": self.status,
                "finished_at": self.finished_at.isoformat(timespec="seconds"),
                "duration_seconds": round(duration, 1),
                "error_code": self.error_code,
                "error_summary": self.error_summary,
                "failed_rule": self.failed_rule,
                "diagnosis_dir": self.diagnosis_dir,
            }
        )
        run_store.append_json_line(
            run_store.run_file_path(self.run_id),
            {
                "type": "end",
                "run_id": self.run_id,
                "ts": _now_text(self.finished_at),
                "status": self.status,
                "duration_seconds": record["duration_seconds"],
                "error_code": self.error_code,
                "error_summary": self.error_summary,
            },
        )
        run_store.append_index(record)
        return record

    def index_record(self) -> dict[str, Any]:
        """当前 run 的索引行（开跑与结束都会写）。"""
        return {
            "run_id": self.run_id,
            "config_name": self.config_name,
            "script_name": self.script_name,
            "task": self.task,
            "attempt": self.attempt,
            "parent_run_id": self.parent_run_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "finished_at": self.finished_at.isoformat(timespec="seconds") if self.finished_at else None,
            "duration_seconds": None,
            "error_code": self.error_code,
            "error_summary": self.error_summary,
            "diagnosis_dir": self.diagnosis_dir,
        }

    def snapshot(self) -> dict[str, Any]:
        """给诊断包用的精简快照。"""
        return {
            "run_id": self.run_id,
            "config_name": self.config_name,
            "script_name": self.script_name,
            "task": self.task,
            "attempt": self.attempt,
            "parent_run_id": self.parent_run_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "finished_at": self.finished_at.isoformat(timespec="seconds") if self.finished_at else None,
            "duration_seconds": (
                round((self.finished_at - self.started_at).total_seconds(), 1)
                if self.finished_at else None
            ),
            "error_code": self.error_code,
            "error_summary": self.error_summary,
            "suggestion": self.suggestion,
            "exception_type": self.exception_type,
            "failed_rule": self.failed_rule,
            "failed_page": self.failed_page,
            "diagnosis_dir": self.diagnosis_dir,
        }

    def error_snapshot(self) -> dict[str, Any]:
        """给诊断包用的错误快照。"""
        return {
            "code": self.error_code or "E_UNKNOWN",
            "summary": self.error_summary or error_codes.explain("E_UNKNOWN")[0],
            "suggestion": self.suggestion or error_codes.explain("E_UNKNOWN")[1],
            "exception_type": self.exception_type,
            "stack": self.stack or "",
            "failed_rule": self.failed_rule,
            "failed_page": self.failed_page,
        }

    def timeline_snapshot(self) -> list[dict[str, Any]]:
        """复制时间线，避免调用方改到内部 deque。"""
        with self._lock:
            return list(self.timeline)


# ---------------------------------------------------------------------- 模块函数
def begin_run(
    config_name: str,
    task: str,
    attempt: int = 1,
    parent_run_id: str | None = None,
    now: datetime | None = None,
) -> RunContext:
    """开启一次 run：先结束遗留 run（标记 aborted），再写 start 事件与索引。"""
    global _active_run
    previous = current_run()
    if previous is not None:
        previous.finish("aborted")

    now = now or datetime.now()
    context = RunContext(
        run_id=new_run_id(now),
        config_name=str(config_name),
        script_name=run_store.normalize_name(config_name),
        task=str(task),
        attempt=max(1, int(attempt)),
        parent_run_id=parent_run_id,
        started_at=now,
    )
    _current_run.set(context)
    with _active_lock:
        _active_run = context

    run_store.append_json_line(
        run_store.run_file_path(context.run_id),
        {
            "type": "start",
            "run_id": context.run_id,
            "ts": _now_text(now),
            "config_name": context.config_name,
            "script_name": context.script_name,
            "task": context.task,
            "attempt": context.attempt,
            "parent_run_id": context.parent_run_id,
        },
    )
    run_store.append_index(context.index_record())
    return context


def current_run() -> RunContext | None:
    """取当前 run：优先 contextvars，跨线程时退回模块级引用。"""
    context = _current_run.get()
    if context is not None and not context.ended:
        return context

    with _active_lock:
        fallback = _active_run
    if fallback is not None and not fallback.ended:
        return fallback
    return None


def end_run(status: str = "success") -> dict[str, Any] | None:
    """结束当前 run，返回写入的索引行。"""
    global _active_run
    context = current_run()
    if context is None:
        return None
    record = context.finish(status)
    _current_run.set(None)
    with _active_lock:
        if _active_run is context:
            _active_run = None
    return record


def add_timeline(level: str, message: str, **extra: Any) -> None:
    """给当前 run 记一条时间线事件（没有 run 时静默忽略）。"""
    context = current_run()
    if context is not None:
        context.record_event(level, message, **extra)


def record_error(exc: BaseException, **kwargs: Any) -> str | None:
    """记录当前 run 的错误，返回错误码。"""
    context = current_run()
    if context is None:
        return None
    return context.mark_error(exc, **kwargs)


def attach_diagnosis(folder_name: str) -> None:
    """把诊断包目录绑定到当前 run。"""
    context = current_run()
    if context is not None:
        context.attach_diagnosis(folder_name)


def snapshot() -> dict[str, Any] | None:
    """当前 run 的快照，没有则返回 None。"""
    context = current_run()
    return context.snapshot() if context is not None else None
