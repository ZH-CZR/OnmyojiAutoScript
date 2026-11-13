# This Python file uses the following encoding: utf-8
"""批次 44 上游修复回归测试。

覆盖本次合入的三条上游提交：

1. ``ad778fba`` 每日琐事商店签到入口重试（最多 4 次、出现签到页即停、无进展退出防卡死）。
2. ``eb156b16`` 突破券数量上限校验：``RealmRaid.read_ticket_count`` /
   ``is_ticket`` / ``check_ticket`` / 聊天框遮挡后的票数识别，以及
   ``Exploration.activate_realm_raid`` 的无效读数拦截。
3. ``27b9f534`` 标注器截图帧缓存隔离：``Screenshot.frame_cache_name`` 与
   ``tool_capture_worker._build_device``。

回归守卫：本地商店页识别仍保留紫色招牌/灯笼变体（未采用上游 11 月 12 日的
``I_CHECK_MALL`` ROI 改动），斗技结束返回庭院链路保持 ``goto_page(page_main)``。
"""
import inspect
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import Mock

from tasks.DailyTrifles.script_task import ScriptTask as DailyTriflesTask
from tasks.Exploration.base import BaseExploration
import tasks.Exploration.page as exploration_pages
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.default_pages import page_mall
from tasks.RealmRaid.script_task import ScriptTask as RealmRaidTask

ROOT = Path(__file__).resolve().parents[1]


class DailyTriflesStoreSignTest(unittest.TestCase):
    """``ad778fba`` 商店签到入口点击重试。"""

    def make_task(self):
        task = object.__new__(DailyTriflesTask)
        task.config = SimpleNamespace(daily_trifles=SimpleNamespace(
            today_is_done=Mock(return_value=False),
            done_record=SimpleNamespace(store_sign_dt=None),
            trifles_config=SimpleNamespace(store_sign=True),
        ))
        task.goto_page = Mock()
        task.screenshot = Mock()
        task.appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=True)
        task.ui_get_reward = Mock(return_value=True)
        return task

    def test_retries_until_gift_sign_appears(self):
        task = self.make_task()
        task.appear = Mock(side_effect=[False, False, True, True])
        with mock.patch('tasks.DailyTrifles.script_task.sleep'):
            task.run_store_sign()

        self.assertEqual(task.appear_then_click.call_count, 2)
        task.goto_page.assert_called_once()
        task.ui_get_reward.assert_called_once()
        self.assertIsNotNone(task.config.daily_trifles.done_record.store_sign_dt)

    def test_retry_cap_is_four_clicks(self):
        task = self.make_task()
        task.appear = Mock(return_value=False)
        with mock.patch('tasks.DailyTrifles.script_task.sleep'):
            task.run_store_sign()

        self.assertEqual(task.appear_then_click.call_count, 4)
        task.ui_get_reward.assert_not_called()

    def test_no_progress_exits_instead_of_spinning(self):
        task = self.make_task()
        task.appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=False)
        with mock.patch('tasks.DailyTrifles.script_task.sleep'):
            task.run_store_sign()

        self.assertEqual(task.appear_then_click.call_count, 1)
        task.ui_get_reward.assert_not_called()

    def test_done_record_short_circuits(self):
        task = self.make_task()
        task.config.daily_trifles.today_is_done = Mock(return_value=True)
        task.run_store_sign()

        task.goto_page.assert_not_called()
        task.screenshot.assert_not_called()


class RealmRaidTicketTest(unittest.TestCase):
    """``eb156b16`` 突破券上限校验与无效读数丢弃。"""

    def make_task(self, counters):
        task = object.__new__(RealmRaidTask)
        task.device = SimpleNamespace(image=object())
        task.O_NUMBER = SimpleNamespace(ocr=Mock(side_effect=counters))
        task.wait_until_appear = Mock()
        task.screenshot = Mock()
        task.reward_detect_click = Mock()
        task.config = SimpleNamespace(realm_raid=SimpleNamespace(
            raid_config=SimpleNamespace(number_attack=2)))
        task.init_tickets = -1
        return task

    def test_invalid_counts_are_discarded_until_a_valid_frame(self):
        task = self.make_task([(31, -1, 30), (999, -969, 30), (-1, 31, 30),
                               (30, 50, 80), (30, 0, 30)])
        self.assertEqual(task.read_ticket_count(), 30)
        self.assertEqual(task.screenshot.call_count, 5)
        self.assertEqual(task.wait_until_appear.call_count, 5)
        task.reward_detect_click.assert_not_called()

    def test_failed_ocr_retries_and_preserves_valid_zero(self):
        task = self.make_task([(0, 0, 0), (0, 0, 0), (0, 30, 30)])
        self.assertEqual(task.read_ticket_count(), 0)
        self.assertEqual(task.reward_detect_click.call_count, 2)
        self.assertEqual(task.screenshot.call_count, 3)

    def test_invalid_counts_do_not_change_initial_or_consumed_tickets(self):
        task = self.make_task([(999, -969, 30), (20, 10, 30),
                               (88, -58, 30), (19, 11, 30), (18, 12, 30)])
        self.assertTrue(task.check_ticket(base=10))
        self.assertEqual(task.init_tickets, 20)
        self.assertTrue(task.check_ticket(base=10))
        self.assertEqual(task.init_tickets, 20)
        self.assertFalse(task.check_ticket(base=10))
        self.assertEqual(task.init_tickets, 20)

    def test_is_ticket_uses_a_valid_count_after_an_overflow(self):
        for current in (0, 30):
            with self.subTest(current=current):
                task = self.make_task([(31, -1, 30), (current, 30 - current, 30)])
                self.assertEqual(task.is_ticket(), current > 0)
                self.assertEqual(task.screenshot.call_count, 2)

    def test_valid_counts_still_enforce_the_starting_threshold(self):
        for current in (0, 4, 5, 30):
            with self.subTest(current=current):
                task = self.make_task([(current, 30 - current, 30)])
                self.assertEqual(task.check_ticket(base=5), current >= 5)

    def test_chat_overlay_requires_a_valid_ticket_counter(self):
        task = self.make_task([])
        del task.reward_detect_click
        task.ui_click_until_disappear = Mock()
        task.appear_then_click = Mock(return_value=False)
        task.O_TEXT = SimpleNamespace(ocr=Mock(side_effect=[
            '聊天消息', '31/30', '30/80', '30/30']))
        self.assertTrue(task.reward_detect_click(False))
        self.assertEqual(task.O_TEXT.ocr.call_count, 4)
        self.assertEqual(task.screenshot.call_count, 3)


