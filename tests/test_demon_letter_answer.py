# This Python file uses the following encoding: utf-8
"""逢魔密信答题的回归测试。

背景：旧实现点一次答案后不再看画面，循环里每 1.5 秒重复点同一行答案。
游戏其实在第一次点击后就推进到下一题，后面的点击落进新题目里，被记成选了错误答案；
题目答完（右侧出现红笔勾/叉）后选项点击完全没有反应，机器人就在原地点满 10 次，
最终触发 GameTooManyClickError。

修复后的约定：
- 每题只点一次，然后靠题目文本变化 / 奖励弹窗 / 关闭按钮消失 / 批改标记判断进展；
- 进入密信时若已批改，直接关信，不点任何选项；
- 点击无效时快速收尾（关信返回），不再连点。
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from tasks.DemonEncounter.script_task import ScriptTask


def make_task():
    """构造一个只带答题所需属性的 ScriptTask 实例，避免走完整的初始化。"""
    task = object.__new__(ScriptTask)
    task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8))
    task.screenshot = Mock()
    task.click = Mock()
    task.appear = Mock(return_value=True)
    task.ui_reward_appear_click = Mock(return_value=False)
    return task


def make_ocr_task(question='以下式神中，有兄弟或姐妹是谁？',
                  options=('O跳跳哥哥', '独眼小僧', 'X雪女')):
    task = make_task()
    task.O_LETTER_QUESTION = SimpleNamespace(detect_text=Mock(return_value=question))
    task.O_LETTER_ANSWER_1 = SimpleNamespace(detect_text=Mock(return_value=options[0]))
    task.O_LETTER_ANSWER_2 = SimpleNamespace(detect_text=Mock(return_value=options[1]))
    task.O_LETTER_ANSWER_3 = SimpleNamespace(detect_text=Mock(return_value=options[2]))
    return task


class LetterAnsweredTest(unittest.TestCase):
    def test_letter_answered_detects_bgr_red_marks(self):
        task = make_task()
        self.assertFalse(task._letter_answered(screenshot=False))
        task.device.image[270:330, 790:860] = (40, 40, 200)  # BGR 里的红色
        self.assertTrue(task._letter_answered(screenshot=False))

    def test_letter_answered_detects_rgb_red_marks(self):
        task = make_task()
        task.device.image[270:330, 790:860] = (200, 40, 40)  # RGB 里的红色
        self.assertTrue(task._letter_answered(screenshot=False))

    def test_letter_answered_ignores_black_text_region(self):
        task = make_task()
        task.device.image[380:420, 560:680] = (30, 30, 30)
        self.assertFalse(task._letter_answered(screenshot=False))

    def test_clean_letter_option_strips_mark_symbols(self):
        self.assertEqual(ScriptTask._clean_letter_option('O跳跳哥哥'), '跳跳哥哥')
        self.assertEqual(ScriptTask._clean_letter_option('X雪女'), '雪女')
        self.assertEqual(ScriptTask._clean_letter_option(' 独眼小僧 '), '独眼小僧')
        self.assertEqual(ScriptTask._clean_letter_option(None), '')


class AnswerLetterOnceTest(unittest.TestCase):
    def test_advances_when_question_changes(self):
        task = make_task()
        task._letter_question_text = Mock(side_effect=['问题1', '问题1', '问题2'])
        task._letter_answered = Mock(return_value=False)
        answer_click = Mock()
        with patch('tasks.DemonEncounter.script_task.time.sleep'):
            result = task._answer_letter_once(answer_click)
        self.assertEqual(result, 'advanced')
        task.click.assert_called_once_with(answer_click, interval=0)

    def test_stops_when_letter_closed(self):
        task = make_task()
        task._letter_question_text = Mock(return_value='问题1')
        task.appear = Mock(return_value=False)  # 关闭按钮消失
        task._letter_answered = Mock(return_value=False)
        with patch('tasks.DemonEncounter.script_task.time.sleep'):
            result = task._answer_letter_once(Mock())
        self.assertEqual(result, 'finished')
        task.ui_reward_appear_click.assert_called()

    def test_stops_when_result_marks_persist(self):
        task = make_task()
        task.LETTER_MARK_SETTLE = 0
        task._letter_question_text = Mock(return_value='问题1')
        task._letter_answered = Mock(return_value=True)
        with patch('tasks.DemonEncounter.script_task.time.sleep'):
            result = task._answer_letter_once(Mock())
        self.assertEqual(result, 'finished')
        self.assertEqual(task.click.call_count, 1)

    def test_reports_stuck_without_progress(self):
        task = make_task()
        task._letter_question_text = Mock(return_value='问题1')
        task._letter_answered = Mock(return_value=False)
        with patch('tasks.DemonEncounter.script_task.time.sleep'):
            result = task._answer_letter_once(Mock(), timeout=0.05)
        self.assertEqual(result, 'stuck')
        self.assertEqual(task.click.call_count, 1)

    def test_reward_popup_advances(self):
        task = make_task()
        task.ui_reward_appear_click = Mock(return_value=True)
        task._wait_reward_closed = Mock()
        task._letter_question_text = Mock(return_value='问题1')
        task._letter_answered = Mock(return_value=False)
        result = task._answer_letter_once(Mock())
        self.assertEqual(result, 'advanced')
        task._wait_reward_closed.assert_called_once()
        self.assertEqual(task.click.call_count, 1)


class MailFlowTest(unittest.TestCase):
    def test_skips_answered_letter(self):
        task = make_ocr_task()
        task._enter_lantern_event = Mock(return_value=True)
        task._letter_answered = Mock(return_value=True)
        task._close_letter = Mock()
        task._answer_letter_once = Mock()
        task.O_LETTER_QUESTION = SimpleNamespace(
            detect_text=Mock(side_effect=AssertionError('已答完的密信不该再读题目')))
        task._mail(Mock())
        task._answer_letter_once.assert_not_called()
        task._close_letter.assert_called_once()

    def test_answers_each_question_once(self):
        task = make_ocr_task()
        task._enter_lantern_event = Mock(return_value=True)
        task._letter_answered = Mock(return_value=False)
        task._close_letter = Mock()
        task._answer_letter_once = Mock(side_effect=['advanced', 'advanced', 'finished'])
        with patch('tasks.DemonEncounter.script_task.Answer') as answer_cls:
            answer_cls.return_value.answer_one.return_value = 1
            with patch('tasks.DemonEncounter.script_task.time.sleep'):
                task._mail(Mock())
        # 三题各点一次，且第一题永远只有一个点击入口
        self.assertEqual(task._answer_letter_once.call_count, 3)
        self.assertEqual(task.O_LETTER_QUESTION.detect_text.call_count, 3)
        task._close_letter.assert_called_once()

    def test_stuck_stops_after_one_click(self):
        task = make_ocr_task()
        task._enter_lantern_event = Mock(return_value=True)
        task._letter_answered = Mock(return_value=False)
        task._close_letter = Mock()
        task._answer_letter_once = Mock(return_value='stuck')
        with patch('tasks.DemonEncounter.script_task.Answer') as answer_cls:
            answer_cls.return_value.answer_one.return_value = 1
            with patch('tasks.DemonEncounter.script_task.time.sleep'):
                task._mail(Mock())
        self.assertEqual(task._answer_letter_once.call_count, 1)
        task._close_letter.assert_called_once()


class CloseLetterTest(unittest.TestCase):
    def test_clicks_until_letter_gone(self):
        task = make_task()
        task.appear = Mock(side_effect=[True, True, False])
        task._close_letter()
        self.assertEqual(task.click.call_count, 2)

    def test_returns_when_letter_already_gone(self):
        task = make_task()
        task.appear = Mock(return_value=False)
        task._close_letter()
        task.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
