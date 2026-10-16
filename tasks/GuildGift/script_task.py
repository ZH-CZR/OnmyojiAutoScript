import time

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.GameUi.game_ui import GameUi
from tasks.GuildGift.assets import GuildGiftAssets
from tasks.RichMan.assets import RichManAssets
from tasks.RichMan.page import page_guid_procurement, page_shrine


class ScriptTask(GameUi, GuildGiftAssets):
    """独立日常任务：按当前可购上限购买阴阳寮礼包。"""

    def run(self):
        success = False
        if self.ui_goto_page(page_guid_procurement):
            success = self.buy_guild_gift()
            # 明确关闭购买窗口再交给公共导航，避免把背景当成当前页面。
            if not self.close_gift_dialog():
                success = False
            elif not self.ui_goto_page(page_shrine):
                self.fail("购买流程结束后未能返回神社")
                success = False
        else:
            self.fail("未能进入寮内采办，未执行购买")

        self.set_next_run(task="GuildGift", success=success, finish=True)
        raise TaskEnd("GuildGift")

    def fail(self, message):
        logger.warning(message)
        self.save_image(wait_time=0, content=message)
        return False

    def read_purchase_message(self):
        """只读取居中提示；不点击未知确认弹窗。"""
        text = self.O_GUILD_GIFT_MESSAGE.ocr(self.device.image)
        if "购买成功" in text:
            return "success"
        if any(word in text for word in ("已达上限", "达到上限", "已售罄", "已买完")):
            return "limit"
        if any(word in text for word in ("不足", "权限", "仅会长", "仅限会长")):
            return "unavailable"
        return None

    def buy_guild_gift(self) -> bool:
        # 打开商品，确认是阴阳寮礼包的购买窗口，避免点击其他商品。
        timeout = Timer(15).start()
        message_timer = Timer(1).start()
        while not timeout.reached():
            self.screenshot()
            if self.appear(self.I_GUILD_GIFT_DIALOG) and self.appear(self.I_GUILD_GIFT_MAX):
                break
            if message_timer.reached_and_reset():
                message = self.read_purchase_message()
                if message == "limit":
                    logger.info("阴阳寮礼包已达购买上限，跳过")
                    return True
                if message == "unavailable":
                    return self.fail("资源或权限不足，跳过购买阴阳寮礼包")
            self.appear_then_click(self.I_GUILD_GIFT, interval=1)
            time.sleep(0.2)
        else:
            return self.fail("未能打开阴阳寮礼包购买窗口，未执行购买")

        balance_before = self.O_GUILD_GIFT_TOTAL.ocr(self.device.image)
        # 对新截图中的最大上限按钮找图点击一次。
        if not self.appear_then_click(self.I_GUILD_GIFT_MAX, interval=0):
            return self.fail("未找到最大上限按钮，未执行购买")
        time.sleep(0.6)

        timeout = Timer(10).start()
        number_record = None
        while not timeout.reached():
            self.screenshot()
            # 必须仍是目标礼包窗口，最大上限按钮和功勋购买按钮均存在。
            if self.appear(self.I_GUILD_GIFT_DIALOG) and self.appear(self.I_GUILD_GIFT_MAX):
                number = self.O_GUILD_GIFT_NUMBER.ocr(self.device.image)
                if number > 0 and number == number_record:
                    if self.appear_then_click(self.I_GUILD_GIFT_BUY, interval=0):
                        break
                number_record = number
            time.sleep(0.2)
        else:
            return self.fail("未找到礼包购买按钮，未执行购买")

        # 购买只点一次。等待奖励作为成功证据，未知状态不重复扣费。
        timeout = Timer(12).start()
        message_timer = Timer(1).start()
        rewarded = False
        while not timeout.reached():
            self.screenshot()
            if self.ui_reward_appear_click():
                rewarded = True
                time.sleep(0.3)
                continue
            if rewarded and not self.appear(self.I_GUILD_GIFT_DIALOG):
                logger.info("阴阳寮礼包购买成功，奖励窗口已关闭")
                return True
            if message_timer.reached_and_reset():
                message = self.read_purchase_message()
                if message == "success":
                    logger.info("检测到阴阳寮礼包购买成功提示")
                    return True
                if message == "limit":
                    logger.info("阴阳寮礼包已达购买上限，跳过")
                    return True
                if message == "unavailable":
                    return self.fail("资源或权限不足，购买未完成")
                if balance_before > 0 and not self.appear(self.I_GUILD_GIFT_DIALOG):
                    if self.ui_page_appear(page_guid_procurement):
                        balance_after = self.O_GUILD_GIFT_TOTAL.ocr(self.device.image)
                        if 0 < balance_after < balance_before:
                            logger.info(f"礼包购买窗口已关闭，功勋余额 {balance_before} -> {balance_after}")
                            return True
            time.sleep(0.2)
        return self.fail("未确认礼包购买结果，已停止点击；请检查任务截图")

    def close_gift_dialog(self):
        """只关闭已识别的礼包购买窗口，确认消失后再导航。"""
        timeout = Timer(6).start()
        while not timeout.reached():
            self.screenshot()
            if not self.appear(self.I_GUILD_GIFT_DIALOG):
                return True
            self.appear_then_click(RichManAssets.I_GUILD_CLOSE_RED, interval=1)
            time.sleep(0.2)
        return self.fail("未能关闭礼包购买窗口，停止页面导航")
