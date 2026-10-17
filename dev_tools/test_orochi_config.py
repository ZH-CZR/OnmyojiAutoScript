"""御魂快捷配置、旧配置兼容和运行调度的离线验证。"""
import unittest
from datetime import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.config_model import ConfigModel
from module.exception import TaskEnd
from tasks.Orochi.config import Layer, NextDayOrochiConfig, Orochi, Plan, UserStatus
from tasks.Orochi.script_task import ScriptTask


class OrochiConfigTest(unittest.TestCase):
    def test_presets_are_saved_and_manual_changes_clear_selection(self):
        model = ConfigModel()
        settings = model.orochi.next_day_orochi_config
        cases = ((Plan.TEN30, Layer.TEN, 30), (Plan.ELEVEN30, Layer.ELEVEN, 30),
                 (Plan.TWELVE50, Layer.TWELVE, 50), (Plan.TWELVE120, Layer.TWELVE, 120))
        with patch.object(ConfigModel, 'save'):
            for plan, layer, count in cases:
                self.assertTrue(model.script_set_arg('Orochi', 'next_day_orochi_config', 'plan', plan.value))
                self.assertEqual((settings.layer, settings.limit_count), (layer, count))
                restored = ConfigModel.model_validate_json(model.model_dump_json())
                self.assertEqual(restored.orochi.next_day_orochi_config.layer, layer)
                self.assertTrue(model.script_set_arg('Orochi', 'next_day_orochi_config', 'limit_count', 17))
                self.assertEqual((settings.plan, settings.layer, settings.limit_count), (Plan.NONE, layer, 17))
            model.script_set_arg('Orochi', 'next_day_orochi_config', 'plan', Plan.TEN30.value)
            model.script_set_arg('Orochi', 'next_day_orochi_config', 'layer', Layer.THIRTEEN.value)
            self.assertEqual((settings.plan, settings.layer), (Plan.NONE, Layer.THIRTEEN))
            model.script_set_arg('Orochi', 'next_day_orochi_config', 'plan', Plan.NONE.value)
            self.assertEqual((settings.layer, settings.limit_count), (Layer.THIRTEEN, 30))

    def test_legacy_plans_and_time_migration(self):
        for plan in ('无限循环', '只执行一次下面的配置', '本次不执行，设置明天运行(拾层-30)'):
            settings = NextDayOrochiConfig(plan=plan, layer=Layer.THIRTEEN, limit_count=42)
            self.assertEqual((settings.plan, settings.layer, settings.limit_count), (Plan.NONE, Layer.THIRTEEN, 42))
        legacy = {'start_time': '11:23:00'}
        self.assertEqual(Orochi(next_day_orochi_config=legacy).scheduler.server_update, time(11, 23))
        for value in ('09:00:00', '14:15:00'):
            task = Orochi(next_day_orochi_config=legacy, scheduler={'server_update': value})
            self.assertEqual(task.scheduler.server_update, time.fromisoformat(value))
            restored = Orochi.model_validate_json(task.model_dump_json())
            self.assertEqual(restored.scheduler.server_update, time.fromisoformat(value))

    def test_gui_exposes_only_quick_presets_and_one_time_setting(self):
        args = ConfigModel().script_task('Orochi')
        fields = {item['name']: item for item in args['next_day_orochi_config']}
        self.assertNotIn('start_time', fields)
        self.assertEqual(fields['plan']['enumEnum'], [plan.value for plan in Plan])
        self.assertIn('server_update', {item['name'] for item in args['scheduler']})

    def test_plans_do_not_change_scheduling_or_runtime_limits(self):
        for plan in Plan:
            config = Orochi(next_day_orochi_config={'plan': plan, 'limit_count': 7})
            config.orochi_config.user_status = UserStatus.ALONE
            task = object.__new__(ScriptTask)
            task.config = SimpleNamespace(orochi=config, true_orochi=SimpleNamespace(
                true_orochi_config=SimpleNamespace(current_success=0)))
            task.is_in_battle = Mock(return_value=True)
            task.run_alone = Mock()
            task.set_next_run = Mock()
            with self.assertRaises(TaskEnd):
                task.run()
            task.run_alone.assert_called_once_with(config.next_day_orochi_config.layer)
            self.assertEqual(task.limit_count, config.next_day_orochi_config.limit_count)
            task.set_next_run.assert_any_call('Orochi', finish=True, success=True)


if __name__ == '__main__':
    unittest.main()
