# -*- coding: utf-8 -*-
"""流程编排（flow）的数据结构、op 规格表与校验。

flow.json 是「步骤编排」的唯一事实源，三处共用：
- annotator 前端按 OP_SPECS 渲染步骤表单（/tool/flow/ops 返回这份规格）；
- FlowRunner 按 steps 解释执行（单步测试、真实运行）；
- codegen 按 steps 生成 tasks/<Task>/script_task.py。

步骤是线性数组，if / loop 用嵌套 block 表达，不做 goto：

    {
      "version": 1,
      "name": "area_boss_flow",
      "task": "CustomFlow",
      "vars": {"times": 0},
      "steps": [
        {"id": "s1", "op": "wait_image", "rule": "I_AREA_BOSS", "timeout": 10},
        {"id": "s2", "op": "click_image", "rule": "I_FILTER"},
        {"id": "s3", "op": "loop", "count": 3, "body": [
            {"id": "s3_1", "op": "ocr_read", "rule": "O_AB_NUM_OF_CHALLENGE", "store": "times"}
        ]},
        {"id": "s4", "op": "if", "cond": {"left": "var:times", "op": ">=", "right": 1},
         "then": [{"id": "s4_1", "op": "log", "message": "还有次数"}],
         "else": [{"id": "s4_2", "op": "end", "success": False}]}
      ]
    }
"""
from __future__ import annotations

import copy
from typing import Any

from module.flow.errors import FlowSchemaError

FLOW_VERSION = 1

# 条件比较运算符；truthy / falsy 不需要右侧操作数
CMP_OPS = ("==", "!=", ">", ">=", "<", "<=", "contains", "not_contains", "truthy", "falsy")
_BINARY_OPS = ("==", "!=", ">", ">=", "<", "<=", "contains", "not_contains")

# 条件里操作数写成 "var:名字" 表示取流程变量，否则当字面量
VAR_PREFIX = "var:"

_FALSY_STRINGS = {"", "false", "none", "null", "no"}


def _p(key: str, type_: str, label: str, **kw: Any) -> dict:
    """声明一个步骤参数。type 决定前端控件与校验方式。"""
    params = {"key": key, "type": type_, "label": label}
    params.update(kw)
    return params


