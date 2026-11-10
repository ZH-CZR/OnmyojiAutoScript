"""Chess runtime: shop access, purchasing, and atomic economy operations."""

# This Python file uses the following encoding: utf-8

from typing import TYPE_CHECKING

import re
import time

import cv2
import numpy as np

from module.atom.click import RuleClick
from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.logger import logger
from tasks.Chess.runtime.performance import frame_cached
from tasks.Chess.strategy.shikigami_catalog import (
    KNOWN_BONDS,
    NON_SHOP_SHIKIGAMI,
    SHIKIGAMI_ENTRIES,
    SHIKIGAMI_BY_ROMAJI,
    STORE_SHIKIGAMI_BY_SIGNATURE,
    bond_key,
    normalize_bond_ocr_text,
)

if TYPE_CHECKING:
    # 仅供类型检查：声明 mixin 最终会被 ScriptTask 混入的能力来源，
    # 使编辑器能解析 self.appear/self.device/self.I_* 等引用。
    from tasks.Chess.assets import ChessAssets
    from tasks.Chess.runtime.settings import ChessRuntimeSettings
    from tasks.GameUi.game_ui import GameUi

    class _ChessTaskBase(GameUi, ChessRuntimeSettings, ChessAssets):
        ...
else:
    _ChessTaskBase = object


