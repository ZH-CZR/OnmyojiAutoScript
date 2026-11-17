# -*- coding: utf-8 -*-
"""把 annotator 标注出来的 tasks/<Task>/res/*.json 解析成运行期规则对象。

res 里的每一项形如（以 image.json 为例）：

    {"itemName": "login", "imageName": "image_login.png",
     "roiFront": "360,1069,58,29", "roiBack": "0,768,720,512",
     "method": "Template matching", "threshold": 0.8, "description": "..."}

dev_tools/assets_extract.py 会把它变成 I_LOGIN 常量，流程里既可以写常量名（I_LOGIN），
也可以写 itemName（login），两种都从这里解析。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from module.atom.click import RuleClick
from module.atom.image import RuleImage
from module.atom.long_click import RuleLongClick
from module.atom.ocr import RuleOcr
from module.atom.swipe import RuleSwipe
from module.flow.errors import FlowSchemaError

# kind -> (json 文件名, const 前缀)；前缀与 dev_tools/assets_extract.py 一致
KIND_FILES: dict[str, tuple[str, str]] = {
    "image": ("image.json", "I"),
    "click": ("click.json", "C"),
    "long_click": ("long_click.json", "L"),
    "swipe": ("swipe.json", "S"),
    "ocr": ("ocr.json", "O"),
}

KIND_LABELS = {
    "image": "图片",
    "click": "点击",
    "long_click": "长按",
    "swipe": "滑动",
    "ocr": "OCR",
}


def parse_roi(value: Any, default: tuple = (0, 0, 0, 0)) -> tuple:
    """把 "x,y,w,h" 或 [x,y,w,h] 解析成 4 元组。"""
    if value is None:
        return tuple(default)
    if isinstance(value, (list, tuple)):
        if len(value) != 4:
            raise FlowSchemaError(f"roi 需要 4 个数字，收到 {value!r}")
        return tuple(int(float(v)) for v in value)
    if isinstance(value, str):
        parts = [p for p in value.replace(" ", "").split(",") if p != ""]
        if len(parts) == 4:
            try:
                return tuple(int(float(p)) for p in parts)
            except ValueError:
                pass
    raise FlowSchemaError(f"无法解析 roi: {value!r}")


@dataclass
class RuleDef:
    """一条标注规则。"""

    kind: str
    item: str
    const: str
    data: dict = field(default_factory=dict)
    json_path: Path | None = None
    image_path: Path | None = None

    @property
    def description(self) -> str:
        return str(self.data.get("description") or "")

    @property
    def label(self) -> str:
        desc = self.description.strip()
        return f"{self.item} {desc}" if desc else self.item

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "item": self.item,
            "const": self.const,
            "description": self.description,
            "image": self.image_path.name if self.image_path else "",
        }


def _read_items(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FlowSchemaError(f"读取规则文件失败 {path}: {e}")
    if not isinstance(raw, list):
        raise FlowSchemaError(f"规则文件必须是数组: {path}")
    return [item for item in raw if isinstance(item, dict)]


def _image_relpath(task: str, image_name: str) -> str:
    """与 assets.py 一致的相对路径写法。"""
    image_name = image_name.replace("\\", "/")
    if image_name.startswith("./"):
        return image_name
    return f"./tasks/{task}/res/{image_name}"


class RuleLibrary:
    """某个任务的规则库：加载 res/*.json，按名字构造规则对象。"""

    def __init__(self, task: str, root: str | Path | None = None) -> None:
        self.task = str(task or "").strip()
        self.root = Path(root) if root is not None else Path.cwd()
        self.res_dir = self.root / "tasks" / self.task / "res"
        self._defs: list[RuleDef] | None = None
        self._index: dict[str, RuleDef] = {}
        self._ambiguous: dict[str, list[str]] = {}
        self._cache: dict[str, Any] = {}

    # -- 加载 ---------------------------------------------------------------
    def load(self) -> "RuleLibrary":
        if self._defs is not None:
            return self
        defs: list[RuleDef] = []
        for kind, (filename, prefix) in KIND_FILES.items():
            path = self.res_dir / filename
            for item in _read_items(path):
                item_name = str(item.get("itemName") or "").strip()
                if not item_name:
                    continue
                image_path = None
                image_name = str(item.get("imageName") or "").strip()
                if image_name:
                    image_path = self.res_dir / image_name
                rule = RuleDef(
                    kind=kind,
                    item=item_name,
                    const=f"{prefix}_{item_name.upper()}",
                    data=dict(item),
                    json_path=path,
                    image_path=image_path,
                )
                defs.append(rule)
                self._index[rule.const] = rule
                if rule.item in self._index:
                    self._ambiguous.setdefault(rule.item, [self._index[rule.item].const])
                    self._ambiguous[rule.item].append(rule.const)
                else:
                    self._index[rule.item] = rule
        self._defs = defs
        return self

    @property
    def defs(self) -> list[RuleDef]:
        self.load()
        return self._defs or []

    # -- 查询 ---------------------------------------------------------------
    def resolve(self, name: str) -> RuleDef:
        key = str(name or "").strip()
        if not key:
            raise FlowSchemaError("规则名不能为空")
        self.load()
        found = self._index.get(key) or self._index.get(key.upper())
        if found is None:
            raise FlowSchemaError(
                f"任务 {self.task} 里没有规则 {name!r}，"
                f"已加载 {len(self.defs)} 条（示例: {', '.join(d.const for d in self.defs[:3]) or '无'}）"
            )
        if key in self._ambiguous:
            raise FlowSchemaError(
                f"规则名 {name!r} 有歧义，请用常量名: {', '.join(self._ambiguous[key])}"
            )
        return found

    def build(self, name: str) -> Any:
        """按名字构造 RuleImage / RuleOcr / RuleClick / RuleSwipe / RuleLongClick。"""
        rule = self.resolve(name)
        cached = self._cache.get(rule.const)
        if cached is not None:
            return cached
        built = _build_rule(self.task, rule)
        self._cache[rule.const] = built
        return built

    def options(self, kinds: tuple[str, ...] | None = None) -> list[dict]:
        """给前端的规则下拉框。"""
        out = []
        for d in self.defs:
            if kinds and d.kind not in kinds:
                continue
            out.append(d.to_dict())
        return out


def _build_rule(task: str, rule: RuleDef) -> Any:
    data = rule.data
    roi_front = parse_roi(data.get("roiFront"))
    roi_back = parse_roi(data.get("roiBack"), default=roi_front)
    if rule.kind == "image":
        return RuleImage(
            roi_front=roi_front,
            roi_back=roi_back,
            method=str(data.get("method") or "Template matching"),
            threshold=float(data.get("threshold") or 0.8),
            file=_image_relpath(task, str(data.get("imageName") or "")),
        )
    if rule.kind == "click":
        return RuleClick(roi_front=roi_front, roi_back=roi_back, name=rule.item)
    if rule.kind == "long_click":
        return RuleLongClick(
            roi_front=roi_front,
            roi_back=roi_back,
            duration=int(data.get("duration") or 1000),
            name=rule.item,
        )
    if rule.kind == "swipe":
        return RuleSwipe(
            roi_front=roi_front,
            roi_back=roi_back,
            mode=str(data.get("mode") or "default"),
            name=rule.item,
        )
    if rule.kind == "ocr":
        return RuleOcr(
            name=rule.item,
            mode=str(data.get("mode") or "Single"),
            method=str(data.get("method") or "Default"),
            roi=roi_front,
            area=roi_back,
            keyword=str(data.get("keyword") or ""),
        )
    raise FlowSchemaError(f"未知的规则类别 {rule.kind!r}")
