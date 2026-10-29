# This Python file uses the following encoding: utf-8
"""批次 32 上游修复回归测试。

本批按提交时间序移植 13 条上游提交 + 1 条自检补正：

1. ``120c881a`` / ``be5f3c97`` / ``47b9064b``（runhey/dev+master）fix(MysteryShop)：
   蓝票多数量窗口改用 buy_more、按确认按钮单价判断（>85 勾玉不买）、
   余额不够买满时逐张买。
2. ``094b30b9``（runhey/dev）：``BaseTask.wait_until_disappear`` 支持 timeout，
   修复邀请组件在元素一直可见时卡死。
3. ``a9597e77``（runhey/dev）fix(Chess)：卖卡与上御魂前清理点击记录，
   修复合法重复操作触发 ``GameTooManyClickError``。
4. ``329ecfc7``（kongdr418/mine）fix(EternitySea)：队员模式开战前补齐进本、
   选层与锁队检查（冲突解决后保留本地三参 ``check_lock``）。
5. ``e68c2d26``（runhey/dev）fix(GlobalGame)：接受/拒绝/奖励按钮适配新 UI。
6. ``921a2b82``（runhey/dev，PR #1973）fix(WantedQuests)：悬赏封印新 UI 几何，
   追踪弹窗关闭改用通用返回键，目标名改子串包含匹配。
7. ``2db22cc3``（runhey/dev）fix(RichMan)：海汐御魂开启自动选择时一次买完。
8. ``3f085151``（runhey/dev）feat(Dokan)：每次运行都尝试开启道馆，不再限定周一。
9. ``506564c6``（runhey/dev）fix(Costume)：替换皮肤模板后清掉缓存的模板图。
10. ``d1ad2c09``（runhey/dev）fix(Chess)：放宽「打开阵容预设」的搜索区，
    本地 assets.py 同步补正（``4698b48c``）。
11. ``91f7d916``（runhey/dev）feat(annotator)：目录下拉显示任务中文名。

``6360d6a9``（道馆攻击后间隔）判定「已覆盖」：本地 ``run_on_dokan_map``/战斗处
早已显式传 ``server=False``，未再改动。
"""
import importlib
import inspect
import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


def _install_ocr_stub_if_missing() -> None:
    """本机未安装 OCR 依赖时注入最小替身，避免测试无法收集。

    仓库生产依赖 ``ppocronnx``；缺失时 ``module.ocr.ppocr`` /
    ``module.atom.list`` / ``module.ocr.base_ocr`` 都会 import 失败。
    只在真实包不可用时打补丁，装了真实包的环境行为不变。
    """
    try:
        import ppocronnx  # noqa: F401
        from ppocronnx import predict_system  # noqa: F401
        return
    except Exception:  # pragma: no cover - 仅在缺依赖的环境执行
        pass

    class _BoxedResult:
        def __init__(self, box=None, ocr_text='', score=1.0):
            self.box = box
            self.ocr_text = ocr_text
            self.score = score

    class _TextSystem:
        def __init__(self, *args, **kwargs):
            pass

        def detect_and_ocr(self, *args, **kwargs):
            return []

    package = types.ModuleType('ppocronnx')
    predict = types.ModuleType('ppocronnx.predict_system')
    predict.BoxedResult = _BoxedResult
    predict.TextSystem = _TextSystem
    predict.sorted_boxes = lambda boxes: boxes
    package.predict_system = predict
    sys.modules['ppocronnx'] = package
    sys.modules['ppocronnx.predict_system'] = predict


_install_ocr_stub_if_missing()

from tasks.base_task import BaseTask
from tasks.Chess.assets import ChessAssets
from tasks.Chess.runtime.hand_operations import ChessHandOperationsMixin
from tasks.Component.Buy.assets import BuyAssets
from tasks.Component.Buy.buy import Buy
from tasks.Component.Costume.costume_base import CostumeBase
from tasks.Dokan.assets import DokanAssets
from tasks.Dokan.script_task import (
    DokanFinishedError,
    DokanNotStartedError,
    ScriptTask as DokanTask,
)
from tasks.EternitySea.script_task import ScriptTask as EternitySeaTask
from tasks.GlobalGame.assets import GlobalGameAssets
from tasks.RichMan.mall.friendship_points import FriendshipPoints
from tasks.RichMan.mall.scales import Scales
from tasks.WantedQuests.assets import WantedQuestsAssets
from tasks.WantedQuests.script_task import ScriptTask as WantedQuestsTask

BUY_MODULE = importlib.import_module('tasks.Component.Buy.buy')
SCALES_MODULE = importlib.import_module('tasks.RichMan.mall.scales')
HAND_MODULE = importlib.import_module('tasks.Chess.runtime.hand_operations')


# ---------------------------------------------------------------- helpers


class _FakeRule:
    """只带 name / roi 的规则替身。"""

    def __init__(self, name='fake', roi_front=(0, 0, 1, 1), roi_back=None):
        self.name = name
        self.roi_front = list(roi_front)
        self.roi_back = list(roi_back if roi_back is not None else roi_front)


