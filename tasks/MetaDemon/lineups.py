"""Unified MetaDemon lineup settings and per-encounter attack plans."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from tasks.Component.config_base import ConfigBase, dynamic_hide


def normalize_lineup(value):
    value = str(value or '').replace('，', ',').strip()
    if not value:
        return ''
    parts = [p.strip() for p in value.split(',')]
    if len(parts) != 2 or not all(parts):
        raise ValueError('阵容格式为 分组名,队伍名')
    return ','.join(parts)


class BossAttack(BaseModel):
    lineup: str = ''
    powerful: bool = False
    mark_main: bool = False
    _normalize = field_validator('lineup', mode='before')(normalize_lineup)


class SpecificBoss(BaseModel):
    boss_name: str
    attack_count: Literal[1, 2] = 1
    first_attack: BossAttack = Field(default_factory=BossAttack)
    second_attack: BossAttack = Field(default_factory=BossAttack)

    @field_validator('boss_name')
    @classmethod
    def valid_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('请填写鬼王完整名称')
        return value


class MetaDemonLineups(ConfigBase):
    enable: bool = Field(default=False, description='每次挑战前检查阵容；与上次挑战相同则跳过御魂切换')
    preset_enable: bool = Field(default=False, description='勾选后在挑战页右侧应用预设，出现御魂不一致弹窗时点击确定自动装配；不再进入式神录。未勾选则只切换御魂。预设须填写实际分组名和队伍名')
    common_stars: str = Field(default='', description='1至4星共用阵容，填写分组名,队伍名；旧版不同阵容会沿用，填写并保存本项后统一替代；新配置留空保留当前阵容')
    five_stars: str = Field(default='', description='五星通用阵容，填写分组名,队伍名')
    six_stars: str = Field(default='', description='六星通用阵容，填写分组名,队伍名')
    specific_bosses: list[SpecificBoss] = Field(default=[], json_schema_extra={'type': 'meta_demon_bosses'})
    # Preserve old distinct 1-4 star teams until common_stars is explicitly set.
    legacy_stars: dict[str, str] = Field(default={})
    hide_legacy = dynamic_hide('legacy_stars')
    _normalize = field_validator('common_stars', 'five_stars', 'six_stars', mode='before')(normalize_lineup)

    @field_validator('specific_bosses')
    @classmethod
    def unique_bosses(cls, values):
        names = [v.boss_name.replace(' ', '') for v in values]
        if len(names) != len(set(names)):
            raise ValueError('特定鬼王名称不能重复')
        return values

    def common_lineup(self, star):
        if star is None:
            return ''
        if 1 <= int(star) <= 4:
            return self.common_stars or self.legacy_stars.get(str(int(star)), '')
        return self.five_stars if int(star) == 5 else self.six_stars if int(star) == 6 else ''

    def specific(self, name):
        name = name.replace(' ', '').strip()
        return next((b for b in self.specific_bosses if b.boss_name.replace(' ', '') == name), None) if name else None


def migrate_lineups(data):
    if not isinstance(data, dict):
        return data
    soul = data.get('switch_soul') or {}
    preset = data.get('preset_switch') or {}
    cfg = {'enable': bool(soul.get('enable') or preset.get('enable')),
           'preset_enable': bool(preset.get('enable')), 'specific_bosses': []}
    if preset.get('enable'):
        for key in ('common_stars', 'five_stars', 'six_stars'):
            cfg[key] = preset.get(key, '')
        for entry in preset.get('name_map', '').replace('：', ':').replace('；', ';').replace('，', ',').split(';'):
            name, sep, lineup = entry.partition(':')
            if sep and name.strip() and lineup.strip():
                cfg['specific_bosses'].append({'boss_name': name.strip(), 'first_attack': {'lineup': lineup}})
    else:
        names = ['one_star', 'two_stars', 'three_stars', 'four_stars']
        teams = [soul.get(k, '') for k in names]
        if len(set(teams)) == 1:
            cfg['common_stars'] = teams[0]
        else:
            cfg['legacy_stars'] = {str(i+1): team for i, team in enumerate(teams) if team}
        for key in ('five_stars', 'six_stars'):
            cfg[key] = soul.get(key, '')
        # Existing per-star battle presets become the optional unified checkbox.
        cfg['preset_enable'] = any(soul.get('enable_'+key+'_preset', False) for key in (*names, 'five_stars', 'six_stars'))
    # Delta saves can create a partial new group; explicit values always win.
    cfg.update(data.get('lineup_config') or {})
    return {**data, 'lineup_config': cfg}
