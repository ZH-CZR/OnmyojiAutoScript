# This Python file uses the following encoding: utf-8
"""DailyTrifles「每日收益」功能回归测试（kongdr418/mine 链，2026-10-16）。

上游提交链：``802643de`` → ``97575ca7`` → ``a0fe1e8d`` → ``f3c61ba4`` → ``e6b00fbe`` → ``83377a19``。

覆盖两块**关键功能**：
1. ``module.log_income``（任务侧与服务端共用的新逻辑，``/income`` 接口全靠它）：
   快照解析、日汇总读写与墓碑、日期并集、基准日查找、历史查询、收益报告做差；
2. ``tasks.DailyTrifles.script_task`` 的**分组常量**与顶栏数字解析：
   回归 ``83377a19``（抽取公共模块时漏掉 ``INCOME_MAIN/SCALES/MALL`` 导致 NameError），
   并守住「各分组常量必须恰好覆盖 ``INCOME_FIELDS``」；勾玉/体力改读详情弹窗后，
   另守住弹窗取数正则 ``INCOME_OWNED``、点击资产与宽 ROI 的接线。

同时静态守卫：``module/server/app.py`` 仍注册 ``income_app``，且未破坏既有路由。
"""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from module import log_income
from module.log_income import (
    INCOME_FIELDS,
    INCOME_LOG_PREFIX,
    build_income_report,
    delete_income_days,
    find_income_baseline,
    income_dates,
    income_history,
    income_store_name,
    last_income_record,
    parse_income_record,
    read_income_store,
    write_income_day,
)

# 顶栏数字解析依赖任务模块（与既有 tests/ 一致，直接导入）
from tasks.DailyTrifles.script_task import (
    INCOME_LOG_FIELDS,
    INCOME_MAIN,
    INCOME_MALL,
    INCOME_OWNED,
    INCOME_SCALES,
    INCOME_TOOLTIP,
    parse_income_number,
)

DAY = date(2026, 10, 16)
VALUES = {
    'gold': 100,
    'jade': 200,
    'ap': 300,
    'sca_orochi_scales': 10,
    'sca_reverse_scale': 20,
    'sca_demon_souls': 30,
    'sca_picture_book': 40,
    'mystery_amulet': 50,
}


def snapshot_line(values=VALUES, dt='2026-10-16 01:06:39'):
    fields = ' '.join(f'{name}={value}' for name, value in values.items())
    return f'{dt} | INFO | {INCOME_LOG_PREFIX}{fields}'


class _TempLogs(unittest.TestCase):
    """把 log_income 的目录常量改到临时目录，避免污染真实 log/。"""

    CONFIG = '大号_日常'

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='oas_income_'))
        self.log_dir = self.tmp / 'log'
        self.store_dir = self.log_dir / 'income'
        self.log_dir.mkdir(parents=True)
        self._orig = (log_income.INCOME_LOG_DIR, log_income.INCOME_STORE_DIR)
        log_income.INCOME_LOG_DIR = self.log_dir
        log_income.INCOME_STORE_DIR = self.store_dir

    def tearDown(self):
        log_income.INCOME_LOG_DIR, log_income.INCOME_STORE_DIR = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_day_log(self, day, lines):
        path = log_income.income_day_path(self.CONFIG, day)
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return path


class ParseIncomeRecordTests(_TempLogs):
    def test_valid_line(self):
        parsed = parse_income_record(snapshot_line())
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['dt'], '2026-10-16 01:06:39')
        self.assertEqual(parsed['values'], VALUES)

    def test_rejects_missing_field(self):
        values = dict(VALUES)
        values.pop('gold')
        self.assertIsNone(parse_income_record(snapshot_line(values)))

    def test_rejects_non_integer(self):
        values = dict(VALUES)
        values['gold'] = 'abc'  # 整数解析失败时必须整行作废，避免半截数据参与做差
        self.assertIsNone(parse_income_record(snapshot_line(values)))

    def test_rejects_line_without_prefix(self):
        self.assertIsNone(parse_income_record('2026-10-16 01:06:39 | INFO | nothing here'))

    def test_joins_wrapped_continuation_lines(self):
        """Rich 写文件日志会按 160 列折行，续段没有时间戳，必须拼回一条。"""
        path = self.write_day_log(DAY, [
            snapshot_line(dt='2026-10-16 01:00:00').rsplit(' ', 4)[0],
            ' '.join(f'{name}={VALUES[name]}' for name in INCOME_FIELDS[4:]),
        ])
        parsed = last_income_record(path)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['values'], VALUES)


