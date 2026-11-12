"""Offline activity limits, persistence, rest boundaries and task integration."""
from datetime import datetime, timedelta, time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from module.script.activity_guard import ActivityGuard
from tasks.Script.config import Script as ScriptConfig


class Clock:
    def __init__(self, now=datetime(2026, 10, 17, 12)):
        self.wall, self.mono = now, 0

    def advance(self, seconds):
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


class ActivityGuardTest(unittest.TestCase):
    def test_settlement_detection_uses_the_actual_global_reward_asset(self):
        from tasks.base_task_parent import BaseTaskParent
        from tasks.GlobalGame.assets import GlobalGameAssets
        task = BaseTaskParent.__new__(BaseTaskParent)
        task.appear = Mock(side_effect=lambda marker: marker is GlobalGameAssets.I_REWARD)
        markers = task._settlement_markers()
        self.assertTrue(markers)
        self.assertTrue(all(marker is GlobalGameAssets.I_REWARD for marker in markers))

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'activity.sqlite3'
        self.clock = Clock()
        self.config = SimpleNamespace(script=ScriptConfig())
        self.config.script.anti_ban.enable = True
        self.guard = self.new_guard()

    def new_guard(self, name='one'):
        return ActivityGuard(lambda: self.config, name, path=self.path,
                             now=lambda: self.clock.wall, monotonic=lambda: self.clock.mono,
                             sleep=self.clock.advance)

    def test_daily_limit_persists_and_legacy_rest_does_not_reset_it(self):
        ab = self.config.script.anti_ban
        ab.daily_runtime_limit = timedelta(seconds=10)
        ab.daily_active_limit = timedelta(seconds=5)
        ab.long_rest_duration = timedelta(seconds=3)
        self.guard.start()
        self.clock.advance(12)
        self.guard.finish()
        restored = self.new_guard()
        self.assertEqual(restored.store.read(self.clock.wall)[:2], (12, 12))
        self.assertEqual(restored.deadline(self.clock.wall), datetime(2026, 10, 18))
        self.assertEqual(restored.store.read(self.clock.wall)[:2], (12, 0))
        self.assertEqual(restored.deadline(self.clock.wall + timedelta(seconds=5)), datetime(2026, 10, 18))

    def test_cross_midnight_splits_daily_accounting(self):
        self.clock.wall = datetime(2026, 10, 17, 23, 59, 58)
        self.guard.start()
        self.clock.advance(7)
        self.guard.finish()
        self.assertEqual(self.guard.store.read(datetime(2026, 10, 17))[0], 2)
        self.assertEqual(self.guard.store.read(datetime(2026, 10, 18))[0], 5)

    def test_daily_limit_waits_for_next_date_then_sleep_end(self):
        self.clock.wall = datetime(2026, 10, 17, 23, 59, 58)
        ab = self.config.script.anti_ban
        ab.daily_runtime_limit = timedelta(seconds=5)
        ab.sleep_start, ab.sleep_end = time(0), time(0, 0, 3)
        self.guard.store.add(self.clock.wall, self.clock.wall, 6)
        self.assertTrue(self.guard.checkpoint())
        self.assertEqual(self.clock.wall, datetime(2026, 10, 18, 0, 0, 3))
        self.assertEqual(self.guard.store.read(self.clock.wall)[0], 0)
        self.assertEqual(self.guard.store.read(datetime(2026, 10, 17))[0], 6)

    def test_file_reload_during_rest_without_shared_event(self):
        from script import Script
        import os
        runner = Script.__new__(Script)
        runner.config_name = 'one'
        cfg = SimpleNamespace(config_reload_event=None, reload=Mock(), scheduler_update_dt='old')
        runner.__dict__['config'] = cfg
        path = Path(self.folder.name) / 'one.json'
        path.write_text('{}', encoding='utf-8')
        with patch('script.filepath_config', return_value=str(path)):
            runner._refresh_activity_config()
            cfg.reload.assert_not_called()
            stamp = path.stat().st_mtime_ns + 1000000000
            os.utime(path, ns=(stamp, stamp))
            runner._refresh_activity_config()
            cfg.reload.assert_called_once()
            self.assertIsNone(cfg.scheduler_update_dt)
            runner._refresh_activity_config()
            cfg.reload.assert_called_once()

    def test_sleep_pause_excludes_rest_and_rechecks_next_day_sleep_window(self):
        self.clock.wall = datetime(2026, 10, 17, 23, 59, 58)
        ab = self.config.script.anti_ban
        ab.sleep_start, ab.sleep_end = time(23), time(0, 0, 3)
        self.guard.start()
        self.assertTrue(self.guard.checkpoint())
        self.assertEqual(self.clock.wall, datetime(2026, 10, 18, 0, 0, 3))
        self.clock.advance(2)
        self.guard.finish()
        self.assertEqual(self.guard.store.read(self.clock.wall)[0], 2)

    def test_pending_rest_only_starts_at_checkpoint_not_during_battle(self):
        ab = self.config.script.anti_ban
        ab.daily_active_limit = timedelta(seconds=5)
        ab.long_rest_duration = timedelta(seconds=3)
        self.guard.start()
        self.clock.advance(6)
        self.guard.tick()
        self.assertTrue(self.guard.pending)
        self.assertIsNone(self.guard.store.read(self.clock.wall)[2])
        self.clock.advance(20)  # battle continues beyond requested rest length
        self.assertTrue(self.guard.checkpoint())
        self.assertEqual(self.clock.mono, 29)
        self.assertEqual(self.guard.store.read(self.clock.wall)[0], 26)

    def test_legacy_rest_deadline_survives_restart(self):
        ab = self.config.script.anti_ban
        ab.daily_active_limit = timedelta(seconds=5)
        ab.long_rest_duration = timedelta(seconds=3)
        self.guard.store.add(self.clock.wall, self.clock.wall, 8)
        until = self.guard.deadline(self.clock.wall)
        restored = self.new_guard()
        self.assertEqual(restored.deadline(self.clock.wall), until)
        self.assertTrue(restored.checkpoint())
        self.assertEqual(self.clock.mono, 3)

    def test_continuous_rest_inside_single_task(self):
        cfg = self.config.script.device
        cfg.continuous_task_rest_enable = True
        cfg.continuous_task_rest_interval = '1,1'
        self.guard.start()
        self.clock.advance(61)
        with patch.object(self.guard, 'sample_rest', return_value=120):
            self.assertTrue(self.guard.checkpoint())
        self.assertEqual(self.clock.mono, 181)
        self.clock.advance(2)
        self.guard.finish()
        self.assertEqual(self.guard.store.read(self.clock.wall)[0], 63)

    def test_config_change_interrupts_wait_without_counting_rest(self):
        self.config.script.anti_ban.sleep_start = time(10)
        self.config.script.anti_ban.sleep_end = time(14)
        self.guard.start()
        def refresh():
            if self.clock.mono >= 1:
                self.config.script.anti_ban.enable = False
        self.guard.refresh = refresh
        self.assertTrue(self.guard.checkpoint())
        self.assertEqual(self.clock.mono, 1)
        self.assertFalse(self.guard.pending)

    def test_pending_manual_request_does_not_bypass_in_task_rest(self):
        from tasks.base_task_parent import BaseTaskParent
        for reason in ('daily', 'sleep', 'long_rest'):
            with self.subTest(reason=reason):
                self.config.script = ScriptConfig()
                ab = self.config.script.anti_ban
                ab.enable = True
                ab.sleep_start = ab.sleep_end = time(0)
                self.clock.wall, self.clock.mono = datetime(2026, 10, 17, 12), 0
                guard = self.new_guard(name=reason)
                if reason == 'daily':
                    self.clock.wall = datetime(2026, 10, 17, 23, 59, 58)
                    ab.daily_runtime_limit = timedelta(seconds=5)
                    guard.store.add(self.clock.wall, self.clock.wall, 6)
                    expected = 2
                elif reason == 'sleep':
                    ab.sleep_start, ab.sleep_end = time(11), time(12, 0, 3)
                    expected = 3
                else:
                    ab.daily_active_limit = timedelta(seconds=5)
                    ab.long_rest_duration = timedelta(seconds=3)
                    guard.store.add(self.clock.wall, self.clock.wall, 6)
                    expected = 3
                guard.start()
                guard.tick(force=True)
                task = SimpleNamespace(config=self.config, device=SimpleNamespace(
                    activity_guard=guard, stuck_record_clear=Mock(),
                    click_record_clear=Mock(), invalidate_image_batch_cache=Mock()))
                with patch('module.config.manual.ManualStore') as store:
                    store.return_value.pending.return_value = {'pets': 'waiting'}
                    self.assertTrue(BaseTaskParent.runtime_checkpoint(task))
                    store.assert_not_called()
                self.assertEqual(self.clock.mono, expected)
                self.assertTrue(guard.active)
                self.assertIsNone(guard.deadline(self.clock.wall))
                task.device.stuck_record_clear.assert_called_once()

    def test_scheduler_rest_can_return_to_selection_for_manual_request(self):
        self.config.script.anti_ban.sleep_start = time(11)
        self.config.script.anti_ban.sleep_end = time(14)
        self.guard.start()
        with patch('module.config.manual.ManualStore') as store:
            store.return_value.pending.return_value = {'pets': 'waiting'}
            self.assertTrue(self.guard.checkpoint(allow_manual_interrupt=True))
            store.return_value.pending.assert_called_once()
        self.assertEqual(self.clock.mono, 0)
        self.assertIsNotNone(self.guard.deadline(self.clock.wall))

    def test_configs_are_isolated_and_backward_clock_still_counts(self):
        self.guard.start()
        self.clock.mono += 9
        self.clock.wall -= timedelta(seconds=20)
        self.guard.finish()
        self.assertEqual(self.guard.store.read(self.clock.wall)[0], 9)
        self.assertEqual(self.new_guard('two').store.read(self.clock.wall)[0], 0)

    def test_disabled_guard_does_not_create_runtime_data(self):
        self.config.script.anti_ban.enable = False
        self.guard.start()
        self.clock.advance(8)
        self.guard.finish()
        self.assertFalse(self.path.exists())

    def test_accounting_is_flushed_at_screenshot_tick(self):
        self.guard.start()
        self.clock.advance(6)
        self.guard.tick()
        restored = self.new_guard()
        self.assertEqual(restored.store.read(self.clock.wall)[0], 6)
        self.clock.advance(1)
        self.guard.finish()
        self.assertEqual(restored.store.read(self.clock.wall)[0], 7)

    def test_interval_validation(self):
        self.assertEqual(ActivityGuard.parse_interval('60，120'), (60, 120))
        for bad in ('0,1', '2,1', '-1,2', '60', 'nan,inf'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ActivityGuard.parse_interval(bad)

    def test_failed_script_flushes_before_recovery(self):
        from script import Script
        runner = Script.__new__(Script)
        runner.config_name = 'one'
        runner.__dict__['config'] = self.config
        runner.__dict__['activity_guard'] = self.guard
        runner.__dict__['device'] = SimpleNamespace(screenshot=Mock())
        self.config.global_game = SimpleNamespace(ocr=SimpleNamespace(save_ocr_log=False))
        def fail():
            self.clock.advance(11)
            raise RuntimeError('simulated failure')
        task = SimpleNamespace(ScriptTask=lambda **kw: SimpleNamespace(run=fail))
        with patch('script.load_module', return_value=task), \
                patch('script.set_ocr_logging_enabled'), \
                patch.object(runner, '_handle_task_exception', return_value=False) as recover:
            self.assertFalse(runner.run('Orochi'))
        recover.assert_called_once()
        self.assertFalse(self.guard.active)
        self.assertEqual(self.guard.store.read(self.clock.wall)[0], 11)
        self.assertIsNone(runner.device.activity_guard)

    def test_recovery_wait_rearms_stuck_detection_before_first_screenshot(self):
        from script import Script
        from module.exception import TaskEnd
        runner = Script.__new__(Script)
        runner.__dict__['config'] = SimpleNamespace(global_game=SimpleNamespace(ocr=SimpleNamespace(save_ocr_log=False)))
        guard = SimpleNamespace(checkpoint=Mock(return_value=True), start=Mock(), finish=Mock())
        runner.__dict__['activity_guard'] = guard
        calls = []
        runner.__dict__['device'] = SimpleNamespace(
            stuck_record_clear=lambda: calls.append('stuck'),
            click_record_clear=lambda: calls.append('click'),
            invalidate_image_batch_cache=lambda: calls.append('cache'),
            screenshot=lambda: calls.append('shot'),
        )
        task = SimpleNamespace(ScriptTask=lambda **kw: SimpleNamespace(run=Mock(side_effect=TaskEnd)))
        with patch('script.load_module', return_value=task), \
                patch('script.set_ocr_logging_enabled'), \
                patch.object(runner, '_finish_task_page'), \
                patch.object(runner, '_handle_task_exception', return_value=True):
            self.assertTrue(runner.run('Orochi'))
        self.assertEqual(calls, ['stuck', 'click', 'cache', 'shot'])
        guard.finish.assert_called_once()


if __name__ == '__main__':
    unittest.main()
