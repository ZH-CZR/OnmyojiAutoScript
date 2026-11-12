"""单人结契的樱饼观察流程；自动期间只在结契页关闭开关。"""
from datetime import datetime

import numpy as np

from module.atom.click import RuleClick
from module.atom.image import RuleImage
from module.base.timer import Timer
from module.exception import GameStuckError, TaskEnd
from module.logger import logger
from tasks.GameUi.page import page_main


class BondlingSakura:
    I_BONDLING_PLATE_LIMIT = RuleImage(
        file='sakura/plate_limit.png', path='./tasks/BondlingFairyland/',
        roi_front=(426, 263, 430, 62), roi_back=(426, 263, 430, 62),
        threshold=0.85, method='Template matching')
    I_BONDLING_PLATE_LIMIT_CONFIRM = RuleImage(
        file='sakura/plate_limit_confirm.png', path='./tasks/BondlingFairyland/',
        roi_front=(665, 407, 178, 65), roi_back=(665, 407, 178, 65),
        threshold=0.85, method='Template matching')
    I_BONDLING_SAKURA_OFF = RuleImage(
        file='sakura/auto_off.png', path='./tasks/BondlingFairyland/',
        roi_front=(786, 638, 32, 32), roi_back=(786, 638, 32, 32),
        threshold=0.8, method='Template matching')
    C_BONDLING_SAKURA = RuleClick(
        roi_front=(795, 647, 14, 14), roi_back=(795, 647, 14, 14),
        name='bondling_sakura')

    def runtime_checkpoint(self):
        # 游戏自动战斗在脚本休息时仍会继续。先在结契页停饼，再进入休息。
        if getattr(self, '_bondling_sakura_observing', False):
            return False
        return super().runtime_checkpoint()

    def confirm_bondling_plate_limit(self):
        """仅确认式盘数量上限提示；不切换“当天不再提醒”复选框。"""
        if not self.appear(self.I_BONDLING_PLATE_LIMIT):
            return False
        timer = Timer(5).start()
        clicks = 0
        while self.appear(self.I_BONDLING_PLATE_LIMIT):
            if (clicks < 3 and self.appear(self.I_BONDLING_PLATE_LIMIT_CONFIRM)
                    and self.click(self.I_BONDLING_PLATE_LIMIT_CONFIRM, interval=1)):
                clicks += 1
                self.device.stuck_record_add('BATTLE_STATUS_S')
            if timer.reached():
                raise GameStuckError('契灵式盘上限提示未关闭')
            self.screenshot()
        logger.info('已确认契灵式盘数量上限提示')
        return True

    def bondling_sakura_state(self):
        """返回开/关/未知；仅由已确认结契页的调用方使用。

        关闭态按圆内 RGB 颜色分布确认，不依赖停止时的图案角度或像素
        对齐；开启态按亮蓝色比例确认。中间亮度及遮挡返回未知。
        """
        image = self.device.image
        if image is None or image.shape[:2] != (720, 1280):
            return None
        patch = image[638:670, 786:818, :3].astype(np.float32)
        y, x = np.ogrid[:32, :32]
        mask = (x - 16) ** 2 + (y - 16) ** 2 <= 12 ** 2
        pixels = patch[mask]
        reference = self.I_BONDLING_SAKURA_OFF.image.astype(np.float32)[mask]
        # 图案停止角度、截图采样和抗锯齿会改变同一坐标的颜色，不能逐点
        # 相减。按通道排序比较分布，保留对颜色/亮度的限制。
        color_difference = np.abs(np.sort(pixels, axis=0) - np.sort(reference, axis=0)).mean()
        if color_difference <= 15:
            return False
        bright_blue = (pixels[:, 2] >= 170) & (pixels[:, 2] - pixels[:, 0] >= 15)
        if bright_blue.mean() >= 0.45:
            return True
        return None

    def confirm_bondling_start_prompt(self):
        """结契背景可确认时处理开战确认，避免把弹窗等待当成耗饼。"""
        def button():
            if not self.in_catch_ui():
                return None
            for marker in (self.I_UI_CONFIRM, self.I_UI_SURE):
                if self.appear(marker):
                    return marker
            return None

        target = button()
        if target is None:
            return False
        timer = Timer(5).start()
        clicks = 0
        while target is not None:
            if timer.reached():
                raise GameStuckError('契灵开战确认未关闭')
            if clicks < 3 and self.click(target, interval=1):
                clicks += 1
                self.device.stuck_record_add('BATTLE_STATUS_S')
            self.screenshot()
            target = button()
        logger.info('已处理契灵开战确认，继续观察自动战斗')
        return True

    def bondling_sakura_limit_reached(self):
        return (self.current_count >= self.limit_count
                or datetime.now() - self.start_time >= self.limit_time)

    def finish_bondling_sakura_exhausted(self):
        # 调用前已经停饼并退回稳定探查页，公共导航不接管战斗或结契弹窗。
        logger.warning('契灵挂饼无进展，已安全退出结契，提前结束本次任务')
        if not self.ui_goto_page(page_main, skip_first_screenshot=False):
            raise GameStuckError('樱饼耗尽后未能返回庭院')
        self.screenshot()
        if not self.ui_page_appear(page_main):
            raise GameStuckError('樱饼耗尽后未确认庭院')
        self.set_next_run(task='BondlingFairyland', finish=True, success=True)
        raise TaskEnd

    def run_bondling_sakura(self, *, can_start=True):
        """沿用进入战斗计一次的规则；到限只在返回结契页后停饼。

        返回 True 表示捕获后已返回探查页，False 表示挂机关闭/到限。
        准备、结算和奖励不点击，不在战斗中强退。
        """
        started = False
        round_active = False
        settled = False
        last_phase = None
        expected = None
        toggle_timer = None
        stable_timer = None
        stable_key = None
        unknown_timer = None
        no_progress_timer = None
        exhaustion_pending = False
        exit_timer = None
        exit_clicks = 0
        paused_for_guard = False
        observing_before = getattr(self, '_bondling_sakura_observing', False)
        self._bondling_sakura_observing = True
        had_wait = 'BATTLE_STATUS_S' in self.device.detect_record
        self.device.stuck_record_add('BATTLE_STATUS_S')
        try:
            while True:
                self.screenshot()
                if self.confirm_bondling_plate_limit() or self.confirm_bondling_start_prompt():
                    # 弹窗会遮暗开关，必须先关闭并重新截图，且不计作战斗。
                    stable_key = stable_timer = unknown_timer = None
                    no_progress_timer = None
                    if toggle_timer is not None:
                        toggle_timer.reset()
                    continue
                catch = self.in_catch_ui()
                if not catch:
                    no_progress_timer = None
                search = not catch and self.in_search_ui()
                reward = not catch and not search and self.appear(self.I_REWARD)
                result = reward or (not catch and not search and self.appear([
                    self.I_CAP_SUCCESS, self.I_CAP_FAILURE, self.I_BATTLE_SUCCESS,
                    self.I_BATTLE_FAIL, self.I_BATTLE_FAIL_ABANDON,
                    self.I_WIN, self.I_FALSE]))
                battle = (not catch and not search and not result
                          and (self.is_in_prepare(False) or self.is_in_battle(False)))
                phase = 'catch' if catch else 'search' if search else 'result' if result else 'battle' if battle else None
                if (exit_timer is not None and not (battle or result or search)
                        and exit_timer.reached()):
                    raise GameStuckError('契灵停饼后未能退出结契页')
                self.device.screenshot_interval_set('combat' if battle else None)
                if phase is not None and phase != last_phase:
                    # 仅识别到实际阶段进展才刷新计时，卡在同一阶段仍会超时。
                    self.device.stuck_timer.reset()
                    self.device.stuck_timer_long.reset()
                    last_phase = phase

                if battle or result:
                    # 停饼期间仍可能开始一场战斗；沿用观察流程等待结算，不能导航强退。
                    exit_timer = None
                    exit_clicks = 0
                    if battle and settled:
                        round_active = False
                        settled = False
                    if not round_active:
                        self.current_count += 1
                        round_active = True
                        logger.info(f'契灵挂饼挑战次数: {self.current_count} / {self.limit_count}')
                    # 捕获提示可能在同场战斗结束前消失，不能将提示后的战斗
                    # 误算新一场；漏过主页时仅以已出现奖励作为分场依据。
                    if reward:
                        settled = True
                    started = True
                    # 开关切换与开战可能竞态；战斗中无法验证开关，返回后重新判断。
                    expected = None

                key = None
                if search:
                    key = 'search'
                elif catch:
                    round_active = False
                    settled = False
                    state = self.bondling_sakura_state()
                    if state is None:
                        if unknown_timer is None:
                            unknown_timer = Timer(5).start()
                        if unknown_timer.reached():
                            raise GameStuckError('无法确认契灵樱饼开关状态')
                    else:
                        unknown_timer = None
                        if state:
                            started = True
                        if expected is not None:
                            if state == expected:
                                expected = None
                            elif toggle_timer.reached():
                                raise GameStuckError('契灵樱饼开关切换未生效')
                        guard = getattr(self.device, 'activity_guard', None)
                        rest = guard is not None and guard.pending
                        stop = exhaustion_pending or not can_start or self.bondling_sakura_limit_reached() or rest
                        if started and expected is None and not stop:
                            # 判定任务界面有没有推进，不让背景/动态图标重置等待。
                            # 只监视结契页，正常战斗、领奖、弹窗及休息均不累计。
                            if no_progress_timer is None:
                                no_progress_timer = Timer(10).start()
                            elif no_progress_timer.current() >= 10:
                                logger.warning('结契页面连续10秒未观察到战斗，先停饼并确认安全退出')
                                exhaustion_pending = True
                                stop = True
                                no_progress_timer = None
                        else:
                            no_progress_timer = None
                        if expected is None:
                            if (state and stop) or (not state and not started and not stop):
                                # 当前截图同时确认结契页和开关状态；一次切换后等确认。
                                if self.click(self.C_BONDLING_SAKURA, interval=0.8):
                                    expected = not state
                                    toggle_timer = Timer(5).start()
                                    self.device.stuck_record_add('BATTLE_STATUS_S')
                                    started = True
                                    paused_for_guard = bool(not exhaustion_pending and state and rest and can_start
                                                            and not self.bondling_sakura_limit_reached())
                            elif not state:
                                if rest and not started and can_start and not self.bondling_sakura_limit_reached():
                                    paused_for_guard = True
                                if stop:
                                    key = 'off'

                if key is None:
                    stable_key = stable_timer = None
                elif key != stable_key:
                    stable_key = key
                    stable_timer = Timer(1).start()
                elif stable_timer.reached():
                    if exhaustion_pending:
                        if key == 'search':
                            self.finish_bondling_sakura_exhausted()
                        # 只在结契页关闭态稳定一秒后点击原返回素材，下一帧重新识别。
                        if exit_timer is None:
                            exit_timer = Timer(10).start()
                        if (exit_clicks < 3 and self.appear(self.I_BACK_YELLOW)
                                and self.click(self.I_BACK_YELLOW, interval=1)):
                            exit_clicks += 1
                            self.device.stuck_record_add('BATTLE_STATUS_S')
                        continue
                    if key == 'off' and paused_for_guard:
                        self._bondling_sakura_observing = False
                        try:
                            self.runtime_checkpoint()
                        finally:
                            self._bondling_sakura_observing = True
                        paused_for_guard = False
                        started = False
                        no_progress_timer = None
                        stable_key = stable_timer = None
                        continue
                    logger.info(f'契灵挂饼结束，挑战次数: {self.current_count} / {self.limit_count}')
                    return key == 'search'
        finally:
            self._bondling_sakura_observing = observing_before
            self.device.screenshot_interval_set()
            if not had_wait:
                self.device.detect_record.discard('BATTLE_STATUS_S')
