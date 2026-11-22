# This Python file uses the following encoding: utf-8

"""百鬼棋局阵容工坊：自定义阵容的浏览、编辑与应用。"""

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tasks.Chess.strategy.custom_lineups import (
    BONDS,
    EMBLEMS,
    ROOT,
    CustomLineup,
    builtin_documents,
    delete_lineup,
    read_lineups,
    save_lineup,
)
from tasks.Chess.strategy.shikigami_catalog import (
    SHIKIGAMI_BY_ROMAJI,
    SHIKIGAMI_ENTRIES,
)
from tasks.Chess.strategy.soul_catalog import SOUL_BY_ROMAJI, SOUL_ENTRIES

chesslineup_app = APIRouter(
    prefix='/tool/chesslineup',
    tags=['chesslineup'],
)
WEB = Path(__file__).resolve().parent / 'web' / 'chesslineup'
CHESS_DIR = Path(__file__).resolve().parents[2] / 'tasks' / 'Chess'


@chesslineup_app.get('')
async def editor():
    return FileResponse(WEB / 'index.html')


@chesslineup_app.get('/api/catalog')
async def catalog():
    def image(kind, key):
        return f'/tool/chesslineup/asset/{kind}/{key}'

    return {
        'shikigami': [
            {
                'key': entry.romaji,
                'name': entry.chinese_name,
                'cost': entry.cost,
                'bonds': list(entry.bonds),
                'image': image('shikigami', entry.romaji),
            }
            for entry in SHIKIGAMI_ENTRIES
        ],
        'soul': [
            {
                'key': entry.romaji,
                'name': entry.chinese_name,
                'category': entry.category,
                'image': image('soul', entry.romaji),
            }
            for entry in SOUL_ENTRIES
        ],
        # 纹章没有本地卡面，前端用文字卡代替。
        'emblem': [
            {'key': key, 'name': name, 'image': ''}
            for key, name in EMBLEMS.items()
        ],
        'bonds': BONDS,
        'configs': sorted(
            path.stem
            for path in (ROOT / 'config').glob('*.json')
            if path.stem != 'template'
        ),
    }


@chesslineup_app.get('/asset/{kind}/{key}')
async def asset(kind: str, key: str):
    """只暴露目录内的卡面，避免任意路径读取。"""
    if kind == 'shikigami' and key in SHIKIGAMI_BY_ROMAJI:
        path = CHESS_DIR / 'shikigami' / 'card' / f'card_{key}.png'
    elif kind == 'soul' and key in SOUL_BY_ROMAJI:
        path = CHESS_DIR / 'soul' / f'sou_{key}.png'
    else:
        raise HTTPException(404, '卡面不存在')
    if not path.is_file():
        raise HTTPException(404, '卡面不存在')
    return FileResponse(path)


@chesslineup_app.get('/api/lineups')
async def lineups():
    return {
        'builtin': list(builtin_documents().values()),
        'custom': list(read_lineups().values()),
    }


@chesslineup_app.post('/api/lineups')
async def save(
    data: CustomLineup,
    source: Literal['builtin', 'custom'] = 'custom',
):
    if source == 'builtin':
        raise HTTPException(409, '内置阵容只读，请使用“另存为”后再保存')
    return save_lineup(data)


def _custom_lineup_references(key: str) -> list[str]:
    """找出仍在使用该自定义阵容的脚本配置名。"""
    references = []
    for path in (ROOT / 'config').glob('*.json'):
        if path.stem == 'template':
            continue
        try:
            raw = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, json.JSONDecodeError):
            continue
        chess = raw.get('chess') or {}
        active = (chess.get('chess_config') or {}).get('custom_lineup', '')
        if str(active).removeprefix('custom:') == key:
            references.append(path.stem)
    return references


@chesslineup_app.delete('/api/lineups/{source}/{key}')
async def remove(
    source: Literal['builtin', 'custom'],
    key: str,
):
    if source == 'builtin':
        raise HTTPException(409, '内置阵容不可删除')
    references = _custom_lineup_references(key)
    if references:
        raise HTTPException(
            409,
            '阵容仍被以下脚本使用，请先切换：' + '、'.join(references),
        )
    try:
        delete_lineup(key)
    except KeyError:
        raise HTTPException(404, '阵容不存在')
    return {'message': '阵容已删除'}


class ApplyBody(BaseModel):
    key: str
    script: str
    source: Literal['builtin', 'custom'] = 'custom'


@chesslineup_app.post('/api/apply')
async def apply(data: ApplyBody):
    if data.key not in read_lineups():
        raise HTTPException(404, '请先保存阵容')
    if not re.fullmatch(r'[\w -]{1,80}', data.script) or data.script == 'template':
        raise HTTPException(400, '脚本配置名无效')
    if not (ROOT / 'config' / f'{data.script}.json').is_file():
        raise HTTPException(404, '脚本配置不存在')

    from module.server.main_manager import mm

    config = mm.config_cache(data.script)
    config.model.chess.chess_config.custom_lineup = data.key
    config.save()
    return {
        'message': (
            f'已应用至 {data.script}，'
            '下一次启动百鬼棋局时使用'
        )
    }
