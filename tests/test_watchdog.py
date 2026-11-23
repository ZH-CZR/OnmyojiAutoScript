# This Python file uses the following encoding: utf-8
"""看门狗判定的回归测试。"""
from datetime import datetime, timedelta

from module.server import watchdog
from module.server.script_process import ScriptState


class _FakeProc:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


class _FakeSP:
    """只暴露 _watch_once 用到的字段。"""

    def __init__(self, state=ScriptState.RUNNING, alive=True, heartbeat_at=None, proc_missing=False):
        self.state = state
        self._process = None if proc_missing else _FakeProc(alive)
        self.latest_metrics = {} if heartbeat_at is None else {"heartbeat_at": heartbeat_at}


def test_heartbeat_age():
    assert watchdog._heartbeat_age({"heartbeat_at": 990.0}, 1000.0) == 10.0
    assert watchdog._heartbeat_age({}, 1000.0) is None
    assert watchdog._heartbeat_age({"heartbeat_at": "bad"}, 1000.0) is None


def test_overdue_tasks_only_enabled_and_late(monkeypatch):
    data = {
        "Exploration": {
            "scheduler": {
                "enable": True,
                "next_run": "2026-11-23 10:00:00",
            }
        },
        "Orochi": {
            "scheduler": {
                "enable": False,
                "next_run": "2026-11-23 10:00:00",
            }
        },
        "Duel": {
            "scheduler": {
                "enable": True,
                "next_run": "2026-11-23 11:50:00",
            }
        },
        "Restart": {
            "scheduler": {
                "enable": True,
                "next_run": "2026-11-23 18:00:00",
            }
        },
    }
    monkeypatch.setattr(watchdog, "read_file", lambda path: data)

    overdue = watchdog._overdue_tasks("oas1", datetime(2026, 11, 23, 12, 0, 0))
    assert [task for task, _ in overdue] == ["Exploration"]


def _patch_notify(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(watchdog, "_notify", lambda name, title, content: calls.append((name, content)))
    monkeypatch.setattr(watchdog, "_overdue_tasks", lambda name, now: [])
    return calls


def test_watch_once_alerts_stale_heartbeat(monkeypatch):
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(heartbeat_at=now.timestamp() - (watchdog.HEARTBEAT_STALE_SECONDS + 60))
    last_alert: dict[str, datetime] = {}

    dead = watchdog._watch_once(now, {"oas1": sp}, set(), last_alert)

    assert dead == set()
    assert len(calls) == 1 and calls[0][0] == "oas1"
    assert "oas1::heartbeat" in last_alert


def test_watch_once_ignores_fresh_heartbeat(monkeypatch):
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(heartbeat_at=now.timestamp() - 10)
    watchdog._watch_once(now, {"oas1": sp}, set(), {})
    assert calls == []


def test_watch_once_ignores_non_running_state(monkeypatch):
    """状态不是 RUNNING（如正在更新）时不按心跳判定卡死。"""
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(state=ScriptState.UPDATING, heartbeat_at=now.timestamp() - 3600)
    watchdog._watch_once(now, {"oas1": sp}, set(), {})
    assert calls == []


def test_watch_once_heartbeat_alert_deduplicated(monkeypatch):
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(heartbeat_at=now.timestamp() - (watchdog.HEARTBEAT_STALE_SECONDS + 60))
    last_alert: dict[str, datetime] = {}

    watchdog._watch_once(now, {"oas1": sp}, set(), last_alert)
    watchdog._watch_once(now + timedelta(minutes=10), {"oas1": sp}, set(), last_alert)
    assert len(calls) == 1

    watchdog._watch_once(now + watchdog.RE_ALERT_EVERY + timedelta(minutes=1), {"oas1": sp}, set(), last_alert)
    assert len(calls) == 2


def test_watch_once_requires_two_rounds_to_confirm_crash(monkeypatch):
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(alive=False)
    last_alert: dict[str, datetime] = {}

    dead = watchdog._watch_once(now, {"oas1": sp}, set(), last_alert)
    assert dead == {"oas1"}
    assert calls == []  # 第一轮只记录，不告警

    dead = watchdog._watch_once(now + timedelta(minutes=1), {"oas1": sp}, dead, last_alert)
    assert dead == {"oas1"}
    assert len(calls) == 1 and calls[0][0] == "oas1"
    assert "oas1::crash" in last_alert


def test_watch_once_crash_alert_deduplicated(monkeypatch):
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(alive=False)
    last_alert: dict[str, datetime] = {}
    dead = {"oas1"}

    watchdog._watch_once(now, {"oas1": sp}, dead, last_alert)
    watchdog._watch_once(now + timedelta(minutes=5), {"oas1": sp}, dead, last_alert)
    assert len(calls) == 1


def test_watch_once_ignores_cleanly_stopped_process(monkeypatch):
    """正常停止（_process 为 None）不视为意外退出。"""
    calls = _patch_notify(monkeypatch)
    now = datetime(2026, 11, 23, 12, 0, 0)
    sp = _FakeSP(proc_missing=True)
    dead = watchdog._watch_once(now, {"oas1": sp}, {"oas1"}, {})
    assert dead == set()
    assert calls == []

