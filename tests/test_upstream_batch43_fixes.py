# This Python file uses the following encoding: utf-8
"""批次 43 上游修复回归测试。

覆盖本次合入的四条上游提交与同批本地修复提交：

1. ``ce9903bf`` 百鬼棋局手牌满且无可操作时出售一张阵容卡（``Chess/runtime``）。
2. ``476617e0`` 删除与 GeneralBuff 重名的 ``I_CLOSE_RED``，Chess 截图顺带点掉红叉。
3. ``d38f6e95`` 狭间暗域确认按钮改用通用 ``I_UI_CONFIRM``。
4. ``0311c189`` 未知页关闭顺序调整 + 种树活动关闭标识搜索区放宽。
5. 同批本地修复提交：超鬼王胜利界面/门票 OCR/队伍锁、探索与寮宴会搜索区、
   悬赏去重按卡清零。

测试原则：资产类断言校验 ``assets.py`` / ``image.json`` / ``png`` 三方一致，
逻辑类断言既做行为验证（可离线构造的），也做关键分支的源码守卫。
"""
import inspect
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tasks.AbyssShadows.assets import AbyssShadowsAssets
from tasks.AbyssShadows.script_task import ScriptTask as AbyssShadowsTask
from tasks.AreaBoss.assets import AreaBossAssets
from tasks.Chess.assets import ChessAssets
from tasks.Chess.runtime.economy import ChessEconomyMixin
from tasks.Chess.runtime.hand_operations import ChessHandOperationsMixin
from tasks.Chess.script_task import ScriptTask as ChessTask
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.navigator import GameUi
from tasks.GlobalGame.assets import GlobalGameAssets
from tasks.GuildBanquet.assets import GuildBanquetAssets
from tasks.KekkaiUtilize.assets import KekkaiUtilizeAssets
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemonTicket.config import TicketGeneralConfig
from tasks.MetaDemonTicket.ticket_farming import metademon_tickets_full
from tasks.Exploration.config import ExplorationLevel

ROOT = Path(__file__).resolve().parents[1]


def _json_entry(rel_path: str, item_name: str):
    """读取 image/ocr json 中指定 itemName 的条目；不存在返回 None。"""
    data = json.loads((ROOT / rel_path).read_text(encoding='utf-8'))
    for entry in data:
        if entry.get('itemName') == item_name:
            return entry
    return None


def _rule_file(rel_rule: str) -> Path:
    """把 ``./tasks/...`` 形式的资产路径转成仓库内绝对路径。"""
    return ROOT / rel_rule.lstrip('./')


def _roi_text(roi) -> str:
    return ','.join(str(v) for v in roi)


class _FakeOcr:
    def __init__(self, value):
        self.value = value

    def ocr_digit_counter(self, image):
        return self.value


class _FakeTicketTask:
    def __init__(self):
        self.device = SimpleNamespace(image='image')

    def appear(self, rule):
        return True


class TestChessHandFullSale(unittest.TestCase):
    """ce9903bf：手牌满且清理无效时出售一张阵容卡。"""

    def test_economy_marks_lineup_recovery(self):
        source = inspect.getsource(ChessEconomyMixin._buy_shop_slot)
        self.assertIn("recovery.get('type') == 'lineup'", source)
        self.assertIn('emergency_cleanup_done = True', source)
        self.assertIn('lineup_sale_done = True', source)

    def test_hand_operations_sells_lineup_when_cleanup_freed_nothing(self):
        source = inspect.getsource(
            ChessHandOperationsMixin._free_one_hand_slot_for_purchase,
        )
        self.assertIn('freed no hand space', source)
        self.assertIn('sell_one_lineup_hand_card()', source)

    def test_chess_burst_closes_red_cross(self):
        source = inspect.getsource(ChessTask._burst)
        self.assertIn('super()._burst()', source)
        self.assertIn('I_UI_BACK_RED', source)
        self.assertTrue(hasattr(ChessTask, 'I_UI_BACK_RED'))


