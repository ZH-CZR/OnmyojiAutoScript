"""Ally marking configuration, attack isolation and bounded battle entry."""
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from dev_tools import test_meta_demon_lineups as lineups
from dev_tools import test_meta_demon_main_mark as main_mark
from module.config.config_model import ConfigModel
from module.exception import GameStuckError
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType
from tasks.MetaDemon.config import BossType
from tasks.MetaDemon.lineups import AllyGreenMark, BossAttack


class AllyMarkTest(unittest.TestCase):
    def test_all_stars_share_settings_without_soul_switch(self):
        task = lineups.MetaDemonLineupTest().task()
        task.conf.lineup_config.enable = False
        task.conf.lineup_config.green_enable = True
        task.conf.lineup_config.green_mark = AllyGreenMark.GREEN_LEFT4
        task.cur_boss_name = '普通鬼王'
        for star in range(1, 7):
            task.cur_boss_type = BossType(star)
            self.assertTrue(task._select_attack())
            self.assertTrue(task._prepare_lineup())
            battle = task._attack_battle_config()
            self.assertTrue(battle.green_enable)
            self.assertEqual(battle.green_mark, GreenMarkType.GREEN_LEFT4)
        task._switch_lineup_souls.assert_not_called()

    def test_special_attacks_override_common_even_with_blank_lineups(self):
        task = lineups.MetaDemonLineupTest().task()
        cfg = task.conf.lineup_config
        cfg.green_enable = True
        cfg.green_mark = AllyGreenMark.GREEN_LEFT5
        boss = cfg.specific_bosses[0]
        boss.first_attack.mark_main = False
        boss.first_attack.lineup = ''
        boss.second_attack.green_enable = True
        boss.second_attack.green_mark = AllyGreenMark.GREEN_LEFT2
        for attempt in range(3):
            task._encounter_attempts = attempt
            task._select_attack()
            battle = task._attack_battle_config()
            self.assertEqual(battle.green_enable, attempt > 0)
            if attempt:
                self.assertEqual(battle.green_mark, GreenMarkType.GREEN_LEFT2)
        self.assertEqual(cfg.green_mark, AllyGreenMark.GREEN_LEFT5)
        self.assertEqual(boss.first_attack.lineup, '')

    def test_schema_api_roundtrip_and_invalid_target_rejected(self):
        model = ConfigModel()
        fields = {f['name']: f for f in model.script_task('MetaDemon')['lineup_config']}
        self.assertFalse(fields['green_enable']['value'])
        self.assertEqual(fields['green_mark']['type'], 'enum')
        attack = BossAttack(green_enable=True, green_mark='green_left3', mark_main=True)
        self.assertEqual(BossAttack.model_validate_json(attack.model_dump_json()), attack)
        self.assertFalse(BossAttack().green_enable)
        for bad in ('green_main', 'invalid', ''):
            with self.assertRaises(ValidationError):
                BossAttack(green_mark=bad)

    def test_settings_save_through_existing_api_and_bad_target_preserves_value(self):
        model = ConfigModel()
        with patch.object(ConfigModel, 'save') as save:
            self.assertTrue(model.script_set_arg('MetaDemon', 'lineup_config', 'green_enable', True))
            self.assertTrue(model.script_set_arg('MetaDemon', 'lineup_config', 'green_mark', 'green_left5'))
            bosses = [{'boss_name': '白藏主', 'attack_count': 2,
                       'first_attack': {'green_enable': True, 'green_mark': 'green_left2'},
                       'second_attack': {'green_enable': False, 'green_mark': 'green_left4'}}]
            self.assertTrue(model.script_set_arg('MetaDemon', 'lineup_config', 'specific_bosses', bosses))
            self.assertFalse(model.script_set_arg('MetaDemon', 'lineup_config', 'green_mark', 'green_main'))
            self.assertEqual(save.call_count, 3)
        cfg = model.meta_demon.lineup_config
        self.assertEqual(cfg.green_mark, AllyGreenMark.GREEN_LEFT5)
        self.assertTrue(cfg.specific_bosses[0].first_attack.green_enable)
        self.assertFalse(cfg.specific_bosses[0].second_attack.green_enable)
        self.assertEqual(cfg.specific_bosses[0].second_attack.green_mark, AllyGreenMark.GREEN_LEFT4)

    def test_all_five_positions_click_once_after_prepare(self):
        for index, mark in enumerate(AllyGreenMark, 1):
            task, _, clock = main_mark.MainMarkTest().task([
                (1001, {'PREPARE', 'BATTLE'}), (1002, set()), (1003, {'BATTLE'})])
            with clock:
                self.assertTrue(task.green_mark(True, mark))
            task.click.assert_called_once_with(getattr(task, f'C_GREEN_LEFT_{index}'))

    def test_main_and_ally_mark_both_run_without_shared_toggle(self):
        task, _, clock = main_mark.MainMarkTest().task([
            (1001, {'BATTLE'}), (1002, {'BATTLE', 'I_MD_MAIN_MARKED'}),
            (1003, {'BATTLE', 'I_MD_MAIN_MARKED'})])
        task._active_attack = BossAttack(mark_main=True, green_enable=True, green_mark='green_left3')
        cfg = task._attack_battle_config()
        with clock:
            self.assertTrue(task.green_mark(cfg.green_enable, cfg.green_mark))
        self.assertEqual(task.click.call_args_list[0].args, (task.C_MD_MARK_MAIN,))
        self.assertEqual(task.click.call_args_list[1].args, (task.C_GREEN_LEFT_3,))
        self.assertEqual(task.click.call_count, 2)

    def test_ending_and_unconfirmed_battle_never_click(self):
        for ending in ('I_WIN', 'I_FALSE', 'I_MD_CURRENT_SUMMON'):
            task, _, clock = main_mark.MainMarkTest().task([(1001, {ending, 'BATTLE'})])
            with clock:
                self.assertFalse(task.green_mark(True, AllyGreenMark.GREEN_LEFT1))
            task.click.assert_not_called()
        task, _, clock = main_mark.MainMarkTest().task([(1001, {'PREPARE'}), (1016, {'PREPARE'})])
        with clock, self.assertRaises(GameStuckError):
            task.green_mark(True, AllyGreenMark.GREEN_LEFT1)
        task.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
