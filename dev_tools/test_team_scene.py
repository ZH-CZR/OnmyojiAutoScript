"""Offline checks for team scene selection and task-local templates."""

import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from tasks.Component.Costume.config import CostumeConfig, TeamType
from tasks.Component.Costume.costume_base import CostumeBase, team_model
from tasks.Component.CostumeTeam.assets import CostumeTeamAssets
from tasks.Component.GeneralInvite.assets import GeneralInviteAssets
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.RealmRaid.assets import RealmRaidAssets
from module.config.config_model import ConfigModel
from module.server.i18n import I18n


class TeamSceneTests(unittest.TestCase):
    def test_oasx_dropdown_has_both_options_and_chinese_labels(self):
        model = ConfigModel()
        fields = model.script_task('GlobalGame')['costume_config']
        field = next(item for item in fields if item['name'] == 'costume_team_type')
        translations = I18n.load_additions()['zh-CN']
        self.assertEqual(field['title'], '组队场景')
        self.assertEqual(field['type'], 'enum')
        self.assertEqual(field['default'], 'costume_team_1')
        self.assertEqual(field['value'], 'costume_team_1')
        self.assertEqual(field['enumEnum'], ['costume_team_1', 'costume_team_2'])
        self.assertEqual([translations[value] for value in field['enumEnum']], ['默认', '宛然春意'])
        self.assertTrue(translations[field['description']])

    def test_oasx_selection_is_saved_and_returned_to_frontend(self):
        model = ConfigModel()
        with patch.object(ConfigModel, 'save') as save:
            self.assertTrue(model.script_set_arg('GlobalGame', 'costume_config',
                                                  'costume_team_type', 'costume_team_2'))
            save.assert_called_once()
        fields = model.script_task('GlobalGame')['costume_config']
        field = next(item for item in fields if item['name'] == 'costume_team_type')
        self.assertEqual(field['value'], 'costume_team_2')

    def test_old_and_missing_config_use_default(self):
        self.assertEqual(CostumeConfig().costume_team_type, TeamType.COSTUME_TEAM_1)
        self.assertEqual(CostumeConfig(costume_team_type='costume_team_default').costume_team_type,
                         TeamType.COSTUME_TEAM_1)

    def test_orochi_constructs_selected_scene_with_shared_device(self):
        from types import SimpleNamespace
        from module.config.config import Config
        from tasks.Orochi.script_task import ScriptTask

        config = Config('template')
        device = SimpleNamespace()
        for scene in TeamType:
            with self.subTest(scene=scene):
                config.global_game.costume_config.costume_team_type = scene
                task = ScriptTask(config, device)
                self.assertIs(task.device, device)
                for name, source_name in team_model[scene].items():
                    self.assertEqual(getattr(task, name).file,
                                     getattr(CostumeTeamAssets, source_name).file)

    def test_templates_load_and_match_manifest(self):
        for path in Path('tasks/Component/CostumeTeam').glob('*/image.json'):
            for item in json.loads(path.read_text(encoding='utf-8')):
                with self.subTest(scene=path.parent.name, image=item['imageName']):
                    asset = getattr(CostumeTeamAssets, 'I_' + item['itemName'].upper())
                    self.assertEqual(Path(asset.file), path.parent / item['imageName'])
                    self.assertEqual(asset.threshold, item['threshold'])
                    self.assertGreater(asset.image.size, 0)

    def test_switching_scenes_keeps_other_tasks_and_templates_unchanged(self):
        first = GeneralInvite.__new__(GeneralInvite)
        second = GeneralInvite.__new__(GeneralInvite)
        original_fire = GeneralInviteAssets.I_FIRE.file
        raid_fire = RealmRaidAssets.I_FIRE.file
        first.check_costume(CostumeConfig(costume_team_type='costume_team_2'))
        second.check_costume(CostumeConfig())
        for name, source_name in team_model[TeamType.COSTUME_TEAM_2].items():
            with self.subTest(asset=name):
                selected = getattr(first, name)
                source = getattr(CostumeTeamAssets, source_name)
                self.assertEqual(selected.file, source.file)
                self.assertEqual(selected.name, name)
                self.assertIsNot(selected, source)
                self.assertIsNot(selected, getattr(second, name))
                self.assertIn('/team1/', getattr(second, name).file)
        first.check_costume(CostumeConfig())
        self.assertIn('/team1/', first.I_FIRE.file)
        self.assertIsNone(first.I_FIRE._image)
        self.assertEqual(GeneralInviteAssets.I_FIRE.file, original_fire)
        self.assertEqual(RealmRaidAssets.I_FIRE.file, raid_fire)

    def test_non_team_task_keeps_its_fire_asset(self):
        class OtherTask(CostumeBase, RealmRaidAssets):
            pass
        task = OtherTask()
        task.check_costume(CostumeConfig(costume_team_type='costume_team_2'))
        self.assertIs(task.I_FIRE, RealmRaidAssets.I_FIRE)
        self.assertNotIn('I_FIRE', task.__dict__)

    def test_room_animation_timer_starts_once_and_resets_after_leaving(self):
        task = GeneralInvite.__new__(GeneralInvite)
        task.appear = Mock(return_value=True)
        timer = Mock()
        timer.start.return_value = timer
        with patch('tasks.Component.GeneralInvite.general_invite.Timer', return_value=timer) as factory:
            self.assertTrue(task.is_in_room(False))
            self.assertTrue(task.is_in_room(False))
            factory.assert_called_once()
            self.assertTrue(3 <= factory.call_args.args[0] <= 5)
            task.appear.return_value = False
            self.assertFalse(task.is_in_room(False))
            self.assertIsNone(task._room_animation_timer)

    def test_challenge_waits_for_animation(self):
        task = GeneralInvite.__new__(GeneralInvite)
        task.screenshot = Mock()
        task.is_in_room = Mock(side_effect=[True, True, False])
        task._room_animation_timer = Mock()
        task._room_animation_timer.reached.side_effect = [False, True]
        task.appear_then_click = Mock(return_value=True)
        task.click_fire()
        task.appear_then_click.assert_called_once_with(task.I_FIRE, interval=1, threshold=0.7)


if __name__ == '__main__':
    unittest.main()