class _FakeOcr:
    """可指定 ocr 返回值的 Ocr 规则替身。"""

    def __init__(self, value, name='fake_ocr', roi=(0, 0, 0, 0)):
        self.name = name
        self.roi = list(roi)
        self._value = value

    def ocr(self, image):
        return self._value


class _AlwaysReachedTimer:
    """立即到期的计时器替身，避免测试真的等待。"""

    def __init__(self, limit=None):
        self.limit = limit

    def start(self):
        return self

    def reset(self):
        return self

    def reached(self):
        return True


class _ClickRecordList(list):
    """记录 remove 调用的 click_record 替身。"""

    def __init__(self, items, events):
        super().__init__(items)
        self.events = events

    def remove(self, value):
        self.events.append(('remove', value))
        super().remove(value)


def _load_json(path) -> list:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _image_entries(path) -> dict:
    return {entry['itemName']: entry for entry in _load_json(path)}


def _join(roi) -> str:
    return ','.join(str(int(value)) for value in roi)


# ------------------------------------------------------------ Buy 蓝票


class BuyMultiPurchaseTests(unittest.TestCase):
    def test_jade_and_price_assets_registered(self):
        self.assertEqual(tuple(BuyAssets.I_BUY_JADE.roi_front), (604, 537, 42, 52))
        self.assertEqual(tuple(BuyAssets.I_BUY_JADE.roi_back), (540, 480, 200, 120))
        self.assertTrue(
            Path('tasks/Component/Buy/buy/buy_buy_jade.png').exists()
        )
        self.assertEqual(BuyAssets.O_BUY_PRICE.name, 'BUY_PRICE')
        self.assertEqual(BuyAssets.O_BUY_PRICE.mode.name, 'DIGIT')

    def test_buy_json_registers_jade_and_price(self):
        images = _image_entries('tasks/Component/Buy/buy/image.json')
        self.assertIn('buy_jade', images)
        self.assertEqual(images['buy_jade']['roiFront'], '604,537,42,52')
        self.assertEqual(images['buy_jade']['roiBack'], '540,480,200,120')
        ocr = _image_entries('tasks/Component/Buy/buy/ocr.json')
        self.assertIn('buy_price', ocr)
        self.assertEqual(ocr['buy_price']['mode'], 'Digit')
        self.assertTrue(Path('tasks/Component/Buy/buy/buy_buy_jade.png').exists())

    def test_buy_one_or_more_signature(self):
        params = inspect.signature(Buy.buy_one_or_more).parameters
        for name in ('start_click', 'check_image', 'number', 'max_price', 'money', 'remain'):
            self.assertIn(name, params)
        self.assertIsNone(params['max_price'].default)
        self.assertIsNone(params['money'].default)
        self.assertIsNone(params['remain'].default)

    def test_price_roi_is_cropped_right_of_jade_icon(self):
        source = inspect.getsource(Buy._buy_read_price)
        self.assertIn('self.O_BUY_PRICE.roi = [x + w, y, 60, h]', source)
        self.assertIn('if price < min_price', source)
        self.assertIn('min_price: int = 40', source)

    def _make_price_reader(self, price, appear=True):
        buy = object.__new__(Buy)
        buy.I_BUY_JADE = _FakeRule('buy_jade', roi_front=(604, 537, 42, 52))
        buy.O_BUY_PRICE = _FakeOcr(price, roi=(0, 0, 0, 0))
        buy.appear = lambda rule: appear
        buy.screenshot = lambda: None
        buy.device = SimpleNamespace(image='image')
        return buy

    def test_read_price_returns_int_and_moves_roi(self):
        buy = self._make_price_reader(90)
        self.assertEqual(buy._buy_read_price(), 90)
        self.assertEqual(buy.O_BUY_PRICE.roi, [646, 537, 60, 52])

    def test_read_price_treats_tiny_value_as_ocr_error(self):
        buy = self._make_price_reader(9)
        self.assertIsNone(buy._buy_read_price())

    def test_read_price_treats_zero_as_ocr_error(self):
        buy = self._make_price_reader(0)
        self.assertIsNone(buy._buy_read_price())

    def test_read_price_returns_none_without_jade_icon(self):
        buy = self._make_price_reader(90, appear=False)
        with mock.patch.object(BUY_MODULE, 'Timer', _AlwaysReachedTimer):
            self.assertIsNone(buy._buy_read_price())

    def _make_with_price(self, price):
        buy = object.__new__(Buy)
        buy._buy_read_price = lambda: price
        calls = []
        buy._buy_cancel = lambda check: calls.append(('cancel', check)) or True
        buy.buy_one = lambda start, check: calls.append(('one', check)) or True
        buy.buy_more = lambda start, number: calls.append(('more', number)) or True
        buy._buy_more_default = lambda start: calls.append(('default',)) or True
        return buy, calls

    def test_price_over_limit_cancels(self):
        buy, calls = self._make_with_price(120)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertFalse(
            buy._buy_with_price(start, check, True, 85, money=1000, remain=3)
        )
        self.assertEqual(calls, [('cancel', check)])

    def test_unknown_price_cancels(self):
        buy, calls = self._make_with_price(None)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertFalse(
            buy._buy_with_price(start, check, True, 85, money=1000, remain=3)
        )
        self.assertEqual(calls, [('cancel', check)])

    def test_single_window_buys_one(self):
        buy, calls = self._make_with_price(85)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertTrue(
            buy._buy_with_price(start, check, False, 85, money=1000, remain=3)
        )
        self.assertEqual(calls, [('one', check)])

    def test_enough_money_buys_all_in_one_call(self):
        buy, calls = self._make_with_price(50)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertTrue(
            buy._buy_with_price(start, check, True, 85, money=1000, remain=5)
        )
        self.assertEqual(calls, [('more', None)])

    def test_buying_one_uses_default_number(self):
        buy, calls = self._make_with_price(50)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertTrue(
            buy._buy_with_price(start, check, True, 85, money=100, remain=3)
        )
        self.assertEqual(calls, [('default',)])

    def test_short_of_money_buys_one_by_one(self):
        buy, calls = self._make_with_price(50)
        start, check = _FakeRule('start'), _FakeRule('check')
        # 100 勾玉只够买 2 张, 但剩余 4 张 -> 每轮只买 1 张, 由调用方循环
        self.assertTrue(
            buy._buy_with_price(start, check, True, 85, money=100, remain=4)
        )
        self.assertEqual(calls, [('default',)])

    def test_cannot_afford_one_cancels(self):
        buy, calls = self._make_with_price(50)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertFalse(
            buy._buy_with_price(start, check, True, 85, money=40, remain=3)
        )
        self.assertEqual(calls, [('cancel', check)])

    def test_no_money_info_buys_one(self):
        buy, calls = self._make_with_price(50)
        start, check = _FakeRule('start'), _FakeRule('check')
        self.assertTrue(
            buy._buy_with_price(start, check, True, 85, money=None, remain=None)
        )
        self.assertEqual(calls, [('default',)])

    def test_buy_window_routes_by_appearance(self):
        cases = [
            ('plus', 85, None, ('with_price', True)),
            ('plus', None, 1, ('default',)),
            ('plus', None, None, ('more', None)),
            ('check', 85, None, ('with_price', False)),
            ('check', None, None, ('one',)),
        ]
        for window, max_price, number, expected in cases:
            with self.subTest(window=window, max_price=max_price, number=number):
                buy = object.__new__(Buy)
                buy.screenshot = lambda: None
                plus = BuyAssets.I_BUY_PLUS
                check = _FakeRule('check')
                buy.appear = lambda rule: rule is plus if window == 'plus' else rule is check
                calls = []
                buy._buy_with_price = (
                    lambda start, image, more, limit, money, remain:
                    calls.append(('with_price', more)) or True
                )
                buy._buy_more_default = lambda start: calls.append(('default',)) or True
                buy.buy_more = lambda start, count: calls.append(('more', count)) or True
                buy.buy_one = lambda start, image: calls.append(('one',)) or True
                result = buy.buy_one_or_more(
                    _FakeRule('start'), check, number=number, max_price=max_price,
                    money=1000, remain=3,
                )
                self.assertTrue(result)
                self.assertEqual(calls, [expected])

    def test_buy_timeout_returns_false(self):
        buy = object.__new__(Buy)
        buy.screenshot = lambda: None
        buy.appear = lambda rule: False
        buy.click = lambda rule, interval=1: False
        with mock.patch.object(BUY_MODULE, 'Timer', _AlwaysReachedTimer):
            self.assertFalse(buy.buy_one_or_more(_FakeRule('start'), _FakeRule('check')))

    def test_mystery_shop_blue_amulet_uses_price_cap(self):
        source = Path('tasks/MysteryShop/script_task.py').read_text(encoding='utf-8')
        self.assertIn('buy_money=85, more_window=True,', source)
        self.assertIn('max_price=85', source)

    def test_friendship_points_pass_price_and_balance(self):
        source = inspect.getsource(FriendshipPoints.buy_mall_one)
        self.assertIn('more_window: bool = False, max_price: int = None', source)
        self.assertIn('max_price=max_price', source)
        self.assertIn('money=current_money', source)
        self.assertIn('remain=_remain', source)
        self.assertIn('return self.buy_one_or_more(buy_button, buy_check, 1)', source)


