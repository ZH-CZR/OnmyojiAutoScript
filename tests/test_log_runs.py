# This Python file uses the following encoding: utf-8
"""结构化运行日志的自动化测试：run 上下文、存储、清理、诊断包与 HTTP 接口。"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from module import exception as oas_exception
from module.log import diagnosis, error_codes, run_context, run_store


@pytest.fixture()
def runs_root(tmp_path, monkeypatch):
    """把 run 存储指到临时目录，避免污染真实 log/。"""
    root = tmp_path / "runs"
    monkeypatch.setattr(run_store, "RUNS_DIR", root)
    run_context._current_run.set(None)
    run_context._active_run = None
    return root


def _parse(response):
    return json.loads(response.body.decode("utf-8"))


def test_run_context_start_end(runs_root):
    context = run_context.begin_run("测试号_日常", "Exploration")
    assert run_context.current_run() is context
    assert context.script_name == "测试号"
    assert context.attempt == 1

    run_context.add_timeline("warning", "测试事件")
    record = run_context.end_run("success")
    assert run_context.current_run() is None
    assert record["status"] == "success"
    assert record["duration_seconds"] is not None

    index = run_store.load_index()
    assert len(index) == 1
    item = index[0]
    assert item["run_id"] == context.run_id
    assert item["task"] == "Exploration"
    assert item["script_name"] == "测试号"
    assert item["status"] == "success"
    assert item["started_at"] and item["finished_at"]

    lines = run_store.read_json_lines(run_store.run_file_path(context.run_id))
    assert [line["type"] for line in lines] == ["start", "event", "end"]
    assert lines[1]["message"] == "测试事件"


def test_run_attempt_chain(runs_root):
    first = run_context.begin_run("oas", "Exploration", attempt=1)
    run_context.end_run("failed")
    second = run_context.begin_run("oas", "Exploration", attempt=2, parent_run_id=first.run_id)
    run_context.end_run("success")
    assert second.parent_run_id == first.run_id
    index = {item["run_id"]: item for item in run_store.load_index()}
    assert index[first.run_id]["status"] == "failed"
    assert index[second.run_id]["attempt"] == 2


def test_jsonl_concurrent_append(tmp_path):
    path = tmp_path / "concurrent.jsonl"

    def worker(worker_id: int) -> None:
        for index in range(50):
            run_store.append_json_line(path, {"worker": worker_id, "index": index})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = run_store.read_json_lines(path)
    assert len(lines) == 200
    assert all(isinstance(line.get("index"), int) for line in lines)


def test_cleanup_boundaries(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    monkeypatch.setattr(run_store, "RUNS_DIR", root)
    now = datetime(2026, 11, 23, 12, 0, 0)

    for offset in range(0, 5):
        day = (now.date() - timedelta(days=offset)).isoformat()
        directory = root / day
        directory.mkdir(parents=True)
        (directory / f"{day.replace('-', '')}-120000-abcdef.jsonl").write_text("", encoding="utf-8")

    index_lines = [
        {"run_id": "20261117-120000-aaaaaa", "script_name": "oas",
         "started_at": (now - timedelta(days=6)).isoformat(timespec="seconds")},
        {"run_id": "20261115-120000-bbbbbb", "script_name": "oas",
         "started_at": (now - timedelta(days=8)).isoformat(timespec="seconds")},
    ]
    index_file = root / run_store.INDEX_FILE_NAME
    index_file.write_text(
        "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in index_lines),
        encoding="utf-8",
    )

    run_store.cleanup_runs(now=now)

    assert (root / "2026-11-23").is_dir()
    assert (root / "2026-11-21").is_dir()
    assert not (root / "2026-11-20").exists()

    kept_ids = {line["run_id"] for line in run_store.read_json_lines(index_file)}
    assert kept_ids == {"20261117-120000-aaaaaa"}


def test_stats_24h_rolling():
    now = datetime(2026, 11, 23, 12, 0, 0)
    records = [
        {"run_id": "a", "script_name": "oas", "task": "探索", "status": "success",
         "started_at": (now - timedelta(hours=1)).isoformat(timespec="seconds"), "duration_seconds": 100},
        {"run_id": "b", "script_name": "oas", "task": "探索", "status": "failed",
         "started_at": (now - timedelta(hours=2)).isoformat(timespec="seconds"), "duration_seconds": 50,
         "error_code": "E_CLICK_GUARD_STUCK"},
        {"run_id": "c", "script_name": "oas", "task": "御魂", "status": "aborted",
         "started_at": (now - timedelta(hours=3)).isoformat(timespec="seconds")},
        {"run_id": "d", "script_name": "oas", "task": "探索", "status": "failed",
         "started_at": (now - timedelta(hours=25)).isoformat(timespec="seconds"), "duration_seconds": 10},
    ]
    stats = run_store.compute_stats_24h(records, now=now)
    assert stats["total"] == 3
    assert stats["success"] == 1
    assert stats["failed"] == 1
    assert stats["aborted"] == 1
    assert stats["success_rate"] == 0.5
    assert stats["avg_duration_seconds"] == 75.0
    assert stats["top_blockers"][0] == {"key": "E_CLICK_GUARD_STUCK", "count": 1}


def test_error_code_catalog_complete():
    for code, item in error_codes.ERROR_CODES.items():
        assert item["summary"].strip(), code
        assert item["suggestion"].strip(), code
    for code in list(error_codes._EXCEPTION_CODES.values()) + [item for _, item in error_codes._MESSAGE_KEYWORDS]:
        assert code in error_codes.ERROR_CODES

    cases = {
        oas_exception.GameStuckError("stuck"): "E_CLICK_GUARD_STUCK",
        oas_exception.GameTooManyClickError("too many"): "E_CLICK_GUARD_TOO_MANY",
        oas_exception.GamePageUnknownError("unknown"): "E_PAGE_UNKNOWN",
        oas_exception.GameNotRunningError("not running"): "E_GAME_NOT_RUNNING",
        oas_exception.EmulatorNotRunningError("offline"): "E_DEVICE_OFFLINE",
        oas_exception.RequestHumanTakeover("config"): "E_TASK_CONFIG",
        RuntimeError("adb connection refused"): "E_ADB",
        RuntimeError("请把分辨率改为 1280x720"): "E_ENV_RESOLUTION",
    }
    for exc, expected in cases.items():
        result = error_codes.classify_exception(exc)
        assert result.code == expected
        assert result.summary and result.suggestion


def test_diagnosis_fit_size_boundary():
    payload = diagnosis.build_diagnosis(
        run={"run_id": "20261123-120000-abcdef", "task": "Exploration"},
        error={"code": "E_UNKNOWN", "summary": "出错了", "suggestion": "看看截图", "stack": "x" * 20000},
        timeline=[{"ts": "2026-11-23T12:00:00", "level": "info", "message": "事件" * 20}] * 200,
        screenshots=["1.png", "2.png"],
        config_snapshot={"config_name": "oas", "script": {"x": "y" * 5000}},
        environment={"machine": "test"},
        log_tail=["日志行" * 100] * 400,
    )
    fitted = diagnosis.fit_size(payload)
    text = json.dumps(fitted, ensure_ascii=False, default=str)
    assert len(text.encode("utf-8")) <= diagnosis.MAX_DIAGNOSIS_BYTES
    for key in ("schema_version", "run", "error", "timeline", "screenshots",
                "config_snapshot", "environment", "log_tail"):
        assert key in fitted


def test_write_diagnosis_from_script(tmp_path, runs_root):
    context = run_context.begin_run("oas", "Exploration")
    context.mark_error(RuntimeError("界面未知，无法识别"))
    folder = tmp_path / "error" / "oas_1700000000000"
    folder.mkdir(parents=True)
    (folder / "2026-11-23_12-00-00-000000.png").write_bytes(b"png")

    class Stub:
        config_name = "oas"
        config = None
        device = None

    path = diagnosis.write_diagnosis_from_script(folder, Stub())
    assert path is not None and path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run"]["run_id"] == context.run_id
    assert data["error"]["code"] == context.error_code
    assert data["screenshots"] == ["2026-11-23_12-00-00-000000.png"]
    assert context.diagnosis_dir == folder.name
    assert data["warning"]
    run_context.end_run("failed")


def test_http_envelope_and_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path / "runs")
    run_context._current_run.set(None)
    run_context._active_run = None

    from module.server import log_run_router

    context = run_context.begin_run("oas", "Exploration")
    run_context.end_run("success")

    response = asyncio.run(log_run_router.list_runs(
        script_name="oas", date_text=None, limit=50, cursor=None))
    body = _parse(response)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    assert body["code"] == "ok" and body["error"] is None
    assert body["data"]["items"][0]["run_id"] == context.run_id

    detail = asyncio.run(log_run_router.get_run_detail(script_name="oas", run_id=context.run_id))
    assert _parse(detail)["data"]["run"]["status"] == "success"

    missing = asyncio.run(log_run_router.get_run_detail(
        script_name="oas", run_id="20260101-000000-abcdef"))
    assert missing.status_code == 404
    assert _parse(missing)["code"] == "LOG_RUN_NOT_FOUND"

    stats = asyncio.run(log_run_router.get_stats_24h(script_name="oas"))
    stats_body = _parse(stats)
    assert stats_body["data"]["script_name"] == "oas"
    assert stats_body["data"]["total"] == 1


def test_existing_log_window_regression(tmp_path, monkeypatch):
    """现有文本日志窗口接口在空目录下仍返回空窗口，不受本次改造影响。"""
    from module.server import log_service

    monkeypatch.setattr(log_service, "LOG_ROOT", tmp_path)
    result = log_service.log_browser_service.read_window("oas")
    assert result["lines"] == []
    assert result["reached_start"] is True
    assert result["script_name"] == "oas"
