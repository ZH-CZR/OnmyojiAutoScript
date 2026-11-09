"""仅复用同一截图的纯识别结果；动作与交易确认始终重新截图。"""
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import os

import cv2
import numpy as np


def match_hand_templates(image, entries, area, threshold):
    """并行进行只读匹配，不在线程中触碰设备、RPC 或 RuleImage 的 ROI。"""
    x, y, w, h = area
    # 与 RuleImage.match_all_any/corp 保持一致：搜索框外扩5像素，
    # 匹配坐标仍按传入 ROI 回填，避免提速顺带改变既有勾玉裁剪基准。
    left, top = max(0, x - 5), max(0, y - 5)
    source = np.ascontiguousarray(image[top:top + min(720 - top, h + 10),
                                         left:left + min(1280 - left, w + 10)])
    templates = [(name, rule.image) for name, rule in entries]

    def match(entry):
        name, template = entry
        th, tw = template.shape[:2]
        if th > source.shape[0] or tw > source.shape[1]:
            return []
        scores = cv2.matchTemplate(source, template, cv2.TM_CCOEFF_NORMED)
        rows, cols = np.where(scores >= threshold)
        if not len(rows):
            return []
        values = scores[rows, cols].tolist()
        boxes = [[int(cx), int(cy), tw, th] for cx, cy in zip(cols, rows)]
        keep = cv2.dnn.NMSBoxes(boxes, values, threshold, .3)
        return [(values[i], name, (x + boxes[i][0], y + boxes[i][1], tw, th)) for i in keep]

    # 生命周期限定在单次纯计算内，任务退出不遗留线程和设备引用。
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as executor:
        return [candidate for matches in executor.map(match, templates) for candidate in matches]


def frame_cached(reader):
    @wraps(reader)
    def read(self, *args):
        device = getattr(self, 'device', None)
        frame = getattr(device, 'image_frame_id', None)
        if frame is None:
            return reader(self, *args)
        image = device.image
        cache = getattr(self, '_chess_frame_cache', None)
        if cache is None or cache[0] != frame or cache[1] is not image:
            cache = (frame, image, {})
            self._chess_frame_cache = cache
        key = (reader, args)
        if key not in cache[2]:
            cache[2][key] = reader(self, *args)
        return cache[2][key]
    return read
