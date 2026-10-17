"""One-time, reviewed import of public task sources from a local checkout.

The persistent maintenance entry point is upstream_sync.py. This bootstrap is
kept to document the initial selection; it never reads or copies native binaries.
"""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {"SwitchAccountOnce", "SwitchAccountLoop", "SwitchAccountMany", "TongXinTeam"}
PROTECTED = {"tasks/Component/config_base.py", "tasks/Component/config_scheduler.py",
             "tasks/GlobalGame/config.py"}


def main():
    source = Path(sys.argv[1]).resolve()
    manifest_path = ROOT / "upstream/manifest.json"
    if manifest_path.exists():
        raise SystemExit("Already bootstrapped; use upstream_sync.py")
    tracked = subprocess.check_output(["git", "-C", str(source), "ls-files", "-z"]).decode().split("\0")
    records = {}
    for name in tracked:
        parts = Path(name).parts
        task = parts[1] if len(parts) > 1 and parts[0] == "tasks" else None
        eligible = task and task not in BLOCKED | {"Script"} and not name.startswith("tasks/Component/SwitchAccount/")
        eligible = eligible or name.startswith("module/atom/") and not name.endswith("/ocr.py")
        if not eligible or name in PROTECTED or Path(name).suffix.lower() not in {".py", ".png", ".jpg", ".json", ".md", ".yaml", ".yml", ".txt", ".gif", ".csv"}:
            continue
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        records[name] = {"upstream_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    # Keep the open core's schema/serialization/API implementation, using the
    # upstream task names and fields so upstream user configurations remain usable.
    upstream_model = (source / "module/config/config_model.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(upstream_model)
    imports = []
    fields = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module.startswith("tasks."):
            task = node.module.split(".")[1]
            if task not in BLOCKED:
                imports.append(ast.get_source_segment(upstream_model, node))
        if isinstance(node, ast.ClassDef) and node.name == "ConfigModel":
            for field in node.body:
                if isinstance(field, ast.AnnAssign) and isinstance(field.annotation, ast.Name) and field.annotation.id not in BLOCKED:
                    fields.append("    " + ast.get_source_segment(upstream_model, field))
    local_path = ROOT / "module/config/config_model.py"
    local = local_path.read_text(encoding="utf-8-sig")
    methods = local[local.index("    def __init__("):]
    start = methods.index("    @staticmethod\n    def _migrate_renamed_tasks")
    end = methods.index("    def __setattr__", start)
    methods = methods[:start] + '''    @staticmethod
    def _migrate_renamed_tasks(data: dict) -> dict:
        """Accept the open core's old shop name without rewriting upstream tasks."""
        data = dict(data)
        if 'weekly_purchase' in data and 'rich_man' not in data:
            data['rich_man'] = data.pop('weekly_purchase')
        if data.get('running_task') == 'WeeklyPurchase':
            data['running_task'] = 'RichMan'
        return data

''' + methods[end:]
    prefix = "from typing import Dict, Any\nimport re\nimport inflection\nfrom pathlib import Path\nfrom pydantic import BaseModel, ValidationError, Field\nfrom module.config.utils import *\nfrom module.logger import logger\n"
    local_path.write_text(prefix + "\n".join(imports) + "\n\nclass ConfigModel(ConfigBase):\n" + "\n".join(fields) + "\n\n" + methods, encoding="utf-8")
    menu = (source / "module/config/config_menu.py").read_text(encoding="utf-8-sig")
    menu = menu.replace('self.menu["Permission Task"] = ["SwitchAccountMany","TongXinTeam"]', 'self.menu["Additional Task"] = ["AutoCake", "MainStory", "MysteryShop", "Tako", "MetaDemon", "Quiz", "KittyShop"]')
    (ROOT / "module/config/config_menu.py").write_text(menu, encoding="utf-8")
    manifest = {"schema_version": 1, "upstream_url": "https://gitee.com/pattering-rain/yys.git",
                "upstream_commit": subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"]).decode().strip(),
                "core_url": "https://github.com/xylolit-mu/OnmyojiAutoScript.git",
                "core_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip(),
                "reuse_permission": "User confirmed permission to reuse public sources on 2026-10-16; upstream checkout contains no root LICENSE.",
                "excluded_tasks": sorted(BLOCKED), "files": records}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(records)} public source/resource files")


if __name__ == "__main__":
    main()
