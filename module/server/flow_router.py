# This Python file uses the following encoding: utf-8
# @author czr
"""自定义流程（annotator 扩展）的 HTTP 接口。

页面:      GET  /tool/flow
op 规格:   GET  /tool/flow/api/ops
流程 CRUD: GET  /tool/flow/api/list, GET /tool/flow/api/flow/{name},
           POST /tool/flow/api/save, POST /tool/flow/api/delete,
           POST /tool/flow/api/duplicate
规则/枚举: GET  /tool/flow/api/rules?task=, GET /tool/flow/api/tasks,
           GET  /tool/flow/api/pages
单步测试:  POST /tool/flow/api/test
生成任务:  POST /tool/flow/api/generate
"""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from module.flow.errors import FlowSchemaError
from module.flow.rules import RuleLibrary
from module.flow.schema import CMP_OPS, RULE_KINDS_BY_OP, VAR_PREFIX, op_meta
from module.flow.store import FlowStore, validate_name
from module.logger import logger
from module.server.api_logger import ApiLoggingRoute
from module.server.tool import AnnotatorError, annotator_manager

STATIC_DIR = (Path(__file__).parent / "web" / "annotator" / "static").resolve()

flow_app = APIRouter(
    prefix="/tool/flow",
    tags=["flow"],
    route_class=ApiLoggingRoute,
)


class FlowSaveBody(BaseModel):
    name: str
    flow: dict[str, Any]


class FlowNameBody(BaseModel):
    name: str


class FlowDuplicateBody(BaseModel):
    name: str
    new_name: str


class FlowTestBody(BaseModel):
    session_id: str
    flow: dict[str, Any]
    step_id: str = ""
    task: str = ""
    image_id: str = ""
    execute: bool = False


class FlowGenerateBody(BaseModel):
    flow: dict[str, Any]
    task: str = ""


def _raise_flow_error(error: Exception) -> None:
    if isinstance(error, AnnotatorError):
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        )
    if isinstance(error, FlowSchemaError):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_flow", "message": str(error)},
        )
    raise HTTPException(
        status_code=500,
        detail={"code": "flow_internal_error", "message": f"{type(error).__name__}: {error}"},
    )


@flow_app.get("")
async def flow_page():
    page = STATIC_DIR / "flow.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail={"code": "page_not_found", "message": "流程页面不存在"})
    return FileResponse(page)


@flow_app.get("/api/ops")
async def flow_ops():
    return {
        "code": "ok",
        "ops": op_meta(),
        "compare_ops": list(CMP_OPS),
        "var_prefix": VAR_PREFIX,
        "rule_kinds": {op: list(kinds) for op, kinds in RULE_KINDS_BY_OP.items()},
    }


@flow_app.get("/api/list")
async def flow_list():
    store = FlowStore()
    return {"code": "ok", "flows": store.list()}


@flow_app.get("/api/flow/{name}")
async def flow_load(name: str):
    store = FlowStore()
    try:
        validate_name(name)
        return {"code": "ok", "flow": store.load(name)}
    except Exception as error:  # noqa: BLE001 - 统一转 HTTP 错误
        _raise_flow_error(error)


@flow_app.post("/api/save")
async def flow_save(data: FlowSaveBody):
    store = FlowStore()
    try:
        flow = store.save(data.name, data.flow)
        return {"code": "ok", "flow": flow}
    except Exception as error:  # noqa: BLE001
        _raise_flow_error(error)


@flow_app.post("/api/delete")
async def flow_delete(data: FlowNameBody):
    store = FlowStore()
    try:
        removed = store.delete(data.name)
        return {"code": "ok", "removed": removed}
    except Exception as error:  # noqa: BLE001
        _raise_flow_error(error)


@flow_app.post("/api/duplicate")
async def flow_duplicate(data: FlowDuplicateBody):
    store = FlowStore()
    try:
        flow = store.duplicate(data.name, data.new_name)
        return {"code": "ok", "flow": flow}
    except Exception as error:  # noqa: BLE001
        _raise_flow_error(error)


@flow_app.get("/api/tasks")
async def flow_tasks():
    return {"code": "ok", "tasks": annotator_manager.list_task_names()}


@flow_app.get("/api/rules")
async def flow_rules(task: str = ""):
    library = RuleLibrary(task or "CustomFlow")
    defs = [item for item in library.options()]
    return {"code": "ok", "task": library.task, "rules": defs}


@flow_app.get("/api/pages")
async def flow_pages():
    try:
        from tasks.GameUi import page as game_pages

        names = sorted(
            name
            for name in dir(game_pages)
            if name.startswith("page_") and not name.startswith("page___")
        )
    except Exception as error:  # noqa: BLE001 - 页面枚举失败时返回空列表
        logger.warning(f"[flow] 读取 GameUi 页面失败: {error}")
        names = []
    return {"code": "ok", "pages": names}


@flow_app.post("/api/test")
async def flow_test(data: FlowTestBody):
    try:
        result = await run_in_threadpool(
            annotator_manager.test_flow_step,
            data.session_id,
            data.flow,
            data.step_id,
            data.task,
            data.image_id,
            data.execute,
        )
        return {"code": "ok", **result}
    except Exception as error:  # noqa: BLE001
        _raise_flow_error(error)


@flow_app.post("/api/generate")
async def flow_generate(data: FlowGenerateBody):
    try:
        result = await run_in_threadpool(
            annotator_manager.generate_flow_task, data.flow, data.task
        )
        return {"code": "ok", **result}
    except Exception as error:  # noqa: BLE001
        _raise_flow_error(error)
