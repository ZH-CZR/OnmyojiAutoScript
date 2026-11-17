# -*- coding: utf-8 -*-
"""把 flow 生成可被调度器直接运行的 tasks/<Task>/script_task.py。

生成物是「能读、能改」的真代码：每个步骤展开成 OAS 已有的调用
（wait_until_appear / wait_until_appear_then_click / swipe / ocr ...），
而不是把 flow.json 塞进任务里解释。条件判断复用 module.flow.schema.evaluate_condition，
保证生成代码与 annotator 里的单步测试语义一致。
"""
from __future__ import annotations

import json
from datetime import datetime

from module.flow.errors import FlowSchemaError
from module.flow.rules import RuleLibrary
from module.flow.runtime import parse_call_args
from module.flow.schema import OP_SPECS, RULE_KINDS_BY_OP, normalize_flow


class _Emitter:
    def __init__(self) -> None:
        self.lines = []
        self.depth = 2  # 类体 1 + 方法体 2

    def line(self, text: str = "") -> None:
        self.lines.append(("    " * self.depth + text) if text else "")

    def comment(self, text: str) -> None:
        self.line(f"# {text}")

    def push(self, header: str) -> None:
        self.line(header)
        self.depth += 1

    def pop(self) -> None:
        self.depth -= 1

    def text(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"


def _rule_const(lib: RuleLibrary, name: str, kinds=()) -> str:
    rule = lib.resolve(name)
    if kinds and rule.kind not in kinds:
        raise FlowSchemaError(f"规则 {name} 是 {rule.kind}，这里需要 {'/'.join(kinds)}")
    return rule.const


def _validate_steps(steps, lib: RuleLibrary) -> None:
    for step in steps:
        for param in OP_SPECS[step["op"]]["params"]:
            if param["type"] != "rule":
                continue
            raw = step.get(param["key"])
            name = raw.strip() if isinstance(raw, str) else ""
            if not name:
                continue
            _rule_const(lib, name, RULE_KINDS_BY_OP.get(step["op"], ()))
        for key in ("then", "else", "body"):
            block = step.get(key)
            if isinstance(block, list) and block:
                _validate_steps(block, lib)

def _emit_wait_image(em, step, lib) -> None:
    const = _rule_const(lib, step["rule"], ("image", "ocr"))
    call = f"self.wait_until_appear(self.{const}, wait_time={float(step['timeout']):g})"
    if step["on_timeout"] != "abort":
        em.line(call)
        return
    em.line(f"if not {call}:")
    em.depth += 1
    em.line(f"raise GameStuckError(f'等待 {const} 超时')")
    em.depth -= 1


def _emit_click_image(em, step, lib) -> None:
    const = _rule_const(lib, step["rule"], ("image", "ocr"))
    if step["mode"] == "until_disappear":
        em.line(f"self.ui_click_until_disappear(self.{const}, interval={float(step['interval']):g})")
        return
    call = f"self.wait_until_appear_then_click(self.{const}, wait_time={float(step['timeout']):g})"
    if step["on_miss"] != "abort":
        em.line(call)
        return
    em.line(f"if not {call}:")
    em.depth += 1
    em.line(f"raise GameStuckError(f'点击 {const} 失败：未出现')")
    em.depth -= 1


def _emit_click_point(em, step, lib) -> None:
    em.line(f"self.device.click(x={int(step['x'])}, y={int(step['y'])}, control_name='FlowClick')")
    if step["delay"]:
        em.line(f"time.sleep({float(step['delay']):g})")


def _emit_long_click(em, step, lib) -> None:
    const = _rule_const(lib, step["rule"], ("image", "click", "long_click"))
    em.line(f"_x, _y = self.{const}.coord()")
    em.line(f"self.device.long_click(x=_x, y=_y, duration={float(step['duration']):g}, control_name='{const}')")


def _emit_swipe(em, step, lib) -> None:
    rule = (step.get("rule") or "").strip()
    if rule:
        const = _rule_const(lib, rule, ("swipe",))
        em.line(f"self.swipe(self.{const})")
    else:
        x1, y1 = int(step["x1"]), int(step["y1"])
        x2 = int(step["x2"] if step.get("x2") is not None else x1)
        y2 = int(step["y2"] if step.get("y2") is not None else y1)
        em.line(f"self.device.swipe(p1=({x1}, {y1}), p2=({x2}, {y2}), control_name='FlowSwipe')")
    if step["delay"]:
        em.line(f"time.sleep({float(step['delay']):g})")


def _emit_ocr_read(em, step, lib) -> None:
    const = _rule_const(lib, step["rule"], ("ocr",))
    store = (step.get("store") or "").strip() or "text"
    em.line("self.screenshot()")
    em.line(f"self._flow_vars[{store!r}] = self.{const}.ocr(self.device.image)")
    if step["on_empty"] == "abort":
        em.line(f"if not str(self._flow_vars[{store!r}] or '').strip():")
        em.depth += 1
        em.line(f"raise GameStuckError(f'OCR {const} 识别为空')")
        em.depth -= 1


def _emit_wait_ocr(em, step, lib) -> None:
    const = _rule_const(lib, step["rule"], ("ocr",))
    keyword = (step.get("keyword") or "").strip()
    em.line(f"_deadline = time.time() + {float(step['timeout']):g}")
    em.line("while time.time() < _deadline:")
    em.depth += 1
    em.line("self.screenshot()")
    em.line(f"_text = self.{const}.ocr(self.device.image)")
    em.line("_text = '' if _text is None else str(_text)")
    if keyword:
        em.line(f"if {keyword!r} in _text:")
    else:
        em.line("if _text.strip():")
    em.depth += 1
    em.line("break")
    em.depth -= 1
    em.line(f"time.sleep({max(0.05, float(step['interval'])):g})")
    em.depth -= 1
    if step["on_timeout"] == "abort":
        em.line("else:")
        em.depth += 1
        em.line(f"raise GameStuckError(f'等待 OCR {const} 超时')")
        em.depth -= 1


def _emit_sleep(em, step, lib) -> None:
    em.line(f"time.sleep({float(step['seconds']):g})")


def _emit_goto_page(em, step, lib) -> None:
    em.line(f"self.goto_page({step['page']})")


def _emit_call(em, step, lib) -> None:
    args = parse_call_args(step.get("args") or "")
    em.line(f"self.{step['func']}(" + ", ".join(repr(a) for a in args) + ")")


def _emit_log(em, step, lib) -> None:
    em.line(f"logger.info({(step.get('message') or '')!r})")


def _emit_end(em, step, lib, task: str) -> None:
    success = bool(step.get("success", True))
    em.line(f"self.set_next_run(task={task!r}, success={success}, finish=False)")
    em.line("raise TaskEnd")


_EMITTERS = {
    "wait_image": _emit_wait_image,
    "click_image": _emit_click_image,
    "click_point": _emit_click_point,
    "long_click": _emit_long_click,
    "swipe": _emit_swipe,
    "ocr_read": _emit_ocr_read,
    "wait_ocr": _emit_wait_ocr,
    "sleep": _emit_sleep,
    "goto_page": _emit_goto_page,
    "call": _emit_call,
    "log": _emit_log,
}


def _emit_block(em, steps, lib, task: str, pages: set) -> bool:
    """生成一个缩进块；块里只有注释或什么都没生成时补 pass，保证语法正确。"""
    start = len(em.lines)
    has_end = _emit_steps(em, steps, lib, task, pages)
    added = em.lines[start:]
    if all((not line.strip()) or line.strip().startswith("#") for line in added):
        em.line("pass")
    return has_end


def _emit_steps(em, steps, lib, task: str, pages: set) -> bool:
    has_end = False
    for step in steps:
        op = step["op"]
        em.comment(f"[{step['id']}] {step.get('title') or OP_SPECS[op]['label']}")
        if not step.get("enabled", True):
            em.comment("已禁用，跳过")
            continue
        if step.get("comment"):
            em.comment(step["comment"])
        if op == "if":
            payload = json.dumps(step["cond"], ensure_ascii=False)
            em.push(f"if evaluate_condition({payload}, self._flow_vars):")
            _emit_block(em, step["then"], lib, task, pages)
            em.pop()
            if step["else"]:
                em.push("else:")
                _emit_block(em, step["else"], lib, task, pages)
                em.pop()
            continue
        if op == "loop":
            count = step["count"]
            if isinstance(count, str) and count.startswith("var:"):
                expr = f"int(float(self._flow_vars.get({count[4:]!r}) or 0))"
            else:
                try:
                    expr = str(int(float(count)))
                except (TypeError, ValueError):
                    raise FlowSchemaError(f"loop 次数不是数字: {count!r}")
            em.push(f"for _ in range({expr}):")
            _emit_block(em, step["body"], lib, task, pages)
            em.pop()
            continue
        if op == "end":
            has_end = True
            _emit_end(em, step, lib, task)
            continue
        if op == "goto_page":
            pages.add(step["page"])
        _EMITTERS[op](em, step, lib)
    return has_end


def generate_task_code(flow: dict, task=None, library=None, source: str = "") -> str:
    """生成 tasks/<Task>/script_task.py 的源码字符串。"""
    flow = normalize_flow(flow)
    task = str(task or flow.get("task") or "").strip()
    if not task:
        raise FlowSchemaError("生成任务代码需要指定任务文件夹名（flow.task，例如 CustomFlow）")
    lib = library or RuleLibrary(task)
    _validate_steps(flow["steps"], lib)

    pages: set = set()
    em = _Emitter()
    has_end = _emit_steps(em, flow["steps"], lib, task, pages)
    body = em.text()
    if not has_end:
        body += "\n        # 流程里没有显式 end 步骤：正常跑完即按成功调度\n"
        body += f"        self.set_next_run(task={task!r}, success=True, finish=False)\n"
        body += "        raise TaskEnd\n"

    doc = flow.get("comment") or flow["name"]
    header = [
        "# -*- coding: utf-8 -*-",
        f"# 由 annotator 流程模式生成，来源: {source or flow['name'] + '.json'}",
        f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# 重新生成会覆盖本文件；需要手写改动请复制成别的任务。",
        "import time",
        "",
        "from module.exception import GameStuckError, TaskEnd",
        "from module.flow.schema import evaluate_condition",
        "from module.logger import logger",
        "from tasks.GameUi.game_ui import GameUi",
    ]
    if pages:
        header.append("from tasks.GameUi.page import " + ", ".join(sorted(pages)))
    header += [
        f"from tasks.{task}.assets import {task}Assets",
        "",
        "",
        f"class ScriptTask(GameUi, {task}Assets):",
        f'    """{doc}"""',
        "",
        "    def run(self) -> None:",
        f"        self._flow_vars = {dict(flow.get('vars') or {})!r}",
    ]
    return "\n".join(header) + "\n" + body

