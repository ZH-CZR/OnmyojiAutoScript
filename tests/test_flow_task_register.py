# -*- coding: utf-8 -*-
"""生成流程任务时的任务登记（config.py / config_model.py / 菜单标记）回归测试。"""
import pytest

from module.server import tool as tool_module


@pytest.fixture()
def manager():
    return tool_module.AnnotatorManager()


def test_snake_case():
    assert tool_module.AnnotatorManager._snake_case("MyDaily") == "my_daily"
    assert tool_module.AnnotatorManager._snake_case("SmokeReg") == "smoke_reg"
    assert tool_module.AnnotatorManager._snake_case("ABCDef") == "abc_def"


def test_config_source_compiles():
    source = tool_module.AnnotatorManager._flow_task_config_source("MyDaily")
    assert "class MyDaily(ConfigBase)" in source
    assert "scheduler: Scheduler = Field(default_factory=Scheduler)" in source
    compile(source, "<task-config>", "exec")


def test_register_config_model_patches_and_is_idempotent(tmp_path, monkeypatch):
    model = tmp_path / "module" / "config" / "config_model.py"
    model.parent.mkdir(parents=True)
    model.write_text(
        "from pydantic import Field\n"
        "from tasks.CustomFlow.config import CustomFlow\n\n\n"
        "class ConfigModel(ConfigBase):\n"
        "    custom_flow: CustomFlow = Field(default_factory=CustomFlow)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tool_module, "PROJECT_ROOT", tmp_path)
    manager = tool_module.AnnotatorManager()

    assert manager._register_config_model("MyDaily") == "patched"
    text = model.read_text(encoding="utf-8")
    assert "from tasks.MyDaily.config import MyDaily" in text
    assert "    my_daily: MyDaily = Field(default_factory=MyDaily)" in text
    compile(text, str(model), "exec")

    assert manager._register_config_model("MyDaily") == "already_registered"
    assert model.read_text(encoding="utf-8") == text


def test_register_config_model_missing_anchor(tmp_path, monkeypatch):
    model = tmp_path / "module" / "config" / "config_model.py"
    model.parent.mkdir(parents=True)
    model.write_text("class ConfigModel(ConfigBase):\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(tool_module, "PROJECT_ROOT", tmp_path)
    manager = tool_module.AnnotatorManager()
    assert manager._register_config_model("MyDaily") == "anchor_missing"
    assert "MyDaily" not in model.read_text(encoding="utf-8")
