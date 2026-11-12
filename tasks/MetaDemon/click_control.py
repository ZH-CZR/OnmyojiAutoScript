"""Task-local retry intervals; new page actions can proceed immediately."""
import copy
import time

import cv2
import numpy as np
from module.atom.ocr import RuleOcr


class MetaDemonClickControl:
    def _meta_frame(self):
        image = getattr(self.device, 'image', None)
        if image is None:
            return None
        return np.asarray(image).copy()

    def _meta_page_changed(self, previous):
        current = self._meta_frame()
        if previous is None or current is None:
            return False
        if previous.shape != current.shape:
            return True
        if previous.ndim >= 2:
            previous = cv2.resize(previous, (160, 90), interpolation=cv2.INTER_AREA)
            current = cv2.resize(current, (160, 90), interpolation=cv2.INTER_AREA)
        difference = np.abs(current.astype(np.float32) - previous.astype(np.float32))
        if difference.ndim == 0:
            return bool(difference)
        if difference.ndim == 3:
            difference = difference.max(axis=2)
        # Ignore small highlights, number changes and background rendering noise.
        return float(np.mean(difference > 32)) >= 0.15

    def _meta_retry_ready(self, key, target=None):
        previous = getattr(self, '_meta_previous_click', None)
        if previous is None or time.monotonic() - previous[1] >= 2 or self._meta_page_changed(previous[2]):
            return True
        if previous[0] != key:
            if target is not None and not isinstance(target, RuleOcr) and hasattr(target, 'match') and previous[2] is not None:
                # A newly appearing control proves a UI transition even when
                # only a small dialog/button changed. Match on an independent
                # rule so old-frame coordinates cannot overwrite the live rule.
                return not copy.deepcopy(target).match(previous[2])
            return True  # Explicit coordinate/RuleClick steps have their own checks.
        return False

    def _meta_record_click(self, key, submitted_at, frame):
        self._meta_previous_click = (key, submitted_at, frame)
        self._meta_click_needs_screenshot = True

    def _meta_wait_retry(self, key, target=None):
        while not self._meta_retry_ready(key, target):
            previous = self._meta_previous_click
            remaining = 2 - (time.monotonic() - previous[1])
            time.sleep(min(0.1, max(0, remaining)))
            self.screenshot()
            # A queued unconditional click belongs to the old page. Return to
            # its caller to select the next action rather than replaying it.
            if self._meta_page_changed(previous[2]):
                return False
            if target is not None and not isinstance(target, RuleOcr) and hasattr(target, 'match') and not copy.deepcopy(target).match(self.device.image):
                return False
        return True

    def _meta_observe_click(self):
        if getattr(self, '_meta_click_needs_screenshot', False):
            self._meta_click_needs_screenshot = False
            self.screenshot()

    def screenshot(self, *args, **kwargs):
        # Base screenshot may itself recognize settlement/invitation markers.
        self._meta_click_needs_screenshot = False
        return super().screenshot(*args, **kwargs)

    def appear(self, *args, **kwargs):
        self._meta_observe_click()
        return super().appear(*args, **kwargs)

    def click(self, click=None, interval=None):
        self._meta_observe_click()
        key = ('click', getattr(click, 'name', None))
        if not self._meta_wait_retry(key, click):
            return False
        if getattr(click, 'burst_count', 1) > 1:
            click = copy.copy(click)
            click.burst_count = 1
        submitted_at, frame = time.monotonic(), self._meta_frame()
        result = super().click(click, interval)
        # BaseTask.click returns False after an actual click with no interval.
        if click is not None and (result or not interval):
            self._meta_record_click(key, submitted_at, frame)
        return result

    def appear_then_click(self, target, *args, **kwargs):
        self._meta_observe_click()
        key = ('image', target.name)
        if not self._meta_retry_ready(key, target):
            return False
        submitted_at, frame = time.monotonic(), self._meta_frame()
        result = super().appear_then_click(target, *args, **kwargs)
        if result:
            self._meta_record_click(key, submitted_at, frame)
        return result

    def ocr_appear_click(self, target, *args, **kwargs):
        self._meta_observe_click()
        key = ('ocr', target.name)
        if not self._meta_retry_ready(key):
            return False
        submitted_at, frame = time.monotonic(), self._meta_frame()
        result = super().ocr_appear_click(target, *args, **kwargs)
        if result:
            self._meta_record_click(key, submitted_at, frame)
        return result

    def _meta_click(self, *args, **kwargs):
        self._meta_observe_click()
        key = ('coordinate', kwargs.get('control_name') or (args, tuple(sorted(kwargs.items()))))
        if not self._meta_wait_retry(key):
            return False
        submitted_at, frame = time.monotonic(), self._meta_frame()
        self.device.click(*args, **kwargs)
        self._meta_record_click(key, submitted_at, frame)
        return True
