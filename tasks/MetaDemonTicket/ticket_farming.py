# This Python file uses the following encoding: utf-8
"""超鬼王门票刷取，复用觉醒和探索的战斗流程。"""
from datetime import datetime
from cached_property import cached_property

from module.logger import logger
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.EvoZone.config import EvoZone, EvoZoneConfig, UserStatus as AwakeUserStatus
from tasks.EvoZone.script_task import ScriptTask as AwakeTask
from tasks.Exploration.config import (
    AutoRotate, Exploration, ExplorationConfig, ExplorationLevel,
    UpType, UserStatus as ExplorationUserStatus,
)
from tasks.Exploration.script_task import ScriptTask as ExplorationTask
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.default_pages import page_reward
import tasks.GameUi.page as pages
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemonTicket.config import TicketMode, ExplorationTarget


class TicketsFull(Exception):
    """达到单刷或协同满票目标，停止开启下一场战斗。"""


class TicketConfigProxy:
    """把超鬼王门票配置映射成复用流程读取的独立任务配置。

    觉醒与探索的流程代码读的是 ``config.evo_zone`` / ``config.exploration``，
    这里只覆盖对应的字段，其余（global_game 等）继续回落到真实配置。
    """

    def __init__(self, config, attr: str, task_config) -> None:
        self._config = config
        self._attr = attr
        self._task_config = task_config

    def __getattr__(self, name):
        if name == self._attr:
            return self._task_config
        return getattr(self._config, name)


def metademon_tickets_full(task) -> bool:
    """读取当前奖励截图的门票/上限；无有效上限时不判满。"""
    # I_REWARD is the red-daruma settlement image; I_UI_REWARD is the
    # separate "获得奖励" banner and does not identify this battle reward screen.
    if not task.appear(GeneralBattleAssets.I_REWARD):
        return False
    current, remaining, total = GeneralBattleAssets.O_METADEMON_PASS.ocr_digit_counter(task.device.image)
    if total <= 0 or current < 0:
        logger.warning('超鬼王门票 OCR 未识别到有效计数')
        return False
    logger.info(f'超鬼王门票: {current}/{total}')
    return current >= total


class TicketRewardMixin:
    def check_ticket_reward(self):
        if getattr(self, '_ticket_farming_complete', False) or getattr(self, '_ticket_full', False):
            return
        if metademon_tickets_full(self):
            logger.info('门票已满')
            raise TicketsFull

    def _handle_reward(self, context, config):
        self.check_ticket_reward()
        return super()._handle_reward(context, config)

    def install_ticket_reward_hook(self):
        reward = self.navigator.resolve_page(page_reward)
        if reward is None:
            return
        # 导航进入奖励页时也必须先 OCR，再执行原来的结算点击。
        reward.on_enter_success.insert(0, lambda task: task.check_ticket_reward())


class AwakeTicketTask(TicketRewardMixin, AwakeTask):
    @cached_property
    def _config(self):
        return ticket_farming_config(self.config.meta_demon_ticket, TicketMode.AWAKE)

    def _infer_task_category(self):
        return 'evo_zone'


class ExplorationTicketTask(TicketRewardMixin, ExplorationTask):
    @cached_property
    def _config(self):
        return ticket_farming_config(self.config.meta_demon_ticket, TicketMode.EXPLORATION)

    def _infer_task_category(self):
        return 'exploration'

    @property
    def exp_page_handle_dict(self):
        handlers = super().exp_page_handle_dict
        original = handlers[page_reward]

        def reward():
            self.check_ticket_reward()
            return original()

        handlers[page_reward] = reward
        return handlers


