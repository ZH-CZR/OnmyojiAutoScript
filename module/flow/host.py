# -*- coding: utf-8 -*-
"""flow 的执行后端。

- TaskFlowHost：真实设备，所有动作都转给已有的 BaseTask / Device 实现；
- PreviewFlowHost：单帧预览，只对一张截图做匹配/识别，动作只记录不执行（可选外发）。

两者都满足 FlowRunner 需要的鸭子接口：appear / wait_until_appear /
wait_until_appear_then_click / ui_click_until_disappear / click_point / long_click /
swipe / ocr / wait_until_ocr / goto_page / call / log / sleep / screenshot。
"""
from __future__ import annotations

import time
from typing import Any, Callable

import cv2

from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.atom.swipe import RuleSwipe
from module.flow.errors import FlowSchemaError
from module.flow.rules import RuleLibrary
from module.logger import logger


class TaskFlowHost:
    """真实执行：包一层 BaseTask，尽量复用 OAS 已有的点击/匹配/导航实现。"""

    def __init__(self, task: Any, rules: RuleLibrary) -> None:
        self.task = task
        self.rules = rules

    # -- 基础 ---------------------------------------------------------------
    def _rule(self, name: str) -> Any:
        return self.rules.build(name)

    def screenshot(self):
        return self.task.screenshot()

    def sleep(self, seconds: float) -> None:
        time.sleep(float(seconds))

    def log(self, message: str) -> None:
        logger.info(f"[flow] {message}")

    # -- 匹配 ---------------------------------------------------------------
    def appear(self, name: str) -> bool:
        self.task.screenshot()
        return bool(self.task.appear(self._rule(name)))

    def wait_until_appear(self, name: str, timeout: float = 10.0) -> bool:
        return bool(self.task.wait_until_appear(self._rule(name), wait_time=timeout))

    def wait_until_appear_then_click(self, name: str, timeout: float = 10.0) -> bool:
        return bool(self.task.wait_until_appear_then_click(self._rule(name), wait_time=timeout))

    def ui_click_until_disappear(self, name: str, interval: float = 0.5) -> bool:
        return bool(self.task.ui_click_until_disappear(self._rule(name), interval=interval))

    # -- 动作 ---------------------------------------------------------------
    def click_point(self, x: int, y: int) -> None:
        self.task.device.click(x=x, y=y, control_name="FlowClick")

    def long_click(self, name: str, duration: float = 1.0) -> None:
        rule = self._rule(name)
        x, y = rule.coord()
        self.task.device.long_click(x=x, y=y, duration=float(duration),
                                    control_name=getattr(rule, "name", "") or "FlowLongClick")

    def swipe(self, rule: str = "", coords: tuple | None = None,
              duration: float = 0.2) -> bool:
        if rule:
            target = self._rule(rule)
            if not isinstance(target, RuleSwipe):
                raise FlowSchemaError(f"{rule} 不是滑动规则")
            return bool(self.task.swipe(target))
        if not coords:
            raise FlowSchemaError("swipe 需要 rule 或坐标")
        x1, y1, x2, y2 = coords
        self.task.device.swipe(p1=(x1, y1), p2=(x2, y2), control_name="FlowSwipe")
        return True

    def goto_page(self, page: str) -> None:
        from tasks.GameUi import page as game_pages

        destination = getattr(game_pages, page, None)
        if destination is None:
            raise FlowSchemaError(f"没有这个 page: {page}（示例: page_main / page_area_boss）")
        self.task.goto_page(destination)

    def call(self, func: str, args: tuple = ()) -> Any:
        method = getattr(self.task, func, None)
        if not callable(method):
            raise FlowSchemaError(f"任务里没有可调用的方法 {func!r}")
        return method(*args)

    # -- OCR ----------------------------------------------------------------
    def _ocr_text(self, name: str) -> str:
        rule = self._rule(name)
        result = rule.ocr(self.task.device.image)
        return "" if result is None else str(result)

    def ocr(self, name: str) -> str:
        self.task.screenshot()
        return self._ocr_text(name)

    def wait_until_ocr(self, name: str, keyword: str = "", timeout: float = 10.0) -> bool:
        self._rule(name)  # 先校验规则存在
        deadline = time.monotonic() + float(timeout)
        while True:
            self.task.screenshot()
            text = self._ocr_text(name)
            if keyword:
                if keyword in text:
                    return True
            elif text.strip():
                return True
            if time.monotonic() >= deadline:
                logger.warning(f"Wait until ocr {name} timeout")
                return False
            time.sleep(0.5)


