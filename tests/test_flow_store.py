# -*- coding: utf-8 -*-
import pytest

from module.flow.errors import FlowSchemaError
from module.flow.store import FlowStore


def test_save_load_list_delete(tmp_path):
    store = FlowStore(tmp_path)
    store.save("demo_flow", {"name": "ignored", "steps": [{"op": "sleep", "seconds": 1}]})
    assert store.exists("demo_flow")
    flow = store.load("demo_flow")
    assert flow["name"] == "demo_flow"
    assert flow["steps"][0]["id"] == "s1"

    listed = store.list()
    assert [item["name"] for item in listed] == ["demo_flow"]
    assert listed[0]["steps"] == 1

    store.duplicate("demo_flow", "demo_copy")
    assert sorted(item["name"] for item in store.list()) == ["demo_copy", "demo_flow"]

    assert store.delete("demo_copy") is True
    assert store.delete("demo_copy") is False


def test_rejects_bad_name(tmp_path):
    store = FlowStore(tmp_path)
    with pytest.raises(FlowSchemaError):
        store.save("../evil", {"steps": []})
    with pytest.raises(FlowSchemaError):
        store.load("nope")


def test_corrupt_file_is_reported(tmp_path):
    store = FlowStore(tmp_path)
    (tmp_path / "flows").mkdir()
    (tmp_path / "flows" / "broken.json").write_text("{not json", encoding="utf-8")
    listed = store.list()
    assert listed[0]["name"] == "broken"
    assert "error" in listed[0]
