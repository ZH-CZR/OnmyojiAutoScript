# This Python file uses the following encoding: utf-8
"""AutoCheckinBigGod 游戏内领取流程回归测试（移植自 Maratrain 9023e04 + 54302449）。

覆盖点：
- 收尾顺序：先关净残留弹层，再还原镜头，最后独立 15s 窗口验证回庭院；
- 镜头还原优先「进阴阳寮再退出」，失败/异常才降级 swipe；
- pan_count 为 0 时不做任何镜头动作；
- script_task 挂载点（继承 GameClaimMixin + 4 处 _run_game_claim 调用）；
- 11 个 I_GAME_* 资产与模板文件、image.json 登记保持一致。
"""
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tasks.AutoCheckinBigGod import game_claim as gc
from tasks.AutoCheckinBigGod.assets import AutoCheckinBigGodAssets
from tasks.GameUi.assets import GameUiAssets
from tasks.GlobalGame.assets import GlobalGameAssets

ROOT = Path(__file__).resolve().parents[1]
GAME_ASSETS = [name for name in vars(AutoCheckinBigGodAssets) if name.startswith('I_GAME_')]


class _Stub:
    """只实现收尾/还原依赖的接口，避免构造完整 BaseTask。"""

    I_CHECK_MAIN = object()
    I_GAME_WELFARE_TITLE = object()
    I_GAME_POPUP_CLOSE = object()
    I_GAME_PANEL_CLOSE = object()
    I_UI_BACK_RED = object()

    def __init__(self):
        self.events = []
        self.device = Mock()

    def screenshot(self):
        pass

    def appear(self, target, threshold=None):
        return False

    def appear_then_click(self, target, interval=None, threshold=None):
        return False

    def ui_reward_appear_click(self):
        return False

    def _game_restore_camera(self, pan_count):
        self.events.append(('restore', pan_count))

    def _game_restore_camera_via_guild(self):
        self.events.append('guild_restore')
        return True

    def _game_swipe_restore(self, pan_count):
        self.events.append(('swipe_restore', pan_count))


class _CloseTimer:
    """总收尾窗口永不到点，验证窗口（15s）立即到点，避免测试空转。"""

    def __init__(self, seconds):
        self.seconds = seconds
        _CloseTimer.recorded.append(seconds)

    def start(self):
        return self

    def reached(self):
        return self.seconds == gc.CLOSE_VERIFY_SECONDS


_CloseTimer.recorded = []


class CloseAfterClaimTests(unittest.TestCase):
    def setUp(self):
        _CloseTimer.recorded = []

    def test_popups_closed_before_camera_restore(self):
        stub = _Stub()
        welfare_visible = [True]

        def appear(target, threshold=None):
            if target is _Stub.I_GAME_WELFARE_TITLE:
                return welfare_visible.pop(0) if welfare_visible else False
            return False

        def appear_then_click(target, interval=None, threshold=None):
            if target is _Stub.I_GAME_POPUP_CLOSE:
                stub.events.append('popup_close')
                return True
            return False

        stub.appear = appear
        stub.appear_then_click = appear_then_click

        with patch.object(gc, 'Timer', _CloseTimer), patch.object(gc.time, 'sleep', lambda _: None):
            gc.GameClaimMixin._game_close_after_claim(stub, pan_count=2)

        self.assertEqual(stub.events, ['popup_close', ('restore', 2)],
                         '必须先在弹层阶段关掉福利中心弹窗，再还原镜头')
        self.assertEqual(_CloseTimer.recorded, [gc.CLOSE_YARD_SECONDS, gc.CLOSE_VERIFY_SECONDS],
                         '验证回庭院必须使用独立的 15s 窗口')


