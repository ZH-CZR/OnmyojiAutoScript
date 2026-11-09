# This Python file uses the following encoding: utf-8
"""旧导入路径的兼容出口；式神数据和转换接口统一由 strategy 目录维护。"""
from tasks.Chess.strategy.shikigami_catalog import (
    ShikigamiEntry,
    SHIKIGAMI_ENTRIES,
    SHIKIGAMI_BY_KEY,
    SHIKIGAMI_BY_ROMAJI,
    SHIKIGAMI_BY_CHINESE_NAME,
    NON_SHOP_SHIKIGAMI,
    BOND_OCR_ALIASES,
    SHIKIGAMI_BONDS_BY_ROMAJI,
    STORE_SHIKIGAMI_BY_SIGNATURE,
    KNOWN_BONDS,
    LEGACY_SHIKIGAMI_KEYS,
    normalize_bond_ocr_text,
    bond_key,
    resolve_shikigami,
    build_lineup_shikigami,
)
