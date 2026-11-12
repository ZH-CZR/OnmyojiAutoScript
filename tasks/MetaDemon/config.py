# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import IntEnum
from pydantic import Field, validator, model_validator
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.config_base import ConfigBase, TimeDelta, Time, dynamic_hide
from tasks.MetaDemon.lineups import MetaDemonLineups, migrate_lineups
from tasks.Component.config_scheduler import Scheduler


class BossType(IntEnum):
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5
    SIX_STARS = 6
    MONEY = 7


class MetaDemonConfig(ConfigBase):
    hide_legacy_order = dynamic_hide('fire_sequence')
    # 仅兼容旧配置；清完门票结束，不再显示或执行总时长/总次数限制。
    hide_legacy_limits = dynamic_hide('limit_time', 'limit_count')
    limit_time: Time = Field(default=Time(minute=45))
    limit_count: int = Field(default=50)
    auto_tea: bool = Field(default=False, description='疲劳度满时是否自动喝茶, 关闭则自动根据调度器等待间隔时间安排下一次调度')
    fire_sequence: str = Field(default='1 2 3 4', description='攻击顺序:从左到右,空格分隔(1:一星鬼王,2:二星鬼王...)\n例:3 2(先攻击三星鬼王然后二星鬼王)')
    powerful_list: str = Field(default='', description='开启强力鬼王列表(空格分隔),例:4 5(四星鬼王和五星鬼王开启强力追击)')

    synthesize_sequence: str = Field(default='', description='自动合成裂变之眼的星级顺序(空格分隔, 可选1-5)\n例:1 2(先合成一星再合成二星)\n一星合成免费, 二星及以上每次消耗1张合成券; 留空则关闭自动合成')

    @property
    def fire_sequence_v(self) -> list[BossType]:
        sequence_text = self.fire_sequence.strip()
        if sequence_text == '':
            return []
        fire_num_list = sequence_text.split(' ')
        fire_boss_type_list = [BossType(int(num_text)) for num_text in fire_num_list]
        return fire_boss_type_list

    @property
    def powerful_list_v(self) -> list[BossType]:
        powerful_list_text = self.powerful_list.strip()
        if powerful_list_text == '':
            return []
        powerful_num_list = powerful_list_text.split(' ')
        powerful_boss_type_list = [BossType(int(num_text)) for num_text in powerful_num_list]
        return powerful_boss_type_list

    @property
    def synthesize_sequence_v(self) -> list[BossType]:
        sequence_text = self.synthesize_sequence.strip()
        if sequence_text == '':
            return []
        result = []
        for num_text in sequence_text.split(' '):
            try:
                boss_type = BossType(int(num_text))
            except ValueError:
                continue
            # 合成面板只能选择一星到五星, 六星及以上无法作为材料
            if BossType.ONE_STAR <= boss_type <= BossType.FIVE_STARS:
                result.append(boss_type)
        return result



class MetaDemonSwitchSoulConfig(ConfigBase):
    enable: bool = Field(default=False, description='是否启用自动切换御魂,清空则不会切换对应御魂\n若是数字,则以编号方式切换御魂(组号,队伍号),组1-7,队伍1-4\n若非数字,则以ocr方式切换御魂(组名,队伍名)')
    switch_once: bool = Field(default=False, description='启用该项会一次性切换所有需要攻击的鬼王御魂(建议全部独立御魂再启用), 否则当鬼王级别变更时会自动切换对应级别御魂')
    one_star: str = Field(default='', description='一星鬼王切换御魂配置')
    enable_one_star_preset: bool = Field(default=False, description='是否战斗内切换一星鬼王预设,仅限数字切换御魂可用,否则无效,下面同理')
    two_stars: str = Field(default='', description='二星鬼王切换御魂配置')
    enable_two_stars_preset: bool = Field(default=False, description='是否战斗内切换二星鬼王预设')
    three_stars: str = Field(default='', description='三星鬼王切换御魂配置')
    enable_three_stars_preset: bool = Field(default=False, description='是否战斗内切换三星鬼王预设')
    four_stars: str = Field(default='', description='四星鬼王切换御魂配置')
    enable_four_stars_preset: bool = Field(default=False, description='是否战斗内切换四星鬼王预设')
    five_stars: str = Field(default='', description='五星鬼王切换御魂配置')
    enable_five_stars_preset: bool = Field(default=False, description='是否战斗内切换五星鬼王预设')
    six_stars: str = Field(default='', description='六星鬼王切换御魂配置')
    enable_six_stars_preset: bool = Field(default=False, description='是否战斗内切换六星鬼王预设')
    # money: str = Field(default='', description='氪金鬼王切换御魂配置')
    # enable_money_preset: bool = Field(default=False, description='是否切换氪金鬼王预设')

    def get_switch_by_enum(self, boss_type: BossType) -> tuple[str, tuple[str | int, str | int]]:
        """根据枚举获取对应的 切换类型, (group,team)"""
        return self.get_switch_by_name(boss_type.name.lower())

    def get_switch_by_name(self, switch_name: str) -> tuple[str, tuple[str | int, str | int]]:
        """根据名称获取对应的御魂预设"""
        group_team = getattr(self, switch_name, None)
        if group_team is None or group_team.strip() == '' or ',' not in group_team or len(group_team.split(',')) != 2:
            return None, (None, None)
        group, team = group_team.split(',')
        if group.isdigit() and team.isdigit():
            return 'int', (int(group), int(team))
        return 'str', (group, team)

    def get_general_battle_conf(self, boss_type: BossType) -> GeneralBattleConfig:
        """获取通用战斗配置"""
        if boss_type is None:
            return GeneralBattleConfig()
        enable_preset = getattr(self, f'enable_{boss_type.name.lower()}_preset', False)
        if not enable_preset:
            return GeneralBattleConfig()
        switch_type, (group, team) = self.get_switch_by_enum(boss_type)
        if switch_type is None or switch_type == 'str':
            return GeneralBattleConfig()
        if switch_type == 'int':
            return GeneralBattleConfig(lock_team_enable=False, preset_enable=True, preset_group=group, preset_team=team)
        return GeneralBattleConfig()


