# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class RaidMode(str, Enum):
    NORMAL = 'retreat_four_attack_nine'
    ATTACK_ALL = 'attack_all'


class AttackNumber(str, Enum):
    NINE = 'nine'
    ALL = 'all'


class WhenAttackFail(str, Enum):
    EXIT = 'Exit'
    CONTINUE = 'Continue'
    REFRESH = 'Refresh'

class ExitType(str, Enum):
    NotEXIT = '不退'
    NineExitFour = '9退4'
    EightExitFour = '18退4'


class RaidConfig(BaseModel):
    number_attack_all: int = Field(title='总挑战次数', default=30, description='默认30，可选范围[1~30]，没有挑战卷自动退出任务（标记为成功）')
    number_attack_success: int = Field(title='成功挑战次数', default=30, description='成功挑战次数，默认30，可选范围[1~30]，没有挑战卷自动退出任务（标记为成功）')
    number_base: int = Field(default=0, description='number_base_help')
    exit_type: ExitType = Field(default=ExitType.NineExitFour, title='个突退出类型')
    order_attack: str = Field(default='5 > 4 > 3 > 2 > 1 > 0', description='order_attack_help')
    three_refresh: bool = Field(default=False, description='three_refresh_help')
    when_attack_fail: WhenAttackFail = Field(default=WhenAttackFail.REFRESH, description='when_attack_fail_help')


class RealmRaid(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    raid_config: RaidConfig = Field(default_factory=RaidConfig)
    general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
