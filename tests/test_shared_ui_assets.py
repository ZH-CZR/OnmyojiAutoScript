# This Python file uses the following encoding: utf-8
"""批次 20「共享 UI 资产统一化」的回归测试。

背景
----
上游把各任务里重复定义的「确认 / 取消 / 勾选」按钮统一收敛到
``GlobalGameAssets`` 的共享资产，并删掉了一批同义私有资产：

* ``GeneralBattle`` / ``RealmRaid`` / ``AbyssShadows`` 等不再各自持有
  ``I_EXIT_ENSURE`` / ``I_FRESH_ENSURE``，统一改用 ``I_UI_CONFIRM``；
* ``SwitchSoul`` 删除 ``I_SOU_SWITCH_SURE``；
* ``GeneralInvite`` 删除 ``I_GI_SURE`` / ``I_GI_CANCEL`` /
  ``I_I_DEFAULT`` / ``I_I_NO_DEFAULT``，改用共享的
  ``I_UI_CONFIRM`` / ``I_UI_CANCEL`` / ``I_UI_CHECK`` / ``I_UI_UNCHECK``；
* 导航未知页兜底关闭列表新增 ``I_UI_BACK_CIRCLE``。

本地专有任务（如 ``QuickLoadout``）虽然不在上游，但也必须沿用共享资产，
否则一旦有人把引用改回已删除的私有资产，构建就会在运行期炸在 ``AttributeError``。

本测试钉死这些不变量：共享资产存在、私有资产确已删除、任务类仍能经 MRO
解析到 ``self.I_UI_CONFIRM`` 等共享资产。
"""
import unittest

from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.assets import GeneralInviteAssets
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.QuickLoadout.quick_loadout import QuickLoadout
from tasks.Component.SwitchSoul.assets import SwitchSoulAssets
from tasks.GameUi.navigator import GameUi
from tasks.GlobalGame.assets import GlobalGameAssets

# 本批统一后的共享确认 / 取消 / 勾选资产。
SHARED_ASSET_NAMES = (
    "I_UI_CONFIRM",
    "I_UI_CANCEL",
    "I_UI_CHECK",
    "I_UI_UNCHECK",
    "I_UI_BACK_CIRCLE",
)


class SharedAssetExistenceTests(unittest.TestCase):
    """共享资产必须存在，私有同义资产必须已被删除。"""

    def test_shared_assets_are_defined_on_global_game(self):
        for name in SHARED_ASSET_NAMES:
            self.assertTrue(hasattr(GlobalGameAssets, name), f"GlobalGameAssets 缺少 {name}")

    def test_general_battle_drops_private_ensure(self):
        self.assertFalse(hasattr(GeneralBattleAssets, "I_EXIT_ENSURE"))

    def test_switch_soul_drops_private_sure(self):
        self.assertFalse(hasattr(SwitchSoulAssets, "I_SOU_SWITCH_SURE"))

    def test_general_invite_drops_private_assets(self):
        for name in ("I_GI_SURE", "I_GI_CANCEL", "I_I_DEFAULT", "I_I_NO_DEFAULT"):
            self.assertFalse(hasattr(GeneralInviteAssets, name), name)


class SharedAssetResolutionTests(unittest.TestCase):
    """任务类必须能经 MRO 解析到共享资产（``self.I_UI_CONFIRM`` 等）。"""

    def test_general_battle_resolves_shared_confirm(self):
        self.assertIs(GeneralBattle.I_UI_CONFIRM, GlobalGameAssets.I_UI_CONFIRM)

    def test_quick_loadout_resolves_shared_confirm(self):
        # 本地专有任务，依赖 SwitchSoulAssets；必须走共享资产而非已删除的私有资产。
        self.assertIs(QuickLoadout.I_UI_CONFIRM, GlobalGameAssets.I_UI_CONFIRM)

    def test_general_invite_resolves_shared_confirm_and_check(self):
        self.assertIs(GeneralInvite.I_UI_CONFIRM, GlobalGameAssets.I_UI_CONFIRM)
        self.assertIs(GeneralInvite.I_UI_CHECK, GlobalGameAssets.I_UI_CHECK)
        self.assertIs(GeneralInvite.I_UI_UNCHECK, GlobalGameAssets.I_UI_UNCHECK)


class UnknownPageCloserTests(unittest.TestCase):
    """导航未知页兜底必须包含新增的 ``I_UI_BACK_CIRCLE``。"""

    def test_default_closers_include_back_circle(self):
        self.assertIn(GlobalGameAssets.I_UI_BACK_CIRCLE, GameUi.DEFAULT_UNKNOWN_CLOSERS)

    def test_default_closers_keep_shared_confirm(self):
        self.assertIn(GlobalGameAssets.I_UI_CONFIRM, GameUi.DEFAULT_UNKNOWN_CLOSERS)


if __name__ == '__main__':
    unittest.main()
