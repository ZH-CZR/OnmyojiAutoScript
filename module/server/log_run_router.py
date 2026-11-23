# This Python file uses the following encoding: utf-8
"""结构化运行日志的 HTTP 接口（给 OASX 等外部客户端使用）。

所有 JSON 接口统一返回 `{code, error, data}` 包络，并带 no-cache；
文件下载类接口除外（直接返回二进制）。字段名统一 snake_case。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Path as PathParam, Query
from fastapi.responses import FileResponse, JSONResponse

from module.log import run_store
from module.server.api_logger import ApiLoggingRoute
from module.server.log_service import (
    ERROR_LOG_ROOT,
    LogServiceError,
    ensure_child_path,
    log_browser_service,
    normalize_script_name,
)

log_run_app = APIRouter(
    prefix="/logs",
    tags=["log-runs"],
    route_class=ApiLoggingRoute,
)

NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}
MAX_RUNS_LIMIT = run_store.MAX_RUN_LIMIT
_FILE_MEDIA_TYPES = {
    ".json": "application/json",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".png": "image/png",
}


def _ok(data: Any) -> JSONResponse:
    """成功包络。"""
    return JSONResponse(
        content={"code": "ok", "error": None, "data": data},
        headers=NO_CACHE_HEADERS,
    )


def _fail(status_code: int, code: str, message: str) -> JSONResponse:
    """失败包络。"""
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "error": message, "data": None},
        headers=NO_CACHE_HEADERS,
    )


def _parse_day(date_text: str | None) -> date | None:
    """解析可选的 date 查询参数。"""
    if not date_text:
        return None
    try:
        return date.fromisoformat(str(date_text))
    except ValueError:
        raise run_store.RunStoreError(422, "LOG_DATE_INVALID", "date 需要 YYYY-MM-DD 格式")


def _parse_offset(cursor: str | None) -> int:
    """解析分页 cursor（这里就是偏移量）。"""
    if not cursor:
        return 0
    try:
        offset = int(str(cursor))
    except ValueError:
        raise run_store.RunStoreError(400, "LOG_CURSOR_INVALID", "cursor 不是合法的分页位置")
    if offset < 0:
        raise run_store.RunStoreError(400, "LOG_CURSOR_INVALID", "cursor 不能为负数")
    return offset


def _find_run_record(script_name: str, run_id: str) -> dict[str, Any] | None:
    """在索引里找属于该脚本的 run。"""
    normalized = normalize_script_name(script_name)
    for record in run_store.load_index():
        if record.get("run_id") == run_id and record.get("script_name") == normalized:
            return record
    return None


@log_run_app.get("/{script_name}/runs")
async def list_runs(
    script_name: str = PathParam(description="脚本配置名"),
    date_text: str | None = Query(default=None, alias="date", description="按开始日期过滤, YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=MAX_RUNS_LIMIT, description="单页最多返回的 run 数量"),
    cursor: str | None = Query(default=None, description="上一页返回的 next_cursor"),
):
    """分页列出某个脚本的运行记录（新到旧）。"""
    try:
        day = _parse_day(date_text)
        offset = _parse_offset(cursor)
        data = run_store.list_runs(script_name, day=day, limit=limit, offset=offset)
    except run_store.RunStoreError as exc:
        return _fail(exc.status_code, exc.code, exc.message)
    return _ok(data)


@log_run_app.get("/{script_name}/runs/{run_id}")
async def get_run_detail(
    script_name: str = PathParam(description="脚本配置名"),
    run_id: str = PathParam(description="run_id, 形如 20261123-153012-a1b2c3"),
):
    """读取单次运行的摘要与事件流。"""
    try:
        detail = run_store.load_run_detail(script_name, run_id)
    except run_store.RunStoreError as exc:
        return _fail(exc.status_code, exc.code, exc.message)
    if detail is None:
        return _fail(404, "LOG_RUN_NOT_FOUND", "没有找到这次运行记录")
    return _ok(detail)


@log_run_app.get("/{script_name}/stats24h")
async def get_stats_24h(
    script_name: str = PathParam(description="脚本配置名"),
):
    """最近 24 小时滚动统计：成功率、平均耗时、卡点 Top3。"""
    normalized = normalize_script_name(script_name)
    records = [
        record for record in run_store.load_index()
        if record.get("script_name") == normalized
    ]
    data = run_store.compute_stats_24h(records)
    data["script_name"] = normalized
    return _ok(data)


@log_run_app.get("/{script_name}/diagnosis/{run_id}")
async def get_diagnosis(
    script_name: str = PathParam(description="脚本配置名"),
    run_id: str = PathParam(description="run_id"),
):
    """读取某次运行的 diagnosis.json（中文结论 + 技术细节）。"""
    try:
        record = _find_run_record(script_name, run_id)
    except run_store.RunStoreError as exc:
        return _fail(exc.status_code, exc.code, exc.message)
    if record is None:
        return _fail(404, "LOG_RUN_NOT_FOUND", "没有找到这次运行记录")

    folder = str(record.get("diagnosis_dir") or "").strip()
    if not folder:
        return _fail(404, "LOG_DIAGNOSIS_NOT_FOUND", "这次运行没有生成诊断包")
    if Path(folder).name != folder:
        return _fail(400, "LOG_PATH_INVALID", "诊断包目录不合法")

    try:
        path = ensure_child_path(ERROR_LOG_ROOT, ERROR_LOG_ROOT / folder / "diagnosis.json")
    except LogServiceError as exc:
        return _fail(exc.status_code, exc.code, exc.message)
    if not path.is_file():
        return _fail(404, "LOG_DIAGNOSIS_NOT_FOUND", "诊断包已被清理或尚未生成")

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return _fail(500, "LOG_DIAGNOSIS_BROKEN", "诊断包内容无法解析")
    return _ok(data)


@log_run_app.get("/{script_name}/error/files")
async def list_error_files(
    script_name: str = PathParam(description="脚本配置名"),
    date_text: str | None = Query(default=None, alias="date", description="按错误日期过滤, YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=200, description="单页最多返回的错误目录数量"),
    cursor: str | None = Query(default=None, description="上一页返回的 next_cursor"),
):
    """列出某个脚本的错误现场目录，并标记是否带诊断包。"""
    try:
        data = log_browser_service.list_error_logs(
            date_text=date_text,
            script_name=script_name,
            limit=limit,
            cursor=cursor,
        )
    except LogServiceError as exc:
        return _fail(exc.status_code, exc.code, exc.message)

    for item in data.get("items", []):
        error_id = str(item.get("id") or "")
        diagnosis = ERROR_LOG_ROOT / error_id / "diagnosis.json"
        item["has_diagnosis"] = bool(error_id) and diagnosis.is_file()
    return _ok(data)


@log_run_app.get("/{script_name}/error/file")
async def get_error_file(
    script_name: str = PathParam(description="脚本配置名"),
    path: str = Query(description="相对 log/error 的路径, 如 <error_id>/diagnosis.json"),
):
    """按白名单读取错误目录内的文件：log.txt、diagnosis.json、截图 PNG。"""
    normalized = normalize_script_name(script_name)
    relative = str(path or "").strip().replace("\\", "/")
    parts = relative.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return _fail(400, "LOG_PATH_INVALID", "path 需要形如 <error_id>/<文件名>")
    error_id, file_name = parts
    if not error_id.startswith(f"{normalized}_"):
        return _fail(403, "LOG_PATH_FORBIDDEN", "这个错误目录不属于该脚本")
    if file_name not in ("log.txt", "diagnosis.json") and not file_name.lower().endswith(".png"):
        return _fail(400, "LOG_PATH_INVALID", "只允许读取 log.txt、diagnosis.json 或 PNG 截图")

    try:
        error_path = ensure_child_path(ERROR_LOG_ROOT, ERROR_LOG_ROOT / error_id)
        file_path = ensure_child_path(error_path, error_path / file_name)
    except LogServiceError as exc:
        return _fail(exc.status_code, exc.code, exc.message)
    if not file_path.is_file():
        return _fail(404, "LOG_FILE_NOT_FOUND", "文件不存在或已被清理")

    media_type = _FILE_MEDIA_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, headers=NO_CACHE_HEADERS)
