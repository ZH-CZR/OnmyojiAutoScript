"""星级识别、账本核对与未知棋盘单位回收。所有交易均走真实任务入口。"""
from collections import Counter
from functools import cached_property
import time

import cv2

from module.atom.click import RuleClick
from module.logger import logger
from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit, copies_for_star
from tasks.Chess.runtime.press_and_drag import Press_and_Drag


class ChessCardTrackingMixin:
    def _inventory_round_matches(self):
        current = getattr(self, '_current_round_no', None)
        return current is not None and self._read_round_number() == current

    @cached_property
    def _star_templates(self):
        # 铜/银/金分别是一/二/三星；手牌图标比棋盘图标小。
        return tuple((star, cv2.resize(rule.image, None, fx=scale, fy=scale))
                     for star, rule in enumerate(self.board_occupancy_rules, 1)
                     for scale in (.70, .75, .80, .85, .90, 1., 1.10, 1.20))

    def _read_card_star(self, roi):
        x, y, w, h = roi
        image = self.device.image
        crop = image[max(0, y):min(image.shape[0], y + h),
                     max(0, x):min(image.shape[1], x + w)]
        scores = {1: 0., 2: 0., 3: 0.}
        for star, template in self._star_templates:
            if crop.shape[0] < template.shape[0] or crop.shape[1] < template.shape[1]:
                continue
            score = cv2.minMaxLoc(cv2.matchTemplate(
                crop, template, cv2.TM_CCOEFF_NORMED))[1]
            scores[star] = max(scores[star], score)
        ranked = sorted(scores, key=scores.get, reverse=True)
        best, second = ranked[:2]
        if scores[best] < .72 or scores[best] - scores[second] < .08:
            return None
        return best

    def _scan_inventory_hand(self):
        candidates = []
        for name, rule in self.shikigami_hand_rules:
            for score, x, y, w, h in rule.match_all_any(
                    self.device.image, roi=list(self.HAND_AREA),
                    threshold=self.HAND_TEMPLATE_THRESHOLD, nms_threshold=.3):
                candidates.append((score, name, (x, y, w, h)))
        selected = []
        for score, name, roi in sorted(candidates, reverse=True):
            x, y, w, h = roi
            center = (x + w // 2, y + h // 2)
            if any(abs(center[0] - card.position[0]) <= 32
                   and abs(center[1] - card.position[1]) <= 40 for card in selected):
                continue
            # 现有手牌素材从人物区开始，左上勾玉位于其上方。
            star = self._read_card_star((x - 7, y - 35, 43, 38))
            selected.append(HandUnit(name, star, center, roi))
        # 捕捉有人物素材漏识别的式神卡，禁止把遗漏当作不存在。
        unknown = []
        image = self.device.image
        x, y, w, _ = self.HAND_AREA
        strip = image[y:y + 55, x:x + w]
        for star, template in self._star_templates:
            if strip.shape[0] < template.shape[0]:
                continue
            result = cv2.matchTemplate(strip, template, cv2.TM_CCOEFF_NORMED)
            for _ in range(16):
                _, score, _, (mx, my) = cv2.minMaxLoc(result)
                if score < .78:
                    break
                cx = x + mx + template.shape[1] // 2
                if not any(abs(cx - (card.roi[0] + 12)) <= 32 for card in selected):
                    if not any(abs(cx - u.position[0]) <= 32 for u in unknown):
                        unknown.append(HandUnit(None, star, (cx, y + my), (cx, y, 1, 1)))
                result[max(0, my - 15):my + 16, max(0, mx - 20):mx + 21] = -1
        return tuple(sorted(selected + unknown, key=lambda card: card.position[0]))

    def _stable_inventory_hand(self, modes):
        previous = None
        for _ in range(3):
            self.screenshot()
            if (self._read_chess_mode() not in modes or self.appear(self.I_SELECT_GRIGRI)
                    or not self.appear(self.I_EXPERIENCE) or not self._inventory_round_matches()):
                return None
            hand = self._scan_inventory_hand()
            signature = CardInventory.hand_signature(hand)
            if previous is not None and previous == signature:
                return hand
            previous = signature
            time.sleep(self.SCREENSHOT_INTERVAL)
        return None

    def _inventory_target_star(self, name):
        return self.get_lineup_strategy()['shikigami'][name].get('target_star', 3)

    def _inventory_card_excess(self, card):
        config = self.get_lineup_strategy()['shikigami'].get(card.name, {})
        return self._card_inventory.excess(card, config.get('target_star', 3),
                                           config.get('target_count', 1))

    def _inventory_needs_upgrade(self, unit, hand):
        return any(c.name == unit.name and c.star is not None and unit.star is not None
                   and c.star > unit.star for c in hand)

    def _inventory_should_buy(self, name):
        if not getattr(self, '_card_tracking_active', False):
            return True
        config = self.get_lineup_strategy()['shikigami'][name]
        allowed = self._card_inventory.can_buy(name, self._inventory_target_star(name),
                                               config.get('target_count', 1))
        if not allowed:
            logger.debug(f'棋局停止购入 {name}: 目标={self._inventory_target_star(name)}星, '
                         f'折算张数={self._card_inventory.totals.get(name, 0)}, '
                         f'账本就绪={self._card_inventory.ready}')
        return allowed

    def _refresh_inventory_hand(self, modes):
        hand = self._stable_inventory_hand(modes)
        if hand is None:
            self._card_inventory.ready = False
            return False
        inventory = self._card_inventory
        hand_mass = Counter()
        uncertain = set(inventory.uncertain)
        for card in hand:
            if card.star is None or card.name is None:
                uncertain.add(card.name)
            else:
                hand_mass[card.name] += copies_for_star(card.star)
        # 买入可能触发场上单位自动合成，用守恒折算量更新其星级；
        # 下一次备阶段仍以棋盘实图核对，不能靠累计购买永久推断。
        board = dict(inventory.board)
        for name in set(inventory.totals) | set(hand_mass):
            slots = [(i, u) for i, u in board.items() if u.name == name and not u.special]
            if len(slots) == 1 and slots[0][1].star is not None and name not in uncertain:
                i, unit = slots[0]
                remainder = inventory.totals.get(name, 0) - hand_mass[name]
                inferred = {1: 1, 3: 2, 9: 3}.get(remainder)
                if inferred is not None and inferred >= unit.star:
                    if inferred != unit.star:
                        board[i] = BoardUnit(name, inferred, star_confirmed=False)
        observed = CardInventory()
        observed.reconcile(hand, board)
        # 局部手牌刷新不能以漏帧抹掉已确认买入量；全量核对在备阶段进行。
        inventory.hand, inventory.board = hand, board
        inventory.uncertain |= observed.uncertain
        inventory.ready = inventory.ready and observed.ready
        for name, count in observed.totals.items():
            inventory.totals[name] = max(count, inventory.totals.get(name, 0))
        return inventory.ready

    def buy_lineup_shikigami_from_shop(self):
        if getattr(self, '_card_tracking_active', False):
            mode = self._read_chess_mode()
            if mode not in ('备', '战') or not self._refresh_inventory_hand((mode,)):
                return None
        return super().buy_lineup_shikigami_from_shop()

    def _buy_shop_slot(self, slot_index, click_rule, matched_name):
        if not getattr(self, '_card_tracking_active', False):
            return super()._buy_shop_slot(slot_index, click_rule, matched_name)
        if not self._inventory_should_buy(matched_name):
            return False
        if not self._inventory_round_matches():
            return False
        success = super()._buy_shop_slot(slot_index, click_rule, matched_name)
        if success:
            self._card_inventory.purchased(matched_name)
            logger.info(f'棋局持有量更新: {matched_name} '
                        f'折算一星={self._card_inventory.totals[matched_name]}')
        else:
            # 已点击但购买结果未明时，本次不能再次据旧数购入同名卡。
            self._card_inventory.uncertain.add(matched_name)
        return success

    def _inventory_board_frame(self):
        inventory = self._card_inventory
        special = getattr(self, '_arakawa_goldfish_current_position', None)
        board = {}
        for position in range(1, 13):
            if not self._board_set_has_shikigami(position):
                continue
            if position == special:
                board[position] = BoardUnit('arakawa_goldfish', None, True)
                continue
            known = inventory.board.get(position)
            name = known.name if known is not None and not known.special else None
            board[position] = BoardUnit(name, self._read_card_star(self._set_jade_area(position)))
        return board

    def _sync_inventory_board_names(self):
        known = {i: u for i, u in self._card_inventory.board.items()
                 if u.name is not None and not u.special}
        self._board_lineup_names = {u.name for u in known.values()
                                    if u.name in self.shikigami_deploy_positions}
        self._board_actual_positions = {u.name: i for i, u in known.items()
                                        if u.name in self._board_lineup_names}
        self._player_deployed_positions = set(known)
        special = getattr(self, '_arakawa_goldfish_current_position', None)
        if special is not None:
            self._player_deployed_positions.add(special)

    def _inventory_action_allowed(self, modes, reserve=6):
        self.screenshot()
        remaining = self._read_remaining_time()
        return (self._read_chess_mode() in modes and remaining is not None
                and remaining > reserve and not self.appear(self.I_SELECT_GRIGRI)
                and self.appear(self.I_EXPERIENCE) and self._inventory_round_matches())

    def _identify_inventory_specials(self, board):
        """右侧未知卡先查详情排除金鱼；明确为普通单位后才允许回收。"""
        if (self._arakawa_goldfish_target_position() is None
                or getattr(self, '_arakawa_goldfish_current_position', None) is not None):
            return True
        attempts = getattr(self, '_inventory_inspect_attempts', {})
        self._inventory_inspect_attempts = attempts
        for position, unit in tuple(board.items()):
            if unit.name is not None or position not in self.ARAKAWA_GOLDFISH_SPAWN_POSITIONS:
                continue
            key = (self._current_round_no, position)
            if attempts.get(key, 0) >= 2 or not self._inventory_action_allowed(('备',), reserve=10):
                return False
            attempts[key] = attempts.get(key, 0) + 1
            x, y = self._set_position(position)
            self.click(RuleClick(roi_front=(x - 8, y - 8, 16, 16),
                                 roi_back=(x - 8, y - 8, 16, 16),
                                 name=f'CHESS_IDENTIFY_SPECIAL_{position}'))
            goldfish = False
            confirmed = True
            for _ in range(2):
                time.sleep(self.SCREENSHOT_INTERVAL)
                self.screenshot()
                if (not self._inventory_round_matches() or self._read_chess_mode() != '备'
                        or not self.appear(self.I_SHIKIGAMI_SPECIFICS)):
                    confirmed = False
                    break
                goldfish |= self.appear(self.I_CHECK_GOLDFISH)
            self.close_shikigami_specifics_if_open()
            if not confirmed:
                return False
            if goldfish:
                self._record_arakawa_goldfish_position(position)
                return True
        return True

    def _recall_inventory_unit(self, position):
        if not self._inventory_action_allowed(('备',), reserve=8):
            return False
        before = self._stable_inventory_hand(('备',))
        if before is None or any(u.star is None or u.name is None for u in before):
            return False
        before_mass = sum(copies_for_star(u.star) for u in before)
        if not self._inventory_action_allowed(('备',), reserve=8):
            return False
        target = (self.HAND_AREA[0] + self.HAND_AREA[2] // 2,
                  self.HAND_AREA[1] + self.HAND_AREA[3] // 2)
        Press_and_Drag(self.device, p1=self._set_position(position), p2=target,
                       hold_duration=.5, swipe_duration=.5,
                       point_random=(-2, -2, 2, 2), name=f'CHESS_IDENTIFY_SET_{position}')
        time.sleep(self.ACTION_SETTLE_INTERVAL)
        after = self._stable_inventory_hand(('备',))
        # 下阵可能触发合成：比较折算张数，不能只比较卡片个数。
        if (after is None or any(u.star is None or u.name is None for u in after)
                or sum(copies_for_star(u.star) for u in after) <= before_mass
                or self._board_set_has_shikigami(position)):
            self._card_inventory.ready = False
            return False
        time.sleep(self.SCREENSHOT_INTERVAL)
        self.screenshot()
        if self._read_chess_mode() != '备' or self._board_set_has_shikigami(position):
            self._card_inventory.ready = False
            return False
        self._card_inventory.board.pop(position, None)
        self._sync_inventory_board_names()
        logger.info(f'棋局未知单位已回收到备战区识别: 原位置={position}')
        return True

    def _prepare_card_inventory(self):
        """备阶段先核对全部12格，未知单位逐个回收；时间不够留待下轮。"""
        if not getattr(self, '_card_tracking_active', False):
            return True
        self._card_inventory.ready = False
        if not self._ensure_shop_closed():
            return False
        previous = None
        board = None
        for _ in range(3):
            if not self._inventory_action_allowed(('备',), reserve=3):
                return False
            board = self._inventory_board_frame()
            if previous == board:
                break
            previous = board
            time.sleep(self.SCREENSHOT_INTERVAL)
        else:
            self._card_inventory.ready = False
            return False
        if any(not unit.special and position not in board
               for position, unit in self._card_inventory.board.items()):
            # 勾玉遮挡不等于已知式神离场，不能据此扣库存后重复购入。
            logger.warning('棋局已知站位暂未识别，保留原身份与持有量，等待下一次备阶段核对')
            return False
        self._card_inventory.board = board
        self._sync_inventory_board_names()
        # 尚未登记的荒川召唤物要先用已有详情识别流程确认，不能当普通卡下阵。
        if not self._identify_inventory_specials(board):
            self._card_inventory.ready = False
            return False
        board = self._card_inventory.board
        for position, unit in tuple(board.items()):
            if not unit.special and (unit.name is None or unit.star is None):
                if not self._recall_inventory_unit(position):
                    self._card_inventory.ready = False
                    return False
        hand = self._stable_inventory_hand(('备',))
        if hand is None:
            self._card_inventory.ready = False
            return False
        # 已知场上低星而备战区已有更高星时，也先下阵再按最高星部署。
        for position, unit in tuple(self._card_inventory.board.items()):
            if not unit.special and self._inventory_needs_upgrade(unit, hand):
                if not self._recall_inventory_unit(position):
                    return False
                hand = self._stable_inventory_hand(('备',))
                if hand is None:
                    return False
        self._card_inventory.reconcile(hand, self._card_inventory.board)
        self._sync_inventory_board_names()
        logger.info(f'棋局持有快照: {self._card_inventory.snapshot()}')
        self._sell_excess_inventory_cards(('备',))
        return self._card_inventory.ready

    def _sell_excess_inventory_cards(self, modes):
        for _ in range(self.HAND_CLEANUP_SAFETY_LIMIT):
            if not self._card_inventory.ready:
                return
            if not self._inventory_action_allowed(modes):
                return
            if not self._ensure_shop_closed(allowed_modes=modes):
                return
            hand = self._stable_inventory_hand(modes)
            if hand is None:
                self._card_inventory.ready = False
                return
            self._card_inventory.hand = hand
            target = next((u for u in hand if u.name in self.shikigami_deploy_positions
                           and self._inventory_card_excess(u)), None)
            if target is None:
                return
            if not self._inventory_action_allowed(modes):
                return
            before = CardInventory.hand_signature(hand)
            self.sell_hand_card(target.position)
            time.sleep(self.ACTION_SETTLE_INTERVAL)
            after = self._stable_inventory_hand(modes)
            if after is None:
                self._card_inventory.ready = False
                return
            expected = before.copy()
            expected[(target.name, target.star)] -= 1
            if +expected != CardInventory.hand_signature(after):
                # 数量未按预期减少，不重复拖动，也不记已出售。
                self._card_inventory.ready = False
                return
            self._card_inventory.hand = after
            self._card_inventory.totals[target.name] = max(
                0, self._card_inventory.totals.get(target.name, 0) - copies_for_star(target.star))
            logger.info(f'棋局出售达标后多余卡: {target.name} {target.star}星')

    def cleanup_non_lineup_hand_cards(self, allowed_modes=('战',), emergency=False):
        if getattr(self, '_card_tracking_active', False):
            self._sell_excess_inventory_cards(allowed_modes)
            if not self._card_inventory.ready:
                return []
        return super().cleanup_non_lineup_hand_cards(allowed_modes=allowed_modes, emergency=emergency)

    def _scan_lineup_hand_card_candidates_once(self, excluded_names):
        candidates = super()._scan_lineup_hand_card_candidates_once(excluded_names)
        if not getattr(self, '_card_tracking_active', False):
            return candidates
        known = []
        for candidate in candidates:
            x, y, _, _ = candidate['roi']
            star = self._read_card_star((x - 7, y - 35, 43, 38))
            if star is not None:
                known.append({**candidate, 'star': star})
        return known

    def _record_arakawa_goldfish_position(self, position):
        active = getattr(self, '_card_tracking_active', False)
        old = getattr(self, '_arakawa_goldfish_current_position', None)
        displaced = self._card_inventory.board.get(position) if active else None
        super()._record_arakawa_goldfish_position(position)
        if active:
            if old is not None and old != position:
                self._card_inventory.board.pop(old, None)
                if displaced is not None and not displaced.special:
                    self._card_inventory.board[old] = displaced
            self._card_inventory.board[position] = BoardUnit('arakawa_goldfish', None, True)
            self._sync_inventory_board_names()

    def relocate_arakawa_goldfish(self, predicted_position=None):
        result = super().relocate_arakawa_goldfish(predicted_position)
        if getattr(self, '_card_tracking_active', False):
            self._sync_inventory_board_names()
        return result

    def deploy_shikigami_hand_card(self, name, source):
        active = getattr(self, '_card_tracking_active', False)
        if active:
            hand = self._stable_inventory_hand(('备',))
            card = min((u for u in hand or () if u.name == name),
                       key=lambda u: abs(u.position[0] - source[0]), default=None)
            if card is None or card.star is None or not self._inventory_action_allowed(('备',)):
                return False
            # 新截图后使用重新定位的位置，不能沿用调用方的旧坐标。
            source = card.position
        success = super().deploy_shikigami_hand_card(name, source)
        if active and success:
            position = self.shikigami_deploy_positions[name]
            self._card_inventory.board[position] = BoardUnit(name, card.star)
            logger.info(f'棋局登记上阵: {position}号位 {name} {card.star}星')
        elif active:
            self._card_inventory.ready = False
        return success
