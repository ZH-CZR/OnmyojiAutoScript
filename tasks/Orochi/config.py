# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralInvite.config_invite import InviteConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class UserStatus(str, Enum):
    LEADER = 'leader'
    MEMBER = 'member'
    ALONE = 'alone'
    # WILD = 'wild'  # 还不打算实现


class Layer(str, Enum):
    ONE = '壹层'
    TWO = '贰层'
    THREE = '叁层'
    FOUR = '肆层'
    FIVE = '伍层'
    SIX = '陆层'
    SEVEN = '柒层'
    EIGHT = '捌层'
    NINE = '玖层'
    TEN = '拾层'
    ELEVEN = '悲鸣'
    TWELVE = '神罚'
    THIRTEEN = '虚无'


class Plan(str, Enum):
    default = '无限循环'
    TEN30 = '拾层-30'
    ELEVEN30 = '悲鸣-30'
    TWELVE50 = '神罚-50'
    TWELVE120 = '神罚-120'
    ONE = '只执行一次下面的配置'
    end = '本次不执行，设置明天运行(拾层-30)'


class NextDayOrochiConfig(BaseModel):
    # 设定时间为第二天的启动时间
    # next_day_orochi_enable: bool = Field(title='设定时间为第二天的启动时间', default=True, description='设定时间为第二天的启动时间')
    plan: Plan = Field(default=Plan.TEN30, title='御魂任务选择')
    # 层数
    layer: Layer = Field(default=Layer.ELEVEN, description='layer_help')
    # 限制次数
    limit_count: int = Field(default=30)
    # 启动时间
    start_time: Time = Field(default=Time(hour=11), title='启动时间')
    # 清理御魂
    soulstidy_enabled: bool = Field(default=False, title='清理御魂')


class OrochiConfig(ConfigBase):
    # 身份
    user_status: UserStatus = Field(default=UserStatus.LEADER, description='user_status_help')
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))
    # 是否开启御魂加成
    soul_buff_enable: bool = Field(default=False, description='soul_buff_enable_help')


class SwitchSoulConfig(BaseModel):
    enable: bool = Field(default=False)
    ten_switch: str = Field(default='-1,-1', title='魂十切换御魂')
    eleven_switch: str = Field(default='-1,-1', title='悲鸣切换御魂')
    twelve_switch: str = Field(default='-1,-1', title='神罚切换御魂')
    thirteen_switch: str = Field(default='-1,-1', title='虚无切换御魂')


class Orochi(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    next_day_orochi_config: NextDayOrochiConfig = Field(default_factory=NextDayOrochiConfig)
    orochi_config: OrochiConfig = Field(default_factory=OrochiConfig)
    invite_config: InviteConfig = Field(default_factory=InviteConfig)
    general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
