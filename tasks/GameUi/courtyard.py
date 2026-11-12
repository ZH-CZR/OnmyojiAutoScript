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
        # 原始 roi_front 是有效点击区域，只校验屏幕边界，不限制区域大小。
        return (0 <= x < 1280 and 0 <= y < 720 and
                w > 0 and h > 0 and
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

    def match_pet(self, image, diagnostics=None):
        """只返回当前截图中可靠的宠物屋位置，不改写共享素材坐标。"""
        if image.shape[:2] != (720, 1280):
            return None
        matches = []
        for entry in self.entries:
            if entry.kind != 'I_PET_HOUSE':
                continue
            matcher = copy(entry.template)
            matcher.roi_front = list(entry.roi)
            # 原始范围用于皮肤兜底；直接识别的点击范围取实际素材大小。
            # 素材已缓存时 load_image 不会再修正尺寸，必须显式设置。
            height, width = matcher.image.shape[:2]
            matcher.roi_front[2:] = [width, height]
            matched = matcher.match(image, threshold=max(0.85, matcher.threshold))
            if diagnostics is not None:
                diagnostics.append((matcher.name, round(matcher.max_val, 3),
                                    tuple(matcher.roi_front) if matched else None))
            if matched:
                if self.safe_roi(matcher.roi_front):
                    matches.append((entry.skin, matcher))
        if not matches:
            return None
        matches.sort(key=lambda pair: pair[1].max_val, reverse=True)
        skins = {skin for skin, _ in matches}
        if len(skins) != 1:
            # 不同皮肤可能截取同一建筑的不同局部（12/13 的宠物屋）。
            # 这里不推断皮肤或选择最高分皮肤，只在所有命中共同覆盖同一
            # 点击区域时返回交集。不同位置、仅边缘重叠仍按冲突拒绝。
            rois = [matcher.roi_front for _, matcher in matches]
            left = max(roi[0] for roi in rois)
            top = max(roi[1] for roi in rois)
            right = min(roi[0] + roi[2] for roi in rois)
            bottom = min(roi[1] + roi[3] for roi in rois)
            if right <= left or bottom <= top:
                return None
            common_area = (right - left) * (bottom - top)
            if common_area < 0.8 * min(roi[2] * roi[3] for roi in rois):
                return None
            button = matches[0][1]
            button.roi_front = [left, top, right - left, bottom - top]
            return ('overlap:' + ','.join(sorted(skins)), button)
        return matches[0]
