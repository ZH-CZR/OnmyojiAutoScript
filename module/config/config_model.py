from typing import Dict, Any
import re
import inflection
from pathlib import Path
from pydantic import BaseModel, ValidationError, Field
from module.config.utils import *
from module.logger import logger
from tasks.Component.config_base import ConfigBase, TimeDelta
from tasks.AbyssShadows.config import AbyssShadows
from tasks.ActivityCommon.config import ActivityCommon
from tasks.ActivityCommon2.config import ActivityCommon2
from tasks.ActivitySimple.config import ActivitySimple
from tasks.AreaBoss.config import AreaBoss
from tasks.AutoCake.config import AutoCake
from tasks.BondlingFairyland.config import BondlingFairyland
from tasks.Chess.config import Chess
from tasks.CollectiveMissions.config import CollectiveMissions
from tasks.DailyTrifles.config import DailyTrifles
from tasks.Delegation.config import Delegation
from tasks.DemonEncounter.config import DemonEncounter
from tasks.DemonRetreat.config import DemonRetreat
from tasks.Dokan.config import Dokan
from tasks.Duel.config import Duel
from tasks.EternitySea.config import EternitySea
from tasks.EvoZone.config import EvoZone
from tasks.ExperienceYoukai.config import ExperienceYoukai
from tasks.Exploration.config import Exploration
from tasks.FallenSun.config import FallenSun
from tasks.FloatParade.config import FloatParade
from tasks.FrogBoss.config import FrogBoss
from tasks.GlobalGame.config import GlobalGame
from tasks.GoldYoukai.config import GoldYoukai
from tasks.GoryouRealm.config import GoryouRealm
from tasks.GuildBanquet.config import GuildBanquet
from tasks.HeroTest.config import HeroTest
from tasks.Hunt.config import Hunt
from tasks.Hyakkiyakou.config import Hyakkiyakou
from tasks.KekkaiActivation.config import KekkaiActivation
from tasks.KekkaiUtilize.config import KekkaiUtilize
from tasks.KittyShop.config import KittyShop
from tasks.LBS.config import LBS
from tasks.MainStory.config import MainStory
from tasks.MemoryScrolls.config import MemoryScrolls
from tasks.MetaDemon.config import MetaDemon
from tasks.MysteryShop.config import MysteryShop
from tasks.Nian.config import Nian
from tasks.NianTrue.config import NianTrue
from tasks.Orochi.config import Orochi
from tasks.Pets.config import Pets
from tasks.Quiz.config import Quiz
from tasks.RealmRaid.config import RealmRaid
from tasks.Restart.config import Restart
from tasks.RichMan.config import RichMan
from tasks.RyouToppa.config import RyouToppa
from tasks.Script.config import Script
from tasks.Secret.config import Secret
from tasks.SixRealms.config import SixRealms
from tasks.Sougenbi.config import Sougenbi
from tasks.SoulsTidy.config import SoulsTidy
from tasks.SwitchAccountConfig.config import SwitchAccountConfig
from tasks.Tako.config import Tako
from tasks.TalismanPass.config import TalismanPass
from tasks.TrueOrochi.config import TrueOrochi
from tasks.WantedQuests.config import WantedQuests
from tasks.WeeklyTrifles.config import WeeklyTrifles
from tasks.Netherworld.config import Netherworld

