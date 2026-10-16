from pydantic import Field

from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class GuildGift(ConfigBase):
    """购买阴阳寮礼包。"""

    scheduler: Scheduler = Field(default_factory=Scheduler)
