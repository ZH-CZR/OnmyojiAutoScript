import re

from module.atom.ocr import RuleOcr
from module.logger import logger

BOSS_NUM_PATTERN = re.compile(r'^(\d+)\s*/\s*(\d+)$')


def parse_boss_num(text: str) -> tuple[int, int] | None:
    """把 OCR 文本解析成 (当前, 总数)，不是 x/y 形状返回 None。"""
    match = BOSS_NUM_PATTERN.match(text.strip())
    if not match:
        return None
    current, total = int(match.group(1)), int(match.group(2))
    return (current, total) if 0 <= current <= total and total > 0 else None


class BossNumCheck:
    """超鬼王门票读取：战斗结算页右上角，探索与觉醒共用。"""

    O_BOSS_NUM_SETTLE = RuleOcr(roi=(1150, 10, 72, 34), area=(1150, 10, 72, 34),
                                mode="Full", method="Default",
                                keyword="", name="boss_num_settle")

    def read_settle_boss_num(self) -> tuple[int, int] | None:
        """静默读结算页门票，读不到返回 None，不写日志。"""
        return self.read_boss_num(self.O_BOSS_NUM_SETTLE)

    def read_boss_num(self, rule) -> tuple[int, int] | None:
        if self.device.image is None:
            return None
        raw = RuleOcr(roi=rule.roi, area=rule.roi, mode='Full', method='Default',
                      keyword='', name=rule.name)
        results = raw.detect_and_ocr(self.device.image, logDisplay=False)
        return parse_boss_num(''.join((item.ocr_text or '') for item in results))

    def log_boss_num(self, cu: int, total: int) -> None:
        logger.info(f'当前鬼王掉落数量: {cu} / {total} 剩余: {total - cu}')