# ------------------------------------------------------- BaseTask 超时


class BaseTaskTimeoutTests(unittest.TestCase):
    def test_signature_has_optional_timeout(self):
        params = inspect.signature(BaseTask.wait_until_disappear).parameters
        self.assertIn('timeout', params)
        self.assertIsNone(params['timeout'].default)

    def test_source_pins_timeout_timer(self):
        source = inspect.getsource(BaseTask.wait_until_disappear)
        self.assertIn('timeout_timer = Timer(timeout).start() if timeout else None', source)
        self.assertIn('still visible after', source)

    def test_returns_after_target_disappears(self):
        task = object.__new__(BaseTask)
        calls = []

        def _appear(target):
            calls.append(1)
            return len(calls) < 2

        task.screenshot = lambda: None
        task.appear = _appear
        task.wait_until_disappear(_FakeRule('target'))
        self.assertEqual(len(calls), 2)

    def test_timeout_breaks_out_even_if_still_visible(self):
        task = object.__new__(BaseTask)
        task.screenshot = lambda: None
        task.appear = lambda target: True
        task.wait_until_disappear(_FakeRule('target'), timeout=0.01)
        self.assertTrue(task.appear(task) is True)


# ------------------------------------------------------ Chess 点击记录


class ChessHandOperationsTests(unittest.TestCase):
    def _make_hand(self, events, click_record_items):
        hand = object.__new__(ChessHandOperationsMixin)
        hand.device = SimpleNamespace(
            click_record=_ClickRecordList(click_record_items, events)
        )
        return hand

    def test_reset_click_record_clears_duplicates(self):
        events = []
        hand = self._make_hand(events, ['dup', 'dup', 'dup', 'keep'])
        hand._reset_click_record('dup')
        self.assertEqual(hand.device.click_record, ['keep'])
        self.assertEqual([call for call in events if call[0] == 'remove'],
                         [('remove', 'dup')] * 3)

    def test_reset_click_record_without_history_is_noop(self):
        events = []
        hand = self._make_hand(events, ['other'])
        hand._reset_click_record('dup')
        self.assertEqual(hand.device.click_record, ['other'])
        self.assertEqual(events, [])

    def test_sell_hand_card_resets_before_drag(self):
        events = []
        hand = self._make_hand(events, ['CHESS_SELL_UNKNOWN_HAND_CARD'])
        hand.I_EXPERIENCE = _FakeRule('experience', roi_back=(0, 0, 20, 20))
        hand.close_shikigami_specifics_if_open = lambda: events.append(('close',))

        def _drag(device, **kwargs):
            events.append(('drag', kwargs.get('name')))

        with mock.patch.object(HAND_MODULE, 'Press_and_Drag', _drag):
            hand.sell_hand_card(source=(5, 5))

        self.assertEqual(
            events,
            [
                ('remove', 'CHESS_SELL_UNKNOWN_HAND_CARD'),
                ('drag', 'CHESS_SELL_UNKNOWN_HAND_CARD'),
                ('close',),
            ],
        )

    def test_sell_hand_card_source_order(self):
        source = inspect.getsource(ChessHandOperationsMixin.sell_hand_card)
        reset_at = source.index("self._reset_click_record('CHESS_SELL_UNKNOWN_HAND_CARD')")
        drag_at = source.index('Press_and_Drag(')
        self.assertLess(reset_at, drag_at)

    def test_equip_soul_card_resets_before_drag(self):
        events = []
        name = 'CHESS_EQUIP_SOUL_HAKUZOSU_SET_2'
        hand = self._make_hand(events, [name])
        hand._ensure_shop_closed = lambda: True
        hand._soul_target_position = lambda set_index: (300, 400)

        def _drag(device, **kwargs):
            events.append(('drag', kwargs.get('name')))

        with mock.patch.object(HAND_MODULE, 'Press_and_Drag', _drag):
            self.assertTrue(
                hand._equip_soul_card(
                    source=(10, 20), set_index=2, operation_name='HAKUZOSU'
                )
            )

        self.assertEqual(events, [('remove', name), ('drag', name)])

    def test_equip_soul_card_aborts_when_shop_cannot_close(self):
        events = []
        hand = self._make_hand(events, [])
        hand._ensure_shop_closed = lambda: False
        with mock.patch.object(HAND_MODULE, 'Press_and_Drag', lambda *a, **k: events.append('drag')):
            self.assertFalse(
                hand._equip_soul_card(
                    source=(10, 20), set_index=2, operation_name='HAKUZOSU'
                )
            )
        self.assertEqual(events, [])

    def test_equip_soul_card_source_order(self):
        source = inspect.getsource(ChessHandOperationsMixin._equip_soul_card)
        self.assertIn("soul_click_name = f'CHESS_EQUIP_SOUL_{operation_name}_SET_{set_index}'", source)
        self.assertLess(
            source.index('self._reset_click_record(soul_click_name)'),
            source.index('Press_and_Drag('),
        )

    def test_open_lineup_search_area_matches_assets(self):
        self.assertEqual(tuple(ChessAssets.I_OPEN_LINEUP.roi_front), (271, 17, 33, 34))
        self.assertEqual(tuple(ChessAssets.I_OPEN_LINEUP.roi_back), (196, 7, 120, 54))
        images = _image_entries('tasks/Chess/c/image.json')
        self.assertEqual(images['open_lineup']['roiFront'], '271,17,33,34')
        self.assertEqual(images['open_lineup']['roiBack'], '196,7,120,54')
        self.assertTrue(Path('tasks/Chess/c/c_open_lineup.png').exists())


