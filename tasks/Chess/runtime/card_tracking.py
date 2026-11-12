"""星级识别、账本核对与未知棋盘单位回收。所有交易均走真实任务入口。"""
from functools import cached_property
import re
import time

import cv2
import numpy as np

from module.atom.click import RuleClick
from module.atom.ocr import RuleOcr
from module.logger import logger
from tasks.Chess.runtime.performance import frame_cached, match_hand_templates
from tasks.Chess.runtime.inventory import BoardUnit, CardInventory, HandUnit, copies_for_star
from tasks.Chess.runtime.press_and_drag import Press_and_Drag
from tasks.Chess.strategy.shikigami_catalog import SHIKIGAMI_BY_CHINESE_NAME


class ChessCardTrackingMixin:
    def _invalidate_inventory_hand_observation(self):
        self.__dict__.pop('_inventory_hand_observation', None)
        self.__dict__.pop('_inventory_hand_pixels', None)

    def _current_inventory_hand(self):
        observation = getattr(self, '_inventory_hand_observation', None)
        device = getattr(self, 'device', None)
        if (observation is not None and observation['frame'] == getattr(device, 'image_frame_id', None)
                and observation['image'] is getattr(device, 'image', None)
                and time.monotonic() - observation['time'] <= .7):
            return observation
        return None

    def _reconcile_inventory(self, hand, board):
        self._card_inventory.reconcile(hand, board, allow_unknown_board=True)
        round_no = getattr(self, '_current_round_no', None)
        self._card_inventory.uncertain.update(
            name for attempted_round, name in getattr(self, '_unconfirmed_inventory_buys', ())
            if attempted_round == round_no
        )

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
        image = self.device.image
        rules = self.shikigami_hand_rules
        x, y, w, h = self.HAND_AREA
        # 覆盖人物搜索外扩区和所有手牌勾玉裁剪区。只在像素完全一致时复用纯识别。
        pixels = image[max(0, y - 35):y + h + 10, max(0, x - 24):x + w + 10]
        previous = getattr(self, '_inventory_hand_pixels', None)
        if previous is not None and previous[0] is rules and np.array_equal(previous[1], pixels):
            return previous[2]

        candidates = match_hand_templates(image, rules, self.HAND_AREA, self.HAND_TEMPLATE_THRESHOLD)
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
        hand = tuple(sorted(selected + unknown, key=lambda card: card.position[0]))
        self._inventory_hand_pixels = (rules, pixels.copy(), hand)
        return hand

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

    @cached_property
    def _inventory_portrait_rules(self):
        return self._load_hand_template_folder('shikigami/card', 'card_')

    def _unidentified_inventory_card_protected(self, card):
        """缺素材不等于非阵容；先保护阵容/替补及所有装备、特殊手牌。"""
        roi = card.roi
        possible = self._possible_lineup_shikigami(roi)
        if possible is not None:
            # 低阈值保护会混淆近似头像。只在一张已收录的非阵容牌明显胜出时解除保护。
            if card.star is None:
                return True
            matches = sorted(match_hand_templates(self.device.image, self._inventory_portrait_rules,
                                                  roi, .75), reverse=True)
            if not matches:
                return True
            score, name, _ = matches[0]
            runner_up = max((other_score for other_score, other, _ in matches if other != name),
                            default=0.)
            return (name in self.shikigami_deploy_positions or score < .85
                    or score - max(runner_up, possible.get('score', 0.)) < .10)
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
            if hand is None or not self._chess_sale_allowed():
                return hand
            target = next((u for u in hand if u.name is None and u.star is not None
                           and u.roi[2] >= 72 and u.roi[3] >= 118
                           and not self._unidentified_inventory_card_protected(u)), None)
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
                        or abs(card.position[0] - target.position[0]) > 16):
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
        hand = self._clean_inventory_hand(modes)
        if hand is None:
            self._card_inventory.ready = False
            return False
        self._reconcile_inventory(hand, self._card_inventory.board)
        if any(card.name is not None and card.name not in self.shikigami_deploy_positions for card in hand):
            self._sell_excess_inventory_cards(modes, include_non_lineup=True, non_lineup_only=True)
        return self._card_inventory.ready

    def buy_lineup_shikigami_from_shop(self):
        if getattr(self, '_card_tracking_active', False):
            mode = self._read_chess_mode()
            if mode not in ('备', '战', '待'):
                return None
            if mode == '战' and not self._ensure_shop_open():
                return None
            if not self._refresh_inventory_hand((mode,)):
                return []
        return super().buy_lineup_shikigami_from_shop()

    def _after_lineup_purchase(self, name):
        if not getattr(self, '_card_tracking_active', False):
            return True
        mode = self._read_chess_mode()
        if mode not in ('备', '战', '待') or not self._inventory_round_matches():
            return False
        # 买卡可能合成，只核对本次购买涉及的场上单位。
        board = self._card_inventory.board
        for position, unit in tuple(board.items()):
            if unit.name == name and not unit.special:
                board[position] = BoardUnit(name, self._read_card_star(self._set_jade_area(position)))
        if mode == '备' and (self._uses_counter_ubume() or self._chess_hand_operations_allowed()):
            return self._handle_preparation() and self._card_inventory.ready
        return self._refresh_inventory_hand((mode,))

    def _buy_shop_slot(self, slot_index, click_rule, matched_name):
        if not getattr(self, '_card_tracking_active', False):
            return super()._buy_shop_slot(slot_index, click_rule, matched_name)
        self._shop_purchase_clicked = False
        if not self._inventory_should_buy(matched_name):
            return False
        if not self._inventory_round_matches():
            return False
        self._invalidate_inventory_hand_observation()
        success = super()._buy_shop_slot(slot_index, click_rule, matched_name)
        if success:
            self._card_inventory.purchased(matched_name)
            logger.info(f'棋局持有量更新: {matched_name} '
                        f'折算一星={self._card_inventory.totals[matched_name]}')
        elif self._shop_purchase_clicked:
            # 已点击但购买结果未明时，本次不能再次据旧数购入同名卡。
            self._card_inventory.uncertain.add(matched_name)
            pending = self.__dict__.setdefault('_unconfirmed_inventory_buys', set())
            pending.add((self._current_round_no, matched_name))
        return success

    def _inventory_board_frame(self):
        inventory = self._card_inventory
        special = getattr(self, '_arakawa_goldfish_current_position', None)
        board = {}
        pending_sales = self.__dict__.setdefault('_inventory_pending_board_sales', set())
        for position in range(1, 13):
            known = inventory.board.get(position)
            if not self._board_set_has_shikigami(position):
                # 过渡动画可能遮住勾玉。确认过的单位由交易移出账本。
                if position in pending_sales:
                    pending_sales.discard(position)
                elif known is not None and known.name is not None:
                    board[position] = known
                continue
            if position == special:
                board[position] = BoardUnit('arakawa_goldfish', None, True)
                continue
            name = known.name if known is not None and not known.special else None
            star = self._read_card_star(self._set_jade_area(position))
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

    def _read_board_detail_name(self):
        # 半透明面板会透出右侧玩家列表。只采用从标题左边起始的文字框。
        titles = [self._normalize_ocr_text(result.ocr_text)
                  for result in self.O_SHIKIGAMI_SPECIFICS_NAME.detect_and_ocr(self.device.image)
                  if result.score >= .85 and min(point[0] for point in result.box) <= 12]
        return titles[0] if len(titles) == 1 else None

    def _inspect_blocking_board_unit(self, position):
        """只在候选上阵受阻时打开详情。出售前须确认完整名称及按钮。"""
        attempts = self.__dict__.setdefault('_inventory_inspect_attempts', set())
        key = (self._current_round_no, position)
        if (key in attempts or not self._inventory_action_allowed(('备',), reserve=self.BOARD_DETAIL_RESERVE)
                or self.appear(self.I_SHIKIGAMI_SPECIFICS)
                or not self._board_set_has_shikigami(position)):
            return False
        attempts.add(key)
        x, y = self._set_position(position)
        roi = (x - 8, y - 8, 16, 16)
        self.click(RuleClick(roi_front=roi, roi_back=roi, name=f'CHESS_INSPECT_{position}'))
        try:
            for _ in range(3):
                time.sleep(self.SCREENSHOT_INTERVAL)
                if not self._inventory_action_allowed(('备',), reserve=3):
                    return False
                if self.appear(self.I_SHIKIGAMI_SPECIFICS):
                    break
            else:
                return False
            if self.appear(self.I_CHECK_GOLDFISH):
                self._record_arakawa_goldfish_position(position)
                return False
            name = self._read_board_detail_name()
            if (not name or not self._inventory_action_allowed(('备',), reserve=3)
                    or not self.appear(self.I_SHIKIGAMI_SPECIFICS)
                    or self._read_board_detail_name() != name):
                logger.debug(f'棋局详情名称未确认: 位置={position}, 名称={name!r}')
                return False
            entry = SHIKIGAMI_BY_CHINESE_NAME.get(name)
            unit_name = entry.romaji if entry is not None else name
            board = self._card_inventory.board
            unit = board[position]
            board[position] = BoardUnit(unit_name, unit.star)
            self._reconcile_inventory(self._card_inventory.hand, board)
            self._sync_inventory_board_names()
            if unit_name in self.shikigami_deploy_positions or not self._chess_sale_allowed():
                return False

            # 技能说明行数不同会改变按钮高度，在面板下部找文字框。
            area = (1008, 516, 170, 106)
            ocr = RuleOcr(roi=area, area=area, mode='Full', method='Default',
                          keyword='', name='chess_board_sell')
            matches = [result for result in ocr.detect_and_ocr(self.device.image)
                       if result.score >= .85 and re.fullmatch(
                           r'(?:[+＋][0-9]+)?出售', self._normalize_ocr_text(result.ocr_text))]
            if len(matches) != 1:
                logger.debug(f'棋局详情未确认唯一出售按钮: 位置={position}, 名称={name}')
                return False
            points = matches[0].box
            x = area[0] + (min(p[0] for p in points) + max(p[0] for p in points)) // 2
            y = area[1] + (min(p[1] for p in points) + max(p[1] for p in points)) // 2
            roi = (int(x) - 4, int(y) - 4, 8, 8)
            pending_sales = self.__dict__.setdefault('_inventory_pending_board_sales', set())
            pending_sales.add(position)
            self.click(RuleClick(roi_front=roi, roi_back=roi, name=f'CHESS_SELL_SET_{position}'))
            empty_frames = 0
            for _ in range(self.BOARD_SALE_CONFIRM_FRAMES):
                time.sleep(self.ACTION_SETTLE_INTERVAL)
                self.screenshot()
                if (self._read_chess_mode() != '备' or not self._inventory_round_matches()
                        or self.appear(self.I_SELECT_GRIGRI)):
                    return False
                if self._board_set_has_shikigami(position):
                    empty_frames = 0
                    continue
                empty_frames += 1
                if empty_frames == 2:
                    break
            else:
                return False
            pending_sales.discard(position)
            board.pop(position)
            self._reconcile_inventory(self._card_inventory.hand, board)
            self._sync_inventory_board_names()
            logger.info(f'棋局出售场上非阵容式神: {position}号位 {name}')
            return True
        finally:
            if self._read_chess_mode() == '备' and self._inventory_round_matches() and self._chess_time_available():
                if self.appear(self.I_SHIKIGAMI_SPECIFICS):
                    self.click(self.C_CLICK_CLOSE_SPECIFICS_AREA)
                    time.sleep(self.SCREENSHOT_INTERVAL)
                    self.screenshot()

    def _recall_inventory_unit(self, position):
        if not self._inventory_action_allowed(('备',), reserve=3):
            return False
        unit = self._card_inventory.board.get(position)
        name = unit.name if unit is not None else None
        before = self._stable_inventory_hand(('备',))
        if before is None:
            return False

        def matching_copies(hand):
            return sum(copies_for_star(card.star) for card in hand
                       if card.star is not None and (name is None or card.name == name))

        before_mass = matching_copies(before)
        if (not self._inventory_action_allowed(('备',), reserve=3)
                or self.appear(self.I_SHIKIGAMI_SPECIFICS)):
            return False
        target = (self.HAND_AREA[0] + self.HAND_AREA[2] // 2,
                  self.HAND_AREA[1] + self.HAND_AREA[3] // 2)
        self._invalidate_inventory_hand_observation()
        Press_and_Drag(self.device, p1=self._set_position(position), p2=target,
                       hold_duration=self._chess_drag_hold_duration(), swipe_duration=.16,
                       point_random=(-2, -2, 2, 2), name=f'CHESS_IDENTIFY_SET_{position}')
        time.sleep(self.ACTION_SETTLE_INTERVAL)
        after = self._stable_inventory_hand(('备',), empty_position=position)
        # 下阵可能触发合成：比较折算张数，不能只比较卡片个数。
        if (after is None or matching_copies(after) <= before_mass
                or self._board_set_has_shikigami(position)):
            self._chess_drag_fallback = True
            self._card_inventory.ready = False
            return False
        if self._read_chess_mode() != '备' or self._board_set_has_shikigami(position):
            self._card_inventory.ready = False
            return False
        self._card_inventory.board.pop(position, None)
        self._reconcile_inventory(after, self._card_inventory.board)
        self._sync_inventory_board_names()
        logger.info(f'棋局单位已回收到备战区: 原位置={position}')
        return True

    def _prepare_card_inventory(self):
        """每回目首次确认备阶段且商店收起后扫棋盘，手牌独立更新。"""
        if not getattr(self, '_card_tracking_active', False):
            return True
        if (not self._ensure_shop_closed() or not self._is_preparation_mode()
                or not self._inventory_round_matches()):
            self._card_inventory.ready = False
            return False
        if getattr(self, '_inventory_board_round', None) != self._current_round_no:
            board = self._inventory_board_frame()
            self._reconcile_inventory(self._card_inventory.hand, board)
            self._sync_inventory_board_names()
            self._inventory_board_round = self._current_round_no
            logger.debug(f'棋局备阶段棋盘: {board}')
        hand = self._stable_inventory_hand(('备',))
        if hand is None:
            self._card_inventory.ready = False
            return False
        self._reconcile_inventory(hand, self._card_inventory.board)
        return True

    def _prepare_inventory_upgrades(self):
        inventory = self._card_inventory
        for position, unit in tuple(inventory.board.items()):
            if (not unit.special and unit.name in self.shikigami_deploy_positions
                    and self._inventory_needs_upgrade(unit, inventory.hand)):
                if not self._recall_inventory_unit(position):
                    break

    def _inventory_sale_target(self, hand, include_non_lineup, non_lineup_only):
        self._card_inventory.hand = hand
        return next((u for u in hand if u.name is not None and u.star is not None
                     and ((not non_lineup_only and u.name in self.shikigami_deploy_positions
                           and self._inventory_card_excess(u))
                          or (include_non_lineup and u.name not in self.shikigami_deploy_positions))), None)

    def _sell_excess_inventory_cards(self, modes, include_non_lineup=False, non_lineup_only=False):
        if not self._chess_sale_allowed():
            return
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
            current = self._scan_inventory_hand()
            if (CardInventory.hand_signature(current) != CardInventory.hand_signature(hand)
                    or not any(card.name == target.name and card.star == target.star
                               and abs(card.position[0] - target.position[0]) <= 12 for card in current)):
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
                0, self._card_inventory.totals.get(target.name, 0) - 1)
            logger.info(f'棋局出售非阵容/达标多余卡: {target.name} {target.star}星')
            if hasattr(self, '_last_inventory_cleaned_positions'):
                self._last_inventory_cleaned_positions.append(target.position)

    def _priority_cleanup_inventory_hand(self):
        if not getattr(self, '_card_tracking_active', False) or not self._chess_sale_allowed():
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

    def _inventory_unit_destination(self, name, position):
        return self.shikigami_deploy_positions.get(name)

    def _reposition_blocking_lineup_unit(self, position, name):
        destination = self._inventory_unit_destination(name, position)
        if (destination is None or destination == position or destination in self._card_inventory.board
                or self._board_set_has_shikigami(destination) or not self._recall_inventory_unit(position)):
            return
        # 回收后的手牌可能重排或合成，重新找同名卡再拖到配置位置。
        card = max((unit for unit in self._card_inventory.hand if unit.name == name and unit.star is not None),
                   key=lambda unit: unit.star, default=None)
        if card is not None and self.shikigami_deploy_positions.get(name) == destination:
            if self.deploy_shikigami_hand_card(name, card.position):
                self._sync_inventory_board_names()

    def _free_inventory_deploy_slot(self, position):
        """空位与人口足够时直接上阵，只有受阻才查看未知单位。"""
        level = self._read_level()
        if level is None or self.appear(self.I_SHIKIGAMI_SPECIFICS):
            return False
        board = self._card_inventory.board
        if position not in board and self._board_set_has_shikigami(position):
            board[position] = BoardUnit(None, self._read_card_star(self._set_jade_area(position)))
        # 目标格优先。若移除目标格后人口仍满，再检查其他占位。
        for slot in (position, *(slot for slot in board if slot != position)):
            board = self._card_inventory.board
            if position not in board and sum(not u.special for u in board.values()) < level:
                return True
            unit = board.get(slot)
            if unit is None or unit.special:
                continue
            if unit.name not in self.shikigami_deploy_positions:
                if self._inspect_blocking_board_unit(slot):
                    continue
                if self.appear(self.I_SHIKIGAMI_SPECIFICS):
                    return False
                unit = self._card_inventory.board[slot]
            if unit.name in self.shikigami_deploy_positions:
                self._reposition_blocking_lineup_unit(slot, unit.name)
            if slot == position and slot in self._card_inventory.board:
                return False
        board = self._card_inventory.board
        return position not in board and sum(not u.special for u in board.values()) < level

    def recall_all_board_cards(self):
        if getattr(self, '_card_tracking_active', False):
            return self._prepare_card_inventory()
        return super().recall_all_board_cards()

    def cleanup_non_lineup_hand_cards(self, allowed_modes=('战',), emergency=False):
        if not self._chess_sale_allowed():
            return []
        if getattr(self, '_card_tracking_active', False):
            hand = self._clean_inventory_hand(allowed_modes)
            if hand is None:
                return list(self._last_inventory_cleaned_positions)
            self._reconcile_inventory(hand, self._card_inventory.board)
            self._sell_excess_inventory_cards(allowed_modes, include_non_lineup=True, non_lineup_only=True)
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
            if card is None or card.star is None or not self._inventory_action_allowed(('备',), reserve=3):
                return False
            before_positions = set(self._card_inventory.board)
            if not self._free_inventory_deploy_slot(position):
                return False
            # 回收会重排整排手牌，必须重新定位，禁止沿用原坐标。
            if before_positions != set(self._card_inventory.board):
                hand = self._stable_inventory_hand(('备',))
                card = min((u for u in hand or () if u.name == name and u.star is not None),
                           key=lambda u: abs(u.position[0] - source[0]), default=None)
                if card is None or not self._inventory_action_allowed(('备',), reserve=3):
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
            self.__dict__.setdefault('_inventory_pending_board_sales', set()).discard(position)
            self._reconcile_inventory(self._scan_inventory_hand(), self._card_inventory.board)
            logger.info(f'棋局登记上阵: {position}号位 {name} {card.star}星')
        elif active:
            self._chess_drag_fallback = True
            self._card_inventory.ready = False
        return success
