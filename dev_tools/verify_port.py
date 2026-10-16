"""Check imported task/config/resource contracts without connecting a device."""
import ast
import importlib
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    manifest = json.loads((ROOT / "upstream/manifest.json").read_text(encoding="utf-8"))
    errors = []
    for name in manifest["files"]:
        path = ROOT / name
        if not path.exists():
            errors.append(f"Missing managed file: {name}")
            continue
        if name.endswith(".py"):
            source = path.read_text(encoding="utf-8-sig")
            try:
                tree = ast.parse(source, filename=name)
                if "marshal.loads" in source or "exec(code_object" in source:
                    errors.append(f"Opaque code: {name}")
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        for keyword in node.keywords:
                            value = keyword.value
                            if keyword.arg == 'file' and isinstance(value, ast.Constant) and isinstance(value.value, str):
                                if value.value.startswith('./tasks/') and not (ROOT / value.value).is_file():
                                    errors.append(f"Missing resource in {name}: {value.value}")
            except SyntaxError as exc:
                errors.append(f"Syntax: {name}: {exc}")
    from module.config.config_menu import ConfigMenu
    from module.config.config_model import ConfigModel
    from module.config.config import Config
    from module.device.device_manager import DeviceManager

    model = ConfigModel()
    model.model_json_schema()
    # Verify the saved representation can round-trip back into the same schema.
    ConfigModel(**json.loads(model.model_dump_json()))
    names = {"Restart"}
    for group, tasks in ConfigMenu().menu.items():
        if group not in ("Config", "Tools"):
            names.update(tasks)
    class OfflineDevice:
        image = None

        def __getattr__(self, name):
            raise AssertionError(f"Task initialization accessed device operation {name}")

    with patch.object(ConfigModel, "read_json", return_value={}), patch.object(ConfigModel, "write_json"):
        config = Config("port_smoke")
        device = OfflineDevice()
        DeviceManager.bind(config, device)
        for name in sorted(names):
            try:
                module = importlib.import_module(f"tasks.{name}.script_task")
                task = module.ScriptTask(config=config)
                if task.device is not device:
                    errors.append(f"Device instance mismatch: {name}")
            except Exception:
                errors.append(f"Task {name}:\n{traceback.format_exc()}")
    for name in ("script", "module.server.app"):
        try:
            importlib.import_module(name)
        except Exception:
            errors.append(f"Entry point {name}:\n{traceback.format_exc()}")
    print(f"Checked {len(manifest['files'])} managed files and {len(names)} task constructors; {len(errors)} errors")
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
