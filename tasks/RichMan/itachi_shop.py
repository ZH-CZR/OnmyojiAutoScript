# This Python file uses the following encoding: utf-8
# 移植自 lgg686/self tasks/WeeklyPurchase/itachi_shop.py
import time
from copy import copy

from module.atom.click import RuleClick
from module.logger import logger
from tasks.Chess.assets import ChessAssets
from tasks.Component.Buy.buy import Buy
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_entertainment
from tasks.RichMan.assets import RichManAssets
from tasks.RichMan.config import ItachiCoinShop as ItachiCoinShopConfig
from tasks.RichMan.page import page_itachi_shop


class ItachiCoinShop(Buy, GameUi, RichManAssets):
    """识别并购买三个鼬乐礼盒，名称匹配容忍 OCR 对「鼬」字的误读。"""

    ENTERTAINMENT_OVERLAY_TIMEOUT = 8.0
    ENTERTAINMENT_STABLE_TIME = 1.0
    GIFT_DIALOG_TIMEOUT = 3.0
    PURCHASE_RESULT_TIMEOUT = 8.0
    PURCHASE_RETURN_GRACE = 3.0
    REWARD_DISMISS_TIMEOUT = 5.0
    MAX_GIFT_PURCHASES = 3
    GIFT_NAME_SUFFIX = '乐礼盒'

    def execute_itachi_coin_shop(self, con: ItachiCoinShopConfig) -> None:
        if not con.itachi_coin_buy_jade:
            logger.info('Itachi coin purchase is disabled')
            return

        logger.hr('Start Itachi coin shop', 1)
        self.goto_page(page_entertainment)
        if not self._wait_entertainment_overlay_closed():
            logger.warning('Itachi Park overlay did not close; skip coin purchase')
            return

        self.goto_page(page_itachi_shop)
        purchased = 0
        purchased_gifts = set()
        for _ in range(self.MAX_GIFT_PURCHASES):
            gift = self._find_itachi_gift(purchased_gifts)
            if gift is None:
                logger.info('No remaining Itachi gift name matched; stop purchase')
                break
            name, area = gift
            if not self._open_front_gift_once(name, area):
                logger.warning(f'Itachi gift dialog did not open: {name}')
                break
            if not self._buy_opened_gift():
                break
            purchased += 1
            purchased_gifts.add(name)

        logger.info(f'Itachi coin gifts purchased: {purchased}')
        self.goto_page(page_entertainment)

    def _wait_entertainment_overlay_closed(self) -> bool:
        """处理鼬乐园附属页，跳过消失并稳定后才允许识别商店。"""

        deadline = time.monotonic() + self.ENTERTAINMENT_OVERLAY_TIMEOUT
        stable_since = None
        while time.monotonic() < deadline:
            self.screenshot()
            if self.appear(ChessAssets.I_SKIP):
                self.appear_then_click(ChessAssets.I_SKIP, interval=0.5)
                stable_since = None
                continue

            if stable_since is None:
                stable_since = time.monotonic()
                continue
            if time.monotonic() - stable_since >= self.ENTERTAINMENT_STABLE_TIME:
                return True

        return False

    @classmethod
    def _is_itachi_gift_text(cls, text: str, keyword: str) -> bool:
        """礼盒名称匹配。

        实机 OCR 会把「鼬」读成「融」甚至直接丢字（小型乐礼盒），
        因此在前缀（小/中/大）与后缀（乐礼盒）一致时也视为同一礼盒。
        """
        text = ''.join(text.split())
        if text == keyword:
            return True
        if not text or not keyword:
            return False
        return (
            text[0] == keyword[0]
            and text.endswith(cls.GIFT_NAME_SUFFIX)
            and len(text) <= len(keyword) + 1
        )

    def _find_itachi_gift(self, purchased_gifts: set[str]):
        """同一截图扫描商品区，名称按前缀+后缀容错匹配，禁止逐字兜底。"""
        self.screenshot()
        rules = (self.O_ITACHI_MINI, self.O_ITACHI_MEDIUM, self.O_ITACHI_LARGE)
        scan = copy(rules[0])
        scan.roi = tuple(rules[0].area)
        results = scan.detect_and_ocr(self.device.image)
        for rule in rules:
            if rule.keyword in purchased_gifts:
                continue
            for result in results:
                text = ''.join(result.ocr_text.split())
                if not self._is_itachi_gift_text(text, rule.keyword):
                    continue
                box = result.box
                x, y = box.min(axis=0)
                right, bottom = box.max(axis=0)
                area = (int(x + scan.roi[0]), int(y + scan.roi[1]),
                        int(right - x), int(bottom - y))
                if area[2] > 0 and area[3] > 0:
                    logger.info(
                        f'Itachi gift matched: {rule.keyword} (ocr={text}), area={area}'
                    )
                    return rule.keyword, area
        return None

    def _open_front_gift_once(self, name: str, area: tuple) -> bool:
        """只点击一次 OCR 匹配位置，并等待至多三秒确认购买框。"""

        self.click(RuleClick(roi_front=area, roi_back=area, name=f'itachi_gift_{name}'))
        deadline = time.monotonic() + self.GIFT_DIALOG_TIMEOUT
        while time.monotonic() < deadline:
            self.screenshot()
            if self.appear(self.I_BUY_PLUS):
                return True
        return False

    def _read_itachi_coin(self) -> tuple[int, int] | None:
        result = self.O_ITACHI_COIN.ocr(self.device.image)
        if isinstance(result, tuple) and len(result) >= 3:
            current, _, total = result[:3]
            if total > 0:
                logger.info(f'Itachi coin: {current}/{total}')
                return int(current), int(total)
        logger.warning(f'Itachi coin OCR failed: {result}')
        return None

    def _read_buy_cost(self) -> int | None:
        result = self.O_ITACHI_BUY_COST.ocr(self.device.image)
        if isinstance(result, int) and result > 0:
            logger.info(f'Itachi gift cost: {result}')
            return result
        logger.warning(f'Itachi gift cost OCR failed: {result}')
        return None

    def _buy_opened_gift(self) -> bool:
        """确认一次购买，并区分奖励成功与直接退回商店的失败状态。"""

        self.screenshot()
        before_coin = self._read_itachi_coin()
        cost = self._read_buy_cost()
        self.click(self.C_BUY_MORE)

        deadline = time.monotonic() + self.PURCHASE_RESULT_TIMEOUT
        dialog_absent_since = None
        while time.monotonic() < deadline:
            self.screenshot()
            if self.appear(self.I_UI_REWARD, threshold=0.6):
                reward_closed = self._dismiss_purchase_reward()
                if reward_closed:
                    self._verify_coin_cost(before_coin, cost)
                return reward_closed

            if self.appear(self.I_BUY_PLUS):
                dialog_absent_since = None
                continue

            if dialog_absent_since is None:
                dialog_absent_since = time.monotonic()
                continue
            if time.monotonic() - dialog_absent_since >= self.PURCHASE_RETURN_GRACE:
                logger.warning('Itachi gift purchase failed or coin is insufficient')
                return False

        logger.warning('Itachi gift purchase result timeout')
        return False

    def _dismiss_purchase_reward(self) -> bool:
        deadline = time.monotonic() + self.REWARD_DISMISS_TIMEOUT
        while time.monotonic() < deadline:
            self.screenshot()
            if not self.appear(self.I_UI_REWARD, threshold=0.6):
                return True
            self.ui_reward_appear_click()
        logger.warning('Itachi gift reward did not close')
        return False

    @staticmethod
    def _is_coin_reading_plausible(coin: tuple[int, int] | None) -> bool:
        """购买后顶部区域可能滚入其他数字，current 大于 total 说明读数不可信。"""
        if coin is None:
            return False
        current, total = coin
        return total > 0 and 0 <= current <= total

    def _verify_coin_cost(
        self,
        before_coin: tuple[int, int] | None,
        cost: int | None,
    ) -> None:
        self.screenshot()
        after_coin = self._read_itachi_coin()
        if (
            not self._is_coin_reading_plausible(before_coin)
            or not self._is_coin_reading_plausible(after_coin)
            or cost is None
        ):
            logger.info('Itachi coin OCR unreliable; skip coin verification')
            return
        consumed = before_coin[0] - after_coin[0]
        if consumed == cost:
            logger.info(f'Itachi gift purchase confirmed: consumed={consumed}')
        else:
            logger.warning(
                'Itachi gift coin change mismatch: '
                f'before={before_coin[0]}, after={after_coin[0]}, '
                f'cost={cost}'
            )
