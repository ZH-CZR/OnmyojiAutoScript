import re

from pydantic import BaseModel, Field, field_validator
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler



def parse_random_delay_interval(value: str) -> tuple[int, int]:
    matched = re.fullmatch(r'\s*(\d+)\s*[,，]\s*(\d+)\s*', value)
    if matched is None:
        raise ValueError('随机延迟区间须为两个非负整数秒，例如2,10')
    lower, upper = map(int, matched.groups())
    if lower > upper:
        raise ValueError('随机延迟最小秒数不能大于最大秒数')
    return lower, upper


class RaidConfig(BaseModel):
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))
    # 限制次数
    limit_count: int = Field(default=50)
    # 是否跳过难度较高的结界，失败后不再攻打该结界
    skip_difficult: bool = Field(default=True, description='skip_difficult_help')
    # 寮管理开启寮突破
    ryou_access: bool = Field(default=False, description='ryou_access_help')
    # 正式进攻前按秒数区间抽取一次延迟，旧配置默认2至10秒。
    random_delay: bool = Field(default=False, description='random_delay_help')
    random_delay_interval: str = Field(default='2,10', description='random_delay_interval_help')

    @field_validator('random_delay_interval')
    @classmethod
    def validate_random_delay_interval(cls, value: str) -> str:
        lower, upper = parse_random_delay_interval(value)
        return f'{lower},{upper}'


    # raid_mode: RaidMode = Field(default=RaidMode.ATTACK_ALL,
    #                             description='raid_mode_help')
    # attack_number: AttackNumber = Field(default=AttackNumber.ALL,
    #                                     description='')
    # 打完没票了 0/6 => 失败
    # 突破压根没开  +> 失败
    # 时间打满了  成功
    # 次数打满了  成功
    # 打完了（有失败的但是大不了） 成功



class RyouToppa(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    raid_config: RaidConfig = Field(default_factory=RaidConfig)
    general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
