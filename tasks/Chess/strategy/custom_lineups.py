# This Python file uses the following encoding: utf-8

"""百鬼棋局自定义阵容：校验、持久化与运行时策略转换。

Web 阵容工坊（``/tool/chesslineup``）与主任务共用本模块：

- 工坊把编辑结果写入 ``custom_lineups.json``（version 2）；
- 主任务在开局边界读取同一份 JSON，转换成与内置阵容同结构的策略。

槽位模型使用 12 个固定位置；式神按罗马音保存，装备只允许御魂
（``soul``）和纹章（``emblem``）。纹章以羁绊名参与运行时决策。
"""

import json
from collections import Counter
from pathlib import Path
from typing import Literal

from filelock import FileLock
from pydantic import BaseModel, Field, model_validator

from tasks.Chess.strategy.shikigami_catalog import (
    SHIKIGAMI_BY_ROMAJI,
    build_lineup_shikigami,
)
from tasks.Chess.strategy.soul_catalog import SOUL_BY_ROMAJI

ROOT = Path(__file__).resolve().parents[3]
STORE = Path(__file__).with_suffix('.json')

# 纹章键与上游阵容工坊保持一致；运行时只使用 ``名字``。
EMBLEMS = {
    'haiguo': '海国纹章',
    'jiazhou': '甲胄纹章',
    'dajiangshan': '大江山纹章',
    'mingfu': '冥府纹章',
    'huangchuan': '荒川纹章',
    'qijiaoshan': '七角山纹章',
    'pinganjing': '平安京纹章',
    'fenlie': '分裂纹章',
    'yixing': '易形纹章',
    'shizhan': '嗜战纹章',
    'duanren': '锻刃纹章',
    'qiangti': '强体纹章',
    'huyou': '护佑纹章',
    'guihuo': '鬼火纹章',
    'hanshuang': '寒霜纹章',
    'huyao': '狐妖纹章',
    'liuhuo': '流火纹章',
    'huixiang': '回响纹章',
    'yinian': '遗念纹章',
}
BONDS = sorted({
    bond
    for entry in SHIKIGAMI_BY_ROMAJI.values()
    for bond in entry.bonds
})


class Equipment(BaseModel):
    kind: Literal['soul', 'emblem']
    key: str


class Slot(BaseModel):
    shikigami: str | None = None
    weight: int = Field(default=1, ge=0, le=99)
    equipment: list[Equipment] = Field(default_factory=list, max_length=2)


def lineup_bond_counts(slots) -> Counter:
    """统计阵容羁绊；纹章按对应羁绊计入。"""
    counts = Counter()
    for slot in slots:
        if slot.shikigami:
            counts.update(SHIKIGAMI_BY_ROMAJI[slot.shikigami].bonds)
        for item in slot.equipment:
            if item.kind == 'emblem':
                counts[EMBLEMS[item.key].removesuffix('纹章')] += 1
    return counts


def goldfish_position(slots, preferred=None):
    """优先保留指定空位；否则从 12 号位向前补，满员时返回 None。"""
    if preferred is not None and not slots[preferred - 1].shikigami:
        return preferred
    return next(
        (
            index
            for index in range(12, 0, -1)
            if not slots[index - 1].shikigami
        ),
        None,
    )


