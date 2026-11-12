import time
import re

from cached_property import cached_property

from module.logger import logger
from module.exception import GameStuckError
from tasks.base_task import BaseTask
from tasks.SixRealms_jue.assets import SixRealms_jueAssets


class MoonSeaSkills(BaseTask, SixRealms_jueAssets):

    cnt_skill101 = 0
    cnt_skillpower = 0
    # 进入绽放之屿次数
    cnt_zhanfang = 0

    def in_main(self, screenshot: bool = False):
        if screenshot:
            self.screenshot()
        if self.appear(self.I_M_STORE):
            return True
        if self.appear(self.I_M_STORE_ACTIVITY):
            return True
        if self.appear(self.I_BOSS_FIRE):
            return True
        return False

    def battle_lock_team(self):
        self.ui_click(self.I_BATTLE_TEAM_UNLOCK, self.I_BATTLE_TEAM_LOCK)
        return

    def island_battle(self):
        # 小怪战斗
        self.screenshot()
        while 1:
            self.screenshot()
            if self.appear(self.I_SKILL_REFRESH):
                break
            if self.appear(self.I_COIN):
                break
            if self.appear_then_click(self.I_NPC_FIRE, interval=1):
                self.device.stuck_record_clear()
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
        self.device.stuck_record_clear()

    @cached_property
    def selects_button(self):
        return [
            self.I_SELECT_0,
            self.I_SELECT_1,
            self.I_SELECT_2,
            self.I_SELECT_3,
        ]

    def _select_skill(self) -> int:
        self.screenshot()
        self.wait_until_stable(self.I_SELECT_3)
        select = 3  # 从0开始计数
        button = None
        # 只选轰雷
        if button is None and self.appear(self.I_SKILL101):
            button = self.I_SKILL101
        if button is not None:
            x, y = button.front_center()
            if x < 360:
                select = 0
            elif 360 <= x < 640:
                select = 1
            elif 640 <= x < 960:
                select = 2
            else:
                select = 3
        logger.info(f'Select {select}')
        return select

    def select_skill(self, refresh: bool = False):
        def check_coin_skill() -> bool:
            coin = self.O_COIN_NUM.ocr(self.device.image)
            return False if coin < 50 else True

        def check_refresh() -> bool:
            # 检测是否有钱刷新技能
            text = self.O_SKILL_REFRESH.ocr(self.device.image)
            matches = re.search(f"剩\d+次", text)
            if matches:
                refresh_time = int(matches.group()[1])
                logger.info(f'刷新次数: {refresh_time}')
                if refresh_time <= 0:
                    return False
                else:
                    return True
            return False

        if self.appear(self.I_UI_SURE):
            self.ui_click_until_disappear(self.I_UI_SURE)
            return True

        # 强化弹窗可能延迟出现，或被邀请处理打断；不能依赖外层四选一按钮。
        if self.select_strengthening():
            return True

        if self.appear(self.I_SKILL_REFRESH) and self.appear(self.I_SELECT_3) and not self.appear(self.I_COIN):
            # 战斗结束后选技能
            logger.info('开始选择技能')
            select = 3
            if self.cnt_skill101 < 1:
                select = self._select_skill()
                # 如果没有轰雷并且钱够并且还有刷新次数
                while self.cnt_zhanfang >= 2 and self.cnt_skillpower >= 3 and refresh and select == 3 and check_coin_skill() and check_refresh():
                    logger.info('开始刷新技能')
                    self.appear_then_click(self.I_SKILL_REFRESH)
                    self.wait_animate_stable(self.C_MAIN_ANIMATE_KEEP, timeout=1)
                    select = self._select_skill()
            if self.appear_then_click(self.selects_button[select], interval=1) and select != 3:
                self.cnt_skill101 += 1
                logger.info(f'轰雷等级：{self.cnt_skill101}, 力量等级：{self.cnt_skillpower}')
            # 强化弹窗在下一帧独立处理，点击外层按钮不算完成升级。
            return True

        if self.appear_then_click(self.I_COIN, action=self.C_UI_REWARD, interval=1.5):
            return True
        return None

    def strengthening_appear(self):
        return self.appear(self.I_PEACOCK_SKILL1) or self.appear(self.I_PEACOCK_SKILL2)

    def select_strengthening(self):
        if not self.strengthening_appear():
            return False
        deadline = time.monotonic() + 10
        attempts = 0
        selected = None
        confirmed_since = None
        while time.monotonic() < deadline:
            # 所有重试共享同一总超时；截图仍经过公共邀请和设备卡死检测。
            if not self.strengthening_appear():
                if (self.appear(self.I_SELECT_3) or self.appear(self.I_COIN)
                        or self.in_main()):
                    if confirmed_since is None:
                        confirmed_since = time.monotonic()
                    if time.monotonic() - confirmed_since < .35:
                        self.screenshot()
                        continue
                    if selected == self.I_PEACOCK_SKILL1:
                        self.cnt_skillpower += 1
                        logger.info(f'轰雷等级：{self.cnt_skill101}, 力量等级：{self.cnt_skillpower}')
                    return True
                confirmed_since = None
                if selected is not None and attempts < 3:
                    if self.appear_then_click(self.I_UI_SURE, interval=1):
                        attempts += 1
            else:
                confirmed_since = None
                if attempts < 3:
                    button = (self.I_PEACOCK_SKILL1 if self.appear(self.I_PEACOCK_SKILL1)
                              else self.I_PEACOCK_SKILL2)
                    if self.appear_then_click(button, interval=1):
                        attempts += 1
                        selected = button
            self.screenshot()
        raise GameStuckError('六道觉强化选择未确认关闭（最多点击3次，限时10秒）')


