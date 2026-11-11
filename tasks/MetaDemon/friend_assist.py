"""Bounded friend selection before opening the summon queue."""
import copy
import re
import time

from module.atom.click import RuleClick
from module.base.timer import Timer
from module.exception import GameStuckError
from module.logger import logger
from tasks.MetaDemon.config import BossType


class MetaDemonFriendAssist:
    def _try_friend_boss(self):
        # Search only the lower-left friend list. The strongest text match may
        # be a lower row; it still identifies an actual visible friend card.
        remaining = copy.copy(self.I_MD_FRIEND_REMAINING)
        if not self.appear(remaining):
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
            if not self.appear(self.I_MD_FIRE):
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
        # Friend cards occupy different rows; never read the empty own card's
        # fixed star coordinates. The selected boss exposes a central x1..x6.
        previous = None
        for _ in range(3):
            self.screenshot()
            self._reject_unplanned_prepare('好友星级复核阶段')
            if not self.appear(self.I_MD_FIRE) or not self.appear(self.I_MD_FRIEND_OWNER):
                return None
            text = str(self.O_MD_FRIEND_STAR.ocr(self.device.image)).strip()
            match = re.fullmatch(r'[xX×✕]?\s*([1-6])', text)
            detected = BossType(int(match[1])) if match else None
            if detected is not None and detected == previous:
                return detected
            previous = detected
            time.sleep(0.35)
        return None
