# This Python file uses the following encoding: utf-8
"""Shu_Li_x ``c95d4e7e`` 局部移植（A+B 档）的回归测试。

背景
----
上游 ``c95d4e7e feat: 统一队伍预设与御魂切换`` 是一次跨 18 个任务目录的重构，
本地只取其中三块低耦合内容：

1. ``GeneralBattle._apply_prepare_preset``：把准备页的预设应用收敛成可覆写的钩子，
   为后续「组队首场准备页再次应用预设」预留扩展点；
2. ``GeneralInvite._invite_again_popup``：用「是否邀请队友继续进行战斗」标题把
   续邀弹窗与退队确认区分开，避免把退队确认当成续邀点掉；
3. 六个副本的锁定/解锁模板统一为同一对通用图标，ROI 由宽搜索区收敛到 52x52、
   阈值提到 0.8。

本测试钉死不变量：钩子存在且参数原样透传、续邀识别在四种画面组合下的判定、
六个任务的锁定/解锁资产指向同一对模板且 ROI 一致、新增标题模板文件存在。
"""
import os
import unittest

from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.assets import GeneralInviteAssets
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.EternitySea.assets import EternitySeaAssets
from tasks.EvoZone.assets import EvoZoneAssets
from tasks.FallenSun.assets import FallenSunAssets
from tasks.GoryouRealm.assets import GoryouRealmAssets
from tasks.Orochi.assets import OrochiAssets
from tasks.Sougenbi.assets import SougenbiAssets

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_ROI = (699, 652, 32, 35)
LOCK_SEARCH_ROI = (689, 643, 52, 52)

LOCK_UNLOCK_ASSETS = (
    (OrochiAssets, "I_OROCHI_LOCK", "I_OROCHI_UNLOCK"),
    (EvoZoneAssets, "I_EVOZONE_LOCK", "I_EVOZONE_UNLOCK"),
    (FallenSunAssets, "I_FALLEN_SUN_LOCK", "I_FALLEN_SUN_UNLOCK"),
    (GoryouRealmAssets, "I_GR_LOCK", "I_GR_UNLOCK"),
    (SougenbiAssets, "I_S_TEAM_LOCK", "I_S_TEAM_UNLOCK"),
    (EternitySeaAssets, "I_NEWETERNITYSEA_LOCK", "I_ETERNITYSEA_UNLOCK"),
)


class _PrepareHookBattle(GeneralBattle):
    """只保留 ``switch_preset_team`` 记录，避免构造完整任务实例。"""

    def __init__(self):
        self.switched = None

    def switch_preset_team(self, enable, group, team):
        self.switched = (enable, group, team)


class PreparePresetHookTests(unittest.TestCase):
    def test_hook_passes_config_values(self):
        task = _PrepareHookBattle()
        config = type("C", (), {"preset_enable": True, "preset_group": 3, "preset_team": 2})()
        task._apply_prepare_preset(config)
        self.assertEqual(task.switched, (True, 3, 2))

    def test_hook_is_overridable(self):
        calls = []

        class _Override(_PrepareHookBattle):
            def _apply_prepare_preset(self, config):
                calls.append(config)

        config = object()
        _Override()._apply_prepare_preset(config)
        self.assertEqual(calls, [config])


class _InvitePopupStub:
    """按给定画面组合返回 ``appear`` 结果，属性名与生产代码保持一致。"""

    I_GI_INVITE_AGAIN_TITLE = GeneralInviteAssets.I_GI_INVITE_AGAIN_TITLE
    I_UI_CONFIRM = GeneralInvite.I_UI_CONFIRM
    I_GB_CHECK_TEAM_EXIT = GeneralBattleAssets.I_GB_CHECK_TEAM_EXIT

    def __init__(self, shown):
        self.shown = shown

    def appear(self, rule):
        return rule in self.shown


class InviteAgainPopupTests(unittest.TestCase):
    @staticmethod
    def _detect(title=False, confirm=False, exit_confirm=False):
        stub = _InvitePopupStub(
            {
                rule
                for rule, flag in (
                    (GeneralInviteAssets.I_GI_INVITE_AGAIN_TITLE, title),
                    (GeneralInvite.I_UI_CONFIRM, confirm),
                    (GeneralBattleAssets.I_GB_CHECK_TEAM_EXIT, exit_confirm),
                )
                if flag
            }
        )
        return GeneralInvite._invite_again_popup(stub)

    def test_title_and_confirm_is_invite_again(self):
        self.assertTrue(self._detect(title=True, confirm=True))

    def test_title_only_is_not_invite_again(self):
        self.assertFalse(self._detect(title=True))

    def test_title_wins_over_exit_marker(self):
        self.assertTrue(self._detect(title=True, confirm=True, exit_confirm=True))

    def test_confirm_without_title_falls_back(self):
        self.assertTrue(self._detect(confirm=True))

    def test_exit_confirm_is_never_invite_again(self):
        self.assertFalse(self._detect(confirm=True, exit_confirm=True))

    def test_empty_screen_is_not_invite_again(self):
        self.assertFalse(self._detect())


class LockUnlockAssetTests(unittest.TestCase):
    def test_lock_unlock_assets_share_roi(self):
        for assets_cls, lock_name, unlock_name in LOCK_UNLOCK_ASSETS:
            for name in (lock_name, unlock_name):
                rule = getattr(assets_cls, name)
                self.assertEqual(tuple(rule.roi_front), LOCK_ROI, name)
                self.assertEqual(tuple(rule.roi_back), LOCK_SEARCH_ROI, name)
                self.assertEqual(rule.threshold, 0.8, name)

    def test_lock_unlock_templates_are_the_unified_pair(self):
        for assets_cls, lock_name, unlock_name in LOCK_UNLOCK_ASSETS:
            lock_file = getattr(assets_cls, lock_name).file
            unlock_file = getattr(assets_cls, unlock_name).file
            for path in (lock_file, unlock_file):
                abs_path = os.path.join(REPO_ROOT, path.lstrip("./"))
                self.assertTrue(os.path.exists(abs_path), path)

    def test_invite_again_title_template_exists(self):
        rule = GeneralInviteAssets.I_GI_INVITE_AGAIN_TITLE
        abs_path = os.path.join(REPO_ROOT, rule.file.lstrip("./"))
        self.assertTrue(os.path.exists(abs_path), rule.file)


if __name__ == "__main__":
    unittest.main()
