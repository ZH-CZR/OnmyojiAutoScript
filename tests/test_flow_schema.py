# -*- coding: utf-8 -*-
import pytest

from module.flow.errors import FlowSchemaError
from module.flow.schema import (
    count_steps,
    evaluate_condition,
    find_step,
    flow_summary,
    normalize_flow,
    normalize_steps,
)


def test_normalize_flow_fills_defaults():
    flow = normalize_flow({"name": "demo", "steps": [{"op": "sleep", "seconds": 1}]})
    assert flow["version"] == 1
    assert flow["task"] == ""
    assert flow["vars"] == {}
    step = flow["steps"][0]
    assert step["id"] == "s1"
    assert step["enabled"] is True
    assert step["title"]  # 未填标题时用 op 的中文名


def test_normalize_steps_dedupes_ids():
    steps = normalize_steps([
        {"id": "s1", "op": "sleep", "seconds": 1},
        {"id": "s1", "op": "sleep", "seconds": 2},
    ])
    assert [s["id"] for s in steps] == ["s1", "s1_2"]


def test_normalize_rejects_unknown_op():
    with pytest.raises(FlowSchemaError):
        normalize_flow({"steps": [{"op": "teleport"}]})


def test_normalize_requires_rule_name():
    with pytest.raises(FlowSchemaError):
        normalize_flow({"steps": [{"op": "wait_image"}]})


def test_normalize_rejects_bad_enum():
    with pytest.raises(FlowSchemaError):
        normalize_flow({"steps": [{"op": "wait_image", "rule": "I_X", "on_timeout": "explode"}]})


def test_condition_supports_var_and_numeric_compare():
    variables = {"times": "3"}
    cond = {"left": "var:times", "op": ">=", "right": 3}
    assert evaluate_condition(cond, variables) is True


def test_condition_contains_and_falsy():
    assert evaluate_condition({"left": "var:t", "op": "contains", "right": "战"}, {"t": "挑战"}) is True
    assert evaluate_condition({"left": "var:t", "op": "falsy"}, {"t": ""}) is True
    assert evaluate_condition({"left": "var:t", "op": "truthy"}, {"t": "x"}) is True


def test_count_and_find_and_summary():
    flow = normalize_flow({"name": "demo", "steps": [
        {"op": "sleep", "seconds": 1},
        {"op": "loop", "count": 2, "body": [{"op": "log", "message": "hi"}]},
    ]})
    assert count_steps(flow["steps"]) == 3
    assert find_step(flow["steps"], "s2_1")["op"] == "log"
    summary = flow_summary(flow)
    assert summary["steps"] == 3
    assert summary["name"] == "demo"