def _image_match(rule: RuleImage, image: Any) -> bool:
    """单帧本地匹配：模板匹配直接走 cv2，不依赖远端图像服务。

    与 dev_tools/assets_test.py 的 detect_image_detail 保持一致：
    先在 roi_back 里裁图，再和模板图做 TM_CCOEFF_NORMED；命中后回写 roi_front，
    这样 coord() 拿到的就是真实命中位置。SIFT 等方法退回规则自带实现。
    """
    name = getattr(rule, "name", "")
    try:
        if rule.is_template_match:
            source = rule.corp(image)
            mat = rule.image
            if mat is None or source.shape[0] < mat.shape[0] or source.shape[1] < mat.shape[1]:
                logger.warning(f"[flow-preview] {name} 的 ROI 比模板还小，按不匹配处理")
                return False
            res = cv2.matchTemplate(source, mat, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            similarity = float(max_val)
            threshold = float(rule.threshold)
            matched = similarity >= threshold
            logger.info(f"[flow-preview] {name} 相似度 {similarity:.4f} / 阈值 {threshold}")
            if matched:
                rule.roi_front[0] = int(max_loc[0] + rule.roi_back[0])
                rule.roi_front[1] = int(max_loc[1] + rule.roi_back[1])
                rule.roi_front[2] = int(mat.shape[1])
                rule.roi_front[3] = int(mat.shape[0])
            return matched
        return bool(rule.test_match(image))
    except Exception as e:  # noqa: BLE001 - 单帧预览不因单条规则异常中断
        logger.warning(f"[flow-preview] {name} 匹配失败: {e}")
        return False


def _ocr_read(rule: RuleOcr, image: Any) -> str:
    """单帧 OCR：用本地 OCR 识别 roi 区域，按 keyword 优先、否则取最高分的框。"""
    name = getattr(rule, "name", "")
    try:
        boxed = rule.detect_and_ocr(image, logDisplay=False)
    except Exception as e:  # noqa: BLE001 - OCR 异常按识别为空处理
        logger.warning(f"[flow-preview] {name} OCR 失败: {e}")
        return ""
    if not boxed:
        return ""

    selected = None
    keyword = str(getattr(rule, "keyword", "") or "")
    if keyword:
        for item in boxed:
            text = str(item.ocr_text or "")
            if keyword in text or text == keyword:
                selected = item
                break
    if selected is None:
        selected = max(boxed, key=lambda item: float(item.score))
    return str(selected.ocr_text or "")


class PreviewFlowHost:
    """单帧预览：动作只记录，不碰真机。

    :param image: 720x1280 RGB 截图
    :param rules: RuleLibrary
    :param action_sink: 可选回调（收到 click/swipe/long_click/goto_page/call 动作字典），
                        server 可据此把动作真正下发给采集 worker
    :param frame_source: 可选回调，返回最新帧；给了才会在等待类 op 里轮询
    """

    MAX_PREVIEW_CLICKS = 20

    def __init__(self, image: Any, rules: RuleLibrary,
                 action_sink: Callable[[dict], None] | None = None,
                 frame_source: Callable[[], Any] | None = None) -> None:
        self.image = image
        self.rules = rules
        self.action_sink = action_sink
        self.frame_source = frame_source
        self.actions: list[dict] = []
        self.logs: list[str] = []
        self.sleeps: list[float] = []

    # -- 基础 ---------------------------------------------------------------
    def _rule(self, name: str) -> Any:
        return self.rules.build(name)

    def screenshot(self):
        if self.frame_source is not None:
            try:
                frame = self.frame_source()
            except Exception as e:  # noqa: BLE001 - 采集端异常不应打断预览
                logger.warning(f"flow preview frame_source 失败: {e}")
                frame = None
            if frame is not None:
                self.image = frame
        return self.image

    def sleep(self, seconds: float) -> None:
        # 预览不真的睡，避免单步测试被等待类 op 卡住
        self.sleeps.append(round(float(seconds), 3))

    def log(self, message: str) -> None:
        self.logs.append(str(message))
        logger.info(f"[flow-preview] {message}")

    def _emit(self, action: dict) -> None:
        action = dict(action)
        self.actions.append(action)
        if callable(self.action_sink):
            try:
                self.action_sink(action)
            except Exception as e:  # noqa: BLE001 - 动作下发失败只记录
                logger.warning(f"flow preview 动作下发失败: {e}")

    # -- 匹配 ---------------------------------------------------------------
    def _match(self, name: str) -> bool:
        rule = self._rule(name)
        if isinstance(rule, RuleOcr):
            return bool(_ocr_read(rule, self.image).strip())
        if isinstance(rule, RuleImage):
            return _image_match(rule, self.image)
        match = getattr(rule, "match", None)
        if not callable(match):
            raise FlowSchemaError(f"{name} 不能做图像匹配（只有图片/OCR 规则可以）")
        return bool(match(self.image))

    def appear(self, name: str) -> bool:
        return self._match(name)

    def wait_until_appear(self, name: str, timeout: float = 10.0) -> bool:
        if self.frame_source is None:
            return self._match(name)
        deadline = time.monotonic() + float(timeout)
        while True:
            self.screenshot()
            if self._match(name):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.2)

    def wait_until_appear_then_click(self, name: str, timeout: float = 10.0) -> bool:
        if not self.wait_until_appear(name, timeout):
            return False
        return self.appear_then_click(name)

    def appear_then_click(self, name: str) -> bool:
        if not self._match(name):
            return False
        rule = self._rule(name)
        x, y = rule.coord()
        self._emit({"type": "click", "x": int(x), "y": int(y),
                    "control": getattr(rule, "name", "")})
        return True

    def ui_click_until_disappear(self, name: str, interval: float = 0.5) -> bool:
        rule = self._rule(name)
        for _ in range(self.MAX_PREVIEW_CLICKS):
            if not self._match(name):
                return True
            x, y = rule.coord()
            self._emit({"type": "click", "x": int(x), "y": int(y),
                        "control": getattr(rule, "name", "")})
            self.sleep(interval)
            if self.frame_source is None:
                # 没有新帧就无从判断是否消失，按「已点一次」处理
                return True
            self.screenshot()
        return False

    # -- 动作 ---------------------------------------------------------------
    def click_point(self, x: int, y: int) -> None:
        self._emit({"type": "click", "x": int(x), "y": int(y), "control": "FlowClick"})

    def long_click(self, name: str, duration: float = 1.0) -> None:
        rule = self._rule(name)
        x, y = rule.coord()
        self._emit({"type": "long_click", "x": int(x), "y": int(y),
                    "duration": float(duration), "control": getattr(rule, "name", "")})

    def swipe(self, rule: str = "", coords: tuple | None = None,
              duration: float = 0.2) -> bool:
        if rule:
            target = self._rule(rule)
            if not isinstance(target, RuleSwipe):
                raise FlowSchemaError(f"{rule} 不是滑动规则")
            x1, y1, x2, y2 = target.coord()
        elif coords:
            x1, y1, x2, y2 = coords
        else:
            raise FlowSchemaError("swipe 需要 rule 或坐标")
        self._emit({"type": "swipe", "x1": int(x1), "y1": int(y1),
                    "x2": int(x2), "y2": int(y2), "duration": float(duration)})
        return True

    def goto_page(self, page: str) -> bool:
        self._emit({"type": "goto_page", "page": str(page)})
        return True

    def call(self, func: str, args: tuple = ()) -> Any:
        self._emit({"type": "call", "func": str(func), "args": list(args)})
        return None

    # -- OCR ----------------------------------------------------------------
    def ocr(self, name: str) -> str:
        rule = self._rule(name)
        if not isinstance(rule, RuleOcr):
            raise FlowSchemaError(f"{name} 不是 OCR 规则")
        return _ocr_read(rule, self.image)

    def wait_until_ocr(self, name: str, keyword: str = "", timeout: float = 10.0) -> bool:
        rule = self._rule(name)
        if not isinstance(rule, RuleOcr):
            raise FlowSchemaError(f"{name} 不是 OCR 规则")
        if self.frame_source is None:
            text = _ocr_read(rule, self.image)
            return (keyword in text) if keyword else bool(text.strip())
        deadline = time.monotonic() + float(timeout)
        while True:
            self.screenshot()
            text = _ocr_read(rule, self.image)
            if (keyword in text) if keyword else bool(text.strip()):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.2)
