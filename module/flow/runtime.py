# -*- coding: utf-8 -*-
"""流程解释执行器：单步测试与真实运行共用同一套解释逻辑。

host 是鸭子类型的执行后端（见 module/flow/host.py）：
- TaskFlowHost   真实设备，包一层 BaseTask；
- PreviewFlowHost 单帧预览，只做匹配/识别，不点真机。

流程里的失败语义：
- 某步按配置（on_timeout/on_miss/on_empty=abort）判定失败 -> 抛 FlowAbort，整轮中止；
- 执到 end 步骤 -> 抛 FlowEnd，正常结束并带上 success；
- 其他异常 -> 包成 FlowAbort 抛出，但失败步骤仍会记录在 results 里。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from module.flow.errors import FlowAbort, FlowEnd, FlowSchemaError
from module.flow.schema import (
    evaluate_condition,
    find_step,
    normalize_flow,
    resolve_operand,
)
from module.logger import logger

MAX_FLOW_STEPS = 5000


@dataclass
class StepResult:
    """单步执行结果。"""

    step_id: str
    op: str
    ok: bool
    message: str = ""
    depth: int = 0
    duration: float = 0.0
    vars: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stepId": self.step_id,
            "op": self.op,
            "ok": self.ok,
            "message": self.message,
            "depth": self.depth,
            "duration": round(self.duration, 3),
            "vars": dict(self.vars),
            "data": dict(self.data),
        }


def parse_call_args(text: str) -> tuple:
    """"1, 'abc', true" -> (1, 'abc', True)。"""
    text = (text or "").strip()
    if not text:
        return ()
    return tuple(_literal(part) for part in _split_args(text) if part.strip() != "")


def _split_args(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote = ""
    for char in text:
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
            continue
        if char == ",":
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _literal(text: str) -> Any:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("none", "null"):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


class FlowRunner:
    """解释执行一份 flow。"""

    def __init__(self, host: Any, flow: Any, max_steps: int = MAX_FLOW_STEPS) -> None:
        self.host = host
        self.flow = normalize_flow(flow)
        self.vars: dict[str, Any] = dict(self.flow.get("vars") or {})
        self.results: list[StepResult] = []
        self.steps_run = 0
        self.max_steps = max_steps
        self._ended = False

    # -- 对外 ---------------------------------------------------------------
    def run(self) -> list[StepResult]:
        """跑完整份流程（FlowEnd / FlowAbort 会抛给调用方）。"""
        try:
            self._run_block(self.flow["steps"], 0)
        finally:
            self._log_results()
        return self.results

    def run_step(self, step_id: str) -> list[StepResult]:
        """只跑一个步骤（含它自己的嵌套块），用于界面单步测试。"""
        step = find_step(self.flow["steps"], step_id)
        if step is None:
            raise FlowSchemaError(f"找不到步骤 {step_id}")
        try:
            self._run_step(step, 0)
        finally:
            self._log_results()
        return self.results

    @property
    def variables(self) -> dict:
        return dict(self.vars)

    # -- 执行 ---------------------------------------------------------------
    def _run_block(self, steps: list[dict], depth: int) -> None:
        for step in steps:
            self._run_step(step, depth)

    def _run_step(self, step: dict, depth: int) -> StepResult | None:
        if self._ended:
            return None
        started = time.perf_counter()
        result = StepResult(step_id=step["id"], op=step["op"], ok=True, depth=depth)
        if not step.get("enabled", True):
            result.message = "已禁用，跳过"
            result.duration = time.perf_counter() - started
            result.vars = dict(self.vars)
            self.results.append(result)
            return result
        try:
            self._tick(step)
            ok, message, data = self._dispatch(step, depth)
            result.ok = ok
            result.message = message
            result.data = data
        except FlowEnd as e:
            result.message = f"流程结束（success={e.success}）"
            result.data["success"] = e.success
            self.results.append(result)
            self._ended = True
            raise
        except FlowAbort as e:
            result.ok = False
            result.message = str(e)
            self.results.append(result)
            raise
        except Exception as e:
            result.ok = False
            result.message = f"{type(e).__name__}: {e}"
            self.results.append(result)
            raise FlowAbort(f"{step['id']} {step['title'] or step['op']} 执行失败: {e}") from e
        result.duration = time.perf_counter() - started
        result.vars = dict(self.vars)
        self.results.append(result)
        return result

    def _tick(self, step: dict) -> None:
        self.steps_run += 1
        if self.steps_run > self.max_steps:
            raise FlowAbort(
                f"流程步数超过上限 {self.max_steps}，疑似死循环（最后一步 {step['id']}）"
            )

    def _log_results(self) -> None:
        if not self.results:
            return
        last = self.results[-1]
        logger.info(
            f"flow {self.flow['name']} 执行 {len(self.results)} 步，"
            f"末步 {last.step_id}/{last.op} ok={last.ok} {last.message}"
        )

    def _dispatch(self, step: dict, depth: int) -> tuple[bool, str, dict]:
        handler = getattr(self, "_op_" + step["op"], None)
        if handler is None:
            raise FlowAbort(f"未实现的 op: {step['op']}")
        return handler(step, depth)

    def _sleep(self, seconds: float) -> None:
        if not seconds or seconds <= 0:
            return
        sleeper = getattr(self.host, "sleep", None)
        if callable(sleeper):
            sleeper(seconds)
        else:
            time.sleep(seconds)

    # -- 各 op --------------------------------------------------------------
    def _op_wait_image(self, step: dict, depth: int):
        name = step["rule"]
        timeout = float(step["timeout"])
        interval = max(0.05, float(step["interval"]))
        waiter = getattr(self.host, "wait_until_appear", None)
        if callable(waiter):
            ok = bool(waiter(name, timeout))
            attempts = 1
        else:
            deadline = time.monotonic() + timeout
            attempts = 0
            ok = False
            while True:
                attempts += 1
                if self.host.appear(name):
                    ok = True
                    break
                if time.monotonic() >= deadline:
                    break
                self._sleep(interval)
        if ok:
            return True, f"{name} 出现", {"attempts": attempts}
        message = f"{name} 在 {timeout:g}s 内未出现"
        if step["on_timeout"] == "continue":
            return False, message + "（继续）", {"attempts": attempts}
        raise FlowAbort(message)

    def _op_click_image(self, step: dict, depth: int):
        name = step["rule"]
        timeout = float(step["timeout"])
        on_miss = step["on_miss"]
        if step["mode"] == "until_disappear":
            interval = max(0.05, float(step["interval"]))
            ok = self.host.ui_click_until_disappear(name, interval)
            message = f"{name} 反复点击直到消失" if ok else f"{name} 没有消失"
        else:
            ok = self.host.wait_until_appear_then_click(name, timeout)
            message = f"{name} 已点击" if ok else f"{name} 在 {timeout:g}s 内未出现"
        if ok:
            return True, message, {}
        if on_miss == "continue":
            return False, message + "（继续）", {}
        raise FlowAbort(message)

    def _op_click_point(self, step: dict, depth: int):
        x, y = int(step["x"]), int(step["y"])
        self.host.click_point(x, y)
        self._sleep(float(step["delay"]))
        return True, f"点击 ({x}, {y})", {"x": x, "y": y}

    def _op_long_click(self, step: dict, depth: int):
        duration = float(step["duration"])
        self.host.long_click(step["rule"], duration)
        return True, f"长按 {step['rule']} {duration:g}s", {"duration": duration}

    def _op_swipe(self, step: dict, depth: int):
        coords = None
        if step.get("x1") is not None and step.get("y1") is not None:
            coords = (
                int(step["x1"]),
                int(step["y1"]),
                int(step["x2"] if step.get("x2") is not None else step["x1"]),
                int(step["y2"] if step.get("y2") is not None else step["y1"]),
            )
        rule = step.get("rule") or ""
        if not rule and coords is None:
            raise FlowAbort("swipe 需要 rule 或起终点坐标")
        duration = float(step["duration"])
        self.host.swipe(rule=rule, coords=coords, duration=duration)
        self._sleep(float(step["delay"]))
        return True, f"滑动 {rule or coords}", {"coords": coords, "rule": rule}

    def _op_ocr_read(self, step: dict, depth: int):
        name = step["rule"]
        text = self.host.ocr(name)
        value = "" if text is None else str(text)
        store = (step.get("store") or "").strip()
        if store:
            self.vars[store] = value
        message = f"{name} -> {store or 'text'}={value!r}"
        if value.strip() == "" and step["on_empty"] == "abort":
            raise FlowAbort(f"{name} 识别为空")
        return True, message, {"text": value, "store": store}

    def _op_wait_ocr(self, step: dict, depth: int):
        name = step["rule"]
        keyword = (step.get("keyword") or "").strip()
        timeout = float(step["timeout"])
        waiter = getattr(self.host, "wait_until_ocr", None)
        text = ""
        if callable(waiter):
            ok = bool(waiter(name, keyword, timeout))
        else:
            interval = max(0.05, float(step["interval"]))
            deadline = time.monotonic() + timeout
            text = ""
            ok = False
            while True:
                text = "" if (self.host.ocr(name) is None) else str(self.host.ocr(name))
                if (keyword in text) if keyword else bool(text.strip()):
                    ok = True
                    break
                if time.monotonic() >= deadline:
                    break
                self._sleep(interval)
        if ok:
            detail = f"{name} 识别到 {text!r}" if text else f"{name} 识别到 {keyword!r}"
            return True, detail, {"text": text}
        message = f"{name} 在 {timeout:g}s 内未识别到 {keyword!r}（最后: {text!r}）"
        if step["on_timeout"] == "continue":
            return False, message + "（继续）", {"text": text}
        raise FlowAbort(message)

    def _op_if(self, step: dict, depth: int):
        cond = step["cond"]
        try:
            hit = evaluate_condition(cond, self.vars)
        except FlowSchemaError as e:
            raise FlowAbort(str(e))
        branch = "then" if hit else "else"
        self._run_block(step[branch], depth + 1)
        return True, f"条件 {branch}（{cond['left']} {cond['op']} {cond['right']}）", {"branch": branch}

    def _op_loop(self, step: dict, depth: int):
        raw = resolve_operand(step["count"], self.vars)
        try:
            count = int(float(raw))
        except (TypeError, ValueError):
            raise FlowAbort(f"loop 次数无效: {raw!r}")
        if count < 0:
            raise FlowAbort(f"loop 次数不能为负: {count}")
        for _ in range(count):
            self._run_block(step["body"], depth + 1)
        return True, f"循环 {count} 次完成", {"count": count}

    def _op_sleep(self, step: dict, depth: int):
        seconds = float(step["seconds"])
        self._sleep(seconds)
        return True, f"等待 {seconds:g}s", {}

    def _op_goto_page(self, step: dict, depth: int):
        page = step["page"]
        self.host.goto_page(page)
        return True, f"导航到 {page}", {"page": page}

    def _op_call(self, step: dict, depth: int):
        func = step["func"]
        args = parse_call_args(step.get("args") or "")
        result = self.host.call(func, args)
        return True, f"调用 {func}{args}", {"result": result}

    def _op_log(self, step: dict, depth: int):
        message = step.get("message") or ""
        log = getattr(self.host, "log", None)
        if callable(log):
            log(message)
        else:
            logger.info(message)
        return True, message, {}

    def _op_end(self, step: dict, depth: int):
        raise FlowEnd(bool(step.get("success", True)))
