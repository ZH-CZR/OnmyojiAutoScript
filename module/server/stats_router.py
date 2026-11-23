# This Python file uses the following encoding: utf-8
from __future__ import annotations

import time
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from module.server.api_logger import ApiLoggingRoute
from module.server.log_stats import log_stats_service

stats_app = APIRouter(
    prefix="/stats",
    tags=["stats"],
    route_class=ApiLoggingRoute,
)


class BattleStatsResponse(BaseModel):
    count: int
    avg_duration_seconds: float


class TaskRunStatsResponse(BaseModel):
    start_time: str
    end_time: str
    duration_seconds: float
    battle: BattleStatsResponse | None = None


class TaskStatsResponse(BaseModel):
    run_count: int
    total_duration_seconds: float
    battle: BattleStatsResponse | None = None
    runs: list[TaskRunStatsResponse] = Field(default_factory=list)


class StatsResponse(BaseModel):
    script_name: str
    total_runtime_seconds: float
    total_task_run_count: int
    total_battle_count: int
    tasks: dict[str, TaskStatsResponse] = Field(default_factory=dict)


class StatsAvailableDatesResponse(BaseModel):
    script_name: str
    dates: list[str] = Field(default_factory=list)


class StatsUpdateResponse(BaseModel):
    script_name: str
    total_runtime_seconds: float
    total_task_run_count: int
    total_battle_count: int
    changed_tasks: dict[str, TaskStatsResponse] = Field(default_factory=dict)
    removed_tasks: list[str] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    script_name: str
    available: bool
    state: int | None = None
    age_seconds: float | None = None
    stale: bool = True
    heartbeat_age_seconds: float | None = None
    heartbeat_stale: bool = True
    metrics: dict = Field(default_factory=dict)


def _parse_target_date(date_text: str) -> date:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD") from exc


@stats_app.get("/{script_name}/dates", response_model=StatsAvailableDatesResponse)
async def stats_available_dates(script_name: str):
    return log_stats_service.list_available_dates(script_name)


@stats_app.get("/{script_name}/metrics", response_model=MetricsResponse)
async def stats_metrics(script_name: str):
    """返回脚本进程最近一次推送的指标快照。数据只在内存中，不落盘。"""
    from module.server.main_manager import mm

    script_process = mm.script_process.get(script_name)
    if script_process is None:
        raise HTTPException(status_code=404, detail=f"Script instance not found: {script_name}")

    now = time.time()
    age_seconds = now - script_process.metrics_updated_at if script_process.metrics_updated_at else None
    snapshot = script_process.latest_metrics or {}
    heartbeat_age_seconds = None
    heartbeat_at = snapshot.get("heartbeat_at")
    if heartbeat_at is not None:
        try:
            heartbeat_age_seconds = now - float(heartbeat_at)
        except (TypeError, ValueError):
            heartbeat_age_seconds = None

    return MetricsResponse(
        script_name=script_name,
        available=bool(snapshot),
        state=int(script_process.state),
        age_seconds=round(age_seconds, 1) if age_seconds is not None else None,
        stale=age_seconds is None or age_seconds > 15,
        heartbeat_age_seconds=round(heartbeat_age_seconds, 1) if heartbeat_age_seconds is not None else None,
        heartbeat_stale=heartbeat_age_seconds is None or heartbeat_age_seconds > 120,
        metrics=snapshot,
    )


@stats_app.get("/{script_name}", response_model=StatsResponse)
async def stats_snapshot(
    script_name: str,
    date_text: str = Query(..., alias="date", description="YYYY-MM-DD"),
):
    target_day = _parse_target_date(date_text)
    return log_stats_service.build_stats(script_name, target_day)


@stats_app.get("/{script_name}/stream")
async def stats_stream(
    script_name: str,
    date_text: str = Query(..., alias="date", description="YYYY-MM-DD"),
):
    target_day = _parse_target_date(date_text)
    if target_day != date.today():
        raise HTTPException(status_code=400, detail="Only today's date supports SSE stream")

    response = StreamingResponse(
        log_stats_service.stream_events(script_name, target_day),
        media_type="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
