# This Python file uses the following encoding: utf-8
# @author AzurTian
import time
import numpy as np
from cached_property import cached_property
from datetime import timedelta, datetime
from module.atom.gif import RuleGif
from module.atom.image import RuleImage
from module.base.timer import Timer

from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.ReplaceShikigami.replace_shikigami import ReplaceShikigami
from tasks.Exploration.assets import ExplorationAssets
from tasks.Exploration.config import UpType, ExplorationLevel, AutoRotate, UserStatus, Exploration
from tasks.Component.GeneralBattle.general_battle import GeneralBattle, ExitMatcher, BattleContext, BattleAction
from tasks.GameUi.game_ui import GameUi
from tasks.Utils.config_enum import ShikigamiClass
import tasks.Exploration.page as pages

from module.logger import logger
from module.exception import TaskEnd, GameStuckError
from module.atom.animate import RuleAnimate
from typing import Optional

# 候补式神按稀有度依次尝试的顺序（新版 UI 中满级式神不能作为候补，
# 只盯一个稀有度极易全部被拒，因此逐类尝试）
ALTERNATE_CLASS_PRIORITY = (ShikigamiClass.MATERIAL, ShikigamiClass.N, ShikigamiClass.R,
                            ShikigamiClass.SR, ShikigamiClass.SSR, ShikigamiClass.SP)
# 候补上限为 50，填到该数量即认为足够（沿用原阈值）
ALTERNATE_ENOUGH = 40
# 同一稀有度连续多轮一个都没上成，即认为该类无可用式神，换下一类
ALTERNATE_STALL_LIMIT = 2