# ------------------------------------------------------ Costume 模板刷新


class CostumeRefreshTests(unittest.TestCase):
    def _make_rule(self, roi_front, roi_back, threshold, file):
        from module.atom.image import RuleImage
        return RuleImage(
            roi_front=roi_front,
            roi_back=roi_back,
            method=RuleImage.METHOD_TEMPLATE_MATCH,
            threshold=threshold,
            file=file,
        )

    def test_refresh_clears_cached_template_state(self):
        image = self._make_rule(
            (0, 0, 10, 10), (0, 0, 10, 10), 0.8,
            './tasks/Chess/c/c_open_lineup.png',
        )
        image._image = 'stale-image'
        image._kp = 'stale-kp'
        image._des = 'stale-des'
        image._match_init = True
        image.name  # 预热 cached_property
        self.assertIn('name', image.__dict__)

        image.refresh()

        self.assertIsNone(image._image)
        self.assertIsNone(image._kp)
        self.assertIsNone(image._des)
        self.assertFalse(image._match_init)
        self.assertNotIn('name', image.__dict__)
        self.assertEqual(image.name, 'C_OPEN_LINEUP')

    def test_refresh_does_not_reintroduce_local_removed_fields(self):
        image = self._make_rule(
            (0, 0, 10, 10), (0, 0, 10, 10), 0.8,
            './tasks/Chess/c/c_open_lineup.png',
        )
        # 本地掩码匹配已服务端化，RuleImage 不应再有 _mask / _mask_loaded
        image.refresh()
        self.assertFalse(hasattr(image, '_mask'))
        self.assertFalse(hasattr(image, '_mask_loaded'))

    def _make_before_after(self):
        before = self._make_rule(
            (1, 2, 3, 4), (5, 6, 7, 8), 0.6,
            './tasks/Component/Costume/main/costume_main_1.png',
        )
        after = self._make_rule(
            (11, 12, 13, 14), (15, 16, 17, 18), 0.9,
            './tasks/Component/Costume/main/costume_main_2.png',
        )
        before._image = 'stale-image'
        before._kp = 'stale-kp'
        before._des = 'stale-des'
        before._match_init = True
        return before, after

    def test_replace_img_copies_geometry_and_refreshes(self):
        before, after = self._make_before_after()
        costume = object.__new__(CostumeBase)
        costume.I_MAIN_GOTO_EXPLORATION = before
        costume.replace_img('I_MAIN_GOTO_EXPLORATION', after)

        self.assertEqual(tuple(before.roi_front), tuple(after.roi_front))
        self.assertEqual(tuple(before.roi_back), tuple(after.roi_back))
        self.assertEqual(before.threshold, after.threshold)
        self.assertEqual(before.file, after.file)
        self.assertIsNone(before._image)
        self.assertIsNone(before._kp)
        self.assertFalse(before._match_init)

    def test_replace_img_can_keep_roi_back(self):
        before, after = self._make_before_after()
        original_back = tuple(before.roi_back)
        costume = object.__new__(CostumeBase)
        costume.I_MAIN_GOTO_EXPLORATION = before
        costume.replace_img('I_MAIN_GOTO_EXPLORATION', after, rp_roi_back=False)
        self.assertEqual(tuple(before.roi_back), original_back)

    def test_replace_img_ignores_unknown_asset(self):
        costume = object.__new__(CostumeBase)
        costume.replace_img('I_NOT_EXIST', _FakeRule('x'))  # 不抛异常即可

    def test_replace_img_source_refreshes_after_file_change(self):
        source = inspect.getsource(CostumeBase.replace_img)
        self.assertIn('asset_before_object.file = asset_after.file', source)
        self.assertLess(
            source.index('asset_before_object.file = asset_after.file'),
            source.index('asset_before_object.refresh()'),
        )


