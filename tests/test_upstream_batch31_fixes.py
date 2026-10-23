# This Python file uses the following encoding: utf-8
"""批次 31 上游修复回归测试。

本批落地三项：

1. ``4354df46`` + ``8bbf87b8``（runhey/dev+master，PR #1963）fix(Dokan)：
   修正馆主等级-修习模板图，并把 ``I_CENTER_GUANZHU_XIUXI`` 阈值 0.8 → 0.7。
2. ``51dbf564``（xylolit-mu/self）：加成开关资产按「金币 / 经验 / 通用」拆分，
   避免 ``set_switch_area`` 共用同一份 roi_back 互相覆盖；寮宴会兼容第二种旗帜。
3. ``1410590f`` + ``fa7a87e7`` + ``47a3a3bc``（kongdr418/mine + xylolit-mu/self）：
   商店槽位 ``C_SHIKIGAMI_1~5`` 是合法的反复点击，需清理点击记录，
   否则累计到 10 次触发 ``GameTooManyClickError``。

Chess 新版（frame/scatter 框架）整链替换判「需立项」，不在本批。
"""
import hashlib
import inspect
import json
import unittest
from pathlib import Path

from tasks.Chess.runtime.economy import ChessEconomyMixin
from tasks.Chess.strategy.shikigami_catalog import SHIKIGAMI_BY_ROMAJI
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Dokan.assets import DokanAssets
from tasks.GuildBanquet.assets import GuildBanquetAssets
from tasks.GuildBanquet.script_task import ScriptTask as GuildBanquetTask

DOKAN_TEMPLATE = Path('tasks/Dokan/res/res_ryou_dokan_center_guanzhu_xiuxi.png')
DOKAN_TEMPLATE_SHA256 = '26ccd12917bdf9abca5a2a3d4746175da970bb8692e9205509ee64b4173694b9'


# ------------------------------------------------------------------ Dokan


class DokanLeaderTemplateTests(unittest.TestCase):
    def test_threshold_lowered_to_07(self):
        self.assertEqual(DokanAssets.I_CENTER_GUANZHU_XIUXI.threshold, 0.7)
        self.assertEqual(
            tuple(DokanAssets.I_CENTER_GUANZHU_XIUXI.roi_front),
            (0, 0, 1280, 720),
        )

    def test_image_json_matches_asset(self):
        data = json.loads(
            Path('tasks/Dokan/res/image.json').read_text(encoding='utf-8')
        )
        item = next(
            entry for entry in data
            if entry['itemName'] == 'center_guanzhu_xiuxi'
        )
        self.assertEqual(item['threshold'], 0.7)
        self.assertEqual(item['imageName'], DOKAN_TEMPLATE.name)

    def test_template_file_is_corrected_version(self):
        payload = DOKAN_TEMPLATE.read_bytes()
        self.assertTrue(payload.startswith(b'\x89PNG'))
        self.assertEqual(hashlib.sha256(payload).hexdigest(), DOKAN_TEMPLATE_SHA256)


# ------------------------------------------------------------ GeneralBuff


class _FakeRule:
    """只带 roi_back 的规则替身，用于验证 set_switch_area 的落点。"""

    def __init__(self, name='fake'):
        self.name = name
        self.roi_back = None


