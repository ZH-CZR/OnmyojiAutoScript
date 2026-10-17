"""Check OASX labels against the shipped translations without running tasks."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel


def required_keys():
    # OASX displays argument.name, not the Pydantic title. Group names and
    # menu labels are also exact translation keys, including their casing.
    for key in ("Home", "Tool"):
        yield key, "home menu", False
    model = ConfigModel()
    for group, tasks in ConfigMenu().menu.items():
        yield group, "menu", False
        for task in tasks:
            yield task, "menu", False
            if task.endswith(" Rule"):
                continue
            for name, fields in model.script_task(task).items():
                yield name, task, False
                for field in fields:
                    yield field["name"], task, False
                    description = field.get("description", "")
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", description):
                        yield description, task, True


def main():
    path = ROOT / "assets/i18n/zh-CN.json"
    translations = json.loads(path.read_text(encoding="utf-8"))
    errors = set()
    keys = set()
    # All schedulers share this flat key with task-specific enable switches.
    # A title from one task must not rename every scheduler's first field.
    if translations.get("enable") != "启用":
        errors.add("scheduler: enable must translate to 启用")
    for key, context, is_help in required_keys():
        keys.add(key)
        value = translations.get(key)
        # Some public OASX help entries intentionally suppress optional help
        # with an empty string; visible labels must always be nonempty.
        if not isinstance(value, str) or (not is_help and (not value.strip() or value == key)):
            errors.add(f"{context}: {key}")
    if errors:
        print("Missing or untranslated labels:\n" + "\n".join(sorted(errors)))
        return 1
    print(f"Chinese translations cover all {len(keys)} menu, group, field and help keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