OP_SPECS: dict[str, dict[str, Any]] = {
    "wait_image": {
        "label": "等待图片出现",
        "group": "image",
        "desc": "反复截图匹配，直到图片出现；超时按 on_timeout 处理",
        "params": [
            _p("rule", "rule", "图片规则", required=True),
            _p("timeout", "float", "超时(秒)", default=10.0),
            _p("interval", "float", "检查间隔(秒)", default=0.5),
            _p("on_timeout", "enum", "超时处理", default="abort", values=["abort", "continue"]),
        ],
    },
    "click_image": {
        "label": "点击图片",
        "group": "image",
        "desc": "图片出现后点击其匹配位置（或标注的点击位）",
        "params": [
            _p("rule", "rule", "图片规则", required=True),
            _p("mode", "enum", "点击方式", default="once", values=["once", "until_disappear"]),
            _p("timeout", "float", "超时(秒)", default=10.0),
            _p("interval", "float", "间隔(秒)", default=0.5),
            _p("on_miss", "enum", "未出现处理", default="abort", values=["abort", "continue"]),
        ],
    },
    "click_point": {
        "label": "点击坐标",
        "group": "image",
        "desc": "直接点击绝对坐标（720x1280 基准）",
        "params": [
            _p("x", "int", "X", required=True),
            _p("y", "int", "Y", required=True),
            _p("delay", "float", "点击后等待(秒)", default=0.3),
        ],
    },
    "long_click": {
        "label": "长按",
        "group": "image",
        "desc": "按规则位置长按指定时长",
        "params": [
            _p("rule", "rule", "点击/图片规则", required=True),
            _p("duration", "float", "时长(秒)", default=1.0),
        ],
    },
    "swipe": {
        "label": "滑动",
        "group": "image",
        "desc": "用标注好的滑动规则，或直接给起终点坐标",
        "params": [
            _p("rule", "rule", "滑动规则", required=False),
            _p("x1", "int", "起点X", default=None),
            _p("y1", "int", "起点Y", default=None),
            _p("x2", "int", "终点X", default=None),
            _p("y2", "int", "终点Y", default=None),
            _p("duration", "float", "时长(秒)", default=0.2),
            _p("delay", "float", "滑动后等待(秒)", default=0.5),
        ],
    },
    "ocr_read": {
        "label": "OCR 读取",
        "group": "ocr",
        "desc": "识别 OCR 规则区域，把文本/数字存进流程变量，供条件判断使用",
        "params": [
            _p("rule", "rule", "OCR 规则", required=True),
            _p("store", "str", "保存到变量", default="text"),
            _p("on_empty", "enum", "识别为空", default="continue", values=["abort", "continue"]),
        ],
    },
    "wait_ocr": {
        "label": "等待 OCR 文字",
        "group": "ocr",
        "desc": "反复识别，直到文本包含 keyword（或识别到任意文本）",
        "params": [
            _p("rule", "rule", "OCR 规则", required=True),
            _p("keyword", "str", "期望包含的文字", default=""),
            _p("timeout", "float", "超时(秒)", default=10.0),
            _p("interval", "float", "间隔(秒)", default=0.5),
            _p("on_timeout", "enum", "超时处理", default="abort", values=["abort", "continue"]),
        ],
    },
    "if": {
        "label": "条件分支",
        "group": "control",
        "desc": "按流程变量判断，分别执行 then / else 块",
        "params": [
            _p("cond", "cond", "条件", required=True),
            _p("then", "block", "条件成立", default=[]),
            _p("else", "block", "条件不成立", default=[]),
        ],
    },
    "loop": {
        "label": "循环",
        "group": "control",
        "desc": "把 body 执行 count 次（count 可写变量）",
        "params": [
            _p("count", "operand", "次数(数字或 var:变量)", default=1),
            _p("body", "block", "循环体", default=[]),
        ],
    },
    "sleep": {
        "label": "等待",
        "group": "control",
        "desc": "固定等待若干秒",
        "params": [_p("seconds", "float", "秒", default=1.0)],
    },
    "goto_page": {
        "label": "导航页面",
        "group": "task",
        "desc": "调用 GameUi 的 goto_page 做页面导航（page_main / page_area_boss ...）",
        "params": [_p("page", "str", "page 名", required=True)],
    },
    "call": {
        "label": "调用已有函数",
        "group": "task",
        "desc": "调用任务类里的已有方法（例如 boss_fight），复用现成逻辑",
        "params": [
            _p("func", "str", "方法名", required=True),
            _p("args", "str", "参数(逗号分隔，可空)", default=""),
        ],
    },
    "log": {
        "label": "日志",
        "group": "task",
        "desc": "输出一条日志",
        "params": [_p("message", "str", "内容", default="")],
    },
    "end": {
        "label": "结束任务",
        "group": "task",
        "desc": "结束本次流程，并按 success 设置下次运行",
        "params": [_p("success", "bool", "标记成功", default=True)],
    },
}

# op -> {param_key: spec}
PARAM_INDEX: dict[str, dict[str, dict]] = {
    op: {p["key"]: p for p in spec["params"]} for op, spec in OP_SPECS.items()
}

# 所有规则类 op 允许的规则类别，供前端过滤下拉框
RULE_KINDS_BY_OP = {
    "wait_image": ("image",),
    "click_image": ("image",),
    "long_click": ("image", "click", "long_click"),
    "swipe": ("swipe",),
    "ocr_read": ("ocr",),
    "wait_ocr": ("ocr",),
}


def op_meta() -> list[dict]:
    """返回给前端的 op 规格（深拷贝，避免调用方改到表里）。"""
    return [{"op": op, **copy.deepcopy(spec)} for op, spec in OP_SPECS.items()]


def ops_by_op() -> dict[str, dict]:
    return {op: copy.deepcopy(spec) for op, spec in OP_SPECS.items()}


# ---------------------------------------------------------------------------
# 操作数 / 条件
# ---------------------------------------------------------------------------
def normalize_operand(raw: Any) -> Any:
    """操作数：数字、布尔、或字符串（"var:名字" 表示变量）。"""
    if raw is None or isinstance(raw, (bool, int, float)):
        return raw
    return str(raw).strip()


def resolve_operand(operand: Any, variables: dict) -> Any:
    if isinstance(operand, str) and operand.startswith(VAR_PREFIX):
        return variables.get(operand[len(VAR_PREFIX):])
    return operand


