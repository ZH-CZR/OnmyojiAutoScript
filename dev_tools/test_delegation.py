"""式神委派离线场景回归，不连接设备或 OCR 服务。"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from module.exception import GameStuckError


ROOT = Path(__file__).resolve().parents[1]


class DelegationTests(unittest.TestCase):
    def make_task(self):
        source = ROOT / 'tasks/Delegation/script_task.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        original = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        methods = [n for n in original.body if isinstance(n, ast.FunctionDef)
                   and n.name != 'run']
        module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(
            name='Task', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[]))
        self.clock = 0
        test = self

        class Timer:
            def __init__(self, limit):
                self.limit = limit

            def start(self):
                self.start_time = test.clock

            reset = start

            def reached(self):
                return test.clock - self.start_time >= self.limit

        namespace = dict(Timer=Timer, logger=Mock(), GameStuckError=GameStuckError)
        exec(compile(module, str(source), 'exec'), namespace)
        task = namespace['Task']()
        for name in ('I_D_START', 'I_D_BACK', 'I_D_SKIP', 'I_D_CONFIRM', 'C_D_ALL',
                     'I_D_SELECT_FIRST', 'I_REWARDS_MIN', 'I_REWARDS_GET', 'I_REWARDS_CHAT',
                     'I_CHAT_1', 'I_CHAT_2', 'I_REWARDS_DONE', 'I_REWARDS_FALSE'):
            setattr(task, name, name)
        task.O_D_NAME = SimpleNamespace(keyword='')
        task.O_D_DONE = SimpleNamespace()
        task.O_D_DONE_CHAT = SimpleNamespace(ocr=Mock(return_value='委派完成'))
        task.device = SimpleNamespace(image=object())

        def screenshot():
            self.clock += 0.25
            if self.clock > 20:
                self.fail('场景未在有限时间内结束')

        task.screenshot = screenshot
        task.ocr_appear = Mock(return_value=True)
        task.ocr_appear_click = Mock(return_value=False)
        task.ui_click_until_disappear = Mock()
        task.wait_until_appear = Mock()
        task.appear = Mock(return_value=False)
        task.appear_then_click = Mock(return_value=False)
        task.click = Mock(return_value=True)
        return task

    def test_one_click_selection_waits_for_marker_before_departure(self):
        for selection_delay in (0, 2):
            with self.subTest(selection_delay=selection_delay):
                task = self.make_task()
                state = dict(page='list', selected_at=None, departed=False)
                last_click = {}
                clicks = []

                def appear(button):
                    if button == task.I_D_START:
                        return state['page'] == 'select' and not state['departed']
                    if button == task.I_D_SELECT_FIRST:
                        return (state['selected_at'] is not None
                                and self.clock >= state['selected_at'])
                    return False

                def click(button, interval):
                    if self.clock - last_click.get(button, -100) < interval:
                        return False
                    last_click[button] = self.clock
                    clicks.append(button)
                    if button == task.C_D_ALL:
                        if state['selected_at'] is None:
                            state['selected_at'] = self.clock + selection_delay
                    elif button == task.I_D_START:
                        self.assertTrue(appear(task.I_D_SELECT_FIRST))
                        state['departed'] = True
                    else:
                        self.fail(f'不应逐个点击式神: {button}')
                    return True

                def open_task(*args, **kwargs):
                    state['page'] = 'select'
                    return True

                task.appear = appear
                task.click = click
                task.appear_then_click = lambda button, interval: appear(button) and click(button, interval)
                task.ocr_appear_click = open_task
                task.delegate_one('鸟羽')
                self.assertTrue(state['departed'])
                self.assertEqual(clicks[0], task.C_D_ALL)
                self.assertEqual(clicks[-1], task.I_D_START)
                self.assertEqual(task.O_D_NAME.keyword, '鸟羽')

    def test_missing_task_does_not_select(self):
        task = self.make_task()
        task.ocr_appear.return_value = False
        self.assertFalse(task.delegate_one('鸟羽'))
        task.click.assert_not_called()

    def test_running_task_returns_without_selecting(self):
        task = self.make_task()
        task.appear.side_effect = lambda button: button == task.I_D_BACK
        self.assertFalse(task.delegate_one('鸟羽'))
        task.ui_click_until_disappear.assert_called_once_with(task.I_D_BACK)
        task.wait_until_appear.assert_called_once_with(task.I_REWARDS_MIN)
        task.click.assert_not_called()

    def test_reward_dialog_advances_until_confirmation(self):
        task = self.make_task()
        task.appear.side_effect = lambda button: (button == task.I_REWARDS_CHAT
            or button == task.I_REWARDS_DONE and task.click.call_count >= 2)
        task.wait_delegation_done_reward()
        self.assertEqual(task.click.call_count, 2)
        task.click.assert_called_with(task.O_D_DONE_CHAT, interval=0.8)

    def test_empty_text_or_missing_dialog_is_not_clicked_and_times_out(self):
        for text, dialog in (('', True), ('委派完成', False)):
            with self.subTest(text=text, dialog=dialog):
                task = self.make_task()
                task.O_D_DONE_CHAT.ocr.return_value = text
                task.appear.side_effect = lambda button: button == task.I_REWARDS_CHAT and dialog
                with self.assertRaises(GameStuckError):
                    task.wait_delegation_done_reward()
                task.click.assert_not_called()
                self.assertLess(self.clock, 6)

    def test_check_reward_waits_after_opening_completed_task(self):
        task = self.make_task()
        task.appear.side_effect = lambda button: button == task.I_REWARDS_MIN
        task.ocr_appear_click.side_effect = [True] + [False] * 20
        task.wait_delegation_done_reward = Mock()
        task.check_reward()
        task.wait_delegation_done_reward.assert_called_once_with()

    def test_unopened_entry_retries_then_handles_choice_and_reward(self):
        task = self.make_task()
        state = dict(retries=0, chosen=False)

        def appear(button):
            if state['retries'] < 2:
                return button == task.I_REWARDS_MIN
            return button == (task.I_REWARDS_GET if state['chosen'] else task.I_CHAT_1)

        def retry(*args, **kwargs):
            state['retries'] += 1
            return True

        def click(button, interval):
            self.assertEqual(button, task.I_CHAT_1)
            state['chosen'] = True
            return True

        task.appear.side_effect = appear
        task.ocr_appear_click.side_effect = retry
        task.click.side_effect = click
        task.wait_delegation_done_reward()
        self.assertEqual(state['retries'], 2)
        self.assertTrue(state['chosen'])
        task.O_D_DONE_CHAT.ocr.assert_not_called()

    def test_unopened_entry_has_bounded_retries_and_specific_error(self):
        task = self.make_task()
        task.appear.side_effect = lambda button: button == task.I_REWARDS_MIN
        task.ocr_appear_click.return_value = True
        with self.assertRaisesRegex(GameStuckError, 'entry did not open'):
            task.wait_delegation_done_reward()
        self.assertEqual(task.ocr_appear_click.call_count, 2)
        task.click.assert_not_called()
        self.assertLess(self.clock, 6)

    def test_cooldown_does_not_consume_entry_retry(self):
        task = self.make_task()
        task.appear.side_effect = lambda button: button == task.I_REWARDS_MIN
        task.ocr_appear_click.side_effect = [False, False, True, False, True]
        with self.assertRaisesRegex(GameStuckError, 'entry did not open'):
            task.wait_delegation_done_reward()
        self.assertEqual(task.ocr_appear_click.call_count, 5)

    def test_reward_result_variants_return_to_outer_handler(self):
        for reward in ('I_REWARDS_DONE', 'I_REWARDS_GET', 'I_REWARDS_FALSE'):
            with self.subTest(reward=reward):
                task = self.make_task()
                task.appear.side_effect = lambda button: button == getattr(task, reward)
                task.wait_delegation_done_reward()
                task.click.assert_not_called()
                task.ocr_appear_click.assert_not_called()

    def test_recognized_dialog_with_empty_ocr_can_skip(self):
        task = self.make_task()
        task.O_D_DONE_CHAT.ocr.return_value = ''
        task.appear.side_effect = lambda button: (
            button == task.I_REWARDS_CHAT or
            button == task.I_REWARDS_DONE and task.appear_then_click.called)
        task.wait_delegation_done_reward()
        task.appear_then_click.assert_called_once_with(task.I_REWARDS_CHAT, interval=1)
        task.click.assert_not_called()

    def test_dialog_does_not_reopen_list_and_still_times_out(self):
        task = self.make_task()
        task.appear.side_effect = lambda button: (
            button == task.I_REWARDS_CHAT and self.clock < 1
            or button == task.I_REWARDS_MIN and self.clock >= 1)
        with self.assertRaisesRegex(GameStuckError, 'reward dialog timed out'):
            task.wait_delegation_done_reward()
        task.ocr_appear_click.assert_not_called()

    def test_task_constructs_with_shared_device_and_assets_load(self):
        from module.config.config import Config
        from tasks.Delegation.script_task import ScriptTask
        from tasks.Delegation.assets import DelegationAssets
        from module.atom.image import RuleImage

        device = SimpleNamespace()
        task = ScriptTask(Config('template'), device)
        self.assertIs(task.device, device)
        for name, rule in vars(DelegationAssets).items():
            if isinstance(rule, RuleImage):
                with self.subTest(asset=name):
                    rule.load_image()
                    self.assertGreater(rule.image.size, 0)
        self.assertEqual(task.C_D_ALL.roi_front, (1097, 449, 133, 39))


if __name__ == '__main__':
    unittest.main()