class TestGameUiUnknownPageClosers(unittest.TestCase):
    """0311c189：种树关闭进入未知页兜底，且确认类按钮优先于返回类。"""

    def setUp(self):
        self.closers = list(GameUi.DEFAULT_UNKNOWN_CLOSERS)

    def test_contains_local_and_new_closers(self):
        names = [id(rule) for rule in self.closers]
        self.assertIn(id(GlobalGameAssets.I_UI_BACK_CIRCLE), names)
        self.assertIn(id(KekkaiUtilizeAssets.I_PLANT_TREE_CLOSE), names)

    def test_confirm_before_back(self):
        def _index(rule):
            for i, item in enumerate(self.closers):
                if item is rule:
                    return i
            self.fail(f'{rule} not in DEFAULT_UNKNOWN_CLOSERS')

        self.assertLess(
            _index(GlobalGameAssets.I_UI_CONFIRM),
            _index(GlobalGameAssets.I_UI_BACK_RED),
        )

    def test_no_duplicate_closers(self):
        ids = [id(rule) for rule in self.closers]
        self.assertEqual(len(ids), len(set(ids)))


class TestKekkaiPlantTreeClose(unittest.TestCase):
    """0311c189：种树关闭标识搜索区放宽到 711,52,395,143。"""

    def test_rule_roi(self):
        rule = KekkaiUtilizeAssets.I_PLANT_TREE_CLOSE
        self.assertEqual(_roi_text(rule.roi_front), '777,91,36,34')
        self.assertEqual(_roi_text(rule.roi_back), '711,52,395,143')

    def test_rule_matches_json_and_png(self):
        rule = KekkaiUtilizeAssets.I_PLANT_TREE_CLOSE
        self.assertTrue(_rule_file(rule.file).is_file())
        entry = _json_entry('tasks/KekkaiUtilize/realm/image.json', 'plant_tree_close')
        self.assertIsNotNone(entry)
        self.assertEqual(entry['roiBack'], _roi_text(rule.roi_back))


class TestAbyssShadowsConfirmAsset(unittest.TestCase):
    """d38f6e95：狭间暗域确认按钮统一走 I_UI_CONFIRM。"""

    def test_old_assets_removed(self):
        self.assertFalse(hasattr(AbyssShadowsAssets, 'I_ENSURE_BUTTON'))
        self.assertFalse(hasattr(AbyssShadowsAssets, 'I_START_ENSURE'))
        self.assertFalse((ROOT / 'tasks/AbyssShadows/res/res_ensure_button.png').exists())
        self.assertFalse((ROOT / 'tasks/AbyssShadows/res/res_start_ensure.png').exists())
        self.assertIsNone(_json_entry('tasks/AbyssShadows/res/image.json', 'ensure_button'))
        self.assertIsNone(_json_entry('tasks/AbyssShadows/res/image.json', 'start_ensure'))

    def test_script_uses_shared_confirm(self):
        source = (ROOT / 'tasks/AbyssShadows/script_task.py').read_text(encoding='utf-8')
        self.assertNotIn('I_ENSURE_BUTTON', source)
        self.assertNotIn('I_START_ENSURE', source)
        self.assertGreaterEqual(source.count('self.I_UI_CONFIRM'), 5)


class TestCloseRedDedup(unittest.TestCase):
    """476617e0：删除与 GeneralBuff 重名的 I_CLOSE_RED。"""

    def test_rules_removed(self):
        self.assertFalse(hasattr(AreaBossAssets, 'I_CLOSE_RED'))
        self.assertFalse(hasattr(GameUiAssets, 'I_CLOSE_RED'))
        self.assertIsNone(_json_entry('tasks/AreaBoss/res/image.json', 'close_red'))
        self.assertIsNone(_json_entry('tasks/GameUi/page/image_chess.json', 'close_red'))

    def test_png_removed_and_no_reference(self):
        self.assertFalse((ROOT / 'tasks/AreaBoss/res/res_close_red.png').exists())
        self.assertFalse((ROOT / 'tasks/GameUi/page/page_close_red.png').exists())
        chess_source = (ROOT / 'tasks/Chess/script_task.py').read_text(encoding='utf-8')
        self.assertNotIn('I_CLOSE_RED', chess_source)


