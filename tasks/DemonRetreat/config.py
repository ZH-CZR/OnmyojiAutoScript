# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime, time, timedelta
import random
from pydantic import Field, field_validator, model_validator
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase, Time, TimeDelta, dynamic_hide
from tasks.Component.config_scheduler import Scheduler


class DemonRetreatTime(ConfigBase):
    # 自定义运行时间
    custom_run_time: Time = Field(default=Time(hour=10, minute=0, second=0))


class DemonRetreatScheduler(Scheduler):
    saturday_time: Time = Field(default=time(11), description='demon_retreat_time_help')
    failure_interval: TimeDelta = Field(default=timedelta(minutes=10), description='failure_interval_help')

    @field_validator('saturday_time')
    @classmethod
    def validate_saturday_time(cls, value):
        if not time(11) <= value < time(23):
            raise ValueError('首领退治执行时间必须在 11:00:00（含）至 23:00:00（不含）之间')
        return value

    @staticmethod
    def is_open(now: datetime) -> bool:
        return now.weekday() == 5 and time(11) <= now.time() < time(23)

    def next_weekly_run(self, now: datetime, completed: bool = False) -> datetime:
        days = (5 - now.weekday()) % 7
        if days == 0 and (completed or now.time() >= time(23)):
            days = 7
        return datetime.combine(now.date() + timedelta(days=days), self.saturday_time)

    def within_open_window(self, target: datetime) -> datetime:
        return target if self.is_open(target) else self.next_weekly_run(target)

    def add_random_delay(self, target: datetime) -> datetime:
        maximum = self.float_time.hour * 3600 + self.float_time.minute * 60 + self.float_time.second
        # 将抽签范围限制在本次开放窗口内，最晚为 22:59:59。
        remaining = int((target.replace(hour=23, minute=0, second=0) - target).total_seconds()) - 1
        return target + timedelta(seconds=random.randint(0, min(maximum, max(0, remaining))))

    @staticmethod
    def _hide_unused(schema):
        for name in ('server_update', 'success_interval', 'delay_date'):
            schema['properties'].pop(name, None)

    model_config = {'json_schema_extra': _hide_unused}


class DemonRetreat(ConfigBase):
    scheduler: DemonRetreatScheduler = Field(default_factory=DemonRetreatScheduler)
    demon_retreat_time: DemonRetreatTime = Field(default_factory=DemonRetreatTime)
    general_battle: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)

    hide_legacy_time = dynamic_hide('demon_retreat_time')

    @model_validator(mode='before')
    @classmethod
    def migrate_execution_time(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        scheduler = values.get('scheduler', {})
        if not isinstance(scheduler, dict) or 'saturday_time' in scheduler:
            return values
        scheduler = dict(scheduler)
        legacy = values.get('demon_retreat_time', {})
        old_time = legacy.get('custom_run_time') if isinstance(legacy, dict) else None
        old_time = old_time if old_time is not None else scheduler.get('server_update')
        if old_time is not None:
            old_time = time.fromisoformat(old_time) if isinstance(old_time, str) else old_time
            scheduler['saturday_time'] = max(time(11), old_time) if old_time < time(23) else time(11)
        values['scheduler'] = scheduler
        return values
