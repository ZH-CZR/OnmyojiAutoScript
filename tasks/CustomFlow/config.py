# -*- coding: utf-8 -*-
"""自定义流程任务的配置：选哪个 flow、什么时候跑。"""
from pydantic import Field

from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class FlowSetting(ConfigBase):
    flow_name: str = Field(default="", description="要运行的流程名，对应 flows/<name>.json")
    stop_after_end: bool = Field(default=False, description="流程结束后不再自动排下一次")


class CustomFlow(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    flow: FlowSetting = Field(default_factory=FlowSetting)
