# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep
import difflib

import copy
from module.atom.image import RuleImage

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from module.ocr.common import BoxedResult
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.Summon.summon import Summon
from tasks.DailyTrifles.assets import DailyTriflesAssets
from tasks.DailyTrifles.page import page_store_sign, page_mall_special, page_summon_store, page_shikigami_debris, page_guild_wish
from tasks.GameUi.page import page_summon, page_guild, page_friends, page_main
from tasks.Restart.back_up.back_up_log import BackUp
from tasks.Restart.big_god.sign_in import BigGodSignIn
from tasks.Restart.login import LoginHandler
from tasks.GameUi.page import win_list
from typing import Any, Optional, List, Callable

class ScriptTask(Summon, DailyTriflesAssets, GeneralBuff):
    """ 每日琐事 """

    def run(self):
        con = self.config.daily_trifles.trifles_config
        # 日志备份
        if con.enable_backup_log:
            logger.hr('日志备份', 3)
            BackUp().run()

        if con.enable_mail or con.enable_courtyard_affairs:
            login_handler = LoginHandler(config=self.config, device=self.device)
            if con.enable_mail:
                logger.hr('邮件领取', 3)
                self.ui_goto_page(page_main)
                login_handler.harvest(con.enable_mail)
            if con.enable_courtyard_affairs:
                logger.hr('庭院事务', 3)
                self.ui_goto_page(page_main)
                login_handler.courtyard_affairs()

        # 每日召唤
        if con.one_summon:
            logger.hr('每日召唤', 3)
            self.summon_one()
        # 召唤厕纸
        if con.broken_amulet:
            logger.hr('召唤厕纸', 3)
            self._broken_amulet(con.broken_amulet)
        # 式神集结
        if con.shikigami_massed:
            logger.hr('式神集结', 3)
            self.massed_run()
        if con.copper_box:
            # 召唤商店 铜铃礼包
            logger.hr('铜铃礼包', 3)
            self.run_summon_store()
        # 友情点 （现在已经可以通过庭院任务获取了）
        # if con.friend_love:
        #     logger.hr('友情点', 3)
        #     self.run_friend_love()
        # 吉闻
        if con.luck_msg:
            logger.hr('吉闻', 3)
            self.run_luck_msg()
        # 商店签到
        if con.store_sign:
            logger.hr('商店签到', 3)
            self.run_store_sign()
        # 购买寿司体力
        if con.buy_sushi_count > 0:
            logger.hr('购买寿司体力', 3)
            self.run_buy_sushi()
        # 招募寮成员
        if con.recruit_members:
            logger.hr('招募寮成员', 3)
            self.run_recruit_members()
        # 抽奖箱抽奖
        if con.lottery_box:
            logger.hr('抽奖箱抽奖', 3)
            self.check_lottery_box()
        # 召唤式神碎片
        if con.shikigami_debris:
            logger.hr('召唤式神碎片', 3)
            self.run_shikigami_debris()
        if self.config.daily_trifles.guild_donate.enable:
            self.run_guild_donate()

        # 大神签到
        if con.big_god_sign_in:
            logger.hr('大神签到', 3)
            try:
                BigGodSignIn().start_sign_in(str(self.config.script.device.serial))
            except Exception as e:
                logger.error(f"大神签到异常: {e}")
                self.push_notify(content=f"大神签到异常: {e}")

        self.set_next_run('DailyTrifles', success=True, finish=False)
        raise TaskEnd('DailyTrifles')

    def run_guild_donate(self):
        logger.hr('guild donate', 2)
        self.ui_goto_page(page_guild_wish)
        timeout_timer = Timer(2).start()
        while not timeout_timer.reached():
            self.screenshot()
            if self.appear(self.I_DT_GW_THANKS):
                self.ui_click(self.I_DT_GW_THANKS, self.I_DT_GW_THANKED, interval=0.8)
                timeout_timer.reset()
                continue
        self.appear_then_click(self.I_BACK_RED)
        donate_datas: list = [
            (self.config.daily_trifles.guild_donate.guild_member_list_v,
             lambda : self.switch_select(self.I_DT_GW_GUILD_MEMBER_SELECTED, self.I_DT_GW_FRIEND_SELECTED, self.I_DT_GW_SELECT_GUILD_MEMBER),
             self.config.daily_trifles.guild_donate.name_check),
            (self.config.daily_trifles.guild_donate.friend_list_v,
             lambda : self.switch_select(self.I_DT_GW_FRIEND_SELECTED, self.I_DT_GW_GUILD_MEMBER_SELECTED, self.I_DT_GW_SELECT_FRIEND),
             self.config.daily_trifles.guild_donate.name_check)
        ]
        all_done = True
        for name_list, switch_func, name_check in donate_datas:
            # 分别执行两个名单，前一个名单失败也不能跳过后一个名单。
            donate_ret = self.donate(name_list, switch_func, name_check)
            all_done = all_done and donate_ret
        if self.config.daily_trifles.guild_donate.auto_get_rewards:
            self.guild_donate_get_reward()

    def donate(self, name_list: List[str], switch_func: Callable, name_check: bool) -> bool:
        """执行碎片捐赠流程

        :param name_list: 待捐赠碎皮的名称列表
        :param switch_func: 切换好友/阴阳寮/...的方法
        :param name_check: 是否使用ocr检查用户名
        :return: 是否全部捐赠成功 (出现检索名称后为空或者碎皮不足都是False, 仅全部捐成功才是True)
        """
        all_done = True
        for name in name_list:
            switch_func()
            self.swipe(self.S_DT_GW_OPEN_SEARCH, interval=1.2)  # 向下滑动拉出搜索框
            # 从按照交换搜索切换到按名称搜索
            self.switch_select(self.I_DT_GW_SEARCH_BY_NAME, self.I_DT_GW_SEARCH_BY_SWAP, self.I_DT_GW_SELECT_BY_NAME)
            self.appear_then_click(self.I_DT_GW_CLEAR_SEARCH)  # 清除搜索框内容
            self.ui_click(self.C_DT_GW_INPUT_SEARCH, self.I_DT_GW_CONFIRM, interval=1.5)  # 点击搜索框
            self.click(self.C_DT_GW_CLICK_INPUT)  # 点击名称输入框
            # uiautomator2 通过 FastInputIME 传输 UTF-8 文本，并在必要时回退到 set_text
            logger.info(f'Inputting name using uiautomator2: {name}, waiting start and send')
            self.device.u2.send_keys(name, clear=True)
            self.ui_click_until_disappear(self.I_DT_GW_CONFIRM, interval=1.5)  # 点击确定
            donate_btn = self.I_DT_GW_DONATE
            if name_check:  # 若有多个相同前缀名称, 则需要取出一样的或最相近的名称
                name_roi = self.find_target_name(name)
                if name_roi is None:
                    logger.warning(f'{name} check failed, maybe not wish or not find')
                    all_done = False
                    continue
                # 设置赠与按钮back与对应name同一行
                donate_btn.roi_back = [name_roi[0]-5, name_roi[1] - 15, 850, 90]  # 设置赠与按钮back区域和对应name同一行
            self.I_DT_GW_FULL.roi_back = donate_btn.roi_back  # 设置已捐满标志back区域和赠与按钮同一行
            self.I_DT_GW_INSUFFICIENT.roi_back = donate_btn.roi_back  # 设置碎片不足标志back区域和赠与按钮同一行
            donate_ret = self.process_donate(donate_btn, name)
            all_done = all_done and donate_ret  # 有一次没成功则all_done永远False
        return all_done

    def process_donate(self, donate_btn: RuleImage, name: str) -> bool:
        """捐赠式神碎片
        TODO: 游戏有bug,搜索结束之后会突然神经展开全部寮友/好友,会有一瞬间识别到了好友,点击捐赠结果实际捐错人了

        :param name: 被捐方名称
        :param donate_btn: 赠与按钮
        :return: 捐赠是否成功(点击了捐赠/确定/识别到已满都认为成功)
        """
        timeout_timer = Timer(3).start()
        donated = False  # 判断是否已执行捐赠
        while not timeout_timer.reached():
            self.screenshot()
            if self.appear(self.I_DT_GW_SEARCH_EMPTY):
                logger.warning('Maybe not wish or not find, skip')
                if self.config.daily_trifles.guild_donate.notify_enable:
                    self.config.notifier.push(title='好友搜索失败', content=f'{name} 搜索失败, 没有搜索到对应用户, 无法捐赠')
                return False
            if not donated and self.appear_then_click(donate_btn, interval=2.5):
                timeout_timer.reset()
                # 点击后，等待所有弹窗消失（确认、奖励），然后重新定位
                post_click_timeout = Timer(3).start()
                while not post_click_timeout.reached():
                    self.screenshot()
                    # 处理确认弹窗
                    if self.appear(self.I_UI_SURE, interval=0.6):
                        self.ui_get_reward(self.I_UI_SURE, click_interval=1.5)
                        donated = True
                    # 如果没有弹窗了，退出子循环
                    if not self.appear(self.I_UI_REWARD) and not self.appear(self.I_UI_REWARD):
                        break
                if donated:
                    # 处理了弹窗，视为捐赠成功
                    logger.info(f'Donate success for {name}!')
                    return True
                else:
                    # 子循环结束后，重新定位目标行（因为如果被搜索到的玩家有多个，被赠与方被赠送满了就会下沉到最后位置）
                    new_roi = self.find_target_name(name)
                    if new_roi is None:
                        logger.warning(f'{name} disappeared after donation, skip')
                        return False
                    # 更新三个按钮的 ROI
                    new_roi_back = [new_roi[0] - 5, new_roi[1] - 15, 850, 90]
                    donate_btn.roi_back = new_roi_back
                    self.I_DT_GW_FULL.roi_back = new_roi_back
                    self.I_DT_GW_INSUFFICIENT.roi_back = new_roi_back
                    logger.info(f"Updated ROI after donation attempt: {new_roi_back}")
                    continue

            if self.appear(self.I_DT_GW_INSUFFICIENT, interval=0.6):
                logger.warning('Not enough fragment to donate, skip')
                if self.config.daily_trifles.guild_donate.notify_enable:
                    self.config.notifier.push(title='捐赠碎片不足', content=f'捐给{name}的碎片不足, 请上线查看')
                return False
            if self.appear(self.I_DT_GW_FULL, interval=0.6):
                logger.info(f'Donate success!')
                donated = True
        return donated

    def find_target_name(self, name) -> List[int]:
        """寻找目标名称
        :param name: 名称
        :return: [x, y, w, h]
        """
        timeout_timer = Timer(3).start()
        name_roi: List[int] = None
        # TODO: 这里只找了第一页, 若相似名称过多后续需要添加翻页继续找功能
        while not timeout_timer.reached():
            self.screenshot()
            if self.appear(self.I_DT_GW_SEARCH_EMPTY):  # 空的直接退出
                if self.config.daily_trifles.guild_donate.notify_enable:
                    self.config.notifier.push(title='好友搜索失败', content=f'没有搜索到对应用户 {name}, 无法捐赠')
                return None
            text_results = self.O_DT_GW_NAME.detect_and_ocr(self.device.image)
            mx_similarity = 0.5
            for result in text_results:
                if result.ocr_text == name:
                    return self.extract_roi(result)  # 名称一模一样则直接返回
                similarity = difflib.SequenceMatcher(None, result.ocr_text, name).ratio()
                if similarity > mx_similarity:
                    mx_similarity = similarity
                    name_roi = self.extract_roi(result)
            if name_roi is None:
                continue
            return name_roi  # 找到了直接退出
        return name_roi

    def extract_roi(self, result: BoxedResult) -> list[int]:
        """从ocr结果提取对应的roi坐标"""
        x = self.O_DT_GW_NAME.roi[0] + result.box[0, 0]
        y = self.O_DT_GW_NAME.roi[1] + result.box[0, 1]
        w, h = result.box[1, 0] - result.box[0, 0], result.box[2, 1] - result.box[0, 1]
        return [x, y, w, h]

    def guild_donate_get_reward(self):
        """领取捐赠碎片的奖励"""
        timeout_timer = Timer(3).start()
        has_reward = False
        while not timeout_timer.reached():
            self.screenshot()
            if self.appear(self.I_BACK_RED, interval=0.6):
                break
            if self.appear(self.I_DT_GW_DONATE_RECORD_RED):
                self.ui_click(self.I_DT_GW_DONATE_RECORD, self.I_BACK_RED, interval=1.2)
                has_reward = True
                continue
        if not has_reward:
            logger.info('No reward can get, exit')
            return
        timeout_timer.reset()
        while not timeout_timer.reached():
            self.screenshot()
            self.ui_reward_appear_click()
            if self.appear_then_click(self.I_UI_SURE, interval=0.6):
                continue
            if self.appear_then_click(self.I_DT_GW_DONATE_RECORD_THANKS, interval=1.5):  # 受赠界面的一键感谢
                timeout_timer.reset()
                continue
            if self.appear(self.I_DT_GW_DONATE_RED, interval=2.5):  # 赠予界面的一键领取
                self.ui_click(self.I_DT_GW_GIVE, self.I_DT_GW_ONE_COLLECT)
                self.appear_then_click(self.I_DT_GW_ONE_COLLECT, interval=0.6)
                timeout_timer.reset()
                continue
        self.ui_click_until_disappear(self.I_BACK_RED)

    def switch_select(self, target: RuleImage, other: RuleImage, select: RuleImage):
        """切换选中的元素"""
        while True:
            self.screenshot()
            if self.appear(target):
                break
            if self.appear_then_click(select, interval=0.6):
                continue
            if self.appear_then_click(other, interval=1.8):
                continue

    def run_shikigami_debris(self):
        self.ui_goto_page(page_shikigami_debris)
        self.ui_click(self.I_PAGE_SHIKIGAMI_DEBRIS, self.I_UI_SURE)
        self.ui_click_until_disappear(self.I_UI_SURE)

    def check_lottery_box(self):
        self.ui_goto_page(page_guild)
        while 1:
            self.screenshot()
            if self.wait_until_appear_then_click(self.I_LOTTERY_BOX, wait_time=2):
                if self.wait_until_appear(self.I_LOTTERY_BOX_PAGE, wait_time=5):
                    break
            else:
                logger.info(f'未发现抽奖箱')
                return

        while 1:
            self.screenshot()
            if self.ui_reward_appear_click():
                continue
            # 获得奖励
            cu, re, total = self.ocr_result(self.O_LOTTERY_NUMBER)
            if cu + re == total and cu != 0:
                logger.info(f'抽奖次数: [{cu}]')
                self.swipe(self.S_SWIPE_LOTTERY_BOX, interval=5)
                sleep(5)
            else:
                logger.info(f'没有可以抽奖的次数')
                return

    def run_summon_store(self):
        self.ui_goto_page(page_summon_store)
        timer = Timer(3)
        timer.start()
        while 1:
            if timer.reached():
                logger.info('未出现召唤商店')
                return
            self.screenshot()
            if self.appear(self.I_SUMMON_STORE_FREE_OVER):
                break
            if self.appear_then_click(self.I_SUMMON_STORE_FREE_1, interval=1):
                timer.reset()
                continue
            if self.appear_then_click(self.I_SUMMON_STORE_FREE, interval=1):
                sleep(1)
                timer.reset()
                continue
            if self.appear_then_click(self.I_SUMMON_STORE_LUCKY, interval=1):
                timer.reset()
                continue

        click_count = 0
        timer.reset()
        clicked = False
        while click_count < 5:
            if timer.reached():
                logger.info('未点击召唤商店')
                break
            self.screenshot()
            if self.ui_reward_appear_click():
                click_count = 0
            if self.appear(self.I_FREE_3_OVER) and self.appear(self.I_FREE_2_OVER) and self.appear(self.I_FREE_1_OVER):
                break
            for btn in [self.I_FREE_1, self.I_FREE_2, self.I_FREE_3]:
                if self.appear_then_click(btn, interval=1):
                    timer.reset()
                    click_count += 1
                    clicked = True
                    break
        if clicked:
            self.save_image(wait_time=0, task_name='铜铃礼包')

    def massed_run(self):
        self.ui_goto_page(page_summon)
        if not self.appear(self.I_MASSED):
            return

        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_MASSED, interval=1):
                continue
            if self.appear_then_click(self.I_AFTER_ON, interval=1):
                break
            if self.appear(self.I_BATTLE):
                break
            x, y = self.I_AFTER_ON.coord()
            self.device.click(x, y)

        click_count = 0
        while click_count <= 3:
            self.screenshot()
            if self.appear_then_click(self.I_MASSED, interval=1):
                continue
            if self.appear_then_click(self.I_AFTER_ON, interval=1):
                continue
            if self.appear_then_click(self.I_BATTLE, interval=1):
                self.device.stuck_record_add('BATTLE_STATUS_S')
                click_count += 1
                continue
            if self.appear_then_click(self.I_CLICK_ANY_POSITION, interval=1):
                continue
            if self.appear_then_click(win_list, interval=1):
                click_count = 0
                continue

    def run_luck_msg(self):
        self.ui_goto_page(page_friends)
        while 1:
            self.screenshot()
            if self.appear(self.I_LUCK_TITLE):
                break
            if self.appear_then_click(self.I_FRIENDSHIP_UP, interval=1):
                continue
            if self.appear_then_click(self.I_LUCK_MSG, interval=1):
                continue
        logger.info('开始查看吉闻')
        check_timer = Timer(5)
        check_timer.start()
        while 1:
            self.screenshot()

            if self.appear_then_click(self.I_CLICK_BLESS, interval=1):
                continue
            if self.appear_then_click(self.I_ONE_CLICK_BLESS, interval=1):
                continue
            if self.ui_reward_appear_click():
                logger.info('领取奖励 of luck msg')
                break
            if check_timer.reached():
                self.save_image(content="收取吉闻超时", wait_time=0, image_type=True, push_flag=True)
                logger.warning('没有任何吉闻')
                break

    def run_friend_love(self):
        self.ui_goto_page(page_friends)
        while 1:
            self.screenshot()
            if self.appear(self.I_L_LOVE):
                break
            if self.appear_then_click(self.I_FRIENDSHIP_UP, interval=1):
                continue
            if self.appear_then_click(self.I_L_FRIENDS, interval=1):
                continue
            if self.appear_then_click(self.I_L_FRIENDS_SELECT, interval=1):
                continue
        logger.info('开始好友点赞')
        check_timer = Timer(5)
        check_timer.start()
        while 1:
            self.screenshot()

            if self.appear_then_click(self.I_L_COLLECT, interval=1):
                continue
            if self.ui_reward_appear_click():
                logger.info('领取奖励 of friend love')
                break
            if check_timer.reached():
                self.save_image(content="收取友情点超时", wait_time=0, image_type=True, push_flag=True)
                logger.warning('没有任何点赞')
                break

    def run_store_sign(self):
        self.ui_goto_page(page_store_sign)
        timer = Timer(5)
        timer.start()
        while 1:
            if timer.reached():
                self.save_image(content="每日签到超时", push_flag=True, wait_time=0, image_type=True)
                return
            self.reject_invite()
            self.screenshot()
            if self.appear(self.I_GIFT_SIGN):
                break
            if self.appear_then_click(self.I_GIFT_RECOMMEND, interval=1):
                continue
        logger.info('进入商店签到')
        sleep(1)  # 等个动画
        self.reject_invite()
        self.screenshot()
        if not self.appear(self.I_GIFT_SIGN):
            logger.warning('没有礼包签到')
            self.save_image(content="未发现每日签到", push_flag=True, wait_time=0, image_type=True)
            return

        if self.ui_get_reward(self.I_GIFT_SIGN, click_interval=2.5):
            logger.info('领取奖励 of gift sign')

    def run_buy_sushi(self):

        # 进入Special
        self.ui_goto_page(page_mall_special)

        def detect_buy_count(base_element) -> (int, int):
            # 返回count,price
            MAX_PRICE = 9999
            MAX_COUNT = 9999
            roi = copy.deepcopy(base_element.roi_front)
            roi[0] = roi[0] + roi[2]
            roi[1] = roi[1] + roi[3] - 30
            roi[2] = 60
            roi[3] = 30
            self.O_STORE_SUSHI_PRICE.roi = roi
            _price = self.O_STORE_SUSHI_PRICE.detect_text(self.device.image)
            # 保守策略，避免OCR错误购买
            try:
                _price = int(_price)
            except Exception as e:
                _price = MAX_PRICE

            if _price < 60:
                return 0, MAX_PRICE
            _count = (_price - 60) / 20
            return _count, _price

        roi = None
        # 购买体力
        while 1:
            self.screenshot()
            # count, price = detect_buy_count(roi)
            # if count >= self.config.model.daily_trifles.trifles_config.buy_sushi_count:
            #     break
            if self.appear(self.I_STORE_COST_TYPE_JADE):
                count, price = detect_buy_count(self.I_STORE_COST_TYPE_JADE)
                if count >= self.config.daily_trifles.trifles_config.buy_sushi_count:
                    break
                self.ui_click_until_disappear(self.I_STORE_COST_TYPE_JADE, interval=2)
                logger.info(f"使用{price}勾玉购买体力")
                continue

            if self.appear(self.I_SPECIAL_SUSHI):
                # 此处确定当前购买体力所需勾玉数量的位置,用于后续识别
                count, price = detect_buy_count(self.I_SPECIAL_SUSHI)
                if count >= self.config.daily_trifles.trifles_config.buy_sushi_count:
                    break
                self.ui_click(self.I_SPECIAL_SUSHI, stop=self.I_STORE_COST_TYPE_JADE, interval=2)
                continue
        return

    def run_recruit_members(self):
        self.ui_goto_page(page_guild)
        flush_count = 0
        timer = Timer(5)
        timer.start()
        while flush_count < 5:
            self.screenshot()
            if timer.reached():
                self.push_notify(content="招募寮成员超时，或没有管理权限")
                return
            if self.appear_then_click(self.I_POSTS):
                timer.reset()
                continue
            if self.appear_then_click(self.I_MEMBER_FLUSH, interval=1):
                flush_count += 1
                timer.reset()
                continue
            if self.appear_then_click(self.I_MEMBER_ADD, interval=0.5):
                timer.reset()
                continue
            if self.appear_then_click(self.I_RECRUIT_MEMBERS, interval=1):
                timer.reset()
                continue
            if self.appear_then_click(self.I_GUILD_MANAGEMENT_1, interval=1):
                timer.reset()
                continue
            if self.appear_then_click(self.I_GUILD_MANAGEMENT, interval=1):
                continue
            if self.appear_then_click(self.I_GUILD_INFO, interval=1):
                timer.reset()
                continue
        logger.info('进入招募成员')

    def _broken_amulet(self, num: int):
        """

        :param num:
        :return:
        """
        if num <= 0:
            logger.warning('没有碎符')
            return

        def click_confirm():
            self.wait_until_appear(self.I_BM_CONFIRM)
            while 1:
                self.screenshot()
                if not self.appear(self.I_BM_CONFIRM):
                    break
                else:
                    self.appear_then_click(self.I_BM_CONFIRM, interval=1)
            logger.info('退出碎符')

        logger.hr('碎符')
        self.ui_goto_page(page_summon)
        self.screenshot()
        number = self.O_BA_AMOUNT_1.ocr(self.device.image)
        if number == 0:
            logger.warning('没有碎符')
            return
        num = min(number, num)
        logger.info(f'碎符数量: {number}')
        count = 0
        self.wait_until_appear(self.I_BM_ENTER)
        while 1:
            self.screenshot()
            if not self.appear(self.I_BM_ENTER):
                break
            if self.appear_then_click(self.I_BM_ENTER, interval=1):
                continue
        count += 10
        logger.info('进入碎符')
        while 1:
            self.screenshot()
            sleep(0.5)

            if not self.appear(self.I_BM_CONFIRM):
                continue
            if count >= num:
                logger.info(f'碎符完成: {count}')
                click_confirm()
                break
            cu, re, total = self.O_BA_AMOUNT_2.ocr(self.device.image)
            if cu <= 10 and total == 10:
                logger.info(f'碎符计数: {count}. 当前: {cu}. 总计: {total}')
                click_confirm()
                break
            if self.appear_then_click(self.I_BM_AGAIN, interval=1):
                logger.info(f'碎符计数: {count}. 当前: {cu}')
                self.device.click_record_clear()
                count += 10
                continue


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)

    # t.run()
    t.run_guild_donate()
