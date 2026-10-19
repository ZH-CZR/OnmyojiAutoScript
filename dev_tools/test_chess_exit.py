"""Chess quit-dialog variants and confirmation; no device or game required."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from module.atom.image import RuleImage
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.chess_battle import ChessBattleNavigationMixin as GlobalNavigation
from tasks.Chess.runtime.battle_navigation import ChessBattleNavigationMixin as TaskNavigation


class ChessExitTest(unittest.TestCase):
    def run_exit(self, navigation, frames, *, return_to_lobby=True):
        clock = SimpleNamespace(now=0.)
        task = SimpleNamespace(
            CHESS_EXIT_TIMEOUT=3., CHESS_EXIT_SCREENSHOT_INTERVAL=.35,
            device=SimpleNamespace(stuck_record_clear=Mock()),
            click=Mock(), return_to_chess_lobby=Mock(return_value=True),
        )
        for key in ('I_CHESS_EXIT', 'I_CHESS_EXIT_CONFIRM',
                    'I_CHESS_EXIT_CONFIRM_ALT', 'I_CHESS_EXIT_CANCEL'):
            setattr(task, key, key)
        sequence = iter(frames)

        def screenshot():
            task.frame = next(sequence, frames[-1])

        task.screenshot = screenshot
        task.appear = lambda marker: marker in task.frame
        task.chess_result_flow_visible = lambda: 'result' in task.frame
        module = navigation.__module__
        with patch(module + '.time.monotonic', side_effect=lambda: clock.now), \
                patch(module + '.time.sleep', side_effect=lambda s: setattr(clock, 'now', clock.now + s)):
            kwargs = {'return_to_lobby': return_to_lobby} if navigation is GlobalNavigation else {}
            result = navigation.exit_chess_battle(task, **kwargs)
        return task, result

    def test_both_dialog_variants_exit_through_result_flow(self):
        for navigation in (GlobalNavigation, TaskNavigation):
            for button in ('I_CHESS_EXIT_CONFIRM', 'I_CHESS_EXIT_CONFIRM_ALT'):
                with self.subTest(navigation=navigation, button=button):
                    task, result = self.run_exit(navigation, [
                        {'I_CHESS_EXIT'}, {button, 'I_CHESS_EXIT_CANCEL'}, {'result'},
                    ])
                    self.assertTrue(result)
                    self.assertEqual([c.args[0] for c in task.click.call_args_list],
                                     ['I_CHESS_EXIT', button])
                    task.return_to_chess_lobby.assert_called_once()

    def test_missing_confirm_and_transition_do_not_finish_exit(self):
        for navigation in (GlobalNavigation, TaskNavigation):
            with self.subTest(navigation=navigation):
                task, result = self.run_exit(navigation, [
                    {'I_CHESS_EXIT_CONFIRM_ALT', 'I_CHESS_EXIT_CANCEL'},
                    {'I_CHESS_EXIT_CANCEL', 'result'}, set(),
                ])
                self.assertFalse(result)
                task.return_to_chess_lobby.assert_not_called()

    def test_cancel_only_never_clicks_unrecognized_confirm(self):
        for navigation in (GlobalNavigation, TaskNavigation):
            task, result = self.run_exit(navigation, [{'I_CHESS_EXIT_CANCEL'}])
            self.assertFalse(result)
            task.click.assert_not_called()

    def test_confirm_retried_while_dialog_remains(self):
        for navigation in (GlobalNavigation, TaskNavigation):
            task, result = self.run_exit(navigation, [
                {'I_CHESS_EXIT_CONFIRM_ALT', 'I_CHESS_EXIT_CANCEL'},
            ])
            self.assertFalse(result)
            self.assertEqual(task.click.call_count, 2)

    def test_global_can_leave_result_handling_to_caller(self):
        task, result = self.run_exit(GlobalNavigation, [
            {'I_CHESS_EXIT_CONFIRM_ALT'}, {'result'},
        ], return_to_lobby=False)
        self.assertTrue(result)
        task.return_to_chess_lobby.assert_not_called()

    def test_templates_match_both_texts_without_lowering_threshold(self):
        for source in (GameUiAssets.I_CHESS_EXIT_CONFIRM, GameUiAssets.I_CHESS_EXIT_CONFIRM_ALT):
            # Reconstruct a frame using only the small shipped button asset.
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            image = cv2.cvtColor(cv2.imdecode(np.fromfile(Path(source.file), dtype=np.uint8), 1),
                                 cv2.COLOR_BGR2RGB)
            x, y, w, h = source.roi_back
            frame[y:y+h, x:x+w] = image
            rule = RuleImage(roi_front=(x, y, w, h), roi_back=(x, y, w, h),
                             method=source.method, threshold=source.threshold, file=source.file)
            self.assertTrue(rule.match(frame))
            self.assertFalse(rule.match(np.zeros_like(frame)))


if __name__ == '__main__':
    unittest.main()
