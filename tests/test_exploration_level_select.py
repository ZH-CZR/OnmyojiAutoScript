# This Python file uses the following encoding: utf-8
"""探索选关的回归测试。

背景：进入副本地图的瞬间，页面识别可能短暂认成 page_exploration，导航就会顺着
page_exploration -> page_exp_entrance 这条边在副本地图里执行「选关」动作。
地图右侧没有章节列表，旧实现会空转 25 次才抛 GameStuckError，且 25 次里一次滑屏都没做。
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import GameStuckError
from tasks.Exploration.base import BaseExploration
from tasks.Exploration.config import ExplorationLevel


def _ocr_result(text):
    return SimpleNamespace(ocr_text=text)


MAP_ANCHORS = (
    BaseExploration.I_E_SETTINGS_BUTTON,
    BaseExploration.I_E_AUTO_ROTATE_ON,
    BaseExploration.I_E_AUTO_ROTATE_OFF,
)


class ExplorationLevelSelectTest(unittest.TestCase):
    def make_task(self, hit_rules=(), ocr_texts=None, level=ExplorationLevel.EXPLORATION_28):
        """构造一个只带选关所需属性的 BaseExploration 实例。

        hit_rules 里的规则在 appear() 里返回 True，用来模拟「已经在地图里」
        「章节栏已出现」等画面状态。
        """
        task = object.__new__(BaseExploration)
        task.config = SimpleNamespace(
            exploration=SimpleNamespace(
                exploration_config=SimpleNamespace(exploration_level=level)
            )
        )
        task.device = SimpleNamespace(image=object(), click_record_clear=Mock())
        task.screenshot = Mock()
        task.click = Mock()
        task.swipe = Mock()
        task.appear = Mock(side_effect=lambda rule, *args, **kwargs: rule in hit_rules)
        task.wait_until_appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=False)
        task.ocr_appear_click = Mock(return_value=False)
        task.is_in_room = Mock(return_value=False)
        task.O_E_EXPLORATION_LEVEL_NUMBER = SimpleNamespace(
            detect_and_ocr=Mock(return_value=[_ocr_result(t) for t in (ocr_texts or [])])
        )
        return task

    def test_skip_when_already_in_map(self):
        # 已经站在副本地图里：选关动作应立即认领成功，不点 tab、不滑屏
        task = self.make_task(hit_rules=(BaseExploration.I_E_SETTINGS_BUTTON,))
        self.assertTrue(task.open_expect_level())
        task.click.assert_not_called()
        task.swipe.assert_not_called()
        task.O_E_EXPLORATION_LEVEL_NUMBER.detect_and_ocr.assert_not_called()

    def test_ensure_mainline_tab_returns_false_when_unreadable(self):
        # 章节栏始终不出现：只做有限次尝试并如实返回 False，不抛异常
        task = self.make_task()
        self.assertFalse(task.ensure_mainline_tab())

    def test_ensure_mainline_tab_returns_true_after_click(self):
        task = self.make_task()
        task.wait_until_appear = Mock(return_value=True)
        self.assertTrue(task.ensure_mainline_tab())
        self.assertEqual(task.click.call_count, 1)

    def test_unreadable_chapter_list_fails_fast(self):
        # 章节栏修不好时立即带诊断失败，不再空转 25 秒
        task = self.make_task()
        with patch('tasks.Exploration.base.time.sleep') as sleep:
            with self.assertRaises(GameStuckError) as ctx:
                task.open_expect_level()
            sleep.assert_not_called()
        self.assertIn('not readable', str(ctx.exception))

    def test_empty_ocr_stops_after_limit(self):
        # 章节栏锚点可读，但 OCR 一帧都读不到章节名：到上限即失败，不再滑到 25 次
        task = self.make_task(hit_rules=(BaseExploration.I_E_CHECK_MAIN_TITLE,), ocr_texts=[])
        with patch('tasks.Exploration.base.time.sleep') as sleep:
            with self.assertRaises(GameStuckError) as ctx:
                task.open_expect_level()
        self.assertIn('unreadable for 5 screenshots', str(ctx.exception))
        self.assertEqual(sleep.call_count, BaseExploration.EXPLORATION_EMPTY_LIMIT - 1)
        task.swipe.assert_not_called()

    def test_levels_sorted_before_swipe_decision(self):
        # OCR 顺序打乱时，min/max 必须按章节索引判断：
        # 目标 27 章落在可见的 26~28 章之间，排序生效时不滑屏（旧实现会误判为向下滑）
        task = self.make_task(
            hit_rules=(BaseExploration.I_E_CHECK_MAIN_TITLE,),
            ocr_texts=['第二十八章', '第二十六章'],
            level=ExplorationLevel.EXPLORATION_27,
        )
        with patch('tasks.Exploration.base.time.sleep'):
            with self.assertRaises(GameStuckError) as ctx:
                task.open_expect_level()
        task.swipe.assert_not_called()
        self.assertIn('never matched', str(ctx.exception))

    def test_swipe_count_only_counts_real_swipes(self):
        # 目标章节始终在可见区间之外：每次都是真实滑屏，累计 25 次后抛原文案
        task = self.make_task(
            hit_rules=(BaseExploration.I_E_CHECK_MAIN_TITLE,),
            ocr_texts=['第二十六章'],
            level=ExplorationLevel.EXPLORATION_28,
        )
        with patch('tasks.Exploration.base.time.sleep'):
            with self.assertRaises(GameStuckError) as ctx:
                task.open_expect_level()
        self.assertEqual(task.swipe.call_count, BaseExploration.EXPLORATION_SWIPE_LIMIT)
        self.assertIn('Swiped too many times (25)', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
