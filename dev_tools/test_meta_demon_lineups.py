"""Unified lineup configuration, migration, API and per-boss attack lifecycle."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.config_model import ConfigModel
from module.exception import GameStuckError
from tasks.MetaDemon.config import MetaDemon, BossType
from tasks.MetaDemon.lineups import MetaDemonLineups, SpecificBoss
from tasks.MetaDemon.script_task import ScriptTask


class MetaDemonLineupTest(unittest.TestCase):
    def task(self):
        task = ScriptTask.__new__(ScriptTask)
        task.conf = MetaDemon(lineup_config={'enable': True, 'common_stars': '活动,通用',
            'five_stars': '活动,五星', 'six_stars': '活动,六星',
            'specific_bosses': [{'boss_name': '白藏主', 'attack_count': 2,
                'first_attack': {'lineup': '活动,第一队', 'powerful': True, 'mark_main': True},
                'second_attack': {'lineup': '活动,第二队', 'powerful': False, 'mark_main': False}}]})
        task.State = SimpleNamespace(done=False)
        task.cur_boss_type = BossType.FIVE_STARS
        task.cur_boss_name = '白藏主'
        task._reset_combat_plan()
        task._switch_lineup_souls = Mock()
        task._apply_preset_team = Mock(return_value=True)
        return task

    def test_unified_schema_hides_both_old_groups(self):
        args = ConfigModel().script_task('MetaDemon')
        self.assertNotIn('switch_soul', args)
        self.assertNotIn('preset_switch', args)
        fields = {a['name']: a for a in args['lineup_config']}
        self.assertEqual(fields['specific_bosses']['type'], 'meta_demon_bosses')
        self.assertNotIn('legacy_stars', fields)

    def test_old_preset_and_mapping_migrate_without_overwriting_explicit_new(self):
        old = {'enable': True, 'common_stars': '活动,通用', 'five_stars': '活动,五星',
               'name_map': '白藏主：活动，专用'}
        m = MetaDemon(preset_switch=old)
        self.assertTrue(m.lineup_config.enable)
        self.assertTrue(m.lineup_config.preset_enable)
        self.assertEqual(m.lineup_config.specific('白藏主').first_attack.lineup, '活动,专用')
        m = MetaDemon(preset_switch=old, lineup_config={'enable': False, 'five_stars': '新,阵容'})
        self.assertFalse(m.lineup_config.enable)
        self.assertEqual(m.lineup_config.five_stars, '新,阵容')
        self.assertEqual(m.lineup_config.common_stars, '活动,通用')

    def test_delta_save_partial_group_preserves_old_migrated_fields(self):
        m = MetaDemon(switch_soul={'enable': True, 'five_stars': '1,2'},
                      lineup_config={'specific_bosses': []})
        self.assertTrue(m.lineup_config.enable)
        self.assertEqual(m.lineup_config.five_stars, '1,2')

    def test_distinct_legacy_star_lineups_survive_until_common_field_saved(self):
        m = ConfigModel(meta_demon={'switch_soul': {'enable': True, 'one_star': '1,1', 'two_stars': '2,2'}})
        self.assertEqual(m.meta_demon.lineup_config.common_lineup(1), '1,1')
        self.assertEqual(m.meta_demon.lineup_config.common_lineup(2), '2,2')
        with patch.object(ConfigModel, 'save'):
            self.assertTrue(m.script_set_arg('MetaDemon', 'lineup_config', 'common_stars', '新组,新队'))
        self.assertEqual(m.meta_demon.lineup_config.legacy_stars, {})
        self.assertEqual(m.meta_demon.lineup_config.common_lineup(2), '新组,新队')

    def test_specific_boss_validation_and_non_destructive_failure(self):
        m = ConfigModel()
        with patch.object(ConfigModel, 'save') as save:
            for invalid in ([{'boss_name': ''}], [{'boss_name': '甲', 'attack_count': 3}],
                            [{'boss_name': '甲'}, {'boss_name': '甲'}],
                            [{'boss_name': '甲', 'first_attack': {'lineup': 'bad'}}]):
                self.assertFalse(m.script_set_arg('MetaDemon', 'lineup_config', 'specific_bosses', invalid))
            save.assert_not_called()
            self.assertEqual(m.meta_demon.lineup_config.specific_bosses, [])
            value = [{'boss_name': '甲', 'attack_count': 2, 'first_attack': {'lineup': '组，队'}}]
            self.assertTrue(m.script_set_arg('MetaDemon', 'lineup_config', 'specific_bosses', value))
            save.assert_called_once()
        self.assertEqual(m.meta_demon.lineup_config.specific_bosses[0].first_attack.lineup, '组,队')

    def test_first_second_and_final_retry_reuse_second_settings(self):
        task = self.task()
        for attempt, team, powerful, mark in [(0, '活动,第一队', True, True),
                                             (1, '活动,第二队', False, False),
                                             (2, '活动,第二队', False, False)]:
            task._encounter_attempts = attempt
            self.assertTrue(task._select_attack())
            self.assertEqual(task._active_attack.lineup, team)
            self.assertEqual(task._active_attack.powerful, powerful)
            self.assertEqual(task._attack_battle_config().green_enable, mark)
            self.assertEqual(task._attack_battle_config().green_mark.value, 'green_main')
        task._encounter_attempts = 3
        self.assertFalse(task._select_attack())
        self.assertTrue(task.State.done)

    def test_one_attack_has_no_unrequested_retry(self):
        task = self.task()
        task.conf.lineup_config.specific_bosses[0].attack_count = 1
        task._encounter_attempts = 1
        self.assertFalse(task._select_attack())

    def test_new_summon_skips_unused_second_attack_and_resets_even_same_name(self):
        task = self.task()
        task._encounter_attempts = 1
        task._new_encounter()
        task._select_attack()
        self.assertEqual(task._active_attack.lineup, '活动,第一队')

    def test_unknown_or_partial_name_uses_star_default(self):
        task = self.task()
        task.cur_boss_name = '白藏'
        task._select_attack()
        self.assertEqual(task._active_attack.lineup, '活动,五星')
        task.cur_boss_type = BossType.ONE_STAR
        task._select_attack()
        self.assertEqual(task._active_attack.lineup, '活动,通用')

    def test_blank_specific_lineup_uses_common_without_mutating_saved_rule(self):
        task = self.task()
        task.conf.lineup_config.specific_bosses[0].first_attack.lineup = ''
        task._select_attack()
        self.assertEqual(task._active_attack.lineup, '活动,五星')
        self.assertEqual(task.conf.lineup_config.specific_bosses[0].first_attack.lineup, '')

    def test_identical_lineup_skips_both_switches_independent_of_power_and_mark(self):
        task = self.task()
        task.conf.lineup_config.preset_enable = True
        task._select_attack()
        task._prepare_lineup()
        task._active_attack.powerful = False
        task._active_attack.mark_main = False
        task._prepare_lineup()
        task._switch_lineup_souls.assert_called_once_with('活动', '第一队')
        task._apply_preset_team.assert_called_once_with('活动', '第一队')

    def test_a_b_b_a_only_switches_on_lineup_change(self):
        task = self.task()
        for attempt in (0, 1, 2):
            task._encounter_attempts = attempt
            task._select_attack()
            task._prepare_lineup()
        task._new_encounter()
        task._select_attack()
        task._prepare_lineup()
        self.assertEqual(task._switch_lineup_souls.call_count, 3)
        task._apply_preset_team.assert_not_called()

    def test_failed_switch_never_updates_cache_and_retry_repeats(self):
        task = self.task()
        task._select_attack()
        task._switch_lineup_souls.side_effect = [GameStuckError('failed'), None]
        with self.assertRaises(GameStuckError):
            task._prepare_lineup()
        self.assertIsNone(task._last_lineup)
        self.assertIsNone(task._lineup_deadline)
        self.assertTrue(task._prepare_lineup())
        self.assertEqual(task._switch_lineup_souls.call_count, 2)

    def test_preset_failure_invalidates_soul_cache_too(self):
        task = self.task()
        task.conf.lineup_config.preset_enable = True
        task._select_attack()
        task._apply_preset_team.return_value = False
        with self.assertRaises(GameStuckError):
            task._prepare_lineup()
        self.assertIsNone(task._last_lineup)
        self.assertIsNone(task._last_preset_lineup)

    def test_next_run_does_not_reuse_prior_lineup_cache(self):
        task = self.task()
        task._select_attack()
        task._prepare_lineup()
        task._reset_combat_plan()
        task._select_attack()
        task._prepare_lineup()
        self.assertEqual(task._switch_lineup_souls.call_count, 2)

    def test_unknown_star_with_configured_special_lineup_cannot_switch(self):
        task = self.task()
        task.cur_boss_type = None
        task._select_attack()
        with self.assertRaises(GameStuckError):
            task._prepare_lineup()
        task._switch_lineup_souls.assert_not_called()

    def test_marking_and_count_progress_only_after_confirmed_battle(self):
        task = self.task()
        task.total_count = 0
        task._select_attack()
        task.run_general_battle = Mock(return_value=False)
        task._fight_current_boss()
        self.assertEqual(task._encounter_attempts, 1)
        self.assertEqual(task.total_count, 1)
        self.assertTrue(task.run_general_battle.call_args.args[0].green_enable)

    def test_soul_switch_requires_confirmation_and_restores_shared_ocr_rules(self):
        from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
        for confirmed in (False, True):
            task = self.task()
            del task._switch_lineup_souls
            task.ui_goto_page = Mock(return_value=True)
            task.screenshot = Mock()
            task.appear = Mock(return_value=False)
            task.click_preset = Mock()
            task.switch_soul_by_name = Mock(side_effect=lambda *a: setattr(task, '_soul_confirmation_clicked', confirmed))
            original = task.O_SS_TEAM_NAME
            previous = SwitchSoul._current_switch_soul
            try:
                SwitchSoul._current_switch_soul = 'stale'
                if confirmed:
                    task._switch_lineup_souls('组', '队')
                else:
                    with self.assertRaises(GameStuckError):
                        task._switch_lineup_souls('组', '队')
                self.assertIs(task.O_SS_TEAM_NAME, original)
                self.assertFalse(task._tracking_soul_confirmation)
                self.assertEqual(SwitchSoul._current_switch_soul, '-')
            finally:
                SwitchSoul._current_switch_soul = previous

    def test_lineup_timeout_keeps_device_stuck_check_enabled(self):
        from tasks.MetaDemon.combat_plan import MetaDemonCombatPlan
        task = self.task()
        task._lineup_deadline = 10
        with patch('tasks.MetaDemon.combat_plan.time.monotonic', return_value=11):
            with self.assertRaises(GameStuckError):
                MetaDemonCombatPlan.screenshot(task)


class MetaDemonLineupApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_structured_list_is_decoded_validated_and_saved_via_existing_endpoint(self):
        import importlib.util
        import json
        from pathlib import Path
        from fastapi import HTTPException
        model = ConfigModel()
        manager = SimpleNamespace(config_cache=Mock(return_value=SimpleNamespace(model=model)))
        spec = importlib.util.spec_from_file_location('_meta_lineup_api', Path(__file__).resolve().parents[1]/'module/server/script_router.py')
        router = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'module.server.main_manager': SimpleNamespace(mm=manager)}):
            spec.loader.exec_module(router)
        with patch.object(ConfigModel, 'save') as save:
            value = [{'boss_name': '白藏主', 'attack_count': 2}]
            self.assertTrue(await router.script_task('offline', 'MetaDemon', 'lineup_config', 'specific_bosses', 'meta_demon_bosses', json.dumps(value)))
            self.assertEqual(model.meta_demon.lineup_config.specific_bosses[0].attack_count, 2)
            save.assert_called_once()
            for malformed in ('{}', 'not json'):
                with self.assertRaises(HTTPException):
                    await router.script_task('offline', 'MetaDemon', 'lineup_config', 'specific_bosses', 'meta_demon_bosses', malformed)
            self.assertEqual(save.call_count, 1)


if __name__ == '__main__':
    unittest.main()