# -------------------------------------------------- EternitySea 开战准备


class EternitySeaPrepareTests(unittest.TestCase):
    def test_prepare_checks_lock_with_three_args(self):
        source = inspect.getsource(EternitySeaTask._prepare_eternity_sea)
        self.assertIn('self.goto_page(page_soul_zones)', source)
        self.assertIn('self._enter_eternity_sea()', source)
        self.assertIn('self.check_layer(layer)', source)
        self.assertIn('self.I_NEWETERNITYSEA_LOCK', source)
        self.assertIn('self.I_ETERNITYSEA_UNLOCK', source)

    def test_leader_and_member_call_prepare(self):
        self.assertTrue(hasattr(EternitySeaTask, 'I_NEWETERNITYSEA_LOCK'))
        self.assertTrue(hasattr(EternitySeaTask, 'I_ETERNITYSEA_UNLOCK'))
        for method, first_action in (
            (EternitySeaTask.run_leader, 'Create team'),
            (EternitySeaTask.run_member, 'stuck_record_add'),
        ):
            source = inspect.getsource(method)
            self.assertEqual(source.count('self._prepare_eternity_sea()'), 1)
            self.assertLess(
                source.index('self._prepare_eternity_sea()'),
                source.index(first_action),
                method,
            )

    def test_prepare_runs_steps_in_order(self):
        # _task_config 是 ScriptTask 的只读 property，用普通对象直接调用未绑定方法
        task = SimpleNamespace()
        events = []
        task._task_config = SimpleNamespace(
            eternity_sea_config=SimpleNamespace(layer=3),
            general_battle_config=SimpleNamespace(lock_team_enable=True),
        )
        task.I_NEWETERNITYSEA_LOCK = _FakeRule('new_eternity_sea_lock')
        task.I_ETERNITYSEA_UNLOCK = _FakeRule('eternity_sea_unlock')
        task.goto_page = lambda page: events.append(('goto', page))
        task._enter_eternity_sea = lambda: events.append(('enter',))
        task.check_layer = lambda layer: events.append(('layer', layer))
        task.check_lock = lambda *args: events.append(('lock',) + args)

        EternitySeaTask._prepare_eternity_sea(task)

        self.assertEqual([event[0] for event in events], ['goto', 'enter', 'layer', 'lock'])
        self.assertEqual(events[2], ('layer', 3))
        self.assertEqual(
            events[3],
            ('lock', True, task.I_NEWETERNITYSEA_LOCK, task.I_ETERNITYSEA_UNLOCK),
        )


