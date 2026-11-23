# This Python file uses the following encoding: utf-8

"""百鬼棋局阵容工坊：数据校验、策略转换与持久化。"""

import pytest

from tasks.Chess.config import ChessConfig
from tasks.Chess.runtime.recognition import ChessRecognitionMixin
from tasks.Chess.strategy import custom_lineups
from tasks.Chess.strategy.custom_lineups import (
    CustomLineup,
    Equipment,
    Slot,
    builtin_documents,
    read_collection,
    write_collection,
)
from tasks.Chess.strategy.lineup import LINEUP_REGISTRY


def _document(**overrides):
    slots = [Slot().model_dump() for _ in range(12)]
    slots[0] = {
        'shikigami': 'kaoru',
        'weight': 1,
        'equipment': [],
    }
    slots[1] = {
        'shikigami': 'yume_san_byakuzou',
        'weight': 2,
        'equipment': [{'kind': 'emblem', 'key': 'haiguo'}],
    }
    document = {
        'key': 'test_lineup',
        'display_name': '测试阵容',
        'slots': slots,
        'primary_bond': '',
        'secondary_bond': '',
        'hakuzosu_protect_position': 2,
        'arakawa_goldfish_position': None,
    }
    document.update(overrides)
    return document


def test_strategy_from_custom_lineup():
    lineup = CustomLineup.model_validate(_document())
    strategy = lineup.strategy()

    assert strategy['key'] == 'custom:test_lineup'
    assert set(strategy['shikigami']) == {'kaoru', 'yume_san_byakuzou'}
    kaoru = strategy['shikigami']['kaoru']
    assert kaoru['position'] == 1
    assert kaoru['equip_hakuzosu_protect'] is False
    assert strategy['hakuzosu_protect_position'] == 2
    assert strategy['shikigami']['yume_san_byakuzou']['preferred_emblems'] == (
        '海国纹章',
    )
    # 鬼火在阵容中出现两次，自动成为主羁绊。
    assert strategy['primary_bond'] == '鬼火'


def test_strategy_uses_explicit_bonds():
    lineup = CustomLineup.model_validate(_document(
        primary_bond='七角山',
        secondary_bond='鬼火',
        hakuzosu_protect_position=None,
    ))
    strategy = lineup.strategy()
    assert strategy['primary_bond'] == '七角山'
    assert strategy['secondary_bond'] == '鬼火'
    assert strategy['shikigami']['kaoru']['equip_hakuzosu_protect'] is False


def test_reject_invalid_equipment():
    document = _document(primary_bond='')
    document['slots'][0]['equipment'] = [
        {'kind': 'emblem', 'key': 'qijiaoshan'},
    ]
    with pytest.raises(ValueError, match='已具有该羁绊'):
        CustomLineup.model_validate(document)

    document = _document(primary_bond='')
    document['slots'][0]['equipment'] = [{'kind': 'soul', 'key': 'unknown'}]
    with pytest.raises(ValueError, match='未知装备'):
        CustomLineup.model_validate(document)


def test_reject_duplicate_and_empty_slot_equipment():
    document = _document(primary_bond='')
    document['slots'][2] = {
        'shikigami': 'kaoru',
        'weight': 1,
        'equipment': [],
    }
    with pytest.raises(ValueError, match='不能重复放置同名式神'):
        CustomLineup.model_validate(document)

    document = _document(primary_bond='')
    document['slots'][2] = {
        'shikigami': None,
        'weight': 1,
        'equipment': [{'kind': 'soul', 'key': 'poshi'}],
    }
    with pytest.raises(ValueError, match='空槽位不能装备'):
        CustomLineup.model_validate(document)


def test_collection_round_trip(tmp_path):
    path = tmp_path / 'lineups.json'
    lineup = CustomLineup.model_validate(_document())
    write_collection(path, {lineup.key: lineup.model_dump()})

    assert read_collection(path) == {lineup.key: lineup.model_dump()}


def test_builtin_documents_cover_registry():
    documents = builtin_documents()
    assert set(documents) == set(LINEUP_REGISTRY)
    for document in documents.values():
        assert len(document['slots']) == 12
        occupied = [slot for slot in document['slots'] if slot['shikigami']]
        assert 1 <= len(occupied) <= 10


def test_custom_lineup_config_default():
    assert ChessConfig().custom_lineup == ''
    assert Equipment(kind='soul', key='poshi').key == 'poshi'


class _LineupStub(ChessRecognitionMixin):
    DEFAULT_LINEUP_KEY = 'arakawa'
    LINEUP_REGISTRY = LINEUP_REGISTRY


def test_custom_lineup_is_snapshotted(monkeypatch):
    raw = {CustomLineup.model_validate(_document()).key: _document()}
    monkeypatch.setattr(custom_lineups, 'read_lineups', lambda: dict(raw))

    stub = _LineupStub()
    strategy = stub.select_custom_lineup('test_lineup')
    assert strategy['key'] == 'custom:test_lineup'

    # 一局内后续识别直接使用快照，不再读取阵容文件。
    monkeypatch.setattr(
        custom_lineups,
        'read_lineups',
        lambda: (_ for _ in ()).throw(AssertionError('不应重复读取')),
    )
    assert stub.get_lineup_strategy() is stub._lineup_strategy_snapshot
