"""星级识别、账本核对与未知棋盘单位回收。所有交易均走真实任务入口。"""
from collections import Counter
from functools import cached_property
import time

import cv2

from module.atom.click import RuleClick
from module.logger import logger
from tasks.Chess.runtime.performance import frame_cached, match_hand_templates
from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit, copies_for_star
from tasks.Chess.runtime.press_and_drag import Press_and_Drag


class ChessCardTrackingMixin:
    def _invalidate_inventory_hand_observation(self):
        self.__dict__.pop('_inventory_hand_observation', None)

    def _current_inventory_hand(self):
        observation = getattr(self, '_inventory_hand_observation', None)
        device = getattr(self, 'device', None)
        if (observation is not None and observation['frame'] == getattr(device, 'image_frame_id', None)
                and observation['image'] is getattr(device, 'image', None)
                and time.monotonic() - observation['time'] <= .7):
            return observation
        return None

    def _defer_unknown_board(self):
        level = self._read_level()
        return (level is not None and level < 6) or getattr(self, '_preparation_priority_pass', False)

    def _reconcile_inventory(self, hand, board):
        inventory = self._card_inventory
        old_totals, old_uncertain = dict(inventory.totals), set(inventory.uncertain)
        priority = getattr(self, '_preparation_priority_pass', False)
        inventory.reconcile(hand, board, allow_unknown_board=self._defer_unknown_board())
        if priority:
            # 此临时账本只允许上阵和装备，未知手牌留到随后的回收/出售步骤。
            inventory.ready = True
            inventory.deferred_board = True
        if inventory.deferred_board:
            # 已购卡可能被系统自动上阵；暂不查身份也不能抹掉确认过的购入量。
            for name, count in old_totals.items():
                inventory.totals[name] = max(count, inventory.totals.get(name, 0))
            inventory.uncertain |= old_uncertain

    def _inventory_round_matches(self):
        current = getattr(self, '_current_round_no', None)
        return current is not None and self._read_round_number() == current

    @cached_property
    def _star_templates(self):
        # 铜/银/金分别是一/二/三星；手牌图标比棋盘图标小。
        return tuple((star, cv2.resize(rule.image, None, fx=scale, fy=scale))
                     for star, rule in enumerate(self.board_occupancy_rules, 1)
                     for scale in (.70, .75, .80, .85, .90, 1., 1.10, 1.20))

    @frame_cached
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

    @frame_cached
    def _scan_inventory_hand(self):
        candidates = match_hand_templates(self.device.image, self.shikigami_hand_rules,
                                         self.HAND_AREA, self.HAND_TEMPLATE_THRESHOLD)
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
                    if not any(abs(cx - (u.roi[0] + 16)) <= 32 for u in unknown):
                        # 勾玉只能定位卡片左上角，拖动/阵容保护必须使用完整卡框。
                        left = max(x, cx - 16)
                        width = min(96, x + w - left)
                        roi = (left, y, width, self.HAND_AREA[3])
                        confirmed_star = self._read_card_star((cx - 20, y + my - 8, 43, 38))
                        unknown.append(HandUnit(None, confirmed_star,
                                                (left + width // 2, y + roi[3] // 2), roi))
                result[max(0, my - 15):my + 16, max(0, mx - 20):mx + 21] = -1
        return tuple(sorted(selected + unknown, key=lambda card: card.position[0]))

    def _stable_inventory_hand(self, modes, empty_position=None):
        cached = self._current_inventory_hand()
        if (cached is not None and self._read_chess_mode() in modes and self._inventory_round_matches()
                and not self.appear(self.I_SELECT_GRIGRI) and self.appear(self.I_EXPERIENCE)
                and (empty_position is None or empty_position in cached['empty_positions'])):
            return cached['hand']
        previous = None
        previous_pictures = None
        previous_empty = False
        for _ in range(3):
            self.screenshot()
            if (self._read_chess_mode() not in modes or self.appear(self.I_SELECT_GRIGRI)
                    or not self.appear(self.I_EXPERIENCE) or not self._inventory_round_matches()):
                return None
            hand = self._scan_inventory_hand()
            signature = CardInventory.hand_signature(hand)
            pictures = [(u.position[0], self._inventory_card_fingerprint(u))
                        for u in hand if u.name is None]
            same_pictures = (previous_pictures is not None and len(pictures) == len(previous_pictures)
                             and all(abs(x - px) <= 16 and picture is not None and old is not None
                                     and float(cv2.absdiff(picture, old).mean()) < 8.
                                     for (x, picture), (px, old) in zip(pictures, previous_pictures)))
            empty = empty_position is None or not self._board_set_has_shikigami(empty_position)
            if previous is not None and previous == signature and same_pictures and empty and previous_empty:
                frame = getattr(getattr(self, 'device', None), 'image_frame_id', None)
                if frame is not None:
                    self._inventory_hand_observation = {
                        'frame': frame, 'image': self.device.image, 'hand': hand,
                        'time': time.monotonic(), 'empty_positions': {empty_position} - {None},
                    }
                return hand
            previous = signature
            previous_pictures = pictures
            previous_empty = empty
            time.sleep(self.SCREENSHOT_INTERVAL)
        return None

    @frame_cached
    def _plain_inventory_shikigami(self, roi, star):
        """高置信星级勾玉是式神独有标志，普通式神无需再遍历装备/OCR。"""
        x, y, w, h = roi
        crop = self.device.image[y:y + min(55, h), x:x + min(48, w)]
        scores = {1: 0., 2: 0., 3: 0.}
        for rank, template in self._star_templates:
            if template.shape[0] > crop.shape[0] or template.shape[1] > crop.shape[1]:
                continue
            score = cv2.minMaxLoc(cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED))[1]
            scores[rank] = max(scores[rank], score)
        return (star in scores and scores[star] >= .88
                and scores[star] - max(value for rank, value in scores.items() if rank != star) >= .12)

    def _unidentified_inventory_card_protected(self, card):
        """缺素材不等于非阵容；先保护阵容/替补及所有装备、特殊手牌。"""
        roi = card.roi
        if self._possible_lineup_shikigami(roi) is not None:
            return True
        if self._plain_inventory_shikigami(roi, card.star):
            return False
        if (self._soul_match_in_card(roi) is not None
                or self._hakuzosu_protect_match_in_card(roi) is not None):
            return True
        special = self._discover_soul_hand_cards() + self._discover_badge_hand_cards()
        badge = self._find_badge_hand_card()
        if badge is not None:
            special.append(badge)
        return any(roi[0] - 8 <= item['position'][0] <= roi[0] + roi[2] + 8 for item in special)

    def _inventory_card_fingerprint(self, card):
        x, y, w, h = card.roi
        crop = self.device.image[y:y + h, x:x + w]
        return cv2.resize(crop, (32, 48)) if crop.size else None

    def _clean_inventory_hand(self, modes):
        """命名素材缺失的普通式神也能清理，不被前三回合旧清理禁令挡住。"""
        self._last_inventory_cleaned_positions = []
        for _ in range(self.HAND_CLEANUP_SAFETY_LIMIT):
            hand = self._stable_inventory_hand(modes)
            if hand is None:
                return None
            target = next((u for u in hand if u.name is None and u.star is not None), None)
            if target is None:
                return hand
            if not self._ensure_shop_closed(allowed_modes=modes):
                return None
            signature = CardInventory.hand_signature(hand)
            previous = self._inventory_card_fingerprint(target)
            # 同一帧刚有两帧卡面/数量稳定证据，仅补一帧，避免重新等待三帧。
            confirmations = 1 if self._current_inventory_hand() is not None else self.UNKNOWN_SELL_CONFIRM_FRAMES
            for confirmation in range(confirmations):
                if not self._inventory_action_allowed(modes, reserve=2):
                    return None
                current = self._scan_inventory_hand()
                if CardInventory.hand_signature(current) != signature:
                    return None
                card = min((u for u in current if u.name is None and u.star == target.star),
                           key=lambda u: abs(u.position[0] - target.position[0]), default=None)
                if (card is None or card.roi[2] < 72 or card.roi[3] < 118
                        or abs(card.position[0] - target.position[0]) > 16
                        or (confirmation == 0 and self._unidentified_inventory_card_protected(card))):
                    return hand
                fingerprint = self._inventory_card_fingerprint(card)
                if fingerprint is None or (previous is not None
                        and float(cv2.absdiff(previous, fingerprint).mean()) >= 8.):
                    return None
                previous = fingerprint
                target = card
                if confirmation + 1 < confirmations:
                    time.sleep(self.SCREENSHOT_INTERVAL)
            # 保护识别可能耗时，出售前再确认阶段、数量、位置及同一张卡面。
            if not self._inventory_action_allowed(modes, reserve=2):
                return None
            current = self._scan_inventory_hand()
            if CardInventory.hand_signature(current) != signature:
                return None
            latest = min((u for u in current if u.name is None and u.star == target.star),
                         key=lambda u: abs(u.position[0] - target.position[0]), default=None)
            fingerprint = self._inventory_card_fingerprint(latest) if latest is not None else None
            if (latest is None or abs(latest.position[0] - target.position[0]) > 16
                    or fingerprint is None or float(cv2.absdiff(previous, fingerprint).mean()) >= 8.):
                return None
            target = latest
            self._invalidate_inventory_hand_observation()
            self.sell_hand_card(target.position)
            time.sleep(self.ACTION_SETTLE_INTERVAL)
            after = self._stable_inventory_hand(modes)
            expected = signature.copy()
            expected[(None, target.star)] -= 1
            if after is None or +expected != CardInventory.hand_signature(after):
                self._card_inventory.ready = False
                self._chess_drag_fallback = True
                return None
            logger.info(f'棋局出售缺素材非阵容式神: {target.star}星，位置={target.position}')
            self._last_inventory_cleaned_positions.append(target.position)
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
        if self._card_inventory.deferred_board and not self._defer_unknown_board():
            self._card_inventory.ready = False
            return False
        hand = self._clean_inventory_hand(modes)
        if hand is None:
            self._card_inventory.ready = False
            return False
        inventory = self._card_inventory
        hand_mass = Counter()
        uncertain = set(inventory.uncertain)
        for card in hand:
            if card.name is None:
                continue  # observed.reconcile 会阻止交易；不能向名称集合塞入 None。
            if card.star is None:
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
        observed.reconcile(hand, board, allow_unknown_board=self._defer_unknown_board())
        # 局部手牌刷新不能以漏帧抹掉已确认买入量；全量核对在备阶段进行。
        inventory.hand, inventory.board = hand, board
        early = self._defer_unknown_board()
        inventory.deferred_board = observed.deferred_board or (inventory.deferred_board and early)
        inventory.uncertain |= observed.uncertain
        if early and not inventory.ready and observed.ready:
            # 中途进入战/待也可按已确认手牌买自然商店；棋盘身份留到备阶段核对。
            inventory.ready = True
            inventory.deferred_board = True
        else:
            inventory.ready = inventory.ready and observed.ready
        for name, count in observed.totals.items():
            inventory.totals[name] = max(count, inventory.totals.get(name, 0))
        return inventory.ready

    def buy_lineup_shikigami_from_shop(self):
        if getattr(self, '_card_tracking_active', False):
            mode = self._read_chess_mode()
            if mode not in ('备', '战', '待') or not self._refresh_inventory_hand((mode,)):
                return None
        return super().buy_lineup_shikigami_from_shop()

    def _after_lineup_purchase(self, name):
        # 所有阵容共用：新购手牌先补阵/装备，再允许继续买牌或运营。
        if getattr(self, '_card_tracking_active', False) and self._read_chess_mode() == '备':
            return self._card_inventory.ready and self._handle_preparation()
        return True

    def _buy_shop_slot(self, slot_index, click_rule, matched_name):
        if not getattr(self, '_card_tracking_active', False):
            return super()._buy_shop_slot(slot_index, click_rule, matched_name)
        if not self._inventory_should_buy(matched_name):
            return False
        if not self._inventory_round_matches():
            return False
        self._invalidate_inventory_hand_observation()
        self._inventory_board_dirty = True
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
            star = (None if name is None and self._defer_unknown_board()
                    else self._read_card_star(self._set_jade_area(position)))
            board[position] = BoardUnit(name, star)
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

    def _inventory_action_allowed(self, modes, reserve=6, refresh=True):
        if refresh or self._current_inventory_hand() is None:
            self.screenshot()
        remaining = self._read_remaining_time()
        return (self._read_chess_mode() in modes and remaining is not None
                and remaining > max(3, reserve) and not self.appear(self.I_SELECT_GRIGRI)
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
        before = self._clean_inventory_hand(('备',))
        if before is None or any(u.star is None or u.name is None for u in before):
            return False
        if any(
                u.name not in self.shikigami_deploy_positions for u in before):
            # 全盘尚未就绪也可清理已确认的非阵容手牌，为后续回收腾空间。
            self._sell_excess_inventory_cards(('备',), include_non_lineup=True, non_lineup_only=True)
            before = self._stable_inventory_hand(('备',))
            if before is None or any(u.star is None or u.name is None
                                     or u.name not in self.shikigami_deploy_positions for u in before):
                return False
        before_mass = sum(copies_for_star(u.star) for u in before)
        if not self._inventory_action_allowed(('备',), reserve=8):
            return False
        target = (self.HAND_AREA[0] + self.HAND_AREA[2] // 2,
                  self.HAND_AREA[1] + self.HAND_AREA[3] // 2)
        self._invalidate_inventory_hand_observation()
        self._inventory_board_dirty = True
        Press_and_Drag(self.device, p1=self._set_position(position), p2=target,
                       hold_duration=self._chess_drag_hold_duration(), swipe_duration=.16,
                       point_random=(-2, -2, 2, 2), name=f'CHESS_IDENTIFY_SET_{position}')
        time.sleep(self.ACTION_SETTLE_INTERVAL)
        after = self._stable_inventory_hand(('备',), empty_position=position)
        # 下阵可能触发合成：比较折算张数，不能只比较卡片个数。
        if (after is None or any(u.star is None for u in after)
                or sum(copies_for_star(u.star) for u in after) <= before_mass
                or self._board_set_has_shikigami(position)):
            self._chess_drag_fallback = True
            self._card_inventory.ready = False
            return False
        if self._read_chess_mode() != '备' or self._board_set_has_shikigami(position):
            self._card_inventory.ready = False
            return False
        self._card_inventory.board.pop(position, None)
        self._card_inventory.hand = after
        self._sync_inventory_board_names()
        logger.info(f'棋局未知单位已回收到备战区识别: 原位置={position}')
        # 回收一张就处理这一张，不能等所有位置回收完才出售。
        cleaned = (self._clean_inventory_hand(('备',))
                   if any(u.name not in self.shikigami_deploy_positions for u in after) else after)
        if cleaned is None:
            self._card_inventory.ready = False
            return False
        self._card_inventory.hand = cleaned
        return True

    def _prepare_card_inventory(self):
        """六阶前保留未知占位；六阶起回收识别，时间不够留待下轮。"""
        if not getattr(self, '_card_tracking_active', False):
            return True
        self._card_inventory.ready = False
        if not self._ensure_shop_closed():
            return False
        if self._read_level() is None:
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
        if any(not unit.special and unit.name is not None and position not in board
               for position, unit in self._card_inventory.board.items()):
            # 勾玉遮挡不等于已知式神离场，不能据此扣库存后重复购入。
            logger.warning('棋局已知站位暂未识别，保留原身份与持有量，等待下一次备阶段核对')
            return False
        self._card_inventory.board = board
        self._inventory_board_dirty = False
        self._sync_inventory_board_names()
        # 尚未登记的荒川召唤物要先用已有详情识别流程确认，不能当普通卡下阵。
        deferred = self._defer_unknown_board()
        if not deferred and not self._identify_inventory_specials(board):
            self._card_inventory.ready = False
            return False
        board = self._card_inventory.board
        for position, unit in tuple(board.items()):
            if not deferred and not unit.special and (unit.name is None or unit.star is None):
                if not self._recall_inventory_unit(position):
                    self._card_inventory.ready = False
                    return False
        hand = (self._stable_inventory_hand(('备',)) if getattr(self, '_preparation_priority_pass', False)
                else self._clean_inventory_hand(('备',)))
        if hand is None:
            self._card_inventory.ready = False
            return False
        # 已知场上低星而备战区已有更高星时，也先下阵再按最高星部署。
        for position, unit in tuple(self._card_inventory.board.items()):
            if (not getattr(self, '_preparation_priority_pass', False)
                    and not unit.special and self._inventory_needs_upgrade(unit, hand)):
                if not self._recall_inventory_unit(position):
                    return False
                hand = self._stable_inventory_hand(('备',))
                if hand is None:
                    return False
        self._reconcile_inventory(hand, self._card_inventory.board)
        self._sync_inventory_board_names()
        logger.info(f'棋局持有快照: {self._card_inventory.snapshot()}')
        if not getattr(self, '_preparation_priority_pass', False):
            self._sell_excess_inventory_cards(('备',), include_non_lineup=True)
        return self._card_inventory.ready

    def _inventory_sale_target(self, hand, include_non_lineup, non_lineup_only):
        self._card_inventory.hand = hand
        return next((u for u in hand if u.name is not None and u.star is not None
                     and ((not non_lineup_only and u.name in self.shikigami_deploy_positions
                           and self._inventory_card_excess(u))
                          or (include_non_lineup and u.name not in self.shikigami_deploy_positions))), None)

    def _sell_excess_inventory_cards(self, modes, include_non_lineup=False, non_lineup_only=False):
        for _ in range(self.HAND_CLEANUP_SAFETY_LIMIT):
            if not self._card_inventory.ready and not non_lineup_only:
                return
            cached = self._current_inventory_hand()
            if cached is not None and self._inventory_sale_target(
                    cached['hand'], include_non_lineup, non_lineup_only) is None:
                return
            if not self._inventory_action_allowed(modes):
                return
            if not self._ensure_shop_closed(allowed_modes=modes):
                return
            hand = self._stable_inventory_hand(modes)
            if hand is None:
                self._card_inventory.ready = False
                return
            target = self._inventory_sale_target(hand, include_non_lineup, non_lineup_only)
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
                self._chess_drag_fallback = True
                return
            self._card_inventory.hand = after
            self._card_inventory.totals[target.name] = max(
                0, self._card_inventory.totals.get(target.name, 0) - copies_for_star(target.star))
            logger.info(f'棋局出售非阵容/达标多余卡: {target.name} {target.star}星')
            if hasattr(self, '_last_inventory_cleaned_positions'):
                self._last_inventory_cleaned_positions.append(target.position)

    def _priority_cleanup_inventory_hand(self):
        if not getattr(self, '_card_tracking_active', False):
            return False
        mode = self._read_chess_mode()
        if (mode not in ('备', '战', '待') or self.appear(self.I_SELECT_GRIGRI)
                or not self.appear(self.I_EXPERIENCE)):
            return False
        hand = self._scan_inventory_hand()
        if not any(u.name not in self.shikigami_deploy_positions and u.star is not None for u in hand):
            return False
        before = CardInventory.hand_signature(hand)
        cleaned = self._clean_inventory_hand((mode,))
        if cleaned is None:
            return False
        self._card_inventory.hand = cleaned
        return before != CardInventory.hand_signature(cleaned)

    def _free_inventory_deploy_slot(self, position):
        """只为已有阵容手牌腾位，优先移走目标格的未知单位。"""
        level = self._read_level()
        if level is None:
            return False
        board = self._card_inventory.board
        target = board.get(position)
        if target is not None and (target.special or target.name is not None):
            return False
        full = sum(not u.special for u in board.values()) >= level
        recall = None
        if target is not None:
            recall = position
        elif full:
            recall = next((p for p, u in board.items() if not u.special and u.name is None), None)
        if recall is None:
            return not full
        # 荒川的未知召唤物仍须先核验，避免拖动金鱼当普通牌。
        if not self._identify_inventory_specials(board):
            return False
        if self._card_inventory.board.get(recall, BoardUnit(None, None)).special:
            return False
        return self._recall_inventory_unit(recall)

    def _recall_one_system_board_card(self, preferred_set_index=None):
        if not getattr(self, '_card_tracking_active', False):
            return super()._recall_one_system_board_card(preferred_set_index)
        before = set(self._card_inventory.board)
        if preferred_set_index is None or not self._free_inventory_deploy_slot(preferred_set_index):
            return None
        return next(iter(before - set(self._card_inventory.board)), None)

    def recall_all_board_cards(self):
        if getattr(self, '_card_tracking_active', False):
            return self._prepare_card_inventory()
        return super().recall_all_board_cards()

    def cleanup_non_lineup_hand_cards(self, allowed_modes=('战',), emergency=False):
        if getattr(self, '_card_tracking_active', False):
            hand = self._clean_inventory_hand(allowed_modes)
            if hand is None:
                return list(self._last_inventory_cleaned_positions)
            self._card_inventory.hand = hand
            self._sell_excess_inventory_cards(allowed_modes)
            sold = list(self._last_inventory_cleaned_positions)
            if not self._card_inventory.ready or not self._chess_equipment_ready():
                return sold
            return sold + super().cleanup_non_lineup_hand_cards(allowed_modes=allowed_modes, emergency=emergency)
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
            position = self.shikigami_deploy_positions.get(name)
            # 先确认真的持有候选卡，再为其回收未知占位；不能空手拆场。
            if position is None:
                return False
            hand = self._stable_inventory_hand(('备',))
            card = min((u for u in hand or () if u.name == name),
                       key=lambda u: abs(u.position[0] - source[0]), default=None)
            if card is None or card.star is None or not self._inventory_action_allowed(('备',)):
                return False
            before_positions = set(self._card_inventory.board)
            if not self._free_inventory_deploy_slot(position):
                return False
            # 回收会重排整排手牌，必须重新定位，禁止沿用原坐标。
            if before_positions != set(self._card_inventory.board):
                hand = self._stable_inventory_hand(('备',))
                card = min((u for u in hand or () if u.name == name and u.star is not None),
                           key=lambda u: abs(u.position[0] - source[0]), default=None)
                if card is None or not self._inventory_action_allowed(('备',)):
                    return False
            # 新截图后使用重新定位的位置，不能沿用调用方的旧坐标。
            source = card.position
        success = super().deploy_shikigami_hand_card(name, source)
        if active and success:
            success = (self._read_chess_mode() == '备' and self._inventory_round_matches()
                       and self.appear(self.I_EXPERIENCE) and not self.appear(self.I_SELECT_GRIGRI))
        if active and success:
            position = self.shikigami_deploy_positions[name]
            self._card_inventory.board[position] = BoardUnit(name, card.star)
            logger.info(f'棋局登记上阵: {position}号位 {name} {card.star}星')
        elif active:
            self._chess_drag_fallback = True
            self._card_inventory.ready = False
        return success
