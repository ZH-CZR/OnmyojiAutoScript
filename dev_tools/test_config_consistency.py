"""Configuration edits remain isolated across task/frontend writers; no device IO."""
import copy
import json
import multiprocessing
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.config_watcher import ConfigWatcher
from module.config.utils import write_config_changes


def _save_from_process(path, key, ready, start):
    baseline = {'task': {'first': 0, 'second': 0}}
    current = copy.deepcopy(baseline)
    current['task'][key] = 1
    ready.put(key)
    if not start.wait(timeout=10):
        raise RuntimeError('Concurrent save was not released')
    write_config_changes(path, baseline, current)


class ConfigSaveConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'config').mkdir()
        self.cwd_patch = patch('module.config.config_model.Path.cwd', return_value=self.root)
        self.cwd_patch.start()
        self.addCleanup(self.cwd_patch.stop)
        self.path = self.root / 'config' / 'offline.json'
        ConfigModel(config_name='offline').save()

    def saved(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def test_old_task_call_preserves_frontend_settings_and_unknown_fields(self):
        worker = Config('offline')
        frontend = Config('offline')
        self.assertTrue(frontend.model.script_set_arg('Orochi', 'scheduler', 'enable', True))
        data = self.saved()
        data['legacy_public_field'] = {'keep': True}
        self.path.write_text(json.dumps(data), encoding='utf-8')
        self.assertTrue(worker.task_call('SoulsTidy'))
        saved = self.saved()
        self.assertTrue(saved['orochi']['scheduler']['enable'])
        self.assertEqual(saved['legacy_public_field'], {'keep': True})
        self.assertNotIn('running_task', saved)

    def test_two_stale_writers_preserve_different_fields_in_same_group(self):
        first, second = ConfigModel(config_name='offline'), ConfigModel(config_name='offline')
        first.orochi.scheduler.enable = True
        first.save()
        second.orochi.scheduler.priority = 17
        second.save()
        saved = self.saved()['orochi']['scheduler']
        self.assertTrue(saved['enable'])
        self.assertEqual(saved['priority'], 17)
        # A later save from the first stale instance must not revert priority.
        first.orochi.scheduler.enable = False
        first.save()
        self.assertEqual(self.saved()['orochi']['scheduler']['priority'], 17)

    def test_read_merge_write_transaction_serializes_concurrent_writers(self):
        baseline = {'task': {'first': 0, 'second': 0}}
        self.path.write_text(json.dumps(baseline), encoding='utf-8')
        start = threading.Barrier(3)
        errors = []

        def save(key):
            try:
                current = copy.deepcopy(baseline)
                current['task'][key] = 1
                start.wait(timeout=5)
                write_config_changes(self.path, baseline, current)
            except Exception as error:
                errors.append(error)

        workers = [threading.Thread(target=save, args=(key,)) for key in ('first', 'second')]
        for worker in workers:
            worker.start()
        start.wait(timeout=5)
        for worker in workers:
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.saved(), {'task': {'first': 1, 'second': 1}})

    def test_unchanged_save_and_runtime_snapshot_do_not_rewrite_file(self):
        model = ConfigModel(config_name='offline')
        stamp = self.path.stat().st_mtime_ns
        model.running_task = 'Pets'
        model.save()
        self.assertEqual(self.path.stat().st_mtime_ns, stamp)

    def test_independent_spawned_processes_do_not_lose_either_change(self):
        self.path.write_text(json.dumps({'task': {'first': 0, 'second': 0}}), encoding='utf-8')
        context = multiprocessing.get_context('spawn')
        ready, start = context.Queue(), context.Event()
        workers = [context.Process(target=_save_from_process,
                                   args=(str(self.path), key, ready, start))
                   for key in ('first', 'second')]
        try:
            for worker in workers:
                worker.start()
            self.assertEqual({ready.get(timeout=10), ready.get(timeout=10)}, {'first', 'second'})
            start.set()
            for worker in workers:
                worker.join(timeout=10)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(self.saved(), {'task': {'first': 1, 'second': 1}})
        finally:
            start.set()
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                if worker.pid is not None:
                    worker.join(timeout=5)
                    worker.close()
            ready.close()
            ready.join_thread()


class ConfigReloadConsistencyTest(unittest.TestCase):
    def test_same_second_save_and_backwards_stamp_interrupt_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text('{}', encoding='utf-8')
            stamp = 1780000000000000000
            os.utime(path, ns=(stamp, stamp))
            watcher = ConfigWatcher()
            with patch('module.config.config_watcher.filepath_config', return_value=path):
                watcher.start_watching()
                os.utime(path, ns=(stamp + 500000000, stamp + 500000000))
                self.assertTrue(watcher.should_reload())
                watcher.start_watching()
                os.utime(path, ns=(stamp, stamp))
                self.assertTrue(watcher.should_reload())

    def test_save_between_model_load_and_wait_is_not_lost(self):
        watcher = ConfigWatcher()
        watcher._loaded_mtime = (1, 2, 100, 20)
        with patch.object(watcher, 'get_mtime', return_value=(1, 3, 101, 20)):
            watcher.start_watching()
            self.assertTrue(watcher.should_reload())

    def test_new_task_configuration_rebinds_existing_shared_device(self):
        from module.base.protect import click_timing_enabled
        from script import Script

        runner = Script.__new__(Script)
        runner.config_name = 'offline'
        runner.startup_task_order = SimpleNamespace()
        old = ConfigModel()
        old.script.anti_ban.click_timing_enable = True
        device = SimpleNamespace(config=SimpleNamespace(script=old.script))
        runner.__dict__['device'] = device
        new = ConfigModel()
        new.script.anti_ban.click_timing_enable = False
        replacement = SimpleNamespace(script=new.script)
        with patch('module.config.config.Config', return_value=replacement):
            selected = Script.config.__get__(runner, Script)
        self.assertIs(selected, replacement)
        self.assertIs(device.config, replacement)
        self.assertFalse(click_timing_enabled(device.config))


if __name__ == '__main__':
    unittest.main()
