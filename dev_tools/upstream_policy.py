"""Reviewed boundary between public YYS tasks and the open OAS runtime.

Keep adaptations here so updating the reference never silently restores a
native-only interface. Files outside this selection belong to the open core.
"""
import ast
from pathlib import PurePosixPath

CORE_URL = "https://github.com/xylolit-mu/OnmyojiAutoScript.git"
CORE_COMMIT = "00c083e83a6ad8a258b05536dab8454a77e20325"
UPSTREAM_URL = "https://gitee.com/pattering-rain/yys.git"
EXCLUDED_TASKS = {"SwitchAccountMany", "SwitchAccountOnce", "SwitchAccountLoop", "TongXinTeam"}
CORE_FALLBACK_TASKS = {"Hyakkiyakou"}  # YYS publishes marshal payloads instead of these sources.
PROTECTED = {
    "tasks/Component/config_base.py", "tasks/Component/config_scheduler.py",
    "tasks/GlobalGame/config.py", "tasks/Restart/config_scheduler.py",
    "tasks/Restart/server_update.py",
}
EXTENSIONS = {".py", ".png", ".jpg", ".jpeg", ".json", ".md", ".yaml", ".yml", ".txt", ".gif", ".csv"}


def selected(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe upstream path: {name}")
    if name in PROTECTED or path.suffix.lower() not in EXTENSIONS:
        return False
    if name in {"module/config/config_model.py", "module/config/config_menu.py"}:
        return True
    if name.startswith("module/atom/"):
        return name != "module/atom/ocr.py"
    if len(path.parts) < 2 or path.parts[0] != "tasks":
        return False
    return path.parts[1] not in EXCLUDED_TASKS | CORE_FALLBACK_TASKS | {"Script"} and not name.startswith("tasks/Component/SwitchAccount/")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Upstream interface changed; review adaptation for {old[:80]!r}")
    return text.replace(old, new, 1)


def adapt(name, data, core_model):
    if not name.endswith(".py"):
        return data
    text = data.decode("utf-8-sig").replace("\r\n", "\n")
    if "marshal.loads" in text or "exec(code_object" in text:
        raise ValueError(f"Opaque code in {name}; provide an open implementation before importing it")
    if name == "module/config/config_model.py":
        tree = ast.parse(text)
        imports, fields = [], []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("tasks."):
                if node.module.split(".")[1] not in EXCLUDED_TASKS:
                    imports.append(ast.get_source_segment(text, node))
            if isinstance(node, ast.ClassDef) and node.name == "ConfigModel":
                for field in node.body:
                    if isinstance(field, ast.AnnAssign):
                        if isinstance(field.annotation, ast.Name) and field.annotation.id in EXCLUDED_TASKS:
                            continue
                        fields.append("    " + ast.get_source_segment(text, field))
        methods = core_model[core_model.index("    def __init__("):]
        start = methods.index("    @staticmethod\n    def _migrate_renamed_tasks")
        end = methods.index("    def __setattr__", start)
        methods = methods[:start] + '''    @staticmethod
    def _migrate_renamed_tasks(data: dict) -> dict:
        from module.compat.config_migration import migrate_config
        return migrate_config(data)

''' + methods[end:]
        text = ("from typing import Dict, Any\nimport re\nimport inflection\nfrom pathlib import Path\n"
                "from pydantic import BaseModel, ValidationError, Field\nfrom module.config.utils import *\n"
                "from module.logger import logger\n" + "\n".join(imports) +
                "\n\nclass ConfigModel(ConfigBase):\n" + "\n".join(fields) + "\n\n" + methods)
    elif name == "module/config/config_menu.py":
        text = replace_once(text, 'self.menu["Permission Task"] = ["SwitchAccountMany","TongXinTeam"]',
                            'self.menu["Additional Task"] = ["AutoCake", "MainStory", "MysteryShop", "Tako", "MetaDemon", "Quiz", "KittyShop"]')
        text = replace_once(text, 'self.menu["other"] = ["Hyakkiyakou", "Chess"]', 'self.menu["other"] = ["Chess"]')
    elif name == "tasks/base_task_parent.py":
        text = replace_once(text, "def __init__(self, config: Config) -> None:",
                            "def __init__(self, config: Config, device: Device = None) -> None:")
        text = replace_once(text, "        self._device = None\n", "        self._device = device\n")
        text = replace_once(text, "return DeviceManager.get_device(config=self.config)",
                            "return self._device if self._device is not None else DeviceManager.get_device(config=self.config)")
    elif name == "module/atom/image.py":
        text = replace_once(text, "file: str, path='') -> None:", "file: str, path='', profile='Default') -> None:")
    elif name == "module/atom/click.py":
        text = replace_once(text, "name: str = None) -> None:", "name: str = None, profile='Default') -> None:")
    elif name == "tasks/GameUi/game_ui.py":
        text = replace_once(text, "        for task_dir in base_dir.iterdir():",
                            "        from module.compat.upstream_catalog import PAGE_TASKS\n"
                            "        for task_dir in (base_dir / name for name in PAGE_TASKS):")
    elif name == "tasks/Restart/config.py":
        text = replace_once(text, "class Restart(ConfigBase):", '''class RestartConfig(ConfigBase):
    enable_daily: bool = Field(default=True)
    error_restart_limit: int = Field(default=3, ge=0)


class TasksReset(BaseModel):
    reset_task_datetime_enable: bool = Field(default=False)
    reset_task_datetime: str = Field(default="2023-01-01 00:00:00")


class Restart(ConfigBase):''')
        text = replace_once(text, "    # scheduler: RestartScheduler = Field(default_factory=RestartScheduler)",
                            "    scheduler: RestartScheduler = Field(default_factory=RestartScheduler)\n"
                            "    restart_config: RestartConfig = Field(default_factory=RestartConfig)\n"
                            "    tasks_config_reset: TasksReset = Field(default_factory=TasksReset)")
    return text.encode("utf-8")