# ------------------------------------------------- RichMan 海汐一次买完


class ScalesBookAutoTests(unittest.TestCase):
    def test_book_auto_branch_precedes_remain_clamp(self):
        source = inspect.getsource(Scales._scales_sea)
        self.assertIn('if self.config.rich_man.scales.enable_book_auto:', source)
        self.assertLess(
            source.index('enable_book_auto'),
            source.index('remain_number < buy_number'),
        )

    def test_book_auto_buys_once_with_full_quantity(self):
        source = inspect.getsource(Scales._scales_sea)
        self.assertEqual(source.count('self._scales_buy_more(self.I_SCA_PICTURE_BOOK)'), 1)

    def test_manual_path_only_uses_sea_more(self):
        source = inspect.getsource(Scales._scales_sea)
        self.assertEqual(source.count('self._scales_buy_sea_more(self.I_SCA_PICTURE_BOOK'), 2)

    def _make_scales(self, enable_book_auto, remain, money):
        scales = object.__new__(Scales)
        scales.config = SimpleNamespace(
            rich_man=SimpleNamespace(
                scales=SimpleNamespace(enable_book_auto=enable_book_auto)
            )
        )
        scales.device = SimpleNamespace(image='image')
        scales.screenshot = lambda: None
        scales.appear = lambda rule: True
        scales.O_SCA_NUMBER_SEA = _FakeOcr(remain, name='number_sea')
        scales.O_SCA_RES_SEA = _FakeOcr(money, name='res_sea')
        calls = []
        scales._scales_buy_more = (
            lambda start, number=None: calls.append(('more', start.name, number)) or True
        )
        scales._scales_buy_sea_more = (
            lambda start, number=None: calls.append(('sea_more', start.name, number)) or True
        )
        return scales, calls

    def test_book_auto_buys_all_once(self):
        scales, calls = self._make_scales(True, remain=10, money=2000)
        with mock.patch.object(SCALES_MODULE.time, 'sleep', lambda *_: None):
            scales._scales_sea(3)
        self.assertEqual(calls, [('more', 'SCALES_SCA_PICTURE_BOOK', None)])

    def test_book_auto_skips_when_money_not_enough(self):
        scales, calls = self._make_scales(True, remain=10, money=300)
        scales._scales_sea(3)
        self.assertEqual(calls, [])

    def test_book_auto_skips_on_ocr_error(self):
        scales, calls = self._make_scales(True, remain=10, money='unknown')
        scales._scales_sea(3)
        self.assertEqual(calls, [])

    def test_manual_path_keeps_cycle_split(self):
        scales, calls = self._make_scales(False, remain=5, money=1000)
        with mock.patch.object(SCALES_MODULE.time, 'sleep', lambda *_: None):
            scales._scales_sea(5)
        self.assertEqual(calls, [('sea_more', 'SCALES_SCA_PICTURE_BOOK', 5)])

    def test_zero_remain_returns_before_book_auto(self):
        source = inspect.getsource(Scales._scales_sea)
        self.assertLess(
            source.index('remain_number == 0'),
            source.index('enable_book_auto'),
        )
        scales, calls = self._make_scales(True, remain=0, money=2000)
        scales._scales_sea(3)
        self.assertEqual(calls, [])


# ------------------------------------------------------- Dokan 每次开馆


