# This Python file uses the following encoding: utf-8
"""诊断包生成：把一次失败的现场压缩成 diagnosis.json（不超过 64KB）。

字段以“普通用户能看懂”为先：error.summary / error.suggestion 是中文结论；
stack、log_tail 等原始技术信息保留，方便开发者或 AI 继续定位。
生成失败绝不向上抛，避免影响错误日志本身的保存。
"""

from __future__ import annotations

import copy
import json
import platform
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from module.log import error_codes, run_context

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 1
MAX_DIAGNOSIS_BYTES = 64 * 1024
LOG_TAIL_LINES = 200

_DEVICE_KEYS = ("screenshot_method", "control_method", "serial", "package_name")


def _json_default(value: Any) -> Any:
    """把 datetime / Path 之类转成 JSON 可序列化的值。"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_json_default)


def _size(payload: dict[str, Any]) -> int:
    return len(_dump(payload).encode("utf-8"))


def _read_version() -> str:
    """读项目版本；没有版本文件时返回 unknown。"""
    for name in ("VERSION", "version.txt", "deploy/version.txt"):
        path = PROJECT_ROOT / name
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8", errors="ignore").strip() or "unknown"
        except OSError:
            continue
    return "unknown"


def collect_environment(device: Any = None, config: Any = None) -> dict[str, Any]:
    """采集运行环境：分辨率、截图/控制方式、序列号、机器名等。"""
    device_config = getattr(getattr(config, "script", None), "device", None)
    environment: dict[str, Any] = {
        "machine": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "oas_version": _read_version(),
        "resolution": None,
        "screenshot_method": None,
        "control_method": None,
        "serial": None,
        "package": None,
    }
    for key in _DEVICE_KEYS:
        environment[key] = getattr(device_config, key, None)

    image = getattr(device, "image", None)
    shape = getattr(image, "shape", None)
    if shape and len(shape) >= 2:
        environment["resolution"] = {"width": int(shape[1]), "height": int(shape[0])}
    environment["package"] = getattr(device, "package", None)
    return environment


def _filter_config(data: dict[str, Any], config_name: str) -> dict[str, Any]:
    """只保留 script 段与已启用任务，控制诊断包体积。"""
    result: dict[str, Any] = {"config_name": config_name}
    script = data.get("script")
    if isinstance(script, dict):
        result["script"] = script
    enabled: dict[str, Any] = {}
    for key, value in data.items():
        if key == "script" or not isinstance(value, dict):
            continue
        scheduler = value.get("scheduler")
        if isinstance(scheduler, dict) and scheduler.get("enable") is True:
            enabled[key] = value
    result["enabled_tasks"] = enabled
    return result


def collect_config_snapshot(config_name: str, config: Any = None) -> dict[str, Any]:
    """读取配置快照。按用户要求保留明文（自用环境，不做脱敏）。"""
    name = str(config_name or "").strip()
    if name and ".." not in name and "/" not in name and "\\" not in name:
        path = PROJECT_ROOT / "config" / f"{name}.json"
        try:
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, dict):
                    return _filter_config(data, name)
        except (OSError, ValueError):
            pass

    model = getattr(config, "model", None)
    try:
        data = model.dict() if model is not None else None
    except Exception:
        data = None
    if isinstance(data, dict):
        return _filter_config(data, name)
    return {"config_name": name, "unavailable": True}


def read_log_tail(log_file: str | Path | None, max_lines: int = LOG_TAIL_LINES) -> list[str]:
    """读文本日志最后若干行。"""
    if not log_file:
        return []
    path = Path(log_file)
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    return lines[-max_lines:]


def build_diagnosis(
    *,
    run: dict[str, Any] | None,
    error: dict[str, Any] | None,
    timeline: list[dict[str, Any]] | None,
    screenshots: list[str] | None,
    config_snapshot: dict[str, Any] | None,
    environment: dict[str, Any] | None,
    log_tail: list[str] | None,
    warning: str | None = None,
) -> dict[str, Any]:
    """组装诊断包结构（未做体积裁剪）。"""
    timeline = list(timeline or [])
    recent_actions = timeline[-30:]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run": run,
        "error": error,
        "timeline": timeline,
        "screenshots": screenshots or [],
        "config_snapshot": config_snapshot,
        "environment": environment,
        "recent_actions": recent_actions,
        "log_tail": list(log_tail or []),
        "warning": warning,
    }


def _shrink_text(value: str | None, limit: int) -> str | None:
    """把文本截到指定字符数，并标注已截断。"""
    if not isinstance(value, str) or len(value) <= limit:
        return value
    return value[:limit] + "\n...(已截断)"


def fit_size(payload: dict[str, Any], max_bytes: int = MAX_DIAGNOSIS_BYTES) -> dict[str, Any]:
    """逐级裁剪到 max_bytes 以内，保证关键字段仍在。"""
    if _size(payload) <= max_bytes:
        return payload

    result = copy.deepcopy(payload)
    result["truncation"] = {"truncated": True, "original_bytes": _size(payload)}

    log_tail = result.get("log_tail") or []
    while _size(result) > max_bytes and len(log_tail) > 20:
        log_tail = log_tail[len(log_tail) // 2:]
        result["log_tail"] = log_tail

    timeline = result.get("timeline") or []
    for keep in (100, 50, 20, 5):
        if _size(result) <= max_bytes:
            break
        result["timeline"] = timeline[-keep:]
        result["recent_actions"] = timeline[-keep:]

    error = result.get("error") or {}
    for limit in (8000, 2000, 500):
        if _size(result) <= max_bytes:
            break
        error["stack"] = _shrink_text(error.get("stack"), limit)
        result["error"] = error

    if _size(result) > max_bytes:
        snapshot = result.get("config_snapshot") or {}
        result["config_snapshot"] = {
            "config_name": snapshot.get("config_name"),
            "_truncated": True,
        }

    if _size(result) > max_bytes:
        result["log_tail"] = log_tail[-20:]
        result["recent_actions"] = []

    if _size(result) > max_bytes:
        result.pop("config_snapshot", None)
        result.pop("recent_actions", None)
        result["timeline"] = timeline[-5:]
        result["log_tail"] = []

    if _size(result) > max_bytes:
        result.pop("timeline", None)
        error["stack"] = _shrink_text(error.get("stack"), 200)
        result["error"] = error

    return result


def write_diagnosis_from_script(folder: Path | str, script: Any) -> Path | None:
    """在错误目录里生成 diagnosis.json，并把目录名绑定到当前 run。

    这里接受 Script 对象（鸭子类型），只读取 config / device，不做任何写配置操作。
    """
    folder = Path(folder)
    context = run_context.current_run()
    error: dict[str, Any]
    if context is not None:
        run_info = context.snapshot()
        timeline = context.timeline_snapshot()
        error = context.error_snapshot()
    else:
        run_info = None
        timeline = []
        summary, suggestion = error_codes.explain("E_UNKNOWN")
        error = {
            "code": "E_UNKNOWN",
            "summary": summary,
            "suggestion": suggestion,
            "exception_type": None,
            "stack": "",
            "failed_rule": None,
            "failed_page": None,
        }

    config_name = (run_info or {}).get("config_name") or getattr(script, "config_name", "")
    device = getattr(script, "device", None)
    config = getattr(script, "config", None)

    try:
        environment = collect_environment(device=device, config=config)
        config_snapshot = collect_config_snapshot(config_name, config=config)
    except Exception:
        environment, config_snapshot = {}, {"config_name": config_name, "unavailable": True}

    screenshots = sorted(path.name for path in folder.glob("*.png"))
    log_file = None
    try:
        from module.logger import logger as text_logger
        log_file = getattr(text_logger, "log_file", None)
    except Exception:
        log_file = None

    payload = build_diagnosis(
        run=run_info,
        error=error,
        timeline=timeline,
        screenshots=screenshots,
        config_snapshot=config_snapshot,
        environment=environment,
        log_tail=read_log_tail(log_file),
        warning="诊断包为便于排查保留了明文配置与日志，请勿上传到公开网络。",
    )
    payload = fit_size(payload)

    target = folder / "diagnosis.json"
    try:
        target.write_text(_dump(payload), encoding="utf-8")
    except OSError:
        return None
    if context is not None:
        context.attach_diagnosis(folder.name)
    return target
