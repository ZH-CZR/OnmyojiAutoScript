# -*- coding: utf-8 -*-
"""flows/<name>.json 的读写（流程的唯一持久化位置）。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from module.flow.errors import FlowSchemaError
from module.flow.schema import flow_summary, normalize_flow

FLOW_DIR = "flows"
_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def validate_name(name: str) -> str:
    name = str(name or "").strip()
    if not _NAME_RE.match(name):
        raise FlowSchemaError("流程名只能是 1-64 位字母、数字、下划线或短横线")
    return name


class FlowStore:
    """flows 目录下的流程文件管理。"""

    def __init__(self, root=None) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.dir = self.root / FLOW_DIR

    def path(self, name: str) -> Path:
        return self.dir / f"{validate_name(name)}.json"

    def exists(self, name: str) -> bool:
        return self.path(name).is_file()

    def list(self) -> list:
        """列出所有流程（概览），按修改时间倒序。"""
        if not self.dir.is_dir():
            return []
        items = []
        for path in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                flow = self.load(path.stem)
            except FlowSchemaError as e:
                items.append({"name": path.stem, "error": str(e), "steps": 0})
                continue
            summary = flow_summary(flow)
            summary["modified"] = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            items.append(summary)
        return items

    def load(self, name: str) -> dict:
        path = self.path(name)
        if not path.is_file():
            raise FlowSchemaError(f"流程不存在: {name}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise FlowSchemaError(f"流程文件损坏 {path.name}: {e}")
        flow = normalize_flow(raw)
        flow["name"] = path.stem
        return flow

    def save(self, name: str, flow: dict) -> dict:
        name = validate_name(name)
        normalized = normalize_flow(flow)
        normalized["name"] = name
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{name}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        return normalized

    def delete(self, name: str) -> bool:
        path = self.path(name)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def duplicate(self, name: str, new_name: str) -> dict:
        flow = self.load(name)
        flow["name"] = validate_name(new_name)
        return self.save(new_name, flow)