class BaseExploration(GameUi, GeneralBattle, GeneralRoom, GeneralInvite, ReplaceShikigami, SwitchSoul, ExplorationAssets):
    fire_monster_type: str = ''
    need_exit: bool = False
    user_status: UserStatus = UserStatus.ALONE
    wait_start_time: datetime = datetime.now()
    pre_page: pages.Page = None

    def _exit_matcher(self) -> ExitMatcher:
        return pages.any_of(self.I_E_SETTINGS_BUTTON, self.I_E_AUTO_ROTATE_ON, self.I_E_AUTO_ROTATE_OFF)

    @cached_property
    def _config(self) -> Exploration:
        self.config.exploration.general_battle_config.lock_team_enable = True
        limit_time = self.config.exploration.exploration_config.limit_time
        self.limit_time: timedelta = timedelta(
            hours=limit_time.hour,
            minutes=limit_time.minute,
            seconds=limit_time.second
        )
        return self.config.model.exploration

    @cached_property
    def _match_end(self):
        return RuleAnimate(self.I_SWIPE_END)

    def pre_process(self):
        if self._config.switch_soul_config.enable:
            self.goto_page(pages.page_shikigami_records)
            self.run_switch_soul(self._config.switch_soul_config.switch_group_team)

        if self._config.switch_soul_config.enable_switch_by_name:
            self.goto_page(pages.page_shikigami_records)
            self.run_switch_soul_by_name(self._config.switch_soul_config.group_name,
                                         self._config.switch_soul_config.team_name)
        # 开启加成
        con = self.config.exploration.exploration_config
        if con.buff_gold_50_click or con.buff_gold_100_click or con.buff_exp_50_click or con.buff_exp_100_click:
            self.goto_page(pages.page_main)
            self.open_buff()
            if con.buff_gold_50_click:
                self.gold_50()
            if con.buff_gold_100_click:
                self.gold_100()
            if con.buff_exp_50_click:
                self.exp_50()
            if con.buff_exp_100_click:
                self.exp_100()
            self.close_buff()
        self.user_status = self._config.exploration_config.user_status
        self.wait_start_time = datetime.now()  # 重置等待时间

    def post_process(self):
        self.goto_page(pages.page_exploration)
        con = self._config.exploration_config
        if con.buff_gold_50_click or con.buff_gold_100_click or con.buff_exp_50_click or con.buff_exp_100_click:
            self.goto_page(pages.page_main)
            self.open_buff()
            self.gold_50(is_open=False)
            self.gold_100(is_open=False)
            self.exp_50(is_open=False)
            self.exp_100(is_open=False)
            self.close_buff()
        self.set_next_run(task='Exploration', success=True, finish=False)
        raise TaskEnd

    def ensure_mainline_tab(self):
        """确保探索大地图停在「主线」tab。

        大地图常驻「主线/玩法」两个 tab，并且会记住上次停留的那一个
        （实测：切成玩法后退出探索再进来，仍落在玩法 tab）。
        选关依赖主线 tab 右侧的章节列表；若停在玩法 tab，右侧是御魂/今日掉落等模块，
        O_E_EXPLORATION_LEVEL_NUMBER 取不到任何章节名，滑屏分支也不会执行，
        只会空转累计到 25 次后抛 GameStuckError。
        """
        if self.appear(self.I_E_CHECK_MAIN_TITLE):
            return
        logger.info('Exploration map is on gameplay tab, switch back to mainline tab')
        self.click(self.C_CLICK_MAIN_TITLE)
        self.wait_until_appear(self.I_E_CHECK_MAIN_TITLE, wait_time=3)

    # 打开指定的章节：
    def open_expect_level(self):
        self.ensure_mainline_tab()
        swipeCount = 0
        config_exploration_level = self.config.exploration.exploration_config.exploration_level
        while True:
            # 判断有无目标章节
            self.screenshot()
            # 获取当前章节名
            results = self.O_E_EXPLORATION_LEVEL_NUMBER.detect_and_ocr(self.device.image)
            text1 = [result.ocr_text for result in results]
            exp_level_enum_list = []
            for txt in text1:
                try:
                    exp_level_enum_list.append(ExplorationLevel(txt))
                except ValueError as e:
                    logger.warning(f'convert {txt} failed')
            sorted(exp_level_enum_list, key=lambda x: x.get_index())  # Sort by index
            # 判断当前章节有无目标章节
            result = set(text1).intersection({config_exploration_level})
            # 有则跳出检测
            if self.appear(self.I_E_EXPLORATION_CLICK) or result and len(result) > 0:
                break
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear_then_click(self.I_UI_CONFIRM_SAMLL, interval=1):
                continue
            self.device.click_record_clear()
            if len(exp_level_enum_list) > 0:
                min_level = exp_level_enum_list[0]
                max_level = exp_level_enum_list[-1]
                if config_exploration_level.get_index() < min_level.get_index():
                    self.swipe(self.S_SWIPE_LEVEL_UP)
                elif config_exploration_level.get_index() > max_level.get_index():
                    self.swipe(self.S_SWIPE_LEVEL_DOWN)
            swipeCount += 1
            debug_info = f"Swiped {swipeCount} times, current exploration level: {text1}"
            logger.info(debug_info)
            if swipeCount >= 25:
                raise GameStuckError(
                    f"Swiped too many times ({swipeCount}), seems stuck in exploration level selection"
                )
            time.sleep(1)

        # 选中对应章节
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear_then_click(self.I_UI_CONFIRM_SAMLL, interval=1):
                continue
            self.O_E_EXPLORATION_LEVEL_NUMBER.keyword = config_exploration_level
            if self.ocr_appear_click(self.O_E_EXPLORATION_LEVEL_NUMBER):
                self.wait_until_appear(self.I_E_EXPLORATION_CLICK, wait_time=3)
            if self.appear(self.I_E_EXPLORATION_CLICK):
                break
            if self.is_in_room():
                break

        return True

    def _alternate_badges(self) -> tuple:
        """自动轮换阵容界面左下角「当前稀有度」徽标（全部 + 各稀有度）"""
        return (self.I_RS_ALL_SELECTED, self.I_RS_MATERIAL_SELECTED, self.I_RS_N_SELECTED,
                self.I_RS_R_SELECTED, self.I_RS_SR_SELECTED, self.I_RS_SSR_SELECTED,
                self.I_RS_SP_SELECTED)

    def _alternate_class_rules(self) -> dict:
        """稀有度 → (扇形菜单里的可点条目, 选中态徽标)"""
        return {
            ShikigamiClass.MATERIAL: (self.I_RS_MATERIAL, self.I_RS_MATERIAL_SELECTED),
            ShikigamiClass.N: (self.I_RS_N, self.I_RS_N_SELECTED),
            ShikigamiClass.R: (self.I_RS_R, self.I_RS_R_SELECTED),
            ShikigamiClass.SR: (self.I_RS_SR, self.I_RS_SR_SELECTED),
            ShikigamiClass.SSR: (self.I_RS_SSR, self.I_RS_SSR_SELECTED),
            ShikigamiClass.SP: (self.I_RS_SP, self.I_RS_SP_SELECTED),
        }

    def alternate_panel_opened(self) -> bool:
        """自动轮换阵容界面是否已打开（以左下角稀有度徽标为判据）

        不用 I_E_OPEN_SETTINGS：该锚点在新版 UI 上得分约 0.79，紧贴 0.8 阈值，会抖动。
        """
        self.screenshot()
        return any(self.appear(badge) for badge in self._alternate_badges())

    def switch_alternate_class(self, shikigami_class: ShikigamiClass) -> bool:
        """切换到指定稀有度（带超时；共享组件的 switch_shikigami_class 在
        「当前徽标不是『全部』」时会一直等『全部』徽标而卡死，故此处自行实现）"""
        check_click, check_selected = self._alternate_class_rules()[shikigami_class]
        timer = Timer(15).start()
        while not timer.reached():
            self.screenshot()
            if self.appear(check_selected, interval=1):
                return True
            # 扇形菜单已展开：直接点目标稀有度
            if self.appear_then_click(check_click, interval=1):
                continue
            # 未展开：点任意一个当前徽标即可弹出扇形菜单
            for badge in self._alternate_badges():
                if self.appear_then_click(badge, interval=1):
                    break
        logger.warning(f'Switch alternate class {shikigami_class} timeout')
        return False

    def read_alternate_count(self) -> int:
        """读取候补出战数量（自动轮换阵容界面右上角的「数量 X/50」）"""
        cur, _, _ = self.O_E_ALTERNATE_NUMBER.ocr(self.device.image)
        return cur

    def fill_shikigami(self):
        """填充候补式神(最后回到探索主界面)

        新版 UI 里满级式神不能作为候补（游戏会提示「该式神经验已满」），
        所以不能只盯一个稀有度：按 素材→N→R→SR→SSR→SP 依次尝试，
        某一稀有度连续多轮一张都上不了就换下一类；
        所有类别都上不了时只告警并跳过填充，不再让整个任务失败。
        """
        # 必须先点候补出战区域，否则后续在列表里选卡不会生效
        self.click(self.C_CLICK_STANDBY_TEAM)
        timer = Timer(6).start()
        while not timer.reached() and not self.alternate_panel_opened():
            time.sleep(0.5)
        if not self.alternate_panel_opened():
            logger.warning('Opening alternate shikigami panel failed')
            return

        self.screenshot()
        total = self.read_alternate_count()
        if total >= ALTERNATE_ENOUGH:
            logger.info('Alternate number is enough')
            self.goto_page(pages.page_exp_main)
            return

        slots = (self.L_ROTATE_1, self.L_ROTATE_2, self.L_ROTATE_3, self.L_ROTATE_4)
        for shikigami_class in ALTERNATE_CLASS_PRIORITY:
            if total >= ALTERNATE_ENOUGH:
                break
            self.switch_alternate_class(shikigami_class)  # 切换式神类别
            stall = 0
            while stall < ALTERNATE_STALL_LIMIT and total < ALTERNATE_ENOUGH:
                progressed = False
                for slot in slots:
                    self.click(slot)  # 长按式神上候补（会把该式神的重复副本一起上）
                    self.screenshot()
                    current = self.read_alternate_count()
                    if current > total:
                        logger.info(f'Alternate +{current - total} by {shikigami_class}, current: {current}')
                        total = current
                        progressed = True
                        break
                if progressed:
                    stall = 0
                else:
                    # 该类当前可见的式神一张都上不了（多半都是满级），换下一个稀有度
                    stall += 1
            logger.info(f'Alternate class {shikigami_class} finished, current: {total}')

        if total == 0:
            logger.warning('No alternate shikigami could be placed (all candidates are max level?), skip filling')
        self.goto_page(pages.page_exp_main)

    # 找up按钮
    def search_up_fight(self, up_type: UpType = None) -> Optional[RuleImage | RuleGif]:
        up_type = self._config.exploration_config.up_type if up_type is None else up_type
        if up_type == UpType.ALL and self.appear(self.I_NORMAL_BATTLE_BUTTON):
            return self.I_NORMAL_BATTLE_BUTTON
        match up_type:
            case UpType.EXP:
                find_flag = self.I_UP_EXP
            case UpType.COIN:
                find_flag = self.I_UP_COIN
            case UpType.DARUMAA:
                find_flag = self.I_UP_DARUMA
            case _:
                find_flag = self.I_UP_EXP
        appear = self.appear(find_flag)
        if not appear:
            return None
        # logger.info(f'Found up type: {up_type} at  {find_flag.roi_front}')
        x, y, _, _ = find_flag.roi_front
        x_center, y_center = find_flag.front_center()
        roi_back_y = max(0, y - 300)
        roi_back_h = y - 20 - roi_back_y
        roi_back_x = max(0, x - 160)
        roi_back_w = min(1280, x + 200) - roi_back_x
        # self.I_NORMAL_BATTLE_BUTTON.roi_back = [roi_back_x, roi_back_y, roi_back_w, roi_back_h]
        # logger.info(f'It will search normal battle button at {roi_back_x, roi_back_y, roi_back_w, roi_back_h}')
        matches = self.I_NORMAL_BATTLE_BUTTON.match_all(
            image=self.device.image,
            threshold=0.9,
            roi=[roi_back_x, roi_back_y, roi_back_w, roi_back_h],
            frame_id=self.device.image_frame_id,
        )
        if not matches:
            return None
        distances = []
        for match in matches:
            x_match, y_match = match[1], match[2]
            distance = np.linalg.norm(
                np.array([x_center, y_center]) - np.array([x_match, y_match])
            )
            distances.append((distance, match))
        distances.sort(key=lambda x: x[0], reverse=False)
        match = distances[0][1]
        roi_front = list(match[1:])  # x,y,w,h
        self.I_NORMAL_BATTLE_BUTTON.roi_front = roi_front
        # logger.info(f"Found normal battle button at {roi_front}")
        self.fire_monster_type = 'normal'
        return self.I_NORMAL_BATTLE_BUTTON

    def activate_realm_raid(self, con_scrolls, con, current_page: pages.Page | None) -> None:
        # 判断是否开启突破票检测
        if not con_scrolls.scrolls_enable or current_page is None or \
                current_page not in (pages.page_exploration, pages.page_exp_entrance):
            return
        if current_page == pages.page_exp_entrance:
            cu, res, total = self.O_REALM_RAID_NUMBER1.ocr(self.device.image)
        else:
            cu, res, total = self.O_REALM_RAID_NUMBER.ocr(self.device.image)
        # 判断突破票数量
        if cu < con_scrolls.scrolls_threshold:
            return
        # 关闭加成
        if con.buff_gold_50_click or con.buff_gold_100_click or con.buff_exp_50_click or con.buff_exp_100_click:
            self.goto_page(pages.page_main)
            self.open_buff()
            self.gold_50(is_open=False)
            self.gold_100(is_open=False)
            self.exp_50(is_open=False)
            self.exp_100(is_open=False)
            self.close_buff()
        # 设置下次执行行时间
        logger.info("RealmRaid and Exploration  set_next_run !")
        next_run = datetime.now() + con_scrolls.scrolls_cd
        self.goto_page(pages.page_exploration)
        self.set_next_run(task='Exploration', success=False, finish=False, target=next_run)
        self.set_next_run(task='RealmRaid', success=False, finish=False, server=False, target=datetime.now())
        self.set_next_run(task='MemoryScrolls', success=False, finish=False, target=datetime.now())
        raise TaskEnd

    def check_exit(self, current_page: pages.Page | None) -> bool:
        # True 表示要退出这个任务
        if self.current_count >= self._config.exploration_config.minions_cnt:
            logger.info('Minions count is enough, exit')
            return True
        if datetime.now() - self.start_time >= self.limit_time:
            logger.info('Exploration time limit out, exit')
            return True
        if self.user_status == UserStatus.MEMBER and \
                datetime.now() - self.wait_start_time >= self._config.invite_config.wait_time_v:
            logger.info('Member wait time out, exit')
            return True
        self.activate_realm_raid(self._config.scrolls, self._config.exploration_config, current_page)
        return False

    def fire(self, button) -> bool:
        """进入战斗(True:成功进入战斗/识别到退出弹窗, 否则False)
        这里之所以违反页面特性使用循环, 是因为由于怪物移动的原因可能导致一次点击会无法进入战斗,
        回到外循环之后由于UP旋转的特性可能导致识别不到怪物然后开始滑动, 导致错过的怪物更多
        因此这里使用贪心的思想, 只要识别到怪物一次就尽最大可能直接进入战斗, 保证尽可能有怪则打
        """
        max_tries = 4
        timeout_timer = Timer(10).start()  # 增加最大时间限制, 防止因未知因素引起无限等待
        while max_tries > 0 and not timeout_timer.reached():
            self.screenshot()
            cur_page = self.get_current_page()
            # 退出动画期间可能再次识别到怪物开始攻击, 因此取消退出
            if cur_page == pages.page_exp_exit:
                self.need_exit = False
                return True
            if cur_page in (pages.page_battle_prepare, pages.page_battle):
                return True
            if self.appear_then_click(button, interval=0.8):
                max_tries -= 1
                continue
        return False

    def switch_rotate(self) -> bool:
        """切换轮换类型并添加式神 True(执行了切换)/False"""
        match self._config.exploration_config.auto_rotate:
            case AutoRotate.yes:
                if self.appear(self.I_E_AUTO_ROTATE_OFF):  # 轮换关闭/式神不够了则需要打开并添加式神
                    self.click(self.C_CLICK_SETTINGS, interval=2)
                    return True
            case AutoRotate.no:  # 不是自动添加候补式神则关闭轮换
                if self.appear_then_click(self.I_E_AUTO_ROTATE_ON, interval=0.8):
                    return True
        return False

    def arrive_end(self) -> bool:
        """是否到达探索的最后方, 需要先调用截图(滑动超过6次直接判定已经到达底部)"""
        if self.device.click_record.count(self.S_SWIPE_BACKGROUND_RIGHT.name) >= 6:
            self.device.click_record_clear()
            return True
        return self._match_end.stable(self.device.image, refresh_after_stable=True, frame_id=self.device.image_frame_id)

    def get_fire_button(self) -> Optional[RuleImage | RuleGif]:
        """获取需要攻击的按钮"""
        if self.appear(self.I_BOSS_BATTLE_BUTTON):
            self.fire_monster_type = 'boss'
            return self.I_BOSS_BATTLE_BUTTON
        return self.search_up_fight()

    def collect_treasure_box(self) -> bool:
        """收集宝箱奖励"""
        if self.appear(self.I_E_REWARD_BOX_SMALL):  # 小宝箱
            logger.info('Treasure box small appear, get it.')
            self.ui_click(self.I_E_REWARD_BOX_SMALL, self.I_REWARD, interval=0.8)
            self.ui_click_until_disappear(self.I_REWARD, interval=0.8)
            return True
        if self.appear(self.I_E_REWARD_BOX_BIG):  # 大宝箱
            logger.info('Treasure box big appear, get it.')
            self.ui_click(self.I_E_REWARD_BOX_BIG, self.I_REWARD, interval=0.8)
            self.ui_click_until_disappear(self.I_REWARD, interval=0.8)
            return True
        return False

    def collect_paper_man_reward(self) -> bool:
        """收集小纸人奖励, 若未开启则自动退出"""
        # 已经打过boss了且设置了不收集小纸人奖励则直接返回
        if self.fire_monster_type == 'boss' and not self._config.exploration_config.collect_paper_reward:
            logger.info("Not collect paper doll reward")
            self.quit_exp_main()
            return True
        # 没打boss或者收集纸人奖励, 且出现了纸人则处理掉落奖励
        if self.appear(self.I_BATTLE_REWARD) and self._config.exploration_config.collect_paper_reward:
            self.ui_get_reward(self.I_BATTLE_REWARD)
            self.wait_start_time = datetime.now()  # 队友等待时间重置
            return True
        return False

    def quit_exp_main(self):
        """退出探索主界面(要求当前必须处于探索主界面, 不保证任何后续结果)"""
        self.need_exit = True
        self.appear_then_click(self.I_UI_BACK_YELLOW, interval=0.8)
        self.wait_start_time = datetime.now()  # 队友等待时间重置

    def collect_reward(self) -> bool:
        """处理掉落奖励(True表示进行了操作, False表示没有操作)"""
        return self.collect_treasure_box() or self.collect_paper_man_reward()

    def enter_team(self) -> bool:
        """进入战斗组队页面"""
        return self.create_room(self.I_EXP_CREATE_TEAM) and self.ensure_private() and self.create_ensure()

if __name__ == "__main__":
    from module.config.config import Config
    from module.device.device import Device

    config = Config('绘卷oas2')
    device = Device(config)
    t = BaseExploration(config, device)
    t.screenshot()
    t.fill_shikigami()