def normalize_condition(raw: Any) -> dict:
    """条件可写成 {"left","op","right"}，也可简写成 "var:times"（真值判断）。"""
    if isinstance(raw, str) or isinstance(raw, (int, float, bool)):
        return {"left": normalize_operand(raw), "op": "truthy", "right": None}
    if not isinstance(raw, dict):
        raise FlowSchemaError(f"条件必须是对象，收到 {raw!r}")
    left = normalize_operand(raw.get("left"))
    if left is None or left == "":
        raise FlowSchemaError("条件缺少 left")
    op = str(raw.get("op") or "truthy").strip()
    if op not in CMP_OPS:
        raise FlowSchemaError(f"不支持的条件运算符 {op!r}，可选: {', '.join(CMP_OPS)}")
    right = normalize_operand(raw.get("right")) if op in _BINARY_OPS else None
    return {"left": left, "op": op, "right": right}


def is_truthy(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in _FALSY_STRINGS
    return bool(value)


def compare_values(left: Any, op: str, right: Any) -> bool:
    """比较两个操作数；类型不匹配时做宽松数字/字符串转换。"""
    if op == "truthy":
        return is_truthy(left)
    if op == "falsy":
        return not is_truthy(left)
    if op == "==":
        return _loose_equal(left, right)
    if op == "!=":
        return not _loose_equal(left, right)
    if op in ("contains", "not_contains"):
        text = "" if left is None else str(left)
        target = "" if right is None else str(right)
        found = target == "" or target in text
        return found if op == "contains" else not found
    try:
        lv = float(left)
        rv = float(right)
    except (TypeError, ValueError):
        raise FlowSchemaError(f"比较运算 {op} 需要数字: left={left!r} right={right!r}")
    if op == ">":
        return lv > rv
    if op == ">=":
        return lv >= rv
    if op == "<":
        return lv < rv
    return lv <= rv


def _loose_equal(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, (int, float)) and isinstance(right, str):
        try:
            return float(left) == float(right)
        except ValueError:
            return False
    if isinstance(right, (int, float)) and isinstance(left, str):
        try:
            return float(left) == float(right)
        except ValueError:
            return False
    if isinstance(left, bool) != isinstance(right, bool):
        return str(left).lower() == str(right).lower()
    return left == right


def evaluate_condition(cond: dict, variables: dict) -> bool:
    left = resolve_operand(cond["left"], variables)
    right = resolve_operand(cond.get("right"), variables)
    return compare_values(left, cond["op"], right)


def describe_condition(cond: dict) -> str:
    """给日志/代码注释用的一行描述。"""
    left = str(cond["left"])
    op = cond["op"]
    if op in ("truthy", "falsy"):
        return f"{left} is {'true' if op == 'truthy' else 'false'}"
    return f"{left} {op} {cond['right']}"


# ---------------------------------------------------------------------------
# 步骤 / 流程 校验
# ---------------------------------------------------------------------------
def _as_float(op: str, key: str, raw: Any, default: float) -> float:
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise FlowSchemaError(f"{op}.{key} 需要数字，收到 {raw!r}")


def _as_int(op: str, key: str, raw: Any, default: int | None) -> int | None:
    if raw is None or raw == "":
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        raise FlowSchemaError(f"{op}.{key} 需要整数，收到 {raw!r}")


def _as_bool(op: str, key: str, raw: Any, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off", ""):
        return False
    raise FlowSchemaError(f"{op}.{key} 需要布尔值，收到 {raw!r}")


def _as_str(op: str, key: str, raw: Any, default: str) -> str:
    if raw is None:
        return default
    return str(raw)


def _normalize_param(op: str, param: dict, raw: Any) -> Any:
    key = param["key"]
    type_ = param["type"]
    default = param.get("default")
    if type_ == "rule":
        value = _as_str(op, key, raw, "")
        if param.get("required") and not value:
            raise FlowSchemaError(f"{op} 缺少必填参数 {key}")
        return value
    if type_ == "int":
        return _as_int(op, key, raw, default)
    if type_ == "float":
        return _as_float(op, key, raw, default if default is not None else 0.0)
    if type_ == "bool":
        return _as_bool(op, key, raw, bool(default))
    if type_ == "str":
        return _as_str(op, key, raw, default if default is not None else "")
    if type_ == "enum":
        value = _as_str(op, key, raw, default)
        if value not in param["values"]:
            raise FlowSchemaError(
                f"{op}.{key} 只能是 {param['values']}，收到 {value!r}"
            )
        return value
    if type_ == "operand":
        return normalize_operand(raw if raw is not None else default)
    if type_ == "cond":
        return normalize_condition(raw)
    if type_ == "block":
        return normalize_block(raw)
    raise FlowSchemaError(f"未知的参数类型 {type_}")


def normalize_block(raw: Any, prefix: str = "s", used: set | None = None) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise FlowSchemaError(f"步骤块必须是数组，收到 {type(raw).__name__}")
    return normalize_steps(raw, prefix=prefix, used=used)


_STEP_META_KEYS = ("id", "op", "title", "enabled", "comment")


def normalize_step(step: Any, index: int, used_ids: set, prefix: str = "s") -> dict:
    if not isinstance(step, dict):
        raise FlowSchemaError(f"第 {index + 1} 个步骤必须是对象，收到 {type(step).__name__}")
    op = str(step.get("op") or "").strip()
    spec = OP_SPECS.get(op)
    if spec is None:
        raise FlowSchemaError(
            f"第 {index + 1} 个步骤的 op 未知: {op!r}，可选: {', '.join(OP_SPECS)}"
        )
    sid = str(step.get("id") or "").strip() or f"{prefix}{index + 1}"
    base_id, suffix = sid, 2
    while sid in used_ids:
        sid = f"{base_id}_{suffix}"
        suffix += 1
    used_ids.add(sid)
    out: dict[str, Any] = {
        "id": sid,
        "op": op,
        "title": str(step.get("title") or spec["label"]),
        "enabled": _as_bool(op, "enabled", step.get("enabled"), True),
        "comment": str(step.get("comment") or ""),
    }
    for param in spec["params"]:
        key = param["key"]
        if param["type"] == "block":
            # 嵌套块用 <父 id>_1 这样的 id，保证整棵树内 id 唯一
            raw = step.get(key, None)
            out[key] = normalize_block(raw, prefix=f"{sid}_", used=used_ids)
            continue
        if param["type"] == "cond":
            raw = step.get(key, None)
            if raw is None and param.get("default") is not None:
                raw = param["default"]
            out[key] = _normalize_param(op, param, raw)
            continue
        out[key] = _normalize_param(op, param, step.get(key, None))
    extra = {k: v for k, v in step.items() if k not in _STEP_META_KEYS and k not in PARAM_INDEX[op]}
    if extra:
        out["extra"] = extra
    return out


def normalize_steps(raw_steps: Any, prefix: str = "s", used: set | None = None) -> list[dict]:
    if not isinstance(raw_steps, list):
        raise FlowSchemaError(f"steps 必须是数组，收到 {type(raw_steps).__name__}")
    if used is None:
        used = set()
    steps: list[dict] = []
    for index, step in enumerate(raw_steps):
        steps.append(normalize_step(step, index, used, prefix=prefix))
    return steps


def normalize_flow(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise FlowSchemaError(f"flow 必须是对象，收到 {type(raw).__name__}")
    name = str(raw.get("name") or "").strip() or "flow"
    variables = raw.get("vars") or raw.get("variables") or {}
    if not isinstance(variables, dict):
        raise FlowSchemaError("vars 必须是对象")
    flow = {
        "version": int(raw.get("version") or FLOW_VERSION),
        "name": name,
        "comment": str(raw.get("comment") or ""),
        "task": str(raw.get("task") or "").strip(),
        "vars": {str(k): v for k, v in variables.items()},
        "steps": normalize_steps(raw.get("steps") or []),
    }
    return flow


def find_step(steps: list[dict], step_id: str) -> dict | None:
    """在（已标准化的）步骤树里按 id 找步骤。"""
    for step in steps:
        if step["id"] == step_id:
            return step
        for key in ("then", "else", "body"):
            block = step.get(key)
            if isinstance(block, list):
                found = find_step(block, step_id)
                if found is not None:
                    return found
    return None


def iter_steps(steps: list[dict], depth: int = 0):
    """深度优先遍历所有步骤，产出 (step, depth)。"""
    for step in steps:
        yield step, depth
        for key in ("then", "else", "body"):
            block = step.get(key)
            if isinstance(block, list) and block:
                yield from iter_steps(block, depth + 1)


def count_steps(steps: list[dict]) -> int:
    return sum(1 for _ in iter_steps(steps))


def flow_summary(flow: dict) -> dict:
    """给前端的概览信息。"""
    return {
        "name": flow.get("name", ""),
        "task": flow.get("task", ""),
        "comment": flow.get("comment", ""),
        "vars": flow.get("vars", {}),
        "steps": count_steps(flow.get("steps") or []),
    }
