# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import json
from pathlib import Path

from cached_property import cached_property
from pydantic import BaseModel, ValidationError, validator, Field

from module.config.utils import *


class ConfigMenu:
    # 手动的代码配置菜单
    def __init__(self) -> None:
        self.menu = {}
        # 总览
        self.menu["Overview"] = []
        self.menu['TaskList'] = []
        # 脚本设置
        self.menu['Script'] = ['Script', 'GlobalGame', 'Restart']
        # 刷御魂
        self.menu["Soul Zones"] = ['Orochi', 'Sougenbi', 'FallenSun', 'EternitySea', 'SixRealms', 'OtherWorldTwilight']
        # 日常的任务
        self.menu["Daily Task"] = ['DailyTrifles', 'AreaBoss', 'GoldYoukai', 'ExperienceYoukai', 'Nian',
                                   'TalismanPass', 'DemonEncounter', 'Pets', 'SoulsTidy', 'Delegation', 'WantedQuests',
                                   'Tako', 'AutoCheckinBigGod']
        # 很肝的任务
        self.menu["Liver Emperor Exclusive"] = [
            "BondlingFairyland",
            "EvoZone",
            "GoryouRealm",
            "Exploration",
            "Hyakkiyakou",
            "HeroTest",
            "FindJade",
            "MemoryScrolls"
        ]
        # 阴阳寮
        self.menu["Guild"] = ['KekkaiUtilize', 'KekkaiActivation', 'RealmRaid', 'RyouToppa', 'Dokan', 'CollectiveMissions',
                              'Hunt' , 'AbyssShadows', 'GuildBanquet', 'DemonRetreat', 'GuildActivityMonitor']
        # 每周任务
        self.menu["Weekly Task"] = ['TrueOrochi', 'RichMan', 'Secret', 'WeeklyTrifles', 'MysteryShop', 'Duel', 'Chess']
        # 活动的任务
        self.menu["Activity Task"] = ['ActivityShikigami', 'MartialTournament', 'MetaDemonTicket', 'MetaDemon', 'ChaoGuiWang', 'ChaoGuiWangAssist', 'FrogBoss', 'FrogChallenge', 'FloatParade', 'LBS', 'Quiz', 'KittyShop', 'DyeTrials', 'GuguArtStudio', 'IbukiArena']
        # 开发工具
        self.menu["Tools"] = ['Image Rule', 'Ocr Rule', 'Click Rule', 'Long Click Rule', 'Swipe Rule', 'List Rule']
        # 自定义流程
        self.menu["Custom Flow"] = ['CustomFlow']
        # 标注器「生成代码」创建的流程任务（任务目录里有 .flow_auto 标记）自动进菜单
        tasks_root = Path(__file__).resolve().parents[2] / "tasks"
        if tasks_root.is_dir():
            for task_dir in sorted(tasks_root.iterdir()):
                name = task_dir.name
                if not task_dir.is_dir() or name in self.menu["Custom Flow"]:
                    continue
                if (task_dir / ".flow_auto").exists() and (task_dir / "config.py").exists():
                    self.menu["Custom Flow"].append(name)

    @cached_property
    def gui_menu(self) -> str:
        """
        生成的是json字符串
        :return:
        """
        return json.dumps(self.menu, ensure_ascii=False, sort_keys=False, default=str)

    @cached_property
    def gui_menu_list(self) -> dict:
        del self.menu['TaskList']
        del self.menu['Tools']
        return self.menu


if __name__ == "__main__":
    try:
        m = ConfigMenu()
        print(m.gui_menu)
    except:
        print('weih')
