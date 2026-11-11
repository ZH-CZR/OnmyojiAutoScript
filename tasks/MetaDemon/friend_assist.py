"""Bounded friend selection before opening the summon queue."""
import copy
import time
import cv2
import numpy as np

from module.atom.click import RuleClick
from module.base.timer import Timer
from module.exception import GameStuckError
from module.logger import logger
from tasks.MetaDemon.config import BossType


class MetaDemonFriendAssist:
    def _try_friend_boss(self, exclude_selected=False):
        # Search only the lower-left friend list. The strongest text match may
        # be a lower row; it still identifies an actual visible friend card.
        remaining = copy.copy(self.I_MD_FRIEND_REMAINING)
        if exclude_selected:
            bounds = self._selected_friend_frame(self.device.image)
            if bounds is None:
                return None  # Cannot distinguish the settling card safely.
            top, bottom = bounds
            # RuleImage expands searches by five pixels. Keep that expansion
            # outside the finished card, so its timer cannot be selected again.
            ranges = [(355, top - 5), (bottom + 6, 615)]
            found = False
            for start, end in ranges:
                if end - start < remaining.image.shape[0]:
                    continue
                remaining.roi_back = (140, start, 100, end - start)
                if self.appear(remaining):
                    found = True
                    break
            if not found:
                return None
        elif not self.appear(remaining):
            return None
        _, y, _, _ = remaining.roi_front
        card = RuleClick((55, y - 25, 65, 55), (55, y - 25, 65, 55),
                         name='MD_FRIEND_CARD')
        self.click(card)
        timeout = Timer(15).start()
        stable = Timer(0.35)
        while not timeout.reached():
            self.screenshot()
            self._reject_unplanned_prepare('好友助战阶段')
            if not self.appear(self.I_MD_FIRE) or self.appear(self.I_MD_SETTLING):
                stable.clear()
                continue
            if not stable.started():
                stable.start()
                continue
            if not stable.reached():
                continue
            if not self.appear(self.I_MD_FRIEND_OWNER):
                logger.info('好友头像不匹配，返回自己发现并继续召唤')
                self._return_to_self_discovery()
                return False
            self._friend_active = True
            self._new_encounter()
            return True
        raise GameStuckError('超鬼王好友详情打开超过15秒')

    def _return_to_self_discovery(self):
        timeout = Timer(15).start()
        response = Timer(2)
        clicks = 0
        while not timeout.reached():
            self.screenshot()
            self._reject_unplanned_prepare('返回自己发现阶段')
            if self.appear(self.I_MD_SELF_SELECTED) and not self.appear(self.I_MD_FRIEND_OWNER):
                self._friend_active = False
                self.cur_boss_type = None
                self.cur_boss_name = ''
                self._new_encounter()
                return
            if clicks < 3 and (not response.started() or response.reached()):
                if self.appear_then_click(self.I_MD_SELF_DISCOVERY, interval=2):
                    clicks += 1
                    response.reset()
        raise GameStuckError('超鬼王未确认返回自己发现，禁止打开召唤队列')

    def _detect_friend_boss_star(self):
        # The central x6 belongs to the skill indicator, not the star rating.
        # Locate the selected card's gold frame and read its six bottom gems.
        previous = None
        for _ in range(3):
            self.screenshot()
            self._reject_unplanned_prepare('好友星级复核阶段')
            if not self.appear(self.I_MD_FIRE) or not self.appear(self.I_MD_FRIEND_OWNER):
                return None
            observed = self._friend_star_observation(self.device.image)
            if observed is not None and observed == previous:
                return observed[0]
            previous = observed
            time.sleep(0.35)
        return None

    @staticmethod
    def _selected_friend_frame(image):
        if image is None or image.shape[:2] != (720, 1280):
            return None
        hsv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2HSV)
        region = hsv[350:620, 40:310]
        gold = ((region[:, :, 0] >= 15) & (region[:, :, 0] <= 40) &
                (region[:, :, 1] >= 70) & (region[:, :, 2] >= 160))
        rows = np.flatnonzero(gold.mean(axis=1) > 0.65) + 350
        bands = np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1)
        centers = [int(np.median(band)) for band in bands if len(band) >= 2]
        frames = [(top, bottom) for top in centers for bottom in centers
                  if 100 <= bottom - top <= 120]
        if len(frames) != 1:
            return None
        return frames[0]

    @staticmethod
    def _friend_star_observation(image):
        frame = MetaDemonFriendAssist._selected_friend_frame(image)
        if frame is None:
            return None
        top, bottom = frame
        hsv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2HSV)
        count = MetaDemonFriendAssist._count_boss_gems(hsv, bottom - 30)
        return (count, top, bottom) if count is not None else None

    @staticmethod
    def _count_boss_gems(hsv, y):
        lit = []
        for index in range(6):
            # Sample the interior of each gem at the actual eleven-pixel spacing.
            patch = hsv[y:y + 8, 56 + 11 * index:64 + 11 * index]
            if patch[:, :, 2].mean() < 70:  # Missing/covered portrait is unknown.
                return None
            # Count filled gems regardless of hue (yellow, purple or mixed).
            # Pixel occupancy separates the gray empty slot from colored edges
            # bleeding in from the neighboring gem; purple need not be bright.
            filled = (patch[:, :, 1] > 110) & (patch[:, :, 2] > 100)
            lit.append(float(filled.mean()) > 0.55)
        count = sum(lit)
        if not 1 <= count <= 6 or lit != [True] * count + [False] * (6 - count):
            return None
        return BossType(count)
