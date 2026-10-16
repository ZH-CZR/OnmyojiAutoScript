# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase, DateTime, MultiLine
from tasks.Component.config_scheduler import Scheduler


class SummonType(str, Enum):
    default = '普通召唤'
    recall = '今忆召唤'


class DoneRecord(ConfigBase):
    courtyard_affairs_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    pickup_email_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    summon_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    guild_donate_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    luck_msg_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    store_sign_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    sushi_dt: DateTime = Field(default=DateTime.fromisoformat("2023-01-01 00:00:00"))
    guild_donate_finish: bool = Field(default=False)

class DailyTriflesConfig(BaseModel):
    # 日志备份
    enable_backup_log: bool = Field(default=True, title='日志备份')
    # 邮件领取
    enable_mail: bool = Field(default=False)
    # 庭院事务
    enable_courtyard_affairs: bool = Field(default=True)
    # 大神签到
    big_god_sign_in: bool = Field(default=False, title='大神签到')

    # 式神集结
    shikigami_massed: bool = Field(default=True)
    # 铜铃礼包
    copper_box: bool = Field(default=True)
    # 每日一抽
    one_summon: bool = Field(default=False)
    # summon_type: SummonType = Field(default=SummonType.default, description='召唤类型')
    # friend_love: bool = Field(default=False)
    # 吉闻
    luck_msg: bool = Field(default=False)
    # 招募成员
    recruit_members: bool = Field(default=False)
    # 抽奖箱
    lottery_box: bool = Field(default=True)
    # 式神碎片合成
    shikigami_debris: bool = Field(default=False)
    # 商店签到 签到50次得黑蛋的
    store_sign: bool = Field(default=False, description='store_sign_help')
    # 召唤破碎的咒符
    broken_amulet: int = Field(default=0, description='trifles_broken_amulet_help')
    # 每天购买体力数量
    buy_sushi_count: int = Field(default=0)


class DailyTriflesScheduler(Scheduler):
    enable: bool = Field(default=True, description='enable_help')

class DailyGuildDonate(ConfigBase):
    enable: bool = Field(default=False)
    auto_get_rewards: bool = Field(default=True)
    notify_enable: bool = Field(default=False, description='guild_donate_notify_help')
    guild_member_list: MultiLine = Field(default='', description='guild_member_list_help')
    friend_list: MultiLine = Field(default='', description='invite_friend_list_help')
    name_check: bool = Field(default=True, description='guild_donate_name_check_help')

    @property
    def guild_member_list_v(self) -> list[str]:
        if not self.guild_member_list or self.guild_member_list == '' or self.guild_member_list.strip() == '' or \
                len(self.guild_member_list.split('\n')) == 0:
            return []
        return [line.strip() for line in self.guild_member_list.split('\n') if line.strip() != '']

    @property
    def friend_list_v(self) -> list[str]:
        if not self.friend_list or self.friend_list == '' or self.friend_list.strip() == '' or \
                len(self.friend_list.split('\n')) == 0:
            return []
        return [line.strip() for line in self.friend_list.split('\n') if line.strip() != '']


class DailyTrifles(ConfigBase):
    scheduler: DailyTriflesScheduler = Field(default_factory=DailyTriflesScheduler)
    trifles_config: DailyTriflesConfig = Field(default_factory=DailyTriflesConfig)
    guild_donate: DailyGuildDonate = Field(default_factory=DailyGuildDonate)