class IncomeStoreTests(_TempLogs):
    def test_store_name_keeps_full_config_name(self):
        # 日志名会在第一个下划线处截断，日汇总必须保留全名，否则大号_日常/大号_活动 互相覆盖
        self.assertEqual(income_store_name('大号_日常'), '大号_日常')
        self.assertEqual(income_store_name('a/b:c'), 'a_b_c')

    def test_write_then_read_roundtrip_and_overwrite_same_day(self):
        write_income_day(self.CONFIG, DAY, {'dt': '2026-10-16 01:00:00', 'values': VALUES})
        updated = dict(VALUES, gold=999)
        write_income_day(self.CONFIG, DAY, {'dt': '2026-10-16 20:00:00', 'values': updated})

        store = read_income_store(self.CONFIG)
        self.assertEqual(set(store), {DAY.isoformat()})
        self.assertEqual(store[DAY.isoformat()]['values']['gold'], 999)

        lines = log_income.income_store_path(self.CONFIG).read_text(encoding='utf-8').strip().splitlines()
        self.assertEqual(len(lines), 1)  # 一天一行

    def test_income_dates_merges_store_and_log(self):
        older = date(2026, 10, 14)
        write_income_day(self.CONFIG, DAY, {'dt': '', 'values': VALUES})
        self.write_day_log(older, [snapshot_line(dt='2026-10-14 09:00:00')])

        self.assertEqual(income_dates(self.CONFIG), [DAY, older])

    def test_delete_leaves_tombstone_blocking_log_fallback(self):
        """删了日汇总后不能让 7 天内的日志把记录「复活」。"""
        self.write_day_log(DAY, [snapshot_line()])
        write_income_day(self.CONFIG, DAY, {'dt': '2026-10-16 01:06:39', 'values': VALUES})

        self.assertEqual(delete_income_days(self.CONFIG, [DAY]), [DAY.isoformat()])
        self.assertEqual(income_dates(self.CONFIG), [])
        self.assertIsNone(build_income_report(self.CONFIG, DAY))

    def test_find_baseline_skips_gap_days(self):
        """机器停几天后仍要跨天做差，基准取最近一个有记录且更早的日子。"""
        day2, day3, day4 = date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 14)
        write_income_day(self.CONFIG, day2, {'dt': '', 'values': dict(VALUES, gold=100)})
        write_income_day(self.CONFIG, day4, {'dt': '', 'values': dict(VALUES, gold=400)})

        baseline = find_income_baseline(self.CONFIG, DAY)
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline[0], day4)
        self.assertEqual(baseline[1]['values']['gold'], 400)
        self.assertIsNone(find_income_baseline(self.CONFIG, day2))
        self.assertEqual(day3, date(2026, 10, 13))  # 无记录的日子不参与

    def test_history_is_ascending_and_skips_missing_days(self):
        write_income_day(self.CONFIG, date(2026, 10, 14), {'dt': '', 'values': dict(VALUES, gold=1)})
        write_income_day(self.CONFIG, DAY, {'dt': '', 'values': dict(VALUES, gold=2)})

        report = income_history(self.CONFIG, 30)
        self.assertEqual([item['date'] for item in report['records']],
                         ['2026-10-14', '2026-10-16'])

    def test_build_report_computes_delta_and_guards_minus_one(self):
        prev = date(2026, 10, 15)
        write_income_day(self.CONFIG, prev, {'dt': '', 'values': dict(VALUES, gold=100, jade=-1)})
        write_income_day(self.CONFIG, DAY, {'dt': '2026-10-16 01:06:39', 'values': dict(VALUES, gold=175, jade=200)})

        report = build_income_report(self.CONFIG, DAY)
        self.assertEqual(report['baseline_date'], prev.isoformat())
        items = {item['name']: item for item in report['items']}
        self.assertEqual(items['gold']['delta'], 75)
        # 上一次 -1（没读到）时不能算差值，delta 必须为 None 而不是 200 - (-1)
        self.assertIsNone(items['jade']['delta'])


class ParseIncomeNumberTests(unittest.TestCase):
    def test_plain_and_units(self):
        self.assertEqual(parse_income_number('1234'), 1234)
        self.assertEqual(parse_income_number('1,234'), 1234)
        self.assertEqual(parse_income_number('1.2万'), 12000)
        self.assertEqual(parse_income_number('6.33亿'), 633000000)
        self.assertEqual(parse_income_number('5000/5000'), 5000)

    def test_ocr_letter_substitutions(self):
        self.assertEqual(parse_income_number('I234'), 1234)

    def test_rejects_ambiguous_values(self):
        # 无单位却带小数点、OCR 把「万」认成「方」、空串、纯字母，一律判不准
        for text in ('1.2', '1.2方', '', 'abc'):
            self.assertIsNone(parse_income_number(text), msg=text)


