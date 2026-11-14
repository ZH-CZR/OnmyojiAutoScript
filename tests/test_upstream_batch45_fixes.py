# This Python file uses the following encoding: utf-8
"""批次 45 上游修复回归测试。

覆盖 kongdr418/mine 窗口内两条可落地提交：

1. ``057628b1`` fix(EvoZone) 兼容缺少头像标志的组队页面：创建队伍判断增加
   ``I_CREATE_ROOM`` 分支。
2. ``cc12900f`` fix(MetaDemonTicket) 满票退出时补点关闭奖励页面：本地按新代际
   ``TicketRewardMixin`` 结构手工移植，新增 ``screenshot()`` 兜底与 finally 调用。

其余 4 条（MetaDemon 双端协同、三人协同刷票、15 级起号两连）依赖本地已删除的
``module/cooperation.py`` / ``tasks/AutoStory`` / ``tasks/BorrowShikigami``，判定为需立项，
不在本文件替身覆盖范围内。
"""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tasks.Component.GeneralRoom.assets import GeneralRoomAssets
from tasks.MetaDemonTicket import ticket_farming as tf
from tasks.MetaDemonTicket.config import TicketMode


ROOT = Path(__file__).resolve().parents[1]


class EvoZoneCreateRoomTests(unittest.TestCase):
    def test_create_team_branch_accepts_create_room_flag(self):
        src = (ROOT / 'tasks' / 'EvoZone' / 'script_task.py').read_text(encoding='utf-8')
        tree = ast.parse(src)
        branches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
                continue
            attrs = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
            if 'I_CHECK_TEAM' in attrs and 'I_CREATE_ROOM' in attrs:
                branches.append(node.lineno)
        self.assertTrue(branches, '创建队伍判断未同时兼容 I_CHECK_TEAM 与 I_CREATE_ROOM')

    def test_create_room_asset_available(self):
        asset = GeneralRoomAssets.I_CREATE_ROOM
        self.assertEqual(asset.name, 'GR_CREATE_ROOM')
        self.assertTrue(asset.file.endswith('gr_create_room.png'))
        self.assertTrue((ROOT / asset.file).exists())


class _ScreenshotBase:
    def __init__(self, page_visible=True):
        self.page_visible = page_visible
        self.shots = 0
        self.clicks = 0
        self.match_calls = 0

    def screenshot(self):
        self.shots += 1
        return self.shots

    def match_page_once(self, page):
        self.match_calls += 1
        return self.page_visible


class _DummyRewardTask(tf.TicketRewardMixin, _ScreenshotBase):
    pass


def _close_reward_page(task):
    task.clicks += 1
    task.page_visible = False


def _stuck_reward_page(task):
    task.clicks += 1


class TicketScreenshotTests(unittest.TestCase):
    def test_incomplete_farming_does_not_close_reward_page(self):
        task = _DummyRewardTask()
        with mock.patch.object(tf, 'handle_battle_reward_page', _close_reward_page):
            result = task.screenshot()
        self.assertEqual(result, 1)
        self.assertEqual(task.shots, 1)
        self.assertEqual(task.clicks, 0)
        self.assertEqual(task.match_calls, 0)

    def test_completed_farming_closes_reward_page_then_returns(self):
        task = _DummyRewardTask()
        task._ticket_farming_complete = True
        with mock.patch.object(tf, 'handle_battle_reward_page', _close_reward_page):
            result = task.screenshot()
        self.assertEqual(result, 2)
        self.assertEqual(task.shots, 2)
        self.assertEqual(task.clicks, 1)

    def test_completed_farming_raises_when_reward_page_stays(self):
        task = _DummyRewardTask()
        task._ticket_farming_complete = True
        clock = iter([0.0, 5.0, 31.0])
        with mock.patch.object(tf, 'handle_battle_reward_page', _stuck_reward_page), \
                mock.patch.object(tf.time, 'monotonic', lambda: next(clock)):
            with self.assertRaises(tf.GamePageUnknownError):
                task.screenshot()
        self.assertEqual(task.clicks, 1)
        self.assertEqual(task.shots, 2)

    def test_check_ticket_reward_skips_ocr_after_complete(self):
        task = _DummyRewardTask()
        task._ticket_farming_complete = True
        with mock.patch.object(tf, 'metademon_tickets_full') as full:
            tf.TicketRewardMixin.check_ticket_reward(task)
        full.assert_not_called()


class _FakeRunner:
    instances = []

    def __init__(self, config, device):
        self.config = config
        self.device = device
        self.calls = []
        self._ticket_farming_complete = False
        self._ticket_full = False
        _FakeRunner.instances.append(self)

    def install_ticket_reward_hook(self):
        self.calls.append('hook')

    def goto_page(self, page):
        self.calls.append('goto')

    def open_buff(self):
        self.calls.append('open_buff')

    def close_buff(self):
        self.calls.append('close_buff')

    def awake(self, is_open):
        self.calls.append(('awake', is_open))

    def run_alone(self):
        self.calls.append('run_alone')

    def pre_process(self):
        self.calls.append('pre_process')

    def exec_exp_page(self):
        self.calls.append('exp_page')

    def screenshot(self):
        self.calls.append('screenshot')


class _FullOnRunRunner(_FakeRunner):
    def run_alone(self):
        self.calls.append('run_alone')
        raise tf.TicketsFull


def _make_owner():
    meta = SimpleNamespace(
        general_config=SimpleNamespace(
            user_status=tf.ExplorationUserStatus.ALONE,
            limit_time_v=600,
            awake_buff_enable=False,
        ),
        switch_soul_config=SimpleNamespace(enable=False, enable_switch_by_name=False),
    )
    return SimpleNamespace(config=SimpleNamespace(meta_demon_ticket=meta), device='device')


class RunTicketFarmingFinallyTests(unittest.TestCase):
    def setUp(self):
        _FakeRunner.instances = []

    def _run(self, runner_cls, mode):
        owner = _make_owner()
        with mock.patch.object(tf, 'tickets_full_before_farming', lambda task: False), \
                mock.patch.object(tf, 'ticket_farming_config', lambda meta, m: SimpleNamespace()), \
                mock.patch.object(tf, 'AwakeTicketTask', runner_cls), \
                mock.patch.object(tf, 'ExplorationTicketTask', runner_cls):
            result = tf.run_ticket_farming(owner, mode)
        return result, _FakeRunner.instances[-1]

    def test_awake_normal_exit_takes_final_screenshot(self):
        result, runner = self._run(_FakeRunner, TicketMode.AWAKE)
        self.assertFalse(result)
        self.assertTrue(runner._ticket_farming_complete)
        self.assertEqual(runner.calls[-1], 'screenshot')

    def test_awake_tickets_full_exit_takes_final_screenshot(self):
        result, runner = self._run(_FullOnRunRunner, TicketMode.AWAKE)
        self.assertTrue(result)
        self.assertTrue(runner._ticket_farming_complete)
        self.assertEqual(runner.calls[-1], 'screenshot')

    def test_exploration_normal_exit_takes_final_screenshot(self):
        result, runner = self._run(_FakeRunner, TicketMode.EXPLORATION)
        self.assertFalse(result)
        self.assertEqual(runner.calls, ['hook', 'pre_process', 'exp_page', 'screenshot'])
        self.assertEqual(runner.calls[-1], 'screenshot')


if __name__ == '__main__':
    unittest.main()
