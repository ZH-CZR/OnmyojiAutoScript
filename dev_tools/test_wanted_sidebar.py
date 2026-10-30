"""探索侧栏进度 OCR 失败不得误报无任务；不连接设备或 OCR 服务。"""
import copy
import unittest
from unittest.mock import Mock, patch, call

from dev_tools import test_wanted_detail as detail_tests
from module.exception import GameStuckError
from tasks.WantedQuests.assets import WantedQuestsAssets as Assets
from tasks.WantedQuests.script_task import ScriptTask


class WantedSidebarTests(unittest.TestCase):
    setUp = detail_tests.WantedDetailTest.setUp
    routes = detail_tests.WantedDetailTest.routes
    click_visible = detail_tests.WantedDetailTest.click_visible

    def setup_sidebar(self, progress=(0, 0, 0), slot=1):
        self.task.current_count = 0
        self.task.appear.return_value = False
        self.task.appear.side_effect = lambda rule: False
        self.task.O_WQ_NUMBER.ocr.return_value = 3864
        for index in range(1, 4):
            getattr(self.task, f'O_WQ_TEXT_{index}').detect_text = Mock(return_value='')
        getattr(self.task, f'O_WQ_TEXT_{slot}').detect_text.return_value = '悬赏封印'
        getattr(self.task, f'O_WQ_NUM_{slot}').ocr.return_value = progress
        self.task.execute_mission = Mock(return_value=False)
        timer = Mock()
        timer.start.return_value = timer
        # 即使 3 秒计时已到，也必须先复核可见条目。
        timer.reached.return_value = True
        return timer

    def test_real_ocr_transcript_076_opens_detail_instead_of_ending(self):
        timer = self.setup_sidebar()
        counter = copy.deepcopy(Assets.O_WQ_NUM_1)
        counter.__dict__['model'] = Mock()
        counter.model.ocr_single_line.return_value = ('076', 0.951495)
        self.task.O_WQ_NUM_1 = counter
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            self.task.play_run()
        self.task.execute_mission.assert_called_once_with(self.task.O_WQ_TEXT_1, 0, 3864)
        # 只有详情明确已完成才能退出，不能把侧栏解析失败当完成。
        timer.reset.assert_not_called()

    def test_invalid_or_inconsistent_counters_all_require_detail(self):
        for progress in ((0, 0, 0), (7, -1, 6), (0, 0, 6), (0, 3, 6)):
            with self.subTest(progress=progress):
                timer = self.setup_sidebar(progress)
                with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
                    self.task.play_run()
                self.task.execute_mission.assert_called_once_with(self.task.O_WQ_TEXT_1, 0, 3864)

    def test_each_of_three_slots_can_fall_back_to_detail(self):
        for slot in range(1, 4):
            with self.subTest(slot=slot):
                timer = self.setup_sidebar(slot=slot)
                with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
                    self.task.play_run()
                self.task.execute_mission.assert_called_once_with(
                    getattr(self.task, f'O_WQ_TEXT_{slot}'), 0, 3864)

    def test_valid_completed_sidebar_and_absent_label_do_not_open_detail(self):
        timer = self.setup_sidebar((6, 0, 6))
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            self.task.play_run()
        self.task.execute_mission.assert_not_called()
        self.task.O_WQ_TEXT_1.detect_text.return_value = ''
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            self.task.play_run()
        self.task.execute_mission.assert_not_called()

    def test_detail_complete_first_slot_does_not_hide_later_slot(self):
        timer = self.setup_sidebar()
        self.task.O_WQ_TEXT_2.detect_text.return_value = '悬赏封印'
        self.task.O_WQ_NUM_2.ocr.return_value = (0, 3, 3)
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            self.task.play_run()
        self.assertEqual(self.task.execute_mission.call_args_list, [
            call(self.task.O_WQ_TEXT_1, 0, 3864), call(self.task.O_WQ_TEXT_2, 3, 3864)])
        timer.reset.assert_not_called()

    def test_unknown_sidebar_progress_reaches_secret_using_detail_count(self):
        self.setup_sidebar()
        self.routes(('秘闻烽火', '烽火寄情·贰(数量:6)'))
        self.task.appear.side_effect = lambda rule: rule.name in self.visible
        self.task._open_wanted_detail = Mock(return_value=True)
        self.task._close_wanted_detail = Mock()
        # 下次扫描条目已因实际任务处理消失，不会重复操作旧位置。
        self.task.O_WQ_TEXT_1.detect_text.side_effect = ['悬赏封印', '']
        self.task.execute_mission = ScriptTask.execute_mission.__get__(self.task)
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.return_value = True
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            self.task.play_run()
        self.task.O_WQ_DETAIL_PROGRESS.ocr.assert_called_once()
        self.task.secret.assert_called_once_with(self.task.I_GOTO_1, 1)
        self.task.challenge.assert_not_called()
        self.task._close_wanted_detail.assert_not_called()

    def test_unreadable_detail_is_an_error_not_a_successful_empty_run(self):
        timer = self.setup_sidebar()
        self.task.execute_mission = ScriptTask.execute_mission.__get__(self.task)
        self.task._open_wanted_detail = Mock(return_value=True)
        self.task.O_WQ_DETAIL_PROGRESS.ocr.return_value = (0, 0, 0)
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaisesRegex(GameStuckError, '进度识别失败'):
                self.task.play_run()
        self.task.secret.assert_not_called()
        timer.reset.assert_not_called()

    def test_detail_confirmed_complete_returns_false_without_battle(self):
        self.task.O_WQ_DETAIL_PROGRESS.ocr.return_value = (6, 0, 6)
        self.task._close_wanted_detail = Mock()
        self.assertIs(self.task.execute_mission(None, 0, 3864), False)
        self.task._close_wanted_detail.assert_called_once_with()
        self.task.secret.assert_not_called()
        self.task.challenge.assert_not_called()


if __name__ == '__main__':
    unittest.main()
