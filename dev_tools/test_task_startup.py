"""Check the task import path without connecting to or operating a device."""
import importlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class TaskStartupTest(unittest.TestCase):
    def test_six_realms_modes_share_device_and_assets_exist(self):
        import ast
        from module.config.config import Config
        from tasks.SixRealms.config import SixRealmsType
        from tasks.SixRealms.script_task import ScriptTask
        from tasks.GameUi.page import page_six_gates, page_six_gates_jue
        from tasks.SixRealms.moon_sea.moon_sea import MoonSea
        from tasks.SixRealms_jue.moon_sea.moon_sea import MoonSea as JueMoonSea

        config = Config('template')
        device = SimpleNamespace()
        for mode, implementation, page in (
                (SixRealmsType.JIAOTU, MoonSea, page_six_gates),
                (SixRealmsType.JUE, JueMoonSea, page_six_gates_jue)):
            with self.subTest(mode=mode):
                config.six_realms.six_realms_gate.six_realms_type = mode
                task = ScriptTask(config, device)
                self.assertIsInstance(task._moon_sea, implementation)
                self.assertIs(task._moon_sea.device, device)
                self.assertIs(task.moon_sea_page, page)

        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / 'tasks/SixRealms_jue/assets.py').read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                values = {kw.arg: kw.value.value for kw in node.keywords if isinstance(kw.value, ast.Constant)}
                if 'file' in values:
                    asset = root / values.get('path', '') / values['file']
                    self.assertTrue(asset.is_file(), str(asset))

    def test_idle_main_page_uses_shared_navigation(self):
        from module.config.config import Config
        from script import Script
        from tasks.GameUi.game_ui import GameUi
        from tasks.GameUi.page import page_main

        runner = Script.__new__(Script)
        runner.__dict__['config'] = Config('template')
        runner.__dict__['device'] = SimpleNamespace(screenshot=Mock(), stuck_record_clear=Mock())
        with patch.object(GameUi, 'ui_goto_page', return_value=True) as navigate, \
                patch('script.load_module') as load:
            self.assertTrue(runner.prepare_main_page())
        navigate.assert_called_once_with(page_main)
        runner.device.screenshot.assert_called_once_with()
        runner.device.stuck_record_clear.assert_called_once_with()
        load.assert_not_called()

    def test_jue_round_dispatches_boss_and_resets_skill_counts(self):
        from tasks.SixRealms.common import MoonSeaType
        from tasks.SixRealms_jue.moon_sea.moon_sea import MoonSea

        task = MoonSea.__new__(MoonSea)
        task.cnt_skill101 = task.cnt_skillpower = task.cnt_zhanfang = 9
        with patch.object(task, '_start', return_value=True), \
                patch.object(task, 'screenshot'), \
                patch.object(task, 'select_skill', return_value=False), \
                patch.object(task, 'enter_island', return_value=False), \
                patch.object(task, 'island_name', return_value=MoonSeaType.island106), \
                patch.object(task, 'boss_team_lock') as lock, \
                patch.object(task, 'boss_battle', return_value=True) as battle:
            self.assertTrue(task.one())
        self.assertEqual((task.cnt_skill101, task.cnt_skillpower, task.cnt_zhanfang), (0, 0, 0))
        lock.assert_called_once_with()
        battle.assert_called_once_with()

    def test_idle_main_page_maintenance_delays_and_other_errors_use_handler(self):
        from module.config.config import Config
        from module.exception import GamePageUnknownError
        from script import Script
        from tasks.GameUi.game_ui import GameUi

        for maintenance in (True, False):
            with self.subTest(maintenance=maintenance):
                runner = Script.__new__(Script)
                runner.__dict__['config'] = Config('template')
                runner.__dict__['device'] = SimpleNamespace(screenshot=Mock(), stuck_record_clear=Mock())
                error = GamePageUnknownError('test navigation boundary')
                with patch.object(GameUi, 'ui_goto_page', side_effect=error), \
                        patch.object(runner, '_delay_tasks_for_server_update', return_value=maintenance), \
                        patch.object(runner, '_capture_task_runtime_outcome') as capture, \
                        patch.object(runner, '_handle_task_exception', return_value=True) as handler:
                    self.assertFalse(runner.prepare_main_page())
                if maintenance:
                    capture.assert_called_once_with('IdleMainPage')
                    handler.assert_not_called()
                else:
                    handler.assert_called_once_with(error, 'IdleMainPage')
                    capture.assert_not_called()

    def test_click_history_is_shared_and_cleared_between_tasks(self):
        from module.atom.click import RuleClick
        from module.atom.long_click import RuleLongClick
        from module.atom.scatter import RuleScatter

        RuleClick.reset_task_points()
        click = RuleClick((10, 20, 30, 40), (50, 60, 20, 30), profile='High')
        for _ in range(20):
            x, y = click.coord()
            self.assertTrue(10 <= x < 40 and 20 <= y < 60)
        long_click = RuleLongClick((10, 20, 30, 40), (10, 20, 30, 40))
        long_click.coord()
        self.assertEqual(len(RuleClick.task_click_history()), 21)
        self.assertEqual(RuleScatter.task_click_history(), RuleClick.task_click_history())
        scatter = RuleScatter(
            (0, 0, 100, 100), (0, 0, 100, 100),
            polygon=[(0, 0), (99, 0), (99, 99), (0, 99)], focus_count=2,
        )
        scatter.coord()
        self.assertEqual(len(RuleClick.task_click_history()), 22)
        RuleClick.reset_task_points()
        self.assertEqual(RuleClick.task_click_history(), ())
        self.assertEqual(RuleScatter.task_click_history(), ())

    def test_scheduler_enters_ryou_toppa_without_device_actions(self):
        from module.atom.click import RuleClick
        from module.config.config import Config
        from module.exception import TaskEnd
        from script import Script
        from tasks.RyouToppa import script_task as task_module
        from tasks.GameUi.page import page_kekkai_toppa

        runner = Script.__new__(Script)
        runner.config_name = 'template'
        runner.__dict__['config'] = Config('template')
        runner.__dict__['device'] = SimpleNamespace(screenshot=Mock())
        marker = TaskEnd('test boundary')
        with patch('script.load_module', return_value=task_module) as load, \
                patch.object(task_module.ScriptTask, 'ui_goto_page', side_effect=marker) as navigate, \
                patch.object(runner, '_handle_task_exception', return_value=True) as handle:
            self.assertTrue(runner.run('RyouToppa'))
        runner.device.screenshot.assert_called_once_with()
        load.assert_called_once()
        navigate.assert_called_once_with(page_kekkai_toppa)
        handle.assert_called_once_with(marker, 'RyouToppa')
        self.assertEqual(RuleClick.task_click_history(), ())

    def test_adb_fallback_outside_virtual_environment(self):
        from module.device.connection_attr import ConnectionAttr

        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'adb.exe'
            binary.touch()
            instance = ConnectionAttr.__new__(ConnectionAttr)
            with patch.object(ConnectionAttr, 'adb_binary_list', [str(binary)]), \
                    patch('module.device.connection_attr.os.path.exists', return_value=False):
                self.assertEqual(Path(instance.adb_binary), binary)

    def test_menu_tasks_reuse_scheduler_device(self):
        from module.config.config import Config
        from module.config.config_menu import ConfigMenu

        config = Config('template')
        device = SimpleNamespace()
        for tasks in ConfigMenu().gui_menu_list.values():
            for task in tasks:
                if task in {'Script', 'GlobalGame'}:
                    continue
                with self.subTest(task=task):
                    module = importlib.import_module(f'tasks.{task}.script_task')
                    instance = module.ScriptTask(config=config, device=device)
                    self.assertIs(instance.device, device)

    def test_automatic_screenshot_benchmark_imports(self):
        module = importlib.import_module('module.daemon.benchmark')
        self.assertTrue(callable(module.Benchmark.run_simple_screenshot_benchmark))

    def test_screenshot_benchmark_reuses_device(self):
        from module.config.config import Config
        from module.daemon.benchmark import Benchmark

        device = SimpleNamespace(
            sdk_ver=32, is_chinac_phone_cloud=False, disable_stuck_detection=Mock(),
        )
        benchmark = Benchmark(config=Config('template'), device=device)
        with patch.object(benchmark, 'benchmark', return_value=('ADB', None)) as run:
            self.assertEqual(benchmark.run_simple_screenshot_benchmark(), 'ADB')
        self.assertIs(benchmark.device, device)
        self.assertEqual(run.call_args.args[1], ())

    def test_screenshot_paths_and_filename_preserve_task_contract(self):
        module = importlib.import_module('module.logger')
        self.assertEqual(Path(module.log_path), Path('log'))
        self.assertEqual(Path(module.week_path), Path('log') / '每周任务')
        with patch.object(module, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 16, 20, 3, 4)
            filename = module.get_filename('OAS_TEST')
        self.assertEqual(filename, 'OAS_TEST 20点03分04秒 2026-10-16')
        self.assertEqual(Path(filename).name, filename)
