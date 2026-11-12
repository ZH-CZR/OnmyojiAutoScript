# This Python file uses the following encoding: utf-8
# @brief    Configurations for Ryou Dokan Toppa (阴阳竂道馆突破配置)
# @author   jackyhwei
# @note     draft version without full test
# github    https://github.com/roarhill/oas

from pydantic import BaseModel, Field, validator
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class WelfareConfig(BaseModel):
    # 是否只开福利寮
    welfare_enable: bool = Field(default=False, title='是否优先开启福利寮')
    offline_battle_enable: bool = Field(default=False, title='福利寮离线战斗',
                                      description='dokan_offline_battle_help')
    # 福利寮刷新次数
    fresh_num: int = Field(default=5, title='福利寮刷新次数')
    # 福利寮最少人数限制
    min_people_num: int = Field(default=-1, title='福利寮最少人数')
    # 刷新多少次才开始减少人数
    fresh_num_less_people: int = Field(default=20, title='刷新多少次才开始减少人数')
    # 是否发送请求检查福利寮开启
    enable_get_requests: bool = Field(default=False, title='是否发送请求检查福利寮开启', hidden=True)
    get_requests_url: str = Field(default='', title='获取请求的URL', hidden=True)


class DokanConfig(BaseModel):
    # # 寮管理开启道馆
    dokan_enable: bool = Field(default=False, title='寮管理开启道馆')
    weekend_abyss_enable: bool = Field(default=False, title='五六七开启狭间',
                                     description='dokan_weekend_abyss_help')
    dokan_battle_count: int = Field(default=2, title='道馆战斗场次')
    # 刷新次数
    fresh_num: int = Field(default=5, title='刷新次数')
    # 道馆系数,赏金/人数 根据喜好配置
    find_dokan_score: float = Field(default=4.6, description='dokan_score_help')
    # 道馆最小人数限制
    min_people_num: int = Field(default=-1, description='min_people_num_help')
    # 最少赏金设置
    min_bounty: int = Field(default=0, description='min_bounty_help')

    # # 选择哪一个竂
    # dokan_declear_war_priority: int = Field(default=0, description='dokan_declear_war_priority_help')

    # 攻击优先顺序: 见习=0,初级=1...
    # dokan_attack_priority: int = Field(default=0, description='dokan_attack_priority_help')

    # 失败CD后自动加油
    # dokan_auto_cheering_while_cd: bool = Field(default=False, description='dokan_auto_cheering_while_cd_help')

    # 正式进攻会设定 2s - 10s 的随机延迟，避免攻击间隔及其相近被检测为脚本。
    # random_delay: bool = Field(default=False, description='random_delay_help')

    # 防封：使用固定的随机区域进行随机点击，若为False将自动识别当前画面中的最大纯色区域作为随机点击区域
    # anti_detect_click_fixed_random_area: bool = Field(default=False, description='anti_detect_click_fixed_random_area_help')


class QQMessageConfig(BaseModel):
    enable: bool = Field(default=False, title='启用QQ群消息检查', description='仅在勾选“是否优先开启福利寮”时检查；未勾选时按原道馆流程运行')
    builtin_qq: bool = Field(default=False, hidden=True, title='旧内置QQ选项', description='内置登录已停用，统一使用外接OneBot')
    group_id: str = Field(default='', title='监听群号')
    member_id: str = Field(default='', title='监听成员QQ号', description='按QQ号筛选，不使用昵称或群名片')
    keywords: str = Field(default='', title='放行关键词', description='多个关键词用换行或英文竖线分隔，包含任意一个即满足')
    excluded_keywords: str = Field(default='', title='排除关键词', description='同一条消息包含任意排除词时不放行，例如“未开启”；换行或英文竖线分隔')
    retry_minutes: int = Field(default=3, ge=1, le=1440, title='未匹配后等待分钟数')
    max_checks: int = Field(default=10, ge=1, le=1000, title='每天最大未匹配次数', description='未匹配或接口失败才计次；匹配不消耗次数，重启或立即执行不清零')
    reset_today_checks: bool = Field(default=False, title='重置当天检查次数为0次',
                                    description='勾选保存后立即清零当前配置的当天次数；自动恢复关闭，不修改任务运行时间或消息缓存')
    callback_secret: str = Field(default='', title='事件上报签名密钥（可选）', description='仅使用历史查询时留空；实时上报时与NapCat HTTP客户端Token一致')
    history_api_url: str = Field(default='', title='群历史消息API地址', description='NapCat HTTP服务端地址，例如 http://127.0.0.1:3000；这里不填WebUI管理端口')
    history_api_token: str = Field(default='', title='历史消息API访问令牌', description='填写NapCat HTTP服务端的Token，不是WebUI登录密码')
    history_page_size: int = Field(default=100, ge=1, le=500, title='每页历史消息数量')
    history_max_pages: int = Field(default=5, ge=1, le=20, title='每次最多读取历史页数', description='分页有上限；未读到匹配消息时仍按未放行重试')

    @validator('builtin_qq', pre=True, always=True)
    def disable_retired_builtin(cls, value):
        return False

    @validator('reset_today_checks', pre=True, always=True)
    def keep_reset_action_off(cls, value):
        # 一次性操作只由配置保存入口执行，读取/复制配置不能重复触发。
        return False

    class Config:
        validate_assignment = True


class Dokan(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    dokan_config: DokanConfig = Field(default_factory=DokanConfig)
    welfare_config: WelfareConfig = Field(default_factory=WelfareConfig)
    qq_message_config: QQMessageConfig = Field(default_factory=QQMessageConfig, title='QQ群消息检查')
    general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    general_battle_config2: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
    switch_soul_config2: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
