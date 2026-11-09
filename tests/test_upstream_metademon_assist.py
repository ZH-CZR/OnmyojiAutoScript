# This Python file uses the following encoding: utf-8
"""超鬼王「六星鬼王上供」移植回归测试（源自 self ``591508f6``）。

本地超鬼王为单脚本结构，仅移植上供所需的召唤/分享/等待逻辑：
新增 ``MetaDemonMode.BOSS_ASSIST`` 与 ``MetaDemonAssistanceConfig``，
``GhostOffering`` 负责选好友与分享，``run_assistance`` 负责循环与收尾。
"""
import inspect
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from module.exception import RequestHumanTakeover, TaskEnd
from tasks.MetaDemon import assistance
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemon.config import (
    AssistanceRole,
    MetaDemonAssistanceConfig,
    MetaDemonConfig,
    MetaDemonMode,
)
from tasks.MetaDemon.script_task import ScriptTask


class MetaDemonAssistConfigTests(unittest.TestCase):
    def test_mode_defaults_to_boss_battle(self):
        self.assertIs(MetaDemonConfig().mode, MetaDemonMode.BOSS_BATTLE)

    def test_assistance_defaults(self):
        conf = MetaDemonAssistanceConfig()
        self.assertIs(conf.role, AssistanceRole.OFFERING)
        self.assertEqual(conf.friend_names, '')
        self.assertEqual(conf.poll_interval, 5)
        self.assertEqual(conf.friends, [])

    def test_friend_names_parsing_and_dedupe(self):
        conf = MetaDemonAssistanceConfig(friend_names=' 甲 ;乙；丙\n丁\r\n甲；')
        self.assertEqual(conf.friends, ['甲', '乙', '丙', '丁'])


class MetaDemonAssistAssetsTests(unittest.TestCase):
    def test_share_panel_assets_present(self):
        for name in (
            'I_MD_INVITE',
            'I_MD_INVITE_FRIENDS',
            'I_MD_FRIEND_SELECTED',
            'O_MD_FRIENDS',
            'S_MD_SWIPE_FRIEND_UP',
            'I_MD_SUMMON_BOSS',
            'I_MD_SETTLING',
        ):
            self.assertTrue(hasattr(MetaDemonAssets, name), name)


class MetaDemonAssistTaskTests(unittest.TestCase):
    def test_run_dispatches_assist_mode(self):
        source = inspect.getsource(ScriptTask.run)
        self.assertIn('MetaDemonMode.BOSS_ASSIST', source)
        self.assertIn('run_assistance', source)

    def test_ticket_switch_accepts_sequence(self):
        parameters = inspect.signature(ScriptTask.check_and_switch_ticket).parameters
        self.assertIn('sequence', parameters)
        self.assertIsNone(parameters['sequence'].default)

    def test_generation_increments_on_confirmed_summon(self):
        source = inspect.getsource(ScriptTask.check_and_switch_ticket)
        self.assertIn('self.boss_generation += 1', source)
        # 召唤确认（看到挑战按钮）之后才更新鬼王级别，避免把残留鬼王当成刚召唤的六星
        fire_index = source.index('self.appear(self.I_MD_FIRE)')
        assign_index = source.index('self.cur_boss_type = target_boss_type')
        self.assertLess(fire_index, assign_index)


class GhostOfferingTests(unittest.TestCase):
    @staticmethod
    def _task(done=False, total_count=0):
        return SimpleNamespace(
            start_time=datetime.now() - timedelta(minutes=1),
            limit_time=timedelta(minutes=45),
            limit_count=50,
            total_count=total_count,
            State=SimpleNamespace(done=done),
            conf=SimpleNamespace(assistance_config=MetaDemonAssistanceConfig()),
        )

    def test_within_limit(self):
        offering = assistance.GhostOffering(self._task())
        self.assertTrue(offering.within_limit())
        self.assertFalse(assistance.GhostOffering(self._task(done=True)).within_limit())
        self.assertFalse(assistance.GhostOffering(self._task(total_count=50)).within_limit())

    def test_normalize_name(self):
        self.assertEqual(assistance.GhostOffering.normalize_name(' 张 三\t'), '张三')

    def test_run_assistance_requires_friends(self):
        task = SimpleNamespace(
            config=SimpleNamespace(
                meta_demon=SimpleNamespace(
                    assistance_config=MetaDemonAssistanceConfig(
                        role=AssistanceRole.OFFERING, friend_names=''
                    )
                )
            )
        )
        with self.assertRaises(RequestHumanTakeover):
            assistance.run_assistance(task)

    def test_run_assistance_assist_role_not_implemented(self):
        calls = {}

        def set_next_run(task, success):
            calls['task'] = task
            calls['success'] = success

        task = SimpleNamespace(
            config=SimpleNamespace(
                meta_demon=SimpleNamespace(
                    assistance_config=MetaDemonAssistanceConfig(role=AssistanceRole.ASSIST)
                )
            ),
            set_next_run=set_next_run,
        )
        with self.assertRaises(TaskEnd):
            assistance.run_assistance(task)
        self.assertEqual(calls, {'task': 'MetaDemon', 'success': False})


if __name__ == '__main__':
    unittest.main()
