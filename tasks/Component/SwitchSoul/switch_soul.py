# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep
from typing import Union

import numpy as np

from module.atom.click import RuleClick
from module.atom.long_click import RuleLongClick
from module.atom.ocr import RuleOcr
from module.base.timer import Timer
from module.exception import GameStuckError
from module.logger import logger
from tasks.Component.Costume.config import ShikigamiType
from tasks.Component.SwitchSoul.assets import SwitchSoulAssets
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_shikigami_records


class SwitchSoul(GameUi, SwitchSoulAssets):
    # 类变量，跨实例共享，不会被 config 重建影响
    _current_switch_soul: str = '-'

    def run_switch_soul(self, target, *, force=False):
        if not force and SwitchSoul._current_switch_soul == target:
            logger.info(f'当前御魂[{target}]已装备, 无需切换')
            return
        logger.info(f'当前装备御魂[{SwitchSoul._current_switch_soul}], 目标御魂[{target}]')

        selection = self.switch_parser(target) if isinstance(target, str) else target
        if not self.ui_goto_page(page_shikigami_records):
            raise GameStuckError('切换御魂未到达式神录，停止换魂及后续任务操作')

        SwitchSoul._current_switch_soul = '-'
        logger.info(f'开始切换御魂[{target}]')
        self.click_preset()
        self.switch_souls(selection)
        SwitchSoul._current_switch_soul = target

    def run_switch_soul_by_name(self, groupName, teamName):
        """
        保证在式神录的界面
        :return:
        """
        group_team = f"{groupName},{teamName}"

        if SwitchSoul._current_switch_soul == group_team:
            logger.info(f'当前御魂[{group_team}]已装备, 无需切换')
            return
        logger.info(f'当前装备御魂[{SwitchSoul._current_switch_soul}], 目标御魂[{group_team}]')

        self.ui_goto_page(page_shikigami_records)

        SwitchSoul._current_switch_soul = group_team
        logger.info(f'开始切换御魂[{group_team}]')

        if isinstance(groupName, str) and isinstance(teamName, str):
            self.click_preset()
            self.switch_soul_by_name(groupName, teamName)

    def click_preset(self) -> None:
        """
        点击预设
        :return:
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_SOU_SWITCH_1):
                break
            if self.appear(self.I_SOU_SWITCH_2):
                break
            if self.appear(self.I_SOU_SWITCH_3):
                break
            if self.appear(self.I_SOU_SWITCH_4):
                break
            if self.appear(self.I_SOU_TEAM_PRESENT):
                break
            if self.appear_then_click(self.I_CANCEL):
                continue
            if self.appear_then_click(self.I_SOUL_PRESET, interval=3):
                continue
        logger.info('在切换御魂中点击预设')

    def switch_soul_one(self, group: int, team: int) -> None:
        if not 1 <= group <= 8:
            raise ValueError('御魂分组配置错误，只支持 [1-8]')
        if not 1 <= team <= 4:
            raise ValueError('御魂队伍配置错误，只支持 [1-4]')

        group_click = getattr(self, f'C_SOU_GROUP_{group}')
        team_equip = getattr(self, f'I_SOU_SWITCH_{team}')
        timeout = Timer(15).start()

        # 滚动前后都读到同一组名称，才按从顶部开始的分组位置点击。
        previous_names = []
        while True:
            self.screenshot()
            if timeout.reached():
                raise GameStuckError('切换御魂未确认分组列表已滚动至顶部')
            results = self.O_SS_GROUP_NAME.detect_and_ocr(self.device.image)
            names = [result.ocr_text for result in results if result.ocr_text.strip()]
            if names and names == previous_names:
                break
            previous_names = names
            self.swipe(self.S_SS_GROUP_SWIPE_UP, 1)
            sleep(0.5)

        for _ in range(3):
            self.click(group_click)
            sleep(0.5)
            self.screenshot()
            if timeout.reached():
                raise GameStuckError(f'切换御魂未确认选中第 {group} 组')
            if self._soul_group_selected(group, group_click):
                break
        else:
            raise GameStuckError(f'切换御魂未确认选中第 {group} 组')

        team_clicked = False
        confirmed = False
        panel_stable = Timer(0.35)
        while True:
            self.screenshot()
            if timeout.reached():
                raise GameStuckError(f'御魂 [{group},{team}] 装配未确认')
            if not team_clicked:
                if (self._soul_group_selected(group, group_click) and not self.appear(self.I_UI_SURE)
                        and not self.appear(self.I_SOU_SWITCH_SURE)):
                    team_clicked = self.appear_then_click(team_equip, interval=None)
            elif not confirmed:
                confirmed = self.appear_then_click(self.I_SOU_SWITCH_SURE, interval=None)
            elif (self.appear(self.I_SOU_SWITCH_SURE) or self.appear(self.I_UI_SURE)
                  or not self._soul_group_selected(group, group_click)
                  or not (self.appear(self.I_SOU_TEAM_PRESENT) or self.appear(team_equip))):
                panel_stable.clear()
            elif panel_stable.started() and panel_stable.reached():
                logger.info(f'御魂 [{group},{team}] 装配确认已完成')
                return
            else:
                panel_stable.start()

    def _soul_group_selected(self, group: int, group_click: RuleClick) -> bool:
        costume = self.config.model.global_game.costume_config.costume_shikigami_type
        if costume != ShikigamiType.COSTUME_SHIKIGAMI_11:
            return self.appear(getattr(self, f'I_SOU_CHECK_GROUP_{group}'))

        # 该幕间皮肤当前用蓝色双侧发光边框标记选中组，旧金色标记素材不再匹配。
        x, _, width, _ = self.O_SS_GROUP_NAME.roi
        _, y, _, height = group_click.roi_front
        center_y = y + height // 2
        row = self.device.image[center_y - 12:center_y + 12, x:x + width]
        left, inner, right = (
            np.median(region, axis=(0, 1))
            for region in (row[:, 1:6], row[:, 16:22], row[:, -6:-1])
        )
        return bool(
            left[2] > left[1] > left[0] and right[2] > right[1] > right[0]
            and min(left[1], right[1]) - inner[1] >= 15
        )

    def switch_souls(self, target: tuple or list[tuple]) -> None:
        """
        切换御魂
        :param target: [(1, 1), (2, 2), (3, 3), (4, 4)]  或者是单独的一个元组(4, 4) 第一个是组, 第二个是队伍
        :return:
        """
        if isinstance(target, tuple):
            target = [target]
        for group, team in target:
            group = int(group)
            team = int(team)
            self.switch_soul_one(group, team)

    def exit_shikigami_records(self) -> None:
        """
        退出式神录的界面
        :return:
        """
        while 1:
            self.screenshot()
            if not self.appear(self.I_SOU_CHECK_IN):
                break
            if self.appear_then_click(self.I_RECORD_SOUL_BACK, interval=1):
                continue
        logger.info('退出式神录')

    def switch_soul_by_name(self, groupName, teamName):
        """
        保证在式神录的界面
        :return:
        """
        logger.hr('按名称切换御魂')
        # 滑动至分组最上层
        last_group_text = ''
        while 1:
            self.screenshot()
            compare1 = self.O_SS_GROUP_NAME.detect_and_ocr(self.device.image)
            now_group_text = str([result.ocr_text for result in compare1])
            if now_group_text == last_group_text:
                break
            self.swipe(self.S_SS_GROUP_SWIPE_UP, 2)
            sleep(2.5)
            last_group_text = now_group_text
        logger.info('滑动到顶部 of group')

        # 判断有无目标分组
        while 1:
            self.screenshot()
            # 获取当前分组名
            results = self.O_SS_GROUP_NAME.detect_and_ocr(self.device.image)
            text1 = [result.ocr_text for result in results]
            # 判断当前分组有无目标分组
            result = set(text1).intersection({groupName})
            # 有则跳出检测
            if result and len(result) > 0:
                break
            self.swipe(self.S_SS_GROUP_SWIPE_DOWN)
            sleep(1.5)
        logger.info('向下滑动查找目标组')

        # 选中分组
        while 1:
            self.screenshot()
            self.O_SS_GROUP_NAME.keyword = groupName
            if self.ocr_appear_click(self.O_SS_GROUP_NAME):
                break
        logger.info(f'Select group {groupName}')

        # 滑动至阵容最上层
        last_team_text = ''
        while 1:
            self.screenshot()
            compare1 = self.O_SS_TEAM_NAME.detect_and_ocr(self.device.image)
            now_team_text = str([result.ocr_text for result in compare1])
            # 向上滑动
            if now_team_text == last_team_text:
                break
            self.swipe(self.S_SS_TEAM_SWIPE_DOWN, 1.5)
            sleep(2)
            last_team_text = now_team_text
        logger.info('滑动到顶部 of team')

        # 判断当前分组有无目标阵容
        while 1:
            self.screenshot()
            # 获取当前阵容名
            results = self.O_SS_TEAM_NAME.detect_and_ocr(self.device.image)
            text1 = [result.ocr_text for result in results]
            # 判断当前分组有无目标阵容
            result = set(text1).intersection({teamName})
            # 有则跳出检测
            if result and len(result) > 0:
                break
            self.swipe(self.S_SS_TEAM_SWIPE_UP, 0.3)
        logger.info('向上滑动查找目标队')

        # 选中分组
        while 1:
            self.screenshot()
            self.O_SS_TEAM_NAME.keyword = teamName
            if self.ocr_appear_click(self.O_SS_TEAM_NAME):
                break
        logger.info(f'Select team {teamName}')
        # 切换御魂
        cnt_click: int = 0
        self.O_SS_TEAM_NAME.keyword = teamName
        while 1:
            self.screenshot()
            if cnt_click >= 4:
                break
            if self.appear_then_click(self.I_UI_SURE, interval=0.8):
                continue
            if self.ocr_appear_click_by_rule(self.O_SS_TEAM_NAME, self.I_SOU_CLICK_PRESENT, interval=1.5):
                cnt_click += 1
                continue
        logger.info(f'Switch soul_one group {groupName} team {teamName}')

    def ocr_appear_click_by_rule(self,
                                 target: RuleOcr,
                                 action: Union[RuleClick, RuleLongClick] = None,
                                 interval: float = None,
                                 duration: float = None) -> bool:
        """
        ocr识别目标，如果目标存在，则触发动作
        :param target:
        :param action:
        :param interval:
        :param duration:
        :return:
        """
        appear = self.ocr_appear(target, interval)

        if not appear:
            return False

        x1, y1, w1, h1 = target.area
        x, y = action.coord()

        self.device.click(x=x, y=y1, control_name=target.name)
        return True


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('百鬼-16480')
    s = SwitchSoul(c)

    # s.click_preset()
    s.run_switch_soul(' 1， 1')
    s.run_switch_soul('4, 1')

    # s.switch_soul_by_name('契灵', '茨球')
    # s.run_switch_soul_by_name('寮活动', '阴界之门')
    # s.run_switch_soul_by_name('寮活动', '阴界之门')
