# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time
import copy
import cv2
import numpy as np
import tasks.MetaDemon.inner_page as ipages
from datetime import datetime
from types import SimpleNamespace
from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.atom.swipe import RuleSwipe
from module.base.timer import Timer
from module.exception import TaskEnd, GameStuckError
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemon.config import MetaDemon, BossType


_BOSS_NAME_CN = {
    BossType.ONE_STAR: '1星鬼王',
    BossType.TWO_STARS: '2星鬼王',
    BossType.THREE_STARS: '3星鬼王',
    BossType.FOUR_STARS: '4星鬼王',
    BossType.FIVE_STARS: '5星鬼王',
    BossType.SIX_STARS: '6星鬼王',
    BossType.MONEY: '氪金猪',
}


def boss_name_cn(boss_type: BossType | None) -> str:
    """BossType -> 日志用中文名, 未知/None 有兜底。"""
    if boss_type is None:
        return '未知鬼王'
    return _BOSS_NAME_CN.get(boss_type, boss_type.name)


class ScriptTask(GeneralBattle, SwitchSoul, GameUi, MetaDemonAssets):
    """超鬼王"""

    conf: MetaDemon = None
    cur_boss_type: BossType = None
    cur_boss_name: str = ''
    total_count: int = 0

    @property
    def enable_powerful_fire(self):
        powerful_list = self.conf.meta_demon_config.powerful_list_v
        return self.cur_boss_type is not None and self.cur_boss_type in powerful_list

    def before_run(self):
        self.State = SimpleNamespace(done=False, switch_soul_done=False, preset_switch_done=False, synthesis_done=False)
        self.total_count = self.current_count = 0
        self.cur_boss_type = None
        self.cur_boss_name = ''
        self._applied_preset = None
        self.ui_close = [*self.ui_close, self.I_MD_GET_YESTERDAY_REWARD]
        self.conf = self.config.meta_demon
        self.limit_time = self.conf.meta_demon_config.limit_time_v
        self.limit_count = self.conf.meta_demon_config.limit_count
        self._navigation_snapshot = [
            (page, {dest: list(buttons) for dest, buttons in page.links.items()})
            for page in (ipages.page_main, ipages.page_shikigami_records,
                         ipages.page_meta_demon_boss)]
        # 更改式神录跳转
        ipages.page_shikigami_records.links.clear()
        ipages.page_shikigami_records.link(button=self.I_BACK_YELLOW, destination=ipages.page_meta_demon_boss)
        ipages.page_meta_demon_boss.link(button=MetaDemonAssets.I_MD_SHIKIGAMI, destination=ipages.page_shikigami_records)
        ipages.page_main.links.pop(ipages.page_shikigami_records, None)

    def run(self):
        original_close = self.ui_close
        try:
            self.before_run()
            while True:
                self.update_global_state()
                if self.State.done:
                    break
                if self._enter_boss_page():
                    if not self.State.synthesis_done:
                        self.check_and_synthesize()
                        self.State.synthesis_done = True
                    if self.check_and_prepare_battle():
                        self.start_battle()
            self.set_next_run(task="MetaDemon", success=True)
            self.finish_task()
        finally:
            self._restore_navigation()
            self.ui_close = original_close

    def _restore_navigation(self):
        for page, links in self.__dict__.pop('_navigation_snapshot', []):
            page.links.clear()
            page.links.update(links)

    def _boss_page_visible(self):
        return self.appear(ipages.page_meta_demon_boss.check_button)

    def _enter_boss_page(self):
        """Use the current event entry without adding it to global navigation."""
        logger.info('开始进入超鬼王挑战界面')
        timeout = Timer(60).start()
        recovered = False
        while not timeout.reached():
            self.screenshot()
            if self.is_in_battle(False):
                self._fight_current_boss()
                return False
            if self._boss_page_visible():
                self.ui_current = ipages.page_meta_demon_boss
                return True
            if self.appear_then_click(self.I_MD_GET_YESTERDAY_REWARD, interval=1):
                continue
            if self.ui_reward_appear_click():
                continue
            if self.appear_then_click(self.I_MD_CHECK_MAIN_PAGE, interval=1):
                continue
            if self.appear_then_click(self.I_MD_CHECK_MAIN_PAGE_2, interval=1):
                continue
            if self.appear_then_click(self.I_MD_ENTRY, interval=1.5):
                continue
            if self.appear(self.I_CHECK_ACT_LIST_METADEMON_ACT):
                self.appear_then_click(self.I_ACT_LIST_GOTO_ACT, interval=1)
                continue
            if self.appear(self.I_MD_CURRENT_ENTER):
                self.appear_then_click(self.I_MD_CURRENT_ENTER, interval=1.5)
                continue
            if self.appear(self.I_MD_CURRENT_ENTRY):
                self.appear_then_click(self.I_MD_CURRENT_ENTRY, interval=1.5)
                continue
            if not recovered and not self.appear(ipages.page_main.check_button):
                recovered = True
                if not self.ui_goto_page(ipages.page_main, timeout=30):
                    raise GameStuckError('超鬼王入口准备未能返回庭院')
        raise GameStuckError('超鬼王入口等待超过60秒')

    def _fight_current_boss(self):
        self.total_count += 1
        self.run_general_battle(GeneralBattleConfig() if self.conf.preset_switch.enable else
                                self.conf.switch_soul.get_general_battle_conf(self.cur_boss_type))

    def start_battle(self):
        logger.info('准备进入超鬼王战斗')
        timeout = Timer(15).start()
        while not timeout.reached():
            self.screenshot()
            if self.is_in_battle(False):
                self._fight_current_boss()
                return
            if self.appear(self.I_MD_DRINK_TEA, interval=1.2):  # 出现喝茶弹窗
                if self.conf.meta_demon_config.auto_tea:
                    self.click(self.I_MD_DRINK_TEA)  # 喝茶
                    continue
                # 不喝茶则结束任务安排下一次运行
                self._close_boss_popup()
                self.set_next_run('MetaDemon', target=datetime.now() + self.conf.scheduler.wait_interval)
                self.finish_task()
            if self.appear_then_click(self.I_MD_FIRE, interval=0.8):
                continue
        raise GameStuckError('超鬼王进入战斗超过15秒')

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        original_markers = self.device.detect_record.copy()
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        logger.info(f"Start battle process on {self.cur_boss_type.name if self.cur_boss_type else 'None'}")
        win = False
        settled = Timer(1)
        timeout = Timer(300).start()
        try:
            while not timeout.reached():
                # Device clicks clear markers; re-add without resetting either timer.
                self.device.detect_record.add('BATTLE_STATUS_S')
                self.screenshot()
                if self.appear_then_click(self.I_WIN, interval=0.8):
                    win = True
                    settled.clear()
                    continue
                if self.appear_then_click(self.I_FALSE, interval=0.8):
                    win = False
                    settled.clear()
                    continue
                if self.ui_reward_appear_click():
                    settled.clear()
                    continue
                # Reward and transition frames are not a confirmed return to the boss.
                ready = any(self.appear(target) for target in (
                    self.I_MD_FIRE, self.I_MD_SWITCH_TICKET,
                    self.I_MD_SUMMON_BOSS, self.I_MD_CURRENT_SUMMON))
                settling = self.appear(self.I_MD_SETTLING)
                if ready and not settling and not self.is_in_battle(False):
                    if not settled.started():
                        settled.start()
                    elif settled.reached():
                        break
                else:
                    settled.clear()
                if settling:
                    logger.info('等待鬼王结算')
            else:
                raise GameStuckError('超鬼王战斗或结算超过300秒')
        finally:
            self.device.detect_record.discard('BATTLE_STATUS_S')
            self.device.detect_record.update(original_markers)
        total_run_time = datetime.now() - self.start_time
        logger.info(f'battle win: {win}')
        logger.info(f'battle count: {self.total_count}/{self.limit_count}')
        logger.info(f'time count: {total_run_time.total_seconds():.1f}s/{self.limit_time.total_seconds()}s')
        return win

    def update_global_state(self):
        if datetime.now() - self.start_time >= self.limit_time or \
                self.total_count >= self.limit_count:
            self.State.done = True

    def check_and_prepare_battle(self) -> bool:
        """检查并做战斗前的准备工作
        :return: True可以战斗, False不能战斗
        """
        logger.hr('battle prepare', 2)
        return self.check_fatigue() and self.check_and_switch_ticket() and \
            self.check_and_switch_powerful() and self.check_and_switch_preset() and self.check_and_switch_soul()

    def check_fatigue(self):
        logger.hr('Check fatigue')
        current, remain, total = self.O_MD_FATIGUE.ocr(self.device.image)
        # 不喝茶且当前疲劳度已满
        if total <= 0 or current < 0 or remain < 0 or current + remain != total:
            raise GameStuckError('超鬼王疲劳度识别失败')
        if not self.conf.meta_demon_config.auto_tea and current >= total:
            self.set_next_run('MetaDemon', target=datetime.now() + self.conf.scheduler.wait_interval)
            self.finish_task()
        return True

    def _close_boss_popup(self):
        timeout = Timer(5).start()
        while not timeout.reached():
            self.screenshot()
            if not self.appear(self.I_MD_GET_BOSS) and not self.appear(self.I_MD_DRINK_TEA) and self._boss_page_visible():
                return
            self.appear_then_click(self.I_MD_CLOSE_POPUP, interval=0.6)
        raise GameStuckError('超鬼王弹窗关闭超过5秒')

    def check_and_switch_ticket(self):
        """切换鬼王门票"""
        logger.hr('Summon boss')
        # 打开切换门票弹窗；固定总超时不随点击重置。
        timeout = Timer(15).start()
        while not timeout.reached():
            self.screenshot()
            if self.appear(self.I_MD_FIRE, interval=1.2):  # 场上已有鬼王
                self._refresh_current_boss_type(clear_on_failure=True)
                return True
            if self.appear(self.I_MD_GET_BOSS, interval=0.6):  # 打开弹窗了
                break
            if self.appear_then_click(self.I_MD_SWITCH_TICKET, interval=0.6):
                continue
            if self.appear_then_click(self.I_MD_CURRENT_SUMMON, interval=0.6):
                continue
            if self.appear_then_click(self.I_MD_SUMMON_BOSS, interval=0.6):
                continue
        else:
            raise GameStuckError('超鬼王门票面板打开超过15秒')
        type_ticket_dict: dict[BossType, RuleImage] = {
            BossType.ONE_STAR: self.I_MD_ONE_STAR,
            BossType.TWO_STARS: self.I_MD_TWO_STARS,
            BossType.THREE_STARS: self.I_MD_THREE_STARS,
            BossType.FOUR_STARS: self.I_MD_FOUR_STARS,
            BossType.FIVE_STARS: self.I_MD_FIVE_STARS,
            BossType.SIX_STARS: self.I_MD_SIX_STARS,
        }
        # 获取所有存在的鬼王门票
        can_fire_list = [boss_type for boss_type, ticket_rule_image in type_ticket_dict.items() if
                         self.appear(ticket_rule_image, threshold=0.92)]
        if len(can_fire_list) <= 0:
            self.State.done = True
            logger.info('No remain boss ticket, exit')
            self._close_boss_popup()
            return False
        # 根据存在的鬼王门票和配置的鬼王序列过滤出需要召唤的鬼王门票
        need_fire_list = [boss_type for boss_type in self.conf.meta_demon_config.fire_sequence_v if
                          boss_type in can_fire_list]
        if len(need_fire_list) <= 0:
            self.State.done = True
            logger.info('There is no boss that needs to be attacked, exit')
            self._close_boss_popup()
            return False
        # 第一次进来或上次一鬼王类型与这一次不同, 则需要切换御魂和预设
        if self.cur_boss_type is None or self.cur_boss_type != need_fire_list[0]:
            if not self.conf.switch_soul.switch_once:
                self.State.switch_soul_done = False
            self.current_count = 0
        self._reset_switch_on_star_change(need_fire_list[0])
        self.cur_boss_name = ''
        if not self.conf.preset_switch.switch_once and self.conf.preset_switch.name_map:
            self.State.preset_switch_done = False
        target_ticket_rule_image = type_ticket_dict[self.cur_boss_type]
        selected = False
        logger.info(f'Summon {self.cur_boss_type.name.lower()} boss')
        timeout = Timer(15).start()
        while not timeout.reached():
            self.screenshot()
            if self.appear(self.I_MD_FIRE):  # 召唤完成，以场上星级复核
                self._refresh_current_boss_type(clear_on_failure=False)
                return True
            if selected and self.appear(self.I_MD_CHECK_SELECTED, interval=0.6):
                actual = self._classify_selected_ticket(type_ticket_dict)
                if actual == self.cur_boss_type:
                    self.appear_then_click(self.I_MD_GET_BOSS, interval=0.6)
                    continue
                if actual is not None:
                    raise GameStuckError('超鬼王选中门票与目标星级不一致，停止召唤')
            if self.appear_then_click(target_ticket_rule_image, interval=0.6, threshold=0.92):  # 选择对应鬼王门票
                selected = True
                continue
        raise GameStuckError('超鬼王门票选择或召唤超过15秒')

    def check_and_switch_powerful(self) -> bool:
        """检查并切换是否开启强力"""
        logger.hr('process power fire')
        if not self.appear(self.I_MD_FIRE):
            self.ui_goto_page(ipages.page_meta_demon_boss)
            self.screenshot()
            if not self.appear(self.I_MD_FIRE):  # 处于boss界面但是没有挑战按钮
                return False
        powerful_list = self.conf.meta_demon_config.powerful_list_v
        # 当前boss类型未知或不在强力列表中则使用普通追击
        if self.cur_boss_type is None or self.cur_boss_type not in powerful_list:
            if not self.ui_click(self.I_MD_ENABLE_POWERFUL_FIRE, self.I_MD_DISABLE_POWERFUL_FIRE, interval=0.6, timeout=5):
                raise GameStuckError('超鬼王普通追击状态未确认')
            return True
        # 已知类型且在强力列表中则开启强力追击
        if not self.ui_click(self.I_MD_DISABLE_POWERFUL_FIRE, self.I_MD_ENABLE_POWERFUL_FIRE, interval=0.6, timeout=5):
            raise GameStuckError('超鬼王强力追击状态未确认')
        return True

    def check_and_switch_soul(self) -> bool:
        """切换御魂"""
        if self.conf.preset_switch.enable or not self.conf.switch_soul.enable or self.State.switch_soul_done:
            return True
        # An already summoned boss has no confirmed star type. Do not guess its team.
        if self.cur_boss_type is None and not self.conf.switch_soul.switch_once:
            logger.warning('当前鬼王星级未知，本场保留现有御魂')
            return True
        logger.hr('Switch soul')
        if not self.ui_goto_page(ipages.page_shikigami_records):
            raise GameStuckError('超鬼王换御魂未能进入式神录')
        if self.conf.switch_soul.switch_once:  # 只切换一次则将配置的鬼王御魂全部切换
            for boss_type in self.conf.meta_demon_config.fire_sequence_v:
                switch_type, (group, team) = self.conf.switch_soul.get_switch_by_enum(boss_type)
                if switch_type is None:
                    continue
                if switch_type == 'int':
                    self.run_switch_soul((group, team))
                if switch_type == 'str':
                    self.run_switch_soul_by_name(group, team)
            if not self.ui_goto_page(ipages.page_meta_demon_boss):
                raise GameStuckError('超鬼王换御魂后未返回挑战页')
            self.State.switch_soul_done = True
            return True
        switch_type, (group, team) = self.conf.switch_soul.get_switch_by_enum(self.cur_boss_type)
        if switch_type is None:
            raise ValueError(f'超鬼王 {self.cur_boss_type.name.lower()} 御魂方案未配置或格式错误')
        if switch_type == 'int':
            self.run_switch_soul((group, team))
        if switch_type == 'str':
            self.run_switch_soul_by_name(group, team)
        if not self.ui_goto_page(ipages.page_meta_demon_boss):
            raise GameStuckError('超鬼王换御魂后未返回挑战页')
        self.State.switch_soul_done = True
        return True

    def _refresh_current_boss_type(self, clear_on_failure: bool = False) -> BossType | None:
        """从场上“自己发现”头像识别星级，并在星级变化时重置御魂切换标记。"""
        detected = self._detect_current_boss_star()
        if detected is not None:
            name = self._detect_boss_name(self.device.image)
            old_name = getattr(self, 'cur_boss_name', '')
            self.cur_boss_name = name or ''
            if self.cur_boss_name != old_name and not self.conf.preset_switch.switch_once:
                self.State.preset_switch_done = False
            if name:
                logger.info(f'鬼王名字: {name}')
            if detected != self.cur_boss_type:
                self._reset_switch_on_star_change(detected)
            return detected
        logger.warning('无法识别当前鬼王星级')
        if clear_on_failure:
            self.cur_boss_type = None
            self.cur_boss_name = ''
            if not self.conf.preset_switch.switch_once:
                self.State.preset_switch_done = False
        return None

    def _reset_switch_on_star_change(self, new_star: BossType) -> None:
        """星级变化时更新当前鬼王并重置预设切换标记。

        new_star 为 None(识别失败, 常见于失败结算/弹窗遮挡)不做事:
        失败后应直接再挑战, 不能因识别抖动重触发切预设。
        """
        if new_star is None or new_star == self.cur_boss_type:
            return
        logger.info(f'当前鬼王: {boss_name_cn(new_star)}')
        self.cur_boss_type = new_star
        if not self.conf.preset_switch.switch_once:
            self.State.preset_switch_done = False
        if not self.conf.switch_soul.switch_once:
            self.State.switch_soul_done = False

    def _detect_current_boss_star(self) -> BossType | None:
        previous = None
        for _ in range(3):
            self.screenshot()
            image = self.device.image
            if image is None or image.shape[:2] != (720, 1280) or not self.appear(self.I_MD_FIRE):
                previous = None
                time.sleep(0.35)
                continue
            hsv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2HSV)
            lit = []
            for index in range(6):
                patch = hsv[207:215, 56 + 11 * index:64 + 11 * index]
                lit.append(float(patch[:, :, 1].mean()) > 100 and float(patch[:, :, 2].mean()) > 160)
            count = sum(lit)
            detected = BossType(count) if 1 <= count <= 6 and lit == [True] * count + [False] * (6-count) else None
            if detected is not None and detected == previous:
                return detected
            previous = detected
            time.sleep(0.35)
        return None

    def _detect_boss_name(self, image=None) -> str:
        """OCR 场上鬼王的竖排名。

        区域 O_MD_BOSS_NAME=(490,170,80,240) 覆盖到 6 字竖排名;
        名字正下方是「技能 x6」等界面标签（与名字块间隔约 60px）,
        按 y 间隔 <=20px 的连续块拼接, 首个远间隔块及其后全部丢弃。
        识别失败返回空串, 不阻塞任务。
        """
        if image is None:
            image = self.screenshot()
        results = self.O_MD_BOSS_NAME.detect_and_ocr(image)
        boxes = []
        for result in results:
            text = (result.ocr_text or '').strip()
            if not text:
                continue
            y1 = min(point[1] for point in result.box)
            y2 = max(point[1] for point in result.box)
            boxes.append((y1, y2, text))
        name = ''
        last_bottom = 0
        for y1, y2, text in sorted(boxes, key=lambda b: b[0]):
            if name and y1 - last_bottom > 20:
                break
            name += text
            last_bottom = y2
        return name

    def _classify_selected_ticket(self, type_ticket_dict) -> BossType | None:
        if not self.appear(self.I_MD_CHECK_SELECTED):
            return None
        x, y, w, h = self.I_MD_CHECK_SELECTED.roi_front
        roi = (max(0, int(x + w / 2) - 40), 305, 80, 85)
        scores = []
        for boss_type, template in type_ticket_dict.items():
            rule = copy.copy(template)
            rule.roi_back = roi
            rule.match(self.device.image, threshold=0)
            scores.append((float(rule.max_val), boss_type))
        scores.sort(reverse=True)
        if scores[0][0] < 0.90 or scores[0][0] - scores[1][0] < 0.03:
            return None
        return scores[0][1]

    def check_and_switch_preset(self) -> bool:
        """执行任务前切换预设队伍: 走鬼王挑战页面板(组名+齿轮), 点出战应用。

        预设切换启用时不再执行式神录切换御魂(check_and_switch_soul), 因为
        出战应用预设时若御魂不一致会自动装配御魂, 先手切御魂会被覆盖, 白跑。
        """
        if not self.conf.preset_switch.enable:
            return True
        if self.State.preset_switch_done:
            return True
        logger.hr('Switch preset')
        if self.conf.preset_switch.switch_once:  # 全量: 攻击序列内所有星级, 相同(组,队)只切一次
            seen_presets = set()
            for boss_type in self.conf.meta_demon_config.fire_sequence_v:
                group, team = self.conf.preset_switch.get_preset_by_enum(boss_type)
                if group is None or (group, team) in seen_presets:
                    continue
                seen_presets.add((group, team))
                if not self._apply_preset_team(group, team):
                    raise GameStuckError('超鬼王预设应用未确认')
            self.State.preset_switch_done = True
            return True
        if self.cur_boss_type is None:
            raise GameStuckError('当前鬼王星级未知，禁止猜测预设队伍')
        # 先检测鬼王再去切预设: 星级已在召唤/刷新时识别; 5/6星再补一次名字检测
        group, team = None, None
        if self.cur_boss_type in (BossType.FIVE_STARS, BossType.SIX_STARS):
            if not self.cur_boss_name:
                self.cur_boss_name = self._detect_boss_name() or ''
                if self.cur_boss_name:
                    logger.info(f'鬼王名字: {self.cur_boss_name}')
            hit = self.conf.preset_switch.get_preset_by_name(self.cur_boss_name)
            if hit is not None and hit != (None, None):
                group, team = hit
                logger.info(f'名字映射命中: {self.cur_boss_name} -> {group},{team}')
        if group is None:  # 名字未命中(或1-4星), 用默认星级配置
            group, team = self.conf.preset_switch.get_preset_by_enum(self.cur_boss_type)
        if group is None:
            logger.info(f'{boss_name_cn(self.cur_boss_type)} 无预设配置, 不切换')
            self.State.preset_switch_done = True
            return True
        if not self._apply_preset_team(group, team):
            raise GameStuckError('超鬼王预设应用未确认')
        self.State.preset_switch_done = True
        return True

    def _pill_matches(self, team_name: str) -> bool:
        current = (self.O_PS_CURRENT.ocr(self.device.image) or '').replace(' ', '').strip()
        return bool(current) and current == team_name.replace(' ', '').strip()

    def _apply_preset_team(self, group_name: str, team_name: str) -> bool:
        try:
            return self._apply_preset_team_inner(group_name, team_name)
        finally:
            self._preset_close_panel()

    def _apply_preset_team_inner(self, group_name: str, team_name: str) -> bool:
        """在预设面板中应用 (组名, 队伍名), 应用后 OCR 右侧命令条验证, 失败重试3轮。

        仅本次已确认的同组同队且命令条精确匹配时跳过。
        """
        self.screenshot()
        if getattr(self, '_applied_preset', None) == (group_name, team_name) and self._pill_matches(team_name):
            logger.info(f'预设已在场: {team_name}, 跳过重复应用')
            return True
        deadline = time.monotonic() + 75
        for attempt in range(1, 4):
            if time.monotonic() >= deadline:
                raise GameStuckError('超鬼王预设切换超过75秒')
            self.screenshot()
            if not self.appear(self.I_MD_FIRE):
                raise GameStuckError('超鬼王预设切换前未确认挑战页')
            logger.info(f'切换预设 第{attempt}轮: {group_name} / {team_name}')
            # 命令条文字是当前预设名会变化, 只能按坐标点击; 面板开着再点只会复位, 无副作用
            self.device.click(1163, 448, control_name='MD_PRESET_OPEN')
            time.sleep(2.0)  # 等面板动画渲染完
            self.screenshot()
            if not self.appear(self.I_MD_PS_BATTLE):
                self._preset_close_panel()
                continue
            if not self._preset_select_by_ocr(self.O_PS_GROUP, group_name):
                self._preset_close_panel()
                continue
            if not self._preset_select_by_ocr(self.O_PS_TEAM, team_name):
                self._preset_close_panel()
                continue
            self.screenshot()
            if not self.appear(self.I_MD_PS_BATTLE):
                raise GameStuckError('超鬼王预设面板未确认，禁止点击出战')
            self.device.click(817, 577, control_name='MD_PRESET_APPLY')  # 出战
            # 御魂不一致会弹「自动装配御魂并出战」确认, 点确定(预设面板专用模板)
            # 没弹窗(御魂一致)就不点, 直接验证后进挑战
            for _ in range(6):
                time.sleep(0.5)
                self.screenshot()
                if self.appear(self.I_MD_PS_SURE):
                    self.click(self.I_MD_PS_SURE)
                    break
            # 等应用完成: 有确认弹窗时御魂自动装配有动画, 面板关闭可能超过 2 秒,
            # 不能用固定 sleep 只验一次(会把成功误判成失败再点一次出战)
            for _ in range(10):
                time.sleep(0.7)
                self.screenshot()
                if not self.appear(self.I_MD_PS_BATTLE):  # 面板已自动关闭
                    break
            if not self.appear(self.I_MD_PS_BATTLE) and not self.appear(self.I_MD_PS_SURE) and self.appear(self.I_MD_FIRE) and self._pill_matches(team_name):
                self._applied_preset = (group_name, team_name)
                logger.info(f'预设已应用: {team_name}')
                return True
            logger.warning(f'切换预设失败: {group_name} / {team_name}')
            self._preset_close_panel()
        return False

    def _preset_select_by_ocr(self, rule_ocr, target_text: str) -> bool:
        """精确匹配组名/队名，按对应列滚动，最多3屏。"""
        for _ in range(3):
            results = rule_ocr.detect_and_ocr(self.screenshot())
            for result in results:
                text = (result.ocr_text or '').replace(' ', '').strip()
                if not text:
                    continue
                if text == target_text.replace(' ', '').strip():
                    y1 = min(point[1] for point in result.box)
                    y2 = max(point[1] for point in result.box)
                    self.device.click(rule_ocr.roi[0] + rule_ocr.roi[2] // 2,
                                      rule_ocr.roi[1] + int((y1 + y2) / 2),
                                      control_name=f'MD_PRESET_{rule_ocr.name}')
                    time.sleep(1.5)  # 等列表刷新
                    return True
            x, y, w, h = rule_ocr.roi
            self.swipe(RuleSwipe(roi_front=(x+w//2, y+60, 10, 10),
                                 roi_back=(x+w//2, y+h-50, 10, 10),
                                 mode='vector', name='md_preset_list'))
            time.sleep(1.5)
        logger.warning(f'预设面板中未找到「{target_text}」')
        return False

    def _preset_close_panel(self):
        """关闭预设面板(点面板外空白), 面板本就没开时无副作用。"""
        for _ in range(3):
            self.screenshot()
            if not self.appear(self.I_MD_PS_BATTLE):
                return
            self.device.click(125, 650, control_name='MD_PRESET_CLOSE')
            time.sleep(1.5)
        raise GameStuckError('超鬼王预设面板未关闭')

    def check_and_synthesize(self) -> bool:
        """自动合成裂变之眼, 每次任务运行执行一次"""
        sequence = self.conf.meta_demon_config.synthesize_sequence_v
        if not sequence:
            return False
        logger.hr('Synthesize eyes')
        self.screenshot()
        if not self.appear(self.I_MD_SYNTH_TITLE):
            if not self.appear_then_click(self.I_MD_SYNTHESIZE, interval=0.8):
                logger.info('Synthesize entry not found, skip')
                return False
            opened = False
            for _ in range(10):
                time.sleep(0.5)
                self.screenshot()
                if self.appear(self.I_MD_SYNTH_TITLE):
                    opened = True
                    break
            if not opened:
                logger.warning('Synthesize panel not opened, skip')
                return False
        try:
            for boss_type in sequence:
                if not 1 <= boss_type.value <= 5:
                    continue
                self._synthesize_one_type(boss_type)
        finally:
            self._close_synthesize_panel()
        return True

    def _synthesize_one_type(self, boss_type: BossType):
        """合成指定星级, 三个同星级合成一个高一级"""
        row_rule = {
            BossType.ONE_STAR: self.I_MD_SYNTH_ROW_ONE,
            BossType.TWO_STARS: self.I_MD_SYNTH_ROW_TWO,
            BossType.THREE_STARS: self.I_MD_SYNTH_ROW_THREE,
            BossType.FOUR_STARS: self.I_MD_SYNTH_ROW_FOUR,
            BossType.FIVE_STARS: self.I_MD_SYNTH_ROW_FIVE,
        }[boss_type]
        count_rule = copy.copy({
            BossType.ONE_STAR: self.O_MD_SYNTH_COUNT_ONE,
            BossType.TWO_STARS: self.O_MD_SYNTH_COUNT_TWO,
            BossType.THREE_STARS: self.O_MD_SYNTH_COUNT_THREE,
            BossType.FOUR_STARS: self.O_MD_SYNTH_COUNT_FOUR,
            BossType.FIVE_STARS: self.O_MD_SYNTH_COUNT_FIVE,
        }[boss_type])
        logger.info(f'合成 {boss_name_cn(boss_type)}')
        deadline = time.monotonic() + 90
        for _ in range(20):
            if time.monotonic() >= deadline:
                raise GameStuckError('超鬼王单星级合成超过90秒')
            self.screenshot()
            if not self.appear(self.I_MD_SYNTH_TITLE):
                raise GameStuckError('超鬼王合成面板未确认')
            # 某星级数量归零后列表会重新排列, 必须动态定位该星级所在行
            if not self.appear(row_rule):
                logger.info(f'{boss_name_cn(boss_type)} 对应行未找到, 停止合成')
                return
            row_y = row_rule.roi_front[1]
            count_rule.roi = (350, row_y + 52, 80, 24)
            count = self._read_synth_number(count_rule)
            if count < 3:
                logger.info(f'{boss_name_cn(boss_type)} 数量 {count} < 3, 停止合成')
                return
            # 二星及以上每次合成消耗一张合成券
            if boss_type.value >= BossType.TWO_STARS:
                ticket = self._read_synth_number(self.O_MD_SYNTH_TICKET)
                if ticket < 1:
                    logger.info(f'无合成票, 停止 {boss_name_cn(boss_type)}')
                    return
            # 选中星级必须点击该行图标, 点击文字只会改变预览
            self.device.click(245, row_y + 45)
            time.sleep(0.5)
            self.screenshot()
            # 选中星级后可能已经自动放入了3个, 此时按钮显示"一键卸载"
            if self.appear(self.I_MD_SYNTH_REMOVE, interval=0.4):
                self.click(self.I_MD_SYNTH_REMOVE)
                time.sleep(0.5)
                self.screenshot()
            if self.appear(self.I_MD_SYNTH_ADD, interval=0.4):
                self.click(self.I_MD_SYNTH_ADD)
                time.sleep(0.5)
                self.screenshot()
            else:
                logger.warning('Add button not found, stop synthesize')
                return
            if not self.appear(self.I_MD_SYNTH_START, interval=0.5):
                logger.warning('Start button not found, stop synthesize')
                return
            self.click(self.I_MD_SYNTH_START)
            time.sleep(1.5)
            # 点击空白处关闭"获得奖励"弹窗
            self.device.click(500, 620)
            time.sleep(0.6)
            self.screenshot()
            if not self.appear(row_rule):
                logger.info(f'{boss_name_cn(boss_type)} 对应行消失, 停止合成')
                return
            row_y = row_rule.roi_front[1]
            count_rule.roi = (350, row_y + 52, 80, 24)
            new_count = self._read_synth_number(count_rule)
            logger.info(f'{boss_name_cn(boss_type)} 数量 {count} -> {new_count}')
            if new_count != count - 3:
                raise GameStuckError('超鬼王合成扣除数量未确认，禁止继续合成')

    def _read_synth_number(self, rule):
        import re
        raw = RuleOcr(roi=rule.roi, area=rule.roi, mode='Full', method='Default',
                      keyword='', name=rule.name)
        text = ''.join((r.ocr_text or '') for r in raw.detect_and_ocr(self.device.image)).strip()
        if not re.fullmatch(r'[0-9]+', text):
            raise GameStuckError('超鬼王合成数量识别失败，禁止猜测消耗')
        return int(text)

    def _close_synthesize_panel(self):
        """关闭合成面板, 返回鬼王页"""
        for _ in range(3):
            self.screenshot()
            if not self.appear(self.I_MD_SYNTH_TITLE):
                return
            if self.appear_then_click(self.I_MD_SYNTH_CLOSE, interval=0.5):
                time.sleep(0.6)
                continue
            time.sleep(0.6)
        raise GameStuckError('超鬼王合成面板未关闭')

    def finish_task(self):
        self._restore_navigation()
        if not self.ui_goto_page(ipages.page_main):
            raise GameStuckError('超鬼王结束后未返回庭院')
        raise TaskEnd


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('4399')
    t = ScriptTask(c)

    t.run()