class IncomeGroupingConstantsTests(unittest.TestCase):
    """回归 83377a19：抽取公共模块时漏掉分组常量会导致 run_income_stat NameError。"""

    def test_groups_exist_and_cover_all_fields(self):
        for group in (INCOME_MAIN, INCOME_TOOLTIP, INCOME_SCALES, INCOME_MALL):
            self.assertTrue(group)
        covered = {item[0] for item in
                   INCOME_MAIN + INCOME_TOOLTIP + INCOME_SCALES + INCOME_MALL}
        self.assertEqual(covered, set(INCOME_LOG_FIELDS))
        self.assertEqual(len(INCOME_LOG_FIELDS), 8)

    def test_grouping_matches_reading_location(self):
        self.assertEqual({item[0] for item in INCOME_MAIN}, {'gold'})
        self.assertEqual([item[0] for item in INCOME_TOOLTIP], ['jade', 'ap'])
        # 弹窗组比顶栏组多一个点击资产（用来弹出资源详情）
        self.assertTrue(all(len(item) == 5 for item in INCOME_TOOLTIP))
        self.assertEqual({item[0] for item in INCOME_MALL}, {'mystery_amulet'})


class IncomeTooltipTests(unittest.TestCase):
    """勾玉/体力改读「点图标 → 详情弹窗」：顶栏会缩写成 "2.8万"，只有 2 位有效数字。"""

    def test_owned_number_is_parsed_from_panel_text(self):
        for text, expect in (('已拥有:27985', '27985'),
                             ('已拥有：29850', '29850'),
                             ('体力 已拥有 29,850', '29,850')):
            match = INCOME_OWNED.search(text)
            self.assertIsNotNone(match, msg=text)
            self.assertEqual(match.group(1), expect, msg=text)

    def test_owned_regex_ignores_other_panel_text(self):
        # 弹窗里还有说明文字，必须锚定「已拥有」才取数，不能见数字就抓
        self.assertIsNone(INCOME_OWNED.search('进入关卡等需要消耗体力，会随着时间恢复'))

    def test_assets_wired(self):
        from tasks.DailyTrifles.assets import DailyTriflesAssets

        for click_name in ('C_INCOME_JADE_ICON', 'C_INCOME_AP_ICON'):
            rule = getattr(DailyTriflesAssets, click_name)
            self.assertTrue(rule.name, msg=click_name)

        owned = DailyTriflesAssets.O_INCOME_OWNED
        self.assertEqual(owned.keyword, '已拥有')
        # 弹窗 x 位置跟着所点图标走（勾玉面板约 x512 起、体力约 x700 起），ROI 必须够宽
        x, _, w, _ = owned.roi
        self.assertLessEqual(x, 470)
        self.assertGreaterEqual(x + w, 830)
        # 弹窗顶部那行「已拥有」在 y≈168..192，ROI 要盖住整行
        _, y, _, h = owned.roi
        self.assertLessEqual(y, 165)
        self.assertGreaterEqual(y + h, 195)

    def test_click_targets_the_icon_left_of_the_number(self):
        from tasks.DailyTrifles.assets import DailyTriflesAssets

        jade = DailyTriflesAssets.C_INCOME_JADE_ICON.roi_front
        ap = DailyTriflesAssets.C_INCOME_AP_ICON.roi_front
        # 都是顶栏图标，y 必须在顶栏内；x 必须落在对应数字 ROI 的左边（点图标本体，不是它右边的 +）
        self.assertTrue(0 < jade[1] < 50 and 0 < ap[1] < 50)
        self.assertLess(jade[0], DailyTriflesAssets.O_INCOME_JADE.roi[0])
        self.assertLess(ap[0], DailyTriflesAssets.O_INCOME_AP.roi[0])


class ServerWiringTests(unittest.TestCase):
    def test_income_router_paths_registered(self):
        from module.server import income_router

        paths = {route.path for route in income_router.income_app.routes}
        self.assertIn('/income/{script_name}', paths)
        self.assertIn('/income/{script_name}/history', paths)
        self.assertIn('/income/{script_name}/dates', paths)

    def test_app_still_registers_income_and_existing_routers(self):
        source = Path('module/server/app.py').read_text(encoding='utf-8')
        for line in ('include_router(home_app)', 'include_router(script_app)',
                     'include_router(stats_app)', 'include_router(income_app)',
                     'include_router(log_app)', 'include_router(tool_app)'):
            self.assertIn(line, source, msg=line)


if __name__ == '__main__':
    unittest.main()
