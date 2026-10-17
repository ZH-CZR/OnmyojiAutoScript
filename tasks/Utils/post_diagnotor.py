import numpy as np
from enum import Enum

from module.logger import logger
from module.exception import *
from module.atom.image import RuleImage

from tasks.GlobalGame.assets import GlobalGameAssets
from tasks.SoulsTidy.assets import SoulsTidyAssets


class AnalyzeType(str, Enum):
    NONE = "none"
    SoulOverflow = "soul_overflow"


class PostDiagnotor(GlobalGameAssets, SoulsTidyAssets):
    def handle(self, e: Exception, command: str, image: np.ndarray) -> AnalyzeType:
        confirm = getattr(self, 'I_UI_CONFIRM_SAMLL', None)
        if confirm is None:
            confirm = getattr(self, 'I_UI_CONFIRM', None)
        overflow = getattr(self, 'I_ST_SOUL_OVERFLOW', None)
        if confirm is not None and overflow is not None and \
                confirm.match(image) and overflow.match(image):
            logger.warning(f"Detect soul overflow, command: {command}")
            return AnalyzeType.SoulOverflow

        return AnalyzeType.NONE
