# This Python file uses the following encoding: utf-8
"""轻量指标注册表与 RPC 计时代理的回归测试。"""
import asyncio
import queue
import time

from module.base.metrics import MetricsRegistry, TimedRpcProxy, metrics, start_metrics_reporter
from module.server.config_manager import ConfigManager
from module.server.script_process import ScriptProcess, ScriptState


def test_counter_gauge_and_labels():
    registry = MetricsRegistry()
    registry.incr("task_runs_total", labels={"task": "Exploration", "result": "started"})
    registry.incr("task_runs_total", 2, labels={"task": "Exploration", "result": "started"})
    registry.set_gauge("process_rss_bytes", 123456)

    snapshot = registry.snapshot()
    assert snapshot["counters"]["task_runs_total|result=started,task=Exploration"] == 3.0
    assert snapshot["gauges"]["process_rss_bytes"] == 123456
    assert snapshot["pid"] > 0


def test_histogram_percentiles():
    registry = MetricsRegistry()
    for value in range(1, 101):
        registry.observe("task_duration_seconds", value, labels={"task": "Exploration"})

    histogram = registry.snapshot()["histograms"]["task_duration_seconds|task=Exploration"]
    assert histogram["count"] == 100
    assert histogram["min"] == 1
    assert histogram["max"] == 100
    assert 49 <= histogram["p50"] <= 51
    assert 94 <= histogram["p95"] <= 96


def test_timed_rpc_proxy_records_success_and_error():
    class FakeClient:
        def ok(self, value):
            return value + 1

        def boom(self):
            raise RuntimeError("boom")

    proxy = TimedRpcProxy(FakeClient(), "test_service")
    assert proxy.ok(1) == 2
    try:
        proxy.boom()
    except RuntimeError:
        pass

    snapshot = metrics.snapshot()
    assert snapshot["counters"]["rpc_calls_total|method=ok,result=success,service=test_service"] == 1
    assert snapshot["counters"]["rpc_calls_total|method=boom,result=error,service=test_service"] == 1
    histogram = snapshot["histograms"]["rpc_latency_ms|method=ok,service=test_service"]
    assert histogram["count"] == 1
    assert histogram["p95"] >= 0


def test_script_metrics_reporter_pushes_snapshot():
    metrics_queue = queue.Queue()
    start_metrics_reporter(metrics_queue, interval=0.2)
    deadline = time.time() + 2
    snapshot = None
    while time.time() < deadline and snapshot is None:
        try:
            snapshot = metrics_queue.get_nowait()
        except queue.Empty:
            time.sleep(0.05)
    assert snapshot is not None
    assert snapshot["heartbeat_at"] > 0
    assert "process_rss_bytes" in snapshot["gauges"]


def test_script_process_collects_metrics_snapshot():
    config_name = next(iter(ConfigManager.all_script_files()))
    script_process = ScriptProcess(config_name)
    script_process.state = ScriptState.RUNNING
    script_process.metrics_queue.put({"heartbeat_at": 1.0})

    async def collect():
        task = asyncio.create_task(script_process.coroutine_collect_metrics())
        await asyncio.sleep(1.0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(collect())
    assert script_process.latest_metrics["heartbeat_at"] == 1.0
    assert script_process.metrics_updated_at > 0
