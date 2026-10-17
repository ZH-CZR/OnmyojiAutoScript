# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime, time, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType


class HuntScheduler(Scheduler):
    kirin_time: Time = Field(default=time(9), description='kirin_time_help')
    netherworld_time: Time = Field(default=time(17), description='netherworld_time_help')

    @model_validator(mode='before')
    @classmethod
    def migrate_server_update(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        legacy = values.get('server_update')
        if legacy is not None:
            legacy = time.fromisoformat(legacy) if isinstance(legacy, str) else legacy
            # 仅沿用位于对应活动开放时段内的旧时间，不覆盖独立设置。
            if time(6) <= legacy <= time(23):
                values.setdefault('kirin_time', legacy)
            if time(17) <= legacy <= time(23):
                values.setdefault('netherworld_time', legacy)
        return values

    @field_validator('kirin_time', 'netherworld_time')
    @classmethod
    def validate_activity_time(cls, value, info):
        start = time(6) if info.field_name == 'kirin_time' else time(17)
        if not start <= value <= time(23):
            raise ValueError(f'执行时间必须在 {start} 至 23:00:00 之间')
        return value

    def execution_time(self, day):
        return self.kirin_time if day.weekday() < 4 else self.netherworld_time

    def next_open_run(self, now: datetime) -> datetime:
        day = now.date()
        if now.time() > time(23):
            day += timedelta(days=1)
        return datetime.combine(day, self.execution_time(day))

    @staticmethod
    def _hide_legacy_time(schema):
        schema['properties'].pop('server_update', None)

    # 旧字段保留用于加载历史配置，界面只展示两个独立时间。
    model_config = {'json_schema_extra': _hide_legacy_time}


class KirinConfig(BaseModel):
    enable_task: bool = Field(default=True, description='是否开启麒麟任务')
    enable: bool = Field(default=False, description='是否启用御魂切换')
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')
    # 是否开启绿标
    green_enable: bool = Field(default=False, description='green_enable_help')
    # 选哪一个绿标
    green_mark: GreenMarkType = Field(default=GreenMarkType.GREEN_LEFT1, description='green_mark_help')
    # 超时退出战斗
    exit_battle_second: int = Field(default=0, description='超时退出战斗（单位秒）, 0代表不退出')


class NetherWorldConfig(BaseModel):
    enable_task: bool = Field(default=True, description='是否开启阴界任务')
    enable: bool = Field(default=False, description='是否启用御魂切换')
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')

    # 是否开启绿标
    green_enable: bool = Field(default=False, description='green_enable_help')
    # 选哪一个绿标
    green_mark: GreenMarkType = Field(default=GreenMarkType.GREEN_LEFT1, description='green_mark_help')

    # 超时退出战斗
    exit_battle_second: int = Field(default=0, description='超时退出战斗（单位秒）, 0代表不退出')


class Hunt(ConfigBase):
    scheduler: HuntScheduler = Field(default_factory=HuntScheduler)
    kirin_config: KirinConfig = Field(default_factory=KirinConfig)
    nether_world_config: NetherWorldConfig = Field(default_factory=NetherWorldConfig)
