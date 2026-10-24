"""道馆运行时清理回归：使用内存导航图和模拟设备，不启动游戏。"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.exception import GameStuckError, TaskEnd
from tasks.Dokan.config import Dokan
from tasks.Dokan.script_task import DokanScene, ScriptTask


class MemoryPage:
    def __init__(self, links=None):
        self.links = links or {}

    def link(self, button, destination):
        buttons = button if isinstance(button, (list, tuple)) else [button]
        if buttons not in self.links.setdefault(destination, []):
            self.links[destination].append(buttons)


class DokanNavigationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.main, self.records, self.dokan, self.extra = [MemoryPage() for _ in range(4)]
        self.main.links = {self.records: [[object(), object()]], self.extra: [[object()]]}
        self.records.links = {self.main: [[object()]], self.extra: [[object()]]}
        self.dokan.links = {self.records: [[object()]], self.extra: [[object()]]}
        self.original = [(page, {key: list(value) for key, value in page.links.items()})
                         for page in (self.main, self.records, self.dokan)]
        self.pages = SimpleNamespace(page_main=self.main, page_shikigami_records=self.records,
                                     page_dokan=self.dokan)
        self.patch_pages = patch('tasks.Dokan.script_task.ipages', self.pages)
        self.patch_pages.start()
        self.addCleanup(self.patch_pages.stop)
        self.task = object.__new__(ScriptTask)
        self.task.config = SimpleNamespace(dokan=Dokan())
        self.task.check_current_weekday = Mock()
        self.task.ui_goto_page = Mock()
        self.task.run_switch_soul = Mock()
        self.task.run_switch_soul_by_name = Mock()

    def assert_restored(self):
        for page, links in self.original:
            self.assertEqual(page.links, links)
        self.assertNotIn('_dokan_navigation_snapshot', self.task.__dict__)

    def assert_temporary_navigation(self):
        self.assertNotIn(self.records, self.main.links)
        self.assertEqual(set(self.records.links), {self.dokan})
        self.assertIn(self.records, self.dokan.links)

    def test_later_battle_failure_restores_exact_routes_after_repeated_soul_switches(self):
        def flow():
            self.task.dokan_switch_soul()
            self.assert_temporary_navigation()
            self.task.dokan_switch_soul()
            self.assert_temporary_navigation()
            raise GameStuckError('battle failed')
        self.task._run_dokan = flow
        with self.assertRaisesRegex(GameStuckError, 'battle failed'):
            self.task.run()
        self.assert_restored()

    def test_switch_and_return_navigation_failures_restore_routes(self):
        self.task.config.dokan.switch_soul_config.enable = True
        for failing in (self.task.run_switch_soul, self.task.ui_goto_page):
            with self.subTest(failing=failing):
                failing.side_effect = GameStuckError('navigation failed')
                self.task._run_dokan = self.task.dokan_switch_soul
                with self.assertRaisesRegex(GameStuckError, 'navigation failed'):
                    self.task.run()
                self.assert_restored()
                failing.side_effect = None

    def test_normal_return_task_end_and_system_exit_restore_routes(self):
        for ending in (None, TaskEnd, SystemExit):
            with self.subTest(ending=ending):
                def flow():
                    self.task.dokan_switch_soul()
                    self.assert_temporary_navigation()
                    if ending is not None:
                        raise ending
                    return 'completed'
                self.task._run_dokan = flow
                if ending is None:
                    self.assertEqual(self.task.run(), 'completed')
                else:
                    with self.assertRaises(ending):
                        self.task.run()
                self.assert_restored()

    def test_finish_without_switch_does_not_invent_or_delete_navigation(self):
        with self.assertRaises(TaskEnd):
            self.task.finish_task()
        self.assert_restored()

    def test_finish_then_run_finally_is_idempotent(self):
        def flow():
            self.task.dokan_switch_soul()
            self.task.finish_task()
        self.task._run_dokan = flow
        with self.assertRaises(TaskEnd):
            self.task.run()
        self.assert_restored()


class DokanProgressSafetyTests(unittest.TestCase):
    def setUp(self):
        self.task = object.__new__(ScriptTask)
        self.task.config = SimpleNamespace(dokan=Dokan())
        self.task.device = Mock()
        self.task.quit_dokan = Mock()
        self.task.appear_then_click = Mock(return_value=False)
        self.now = 0.

    def tick(self, scene):
        self.now += 10
        return True, scene

    def test_unknown_screen_cannot_refresh_device_watchdog_every_fifty_seconds(self):
        self.task.get_current_scene = Mock(side_effect=lambda: self.tick(
            DokanScene.RYOU_DOKAN_SCENE_UNKNOWN))
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=lambda: self.now):
            with self.assertRaisesRegex(GameStuckError, '60 秒没有进展'):
                self.task.dokan_process(self.task.config.dokan)
        self.assertEqual(self.now, 60)
        self.task.device.stuck_record_clear.assert_not_called()
        self.task.device.stuck_record_add.assert_not_called()

    def test_recognized_wait_allows_long_wait_but_unknown_flicker_is_not_progress(self):
        gathering = DokanScene.RYOU_DOKAN_SCENE_GATHERING
        unknown = DokanScene.RYOU_DOKAN_SCENE_UNKNOWN
        self.task.get_current_scene = Mock(side_effect=lambda: self.tick(
            gathering if self.now % 20 == 0 else unknown))
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=lambda: self.now):
            with self.assertRaisesRegex(GameStuckError, '300 秒没有进展'):
                self.task.dokan_process(self.task.config.dokan)
        self.assertEqual(self.now, 310)
        self.task.device.stuck_record_clear.assert_called_once_with()
        self.task.device.stuck_record_add.assert_called_once_with('BATTLE_STATUS_S')

    def test_actual_stage_change_starts_new_wait_budget(self):
        frames = iter([
            (10, DokanScene.RYOU_DOKAN_SCENE_GATHERING),
            (290, DokanScene.RYOU_DOKAN_SCENE_GATHERING),
            (300, DokanScene.RYOU_DOKAN_SCENE_CD),
            (580, DokanScene.RYOU_DOKAN_SCENE_CD),
        ])
        def scene():
            try:
                self.now, stage = next(frames)
            except StopIteration:
                raise TaskEnd
            return True, stage
        self.task.get_current_scene = scene
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=lambda: self.now):
            with self.assertRaises(TaskEnd):
                self.task.dokan_process(self.task.config.dokan)
        self.assertEqual(self.task.device.stuck_record_clear.call_count, 2)
        self.assertEqual(self.task.device.stuck_record_add.call_count, 2)

    def test_completed_inner_battle_does_not_exhaust_next_prepare_budget(self):
        self.task.get_current_scene = Mock(side_effect=[
            (True, DokanScene.RYOU_DOKAN_SCENE_IN_FIELD),
            (True, DokanScene.RYOU_DOKAN_SCENE_IN_FIELD), TaskEnd])
        def battle(cfg):
            # 正常长战斗/离线等待由内层保护，返回表示实际阶段已推进。
            self.now += 540
        self.task.dokan_battle = Mock(side_effect=battle)
        with patch('tasks.Dokan.script_task.time.monotonic', side_effect=lambda: self.now):
            with self.assertRaises(TaskEnd):
                self.task.dokan_process(self.task.config.dokan)
        self.assertEqual(self.task.dokan_battle.call_count, 2)


if __name__ == '__main__':
    unittest.main()
