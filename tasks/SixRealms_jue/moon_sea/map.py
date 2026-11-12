from module.logger import logger
from module.exception import GameStuckError
from time import monotonic
from tasks.SixRealms_jue.moon_sea.skills import MoonSeaSkills
from cached_property import cached_property
from tasks.GameUi.assets import GameUiAssets


class MoonSeaMap(MoonSeaSkills):
    priority_queue = [[0, 3, 1, 5, 4, 2], [0, 1, 5, 3, 4, 2]]  # 两种优先级方案

    @cached_property
    def island_list(self):
        return [
            GameUiAssets.I_CANCEL,
            self.I_SHENMI,
            self.I_HUNDUN,
            self.I_ZHAN,
            self.I_XING,
            self.I_NINGXI
        ]

    def enter_island(self):
        self.screenshot()
        # 技能页的暗色图案会误匹配小岛模板，必须先确认地图且无技能遮挡。
        if self.strengthening_appear() or self.appear(self.I_SKILL_REFRESH):
            return None
        if self.appear_then_click(GameUiAssets.I_CANCEL, interval=1):
            return True
        if not self.in_main():
            return None
        priority = 0 if self.cnt_skill101 < 1 and self.cnt_skillpower < 4 else 1
        for index in self.priority_queue[priority][1:]:  # 取消弹窗已在地图确认前处理。
            button = self.island_list[index]
            if self.appear(button):
                return self._enter_island(button)
        return None

    def _enter_island(self, button):
        deadline = monotonic() + 15
        attempts = 0
        while monotonic() < deadline:
            if self.strengthening_appear() or self.appear(self.I_SKILL_REFRESH):
                return True  # 交回主循环优先处理技能，禁止点击遮挡后的地图。
            if not self.in_main():
                return True
            if attempts < 3 and self.appear_then_click(button, interval=1):
                attempts += 1
            self.screenshot()
        raise GameStuckError('六道觉进入岛屿失败（最多点击3次，限时15秒）')

    def activate_store(self) -> bool:
        """
        最后打boss前面激活一次商店买东西
        @return: 有钱够就是True
        """
        if self.cnt_skill101 >= 1:
            # 如果轰雷就不召唤
            return False
        self.screenshot()
        if not self.appear_rgb(self.I_M_STORE_ACTIVITY):
            return False
        cnt_act = 0
        logger.info('激活商店')
        while 1:
            self.screenshot()
            if self.appear(self.I_UI_SURE):
                self.ui_click_until_disappear(self.I_UI_SURE, interval=2)
                break
            if cnt_act >= 3:
                logger.warning('商店未激活')
                return False
            if self.appear_then_click(self.I_M_STORE_ACTIVITY, interval=1.5):
                cnt_act += 1
                continue
        return True


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = MoonSeaMap(c)
    # t.screenshot()
    # t.device.image = load_image(r'C:\Users\Ryland\Desktop\Desktop\34.png')
    # match = re.search(r'\d{1,2}', '<17回合后迎战月读')
    # if match:
    #     isl_num = int(match.group())
    #     print(isl_num)
