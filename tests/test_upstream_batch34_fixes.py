# This Python file uses the following encoding: utf-8
"""批次 34 上游修复回归测试。

本轮可落地 4 项（上游架构与本地不同，按语义手工移植）：
1. ``df572d01c`` + ``181801d1c`` + ``a3e6e028``（PR #2006）：悬赏地点数量 OCR 漏读时
   收紧上下留白（``y+7, h-14``）重试一次，且保留本地更宽松的「数/教量」匹配；
2. ``1fd87d34`` 自有分支：探索退出期间回到主界面不能重新开战而取消已请求的退出；
3. ``23edaa78`` 自有分支：超鬼王 1~6 星召唤票阈值统一回落到 0.8；
4. ``5ba75f9b``（PR #1979）：登录选服「已有角色」OCR 区域左扩并加宽。

判退：``692ee2156``（AreaBoss 动态数量/重名跳过）与 ``f636e9d99`` / ``043d3aa92``
（六道月海选岛）依赖本地不存在的动态计数与 island marker 架构；``4a6ad558`` /
``5ba75f9b`` 的 GeneralBattle 主体依赖本地未引入的 ``battle_wait``；``657bb1b3``
main16 模板与本地区服/皮肤 ROI 不匹配；``9cfb4d29`` / ``d9c28f51`` 为上游仓库自动化；
``f219e835`` / ``66f7d818`` / ``fbfff834`` 对应本地不存在的 CustomTask / MetaDemonTicket /
GameUi 页面模块。
"""
import inspect
import json
import unittest
from pathlib import Path

from tasks.Component.SwitchAccount.assets import SwitchAccountAssets
from tasks.Exploration.base import BaseExploration
from tasks.Exploration.script_task import ScriptTask as ExplorationTask
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.WantedQuests.script_task import ScriptTask as WantedQuestsTask
from tasks.WantedQuests.script_task import _parse_location_info


class WantedQuestsLocationRetryTests(unittest.TestCase):
    def test_parse_half_width(self):
        match = _parse_location_info('荒川之怒·壹 数量:4')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), '荒川之怒·壹')
        self.assertEqual(int(match.group(2)), 4)

    def test_parse_full_width(self):
        match = _parse_location_info('荒川之怒·壹（数量：4）')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), '荒川之怒·壹')
        self.assertEqual(int(match.group(2)), 4)

    def test_parse_ocr_error_jiao(self):
        match = _parse_location_info('荒川之怒·壹 教量:4')
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(2)), 4)

    def test_parse_requires_quantity(self):
        self.assertIsNone(_parse_location_info('荒川之怒·壹'))

    def test_build_wq_info_retries_with_trimmed_roi(self):
        source = inspect.getsource(WantedQuestsTask.build_wq_info)
        self.assertIn('_parse_location_info(wq_info_txt)', source)
        self.assertIn('retry = copy(info_rule)', source)
        self.assertIn('retry.roi = [x, y + 7, w, h - 14]', source)
        self.assertIn('_parse_location_info(retry.ocr(self.device.image))', source)


class ExplorationExitStateTests(unittest.TestCase):
    def test_fire_keeps_exit_flag(self):
        source = inspect.getsource(BaseExploration.fire)
        self.assertNotIn('self.need_exit = False', source)

    def test_run_on_exp_main_quits_before_restart(self):
        source = inspect.getsource(ExplorationTask.run_on_exp_main)
        self.assertIn('if self.need_exit:', source)
        self.assertIn('self.quit_exp_main()', source)


class MetaDemonTicketThresholdTests(unittest.TestCase):
    ITEMS = {
        'I_MD_ONE_STAR': 'md_one_star',
        'I_MD_TWO_STARS': 'md_two_stars',
        'I_MD_THREE_STARS': 'md_three_stars',
        'I_MD_FOUR_STARS': 'md_four_stars',
        'I_MD_FIVE_STARS': 'md_five_stars',
        'I_MD_SIX_STARS': 'md_six_stars',
    }

    def test_threshold_is_point_eight(self):
        for attr in self.ITEMS:
            self.assertEqual(getattr(MetaDemonAssets, attr).threshold, 0.8, attr)

    def test_image_json_matches_assets(self):
        data = json.loads(Path('tasks/MetaDemon/md/image.json').read_text(encoding='utf-8'))
        by_name = {entry['itemName']: entry for entry in data}
        for attr, item_name in self.ITEMS.items():
            rule = getattr(MetaDemonAssets, attr)
            entry = by_name[item_name]
            self.assertEqual(entry['threshold'], rule.threshold, item_name)
            self.assertEqual(entry['roiFront'], ','.join(map(str, rule.roi_front)), item_name)


class SwitchAccountSelectSvrRoiTests(unittest.TestCase):
    def test_roi_widened_to_left(self):
        rule = SwitchAccountAssets.O_SA_CHECK_SELECT_SVR
        self.assertEqual(tuple(rule.roi), (231, 145, 102, 32))
        self.assertEqual(tuple(rule.area), (231, 141, 103, 38))


if __name__ == '__main__':
    unittest.main()