class RestoreCameraTests(unittest.TestCase):
    def test_prefers_guild_restore(self):
        stub = _Stub()
        gc.GameClaimMixin._game_restore_camera(stub, pan_count=2)
        self.assertEqual(stub.events, ['guild_restore'])
        self.assertFalse(stub.device.swipe.called)

    def test_falls_back_to_swipe_when_guild_fails(self):
        stub = _Stub()
        stub._game_restore_camera_via_guild = Mock(return_value=False)

        with patch.object(gc.time, 'sleep', lambda _: None):
            gc.GameClaimMixin._game_restore_camera(stub, pan_count=2)

        self.assertEqual(stub.events, [('swipe_restore', 2)])

    def test_falls_back_to_swipe_when_guild_raises(self):
        stub = _Stub()
        stub._game_restore_camera_via_guild = Mock(side_effect=RuntimeError('boom'))

        with patch.object(gc.time, 'sleep', lambda _: None):
            gc.GameClaimMixin._game_restore_camera(stub, pan_count=1)

        self.assertEqual(stub.events, [('swipe_restore', 1)])

    def test_no_pan_does_nothing(self):
        stub = _Stub()
        gc.GameClaimMixin._game_restore_camera(stub, pan_count=0)
        self.assertEqual(stub.events, [])

    def test_swipe_restore_uses_dedicated_control_name(self):
        stub = _Stub()
        with patch.object(gc.time, 'sleep', lambda _: None):
            gc.GameClaimMixin._game_swipe_restore(stub, 2)
        self.assertEqual(stub.device.swipe.call_count, 2)
        for call in stub.device.swipe.call_args_list:
            self.assertEqual(call.kwargs.get('control_name'), 'ACG_CAM_PAN')


class RestoreCameraViaGuildTests(unittest.TestCase):
    def _stub(self):
        stub = _Stub()
        stub.appear_then_click = Mock(
            side_effect=lambda target, **kwargs: target in (GameUiAssets.I_MAIN_GOTO_GUILD,
                                                            GlobalGameAssets.I_UI_BACK_YELLOW)
        )
        stub._game_wait_appear = Mock(side_effect=[True, True])
        return stub

    def test_enter_guild_then_back_returns_true(self):
        stub = self._stub()
        with patch.object(gc.time, 'sleep', lambda _: None):
            ok = gc.GameClaimMixin._game_restore_camera_via_guild(stub)
        self.assertTrue(ok)
        first_assets = stub._game_wait_appear.call_args_list[0].args[0]
        second_assets = stub._game_wait_appear.call_args_list[1].args[0]
        self.assertEqual(first_assets, (GameUiAssets.I_CHECK_GUILD,))
        self.assertEqual(second_assets, (GameUiAssets.I_CHECK_MAIN,))

    def test_retries_when_guild_entry_missing(self):
        stub = self._stub()
        stub.appear_then_click = Mock(
            side_effect=[False, True, True]
        )
        with patch.object(gc.time, 'sleep', lambda _: None):
            ok = gc.GameClaimMixin._game_restore_camera_via_guild(stub)
        self.assertTrue(ok)
        self.assertEqual(stub.appear_then_click.call_count, 3)


class ScriptTaskMountTests(unittest.TestCase):
    def setUp(self):
        self.src = (ROOT / 'tasks' / 'AutoCheckinBigGod' / 'script_task.py').read_text(encoding='utf-8')

    def test_imports_game_claim_mixin(self):
        self.assertIn('from tasks.AutoCheckinBigGod.game_claim import GameClaimMixin', self.src)

    def test_script_task_inherits_game_claim_mixin(self):
        self.assertIn('class ScriptTask(GameClaimMixin, ManualClaimMixin):', self.src)

    def test_game_claim_called_on_all_paths(self):
        self.assertEqual(self.src.count('self._run_game_claim()'), 5)

    def test_local_board_variant_mounted(self):
        source = (ROOT / 'tasks' / 'AutoCheckinBigGod' / 'game_claim.py').read_text(encoding='utf-8')
        self.assertIn('self.I_GAME_BOARD_RED', source,
                      '本机红木牌曜日牌变体必须参与并列匹配')


class AssetRegistrationTests(unittest.TestCase):
    def test_game_assets_registered(self):
        self.assertEqual(len(GAME_ASSETS), 12)
        for name in GAME_ASSETS:
            path = Path(getattr(AutoCheckinBigGodAssets, name).file)
            self.assertTrue(path.is_file(), f'{name} 模板缺失: {path}')

    def test_image_json_matches_assets(self):
        entries = json.loads((ROOT / 'tasks' / 'AutoCheckinBigGod' / 'res' / 'image.json')
                             .read_text(encoding='utf-8'))
        game_entries = [e for e in entries if e['itemName'].startswith('game_')]
        self.assertEqual(len(game_entries), 12)
        registered = {name.replace('I_GAME_', '').lower() for name in GAME_ASSETS}
        self.assertEqual({e['itemName'].replace('game_', '') for e in game_entries}, registered)


if __name__ == '__main__':
    unittest.main()
