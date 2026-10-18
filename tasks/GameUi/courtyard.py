"""庭院入口交叉定位；原始坐标独立保存，不修改共享素材。"""

from copy import copy
from dataclasses import dataclass


@dataclass(frozen=True)
class Entrance:
    skin: str
    kind: str
    template: object
    roi: tuple


class CourtyardEntrances:
    def __init__(self, groups):
        self.entries = []
        for kind, templates in groups.items():
            for template in templates:
                # 动画变体（如 _14_1）属于同一皮肤，不重复计票。
                suffix = template.name.rsplit(kind, 1)[-1].strip('_')
                skin = suffix.split('_')[0] if suffix else 'default'
                frozen = copy(template)
                frozen.roi_front = list(template.roi_front)
                self.entries.append(Entrance(skin, kind, frozen, tuple(template.roi_front)))

    @staticmethod
    def safe_roi(roi):
        x, y, w, h = roi
        # 过大的旧记录是搜索范围，不视为按钮坐标。
        return (0 <= x < 1280 and 0 <= y < 720 and
                0 < w <= 100 and 0 < h <= 100 and
                x + w <= 1280 and y + h <= 720)

    def infer(self, image, target_kind):
        if image.shape[:2] != (720, 1280):
            return None
        evidence = {}
        for entry in self.entries:
            if entry.kind == target_kind:
                continue
            matcher = copy(entry.template)
            matcher.roi_front = list(entry.roi)
            x, y, w, h = entry.roi
            # 只在原始位置附近识别，避免大搜索范围把其他皮肤认作本皮肤。
            left, top = max(0, x - 16), max(0, y - 16)
            matcher.roi_back = (left, top, min(1280, x + w + 16) - left,
                                min(720, y + h + 16) - top)
            if matcher.match(image, threshold=max(0.85, matcher.threshold)):
                evidence.setdefault(entry.skin, set()).add(entry.kind)
        if not evidence:
            return None
        ranked = sorted(evidence, key=lambda skin: len(evidence[skin]), reverse=True)
        skin = ranked[0]
        if len(ranked) > 1 and len(evidence[skin]) <= len(evidence[ranked[1]]):
            return None
        # 即使竞争皮肤缺少目标入口，也不能先过滤掉它来消除歧义。
        if skin == '5' and target_kind == 'I_PET_HOUSE':
            return None
        targets = {entry.roi for entry in self.entries
                   if entry.skin == skin and entry.kind == target_kind}
        if len(targets) != 1:
            return None
        roi = targets.pop()
        return (skin, roi) if self.safe_roi(roi) else None