class ConfigModel(ConfigBase):
    config_name: str = "yys"
    running_task: str = ""
    script: Script = Field(default_factory=Script)
    restart: Restart = Field(default_factory=Restart)
    global_game: GlobalGame = Field(default_factory=GlobalGame)
    area_boss: AreaBoss = Field(default_factory=AreaBoss)
    experience_youkai: ExperienceYoukai = Field(default_factory=ExperienceYoukai)
    gold_youkai: GoldYoukai = Field(default_factory=GoldYoukai)
    nian: Nian = Field(default_factory=Nian)
    realm_raid: RealmRaid = Field(default_factory=RealmRaid)
    ryou_toppa: RyouToppa = Field(default_factory=RyouToppa)
    kekkai_utilize: KekkaiUtilize = Field(default_factory=KekkaiUtilize)
    kekkai_activation: KekkaiActivation = Field(default_factory=KekkaiActivation)
    demon_encounter: DemonEncounter = Field(default_factory=DemonEncounter)
    daily_trifles: DailyTrifles = Field(default_factory=DailyTrifles)
    talisman_pass: TalismanPass = Field(default_factory=TalismanPass)
    pets: Pets = Field(default_factory=Pets)
    souls_tidy: SoulsTidy = Field(default_factory=SoulsTidy)
    delegation: Delegation = Field(default_factory=Delegation)
    exploration: Exploration = Field(default_factory=Exploration)
    wanted_quests: WantedQuests = Field(default_factory=WantedQuests)
    tako: Tako = Field(default_factory=Tako)
    orochi: Orochi = Field(default_factory=Orochi)
    sougenbi: Sougenbi = Field(default_factory=Sougenbi)
    fallen_sun: FallenSun = Field(default_factory=FallenSun)
    eternity_sea: EternitySea = Field(default_factory=EternitySea)
    six_realms: SixRealms = Field(default_factory=SixRealms)
    activity_simple: ActivitySimple = Field(default_factory=ActivitySimple)
    activity_common: ActivityCommon = Field(default_factory=ActivityCommon)
    activity_common_2: ActivityCommon2 = Field(default_factory=ActivityCommon2)
    auto_cake: AutoCake = Field(default_factory=AutoCake)
    meta_demon: MetaDemon = Field(default_factory=MetaDemon)
    frog_boss: FrogBoss = Field(default_factory=FrogBoss)
    float_parade: FloatParade = Field(default_factory=FloatParade)
    quiz: Quiz = Field(default_factory=Quiz)
    kitty_shop: KittyShop = Field(default_factory=KittyShop)
    nian_true: NianTrue = Field(default_factory=NianTrue)
    main_story: MainStory = Field(default_factory=MainStory)
    lbs: LBS = Field(default_factory=LBS)
    switch_account_config: SwitchAccountConfig = Field(default_factory=SwitchAccountConfig)
    bondling_fairyland: BondlingFairyland = Field(default_factory=BondlingFairyland)
    evo_zone: EvoZone = Field(default_factory=EvoZone)
    goryou_realm: GoryouRealm = Field(default_factory=GoryouRealm)
    hyakkiyakou: Hyakkiyakou = Field(default_factory=Hyakkiyakou)
    chess: Chess = Field(default_factory=Chess)
    hero_test: HeroTest = Field(default_factory=HeroTest)
    memory_scrolls: MemoryScrolls = Field(default_factory=MemoryScrolls)
    true_orochi: TrueOrochi = Field(default_factory=TrueOrochi)
    rich_man: RichMan = Field(default_factory=RichMan)
    secret: Secret = Field(default_factory=Secret)
    weekly_trifles: WeeklyTrifles = Field(default_factory=WeeklyTrifles)
    mystery_shop: MysteryShop = Field(default_factory=MysteryShop)
    duel: Duel = Field(default_factory=Duel)
    netherworld: Netherworld = Field(default_factory=Netherworld)
    collective_missions: CollectiveMissions = Field(default_factory=CollectiveMissions)
    hunt: Hunt = Field(default_factory=Hunt)
    dokan: Dokan = Field(default_factory=Dokan)
    abyss_shadows: AbyssShadows = Field(default_factory=AbyssShadows)
    demon_retreat: DemonRetreat = Field(default_factory=DemonRetreat)
    guild_banquet: GuildBanquet = Field(default_factory=GuildBanquet)

    def __init__(self, config_name: str=None, **data) -> None:
        """

        :param config_name:
        """
        if data:
            data = self._migrate_renamed_tasks(data)
            if config_name:
                data["config_name"] = config_name
            super().__init__(**data)
            return
        if not config_name:
            super().__init__()
            return
        data = self._migrate_renamed_tasks(self.read_json(config_name))
        data["config_name"] = config_name
        super().__init__(**data)

    @staticmethod
    def _migrate_renamed_tasks(data: dict) -> dict:
        """Accept the open core's old shop name without rewriting upstream tasks."""
        data = dict(data)
        if 'weekly_purchase' in data and 'rich_man' not in data:
            data['rich_man'] = data.pop('weekly_purchase')
        if data.get('running_task') == 'WeeklyPurchase':
            data['running_task'] = 'RichMan'
        return data

    def __setattr__(self, key, value):
        """
        只要修改属性就会触发这个函数 自动保存
        :param key:
        :param value:
        :return:
        """
        super().__setattr__(key, value)
        logger.info("auto save config")
        self.save()

    @staticmethod
    def read_json(config_name: str) -> dict:
        """
        读文件 没有额外操作
        :param config_name:  不带后缀
        :return:
        """
        filepath = Path.cwd() / "config" / f"{config_name}.json"
        return read_file(filepath)

    @staticmethod
    def write_json(config_name: str, data) -> None:
        """

        :param config_name: 不带后缀
        :param data:  字典而不是字符串
        :return:
        """
        filepath = Path.cwd() / "config" / f"{config_name}.json"
        write_file(filepath, data)

    def gui_args(self, task: str) -> str:
        """
        返回提供给gui显示的参数
        :param task: 输入的是任务的名称英文 如'Script' 或者是'script'都是可以的
        :return: 返回的是pydantic给我们结构化的输出的信息, 如果不能获取就返回空的str
        """
        task = convert_to_underscore(task)
        task_gui = getattr(self, task, None)
        if task_gui is None:
            logger.warning(f'{task} is no inexistence')
            return ''

        schema2 = task_gui.schema()
        # https://github.com/pydantic/pydantic/discussions/5687
        if 'definitions' in schema2:
            if 'Scheduler' in schema2['definitions']:
                if 'properties' in schema2['definitions']['Scheduler']:
                    properties = schema2['definitions']['Scheduler']['properties']
                    if 'success_interval' in properties:
                        properties['success_interval']['type'] = 'string'
                    if 'failure_interval' in properties:
                        properties['failure_interval']['type'] = 'string'
        return json.dumps(schema2)

    def gui_task(self, task: str) -> str:
        """
        返回提供给gui显示的参数
        :param task:
        :return:
        """
        task_name = convert_to_underscore(task)
        task = getattr(self, task_name, None)
        if task is None:
            logger.warning(f'{task_name} is no inexistence')
            return ''
        return task.json()

    def save(self) -> None:
        """

        :return:
        """
        self.write_json(self.config_name, self.model_dump())

    @staticmethod
    def type(key: str) -> str:
        """
        输入模型的键值，获取这个字段对象的类型 比如输入是orochi输出是Orochi
        :param key:
        :return:
        """
        field_type: str = str(ConfigModel.__annotations__[key])
        # return field_type
        if '.' in field_type:
            classname = field_type.split('.')[-1][:-2]
            return classname
        else:
            classname = re.findall(r"'([^']*)'", field_type)[0]
            return classname

    @staticmethod
    def deep_get(obj, keys: str, default=None):
        """
        递归获取模型的值
        :param obj:
        :param keys:
        :param default:
        :return:
        """
        if not isinstance(keys, list):
            keys = keys.split('.')
        value = obj
        try:
            for key in keys:
                value = getattr(value, key)
        except AttributeError:
            return default
        return value

    @staticmethod
    def deep_set(obj, keys: str, value) -> bool:
        if not isinstance(keys, list):
            keys = keys.split('.')
        current_obj = obj
        try:
            for key in keys[:-1]:
                current_obj = getattr(current_obj, key)
            setattr(current_obj, keys[-1], value)
            return True
        except (AttributeError, KeyError):
            return False

    # ----------------------------------- fastapi -----------------------------------
    def script_task(self, task: str) -> dict:
        """

        :param task: 同gui_args函数
        :return:
        """
        task = convert_to_underscore(task)
        task = getattr(self, task, None)
        if task is None:
            logger.warning(f'{task} is no inexistence')
            return {}

        def extract_groups(sch):
            # 从schema 中提取未解析的group的数据
            # properties = properties_groups(sch)
            results = {}
            properties = {}
            for key, value in sch["properties"].items():
                if 'items' in value:
                    properties[key] = re.search(r"/([^/]+)$", value['items']['$ref']).group(1)
                else:
                    properties[key] = re.search(r"/([^/]+)$", value['$ref']).group(1)

            for key, value in properties.items():
                results[key] = sch["$defs"][value]
            return results

        def merge_value(groups, jsons, definitions) -> list[dict]:
            # 将 groups的参数，同导出的json一起合并, 用于前端显示
            result = []
            for key, value in groups["properties"].items():
                # deal with exclude 
                if key in jsons and jsons[key] == 0xABCDEF:
                    continue

                item = {}
                item["name"] = key
                item["title"] = value["title"] if "title" in value else inflection.underscore(key)
                if "description" in value:
                    item["description"] = value["description"]
                item["default"] = value["default"]
                item["value"] = jsons[key] if key in jsons else value["default"]
                item["type"] = value["type"] if "type" in value else "enum"
                if '$ref' in value:  # list
                    enum_key = re.search(r"/([^/]+)$", value['$ref']).group(1)
                    item["enumEnum"] = definitions[enum_key]["enum"]
                elif value.get('type') == 'array' and '$ref' in value.get('items', {}):
                    enum_key = re.search(r"/([^/]+)$", value['items']['$ref']).group(1)
                    enum_values = definitions.get(enum_key, {}).get('enum')
                    if enum_values:
                        item["type"] = "multi_enum"
                        item["enumEnum"] = enum_values
                # if 'allOf' in value:
                #     enum_key = re.search(r"/([^/]+)$", value['allOf'][0]['$ref']).group(1)
                #     item["enumEnum"] = definitions[enum_key]["enum"]
                result.append(item)
            return result

        schema = task.model_json_schema()
        groups = extract_groups(schema)
        groups_value = groups.copy()

        result: dict[str, list] = {}
        for key, value in task.model_dump(context={'hide': True}).items():
            if value == 0xABCDEF:
                continue
            if key not in groups:
                for group_name in groups.keys():
                    if group_name in key:
                        groups_value[key] = groups[group_name]
            result[key] = merge_value(groups_value[key], value, schema["$defs"])

        return result

    def script_set_arg(self, task: str, group: str, argument: str, value) -> bool:
        # 验证参数
        task = convert_to_underscore(task)
        group = convert_to_underscore(group)
        argument = convert_to_underscore(argument)

        # pandtic验证
        if isinstance(value, str) and len(value) == 8:
            try:
                value = datetime.strptime(value, '%H:%M:%S').time()
            except ValueError:
                pass
        if isinstance(value, str) and len(value) == 11:
            try:
                date_time = datetime.strptime(value, '%d %H:%M:%S')
                value = TimeDelta(days=date_time.day, hours=date_time.hour, minutes=date_time.minute, seconds=date_time.second)
            except ValueError:
                pass
        if isinstance(value, str) and len(value) == 19:
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        if isinstance(value, str) and value == 'true':
            value = True
        if isinstance(value, str) and value == 'false':
            value = False

        task_object = getattr(self, task, None)
        group_object = getattr(task_object, group, None)
        if group_object is None:  # deal list
            matchs = re.findall(r'\d+', group)
            index = int(matchs[-1]) - 1 if matchs else None
            task_object_list = list(dict(task_object))
            for k, v in dict(task_object).items():
                if k not in group:
                    continue
                group_object = v[index] if group_object is None else None
        argument_object = getattr(group_object, argument, None)

        if argument_object is None:
            logger.error(f'Set arg {task}.{group}.{argument}.{value} failed')
            return False

        # XXX temp implementation to enable oasx control the datetime configuration globally rather than a single task
        if task == "restart" and group == "task_config" and argument == "reset_task_datetime_enable" and value == True:
            date_time = self.restart.task_config.reset_task_datetime
            logger.info(f"reset_task_datetime={date_time}")
            self.reset_datetime_for_all_enabled_tasks(date_time)

        # 设置参数
        try:
            # 先验证再写入，防止未经校验的字符串污染多选配置。
            candidate_data = {**group_object.model_dump(), argument: value}
            orochi_settings = task == 'orochi' and group == 'next_day_orochi_config'
            if orochi_settings and argument in ('layer', 'limit_count'):
                candidate_data['plan'] = '不选择'
            candidate = group_object.model_validate(candidate_data)
            value = getattr(candidate, argument)
            setattr(group_object, argument, value)
            if orochi_settings:
                for name in ('plan', 'layer', 'limit_count'):
                    setattr(group_object, name, getattr(candidate, name))
            logger.info(f'Set arg {self.config_name}.{task}.{group}.{argument}.{value}')
            self.save()  # 我是没有想到什么方法可以使得属性改变自动保存的
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    def copy_script_task(self, task_name: str, source_task: BaseModel) -> bool:
        model_task_name = convert_to_underscore(task_name)
        try:
            setattr(self, model_task_name, source_task)
            self.save()
            logger.info(f'Copy task {model_task_name} success')
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    def copy_task_group(self, task_name: str, group_name: str, source_task: BaseModel) -> bool:
        model_task_name = convert_to_underscore(task_name)
        model_group_name = convert_to_underscore(group_name)
        task_object = getattr(self, model_task_name, None)
        if not task_object:
            return False
        source_group_obj = getattr(source_task, model_group_name, None)
        if not source_group_obj:
            return False
        try:
            setattr(task_object, model_group_name, source_group_obj)
            self.save()
            logger.info(f'Copy task group {model_task_name}.{model_group_name} success')
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    def replace_next_run(self, d, dt: datetime):
        for k, v in d.items():
            if isinstance(v, dict):
                self.replace_next_run(v, dt=dt)
            elif k == "next_run":
                d[k] = dt
                # convert value to datetime if it's a str
                if isinstance(v, str):
                    current_time = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    if current_time != dt:
                        d[k] = dt.strftime("%Y-%m-%d %H:%M:%S")
                # already a datetime value
                elif isinstance(v, datetime) and v != dt:
                    d[k] = dt.strftime("%Y-%m-%d %H:%M:%S")

    def reset_datetime_for_all_enabled_tasks(self, task_datetime: datetime):
        logger.warn(f"trying to reset datetime of all tasks to: {task_datetime}")
        # logger.info(f"current config: {self.dict()}")
        data = self.dict()
        self.replace_next_run(data, task_datetime)
        # logger.info(f"new config: {data}")

        # write to json config  file
        self.write_json(self.config_name, data)

        # reload from the newly modified json config file
        data = self.read_json(self.config_name)
        super().__init__(**data)


if __name__ == "__main__":
    try:
        c = ConfigModel("oas1")
    except ValidationError as e:
        print(e)
        c = ConfigModel()

    print(c.script_task('GuildBanquet'))
