# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep
from copy import copy

from collections import deque
from module.atom.ocr import RuleOcr
from module.atom.base_atom import BaseAtom
from module.base.decorator import run_once
from module.base.timer import Timer
from module.exception import (GameNotRunningError, GamePageUnknownError, GameStuckError)
from module.logger import logger
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.page import Page, PageRegistry
from tasks.Hyakkiyakou.assets import HyakkiyakouAssets
from tasks.Restart.assets import RestartAssets
from tasks.SixRealms.assets import SixRealmsAssets
from tasks.base_task import BaseTask
from tasks.GameUi.page import win_list, false_list
from tasks.GlobalGame.assets import GlobalGameAssets


class GameUi(BaseTask, GameUiAssets, GeneralBattleAssets):
    ui_current: Page = None
    ui_close = [GlobalGameAssets.I_UI_CONFIRM, GlobalGameAssets.I_UI_SURE,
                GameUiAssets.I_CANCEL,
                win_list, false_list, GlobalGameAssets.I_REWARD,
                SixRealmsAssets.I_EXIT_SIXREALMS,
                GameUiAssets.I_BACK_RED, GameUiAssets.I_BACK_BLUE, GameUiAssets.I_BACK_YELLOW,
                GeneralBattleAssets.I_EXIT_OLD, GeneralBattleAssets.I_EXIT,
                GameUiAssets.I_SKIP_BUTTON,
                RestartAssets.I_HARVEST_CHAT_CLOSE,
                HyakkiyakouAssets.I_HEND
                ]

    def __init__(self, config, device=None):
        super().__init__(config, device)
        # Global pages and each task's explicitly imported page module register
        # themselves. Scanning every folder also executes leftover open-core
        # navigator modules, which use a different Page API and registry.

    @property
    def ui_pages(self) -> list[Page]:
        return PageRegistry.all()

    def ui_page_appear(self, page: Page, skip_first_screenshot: bool = True, interval: float = None):
        """
        判断当前页面是否为page
        """
        self.maybe_screenshot(skip_first_screenshot)
        return self.appear(page.check_button, interval)

    def ui_wait_until_appear(self, page: Page, timeout: float = 5, interval: float = 0.5,
                             skip_first_screenshot: bool = True) -> bool:
        """
        等待页面出现
        :param page: 等待的页面
        :param timeout: 超时时间
        :param interval: 检查间隔时间
        :param skip_first_screenshot:
        :return: 页面出现返回True, 否则返回False
        """
        logger.attr("等待页面", page)
        timeout_timer = Timer(timeout).start()
        while not timeout_timer.reached():
            if self.ui_page_appear(page, skip_first_screenshot, interval=interval):
                return True
            skip_first_screenshot = False
        return False

    def ui_get_current_page(self, skip_first_screenshot=False) -> Page:
        """
        获取当前页面
        :param skip_first_screenshot:
        :return:
        """

        @run_once
        def app_check():
            if not self.device.app_is_running():
                raise GameNotRunningError("游戏未运行")

        @run_once
        def minicap_check():
            if self.config.script.device.control_method == "uiautomator2":
                self.device.uninstall_minicap()

        @run_once
        def rotation_check():
            self.device.get_orientation()

        timeout = Timer(15, count=20).start()
        while 1:
            self.maybe_screenshot(skip_first_screenshot)
            skip_first_screenshot = False
            # 如果10S还没有到底，那么就抛出异常
            if timeout.reached():
                break
            # Known pages
            for page in self.ui_pages:
                if not page.check_button:
                    continue
                if self.ui_page_appear(page=page, interval=None):
                    logger.attr("当前页面", page)
                    self.ui_current = page
                    return page
            # Try to close unknown page
            if self.try_close_unknown_page():
                timeout = Timer(15, count=20).start()
                sleep(0.5)
            else:
                app_check()
        # Unknown page, need manual switching
        logger.warning("未知的UI页面")
        # logger.attr("截图方式", self.config.script.device.screenshot_method)
        # logger.attr("控制方式", self.config.script.device.control_method)
        # logger.warning(f"支持的页面: {[str(page) for page in self.ui_pages]}")
        logger.critical("请在探索页面, 启动脚本")
        raise GamePageUnknownError

    def ui_goto(self, destination: Page, confirm_wait=0, skip_first_screenshot=True, timeout: int = 60) -> bool:
        """
        Args:
            destination (Page):
            confirm_wait:
            skip_first_screenshot:
        :return: find destination page or timeout reached
        """
        # 如果当前页面就是目标页面，直接返回
        if self.ui_current == destination:
            return True

        logger.attr("UI前往页面", destination)
        # 初始化
        timeout_timer = Timer(timeout).start()
        confirm_timer = Timer(confirm_wait, count=int(confirm_wait // 0.5)).start()
        close_unknown_timer = Timer(6).start()
        # 构建路径映射
        path_dict = self.build_reverse_path_dict(destination)
        courtyard_attempts = {}

        found = False
        while not timeout_timer.reached():
            if found:
                confirm_timer.wait()
                return True
            confirm_timer.reset()
            path = path_dict.get(self.ui_current, None)
            # 找不到路径则重新获取页面重试
            if not path:
                self.ui_get_current_page()
                continue
            # logger.attr(f"Current page", self.ui_current)
            show_paths: str = ' -> '.join([str(p) for p in path])
            logger.attr("路径", show_paths)
            # 遍历路径
            found = self._execute_path(path, timeout_timer, courtyard_attempts)
            if not found:
                if close_unknown_timer.reached_and_reset():
                    self.try_close_unknown_page(skip_screenshot=False)
                    self.ui_current = None
        else:
            logger.error(f'⚠️ 不能到达 [{destination}], 超时 [{timeout}s]')
        return False

    def ui_goto_page(self, page: Page, confirm_wait=0, skip_first_screenshot=True, timeout: int = 60) -> bool:
        """
        前往指定page，自动调用获取当前页面方法，其他参数同ui_goto
        """
        self.ui_get_current_page()
        return self.ui_goto(page, confirm_wait, skip_first_screenshot, timeout)

    def ui_button_interval_reset(self, button):
        """
        Reset interval of some button to avoid mistaken clicks

        Args:
            button (Button):
        """
        if getattr(button, 'name', None) and button.name in self.interval_timer:
            self.interval_timer[button.name].reset()

    def build_reverse_path_dict(self, destination: Page) -> dict[Page, list[Page]]:
        """
        构建从每个页面到目标页面的最短路径（反向 BFS）

        Returns:
            dict[Page, list[Page]] -> {start_page: [page1, ...destinationPage], ...}
        """
        paths = {destination: [destination]}
        queue = deque([destination])
        while queue:
            cur = queue.popleft()
            for page in self.ui_pages:
                if page not in paths and cur in page.links:
                    # page -> cur
                    paths[page] = [page] + paths[cur]
                    queue.append(page)
        return paths

    def build_reverse_paths(self, destination: Page) -> list[tuple[Page, list[Page]]]:
        """
        构建从每个页面到目标页面的最短路径（反向 BFS）
        路径从短到长排序

        Returns:
            [(start_page, [page1, ...destinationPage]), ...]
        """
        paths = self.build_reverse_path_dict(destination)
        # 转换成列表并按路径长度排序, 短到长
        sorted_paths = sorted(paths.items(), key=lambda kv: len(kv[1]))
        return sorted_paths

    def try_close_unknown_page(self, skip_screenshot: bool = True):
        """
        尝试关闭未知界面
        :return: 执行了关闭返回True, 否则False
        """
        self.maybe_screenshot(skip_screenshot)
        # timer = Timer(None).start()
        # logger.warning('⚠️ 未知页面, 尝试点击UI按钮, 切换到支持的页面')
        for close in self.ui_close:
            if self.appear_then_click(close, interval=1.5):
                # logger.info(f'⚠️ [{timer.current():.1f}s] 点击按钮 {close} 在 {self.ui_current} 页')
                return True
        # logger.warning('❌ 当前页没有可点击的UI按钮')
        return False

    def _execute_path(self, path: list, timeout_timer, courtyard_attempts=None):
        """
        执行路径
        :param path: currentPage,page1,page2,...,destinationPage
        :param timeout_timer: 超时定时器
        :return: currentPage==destinationPage
        """
        if courtyard_attempts is None:
            courtyard_attempts = {}
        for i, current_page in enumerate(path):
            if timeout_timer.reached():
                return False
            # 当前页不等于路径中对应页, 尝试下一页
            if self.ui_current != current_page:
                continue
            self.run_additional(current_page, interval=0.6, skip_first_screenshot=False)
            # 如果已经是最后一页，不再跳转
            if i == len(path) - 1:
                if len(path) == 1:
                    logger.info(f'已到达页面 {current_page}')
                break
            next_page = path[i + 1]
            logger.attr('页面切换', f'{current_page} -> {next_page}')
            # 获取页面跳转操作 - 现在返回按钮列表
            buttons = current_page.links.get(next_page, [])
            if not buttons:
                logger.error(f"❌ 从 {current_page} 到 {next_page} 无链接")
                continue

            # 尝试所有可能的按钮
            operated = False
            from tasks.GameUi.page import page_main, page_pet
            pet_entrance = current_page == page_main and next_page == page_pet
            if pet_entrance:
                # 统计整轮识别尝试，而非仅统计成功点击的兜底；入口一直
                # 未命中时也必须退出，不能反复收起确认直到外层超时。
                pet_attempt = courtyard_attempts.get('pet_navigation', 0)
                if pet_attempt >= 3:
                    raise GameStuckError('宠物屋导航失败：三次入口定位或页面确认均未成功')
                courtyard_attempts['pet_navigation'] = pet_attempt + 1
                if not self._prepare_pet_entrance(timeout_timer):
                    raise GameStuckError('宠物屋导航中止：未确认右侧灯笼收起，请检查小纸人识别日志及错误截图')
                buttons = [None]
            for button in buttons:
                if timeout_timer.reached():
                    return False

                # 尝试点击当前按钮
                if pet_entrance:
                    clicked = self._try_pet_entrance(timeout_timer)
                else:
                    clicked = self.appear_then_operate(button, interval=0.5, skip_first_screenshot=False)
                if not clicked:
                    continue
                operated = True

                # 等待页面跳转完成
                max_wait_timer = Timer(6).start()
                page_arrived = False

                while not max_wait_timer.reached():
                    if timeout_timer.reached():
                        return False
                    if self.ui_wait_until_appear(next_page, timeout=3, skip_first_screenshot=False):
                        logger.info(f'✅ [{max_wait_timer.current():.1f}s] 到达页面 {next_page}')
                        self.ui_current = next_page
                        page_arrived = True
                        break
                    sleep(0.2)  # 短暂等待

                if page_arrived:
                    # 成功跳转到下一页，跳出按钮循环
                    break

            if not operated and self._try_courtyard_fallback(
                    current_page, next_page, timeout_timer, courtyard_attempts):
                self.ui_current = next_page
            if (pet_entrance and self.ui_current != next_page
                    and courtyard_attempts['pet_navigation'] >= 3):
                raise GameStuckError('宠物屋导航失败：三次入口定位或页面确认均未成功')

        return self.ui_current == path[-1]

    def _prepare_pet_entrance(self, timeout_timer):
        """仅在展开时点击小纸人，连续两帧未检测到展开即视为收起。"""
        from tasks.GameUi.page import page_main

        expanded = copy(self.I_PAPER_DOLL_EXPANDED)
        collapsed = copy(self.I_PAPER_DOLL_CLOSE)
        expanded.roi_front = list(expanded.roi_front)
        collapsed.roi_front = list(collapsed.roi_front)
        wait = Timer(4).start()
        clicked = False
        confirmed = 0
        previous_expanded = None
        while not wait.reached() and not timeout_timer.reached():
            self.device.screenshot()
            image = self.device.image
            if image.shape[:2] != (720, 1280):
                logger.warning(f'宠物屋小纸人：截图尺寸异常 {image.shape}')
                return False
            at_main = self.ui_page_appear(page_main)
            popup = self.appear([GlobalGameAssets.I_UI_CONFIRM, GlobalGameAssets.I_UI_SURE,
                                 self.I_CANCEL, RestartAssets.I_LOGIN_SCROOLL_CLOSE])
            is_expanded = expanded.match(image)
            is_collapsed = collapsed.match(image)
            logger.info(f'宠物屋小纸人：庭院={at_main}, 弹窗={popup}, 已点击={clicked}, '
                        f'展开={is_expanded}/{expanded.max_val:.3f}, ROI={tuple(expanded.roi_front)}, '
                        f'收起={is_collapsed}/{collapsed.max_val:.3f}, ROI={tuple(collapsed.roi_front)}')
            if not at_main or popup:
                logger.warning('宠物屋小纸人：页面变化或弹窗遮挡，停止入口点击')
                return False
            # 收起素材也会随动画波动，只作诊断；以展开状态消失为准。
            if not is_expanded:
                previous_expanded = None
                confirmed += 1
                if confirmed >= 2:
                    logger.info('宠物屋小纸人：连续两帧未检测到展开，视为灯笼已收起')
                    return True
            else:
                confirmed = 0
                if not clicked:
                    roi = tuple(expanded.roi_front)
                    if previous_expanded is not None and all(
                            abs(a - b) <= 3 for a, b in zip(previous_expanded, roi)):
                        if timeout_timer.reached():
                            return False
                        # 展开素材仅保留头部，排除摆动的耳饰、身体及背景。
                        head = (roi[0] + 7, roi[1] + 3, 14, 14)
                        x, y = expanded.coord_list(head)
                        self.device.click(x, y, control_name=expanded.name)
                        logger.info(f'宠物屋小纸人：尝试点击头部 ({x}, {y})，等待灯笼收起确认')
                        clicked = True
                    previous_expanded = roi
            sleep(0.35)
        logger.warning('未确认庭院右侧灯笼已收起，暂不点击宠物屋')
        return False

    def _try_pet_entrance(self, timeout_timer):
        from tasks.GameUi.page import page_main, courtyard_entrances

        previous = None
        for _ in range(2):
            if timeout_timer.reached():
                return False
            self.device.screenshot()
            if not self.ui_page_appear(page_main):
                return False
            if self.appear([GlobalGameAssets.I_UI_CONFIRM, GlobalGameAssets.I_UI_SURE,
                            self.I_CANCEL, RestartAssets.I_LOGIN_SCROOLL_CLOSE]):
                return False
            diagnostics = []
            current = courtyard_entrances.match_pet(self.device.image, diagnostics=diagnostics)
            candidates = sorted(diagnostics, key=lambda candidate: candidate[1], reverse=True)[:3]
            logger.info(f'宠物屋入口识别：候选(名称,分数,位置)={candidates}, '
                        f'结果={None if current is None else (current[0], tuple(current[1].roi_front))}')
            if current is None:
                return False
            if previous is None:
                previous = (current[0], tuple(current[1].roi_front))
                sleep(0.35)
                continue
            skin, roi = previous
            if current[0] != skin or any(abs(a - b) > 3 for a, b in zip(roi, current[1].roi_front)):
                logger.warning('宠物屋入口识别：两帧皮肤或位置变化，取消点击')
                return False
        if timeout_timer.reached():
            return False
        button = current[1]
        x, y = button.coord_list(button.roi_front)
        self.device.click(x, y, control_name=button.name)
        return True

    def _try_courtyard_fallback(self, current_page, destination, timeout_timer, attempts):
        from tasks.GameUi.page import (page_main, page_exploration, page_town,
                                       page_pet, page_summon, courtyard_entrances)

        kinds = {page_exploration: 'I_MAIN_GOTO_EXPLORATION',
                 page_town: 'I_MAIN_GOTO_TOWN', page_pet: 'I_PET_HOUSE',
                 page_summon: 'I_MAIN_GOTO_SUMMON'}
        kind = kinds.get(destination)
        if current_page != page_main or kind is None or attempts.get(kind, 0) >= 3:
            return False

        def ready():
            if timeout_timer.reached():
                return False
            self.device.screenshot()
            if not self.ui_page_appear(page_main):
                return False
            return not self.appear([GlobalGameAssets.I_UI_CONFIRM, GlobalGameAssets.I_UI_SURE,
                                    self.I_CANCEL, RestartAssets.I_LOGIN_SCROOLL_CLOSE])

        if not ready():
            return False
        first = courtyard_entrances.infer(self.device.image, kind)
        if first is None:
            return False
        sleep(0.35)
        if not ready():
            return False
        if courtyard_entrances.infer(self.device.image, kind) != first:
            return False
        if timeout_timer.reached():
            return False
        skin, roi = first
        attempts[kind] = attempts.get(kind, 0) + 1
        logger.info(f'庭院交叉定位: skin={skin}, target={kind}, attempt={attempts[kind]}')
        # 沿用图像点击的随机落点算法，使用保存的原始区域而非匹配后的坐标。
        x, y = BaseAtom().coord_list(roi)
        self.device.click(x, y, control_name=f'Courtyard_{kind}')
        # 点击只代表尝试；目标页识别成功后才更新导航状态。
        return self.ui_wait_until_appear(destination, timeout=6, skip_first_screenshot=False)

    def run_additional(self, page: Page, interval: float = None, skip_first_screenshot: bool = True):
        """执行页面附加操作"""
        if not page.additional:
            return
        for btn in page.additional:
            if self.appear_then_operate(btn, interval=interval, skip_first_screenshot=skip_first_screenshot):
                logger.info(f'页面 {page} 附加操作 {btn} 已点击')
                skip_first_screenshot = False

    def appear_then_operate(self, targets, interval: float = None, skip_first_screenshot: bool = True):
        """
        出现对应目标执行操作(点击图像, 滑动列表至array第一个元素并点击, 点击OCR, 点击)
        :param targets: 目标
        :param interval: 间隔
        :param skip_first_screenshot: 是否跳过首次截图
        :return: 是否成功操作
        """
        timer = Timer(interval).start()
        targets = [targets] if not isinstance(targets, (list, tuple)) else targets
        while 1:
            if timer.reached():
                return False
            self.maybe_screenshot(skip_first_screenshot)

            match_results = []
            for item in targets:
                # 自动兼容嵌套
                if isinstance(item, RuleOcr):
                    if self.ocr_appear_click(item, interval=0.5):
                        return True
                elif item.match(self.device.image):
                    match_results.append((item, item.max_val))
                    if item.max_val > 0.9:
                        break

            if match_results:
                best = max(match_results, key=lambda x: x[1])[0]
                if self.appear_then_click(best, interval=0.5):
                    return True

    def ui_goto_active(self, active: str = ''):
        """
        跳转到指定的活动页面
        参数:
            active (str): 要跳转的目标活动名称，默认为空字符串
        返回值:
            bool: 成功点击目标活动时返回True
        """
        if active == '':
            logger.warning('❌指定的活动页面未传值!')
            return False
        self.ui_goto_page(page_all_active)
        self.O_OCR_ACTIVE.keyword = active
        while 1:
            self.screenshot()
            if self.ocr_appear_click(self.O_OCR_ACTIVE):
                return True
            else:
                sleep(1)


if __name__ == '__main__':
    from module.config.config import Config
    from tasks.GameUi.page import PageRegistry, page_all_active
    from tasks.GameUi.page import page_main, page_summon, page_exploration, page_pet, page_town, page_shikigami_records

    c = Config('切换账号')
    game = GameUi(config=c)
    # print(len(game.ui_pages))
    # for page in game.ui_pages:
    #     print(page)
    # game.ui_goto_page(page_main)
    # game.ui_goto_page(page_awake_zones)
    while 1:
        game.ui_goto_page(page_pet)

        game.ui_goto_page(page_summon)
        game.ui_goto_page(page_town)

        game.ui_goto_page(page_shikigami_records)
        game.ui_goto_page(page_exploration)
        game.ui_goto_page(page_main)

    # game.ui_goto_active('版本活动')
