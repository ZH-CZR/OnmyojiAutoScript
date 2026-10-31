# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep, monotonic
from typing import Union

from module.atom.click import RuleClick
from module.atom.long_click import RuleLongClick
from module.atom.ocr import RuleOcr
from module.logger import logger
from module.exception import GameStuckError
from tasks.Component.SwitchSoul.assets import SwitchSoulAssets
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_shikigami_records


class SwitchSoul(GameUi, SwitchSoulAssets):
    # 类变量，跨实例共享，不会被 config 重建影响
    _current_switch_soul: str = '-'

    def run_switch_soul(self, target):
        """
        保证在式神录的界面
        :return:
        """
        if SwitchSoul._current_switch_soul == target:
            logger.info(f'当前御魂[{target}]已装备, 无需切换')
            return
        logger.info(f'当前装备御魂[{SwitchSoul._current_switch_soul}], 目标御魂[{target}]')

        self.ui_goto_page(page_shikigami_records)

        logger.info(f'开始切换御魂[{target}]')

        cache_target = target
        if isinstance(target, str):
            try:
                target = self.switch_parser(target)
            except ValueError:
                logger.error('切换御魂配置错误')
                return
        SwitchSoul._current_switch_soul = '-'
        self.click_preset()
        if self.switch_souls(target) is True:
            SwitchSoul._current_switch_soul = cache_target

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

        logger.info(f'开始切换御魂[{group_team}]')

        if not isinstance(groupName, str) or not isinstance(teamName, str) or not groupName or not teamName:
            raise ValueError('御魂分组名和阵容名不能为空')
        SwitchSoul._current_switch_soul = '-'
        self.click_preset()
        if self.switch_soul_by_name(groupName, teamName) is True:
            SwitchSoul._current_switch_soul = group_team

    def click_preset(self) -> None:
        """
        点击预设
        :return:
        """
        deadline = monotonic() + 15
        while monotonic() < deadline:
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
        else:
            raise GameStuckError('打开御魂预设超时')
        logger.info('在切换御魂中点击预设')

    def switch_soul_one(self, group: int, team: int) -> bool:
        """
        设置一个队伍的预设御魂
        :param group: 只能是[1-8]
        :param team: 只能是[1-4]
        :return:
        """

        def get_group_assets(group: int) -> tuple:
            match = {
                1: tuple([self.C_SOU_GROUP_1, self.I_SOU_CHECK_GROUP_1]),
                2: tuple([self.C_SOU_GROUP_2, self.I_SOU_CHECK_GROUP_2]),
                3: tuple([self.C_SOU_GROUP_3, self.I_SOU_CHECK_GROUP_3]),
                4: tuple([self.C_SOU_GROUP_4, self.I_SOU_CHECK_GROUP_4]),
                5: tuple([self.C_SOU_GROUP_5, self.I_SOU_CHECK_GROUP_5]),
                6: tuple([self.C_SOU_GROUP_6, self.I_SOU_CHECK_GROUP_6]),
                7: tuple([self.C_SOU_GROUP_7, self.I_SOU_CHECK_GROUP_7]),
                8: tuple([self.C_SOU_GROUP_8, self.I_SOU_CHECK_GROUP_8]),
            }
            return match[group]

        def get_team_asset(team: int):
            match = {
                1: self.I_SOU_SWITCH_1,
                2: self.I_SOU_SWITCH_2,
                3: self.I_SOU_SWITCH_3,
                4: self.I_SOU_SWITCH_4,
            }
            return match[team]

        # 滑动至分组最上层(分組過多, 导致第一个分组显示不全)
        SwitchSoul._current_switch_soul = '-'
        cur_text = ""
        deadline = monotonic() + 20
        while monotonic() < deadline:
            self.screenshot()
            compare1 = self.O_SS_GROUP_NAME.detect_and_ocr(self.device.image)
            ocr_text = str([result.ocr_text for result in compare1])
            # 相等时 滑动到最上层
            if compare1 and cur_text == ocr_text:
                break
            cur_text = ocr_text
            # 向上滑动
            self.swipe(self.S_SS_GROUP_SWIPE_UP, 1)
            # 等待滑动动画
            sleep(0.5)
        else:
            raise GameStuckError('御魂数字分组列表回到顶部超时')

        if group < 1 or group > 8:
            raise ValueError('御魂分组配置错误，只支持 [1-8]')
        if team < 1 or team > 4:
            raise ValueError('御魂队伍配置错误，只支持 [1-4]')
        # 这一步是选择组
        target_click, target_check = get_group_assets(group)
        # logger.info(f'选择分组 {group} in initial area {target_click.roi_front}')

        # while 1:
        #     self.screenshot()
        #     if self.click(target_click, interval=1):
        #         continue
        #     if self.appear(target_check):
        #         break
        # 2023.8.5 修改为无反馈的点击切换
        for i in range(3):
            self.click(target_click)
            sleep(0.5)
        # 游戏无确认弹窗，实际发出切换点击即完成，不等待额外配装反馈。
        target_team = get_team_asset(team)
        deadline = monotonic() + 10
        while monotonic() < deadline:
            self.screenshot()
            if self.appear_then_click(target_team, interval=1):
                break
            sleep(0.1)
        else:
            raise GameStuckError(f'御魂阵容按钮查找超时：{group},{team}')

        logger.info(f'已切换御魂 [{group},{team}]')
        return True

    def switch_souls(self, target: tuple or list[tuple]) -> bool:
        """
        切换御魂
        :param target: [(1, 1), (2, 2), (3, 3), (4, 4)]  或者是单独的一个元组(4, 4) 第一个是组, 第二个是队伍
        :return:
        """
        if isinstance(target, tuple):
            target = [target]
        confirmed = bool(target)
        for group, team in target:
            group = int(group)
            team = int(team)
            if self.switch_soul_one(group, team) is not True:
                confirmed = False
        return confirmed

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

    def _soul_name_rows(self, rule):
        """完整名称及屏幕矩形；不使用公共 OCR 的单字兜底匹配。"""
        rows = []
        rx, ry, rw, rh = rule.roi
        for result in rule.detect_and_ocr(self.device.image):
            box = result.box
            x1, y1 = box.min(axis=0)
            x2, y2 = box.max(axis=0)
            # 边缘裁断的名字不能用于定位或点击。
            if x1 < 0 or y1 < 0 or x2 > rw or y2 > rh or x2 <= x1 or y2 <= y1:
                continue
            rows.append((result.ocr_text, (int(rx+x1), int(ry+y1),
                                          int(x2-x1), int(y2-y1))))
        return rows

    def _soul_list_top(self, rule, swipe, label):
        deadline = monotonic() + 20
        previous = None
        while monotonic() < deadline:
            self.screenshot()
            rows = self._soul_name_rows(rule)
            if rows and previous and len(rows) == len(previous) and all(
                    text == old_text and all(abs(a-b) <= 8 for a, b in zip(area, old_area))
                    for (text, area), (old_text, old_area) in zip(rows, previous)):
                return
            previous = rows or None
            self.swipe(swipe, 1)
            sleep(0.5)
        raise GameStuckError(f'御魂{label}列表回到顶部超时')

    def _find_soul_name(self, rule, name, forward, backward, label):
        """两张新截图位置稳定后返回当前帧坐标；丢失目标继续搜索。"""
        deadline = monotonic() + 30
        candidate = None
        previous = None
        direction = forward
        while monotonic() < deadline:
            self.screenshot()
            rows = self._soul_name_rows(rule)
            matches = [area for text, area in rows if text == name]
            if len(matches) == 1:
                area = matches[0]
                if candidate is not None and all(abs(a-b) <= 8 for a, b in zip(candidate, area)):
                    return area
                candidate = area
                sleep(0.35)
                continue
            candidate = None
            # 搜索到边界或错过目标时反向寻找，不停留在只重试点击的死循环。
            if rows and previous and len(rows) == len(previous) and all(
                    text == old_text and all(abs(a-b) <= 8 for a, b in zip(area, old_area))
                    for (text, area), (old_text, old_area) in zip(rows, previous)):
                direction = backward if direction is forward else forward
            previous = rows or None
            self.swipe(direction, 0.3)
            sleep(0.5)
        raise GameStuckError(f'御魂{label}查找超时：{name}')

    def switch_soul_by_name(self, groupName, teamName):
        SwitchSoul._current_switch_soul = '-'
        logger.hr('按名称切换御魂')
        self._soul_list_top(self.O_SS_GROUP_NAME, self.S_SS_GROUP_SWIPE_UP, '分组')
        area = self._find_soul_name(self.O_SS_GROUP_NAME, groupName,
                                    self.S_SS_GROUP_SWIPE_DOWN, self.S_SS_GROUP_SWIPE_UP, '分组')
        self.click(RuleClick(roi_front=area, roi_back=area, name='SS_GROUP_NAME'))
        logger.info(f'Select group {groupName}')
        sleep(0.5)
        self._soul_list_top(self.O_SS_TEAM_NAME, self.S_SS_TEAM_SWIPE_DOWN, '阵容')
        area = self._find_soul_name(self.O_SS_TEAM_NAME, teamName,
                                    self.S_SS_TEAM_SWIPE_UP, self.S_SS_TEAM_SWIPE_DOWN, '阵容')
        # 用同一帧完整名称的行位置直接点击应用按钮，不再次 OCR，也不修改共享素材。
        x, _, width, _ = self.I_SOU_CLICK_PRESENT.roi_front
        _, y, _, height = area
        button_area = (x, y, width, height)
        self.click(RuleClick(roi_front=button_area, roi_back=button_area, name='SS_TEAM_APPLY'))
        logger.info(f'已切换御魂 [{groupName},{teamName}]')
        return True

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
