# -*- coding: utf-8 -*-
import json

import pytest

from module.flow.codegen import generate_task_code
from module.flow.errors import FlowSchemaError
from module.flow.rules import RuleLibrary
from module.flow.schema import normalize_flow


def _make_task(root, task="DemoTask"):
    res = root / "tasks" / task / "res"
    res.mkdir(parents=True, exist_ok=True)
    (res / "image.json").write_text(json.dumps([{
        "itemName": "demo_img", "imageName": "res_demo_img.png",
        "roiFront": "100,200,50,60", "roiBack": "0,0,720,1280",
        "method": "Template matching", "threshold": 0.8, "description": "测试图",
    }], ensure_ascii=False), encoding="utf-8")
    (res / "ocr.json").write_text(json.dumps([{
        "itemName": "demo_num", "roiFront": "10,20,100,40", "roiBack": "0,0,720,1280",
        "mode": "Digit", "method": "default", "keyword": "", "description": "次数",
    }], ensure_ascii=False), encoding="utf-8")
    return RuleLibrary(task, root=root)


def test_generate_basic_flow_compiles(tmp_path):
    lib = _make_task(tmp_path)
    flow = normalize_flow({"name": "demo", "task": "DemoTask", "steps": [
        {"op": "wait_image", "rule": "demo_img", "timeout": 5},
        {"op": "click_image", "rule": "demo_img"},
        {"op": "ocr_read", "rule": "demo_num", "store": "times"},
        {"op": "if", "cond": {"left": "var:times", "op": ">=", "right": 1},
         "then": [{"op": "log", "message": "还有次数"}],
         "else": [{"op": "end", "success": False}]},
        {"op": "loop", "count": 2, "body": [{"op": "sleep", "seconds": 0.5}]},
    ]})
    code = generate_task_code(flow, library=lib)
    assert "class ScriptTask(GameUi, DemoTaskAssets)" in code
    assert "self.wait_until_appear(self.I_DEMO_IMG, wait_time=5)" in code
    assert "self.wait_until_appear_then_click(self.I_DEMO_IMG" in code
    assert "self._flow_vars['times'] = self.O_DEMO_NUM.ocr(self.device.image)" in code
    assert "evaluate_condition(" in code
    assert "raise TaskEnd" in code
    assert "for _ in range(2)" in code
    compile(code, "<generated>", "exec")


def test_missing_rule_raises(tmp_path):
    lib = _make_task(tmp_path)
    flow = normalize_flow({"name": "demo", "task": "DemoTask",
                           "steps": [{"op": "wait_image", "rule": "I_NOT_EXIST"}]})
    with pytest.raises(FlowSchemaError):
        generate_task_code(flow, library=lib)


def test_requires_task_name():
    with pytest.raises(FlowSchemaError):
        generate_task_code({"name": "x", "steps": []})

def test_continue_branches_and_empty_blocks_compile(tmp_path):
    lib = _make_task(tmp_path)
    flow = normalize_flow({"name": "demo", "task": "DemoTask", "steps": [
        {"op": "wait_image", "rule": "demo_img", "on_timeout": "continue"},
        {"op": "click_image", "rule": "demo_img", "on_miss": "continue"},
        {"op": "if", "cond": {"left": "var:none", "op": "truthy"}, "then": [], "else": []},
        {"op": "loop", "count": 1, "body": []},
        {"op": "if", "cond": {"left": "var:none", "op": "truthy"},
         "then": [{"op": "log", "message": "禁用步骤", "enabled": False}]},
    ]})
    code = generate_task_code(flow, library=lib)
    assert "if not self.wait_until_appear(" not in code
    assert "if not self.wait_until_appear_then_click(" not in code
    assert "pass" in code
    compile(code, "<generated>", "exec")
