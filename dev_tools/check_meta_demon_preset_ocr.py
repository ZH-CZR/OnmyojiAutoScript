"""Replay saved preset crops through an existing OCR server; never create a device.

Run: python -m dev_tools.check_meta_demon_preset_ocr [--address 127.0.0.1:22268]
The fixture pixels retain the RGB array saved by OcrLogger with cv2.imwrite.
"""
import argparse
import copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from module.ocr.rpc import get_ocr_client
from tasks.MetaDemon.script_task import ScriptTask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address', default='127.0.0.1:22268')
    args = parser.parse_args()
    model = get_ocr_client(args.address)
    model.save_log = False
    root = Path(__file__).parent / 'fixtures/meta_demon_preset'
    cases = [
        ('group_selected.png', 'O_PS_GROUP', '活动', (560, 324)),
        ('group_earlier.png', 'O_PS_GROUP', '活动', (560, 509)),
        ('group_earlier.png', 'O_PS_GROUP', '寮活动', (560, 407)),
        ('team_fourth.png', 'O_PS_TEAM', '雪月', (786, 536)),
        ('team_fourth.png', 'O_PS_TEAM', 'SP鬼童丸', (786, 343)),
    ]
    for filename, asset, target, expected in cases:
        rule = copy.copy(getattr(ScriptTask, asset))
        rule.__dict__['model'] = model
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        crop = cv2.imread(str(root / filename))
        if crop is None:
            raise RuntimeError(f'Missing fixture: {filename}')
        x, y, w, h = rule.roi
        assert crop.shape[:2] == (h, w), filename
        image[y:y+h, x:x+w] = crop
        task = ScriptTask.__new__(ScriptTask)
        task.device = SimpleNamespace(image=image, click=Mock())
        task.screenshot = Mock(return_value=image)
        task.swipe = Mock()
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            assert task._preset_select_by_ocr(rule, target), (filename, target)
        if asset == 'O_PS_GROUP':
            task.screenshot.assert_called_once()
            task.swipe.assert_not_called()
        else:
            # 固定的顶部截图：先向下拖内容两次确认到顶，才开始队名OCR。
            assert task.screenshot.call_count == 4
            assert task.swipe.call_count == 2
            for call in task.swipe.call_args_list:
                swipe = call.args[0]
                assert swipe.roi_front[1] < swipe.roi_back[1]
        task.device.click.assert_called_once()
        cx, cy = task.device.click.call_args.args
        assert abs(cx-expected[0]) <= 3 and abs(cy-expected[1]) <= 4, (filename, target, cx, cy)
        print(f'PASS {filename}: {target} -> ({cx}, {cy}), {task.swipe.call_count} top-reset swipes')


if __name__ == '__main__':
    main()
