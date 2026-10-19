# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import Field, model_validator

from tasks.Component.config_base import ConfigBase, TimeDelta, DateTime, Time

class ExecutionMode(str, Enum):
    TIMED = '定时执行'
    IDLE = '闲时执行'


class IdleGoal(str, Enum):
    DAILY = '每日目标'
    WEEKLY = '每周目标'
    SESSION = '本次目标'


class Scheduler(ConfigBase):
    enable: bool = Field(default=False, description='enable_help')
    execution_mode: ExecutionMode = Field(default=ExecutionMode.TIMED, description='execution_mode_help')
    idle_goal: IdleGoal = Field(default=IdleGoal.DAILY, description='idle_goal_help')
    idle_start_minutes: int = Field(default=15, ge=1, description='idle_start_minutes_help')
    idle_stop_minutes: int = Field(default=5, ge=0, description='idle_stop_minutes_help')
    next_run: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"), description='next_run_help')
    priority: int = Field(default=5, description='priority_help')

    success_interval: TimeDelta = Field(default=TimeDelta(days=1), description='success_interval_help')
    failure_interval: TimeDelta = Field(default=TimeDelta(days=1), description='failure_interval_help')
    server_update: Time = Field(default=Time(hour=9, minute=0, second=0), description='server_update_help')
    delay_date: int = Field(default=1, description='delay_date_help', ge=1, le=31)
    float_time: Time = Field(default=Time(hour=0, minute=0, second=0), description='float_time_help')

    @model_validator(mode='after')
    def validate_idle_window(self):
        if self.idle_start_minutes <= self.idle_stop_minutes:
            raise ValueError('闲时开始余量 Y 必须大于让位余量 X')
        return self


if __name__ == "__main__":
    dict_s = {
        "enable": False,
        "next_run": "2026-07-19T14:15:37",
        "priority": 5,
        "success_interval": "10 00:00:01",
        "failure_interval": "10 00:00:01",
        "server_update": "09:03:00",
        "float_time": "02:00:05"
    }
    s = Scheduler(**dict_s)
    print(s.model_dump())