def ticket_farming_config(meta, mode):
    """仅把超鬼王专用字段适配为复用流程需要的设置，不读取独立任务配置。"""
    common = meta.general_config
    soul = meta.switch_soul_config.model_copy()
    battle = meta.general_battle_config
    if mode == TicketMode.AWAKE:
        return EvoZone(
            evo_zone_config=EvoZoneConfig(user_status=AwakeUserStatus(common.user_status.value),
                layer=common.awake_layer, kirin_type=common.awake_kirin_type,
                limit_time=common.limit_time, limit_count=2 ** 31 - 1,
                soul_buff_enable=common.awake_buff_enable),
            switch_soul_config=soul, general_battle_config=battle, invite_config=meta.invite_config)
    if mode == TicketMode.EXPLORATION:
        target = {ExplorationTarget.ALL: UpType.ALL, ExplorationTarget.COIN: UpType.COIN,
                  ExplorationTarget.EXP: UpType.EXP, ExplorationTarget.DARUMA: UpType.DARUMAA}
        if common.exploration_rotate and battle.lock_team_enable:
            battle = battle.model_copy(update={'lock_team_enable': False})
        return Exploration(
            exploration_config=ExplorationConfig(user_status=ExplorationUserStatus(common.user_status.value),
                exploration_level=ExplorationLevel.EXPLORATION_28,
                limit_time=common.limit_time, minions_cnt=2 ** 31 - 1,
                auto_rotate=AutoRotate.yes if common.exploration_rotate else AutoRotate.no,
                up_type=target[common.exploration_target]),
            switch_soul_config=soul, general_battle_config=battle, invite_config=meta.invite_config)
    raise ValueError(f'未知门票刷取模式: {mode}')


def tickets_full_before_farming(owner) -> bool:
    """Check the courtyard's exploration landing page before any farming setup."""
    owner.goto_page(pages.page_exploration)
    for _ in range(3):
        owner.screenshot()
        if not owner.appear(GameUiAssets.I_CHECK_EXPLORATION):
            continue
        current, _, total = MetaDemonAssets.O_MD_TICKET.ocr_digit_counter(owner.device.image)
        if current >= 0 and total > 0:
            logger.info(f'门票刷取前检测: {current}/{total}')
            return current >= total
    logger.warning('探索入口未识别到有效超鬼王门票计数，继续刷取并由奖励页检测满票')
    return False


def run_ticket_farming(owner, mode) -> bool:
    """共享运行环境；御魂和战斗参数直接使用超鬼王门票刷取配置。"""
    if mode not in (TicketMode.AWAKE, TicketMode.EXPLORATION):
        raise ValueError(f'未知门票刷取模式: {mode}')
    config = owner.config
    meta = config.meta_demon_ticket
    if tickets_full_before_farming(owner):
        logger.info('超鬼王门票已满，跳过门票刷取')
        return True
    role = meta.general_config.user_status
    limit_time = meta.general_config.limit_time_v
    if mode == TicketMode.AWAKE:
        runner = AwakeTicketTask(config, owner.device)
        runner.config = TicketConfigProxy(config, 'evo_zone', ticket_farming_config(meta, mode))
    else:
        runner = ExplorationTicketTask(config, owner.device)
        runner.config = TicketConfigProxy(config, 'exploration', ticket_farming_config(meta, mode))
    runner.start_time = datetime.now()
    runner.current_count = 0
    runner.limit_count = 2 ** 31 - 1
    runner._ticket_farming_complete = False
    runner._ticket_full = False
    runner.install_ticket_reward_hook()
    buff_opened = False
    result = False
    try:
        if mode == TicketMode.AWAKE:
            soul = meta.switch_soul_config
            if soul.enable or soul.enable_switch_by_name:
                runner.goto_page(pages.page_shikigami_records)
                if soul.enable_switch_by_name:
                    runner.run_switch_soul_by_name(soul.group_name, soul.team_name)
                else:
                    runner.run_switch_soul(soul.switch_group_team)
            if meta.general_config.awake_buff_enable:
                runner.goto_page(pages.page_main)
                runner.open_buff()
                runner.awake(is_open=True)
                buff_opened = True
                runner.close_buff()
            runner.limit_time = limit_time
            if role == ExplorationUserStatus.LEADER:
                runner.run_leader()
            elif role == ExplorationUserStatus.MEMBER:
                runner.run_member()
            else:
                runner.run_alone()
        else:
            runner.pre_process()
            runner.limit_time = limit_time
            runner.exec_exp_page()
    except TicketsFull:
        result = True
        logger.info('门票已满，结束门票刷取')
    finally:
        runner._ticket_farming_complete = True
        if role != ExplorationUserStatus.ALONE or buff_opened:
            runner.goto_page(pages.page_main)
        if buff_opened:
            runner.open_buff()
            runner.awake(is_open=False)
            runner.close_buff()
    return result