class ExplorationTicketTest(unittest.TestCase):
    """``eb156b16`` 探索/寮宴会突破券检测只接受 0~30 的有效读数。"""

    def make_task(self, current, total):
        scrolls = SimpleNamespace(scrolls_enable=True, scrolls_threshold=25,
                                  scrolls_cd=timedelta(minutes=30))
        exploration = SimpleNamespace(buff_gold_50_click=False, buff_gold_100_click=False,
                                      buff_exp_50_click=False, buff_exp_100_click=False)
        task = object.__new__(BaseExploration)
        task.device = SimpleNamespace(image=object())
        task.O_REALM_RAID_NUMBER = SimpleNamespace(ocr=Mock(return_value=(current, total - current, total)))
        task.O_REALM_RAID_NUMBER1 = SimpleNamespace(ocr=Mock(return_value=(current, total - current, total)))
        task.goto_page = Mock()
        task.set_next_run = Mock()
        return task, scrolls, exploration

    def test_only_valid_ticket_counts_can_schedule_realm_raid(self):
        from module.exception import TaskEnd
        for page in (exploration_pages.page_exploration, exploration_pages.page_exp_entrance):
            for current, total in ((31, 30), (999, 30), (30, 80), (0, 0),
                                   (-1, 30), (0, 30), (24, 30), (25, 30), (30, 30)):
                with self.subTest(page=page.name, current=current, total=total):
                    task, scrolls, exploration = self.make_task(current, total)
                    if total == 30 and 25 <= current <= 30:
                        with self.assertRaises(TaskEnd):
                            task.activate_realm_raid(scrolls, exploration, page)
                        self.assertEqual(task.set_next_run.call_count, 3)
                    else:
                        task.activate_realm_raid(scrolls, exploration, page)
                        task.goto_page.assert_not_called()
                        task.set_next_run.assert_not_called()
                    rule = task.O_REALM_RAID_NUMBER1 if page == exploration_pages.page_exp_entrance \
                        else task.O_REALM_RAID_NUMBER
                    rule.ocr.assert_called_once_with(task.device.image)


class AnnotatorFrameCacheTest(unittest.TestCase):
    """``27b9f534`` 标注器截图使用独立帧缓存名。"""

    def test_screenshot_accepts_frame_cache_name_before_connection(self):
        from module.device.screenshot import Screenshot
        source = inspect.getsource(Screenshot.__init__)
        self.assertIn('frame_cache_name', source)
        self.assertLess(source.index('self.frame_cache_name'),
                        source.index('super().__init__'))

        file_source = (ROOT / 'module/device/screenshot.py').read_text(encoding='utf-8')
        self.assertIn('self.frame_cache_name or self.config.config_name', file_source)

    def test_capture_worker_builds_annotator_scoped_device(self):
        from module.server import tool_capture_worker
        with mock.patch('module.server.tool_capture_worker.Device') as device_cls:
            device = tool_capture_worker._build_device('sess-1', 'oas', object(), 0.5)
        self.assertEqual(device_cls.call_args.kwargs['frame_cache_name'], 'annotator:sess-1')
        device.disable_stuck_detection.assert_called_once()
        device.screenshot_interval_set.assert_called_once_with(0.5)


class UntouchedFeatureGuardTest(unittest.TestCase):
    """本次刻意未采纳的上游改动不得回流。"""

    def test_mall_detection_keeps_local_variants(self):
        names = [child.target.name for child in page_mall.recognizer.children]
        self.assertIn(GameUiAssets.I_CHECK_MALL.name, names)
        self.assertIn(GameUiAssets.I_CHECK_MALL_PURPLE.name, names)
        self.assertIn(GameUiAssets.I_CHECK_MALL_LANTERN.name, names)
        self.assertEqual(tuple(GameUiAssets.I_CHECK_MALL.roi_front), (231, 455, 131, 78))
        for rule in (GameUiAssets.I_CHECK_MALL, GameUiAssets.I_CHECK_MALL_PURPLE,
                     GameUiAssets.I_CHECK_MALL_LANTERN):
            self.assertTrue((ROOT / rule.file.lstrip('./')).exists(), rule.file)

    def test_gift_sign_asset_available(self):
        self.assertIn('store_gift_sign.png', DailyTriflesTask.I_GIFT_SIGN.file)
        self.assertTrue((ROOT / DailyTriflesTask.I_GIFT_SIGN.file.lstrip('./')).exists())

    def test_duel_still_returns_to_courtyard(self):
        file_source = (ROOT / 'tasks/Duel/script_task.py').read_text(encoding='utf-8')
        self.assertIn('self.goto_page(page_main)', file_source)


if __name__ == '__main__':
    unittest.main()