class DokanOpenEveryRunTests(unittest.TestCase):
    def test_map_handler_always_tries_to_create_dokan(self):
        source = inspect.getsource(DokanTask.run_on_dokan_map)
        self.assertIn('self.creat_dokan()', source)
        self.assertNotIn('weekday', source)

    def test_run_keeps_page_state_machine_and_weekend_guard(self):
        source = inspect.getsource(DokanTask.run)
        self.assertIn('self.get_current_page()', source)
        self.assertIn('case pages.page_dokan_map:', source)
        self.assertIn('monday_to_thursday', source)

    def _make_dokan(self, found_cnt, remain_attack, find_result):
        dokan = object.__new__(DokanTask)
        events = []
        dokan.config = SimpleNamespace(
            dokan=SimpleNamespace(
                dokan_config=SimpleNamespace(
                    try_start_dokan=True,
                    find_dokan_score=8000,
                )
            )
        )
        dokan.found_dokan_cnt = found_cnt
        dokan.appear = lambda rule: rule is DokanAssets.I_RYOU_DOKAN_FINDING_DOKAN
        dokan.update_remain_attack_count = lambda: remain_attack
        dokan.creat_dokan = lambda: events.append('create')
        dokan.find_dokan = lambda score: find_result
        dokan.wait_until_appear = lambda *args: events.append('wait')
        return dokan, events

    def test_creates_dokan_when_not_started(self):
        dokan, events = self._make_dokan(found_cnt=0, remain_attack=5, find_result=True)
        dokan.run_on_dokan_map()
        self.assertEqual(events, ['create', 'wait'])

    def test_skips_when_already_searched_without_entering(self):
        dokan, events = self._make_dokan(found_cnt=1, remain_attack=5, find_result=True)
        with self.assertRaises(DokanNotStartedError):
            dokan.run_on_dokan_map()
        self.assertEqual(events, [])

    def test_no_attack_left_counts_as_finished(self):
        dokan, events = self._make_dokan(found_cnt=0, remain_attack=0, find_result=True)
        with self.assertRaises(DokanFinishedError):
            dokan.run_on_dokan_map()
        self.assertEqual(events, [])


# ------------------------------------------------ WantedQuests 新 UI


WQ_NEW_UI_ASSETS = {
    'I_TRACE_ENABLE': ((1159, 606, 52, 58), (1075, 518, 198, 196)),
    'I_TRACE_DISABLE': ((1154, 609, 68, 58), (1065, 495, 215, 225)),
    'I_TRACE_TRUE': ((1148, 571, 77, 69), (1035, 502, 245, 213)),
    'I_TRACE_FALSE': ((1152, 569, 83, 79), (1051, 481, 229, 239)),
    'I_GOTO_1': ((1075, 287, 62, 29), (1054, 266, 99, 70)),
    'I_WQ_TRACE_ONE_ENABLE': ((1150, 570, 79, 75), (1047, 500, 233, 220)),
    'I_WQ_TRACE_ONE_CHECK_OPENED': ((778, 166, 52, 29), (582, 147, 431, 110)),
    'I_WQ_TRACE_ONE_REALWORLD': ((1173, 579, 51, 54), (1037, 517, 243, 203)),
}

WQ_IMAGE_JSON_NAMES = {
    'I_TRACE_ENABLE': 'trace_enable',
    'I_TRACE_DISABLE': 'trace_disable',
    'I_TRACE_TRUE': 'trace_true',
    'I_TRACE_FALSE': 'trace_false',
    'I_GOTO_1': 'goto_1',
    'I_WQ_TRACE_ONE_ENABLE': 'wq_trace_one_enable',
    'I_WQ_TRACE_ONE_CHECK_OPENED': 'wq_trace_one_check_opened',
    'I_WQ_TRACE_ONE_REALWORLD': 'wq_trace_one_realworld',
}


