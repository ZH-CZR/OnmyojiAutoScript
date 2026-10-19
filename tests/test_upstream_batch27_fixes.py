# This Python file uses the following encoding: utf-8
"""批次 27 上游小修回归测试（Delegation / WantedQuests / GeneralBattle / 摸鱼 / 桌面登录）。

这些提交的落点大多依赖真实截图与点击，无法在本机离线复现，因此：
- 纯逻辑（Restart 桌面重试、摸鱼弹窗清理顺序）用假对象驱动真实方法；
- 其余用源码契约钉死不变量，防止后续同步把上游语义改回去。
"""
import inspect
import unittest
from unittest import mock

from module.exception import (GameStuckError,
                              GameTooManyClickError,
                              RequestHumanTakeover)
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.Login import service as login_service
from tasks.Delegation.script_task import ScriptTask as DelegationTask
from tasks.GameUi.page import page_main
from tasks.Restart import script_task as restart
from tasks.WantedQuests.script_task import ScriptTask as WantedQuestsTask
from tasks.WeeklyTrifles import script_task as weekly_trifles
from tasks.WeeklyTrifles.script_task import ScriptTask as WeeklyTriflesTask


class DelegationFixTests(unittest.TestCase):
    def test_enter_and_start_have_timeouts(self):
        source = inspect.getsource(DelegationTask.delegate_one)
        self.assertIn('enter_timer = Timer(15)', source)
        self.assertIn('start_timer = Timer(10)', source)

    def test_jade_confirm_is_cancelled(self):
        source = inspect.getsource(DelegationTask.delegate_one)
        self.assertIn('self.I_UI_CANCEL', source)
        self.assertIn('Exit delegation detail timeout', source)

    def test_task_name_debounce_raised_to_three_seconds(self):
        source = inspect.getsource(DelegationTask.delegate_one)
        self.assertIn('self.ocr_appear_click(self.O_D_NAME, interval=3)', source)
        self.assertNotIn('self.ocr_appear_click(self.O_D_NAME, interval=1)', source)


class WantedQuestsFixTests(unittest.TestCase):
    def test_selected_friend_uses_invite_selected_asset(self):
        source = inspect.getsource(WantedQuestsTask.invite_random)
        self.assertIn('self.I_WQ_INVITE_SELECTED', source)
        self.assertNotIn('self.I_SELECTED', source)


class GeneralBattleFixTests(unittest.TestCase):
    def test_prepare_clicked_after_buff_panel_closes(self):
        source = inspect.getsource(GeneralBattle.check_and_open_buff)
        self.assertIn(
            'self.ui_click_until_disappear(self.I_PREPARE_HIGHLIGHT, interval=0.8)',
            source,
        )


class _TouchFishStub(WeeklyTriflesTask):
    def __init__(self):
        self.visited = []
        self.smt_calls = []

    def goto_page(self, page, **kwargs):
        self.visited.append(page)

    def screenshot(self):
        pass

    def appear(self, rule, **kwargs):
        return rule is WeeklyTriflesTask.I_WT_FOLD_WINDOW

    def appear_then_click(self, rule, **kwargs):
        return False

    def ui_click_until_smt_disappear(self, click, stop, interval=1):
        self.smt_calls.append(stop)
        return True


class TouchFishFixTests(unittest.TestCase):
    def test_last_save_popup_cleared_before_checking_save_all(self):
        stub = _TouchFishStub()
        with mock.patch.object(weekly_trifles, 'sleep'), \
                mock.patch.object(weekly_trifles, 'logger'):
            stub._save_touch_fish()

        self.assertEqual(stub.smt_calls, [WeeklyTriflesTask.I_WT_LAST_SAVE],
                         '进入摸鱼页后应先用随机点击清掉「上次存储」提示')
        self.assertIn(page_main, stub.visited)


class RestartDesktopTests(unittest.TestCase):
    def _task(self):
        task = object.__new__(restart.ScriptTask)
        task.config = object()
        task.device = mock.Mock()
        task.device.is_desktop = True
        return task

    def test_desktop_start_and_login_retries_then_succeeds(self):
        task = self._task()
        login = mock.Mock(side_effect=[GameStuckError('boom'), None])
        with mock.patch.object(restart, 'LoginService', return_value=mock.Mock(app_handle_login=login)):
            task._desktop_start_and_login()
        self.assertEqual(task.device.app_start.call_count, 2)
        self.assertEqual(login.call_count, 2)
        task.device.desktop_stop_client.assert_called_once()

    def test_desktop_start_and_login_fails_closed(self):
        task = self._task()
        task.device.desktop_stop_client.return_value = True
        login = mock.Mock(side_effect=GameTooManyClickError('nope'))
        with mock.patch.object(restart, 'LoginService', return_value=mock.Mock(app_handle_login=login)):
            with self.assertRaises(RequestHumanTakeover):
                task._desktop_start_and_login()
        self.assertEqual(login.call_count, restart.DESKTOP_RESTART_ATTEMPTS)

    def test_desktop_restart_does_not_stop_healthy_client(self):
        task = self._task()
        with mock.patch.object(task, '_desktop_start_and_login') as start:
            task.app_restart()
        start.assert_called_once()
        task.device.app_stop.assert_not_called()

    def test_emulator_restart_keeps_stop_start(self):
        task = self._task()
        task.device.is_desktop = False
        with mock.patch.object(task, 'app_start') as start:
            task.app_restart()
        task.device.app_stop.assert_called_once()
        start.assert_called_once()


class LoginDesktopTests(unittest.TestCase):
    def test_mpay_popup_handling_is_wired_into_login_loop(self):
        source = inspect.getsource(login_service.LoginService._app_handle_login)
        self.assertIn('handle_desktop_login_popup()', source)
        self.assertIn('find_desktop_login_popup', source)
        self.assertEqual(login_service.DESKTOP_MPAY_CLOSE_LIMIT, 5)

    def test_successful_login_marks_desktop_state(self):
        source = inspect.getsource(login_service.LoginService.app_handle_login)
        self.assertIn('desktop_mark_logged_in()', source)

    def test_navigator_stops_on_lost_login(self):
        from tasks.GameUi import navigator
        source = inspect.getsource(navigator.GameUi)
        self.assertIn('app_lost_login()', source)


if __name__ == '__main__':
    unittest.main()
