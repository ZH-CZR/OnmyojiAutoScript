# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

import re
from cached_property import cached_property
from datetime import datetime
from module.atom.image import RuleImage
from module.base.timer import Timer
from module.exception import GameStuckError, TaskEnd
from module.logger import logger
from tasks.Component.Costume.config import MainType
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.GameUi.page import page_main, page_exploration
from tasks.Secret.script_task import ScriptTask as SecretScriptTask
from tasks.WantedQuests.assets import WantedQuestsAssets
from tasks.WantedQuests.config import CooperationType, CooperationSelectMask
from typing import List

""" 悬赏封印 """


class ScriptTask(SecretScriptTask, GeneralInvite, WantedQuestsAssets):
    # 定义检查次数
    play_count = 0
    secret_layer = {"柒", "捌", "玖", "拾", "番外", "七", "八", "九", "十", "7", "8", "9", "10"}

    def run(self):

        con = self.config.wanted_quests

        switch_souled = False
        while 1:
            if not self.pre_work():
                # 无法完成预处理 很有可能你已经完成了悬赏任务
                logger.warning('你可能已完成悬赏任务')
                self.next_run()
                raise TaskEnd

            if not switch_souled:
                if con.switch_soul.enable:
                    self.run_switch_soul(con.switch_soul.switch_group_team)
                if con.switch_soul.enable_switch_by_name:
                    self.run_switch_soul_by_name(con.switch_soul.group_name, con.switch_soul.team_name)
                switch_souled = True

            # 执行悬赏
            self.play_run()
            self.next_run()
            raise TaskEnd

    def play_run(self):
        self.ui_goto_page(page_exploration)
        number_challenge = self._wanted_challenge_tickets()
        wq_timer = Timer(3)
        wq_timer.start()
        self.limit_count = 20
        while 1:
            self.screenshot()

            if self.appear(self.I_WQ_BOX):
                logger.info("检测到奖励宝箱，尝试领取")
                self.ui_get_reward(self.I_WQ_BOX)
                wq_timer.reset()
                continue

            if self.current_count >= self.limit_count:
                logger.warning(f'战斗次数超标（{self.current_count}次），强制退出')
                self.push_notify(content=f'战斗次数超标（{self.current_count}次），强制退出')
                break

            target_found = False
            wq_instances = [
                (self.O_WQ_TEXT_1, self.O_WQ_NUM_1),
                (self.O_WQ_TEXT_2, self.O_WQ_NUM_2),
                (self.O_WQ_TEXT_3, self.O_WQ_NUM_3)
            ]
            for text_obj, num_obj in wq_instances:
                detected_str = text_obj.detect_text(self.device.image)
                if "印" in detected_str:
                    current, remaining, total = num_obj.ocr(self.device.image)
                    valid = total > 0 and 0 <= current <= total and remaining == total - current
                    if valid and remaining == 0:
                        continue
                    if not valid:
                        logger.warning('悬赏侧栏进度无法确认，打开详情复核')
                    # 侧栏 0/6 可能被识别为 076；无效结果不能代表任务已完成。
                    # execute_mission 始终从详情重读实际数量，不猜测侧栏数字。
                    result = self.execute_mission(text_obj, remaining if valid else 0, number_challenge)
                    self.ui_goto_page(page_exploration)
                    if result is False:
                        # 详情明确已完成时继续检查其余条目，不重复重置无任务计时。
                        continue
                    wq_timer.reset()
                    target_found = True
                    # 战斗或取消追踪会使左列任务上移，重新从第一项识别。
                    break

            if target_found:
                continue

            # if self.appear(self.I_WQ_CHECK_TASK):
            #     logger.info('悬赏发现残留任务，尝试处理')
            #     # self.save_image(task_name='悬赏发现残留任务', wait_time=0, image_type='png')
            #     x, y, w, h = self.I_WQ_CHECK_TASK.roi_front
            #     self.I_WQ_CHECK_TASK_CLICK.roi_front = (x - 70, y, w + 30, h)
            #     logger.info(f'调整点击区域至: {self.I_WQ_CHECK_TASK_CLICK.roi_front}')
            #     self.execute_mission(self.I_WQ_CHECK_TASK_CLICK, 1, number_challenge, flag=True)
            #     # self.save_image(task_name='悬赏发现残留任务,战斗结束', wait_time=0, image_type='png')
            #     wq_timer.reset()
            #     continue

            if wq_timer.reached():
                logger.info('无未完成悬赏，退出')
                # self.save_image(task_name='无未完成悬赏', wait_time=0, image_type='png')
                break

    def next_run(self):
        next_run_datetime = self.config.wanted_quests.scheduler.next_refresh_run(datetime.now(), random_delay=True)
        self.set_next_run(task='WantedQuests', target=next_run_datetime, server=False)
        # 使用PPOCR
        # OCR_MODEL.switch_to_ppocr()

    def pre_work(self):
        """
        前置工作，
        :return:
        """
        self.play_count += 1
        self.screenshot()
        if not self.appear(self.I_WQ_PANEL):
            self.ui_goto_page(page_main)
        done_timer = Timer(5)
        prepare_timer = Timer(30).start()
        if self.play_count >= 3:
            return False
        while 1:
            self.screenshot()
            if prepare_timer.reached():
                raise GameStuckError('悬赏面板追踪准备超时')
            if self.appear(self.I_WQ_PANEL):
                if self.appear(self.I_TARCE_DISENABLE) and self.appear(self.I_WQ_GOTO_EXPLORATION):
                    break
                self.appear_then_click(self.I_TRACE_ENABLE, interval=3)
                continue
            if self.appear_then_click(self.I_WQ_SEAL, interval=1):
                continue
            if self.appear_then_click(self.I_WQ_DONE, interval=1):
                continue
            if self.appear(self.I_BACK_RED):
                if not done_timer.started():
                    done_timer.start()
            if done_timer.started() and done_timer.reached():
                self.ui_click_until_disappear(self.I_BACK_RED)
                return False
        # 已追踪所有任务
        logger.info('所有悬赏已追踪')

        # 存在协作任务则邀请
        self.screenshot()
        if any(self.appear(button) for button in self.cooperation_buttons):
            if self.config.wanted_quests.wanted_quests_config.invite_friend_name:
                self.all_cooperation_invite(self.config.wanted_quests.wanted_quests_config.invite_friend_name)
            else:
                self.invite_five()
        self._goto_wanted_exploration()
        return True

    def _goto_wanted_exploration(self):
        """从追踪后的面板直达探索，确认实际页面后才更新导航状态。"""
        timer = Timer(15).start()
        while 1:
            self.screenshot()
            panel_visible = self.appear(self.I_WQ_PANEL)
            if not panel_visible and self.appear(page_exploration.check_button):
                self.ui_current = page_exploration
                return
            if timer.reached():
                raise GameStuckError('悬赏前往探索后未确认探索页面')
            if panel_visible and self.appear(self.I_TARCE_DISENABLE):
                self.appear_then_click(self.I_WQ_GOTO_EXPLORATION, interval=1)

    def _wanted_challenge_tickets(self):
        # 左侧独立数字为式神挑战券；右侧当前数/容量是突破券。
        return self.O_WQ_NUMBER.ocr(self.device.image)

    @staticmethod
    def _wanted_monster_name(title):
        text = re.sub(r'\s+', '', title)
        match = re.fullmatch(r'悬赏目标[:：]击败\d+个(.+)', text)
        return match.group(1) if match else None

    def _wanted_blacklist(self):
        value = self.config.wanted_quests.wanted_quests_config.unwanted_boss_names
        return {re.sub(r'\s+', '', name) for name in re.split(r'[,，、;；\r\n]+', value)
                if name.strip()}

    def _open_wanted_detail(self, ocr, flag=False):
        timer = Timer(10).start()
        clicks = 0
        while 1:
            self.screenshot()
            if self.appear(self.I_WQ_DETAIL):
                return True
            if timer.reached():
                raise GameStuckError('悬赏妖怪进攻详情未打开')
            if flag and not self.appear(self.I_WQ_CHECK_TASK):
                return False
            if clicks < 5 and self.click(ocr, interval=1):
                clicks += 1

    def _close_wanted_detail(self, cancel_tracking=False):
        timer = Timer(10).start()
        cancelled = False
        while 1:
            self.screenshot()
            detail = self.appear(self.I_WQ_DETAIL)
            if not detail and self.appear(page_exploration.check_button):
                if cancel_tracking and not cancelled:
                    raise GameStuckError('悬赏详情已关闭，但未确认取消追踪')
                self.ui_current = page_exploration
                return
            if timer.reached():
                raise GameStuckError('悬赏取消追踪或关闭详情未确认')
            if not detail:
                continue
            if cancel_tracking:
                cancel_visible = self.appear(self.I_WQ_DETAIL_CANCEL_TRACK)
                # 必须看到正向的“追踪”按钮；过渡帧或漏识别不视为取消成功。
                if not cancel_visible and self.appear(self.I_WQ_DETAIL_TRACK):
                    cancelled = True
                else:
                    if cancel_visible and not cancelled:
                        self.appear_then_click(self.I_WQ_DETAIL_CANCEL_TRACK, interval=1)
                    continue
            self.appear_then_click(self.I_WQ_DETAIL_CLOSE, interval=1)

    def _select_wanted_route(self, remaining, tickets, excluded=()):
        unreadable = False
        visible = False
        for slot in range(1, 5):
            goto = getattr(self, f'I_GOTO_{slot}')
            if goto.name in excluded:
                continue
            if not self.appear(goto):
                continue
            visible = True
            kind = re.sub(r'\s+', '', getattr(self, f'O_WQ_TYPE_{slot}').ocr(self.device.image))
            # 类型 ROI 覆盖宽度不同的标签，可能带有后面的少量关卡文字。
            if kind.startswith('式神'):
                if tickets < 10:
                    continue
                battle = 'CHALLENGE'
            elif kind.startswith('秘闻'):
                battle = 'SECRET'
            elif kind.startswith('探索'):
                # 探索流程尚未接入，继续查找可用的秘闻路线。
                continue
            else:
                unreadable = True
                continue
            info = re.sub(r'\s+', '', getattr(self, f'O_WQ_INFO_{slot}').ocr(self.device.image))
            info = info.replace('（', '(').replace('）', ')').replace('：', ':')
            count = re.search(r'数量:(\d+)\)', info)
            if not count or int(count.group(1)) <= 0:
                unreadable = True
                continue
            if battle == 'SECRET' and self.config.wanted_quests.wanted_quests_config.enable_secret_layer_h:
                layer = re.search(r'[·•.]([^·•.()]+)\(数量:', info)
                if not layer:
                    unreadable = True
                    continue
                if layer.group(1) in self.secret_layer:
                    logger.info(f'[{info}] 高层秘闻跳过')
                    continue
            per_battle = int(count.group(1))
            battles = min((remaining + per_battle - 1) // per_battle, 5)
            return battle, battles, goto
        if unreadable or (not visible and not excluded):
            raise GameStuckError('悬赏关卡类型或怪物数量识别失败')
        return None

    def execute_mission(self, ocr, num_want: int, num_challenge: int, flag=False):
        # 保留旧调用参数；数量与挑战券以已打开详情页的新截图为准。
        logger.hr('开始悬赏任务')
        if not self._open_wanted_detail(ocr, flag):
            return
        blacklist = self._wanted_blacklist()
        if blacklist:
            target = self._wanted_monster_name(self.O_WQ_DETAIL_TARGET.ocr(self.device.image))
            if not target:
                raise GameStuckError('悬赏目标名称无法确认，未执行战斗或取消追踪')
            if target in blacklist:
                logger.info(f'跳过悬赏妖怪：{target}')
                self._close_wanted_detail(cancel_tracking=True)
                return
        current, remaining, total = self.O_WQ_DETAIL_PROGRESS.ocr(self.device.image)
        if total <= 0 or not 0 <= current <= total or remaining != total - current:
            raise GameStuckError('悬赏目标进度识别失败')
        if remaining == 0:
            self._close_wanted_detail()
            return False
        excluded = set()
        while True:
            route = self._select_wanted_route(remaining, self._wanted_challenge_tickets(), excluded)
            if route is None:
                if excluded:
                    raise GameStuckError('悬赏可用路线均未能进入，保留追踪等待重试')
                logger.warning('没有可挑战的悬赏，取消本项追踪')
                self._close_wanted_detail(cancel_tracking=True)
                return
            battle, num, goto = route
            logger.info(f'悬赏选择 {battle} 路线 {goto.name}，计划 {num} 次')
            result = self.challenge(goto, num) if battle == 'CHALLENGE' else self.secret(goto, num)
            if result is not False:
                return
            excluded.add(goto.name)
            logger.warning(f'悬赏路线 {goto.name} 未进入，尝试其他路线')

    def _enter_wanted_route(self, goto, fire):
        """点击不延长入口总超时；仍在详情才允许切换另一条路线。"""
        timer = Timer(15).start()
        while True:
            self.screenshot()
            detail = self.appear(self.I_WQ_DETAIL)
            if not detail and self.appear(fire):
                return True
            if timer.reached():
                if detail:
                    return False
                raise GameStuckError('悬赏已离开详情但未确认战斗入口')
            if detail:
                self.appear_then_click(goto, interval=2)

    def challenge(self, goto, num):
        if not self._enter_wanted_route(goto, self.I_WQC_FIRE):
            return False
        self.ui_click_until_disappear(self.I_WQC_FIRE)
        self.run_general_battle()

    def secret(self, goto, num=1):
        if not self._enter_wanted_route(goto, self.I_WQSE_FIRE):
            return False
        for i in range(num):
            if self.current_count >= self.limit_count:
                return
            if not self.wait_until_appear(self.I_WQSE_FIRE, wait_time=15):
                raise GameStuckError('悬赏秘闻挑战入口未出现')
            # self.ui_click_until_disappear(self.I_WQSE_FIRE)
            # 又臭又长的对话针的是服了这个网易
            click_count = 0
            start_timer = Timer(30).start()
            while 1:
                self.screenshot()
                if start_timer.reached():
                    raise GameStuckError('悬赏秘闻准备或对话超时')
                if not self.appear(self.I_WQSE_FIRE) and not self.appear(self.I_CHECK_SECRET_ZONES) and not self.appear(self.I_BACK_RED):
                    break
                if self.appear_then_click(self.I_WQSE_FIRE, interval=1):
                    continue
                if self.appear(self.I_BACK_RED, threshold=0.7) and not self.appear(self.I_WQSE_FIRE):
                    self.click(self.C_SECRET_CHAT, interval=0.8)
                    click_count += 1
                    if click_count >= 6:
                        logger.warning('悬赏秘闻仍在对话中，等待确认进入战斗')
                        click_count = 0
                    continue
            success = self.run_general_battle()
            # 战斗结束对话
            end_timer = Timer(30).start()
            while 1:
                self.screenshot()
                if self.appear(self.I_WQSE_FIRE):
                    break
                if self.appear(self.I_CHECK_SECRET_ZONES):
                    break
                if self.appear(self.I_SE_ENTER):
                    break
                if end_timer.reached():
                    raise GameStuckError('悬赏秘闻战后对话未结束')
                if self.click(self.C_SECRET_CHAT, interval=1):
                    continue
        logger.info('秘闻任务完成')

    def invite_random(self, add_button: RuleImage):
        if not self._cooperation_allowed(add_button):
            return False
        if not self._open_cooperation_invite(add_button):
            return False
        logger.info('进入邀请表单')
        sleep(1)
        self.click(self.I_WQ_FRIEND_1)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_2)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_3)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_4)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_5)
        sleep(0.2)
        self.screenshot()
        if not self.appear(self.I_WQ_INVITE_SELECTED):
            logger.warning('未选择好友')
            return False
        self.ui_click_until_disappear(self.I_WQ_INVITE_ENSURE)
        sleep(0.5)

    def invite_five(self):
        """
        邀请好友，默认点五个
        :return:
        """

        logger.hr('按协作类型邀请好友')
        for button in self.cooperation_buttons:
            self.invite_random(button)

    @property
    def cooperation_buttons(self):
        return tuple(getattr(self, f'I_WQ_INVITE_{slot}') for slot in range(1, 5))

    def _cooperation_click(self, button):
        for slot, candidate in enumerate(self.cooperation_buttons, 1):
            if candidate is button:
                return getattr(self, f'C_WQ_INVITE_{slot}')
        raise ValueError('不是当前悬赏面板的邀请按钮')

    def _open_cooperation_invite(self, button):
        """逐帧复核协作类型，只在对应邀请横条内点击，不延长总超时。"""
        timer = Timer(10).start()
        while 1:
            self.screenshot()
            if self.appear(self.I_WQ_INVITE_ENSURE):
                return True
            if timer.reached():
                raise GameStuckError('悬赏邀请好友表单未打开')
            if not self._cooperation_allowed(button):
                return False
            self.click(self._cooperation_click(button), interval=2.5)

    def all_cooperation_invite(self, name: str):
        """
            所有的协作任务依次邀请
        @param name: 被邀请的朋友名
        @return:

        """
        ret = self.get_cooperation_info()
        if len(ret) == 0:
            logger.info("未找到协作")
            return False
        typeMask = CooperationSelectMask[self.config.wanted_quests.wanted_quests_config.cooperation_type.value]
        for item in ret:
            # 该任务是需要邀请的任务类型
            if not (item['type'] & typeMask):
                logger.info("协作类型 %s 但需要类型 %s ,跳过", item['type'], typeMask)
                continue
            '''
               尝试5次 如果邀请失败 等待20s 重新尝试
               阴阳师BUG: 好友明明在线 但邀请界面找不到该好友(好友未接受任何协作任务的情况下)
           '''
            index = 0
            while index < 5:
                # 好友接受后列表可能变化，每次尝试都重新核对当前位置的奖励。
                if not self._cooperation_allowed(item['inviteBtn']):
                    break
                if self.cooperation_invite(item['inviteBtn'], name):
                    item['inviteResult'] = True
                    break
                index += 1
                if index < 5:
                    logger.info("%s 未找到,等待20秒,剩余 %d 次邀请", name, 5 - index)
                    sleep(20)
        return ret

    def _cooperation_allowed(self, btn: RuleImage) -> bool:
        """两种邀请方式共用筛选；使用新截图，不沿用上次邀请前的位置。"""
        mask = CooperationSelectMask[self.config.wanted_quests.wanted_quests_config.cooperation_type.value]
        if mask == CooperationSelectMask.NoInvite:
            return False
        for item in self.get_cooperation_info():
            if item['inviteBtn'] is btn:
                return bool(item['type'] & mask)
        # 无法识别奖励类型时不自动邀请。
        return False

    def cooperation_invite(self, btn: RuleImage, name: str):
        """
            单个协作任务邀请
        @param btn:
        @param name:
        @return:
        """
        if not self._open_cooperation_invite(btn):
            return False

        # 选人
        self.O_WQ_INVITE_COLUMN_1.keyword = name
        self.O_WQ_INVITE_COLUMN_2.keyword = name

        find = False
        for i in range(2):
            self.screenshot()
            in_col_1 = self.ocr_appear_click(self.O_WQ_INVITE_COLUMN_1)
            in_col_2 = self.ocr_appear_click(self.O_WQ_INVITE_COLUMN_2)
            find = in_col_2 or in_col_1
            if find:
                self.screenshot()
                if self.appear(self.I_WQ_INVITE_SELECTED):
                    logger.info("找到并选择了好友")
                    break
                # TODO OCR识别到文字 但是没有选中 尝试重新选择  (选择好友时,弹出协作邀请导致选择好友失败)
            # 在当前服务器没找到,切换服务器
            self.click(self.I_WQ_INVITE_DIFF_SVR)
            # NOTE 跨服好友刷新缓慢,切换标签页难以检测,姑且用延时.非常卡的模拟器可能出问题
            sleep(2)
        # 没有找到需要邀请的人,点击取消 返回悬赏封印界面
        if not find:
            self.screenshot()
            self.click(self.I_CANCEL)
            return False
        #
        self.ui_click_until_disappear(self.I_WQ_INVITE_ENSURE)
        return True

    def get_cooperation_info(self) -> List:
        """
            获取协作任务详情
        @return: 协作任务类型与邀请按钮
        """
        self.screenshot()
        retList = []
        if not self.appear(self.I_WQ_PANEL):
            return retList
        for index, btn in enumerate(self.cooperation_buttons):
            if not self.appear(btn):
                continue
            if self.appear(self.__getattribute__("I_WQ_COOPERATION_TYPE_JADE_" + str(index + 1))):
                retList.append({'type': CooperationType.Jade, 'inviteBtn': btn})
                continue
            if self.appear(self.__getattribute__("I_WQ_COOPERATION_TYPE_DOG_FOOD_" + str(index + 1))):
                retList.append({'type': CooperationType.Food, 'inviteBtn': btn})
                continue
            if self.appear(self.__getattribute__("I_WQ_COOPERATION_TYPE_CAT_FOOD_" + str(index + 1))):
                retList.append({'type': CooperationType.Food, 'inviteBtn': btn})
                continue
            if self.appear(self.__getattribute__("I_WQ_COOPERATION_TYPE_SUSHI_" + str(index + 1))):
                retList.append({'type': CooperationType.Sushi, 'inviteBtn': btn})
                continue
            # NOTE 因为食物协作里面也有金币奖励 ,所以判断金币协作放在最后面
            if self.appear(self.__getattribute__("I_WQ_COOPERATION_TYPE_GOLD_" + str(index + 1))):
                retList.append({'type': CooperationType.Gold, 'inviteBtn': btn})
                continue

        return retList


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('16448-切换')
    t = ScriptTask(c)
    t.screenshot()

    # t.play_run()
    t.run()