class MetaDemonPresetSwitchConfig(ConfigBase):
    """预设切换: 鬼王挑战页「组名+齿轮」面板, 按组名/队名 OCR 点击并点出战应用。"""
    enable: bool = Field(default=False, title='执行任务前切换预设',
                         description='执行任务前按鬼王星级切换预设队伍, 通过挑战页右下「组名+齿轮」面板点\"出战\"应用\n出战时若御魂与预设不一致会弹窗确认并自动装配御魂\n启用后不再执行\"执行任务前切换御魂\"的式神录流程')
    switch_once: bool = Field(default=False, title='一次性全切',
                              description='启用后按\"攻击顺序\"一次性切换序列内所有星级的预设队伍(相同组名和队伍名只切一次)\n否则只在星级变更后按当前鬼王星级切一次')
    common_stars: str = Field(default='', title='1-4星',
                              description='1-4星鬼王切换预设队伍配置(组名,队伍名)\n例:限时活动,通用')
    five_stars: str = Field(default='', title='5星', description='五星鬼王切换预设队伍配置(组名,队伍名)')
    six_stars: str = Field(default='', title='6星', description='六星鬼王切换预设队伍配置(组名,队伍名)')
    # money: str = Field(default='', description='氪金鬼王切换预设队伍配置')
    name_map: str = Field(default='', title='5/6星名字映射',
                          description='按鬼王名字切换预设队伍, 仅5/6星生效, 优先级高于5星/6星默认配置\n格式: 名字:组名,队名 多个条目用分号隔开\n例:梦山白藏主:限时活动,通用;卑弥呼:限时活动,超鬼王群体\nOCR识别的名字不在映射里时用5星/6星默认配置, 默认配置留空则不切换预设')

    @validator('common_stars', 'five_stars', 'six_stars', 'name_map', pre=True)
    def normalize_fullwidth_comma(cls, value):
        """输入中的中文逗号/冒号/分号自动转成英文符号, 免得按名称切换解析失败"""
        if isinstance(value, str):
            return value.replace('，', ',').replace('：', ':').replace('；', ';')
        return value

    def get_preset_by_enum(self, boss_type: BossType) -> tuple[str | None, str | None]:
        """根据星级取 (组名, 队伍名); 1-4星共用 common_stars, 无配置返回 (None, None)"""
        if BossType.ONE_STAR <= boss_type <= BossType.FOUR_STARS:
            name = 'common_stars'
        else:
            name = boss_type.name.lower()
        group_team = getattr(self, name, '') if name else ''
        if group_team is None or ',' not in str(group_team) or len(str(group_team).split(',')) != 2:
            return None, None
        group, team = (part.strip() for part in str(group_team).split(','))
        return (group, team) if group and team else (None, None)

    def get_preset_by_name(self, boss_name: str) -> tuple[str | None, str | None]:
        """按鬼王名字查 name_map, 命中返回 (组名, 队伍名), 未命中返回 (None, None)。

        条目格式 名字:组名,队名, 分号分隔; 名字匹配先精确后互含(容 OCR 缺字)。
        """
        text = (self.name_map or '').strip()
        if not text or not boss_name:
            return None, None
        name_target = boss_name.replace(' ', '').strip()
        if not name_target:
            return None, None
        for entry in text.split(';'):
            entry = entry.strip()
            if not entry or ':' not in entry:
                continue
            name, _, group_team = entry.partition(':')
            name = name.replace(' ', '').strip()
            group_team = group_team.strip()
            if not name or ',' not in group_team or len(group_team.split(',')) != 2:
                continue
            group, team = (part.strip() for part in group_team.split(','))
            if group and team and name == name_target:
                return group, team
        return None, None


class MetaDemonScheduler(Scheduler):
    wait_interval: TimeDelta = Field(default=TimeDelta(hours=1, minutes=40), description='疲劳度满时等多长时间后再次运行本任务,建议设置等待完全恢复疲劳度所需的时间\n例:100分钟恢复100点疲劳度,再次运行必定可以继续战斗')

    # hide_fields = dynamic_hide('server_update', 'delay_date')


class MetaDemon(ConfigBase):
    scheduler: MetaDemonScheduler = Field(default_factory=MetaDemonScheduler)
    meta_demon_config: MetaDemonConfig = Field(default_factory=MetaDemonConfig)
    switch_soul: MetaDemonSwitchSoulConfig = Field(default_factory=MetaDemonSwitchSoulConfig)
    preset_switch: MetaDemonPresetSwitchConfig = Field(default_factory=MetaDemonPresetSwitchConfig)
    lineup_config: MetaDemonLineups = Field(default_factory=MetaDemonLineups)
    hide_old_lineups = dynamic_hide('switch_soul', 'preset_switch')
    _migrate_lineups = model_validator(mode='before')(migrate_lineups)