class TestMetaDemonWinAssets(unittest.TestCase):
    """本地修复提交：超鬼王胜利界面与队伍锁资产。"""

    def test_win_rule_and_png(self):
        rule = MetaDemonAssets.I_MD_WIN
        self.assertEqual(_roi_text(rule.roi_back), '668,32,282,216')
        self.assertTrue(_rule_file(rule.file).is_file())

    def test_team_lock_rules_match_json(self):
        for rule, item in (
            (GeneralBattleAssets.I_TEAM_LOCK, 'team_lock'),
            (GeneralBattleAssets.I_TEAM_UNLOCK, 'team_unlock'),
        ):
            self.assertTrue(_rule_file(rule.file).is_file())
            entry = _json_entry('tasks/Component/GeneralBattle/lock/image.json', item)
            self.assertIsNotNone(entry)
            self.assertEqual(entry['roiFront'], _roi_text(rule.roi_front))
            self.assertEqual(entry['roiBack'], _roi_text(rule.roi_back))

    def test_metademon_pass_ocr_roi(self):
        rule = GeneralBattleAssets.O_METADEMON_PASS
        self.assertEqual(_roi_text(rule.roi), '1119,7,114,32')
        entry = _json_entry('tasks/Component/GeneralBattle/gb/ocr.json', 'metademon_pass')
        self.assertIsNotNone(entry)
        self.assertEqual(entry['roiFront'], '1119,7,114,32')


class TestMetaDemonTicketGuards(unittest.TestCase):
    """本地修复提交：门票越界按识别错误处理 + 探索章节可配置。"""

    def test_exploration_level_default(self):
        self.assertEqual(
            TicketGeneralConfig().exploration_level,
            ExplorationLevel.EXPLORATION_28,
        )

    def _call(self, current: int, total: int) -> bool:
        fake = _FakeOcr((current, 0, total))
        with mock.patch.object(GeneralBattleAssets, 'O_METADEMON_PASS', fake):
            return metademon_tickets_full(_FakeTicketTask())

    def test_not_full(self):
        self.assertFalse(self._call(10, 30))

    def test_full(self):
        self.assertTrue(self._call(30, 30))

    def test_over_limit_treated_as_ocr_error(self):
        # 当前值不可能超过上限，越界一定是识别错误，不能按“已满”结束任务。
        self.assertFalse(self._call(31, 30))

    def test_invalid_total_not_full(self):
        self.assertFalse(self._call(5, 0))


class TestWantedQuestsPerCardDedupe(unittest.TestCase):
    """本地修复提交：wq_executed_set 每张卡独立，换卡清零。"""

    def test_reset_per_card(self):
        source = (ROOT / 'tasks/WantedQuests/script_task.py').read_text(encoding='utf-8')
        self.assertGreaterEqual(source.count('self.wq_executed_set = set()'), 2)
        self.assertIn('_wq_last_monster', source)


class TestSharedRoiUpdates(unittest.TestCase):
    """本地修复提交：探索标识与寮宴会旗帜搜索区放宽。"""

    def test_exploration_marker(self):
        rule = GameUiAssets.I_CHECK_EXPLORATION
        self.assertEqual(rule.roi_back, (1138, 134, 56, 50))
        entry = _json_entry('tasks/GameUi/page/image_exploration.json', 'check_exploration')
        self.assertIsNotNone(entry)
        self.assertEqual(entry['roiBack'], '1138,134,56,50')

    def test_banquet_flag(self):
        rule = GuildBanquetAssets.I_BANQUET_FLAG
        self.assertEqual(_roi_text(rule.roi_front), '972,10,33,60')
        self.assertEqual(_roi_text(rule.roi_back), '886,0,190,86')
        entry = _json_entry('tasks/GuildBanquet/res/image.json', 'banquet_flag')
        self.assertIsNotNone(entry)
        self.assertEqual(entry['roiFront'], '972,10,33,60')
        self.assertEqual(entry['roiBack'], '886,0,190,86')


class TestAbyssShadowsInstantWin(unittest.TestCase):
    """本地修复提交：战斗瞬结时直接识别胜利界面。"""

    def test_win_branch_present(self):
        source = (ROOT / 'tasks/AbyssShadows/script_task.py').read_text(encoding='utf-8')
        self.assertIn('if self.appear(self.I_WIN):', source)
        self.assertTrue(hasattr(AbyssShadowsTask, 'I_WIN'))


class TestChessAssetsStillLoadable(unittest.TestCase):
    """回归：删除 I_CLOSE_RED 后棋局资产类仍可正常实例化。"""

    def test_chess_assets_loadable(self):
        self.assertTrue(hasattr(GameUiAssets, 'I_CHESS_EXIT'))
        self.assertFalse(hasattr(ChessAssets, 'I_CLOSE_RED'))


if __name__ == '__main__':
    unittest.main()