class WantedQuestsNewUiTests(unittest.TestCase):
    def test_new_ui_geometry(self):
        for attr, (front, back) in WQ_NEW_UI_ASSETS.items():
            with self.subTest(asset=attr):
                rule = getattr(WantedQuestsAssets, attr)
                self.assertEqual(tuple(rule.roi_front), front)
                self.assertEqual(tuple(rule.roi_back), back)

    def test_image_json_matches_new_ui_assets(self):
        images = _image_entries('tasks/WantedQuests/wq/image.json')
        for attr, item in WQ_IMAGE_JSON_NAMES.items():
            with self.subTest(asset=attr, item=item):
                entry = images[item]
                front, back = WQ_NEW_UI_ASSETS[attr]
                self.assertEqual(entry['roiFront'], _join(front))
                self.assertEqual(entry['roiBack'], _join(back))
                self.assertTrue(
                    Path('tasks/WantedQuests/wq') / entry['imageName'].split('/')[-1]
                )

    def test_new_templates_exist(self):
        for entry in _load_json('tasks/WantedQuests/wq/image.json'):
            path = Path('tasks/WantedQuests/wq') / Path(entry['imageName']).name
            if entry['itemName'] in WQ_IMAGE_JSON_NAMES.values():
                self.assertTrue(path.exists(), path)

    def test_ocr_assets_use_horizontal_layout(self):
        self.assertEqual(tuple(WantedQuestsAssets.O_WQ_NUMBER.roi), (541, 14, 97, 33))
        self.assertEqual(tuple(WantedQuestsAssets.O_WQ_MONSTER_TYPE.roi), (634, 154, 483, 52))
        self.assertEqual(WantedQuestsAssets.O_WQ_MONSTER_TYPE.mode.name, 'FULL')
        ocr = _image_entries('tasks/WantedQuests/wq/ocr.json')
        self.assertEqual(ocr['wq_number']['roiFront'], '541,14,97,33')
        self.assertEqual(ocr['wq_monster_type']['roiFront'], '634,154,483,52')

    def test_local_only_assets_kept(self):
        self.assertEqual(
            tuple(WantedQuestsAssets.I_WQ_LIST_TOP_BOTTOM_CHECK.roi_front), (120, 125, 25, 425)
        )
        self.assertEqual(tuple(WantedQuestsAssets.O_WQ_LIST_CHECK.roi), (11, 114, 92, 388))
        self.assertEqual(WantedQuestsAssets.O_WQ_LIST_CHECK.keyword, '悬赏封印')
        self.assertEqual(
            tuple(WantedQuestsAssets.I_WQSE_SPECIAL_FIRE.roi_front), (1116, 555, 96, 96)
        )
        self.assertEqual(
            tuple(WantedQuestsAssets.I_WQSE_SPECIAL_FIRE.roi_back), (1076, 525, 168, 160)
        )
        self.assertTrue(
            Path('tasks/WantedQuests/wq/wq_list_top_bottom_check.png').exists()
        )
        self.assertTrue(
            Path('tasks/WantedQuests/wq/wq_wqse_special_fire.png').exists()
        )

    def test_removed_legacy_assets(self):
        for legacy in ('C_WQ_TRACE_ONE_CLOSE', 'I_WQ_CHECK_TASK'):
            self.assertFalse(hasattr(WantedQuestsAssets, legacy), legacy)
        for template in ('wq_wq_check_task.png', 'wq_tarce_disenable.png'):
            self.assertFalse((Path('tasks/WantedQuests/wq') / template).exists(), template)
        names = {entry['itemName'] for entry in _load_json('tasks/WantedQuests/wq/image.json')}
        self.assertNotIn('wq_check_task', names)

    def test_trace_one_closes_popup_with_common_back(self):
        source = inspect.getsource(WantedQuestsTask.trace_one)
        self.assertIn(
            'self.ui_click_until_smt_disappear(self.I_UI_BACK_RED, '
            'stop=self.I_WQ_TRACE_ONE_CHECK_OPENED',
            source,
        )
        self.assertNotIn('C_WQ_TRACE_ONE_CLOSE', source)

    def test_unwanted_boss_uses_substring_match(self):
        source = inspect.getsource(WantedQuestsTask.execute_mission)
        self.assertIn('any(name in monster_name for name in self.unwanted_boss_name_list)', source)
        self.assertNotIn('if monster_name in self.unwanted_boss_name_list', source)


# ---------------------------------------------------- GlobalGame 新 UI


GG_NEW_UI_ASSETS = {
    'I_G_ACCEPT': ((846, 471, 56, 46), (810, 448, 120, 192), 'g_accept'),
    'I_G_REJECT': ((846, 561, 53, 51), (826, 458, 99, 172), 'g_reject'),
    'I_G_JADE': ((677, 510, 43, 46), (549, 483, 202, 111), 'g_jade'),
    'I_G_CAT_FOOD': ((635, 501, 59, 65), (558, 472, 191, 132), 'g_cat_food'),
    'I_G_DOG_FOOD': ((643, 505, 60, 63), (541, 485, 234, 115), 'g_dog_food'),
    'I_G_IGNORE': ((859, 94, 21, 21), (725, 40, 197, 142), 'g_ignore'),
}


class GlobalGameNewUiTests(unittest.TestCase):
    def test_new_ui_geometry(self):
        for attr, (front, back, _) in GG_NEW_UI_ASSETS.items():
            with self.subTest(asset=attr):
                rule = getattr(GlobalGameAssets, attr)
                self.assertEqual(tuple(rule.roi_front), front)
                self.assertEqual(tuple(rule.roi_back), back)

    def test_image_json_matches_new_ui_assets(self):
        images = _image_entries('tasks/GlobalGame/gg/image.json')
        for attr, (front, back, item) in GG_NEW_UI_ASSETS.items():
            with self.subTest(asset=attr, item=item):
                entry = images[item]
                self.assertEqual(entry['roiFront'], _join(front))
                self.assertEqual(entry['roiBack'], _join(back))

    def test_new_templates_exist(self):
        images = _image_entries('tasks/GlobalGame/gg/image.json')
        for _, _, item in GG_NEW_UI_ASSETS.values():
            path = Path('tasks/GlobalGame/gg') / images[item]['imageName']
            self.assertTrue(path.exists(), path)


# ------------------------------------------------- annotator 中文任务名


class AnnotatorTaskLabelTests(unittest.TestCase):
    def setUp(self):
        self.source = Path(
            'module/server/web/annotator/static/js/app.js'
        ).read_text(encoding='utf-8')

    def test_task_labels_table_exists(self):
        self.assertIn('const TASK_LABELS = {', self.source)

    def test_labels_match_oasx_translations(self):
        for entry in (
            'Chess: "百鬼棋局"',
            'Dokan: "道馆"',
            'EternitySea: "永生之海"',
            'MysteryShop: "神秘商店"',
            'WantedQuests: "悬赏封印"',
        ):
            self.assertIn(entry, self.source)

    def test_option_text_falls_back_to_raw_name(self):
        self.assertIn('const zh = TASK_LABELS[name];', self.source)
        self.assertIn('createOption(select, name, zh ? `${zh}（${name}）` : name);', self.source)


if __name__ == '__main__':
    unittest.main()
