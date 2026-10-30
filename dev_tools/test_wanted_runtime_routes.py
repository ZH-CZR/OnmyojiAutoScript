"""悬赏路线入口与协作弹窗确认回归，无游戏输入。"""
import unittest
from unittest.mock import Mock, patch, call

from module.exception import GameStuckError
from dev_tools import test_wanted_detail as detail_tests
from dev_tools import test_wanted_invitation as invitation_tests
from tasks.GlobalGame.config_emergency import FriendInvitation


class WantedRouteRuntimeTests(unittest.TestCase):
    setUp = detail_tests.WantedDetailTest.setUp
    routes = detail_tests.WantedDetailTest.routes
    click_visible = detail_tests.WantedDetailTest.click_visible

    def test_sakura_without_challenge_route_selects_first_secret(self):
        # 用户 2026-10-30 完整截图的本地 PP-OCRv6 实际输出。
        self.task.O_WQ_NUMBER.ocr.return_value = 3864
        self.routes(('秘闻烽火', '烽火寄情·贰(数量:6)'),
                    ('秘闻山巅', '山巅之禁·壹(数量:3)'),
                    ('秘闻道成', '道成夙怨·贰(数量:4)'),
                    ('探索第八', '第八章(数量:3)'))
        self.task.execute_mission(None, 6, 3864)
        self.task.challenge.assert_not_called()
        self.task.secret.assert_called_once_with(self.task.I_GOTO_1, 1)

    def test_failed_challenge_entry_tries_secret(self):
        self.task.O_WQ_NUMBER.ocr.return_value = 3864
        self.routes(('式神碎片', '第八章(数量:14)'), ('秘闻', '山巅之禁·壹(数量:3)'))
        self.task.challenge.return_value = False
        self.task.execute_mission(None, 6, 3864)
        self.task.challenge.assert_called_once_with(self.task.I_GOTO_1, 1)
        self.task.secret.assert_called_once_with(self.task.I_GOTO_2, 2)

    def test_failed_first_secret_tries_next_secret(self):
        self.routes(('秘闻烽火', '烽火寄情·贰(数量:6)'), ('秘闻山巅', '山巅之禁·壹(数量:3)'))
        self.task.secret.side_effect = [False, None]
        self.task.execute_mission(None, 6, 3864)
        self.assertEqual(self.task.secret.call_args_list,
                         [call(self.task.I_GOTO_1, 1), call(self.task.I_GOTO_2, 2)])

    def test_all_failed_entries_keep_tracking(self):
        self.routes(('秘闻', '山巅之禁·壹(数量:3)'))
        self.task.secret.return_value = False
        with self.assertRaisesRegex(GameStuckError, '保留追踪'):
            self.task.execute_mission(None, 6, 3864)
        self.task.secret.assert_called_once()
        self.task.click.assert_not_called()

    def test_entry_timeout_only_allows_fallback_while_still_in_detail(self):
        for in_detail in (True, False):
            self.visible = {self.task.I_WQ_DETAIL.name} if in_detail else set()
            timer = Mock()
            timer.start.return_value = timer
            timer.reached.side_effect = [False, True]
            with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
                if in_detail:
                    self.assertFalse(self.task._enter_wanted_route(self.task.I_GOTO_1, self.task.I_WQSE_FIRE))
                else:
                    with self.assertRaises(GameStuckError):
                        self.task._enter_wanted_route(self.task.I_GOTO_1, self.task.I_WQSE_FIRE)
            timer.reset.assert_not_called()

    def prepare_secret(self):
        self.task._enter_wanted_route = Mock(return_value=True)
        self.task.wait_until_appear = Mock(return_value=True)
        self.task.run_general_battle = Mock()
        self.task.current_count = 0
        self.task.limit_count = 20

    def test_secret_does_not_exceed_global_battle_limit(self):
        self.prepare_secret()
        self.task.current_count = 20
        detail_tests.ScriptTask.secret(self.task, self.task.I_GOTO_1, 5)
        self.task.wait_until_appear.assert_not_called()
        self.task.run_general_battle.assert_not_called()

    def test_secret_preparation_times_out_without_faking_a_battle(self):
        self.prepare_secret()
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.return_value = True
        with patch('tasks.WantedQuests.script_task.Timer', return_value=timer):
            with self.assertRaisesRegex(GameStuckError, '准备或对话超时'):
                detail_tests.ScriptTask.secret(self.task, self.task.I_GOTO_1, 1)
        self.task.run_general_battle.assert_not_called()
        timer.reset.assert_not_called()

    def test_secret_settlement_dialog_has_independent_timeout(self):
        self.prepare_secret()
        self.visible.clear()
        start, end = Mock(), Mock()
        for timer, reached in ((start, False), (end, True)):
            timer.start.return_value = timer
            timer.reached.return_value = reached
        with patch('tasks.WantedQuests.script_task.Timer', side_effect=[start, end]):
            with self.assertRaisesRegex(GameStuckError, '战后对话未结束'):
                detail_tests.ScriptTask.secret(self.task, self.task.I_GOTO_1, 1)
        self.task.run_general_battle.assert_called_once()
        end.reset.assert_not_called()


class WantedInvitationConfirmationTests(unittest.TestCase):
    setUp = invitation_tests.WantedInvitationTests.setUp
    click_invitation = invitation_tests.WantedInvitationTests.click_invitation

    def test_reject_recognizes_invitation_even_if_accept_is_missed(self):
        self.task.config.wanted_quests.emergency.friend_invitation = FriendInvitation.REJECT
        self.visible = {self.task.I_G_REJECT.name}
        self.assertTrue(self.task._burst())
        self.task.appear_then_click.assert_called_once_with(self.task.I_G_REJECT, interval=0.8)
        self.task.set_next_run.assert_not_called()

    def test_missing_selected_button_does_not_report_success(self):
        self.task.config.wanted_quests.emergency.friend_invitation = FriendInvitation.ACCEPT
        self.visible = {self.task.I_G_REJECT.name}
        self.task.appear_then_click.side_effect = lambda *args, **kwargs: False
        timer = Mock()
        timer.start.return_value = timer
        timer.reached.side_effect = [False, True]
        with patch('tasks.base_task_parent.Timer', return_value=timer):
            with self.assertRaisesRegex(GameStuckError, '悬赏邀请'):
                self.task._burst()
        self.task.set_next_run.assert_not_called()
        self.assertIn('BATTLE_STATUS_S', self.device.detect_record)
        timer.reset.assert_not_called()

    def test_disappeared_before_click_does_not_schedule_wanted_task(self):
        self.task.config.wanted_quests.emergency.friend_invitation = FriendInvitation.ACCEPT
        self.device.screenshot.side_effect = self.visible.clear
        self.assertFalse(self.task._burst())
        self.task.appear_then_click.assert_not_called()
        self.task.set_next_run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
