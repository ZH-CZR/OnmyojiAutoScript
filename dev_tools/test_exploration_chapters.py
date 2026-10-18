"""探索章节 OCR 接口及屏幕点击坐标回归；不连接设备或启动 OCR 服务。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from module.atom.ocr import RuleOcr
from module.ocr.common import BoxedResult
from tasks.Exploration.base import BaseExploration
from tasks.Exploration.config import ExplorationLevel


class ExplorationChaptersTest(unittest.TestCase):
    def make_task(self, results):
        ocr = RuleOcr(roi=(1058, 206, 120, 348), area=(1058, 206, 120, 348),
                      mode='Full', method='Default', keyword='', name='chapters')
        ocr.__dict__['model'] = Mock()
        ocr.model.detect_and_ocr.return_value = results
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        image[206:554, 1058:1178] = 127
        task = SimpleNamespace(
            O_E_EXPLORATION_LEVEL_NUMBER=ocr,
            device=SimpleNamespace(image=image, click_record_clear=Mock()),
            screenshot=Mock(), click=Mock(), appear=Mock(return_value=True),
            appear_then_click=Mock(return_value=False),
            wait_until_appear=Mock(return_value=True),
            ui_click_until_disappear=Mock(),
            I_E_EXPLORATION_CLICK='entrance', I_UI_SURE='sure',
            I_UI_CONFIRM='confirm', I_BACK_RED='back',
        )
        task._detect_visible_chapters = lambda: BaseExploration._detect_visible_chapters(task)
        return task

    def chapter(self, text='第二十八章', score=0.99):
        # 四点框含轻微倾斜，点击矩形应覆盖整个文本。
        return BoxedResult(np.array([[12, 44], [94, 46], [92, 72], [10, 70]]),
                           None, text, score)

    def test_detection_crops_once_and_filters_low_confidence(self):
        chapter = self.chapter()
        task = self.make_task([chapter, self.chapter('第二十七章', 0.1)])
        results = task._detect_visible_chapters()
        self.assertEqual(results, [chapter])
        cropped = task.O_E_EXPLORATION_LEVEL_NUMBER.model.detect_and_ocr.call_args.args[0]
        self.assertEqual(cropped.shape, (348, 120, 3))
        self.assertTrue(np.all(cropped == 127))
        self.assertEqual(chapter.ocr_text, '第二十八章')

    def test_empty_detection(self):
        self.assertEqual(self.make_task([])._detect_visible_chapters(), [])

    def test_target_chapter_click_uses_screen_coordinates(self):
        task = self.make_task([self.chapter('第二十七章'), self.chapter()])
        self.assertTrue(BaseExploration.open_expect_level(task, ExplorationLevel.EXPLORATION_28))
        task.click.assert_called_once()
        button = task.click.call_args.args[0]
        self.assertEqual(button.roi_front, (1068, 250, 84, 28))
        self.assertEqual(button.roi_back, button.roi_front)
        task.wait_until_appear.assert_called_once_with('entrance', wait_time=5)


if __name__ == '__main__':
    unittest.main()