class GeneralBuffSwitchAreaTests(unittest.TestCase):
    def _make_buff(self):
        buff = object.__new__(GeneralBuff)
        for attr in (
            'I_BUFF_OPEN_YELLOW', 'I_GOLD_OPEN_YELLOW',
            'I_EXPERIENCE_OPEN_YELLOW', 'I_BUFF_CLOSE_RED',
            'I_GOLD_CLOSE_RED', 'I_EXPERIENCE_CLOSE_RED',
        ):
            setattr(buff, attr, _FakeRule(attr))
        return buff

    def test_assets_are_split_by_kind(self):
        for attr in (
            'I_BUFF_OPEN_YELLOW', 'I_GOLD_OPEN_YELLOW',
            'I_EXPERIENCE_OPEN_YELLOW', 'I_BUFF_CLOSE_RED',
            'I_GOLD_CLOSE_RED', 'I_EXPERIENCE_CLOSE_RED',
        ):
            self.assertTrue(hasattr(GeneralBuff, attr), attr)
        for legacy in ('I_OPEN_YELLOW', 'I_CLOSE_RED'):
            self.assertFalse(hasattr(GeneralBuff, legacy), legacy)

    def test_image_json_registers_all_kinds(self):
        data = json.loads(
            Path('tasks/Component/GeneralBuff/gb/image.json').read_text(encoding='utf-8')
        )
        names = {entry['itemName'] for entry in data}
        for name in (
            'buff_open_yellow', 'buff_close_red',
            'gold_open_yellow', 'gold_close_red',
            'experience_open_yellow', 'experience_close_red',
        ):
            self.assertIn(name, names)
        self.assertNotIn('open_yellow', names)
        self.assertNotIn('close_red', names)
        for entry in data:
            if entry['itemName'].endswith(('open_yellow', 'close_red')):
                path = Path('tasks/Component/GeneralBuff/gb') / entry['imageName']
                self.assertTrue(path.exists(), path)

    def test_set_switch_area_only_touches_requested_kind(self):
        buff = self._make_buff()
        buff.set_switch_area((11, 22, 33, 44), kind='gold')
        self.assertEqual(buff.I_GOLD_OPEN_YELLOW.roi_back, [11, 22, 33, 44])
        self.assertEqual(buff.I_GOLD_CLOSE_RED.roi_back, [11, 22, 33, 44])
        self.assertIsNone(buff.I_BUFF_OPEN_YELLOW.roi_back)
        self.assertIsNone(buff.I_EXPERIENCE_OPEN_YELLOW.roi_back)

    def test_set_switch_area_defaults_to_buff_kind(self):
        buff = self._make_buff()
        buff.set_switch_area((1, 2, 3, 4))
        self.assertEqual(buff.I_BUFF_OPEN_YELLOW.roi_back, [1, 2, 3, 4])
        self.assertEqual(buff.I_BUFF_CLOSE_RED.roi_back, [1, 2, 3, 4])
        self.assertIsNone(buff.I_GOLD_OPEN_YELLOW.roi_back)

    def test_each_toggle_uses_its_own_kind(self):
        sources = {
            'gold_50': inspect.getsource(GeneralBuff.gold_50),
            'gold_100': inspect.getsource(GeneralBuff.gold_100),
            'exp_50': inspect.getsource(GeneralBuff.exp_50),
            'exp_100': inspect.getsource(GeneralBuff.exp_100),
            'awake': inspect.getsource(GeneralBuff.awake),
            'soul': inspect.getsource(GeneralBuff.soul),
        }
        self.assertIn('I_GOLD_CLOSE_RED', sources['gold_50'])
        self.assertIn('I_GOLD_OPEN_YELLOW', sources['gold_100'])
        self.assertIn('kind="gold"', sources['gold_50'])
        self.assertIn('kind="gold"', sources['gold_100'])
        self.assertIn('I_EXPERIENCE_CLOSE_RED', sources['exp_50'])
        self.assertIn('I_EXPERIENCE_OPEN_YELLOW', sources['exp_100'])
        self.assertIn('kind="experience"', sources['exp_50'])
        self.assertIn('kind="experience"', sources['exp_100'])
        self.assertIn('I_BUFF_CLOSE_RED', sources['awake'])
        self.assertIn('I_BUFF_OPEN_YELLOW', sources['soul'])
        for legacy in ('I_CLOSE_RED', 'I_OPEN_YELLOW'):
            for name, source in sources.items():
                self.assertNotIn(legacy + ',', source.replace(
                    'I_GOLD_' + legacy, '').replace('I_EXPERIENCE_' + legacy, ''
                    ).replace('I_BUFF_' + legacy, ''), name)


# ------------------------------------------------------------ GuildBanquet


class GuildBanquetSecondFlagTests(unittest.TestCase):
    def test_second_flag_asset_registered(self):
        self.assertEqual(
            tuple(GuildBanquetAssets.I_BANQUET_FLAG_2.roi_front),
            (972, 12, 33, 60),
        )
        self.assertEqual(
            tuple(GuildBanquetAssets.I_BANQUET_FLAG_2.roi_back),
            (967, 7, 43, 70),
        )
        self.assertTrue(
            Path('tasks/GuildBanquet/res/res_banquet_flag_2.png').exists()
        )

    def test_image_json_matches_asset(self):
        data = json.loads(
            Path('tasks/GuildBanquet/res/image.json').read_text(encoding='utf-8')
        )
        item = next(entry for entry in data if entry['itemName'] == 'banquet_flag_2')
        self.assertEqual(item['roiFront'], '972,12,33,60')
        self.assertEqual(item['roiBack'], '967,7,43,70')
        self.assertEqual(item['threshold'], 0.8)

    def _make_task(self, second_only):
        task = object.__new__(GuildBanquetTask)

        def _appear(rule):
            if rule is GuildBanquetAssets.I_BANQUET_FLAG_2:
                return True
            return False if second_only else True

        task.appear = _appear
        return task

    def test_visible_when_only_second_flag_matches(self):
        task = self._make_task(second_only=True)
        self.assertTrue(task._banquet_flag_visible())

    def test_run_uses_combined_flag_check(self):
        source = inspect.getsource(GuildBanquetTask.run)
        self.assertEqual(source.count('self._banquet_flag_visible()'), 2)
        self.assertNotIn('self.appear(self.I_BANQUET_FLAG)', source)