class ChessEconomyMixin(_ChessTaskBase):
    """Internal mixin; use through ``ScriptTask`` only."""

    def _shop_slots(self) -> list[tuple[int, RuleClick]]:
        """返回商店五个卡面点击区；编号按原资源定义从右向左。"""
        return [
            (
                index,
                getattr(self, f'C_SHIKIGAMI_{index}'),
            )
            for index in range(1, 6)
        ]

    def _is_shop_open(self) -> bool:
        """使用刷新按钮判断商店是否展开；禁止在此读取价格 OCR。

        ``check_market`` 是开店确认的辅助标志，不能用于“商店仍展开”
        的通用判断，否则商店关闭后仍可能命中该图标，导致上卡阶段被
        误判为商店未关闭。
        """
        visible = self._shop_refresh_marker_visible()
        if visible:
            self._shop_assumed_open = True
            return True
        self._shop_assumed_open = False
        return False

    def _shop_refresh_marker_visible(self) -> bool:
        """刷新/金币不足刷新任一出现，表示商店明确展开。"""
        return self.appear(self.I_CHESS_SHOP_REFRESH) or self.appear(self.I_REFRESH_NOT_GOLD)

    def _shop_open_confirm_marker_visible(self) -> bool:
        """只用展开后的刷新标志确认；check_market 在收起时也可能出现。"""
        return self._shop_refresh_marker_visible()

    def _is_preparation_mode(self) -> bool:
        """只有无符咒弹窗的“备”可继续操作；弹窗出现立即中断。"""
        if self._read_chess_mode() != '备' or not self._chess_time_available():
            return False
        if self.appear(self.I_SELECT_GRIGRI):
            logger.debug(
                '立即中断棋局备阶段: '
                '检测到符咒选择面板'
            )
            return False
        return True

    def _chess_time_available(self) -> bool:
        """最后三秒仅观察及确认已发出的交易，不发起新操作。"""
        remaining = self._read_remaining_time()
        return remaining is not None and remaining > 3

    def _is_purchase_allowed(self) -> bool:
        return (self._read_chess_mode() in ('备', '战', '待')
                and not getattr(self, '_preparation_priority_pass', False)
                and self._chess_time_available())

    @frame_cached
    def _read_shop_gold(self) -> int | None:
        """读取当前金币；OCR 异常时返回 None，避免误停购买流程。"""
        raw = self._normalize_ocr_text(self.O_GOLD.ocr(self.device.image))
        matched = re.search(r'\d+', raw)
        if matched is None:
            logger.warning(f'棋局金币 OCR 无效: [{raw}]')
            return None
        return int(matched.group(0))

    @staticmethod
    def _parse_coin_text(raw_text: str) -> dict | None:
        """解析鼬乐币 m/600，并恢复斜杠丢失或误识别为 1/I 的结果。"""
        raw = ''.join(str(raw_text or '').split())
        if not raw:
            return None

        # 标准斜杠以及被识别为 I/l/竖线的分隔符。
        explicit = re.search(r'(\d{1,3})[/／Iil|](600)$', raw)
        recovered = False
        if explicit is not None:
            current = int(explicit.group(1))
            recovered = '/' not in raw and '／' not in raw
        else:
            digits = ''.join(re.findall(r'\d', raw))
            if not digits.endswith('600'):
                return None
            prefix = digits[:-3]
            # 3441600 表示 344/600，其中额外的 1 是斜杠误识别。
            if len(prefix) == 4 and prefix.endswith('1'):
                prefix = prefix[:-1]
                recovered = True
            elif prefix:
                recovered = True
            if not prefix:
                return None
            current = int(prefix)

        if not 0 <= current <= 600:
            return None
        return {
            'current': current,
            'total': 600,
            'raw': raw,
            'recovered': recovered,
        }

    def _read_coin(self) -> dict | None:
        """读取棋局大厅鼬乐币，OCR 无效时返回 None。"""
        raw = self._normalize_ocr_text(self.O_COIN.ocr(self.device.image))
        coin = self._parse_coin_text(raw)
        if coin is None:
            logger.warning(f'棋局鼬乐币 OCR 无效: [{raw}]')
            return None
        if coin['recovered']:
            logger.debug(
                f'棋局鼬乐币 OCR 已修正: [{raw}] -> '
                f'{coin["current"]}/{coin["total"]}'
            )
        else:
            logger.debug(
                f'棋局鼬乐币: {coin["current"]}/{coin["total"]}'
            )
        return coin

    def _coin_is_full(self) -> bool:
        """最多复查三帧，仅 600/600 才视为鼬乐币已满。"""
        for attempt in range(1, 4):
            coin = self._read_coin()
            if coin is not None:
                full = coin['current'] == coin['total'] == 600
                if full:
                    logger.info('棋局鼬乐币已满: 600/600')
                return full
            if attempt < 3:
                time.sleep(self.SCREENSHOT_INTERVAL)
                self.screenshot()
        return False

    def _can_afford_shop_shikigami(
        self,
        slot_index: int,
        known_price: int | None = None,
    ) -> bool:
        """判断购买能力；身份已确定时优先使用目录费用。"""
        if slot_index not in range(1, 6):
            logger.warning(f'棋局商店格子编号无效: {slot_index}')
            return False

        gold = self._read_shop_gold()
        raw_price = ''
        price = known_price
        if price is None:
            price, raw_price = self._read_shop_slot_price(slot_index)
        if gold is None or price is None:
            logger.warning(
                '跳过棋局商店购买，购买力 OCR 不可用: '
                f'格子={slot_index}, 金币={gold}, '
                f'价格原文=[{raw_price}]'
            )
            return False

        affordable = gold >= price
        logger.debug(
            '棋局商店购买力: '
            f'格子={slot_index}, 金币={gold}, 价格={price}, '
            f'可购买={affordable}'
        )
        return affordable

    def _read_shop_slot_price(self, slot_index: int) -> tuple[int | None, str]:
        """定位金币图标并读取其右侧费用数字。"""
        if slot_index not in range(1, 6):
            return None, ''
        price_rule = getattr(self, f'O_SHIKIGAMI_GOLD_{slot_index}')
        price_roi = tuple(price_rule.roi)
        matches = self.store_gold_rule.match_all_any(
            self.device.image,
            roi=list(price_roi),
            threshold=self.SHOP_GOLD_ICON_THRESHOLD,
            nms_threshold=0.3,
        )
        if not matches:
            logger.debug(
                '棋局商店价格图标不可用: '
                f'格子={slot_index}, roi={price_roi}'
            )
            return None, ''

        _, icon_x, _, icon_width, _ = max(
            matches,
            key=lambda item: item[0],
        )
        roi_x, roi_y, roi_width, roi_height = price_roi
        price_x = icon_x + icon_width
        price_right = roi_x + roi_width
        price_width = price_right - price_x
        if price_width <= 0:
            return None, ''

        digit_rule = RuleOcr(
            roi=(price_x, roi_y, price_width, roi_height),
            area=(price_x, roi_y, price_width, roi_height),
            mode='Single',
            method='Default',
            keyword='',
            name=f'shikigami_gold_value_{slot_index}',
        )
        raw = self._normalize_ocr_text(
            digit_rule.ocr(self.device.image)
        )
        matched = re.search(r'\d+', raw)
        if matched is None:
            return None, raw
        price = int(matched.group(0))
        if price not in range(1, 6):
            return None, raw
        return price, raw

    def _ensure_shop_open(self) -> bool:
        """必要时点击商店图标，并等待刷新按钮确认商店已经展开。"""
        if not self._is_purchase_allowed():
            logger.debug('停止打开棋局商店: 检测到鬼阶段')
            return False
        if getattr(self, '_economy_battle_mode', False):
            return self._ensure_battle_economy_shop_open()
        if self._is_shop_open():
            logger.debug('棋局商店已经打开')
            self._shop_assumed_open = True
            return True

        logger.debug('棋局商店已关闭，点击商店图标打开')
        # C_MARKET 是跨回合反复使用的合法开关；每次新状态转换单独计数。
        self.device.click_record_remove(self.I_MARKET)
        deadline = time.monotonic() + self.SHOP_OPEN_TIMEOUT
        attempts = 0
        while time.monotonic() < deadline:
            if not self._is_purchase_allowed():
                logger.debug('停止打开棋局商店: 检测到鬼阶段')
                return False
            attempts += 1
            if not self._chess_time_available():
                return False
            self.click(self.I_MARKET)
            attempt_deadline = min(
                deadline,
                time.monotonic() + 2 * self.SLOW_POLL_INTERVAL,
            )
            while time.monotonic() < attempt_deadline:
                time.sleep(self.SCREENSHOT_INTERVAL)
                self.screenshot()
                if not self._is_purchase_allowed():
                    logger.debug('停止打开棋局商店: 检测到鬼阶段')
                    return False
                if self._shop_open_confirm_marker_visible():
                    logger.debug(
                        f'棋局商店打开成功, 尝试次数={attempts}'
                    )
                    self._shop_assumed_open = True
                    return True

        logger.warning('棋局商店超时仍未打开')
        return False

    def _ensure_battle_economy_shop_open(self) -> bool:
        """战斗中单次开店后等待可见确认，不把点击或缓存当成成功。"""
        expected_mode = getattr(self, '_economy_expected_mode', None) or '战'
        if self._read_chess_mode() != expected_mode:
            logger.debug('停止战阶段经济开店: 已不在战阶段')
            return False
        if self._shop_open_confirm_marker_visible():
            self._shop_assumed_open = True
            logger.debug('棋局战阶段经济商店可见且已打开')
            return True

        # 上一帧可能被技能遮住，先等新截图再决定是否需要切换商店。
        time.sleep(self.SCREENSHOT_INTERVAL)
        self.screenshot()
        if self._read_chess_mode() != expected_mode:
            return False
        if self._shop_open_confirm_marker_visible():
            self._shop_assumed_open = True
            return True
        self._shop_assumed_open = False
        logger.debug('战阶段打开棋局商店，等待画面确认')
        self.device.click_record_remove(self.I_MARKET)
        if not self._chess_time_available():
            return False
        self.click(self.I_MARKET)
        deadline = time.monotonic() + self.SHOP_OPEN_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(self.SCREENSHOT_INTERVAL)
            self.screenshot()
            if self._read_chess_mode() != expected_mode:
                break
            if self._shop_open_confirm_marker_visible():
                self._shop_assumed_open = True
                return True
        self._shop_assumed_open = False
        logger.warning('战阶段商店未确认展开，停止购买和刷新')
        return False

    def _ensure_shop_closed(
        self,
        allowed_modes: tuple[str, ...] = ('备',),
    ) -> bool:
        """在指定模式内关闭商店；上卡默认仅允许“备”。"""
        if self._read_chess_mode() not in allowed_modes:
            logger.debug(
                '停止关闭棋局商店: 当前阶段不在 '
                f'{allowed_modes}'
            )
            return False
        shop_visible = self._shop_refresh_marker_visible()
        shop_assumed_open = getattr(self, '_shop_assumed_open', False)
        if not shop_visible and not shop_assumed_open:
            logger.debug('棋局商店已经关闭')
            return True
        if self._read_chess_mode() != '战' and not shop_visible:
            # 非战斗画面刷新按钮不会被技能遮挡；看不到即以实际画面为准，
            # 清除跨阶段遗留的内部状态，禁止误点后把商店反而打开。
            self._shop_assumed_open = False
            logger.debug('棋局商店画面上已关闭，清除残留状态')
            return True
        if (
            self._read_chess_mode() in ('鬼', '待')
            and not shop_visible
        ):
            # 进入鬼/待后游戏会自行收起商店；内部状态可能仍停留在上一帧。
            # 此时不能点击不可用的商店位置，只清除脚本侧状态。
            self._shop_assumed_open = False
            logger.debug('被动阶段清除棋局商店的残留状态')
            return True

        logger.debug('棋局商店已打开，点击商店图标关闭')
        self.device.click_record_remove(self.I_MARKET)
        # 战斗中刷新按钮可能完全被技能遮挡。若商店仅由内部状态确认，
        # 固定点击一次即可关闭，禁止进入“看不见 -> 再点一次”的抖动。
        if (
            self._read_chess_mode() == '战'
            and shop_assumed_open
            and not shop_visible
        ):
            if not self._chess_time_available():
                return False
            self.click(self.I_MARKET)
            time.sleep(2 * self.SLOW_POLL_INTERVAL)
            self.screenshot()
            self._shop_assumed_open = False
            logger.debug('棋局战阶段经济商店已由单次点击关闭')
            return True

        deadline = time.monotonic() + self.SHOP_CLOSE_TIMEOUT
        while time.monotonic() < deadline:
            if self._read_chess_mode() not in allowed_modes:
                logger.debug(
                    '停止关闭棋局商店: 阶段已切换出 '
                    f'{allowed_modes}'
                )
                return False
            if not self._chess_time_available():
                return False
            self.click(self.I_MARKET)
            attempt_deadline = min(
                deadline,
                time.monotonic() + 2 * self.SLOW_POLL_INTERVAL,
            )
            while time.monotonic() < attempt_deadline:
                time.sleep(self.SCREENSHOT_INTERVAL)
                self.screenshot()
                if self._read_chess_mode() not in allowed_modes:
                    logger.debug(
                        '停止关闭棋局商店: 阶段已切换出 '
                        f'{allowed_modes}'
                    )
                    return False
                if not self._is_shop_open():
                    logger.debug('棋局商店关闭成功')
                    self._shop_assumed_open = False
                    return True

        logger.warning('棋局商店超时仍未关闭')
        return False

    def _clear_economy_click_history(self) -> None:
        """豁免合法的经验/刷新循环，保留其他按钮的全局防重复点击保护。"""
        removed_experience = self.device.click_record_remove(self.I_EXPERIENCE)
        removed_refresh = self.device.click_record_remove(self.I_CHESS_SHOP_REFRESH)
        if removed_experience or removed_refresh:
            logger.debug(
                '合法循环前清除棋局经济点击记录: '
                f'经验={removed_experience}, 刷新={removed_refresh}'
            )

    def _match_shop_shikigami_avatar(
        self,
        click_rule: RuleClick,
        expected_name: str | None = None,
        rules: list[tuple[str, RuleImage]] | None = None,
    ) -> dict | None:
        """只在一个商店点击框内匹配 ``*_m`` 式神头像。"""
        best = None
        rules = self.shikigami_shop_rules if rules is None else rules
        for name, rule in rules:
            if expected_name is not None and name != expected_name:
                continue
            matches = rule.match_all_any(
                self.device.image,
                roi=list(click_rule.roi_back),
                threshold=rule.threshold,
                nms_threshold=0.3,
            )
            if not matches:
                continue
            score, x, y, width, height = max(matches, key=lambda item: item[0])
            if best is None or score > best['score']:
                best = {
                    'name': name,
                    'score': float(score),
                    'position': (x + width // 2, y + height // 2),
                }
        if best is not None:
            return best

        fallback = self._match_shop_shikigami_avatar_glow_fallback(
            click_rule,
            expected_name=expected_name,
            rules=rules,
        )
        if fallback is not None:
            logger.debug(
                '棋局商店头像由发光兜底匹配命中: '
                f'名称={fallback["name"]}, 分数={fallback["score"]:.3f}, '
                f'阈值={self.SHOP_GLOW_TEMPLATE_THRESHOLD}'
            )
        return fallback

    @frame_cached
    def _read_shop_slot_name(self, slot_index: int) -> str:
        name_rule = getattr(self, f'O_SHIKIGAMI_NAME_{slot_index}')
        return self._normalize_ocr_text(name_rule.ocr(self.device.image))

    def _recognize_shop_shikigami_by_name(
        self,
        slot_index: int,
        click_rule: RuleClick,
    ) -> dict | None:
        """只使用式神底部名字OCR确认商店身份。"""
        if slot_index not in range(1, 6):
            return None
        raw = self._read_shop_slot_name(slot_index)
        if not raw:
            return None

        entries = tuple(
            entry
            for entry in SHIKIGAMI_ENTRIES
            if entry.romaji not in NON_SHOP_SHIKIGAMI
        )
        exact = [
            entry
            for entry in entries
            if entry.chinese_name in raw
        ]
        if exact:
            entry = max(exact, key=lambda item: len(item.chinese_name))
            score = 1.0
        else:
            candidates = []
            for entry in entries:
                matched, similarity, _ = self._fuzzy_text_match(
                    entry.chinese_name,
                    raw,
                )
                if matched:
                    candidates.append((similarity, entry))
            if not candidates:
                logger.debug(
                    '棋局商店名称 OCR 不可用: '
                    f'格子={slot_index}, 原文=[{raw}]'
                )
                return None
            score, entry = max(candidates, key=lambda item: item[0])

        x, y, width, height = click_rule.roi_back
        logger.debug(
            '棋局商店名称身份: '
            f'格子={slot_index}, 原文=[{raw}], 分数={score:.3f} '
            f'-> {entry.romaji}'
        )
        return {
            'name': entry.romaji,
            'score': float(score),
            'position': (x + width // 2, y + height // 2),
            'source': 'ocr_name',
            'price': entry.cost,
            'bonds': entry.bonds,
            'raw_name': raw,
        }

    def _recognize_shop_shikigami_by_ocr(
        self,
        slot_index: int,
        click_rule: RuleClick,
    ) -> dict | None:
        """羁绊优先；有歧义时读取费用，仍失败则由外层图片兜底。"""
        if slot_index not in range(1, 6):
            return None

        skill_rule = getattr(self, f'O_SHIKIGAMI_SKILL_{slot_index}')
        raw_skill = self._normalize_ocr_text(
            skill_rule.ocr(self.device.image)
        )
        skill_text = normalize_bond_ocr_text(raw_skill)
        if not skill_text:
            logger.debug(
                '棋局商店 OCR 身份不可用: '
                f'格子={slot_index}, 羁绊=[{raw_skill}]'
            )
            return None

        observed_bonds = tuple(
            bond
            for bond in KNOWN_BONDS
            if bond in skill_text
        )
        observed_key = bond_key(observed_bonds)
        if not observed_key:
            logger.debug(
                '棋局商店羁绊不可用，改用图片兜底: '
                f'格子={slot_index}, 原文=[{raw_skill}]'
            )
            return None

        all_names = tuple(STORE_SHIKIGAMI_BY_SIGNATURE.values())
        candidates = [
            name
            for name in all_names
            if observed_key.issubset(
                bond_key(SHIKIGAMI_BY_ROMAJI[name].bonds)
            )
        ]

        price = None
        raw_price = ''
        source = 'ocr_bonds'
        if len(candidates) != 1:
            price, raw_price = self._read_shop_slot_price(slot_index)
            if price is None:
                logger.debug(
                    '棋局商店羁绊候选需要价格但价格 OCR 失败: '
                    f'格子={slot_index}, 羁绊={observed_bonds}, '
                    f'候选={candidates}, 价格原文=[{raw_price}]'
                )
                return None
            candidates = [
                name
                for name in candidates
                if SHIKIGAMI_BY_ROMAJI[name].cost == price
            ]
            source = 'ocr_bonds_price'

        if len(candidates) != 1:
            logger.debug(
                '棋局商店身份仍有歧义，改用图片兜底: '
                f'格子={slot_index}, 羁绊={observed_bonds}, 价格={price}, '
                f'候选={candidates}'
            )
            return None

        name = candidates[0]
        entry = SHIKIGAMI_BY_ROMAJI[name]
        x, y, width, height = click_rule.roi_back
        logger.debug(
            '棋局商店羁绊身份: '
            f'格子={slot_index}, 羁绊={observed_bonds}, '
            f'价格={price}, 来源={source} -> {name}'
        )
        return {
            'name': name,
            'score': 1.0,
            'position': (x + width // 2, y + height // 2),
            'source': source,
            # 羁绊已唯一时直接采用目录费用，购买能力判断无需再次 OCR。
            'price': entry.cost,
            'bonds': entry.bonds,
            'raw_bonds': raw_skill,
        }

    def _recognize_shop_slot(
        self,
        slot_index: int,
        click_rule: RuleClick,
        expected_name: str | None = None,
        fallback_rules: list[tuple[str, RuleImage]] | None = None,
    ) -> dict | None:
        """商店只读取底部名称，不加载人物头像或识别羁绊。"""
        recognized = self._recognize_shop_shikigami_by_name(slot_index, click_rule)
        if recognized is not None and (expected_name is None or recognized['name'] == expected_name):
            return recognized
        return None

    @staticmethod
    def _template_gray(image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return image
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _match_shop_shikigami_avatar_glow_fallback(
        self,
        click_rule: RuleClick,
        expected_name: str | None = None,
        rules: list[tuple[str, RuleImage]] | None = None,
    ) -> dict | None:
        """发光商店卡兜底：用灰度归一化匹配降低光效影响。"""
        x, y, width, height = click_rule.roi_back
        source = self.device.image[y:y + height, x:x + width]
        if source.size == 0:
            return None
        source_gray = self._template_gray(source)
        best = None
        rules = self.shikigami_shop_rules if rules is None else rules
        for name, rule in rules:
            if expected_name is not None and name != expected_name:
                continue
            template = rule.image
            if template is None or template.size == 0:
                continue
            if (
                template.shape[0] > source.shape[0]
                or template.shape[1] > source.shape[1]
            ):
                continue
            template_gray = self._template_gray(template)
            result = cv2.matchTemplate(
                source_gray,
                template_gray,
                cv2.TM_CCOEFF_NORMED,
            )
            _, score, _, location = cv2.minMaxLoc(result)
            if best is None or score > best['score']:
                best = {
                    'name': name,
                    'score': float(score),
                    'position': (
                        x + location[0] + template.shape[1] // 2,
                        y + location[1] + template.shape[0] // 2,
                    ),
                }
        if best is None:
            return None
        if best['score'] < self.SHOP_GLOW_TEMPLATE_THRESHOLD:
            logger.debug(
                '棋局商店发光兜底最佳候选低于阈值: '
                f'名称={best["name"]}, 分数={best["score"]:.3f}, '
                f'阈值={self.SHOP_GLOW_TEMPLATE_THRESHOLD}'
            )
            return None
        return best

    def _buy_shop_slot(
        self,
        slot_index: int,
        click_rule: RuleClick,
        matched_name: str,
    ) -> bool:
        """名称确认后单次点击，必须确认扣款及目标消失才登记持有量。"""
        price = SHIKIGAMI_BY_ROMAJI[matched_name].cost
        recognized = self._recognize_shop_slot(slot_index, click_rule, expected_name=matched_name)
        if recognized is None or not self._is_shop_open() or not self._is_purchase_allowed():
            return False
        before = self._read_shop_gold()
        mode, round_no = self._read_chess_mode(), self._read_round_number()
        if before is None or before < price or not self._can_afford_shop_shikigami(slot_index, known_price=price):
            return False
        # OCR/余额检查之后再次核对倒计时，漏字绝不触发补点。
        if not self._is_purchase_allowed():
            return False
        self.click(click_rule)
        for _ in range(self.ECONOMY_CONFIRM_RETRIES + 1):
            time.sleep(self.SCREENSHOT_INTERVAL)
            self.screenshot()
            if self._read_chess_mode() != mode or self._read_round_number() != round_no or not self._is_shop_open():
                return False
            after = self._read_shop_gold()
            target = self._recognize_shop_slot(slot_index, click_rule, expected_name=matched_name)
            if after == before - price and target is None:
                logger.info(f'棋局购牌已确认: {matched_name}, 格子={slot_index}, 金币={before}→{after}')
                return True
        logger.warning(f'棋局购牌未确认，停止本轮购买及刷新: {matched_name}')
        return False

    def buy_lineup_shikigami_from_shop(self) -> list[str] | None:
        """只以底部名称记录商店目标，再按记录购买所有阵容式神。"""
        if not self._is_purchase_allowed():
            logger.debug('停止棋局商店购买: 检测到鬼阶段')
            return None
        if not self._ensure_shop_open():
            return None

        logger.debug('购买前扫描全部棋局商店格子')
        targets = []
        recognized_slots = {}

        for slot_index, click_rule in self._shop_slots():
            if not self._is_purchase_allowed():
                logger.debug('停止棋局商店购买: 检测到鬼阶段')
                return None
            matched = self._recognize_shop_slot(
                slot_index,
                click_rule,
            )
            if matched is None:
                recognized_slots[slot_index] = '未识别'
                logger.debug(
                    f'棋局商店格子 {slot_index}: 身份未识别'
                )
                continue

            recognized_slots[slot_index] = self._shikigami_display_name(
                matched['name']
            )

            if matched['name'] not in self.shikigami_deploy_positions:
                logger.debug(
                    f'棋局商店格子 {slot_index}: 识别到非阵容'
                    f'卡 {matched["name"]}'
                )
                continue

            logger.debug(
                f'棋局商店格子 {slot_index}: {matched["source"]} -> '
                f'{matched["name"]}, 分数={matched["score"]:.3f}'
            )
            targets.append({
                'slot_index': slot_index,
                'click_rule': click_rule,
                'matched_name': matched['name'],
                'known_price': SHIKIGAMI_BY_ROMAJI[matched['name']].cost,
            })

        # 资源编号从右向左为 1→5；日志按玩家看到的左→右输出 5→1。
        logger.info(
            '棋局商店识别结果(左->右): '
            + ' | '.join(
                recognized_slots.get(slot_index, '未识别')
                for slot_index in range(5, 0, -1)
            )
        )
        logger.debug(
            '棋局商店目标扫描完成: '
            f'{[(item["slot_index"], item["matched_name"]) for item in targets]}'
        )
        purchased = []
        while targets:
            # 上一张买入后的优先补阵/装备会关闭商店，下一张必须重新确认展开。
            if not self._ensure_shop_open():
                return None
            priority = getattr(self, '_shop_purchase_priority', None)
            if priority is not None:
                targets.sort(key=lambda target: priority(target['matched_name']))
            target = targets.pop(0)
            if not self._is_purchase_allowed():
                logger.debug('停止棋局商店购买: 检测到鬼阶段')
                return None
            should_buy = getattr(self, '_inventory_should_buy', None)
            if should_buy is not None and not should_buy(target['matched_name']):
                continue
            if not self._can_afford_shop_shikigami(
                target['slot_index'],
                known_price=target['known_price'],
            ):
                logger.debug(
                    '跳过买不起的棋局商店目标: '
                    f'格子={target["slot_index"]}, '
                    f'名称={target["matched_name"]}'
                )
                continue
            if self._buy_shop_slot(
                slot_index=target['slot_index'],
                click_rule=target['click_rule'],
                matched_name=target['matched_name'],
            ):
                purchased.append(target['matched_name'])
                # 第一张卡购买/升星动画会短暂覆盖其他商店格。等待稳定并
                # 刷新截图后再处理目标列表中的下一格，重复卡也逐格购买。
                time.sleep(self.ACTION_SETTLE_INTERVAL)
                self.screenshot()
                after_purchase = getattr(self, '_after_lineup_purchase', None)
                if after_purchase is not None and not after_purchase(target['matched_name']):
                    return purchased
            elif not self._is_purchase_allowed():
                return None
            elif not self._can_afford_shop_shikigami(
                target['slot_index'],
                known_price=target['known_price'],
            ):
                logger.debug(
                    '棋局目标已买不起, 跳过并继续: '
                    f'格子={target["slot_index"]}, '
                    f'名称={target["matched_name"]}'
                )
                continue
            else:
                logger.warning(
                    '棋局目标购买未通过扣款及名称消失确认; '
                    f'格子={target["slot_index"]}, '
                    f'名称={target["matched_name"]}; '
                    '刷新前先停止本轮商店循环'
                )
                return None

        logger.debug(f'棋局商店检查完成, 已购买={purchased}')
        return purchased

    def purchase_lineup_cards_once(self) -> list[str] | None:
        """确保商店打开后扫描并购买，不负责关闭商店。"""
        return self.buy_lineup_shikigami_from_shop()

    def _reset_economy_state(self) -> None:
        """重置单局可暂停的回目结束任务和商店状态。"""
        self._economy_pending = False
        self._economy_step_state = 'idle'
        self._economy_sequence_level = None
        self._economy_sequence_index = 0
        self._formation_pending = False
        self._economy_battle_mode = False
        self._economy_expected_mode = None
        self._shop_assumed_open = False
        self._unconfirmed_experience_round = None
        self._unconfirmed_shop_refresh = False

    def _schedule_economy_cycle(self) -> None:
        """登记一次经济任务；已有未完成原子动作时保持其精确进度。"""
        if getattr(self, '_economy_pending', False):
            logger.debug(
                '棋局经济任务已在待处理: '
                f'状态={self._economy_step_state}'
            )
            return
        self._economy_pending = True
        self._economy_step_state = 'ready'
        logger.debug('登记棋局经济升级/刷新循环')

    def _schedule_round_end_actions(self, round_no: int) -> None:
        """登记回目结束任务；第四回目起额外登记系统站位整理。"""
        if round_no > 3:
            if not getattr(self, '_formation_pending', False):
                logger.debug(
                    f'登记第 {round_no} 回目结束后的棋局站位整理'
                )
            self._formation_pending = True
        else:
            logger.debug(
                f'棋局第 {round_no} 回目使用前期备用布阵; '
                '跳过登记站位整理'
            )
        self._schedule_economy_cycle()

    def _finish_economy_cycle(self, reason: str) -> None:
        self._economy_pending = False
        self._economy_step_state = 'idle'
        logger.debug(f'棋局经济循环完成: {reason}')

    def _click_economy_button_and_confirm_gold(
        self,
        button: RuleImage,
        expected_cost: int,
        label: str,
        allow_hidden: bool,
    ) -> str:
        """新帧确认后只点击一次；扣款未确认时本回目不再购买经验。"""
        round_no = getattr(self, '_current_round_no', -1)
        uncertain = getattr(self, '_unconfirmed_experience_round', None)
        if uncertain is not None and uncertain == round_no:
            return 'no_progress'
        expected_mode = (getattr(self, '_economy_expected_mode', None) or '战') if allow_hidden else '备'
        self.screenshot()
        if self._read_chess_mode() != expected_mode or self.appear(self.I_SELECT_GRIGRI):
            return 'no_progress'
        if self._read_round_number() != round_no:
            return 'no_progress'
        if not self.appear(button):
            logger.warning(f'无法执行棋局{label}: 当前帧未确认按钮')
            return 'no_progress'
        remaining = self._read_remaining_time()
        if remaining is None or remaining <= 3:
            return 'no_progress'
        level = self._read_level()
        gold_before = self._read_shop_gold()
        if level is None or gold_before is None:
            logger.warning(f'无法确认棋局{label}: 等级或金币 OCR 不可用')
            return 'no_progress'
        if not self._can_execute_economy_operation(level, gold_before, 'experience'):
            return 'no_progress'

        if not self._chess_time_available():
            return 'no_progress'
        self._clear_economy_click_history()
        self.click(button)
        # 在截图前记录可能已扣款。OCR 延迟或阶段变化不能触发第二次点击；
        # 下一回目会重新读取预算，当前回目只等待本次结果。
        self._unconfirmed_experience_round = round_no
        for frame in range(self.ECONOMY_CONFIRM_RETRIES + 1):
            time.sleep(self.ACTION_SETTLE_INTERVAL if frame == 0 else self.SCREENSHOT_INTERVAL)
            self.screenshot()
            if self._read_chess_mode() != expected_mode or self._read_round_number() != round_no:
                return 'unknown'
            if self.appear(self.I_SELECT_GRIGRI) or not self.appear(button):
                return 'unknown'
            gold_after = self._read_shop_gold()
            if gold_after is None:
                continue
            if gold_after <= gold_before - expected_cost:
                self._unconfirmed_experience_round = None
                logger.debug(
                    f'棋局{label}已由金币变化确认: '
                    f'{gold_before} -> {gold_after}'
                )
                return 'success'
        logger.warning(f'棋局{label}扣款未确认，本回目停止重复购买经验')
        return 'unknown'

    def _shop_slot_refresh_snapshot(self) -> dict[int, dict]:
        """保存五个商店槽位的身份和低分辨率图像，用于确认刷新。"""
        snapshot = {}
        image_height, image_width = self.device.image.shape[:2]
        for slot_index, click_rule in self._shop_slots():
            matched = self._recognize_shop_slot(
                slot_index,
                click_rule,
            )
            x, y, width, height = click_rule.roi_back
            x = max(0, int(x))
            y = max(0, int(y))
            width = min(int(width), image_width - x)
            height = min(int(height), image_height - y)
            crop = self.device.image[y:y + height, x:x + width]
            if crop.size:
                gray = self._template_gray(crop)
                signature = cv2.resize(
                    gray,
                    (32, 32),
                    interpolation=cv2.INTER_AREA,
                )
            else:
                signature = None
            snapshot[slot_index] = {
                'name': None if matched is None else matched['name'],
                'image': signature,
            }
        return snapshot

    def _shop_refresh_changed_slots(
        self,
        before: dict[int, dict],
        after: dict[int, dict],
    ) -> tuple[list[int], dict[int, float]]:
        """比较对应槽位；身份可用时比较身份，否则以卡面图像差异兜底。"""
        changed = []
        image_differences = {}
        for slot_index in range(1, 6):
            previous = before[slot_index]
            current = after[slot_index]
            previous_name = previous['name']
            current_name = current['name']
            previous_image = previous['image']
            current_image = current['image']
            difference = 0.0
            if previous_image is not None and current_image is not None:
                difference = float(np.mean(cv2.absdiff(
                    previous_image,
                    current_image,
                )))
            image_differences[slot_index] = difference
            if previous_name is not None and current_name is not None:
                slot_changed = previous_name != current_name
            else:
                slot_changed = (
                    difference
                    >= self.SHOP_REFRESH_SLOT_IMAGE_DIFF_THRESHOLD
                )
            if slot_changed:
                changed.append(slot_index)
        return changed, image_differences

    def _wait_for_shop_refresh_button(self) -> bool:
        """短暂遮挡时等待新帧；不切换商店，不按旧缓存盲点。"""
        for frame in range(3):
            if frame:
                time.sleep(self.SCREENSHOT_INTERVAL)
                self.screenshot()
            if not self._is_purchase_allowed():
                logger.info('停止棋局商店刷新: 检测到鬼阶段')
                return False
            if self.appear(self.I_CHESS_SHOP_REFRESH):
                return True
        self._shop_assumed_open = False
        logger.warning(
            '无法刷新棋局商店: 连续3帧未确认可用刷新按钮, '
            f'阶段={self._read_chess_mode()}, '
            f'匹配分数={getattr(self.I_CHESS_SHOP_REFRESH, "max_val", 0.):.3f}'
        )
        return False

    def _shop_refresh_snapshot_stable(self, previous: dict, current: dict) -> bool:
        """两张新帧中每个槽位身份或卡面均稳定，不能用全空识别确认。"""
        for index in range(1, 6):
            old, new = previous[index], current[index]
            if old['name'] != new['name']:
                return False
            if old['image'] is not None and new['image'] is not None:
                difference = float(np.mean(cv2.absdiff(old['image'], new['image'])))
                if difference >= self.SHOP_REFRESH_SLOT_IMAGE_DIFF_THRESHOLD:
                    return False
            elif old['name'] is None:
                return False
        return True

    def _click_shop_refresh_and_confirm_slots(self, allow_hidden: bool) -> str:
        """一次点击后只观察；未确认时本局不再付费刷新。"""
        if getattr(self, '_unconfirmed_shop_refresh', False):
            return 'no_progress'
        if not self._wait_for_shop_refresh_button():
            return 'no_progress'
        mode = (getattr(self, '_economy_expected_mode', None) or '战') if allow_hidden else '备'
        remaining = self._read_remaining_time()
        if self._read_chess_mode() != mode or remaining is None or remaining <= 3:
            return 'no_progress'
        round_no = self._read_round_number()
        if round_no is None:
            return 'no_progress'
        before = self._shop_slot_refresh_snapshot()
        # 五格 OCR 可能耗时；点击前必须重新核验，禁止沿用扫描前的阶段和倒计时。
        self.screenshot()
        remaining = self._read_remaining_time()
        if (self._read_round_number() != round_no or self._read_chess_mode() != mode
                or remaining is None or remaining <= 3
                or not self.appear(self.I_CHESS_SHOP_REFRESH)
                or self.appear(self.I_SELECT_GRIGRI)):
            return 'no_progress'
        gold_before = self._read_shop_gold()
        self._unconfirmed_shop_refresh = True
        self._clear_economy_click_history()
        self.click(self.I_CHESS_SHOP_REFRESH)
        previous = None
        paid = False
        for frame in range(self.ECONOMY_CONFIRM_RETRIES + 2):
            time.sleep(self.ACTION_SETTLE_INTERVAL if frame == 0 else self.SCREENSHOT_INTERVAL)
            self.screenshot()
            if (self._read_round_number() != round_no
                    or self._read_chess_mode() != mode or not self._is_shop_open()
                    or self.appear(self.I_SELECT_GRIGRI)):
                return 'no_progress'
            after = self._shop_slot_refresh_snapshot()
            gold_after = self._read_shop_gold()
            paid = paid or (gold_before is not None and gold_after is not None
                            and gold_before - gold_after == self.SHOP_REFRESH_COST)
            changed, _ = self._shop_refresh_changed_slots(before, after)
            if (previous is not None and self._shop_refresh_snapshot_stable(previous, after)
                    and (paid or changed)):
                self._unconfirmed_shop_refresh = False
                logger.info(f'棋局刷新已确认：变化槽位={changed}, 扣款={paid}')
                return 'success'
            previous = after
        logger.warning('棋局刷新结果未明，本局停止付费刷新，保留当前商店')
        return 'no_progress'

    def _economy_sequence_for_level(self, level: int) -> tuple[str, ...]:
        """返回当前阶数的原子操作序列。"""
        if level >= self._lineup_final_level():
            return ('refresh',)
        if level <= 2:
            return ('experience', 'experience')
        if level <= 7:
            return ('experience', 'experience', 'refresh')
        return ('experience', 'experience', 'refresh', 'refresh')

    def _economy_reserve_for_level(self, level: int) -> int:
        if level >= self._lineup_final_level():
            return 0
        if level <= 2:
            return 0
        elif level <= 5:
            return 35
        elif level <= 7:
            return 23
        return 10

    def _reset_economy_sequence_if_level_changed(self, level: int) -> None:
        if self._economy_sequence_level == level:
            return
        logger.debug(
            '重置棋局经济操作计数器: '
            f'{self._economy_sequence_level} -> {level}'
        )
        self._economy_sequence_level = level
        self._economy_sequence_index = 0

    def _next_economy_operation(self, level: int) -> str:
        self._reset_economy_sequence_if_level_changed(level)
        sequence = self._economy_sequence_for_level(level)
        index = self._economy_sequence_index % len(sequence)
        operation = sequence[index]
        logger.debug(
            '棋局经济下一个操作: '
            f'等级={level}, 序列={sequence}, 序号={index}, '
            f'操作={operation}'
        )
        return operation

    def _advance_economy_operation_counter(self, level: int) -> None:
        self._reset_economy_sequence_if_level_changed(level)
        sequence = self._economy_sequence_for_level(level)
        self._economy_sequence_index = (
            self._economy_sequence_index + 1
        ) % len(sequence)
        logger.debug(
            '推进棋局经济操作计数器: '
            f'等级={level}, 下一序号={self._economy_sequence_index}'
        )

    def _can_execute_economy_operation(
        self,
        level: int,
        gold: int,
        operation: str,
    ) -> bool:
        reserve = self._economy_reserve_for_level(level)
        cost = (
            self.EXPERIENCE_COST
            if operation == 'experience'
            else self.SHOP_REFRESH_COST
        )
        if level < self._lineup_final_level() and gold <= reserve:
            return False
        return gold >= reserve + cost

    def _run_economy_atomic_batch(self, battle_mode: bool = False) -> str:
        """执行一个由计数器决定的升级/刷新原子动作。"""
        if not getattr(self, '_economy_pending', False):
            return 'complete'
        if not self._is_purchase_allowed():
            logger.debug('暂停棋局经济: 检测到鬼阶段')
            return 'blocked'

        previous_battle_mode = getattr(self, '_economy_battle_mode', False)
        previous_expected_mode = getattr(self, '_economy_expected_mode', None)
        if battle_mode and previous_expected_mode is None:
            self._economy_expected_mode = self._read_chess_mode()
        self._economy_battle_mode = battle_mode
        try:
            level = self._read_level()
            gold = self._read_shop_gold()
            if level is None or gold is None:
                logger.warning(
                    '暂停棋局经济: 等级或金币 OCR 不可用'
                )
                return 'blocked'

            operation = self._next_economy_operation(level)
            if not self._can_execute_economy_operation(level, gold, operation):
                self._finish_economy_cycle(
                    f'已达预算上限, 等级={level}, 金币={gold}, '
                    f'操作={operation}, '
                    f'保留={self._economy_reserve_for_level(level)}, '
                    f'目标等级={self._lineup_final_level()}'
                )
                return 'complete'

            if operation == 'experience':
                result = self._click_economy_button_and_confirm_gold(
                    self.I_EXPERIENCE,
                    self.EXPERIENCE_COST,
                    '购买经验',
                    allow_hidden=battle_mode,
                )
                if result != 'success':
                    return 'blocked'
                self._advance_economy_operation_counter(level)
            else:
                # 只有刷新动作要求商店打开；购买经验不改变商店状态。
                if not self._ensure_shop_open():
                    return 'blocked'
                result = self._click_shop_refresh_and_confirm_slots(
                    allow_hidden=battle_mode,
                )
                if result == 'no_progress':
                    return 'blocked'
                logger.info('棋局商店刷新完成')
                self._advance_economy_operation_counter(level)
                # 槽位变化确认时商店已完成换牌；仍额外等待稳定帧，
                # 再读取底部名称，避免残余动画影响购买识别。
                time.sleep(self.ACTION_SETTLE_INTERVAL)
                self.screenshot()
                purchased = self.purchase_lineup_cards_once()
                if purchased is None:
                    logger.warning(
                        '刷新后暂停棋局经济: 购买未确认'
                    )
                    return 'blocked'
            self._economy_step_state = 'ready'

            logger.debug(
                '棋局经济原子步骤结束: '
                f'操作={operation}, 战阶段模式={battle_mode}'
            )

            # 只判断是否还有下一批；真正执行留到外层重新截图、检查回目
            # 后，确保新回目的备阶段能够抢占长时间经济循环。
            level = self._read_level()
            gold = self._read_shop_gold()
            if level is None or gold is None:
                return 'pending'
            next_operation = self._next_economy_operation(level)
            if self._can_execute_economy_operation(
                level,
                gold,
                next_operation,
            ):
                return 'pending'
            self._finish_economy_cycle(
                f'原子步骤后已达预算上限, 等级={level}, '
                f'金币={gold}, 下一操作={next_operation}, '
                f'保留={self._economy_reserve_for_level(level)}, '
                f'目标等级={self._lineup_final_level()}'
            )
            return 'complete'
        finally:
            self._economy_battle_mode = previous_battle_mode
            self._economy_expected_mode = previous_expected_mode
