"""Summon once between friend attacks, preserving the interrupted encounter."""
import cv2
import numpy as np

from module.atom.click import RuleClick
from module.base.timer import Timer
from module.exception import GameStuckError
from module.logger import logger


class MetaDemonTicketPriority:
    def _prioritize_ticket_boss(self):
        if not getattr(self, '_friend_active', False):
            return True
        fatigue, _ = self._read_fatigue()
        checked = getattr(self, '_tickets_checked', False)
        if fatigue <= 70 or (checked and not self.has_summon_ticket):
            return True
        frame = self._selected_friend_frame(self.device.image)
        if frame is None:
            raise GameStuckError('超鬼王助战卡片身份无法保存，禁止中途切换')
        top, bottom = frame
        # Keep the portrait and name, excluding gems/HP and the changing timer.
        portrait = self.device.image[top + 8:bottom - 40, 48:300].copy()
        snapshot = (portrait, self.cur_boss_type, self.cur_boss_name,
                    getattr(self, '_encounter_attempts', 0))
        self._return_to_self_discovery()
        if self.check_and_switch_ticket(_summon_only=True):
            logger.info('疲劳超过70，先攻打本次召唤的最高星鬼王，再恢复原助战')
            while True:
                if not getattr(self, '_resident_mode', False):
                    if self.State.done:
                        return False
                    self.check_fatigue()
                else:
                    fatigue, total = self._read_fatigue()
                    if not self.conf.meta_demon_config.auto_tea and fatigue >= total:
                        return False
                    self._resident_checkpoint()
                if not (self._select_attack() and self._prepare_lineup()
                        and self.check_and_switch_powerful()):
                    return False
                if getattr(self, '_resident_mode', False):
                    self._resident_checkpoint()
                previous = getattr(self, '_ticket_priority_own_battle', False)
                self._ticket_priority_own_battle = True
                try:
                    self.start_battle()
                finally:
                    self._ticket_priority_own_battle = previous
                self.screenshot()
                self._reject_unplanned_prepare('召唤战后恢复阶段')
                if self.appear(self.I_MD_SETTLING):
                    # Restore/verify the saved friend now; probing the queue
                    # here would put us back into the own-boss settlement wait.
                    self._tickets_checked = False
                    return self._resume_ticket_friend(snapshot)
                if not self.appear(self.I_MD_FIRE):
                    break
                self._refresh_current_boss_type(clear_on_failure=True)
            # Refresh the boolean after consuming a ticket, without summoning again.
            self.check_and_switch_ticket(_summon_only=True, _probe_only=True)
        return self._resume_ticket_friend(snapshot)

    @staticmethod
    def _locate_ticket_friend(image, portrait):
        if image is None or image.shape[:2] != (720, 1280):
            return None
        region = image[355:580, 48:300]
        if portrait.size == 0 or float(np.std(portrait)) < 1:
            return None
        # Compare both the portrait and the upper name strip. The right-hand
        # countdown/HP below the name is deliberately excluded from matching.
        faces = cv2.matchTemplate(region[:, :84], portrait[:, :84], cv2.TM_CCOEFF_NORMED)[:, 0]
        names = cv2.matchTemplate(region[:, 84:], portrait[:20, 84:], cv2.TM_CCOEFF_NORMED)[:, 0]
        scores = np.minimum(faces, names[:len(faces)])
        best = int(np.argmax(scores))
        if scores[best] < 0.97:
            return None
        other = scores.copy()
        other[max(0, best - 35):best + 36] = -1
        if float(other.max()) >= float(scores[best]) - 0.02:
            raise GameStuckError('超鬼王原助战卡片匹配不唯一，禁止猜测恢复目标')
        return 355 + best

    def _resume_ticket_friend(self, snapshot):
        portrait, star, name, attempts = snapshot
        timeout = Timer(15).start()
        stable = Timer(0.35)
        clicked = False
        while not timeout.reached():
            self.screenshot()
            self._reject_unplanned_prepare('恢复原助战阶段')
            y = self._locate_ticket_friend(self.device.image, portrait)
            if y is None:
                # The friend may have been defeated by someone else. Never
                # transfer its attack count to another card at the old position.
                logger.info('原助战鬼王已不在可见列表，本轮不猜测其他目标')
                return False
            if not clicked:
                card = RuleClick((55, y, 65, 45), (55, y, 65, 45), name='MD_RESUME_FRIEND')
                self.click(card)
                clicked = True
                continue
            frame = self._selected_friend_frame(self.device.image)
            ready = (frame is not None and abs(frame[0] + 8 - y) <= 3
                     and self.appear(self.I_MD_FIRE) and self.appear(self.I_MD_FRIEND_OWNER)
                     and not self.appear(self.I_MD_SETTLING))
            if not ready:
                stable.clear()
                continue
            if not stable.started():
                stable.start()
                continue
            if not stable.reached():
                continue
            self._friend_active = True
            self._friend_settlement_pending = False
            self._refresh_current_boss_type(clear_on_failure=True)
            if self.cur_boss_type != star or self.cur_boss_name != name:
                raise GameStuckError('超鬼王恢复助战星级或名称不一致，禁止继续第二次进攻')
            self._encounter_attempts = attempts
            self._active_attack = None
            return True
        raise GameStuckError('超鬼王恢复原助战超过15秒')
