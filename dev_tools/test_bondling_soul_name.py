"""契灵抓捕 OCR 队伍名配置及任务入口回归，不连接设备。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from module.config.config_model import ConfigModel
from tasks.BondlingFairyland.config import BondlingClass, BondlingFairyland, BondlingMode
from tasks.BondlingFairyland.script_task import ScriptTask


class BondlingSoulNameTests(unittest.TestCase):
    def test_default_and_api_scope(self):
        config = BondlingFairyland(switch_soul_config={'team_name': '原队伍'})
        self.assertFalse(config.switch_soul_config.team_name_same_as_bondling)
        self.assertEqual(config.switch_soul_config.resolve_team_name(BondlingClass.BONDLING_2_3), '原队伍')
        groups = ConfigModel().script_task('BondlingFairyland')
        names = [field['name'] for field in groups['switch_soul_config']]
        self.assertEqual(names[names.index('team_name') + 1], 'team_name_same_as_bondling')
        self.assertNotIn('team_name_same_as_bondling', config.bondling_find_switch.model_dump())

    def test_runtime_uses_selected_name_and_keeps_exploration_team(self):
        class NavigationReached(Exception):
            pass

        for enabled in (False, True):
            for species in BondlingClass:
                with self.subTest(enabled=enabled, species=species):
                    config = BondlingFairyland()
                    config.bondling_check.check_enable = False
                    config.bondling_config.bondling_mode = BondlingMode.MODE1
                    config.bondling_config.bondling_stone_class = species
                    capture = config.switch_soul_config
                    capture.enable_switch_by_name = True
                    capture.group_name = '抓捕组'
                    capture.team_name = '手填队伍'
                    capture.team_name_same_as_bondling = enabled
                    explore = config.bondling_find_switch
                    explore.enable_switch_by_name = True
                    explore.group_name = '探查组'
                    explore.team_name = '探查队伍'
                    task = ScriptTask.__new__(ScriptTask)
                    task.config = SimpleNamespace(bondling_fairyland=config)
                    task.run_switch_soul_by_name = Mock()
                    task.ui_goto_page = Mock(side_effect=NavigationReached)
                    with self.assertRaises(NavigationReached):
                        task.run()
                    self.assertEqual(task.run_switch_soul_by_name.call_args_list[0].args,
                                     ('抓捕组', species.value if enabled else '手填队伍'))
                    self.assertEqual(task.run_switch_soul_by_name.call_args_list[1].args,
                                     ('探查组', '探查队伍'))
                    self.assertEqual(capture.team_name, '手填队伍')


if __name__ == '__main__':
    unittest.main()