# ------------------------------------------------------------------ Chess


class _FakeDevice:
    def __init__(self):
        self.removed = []

    def click_record_remove(self, rule):
        self.removed.append(str(rule))
        return 1


class _Named:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class ChessShopClickRecordTests(unittest.TestCase):
    def _make_economy(self):
        economy = object.__new__(ChessEconomyMixin)
        economy.I_EXPERIENCE = _Named('experience')
        economy.I_REFRESH = _Named('refresh')
        for index in range(1, 6):
            setattr(economy, f'C_SHIKIGAMI_{index}', _Named(f'shikigami_{index}'))
        economy.device = _FakeDevice()
        return economy

    def test_clear_click_history_includes_shop_slots(self):
        economy = self._make_economy()
        economy._clear_economy_click_history()
        self.assertEqual(
            set(economy.device.removed),
            {
                'experience', 'refresh',
                'shikigami_1', 'shikigami_2', 'shikigami_3',
                'shikigami_4', 'shikigami_5',
            },
        )
        self.assertEqual(len(economy.device.removed), 7)

    def test_clear_click_history_tolerates_missing_slots(self):
        """槽位记录本就不存在时也应逐项调用，不应提前中断。"""
        economy = self._make_economy()
        economy.device.click_record_remove = lambda rule: 0
        economy._clear_economy_click_history()  # 不抛异常即可

    def test_buy_clears_click_record_before_clicking(self):
        economy = self._make_economy()
        slot_rule = _Named('shikigami_1')
        romaji = next(iter(SHIKIGAMI_BY_ROMAJI))
        events = []

        economy.SHOP_BUY_TIMEOUT = 5.0
        economy.SCREENSHOT_INTERVAL = 0.0
        economy._is_purchase_allowed = lambda: True
        economy._can_afford_shop_shikigami = lambda *args, **kwargs: True
        economy._shikigami_display_name = lambda name: name
        economy.screenshot = lambda: None
        matches = [{'source': 'avatar', 'score': 0.99}, None]

        def _recognize(*args, **kwargs):
            return matches.pop(0)

        economy._recognize_shop_slot = _recognize
        economy.click = lambda rule: events.append(('click', str(rule)))
        economy.device.click_record_remove = lambda rule: events.append(
            ('remove', str(rule))
        )

        self.assertTrue(economy._buy_shop_slot(1, slot_rule, romaji))
        self.assertEqual(events[0], ('remove', 'shikigami_1'))
        self.assertEqual(events[1], ('click', 'shikigami_1'))
        self.assertEqual(
            events[2], ('remove', 'shikigami_1'),
            '购买成功后应清理该格点击记录，供下一张卡使用',
        )

    def test_refresh_clears_click_record_of_changed_slots(self):
        economy = self._make_economy()
        rules = {index: _Named(f'shikigami_{index}') for index in range(1, 6)}
        economy.ECONOMY_CONFIRM_RETRIES = 1
        economy.SHOP_REFRESH_CHANGED_SLOT_MINIMUM = 3
        economy.ACTION_SETTLE_INTERVAL = 0.0
        economy._shop_slots = lambda: [(i, rules[i]) for i in range(1, 6)]
        economy._clear_economy_click_history = lambda: None
        economy.appear = lambda rule: True
        economy.screenshot = lambda: None
        economy.click = lambda rule: None
        economy._shop_slot_refresh_snapshot = lambda: {
            i: {'name': 'x'} for i in range(1, 6)
        }
        economy._shop_refresh_changed_slots = lambda before, after: (
            [1, 3, 5], {i: 0.0 for i in range(1, 6)},
        )

        self.assertEqual(economy._click_shop_refresh_and_confirm_slots(False), 'success')
        self.assertEqual(
            sorted(economy.device.removed),
            ['shikigami_1', 'shikigami_3', 'shikigami_5'],
        )

    def test_source_pins_click_record_removal(self):
        source = inspect.getsource(ChessEconomyMixin._buy_shop_slot)
        remove_at = source.index('self.device.click_record_remove(click_rule)')
        click_at = source.index('self.click(click_rule)')
        self.assertLess(remove_at, click_at)
        self.assertIn('self.device.click_record_remove(click_rule)', source[click_at:])


if __name__ == '__main__':
    unittest.main()
