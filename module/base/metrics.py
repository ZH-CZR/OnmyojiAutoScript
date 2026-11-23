# This Python file uses the following encoding: utf-8
"""轻量进程内指标。

只记录本项目真正需要的三类数据：
- counter: 任务次数、失败次数、RPC 调用次数
- gauge: 进程 RSS、CPU
- histogram: 任务耗时、RPC 延迟（保留最近 N 个样本，输出 p50/p95）

不依赖 Prometheus / OpenTelemetry，快照是可直接 JSON 序列化的 dict。
脚本进程每 5 秒通过 metrics_queue 推送一次快照，服务进程只负责缓存和展示。
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from threading import Thread
from typing import Any

DEFAULT_MAX_SAMPLES = 256


def _percentile(sorted_values: list[float], ratio: float) -> float:
    """线性插值百分位；样本为空时返回 0。"""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * ratio
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)


class MetricsRegistry:
    """线程安全的极简指标注册表。"""

    def __init__(self, max_samples: int = DEFAULT_MAX_SAMPLES) -> None:
        self._lock = threading.Lock()
        self._max_samples = max_samples
        self._created_at = time.time()
        self._heartbeat_at = time.time()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, Any] = {}
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=self._max_samples))

    @staticmethod
    def _key(name: str, labels: dict[str, Any] | None = None) -> str:
        if not labels:
            return name
        label_text = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
        return f"{name}|{label_text}"

    def incr(self, name: str, value: float = 1.0, labels: dict[str, Any] | None = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] += float(value)

    def set_gauge(self, name: str, value: Any, labels: dict[str, Any] | None = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._samples[key].append(float(value))
            self._counters[self._key(f"{name}_count", labels)] += 1
            self._counters[self._key(f"{name}_sum", labels)] += float(value)

    def heartbeat(self) -> None:
        with self._lock:
            self._heartbeat_at = time.time()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            histograms: dict[str, dict[str, float | int]] = {}
            for key, samples in self._samples.items():
                if not samples:
                    continue
                values = sorted(samples)
                histograms[key] = {
                    "count": len(values),
                    "min": round(values[0], 3),
                    "max": round(values[-1], 3),
                    "mean": round(sum(values) / len(values), 3),
                    "p50": round(_percentile(values, 0.50), 3),
                    "p95": round(_percentile(values, 0.95), 3),
                }
            return {
                "pid": os.getpid(),
                "created_at": self._created_at,
                "heartbeat_at": self._heartbeat_at,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histograms,
            }


metrics = MetricsRegistry()


class TimedRpcProxy:
    """透明包装 zerorpc.Client，记录每次 RPC 的耗时与成败。

    只代理方法调用，不改变返回值；非可调用属性直接透传。
    """

    def __init__(self, client: Any, service: str) -> None:
        object.__setattr__(self, "_client", client)
        object.__setattr__(self, "_service", service)

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._client, name)
        if not callable(attribute):
            return attribute

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            success = False
            try:
                result = attribute(*args, **kwargs)
                success = True
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                metrics.incr(
                    "rpc_calls_total",
                    labels={
                        "service": self._service,
                        "method": name,
                        "result": "success" if success else "error",
                    },
                )
                metrics.observe(
                    "rpc_latency_ms",
                    elapsed_ms,
                    labels={"service": self._service, "method": name},
                )

        return wrapper

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._client, name, value)


def start_metrics_reporter(metrics_queue: Any, interval: float = 5.0) -> Thread:
    """启动指标心跳线程：定期采集进程指标并把快照放进队列。"""

    def report() -> None:
        try:
            import psutil

            process = psutil.Process()
            process.cpu_percent(None)
        except Exception:
            process = None
        while 1:
            try:
                if process is not None:
                    metrics.set_gauge("process_rss_bytes", process.memory_info().rss)
                    metrics.set_gauge("process_cpu_percent", process.cpu_percent(None))
                metrics.heartbeat()
                if metrics_queue is not None:
                    try:
                        metrics_queue.put_nowait(metrics.snapshot())
                    except Exception:
                        pass
            except Exception as e:
                from module.logger import logger

                logger.warning(f'Metrics report failed: {e}')
            time.sleep(interval)

    thread = Thread(target=report, name='Script_metrics', daemon=True)
    thread.start()
    return thread
