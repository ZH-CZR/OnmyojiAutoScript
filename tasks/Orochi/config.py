# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
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
    NONE = '不选择'
    TEN30 = '拾层-30'
    ELEVEN30 = '悲鸣-30'
    TWELVE50 = '神罚-50'
    TWELVE120 = '神罚-120'


class NextDayOrochiConfig(BaseModel):
    plan: Plan = Field(default=Plan.NONE, title='御魂任务选择', description='orochi_plan_help')
    # 层数
    layer: Layer = Field(default=Layer.ELEVEN, description='layer_help')
    # 限制次数
    limit_count: int = Field(default=30)
    # 仅保留用于加载旧配置，执行时间统一由调度器控制。
    start_time: Time = Field(default=Time(hour=11), title='启动时间')
    # 清理御魂
    soulstidy_enabled: bool = Field(default=False, title='清理御魂')

    @field_validator('plan', mode='before')
    @classmethod
    def migrate_plan(cls, value):
        if value in ('无限循环', '只执行一次下面的配置',
                     '本次不执行，设置明天运行(拾层-30)'):
            return Plan.NONE
        return value

    @model_validator(mode='after')
    def apply_preset(self):
        presets = {
            Plan.TEN30: (Layer.TEN, 30),
            Plan.ELEVEN30: (Layer.ELEVEN, 30),
            Plan.TWELVE50: (Layer.TWELVE, 50),
            Plan.TWELVE120: (Layer.TWELVE, 120),
        }
        if self.plan in presets:
            self.layer, self.limit_count = presets[self.plan]
        return self

    @staticmethod
    def _hide_legacy_time(schema):
        schema['properties'].pop('start_time', None)

    model_config = {'json_schema_extra': _hide_legacy_time}


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

    @model_validator(mode='before')
    @classmethod
    def migrate_start_time(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        settings = values.get('next_day_orochi_config', {})
        scheduler = values.get('scheduler', {})
        if isinstance(settings, dict) and isinstance(scheduler, dict):
            legacy = settings.get('start_time')
            if legacy is not None and 'server_update' not in scheduler:
                values['scheduler'] = {**scheduler, 'server_update': legacy}
        return values
