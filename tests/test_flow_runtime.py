# -*- coding: utf-8 -*-
import pytest

from module.flow.errors import FlowAbort, FlowEnd
from module.flow.runtime import FlowRunner


class StubHost:
    def __init__(self, appear=True, text="", click_ok=True):
        self.appear_ok = appear
        self.text = text
        self.click_ok = click_ok
        self.calls = []
        self.sleeps = []

    def screenshot(self):
        return None

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log(self, message):
        self.calls.append(("log", message))

    def appear(self, name):
        self.calls.append(("appear", name))
        return self.appear_ok

    def wait_until_appear(self, name, timeout=10.0):
        self.calls.append(("wait_until_appear", name, timeout))
        return self.appear_ok

    def wait_until_appear_then_click(self, name, timeout=10.0):
        self.calls.append(("wait_until_appear_then_click", name, timeout))
        return self.click_ok

    def ui_click_until_disappear(self, name, interval=0.5):
        self.calls.append(("ui_click_until_disappear", name))
        return True

    def click_point(self, x, y):
        self.calls.append(("click_point", x, y))

    def long_click(self, name, duration=1.0):
        self.calls.append(("long_click", name, duration))

    def swipe(self, rule="", coords=None, duration=0.2):
        self.calls.append(("swipe", rule, coords, duration))
        return True

    def goto_page(self, page):
        self.calls.append(("goto_page", page))

    def call(self, func, args=()):
        self.calls.append(("call", func, tuple(args)))
        return "called"

    def ocr(self, name):
        self.calls.append(("ocr", name))
        return self.text

    def wait_until_ocr(self, name, keyword="", timeout=10.0):
        self.calls.append(("wait_until_ocr", name, keyword))
        return keyword in self.text if keyword else bool(self.text.strip())


def test_run_sequence_and_vars():
    host = StubHost(text="3")
    flow = {"name": "f", "steps": [
        {"op": "wait_image", "rule": "I_A"},
        {"op": "ocr_read", "rule": "O_N", "store": "times"},
        {"op": "sleep", "seconds": 0.1},
    ]}
    results = FlowRunner(host, flow).run()
    assert [r.op for r in results] == ["wait_image", "ocr_read", "sleep"]
    assert results[1].vars["times"] == "3"
    assert host.sleeps == [0.1]


def test_condition_branches():
    host = StubHost()
    flow = {"name": "f", "vars": {"times": 0}, "steps": [
        {"op": "if", "cond": {"left": "var:times", "op": ">=", "right": 1},
         "then": [{"op": "log", "message": "还有"}],
         "else": [{"op": "log", "message": "没有"}]},
    ]}
    FlowRunner(host, flow).run()
    assert ("log", "没有") in host.calls


def test_loop_runs_body_n_times():
    host = StubHost()
    flow = {"name": "f", "steps": [
        {"op": "loop", "count": 3, "body": [{"op": "click_point", "x": 1, "y": 2, "delay": 0}]},
    ]}
    FlowRunner(host, flow).run()
    assert host.calls.count(("click_point", 1, 2)) == 3


def test_end_raises_flow_end():
    host = StubHost()
    flow = {"name": "f", "steps": [{"op": "end", "success": False}]}
    with pytest.raises(FlowEnd) as info:
        FlowRunner(host, flow).run()
    assert info.value.success is False


def test_wait_image_timeout_aborts_or_continues():
    flow = {"name": "f", "steps": [{"op": "wait_image", "rule": "I_A", "timeout": 0.1}]}
    with pytest.raises(FlowAbort):
        FlowRunner(StubHost(appear=False), flow).run()

    flow["steps"][0]["on_timeout"] = "continue"
    results = FlowRunner(StubHost(appear=False), flow).run()
    assert results[0].ok is False


def test_run_step_only_executes_one():
    host = StubHost()
    flow = {"name": "f", "steps": [
        {"op": "click_point", "x": 1, "y": 1, "delay": 0},
        {"op": "click_point", "x": 2, "y": 2, "delay": 0},
    ]}
    runner = FlowRunner(host, flow)
    runner.run_step("s2")
    assert host.calls == [("click_point", 2, 2)]


def test_disabled_step_is_skipped():
    host = StubHost()
    flow = {"name": "f", "steps": [{"op": "click_point", "x": 9, "y": 9, "enabled": False}]}
    results = FlowRunner(host, flow).run()
    assert host.calls == []
    assert "禁用" in results[0].message