class CustomLineup(BaseModel):
    key: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    display_name: str = Field(min_length=1, max_length=40)
    slots: list[Slot] = Field(min_length=12, max_length=12)
    primary_bond: str = ''
    secondary_bond: str = ''
    hakuzosu_protect_position: int | None = Field(default=None, ge=1, le=12)
    arakawa_goldfish_position: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode='after')
    def valid_assignment(self):
        self.display_name = self.display_name.strip()
        if not self.display_name:
            raise ValueError('阵容名称不能为空')
        names = []
        for slot in self.slots:
            if slot.shikigami is None:
                if slot.equipment:
                    raise ValueError('空槽位不能装备御魂或纹章')
                continue
            if slot.shikigami not in SHIKIGAMI_BY_ROMAJI:
                raise ValueError(f'未知式神：{slot.shikigami}')
            names.append(slot.shikigami)
            seen = set()
            for equipment in slot.equipment:
                library = (
                    SOUL_BY_ROMAJI
                    if equipment.kind == 'soul'
                    else EMBLEMS
                )
                identity = (equipment.kind, equipment.key)
                if equipment.key not in library:
                    raise ValueError(f'未知装备：{equipment.key}')
                if identity in seen:
                    raise ValueError('同一式神不能重复装备相同御魂或纹章')
                if (
                    equipment.kind == 'emblem'
                    and EMBLEMS[equipment.key].removesuffix('纹章')
                    in SHIKIGAMI_BY_ROMAJI[slot.shikigami].bonds
                ):
                    raise ValueError('式神已具有该羁绊，不能装备对应纹章')
                seen.add(identity)
        if not 1 <= len(names) <= 10:
            raise ValueError('阵容需要 1–10 名式神')
        if len(names) != len(set(names)):
            raise ValueError('阵容中不能重复放置同名式神')
        for bond in (self.primary_bond, self.secondary_bond):
            if bond and bond not in BONDS:
                raise ValueError(f'未知羁绊：{bond}')
        counts = lineup_bond_counts(self.slots)
        if self.secondary_bond and not counts.get(self.secondary_bond):
            raise ValueError('次要羁绊必须是当前阵容已有的羁绊')
        if counts.get('荒川', 0) >= 2:
            self.arakawa_goldfish_position = goldfish_position(
                self.slots,
                self.arakawa_goldfish_position,
            )
        else:
            self.arakawa_goldfish_position = None
        if self.hakuzosu_protect_position:
            if not self.slots[self.hakuzosu_protect_position - 1].shikigami:
                raise ValueError('守护之印目标必须是已上阵式神')
            if 'yume_san_byakuzou' not in names:
                raise ValueError('使用守护之印需要上阵梦山白藏主')
        return self

    def strategy(self, prefix='custom:') -> dict:
        """转换成主任务使用的标准阵容结构。"""
        shikigami = build_lineup_shikigami({
            slot.shikigami: {
                'position': index,
                'weight': slot.weight,
                'souls': [
                    item.key
                    for item in slot.equipment
                    if item.kind == 'soul'
                ],
                'emblems': [
                    EMBLEMS[item.key]
                    for item in slot.equipment
                    if item.kind == 'emblem'
                ],
            }
            for index, slot in enumerate(self.slots, 1)
            if slot.shikigami
        })
        counts = lineup_bond_counts(self.slots)
        return {
            'key': prefix + self.key,
            'display_name': self.display_name,
            'shikigami': shikigami,
            'primary_bond': (
                self.primary_bond
                or (
                    counts.most_common(1)[0][0]
                    if counts
                    else self.display_name
                )
            ),
            'secondary_bond': self.secondary_bond,
            'hakuzosu_protect_position': self.hakuzosu_protect_position,
            'arakawa_goldfish_position': self.arakawa_goldfish_position,
        }


def read_collection(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding='utf-8'))
    if 'version' in raw:
        if raw['version'] != 2 or not isinstance(raw.get('lineups'), list):
            raise ValueError('阵容 JSON 格式无效')
        documents = raw['lineups']
    else:
        documents = list(raw.values())
    result = {}
    for document in documents:
        model = CustomLineup.model_validate(document)
        if model.key in result:
            raise ValueError(f'重复阵容标识：{model.key}')
        result[model.key] = model.model_dump()
    return result


def write_collection(path, documents) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(
        json.dumps(
            {'version': 2, 'lineups': list(documents.values())},
            ensure_ascii=False,
            indent=2,
        ) + '\n',
        encoding='utf-8',
    )
    temporary.replace(path)


def read_lineups() -> dict:
    return read_collection(STORE)


def save_lineup(lineup: CustomLineup, overwrite=True) -> dict:
    with FileLock(str(STORE) + '.lock'):
        data = read_lineups()
        if not overwrite and lineup.key in data:
            raise FileExistsError(lineup.key)
        data[lineup.key] = lineup.model_dump()
        write_collection(STORE, data)
    return data[lineup.key]


def delete_lineup(key: str) -> None:
    with FileLock(str(STORE) + '.lock'):
        data = read_lineups()
        if key not in data:
            raise KeyError(key)
        del data[key]
        write_collection(STORE, data)


def load_strategy(key: str) -> dict:
    """按标识读取自定义阵容；不存在时抛错，由调用方决定回退。"""
    raw = read_lineups().get(key)
    if raw is None:
        raise ValueError(f'自定义阵容不存在：{key}')
    return CustomLineup.model_validate(raw).strategy()


def builtin_documents() -> dict:
    """把内置 Python 阵容转换成工坊文档，供“打开已有阵容”使用。"""
    from tasks.Chess.strategy.lineup import LINEUP_REGISTRY

    documents = {}
    for key, entry in LINEUP_REGISTRY.items():
        strategy = entry['strategy']
        slots = [Slot() for _ in range(12)]
        for name, unit in strategy['shikigami'].items():
            position = int(unit['position'])
            while slots[position - 1].shikigami is not None:
                position = position % 12 + 1
            slots[position - 1] = Slot(
                shikigami=name,
                weight=int(unit['deploy_weight']),
                # 内置阵容可能声明三件候选御魂，工坊只有两个装备位。
                equipment=[
                    Equipment(kind='soul', key=soul)
                    for soul in unit['preferred_souls'][:2]
                ],
            )
        documents[key] = {
            'key': key,
            'display_name': entry['display_name'],
            'slots': [slot.model_dump() for slot in slots],
            'primary_bond': entry['display_name'],
            'secondary_bond': '',
            'hakuzosu_protect_position': strategy.get(
                'hakuzosu_protect_position'
            ),
            'arakawa_goldfish_position': strategy.get(
                'arakawa_goldfish_position'
            ),
        }
    return documents
