"""Offline regression for the 2026-11-09 YYS MetaDemon port; no devices."""
import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.exception import GameStuckError
from tasks.Component.BossNum.boss_num import parse_boss_num, BossNumCheck
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Exploration.config import Exploration, Scrolls
from tasks.Exploration.solo import SoloExploration
from tasks.MetaDemon.config import MetaDemon, BossType, MetaDemonPresetSwitchConfig
from tasks.MetaDemon.script_task import ScriptTask


class MetaDemonUpdatesTest(unittest.TestCase):
    def task(self):
        task = ScriptTask.__new__(ScriptTask)
        task.conf = MetaDemon()
        task.State = SimpleNamespace(preset_switch_done=False, switch_soul_done=False)
        task.cur_boss_type = None
        task.cur_boss_name = ''
        task.device = SimpleNamespace(image=np.zeros((720, 1280, 3), dtype=np.uint8), click=Mock())
        task.screenshot = Mock(side_effect=lambda: task.device.image)
        task.click = Mock()
        task.appear = Mock(return_value=True)
        return task

    def test_synthesis_defaults_off_and_parses_only_material_stars(self):
        config = MetaDemon().meta_demon_config
        self.assertEqual(config.synthesize_sequence_v, [])
        config.synthesize_sequence = '1 2 6 0 bad 5'
        self.assertEqual(config.synthesize_sequence_v, [BossType.ONE_STAR, BossType.TWO_STARS, BossType.FIVE_STARS])

    def test_presets_normalize_punctuation_and_keep_soul_compatibility(self):
        config = MetaDemonPresetSwitchConfig(common_stars='活动， 通用', name_map='白藏主：活动，五星；卑弥呼：活动，六星')
        self.assertEqual(config.get_preset_by_enum(BossType.THREE_STARS), ('活动', '通用'))
        self.assertEqual(config.get_preset_by_name('白藏主'), ('活动', '五星'))
        self.assertEqual(config.get_preset_by_name('白藏'), (None, None))
        old = MetaDemon(switch_soul={'enable': True, 'one_star': '1,2'})
        self.assertTrue(old.switch_soul.enable)
        self.assertFalse(old.preset_switch.enable)

    def test_scene_star_requires_two_matching_frames(self):
        task = self.task()
        task.device.image[207:215, 56:124] = (120, 120, 120)
        for i in range(4):
            task.device.image[207:215, 56+11*i:64+11*i] = (255, 190, 0)
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertEqual(task._detect_current_boss_star(), BossType.FOUR_STARS)
        self.assertEqual(task.screenshot.call_count, 2)

    def test_scattered_lit_gems_are_not_a_star_count(self):
        task = self.task()
        task.device.image[207:215, 56:124] = (120, 120, 120)
        task.device.image[207:215, 67:75] = (255, 190, 0)
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertIsNone(task._detect_current_boss_star())

    def test_refresh_star_and_name_reset_only_relevant_switches(self):
        task = self.task()
        task.cur_boss_type = BossType.FIVE_STARS
        task.cur_boss_name = '白藏主'
        task.State.preset_switch_done = task.State.switch_soul_done = True
        task._detect_current_boss_star = Mock(return_value=BossType.FIVE_STARS)
        task._detect_boss_name = Mock(return_value='卑弥呼')
        task._refresh_current_boss_type()
        self.assertFalse(task.State.preset_switch_done)
        self.assertTrue(task.State.switch_soul_done)
        task._reset_switch_on_star_change(BossType.SIX_STARS)
        self.assertFalse(task.State.switch_soul_done)

    def test_unknown_boss_never_guesses_a_preset(self):
        task = self.task()
        task.conf.preset_switch.enable = True
        task._apply_preset_team = Mock()
        with self.assertRaises(GameStuckError):
            task.check_and_switch_preset()
        task._apply_preset_team.assert_not_called()

    def test_name_map_overrides_star_and_preset_suppresses_old_soul_switch(self):
        task = self.task()
        task.cur_boss_type = BossType.FIVE_STARS
        task.cur_boss_name = '白藏主'
        task.conf.preset_switch = MetaDemonPresetSwitchConfig(enable=True, five_stars='活动,默认', name_map='白藏主:活动,专用')
        task._apply_preset_team = Mock(return_value=True)
        self.assertTrue(task.check_and_switch_preset())
        task._apply_preset_team.assert_called_once_with('活动', '专用')
        task.conf.switch_soul.enable = True
        task.ui_goto_page = Mock()
        self.assertTrue(task.check_and_switch_soul())
        task.ui_goto_page.assert_not_called()

    def test_failed_preset_does_not_mark_complete_and_always_closes(self):
        task = self.task()
        task._apply_preset_team_inner = Mock(side_effect=GameStuckError('unconfirmed'))
        task._preset_close_panel = Mock()
        with self.assertRaises(GameStuckError):
            task._apply_preset_team('活动', '队伍')
        task._preset_close_panel.assert_called_once()
        self.assertFalse(task.State.preset_switch_done)

    def test_preset_ocr_click_adds_roi_offset_and_does_not_accept_partial_name(self):
        task = self.task()
        task.swipe = Mock()
        rule = SimpleNamespace(roi=(500, 235, 120, 375), name='group', detect_and_ocr=Mock(return_value=[
            SimpleNamespace(ocr_text='目标队伍', box=[[4, 10], [80, 10], [80, 30], [4, 30]])]))
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertTrue(task._preset_select_by_ocr(rule, '目标队伍'))
            task.device.click.assert_called_once_with(560, 255, control_name='MD_PRESET_group')
            task.device.click.reset_mock()
            self.assertFalse(task._preset_select_by_ocr(rule, '目标'))
        task.device.click.assert_not_called()

    def test_preset_team_roi_covers_fourth_title_and_excludes_rank_badge(self):
        task = self.task()
        rule = task.O_PS_TEAM
        x, y, w, h = rule.roi
        # User's 1280x720 frame: fourth title 雪月, left rank diamond and bottom 出战.
        self.assertLessEqual(x, 687)
        self.assertGreaterEqual(x + w, 724)
        self.assertLessEqual(y, 528)
        self.assertGreaterEqual(y + h, 549)
        self.assertGreater(x, 681)
        self.assertLessEqual(y + h, 550)
        metadata = json.loads((Path(__file__).resolve().parents[1] /
                               'tasks/MetaDemon/md/ocr.json').read_text('utf-8'))
        team = next(item for item in metadata if item['itemName'] == 'ps_team')
        self.assertEqual(team['roiFront'], ','.join(map(str, rule.roi)))
        self.assertEqual(team['roiBack'], ','.join(map(str, rule.area)))

    def test_visible_group_clicks_immediately_without_swiping(self):
        task = self.task()
        task.swipe = Mock(side_effect=AssertionError('visible group must not scroll'))
        rule = copy.copy(task.O_PS_GROUP)
        rule.detect_and_ocr = Mock(return_value=[
            SimpleNamespace(ocr_text='御魂', box=[[25, 25], [75, 25], [75, 45], [25, 45]]),
            SimpleNamespace(ocr_text='活动', box=[[25, 75], [75, 75], [75, 95], [25, 95]])])
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertTrue(task._preset_select_by_ocr(rule, '活动'))
        task.device.click.assert_called_once_with(560, 320, control_name='MD_PRESET_PS_GROUP')
        task.screenshot.assert_called_once()
        rule.detect_and_ocr.assert_called_once_with(task.device.image, box_thresh=0.7)
        task.swipe.assert_not_called()

    def test_fourth_team_title_is_read_only_after_reset_to_top(self):
        task = self.task()
        task._preset_scroll_to_top = Mock(return_value=True)
        task._preset_scroll = Mock()
        rule = copy.copy(task.O_PS_TEAM)
        def read(image, **kwargs):
            task._preset_scroll_to_top.assert_called_once()
            return [SimpleNamespace(ocr_text='雪月', box=[[3, 298], [40, 298], [40, 319], [3, 319]])]
        rule.detect_and_ocr = Mock(side_effect=read)
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertTrue(task._preset_select_by_ocr(rule, '雪月'))
        task.device.click.assert_called_once_with(786, 538, control_name='MD_PRESET_PS_TEAM')
        task._preset_scroll.assert_not_called()

    def test_missing_group_resets_to_top_then_searches_downward(self):
        task = self.task()
        events = []
        task._preset_scroll_to_top = Mock(side_effect=lambda *args: events.append('top') or True)
        task._preset_scroll = Mock(side_effect=lambda *args, **kw: events.append(('scroll', kw['to_top'])))
        rule = copy.copy(task.O_PS_GROUP)
        labels = iter(['御魂', '道馆', '活动'])
        def read(image, **kwargs):
            text = next(labels)
            events.append(text)
            return [SimpleNamespace(ocr_text=text, box=[[25, 75], [75, 75], [75, 95], [25, 95]])]
        rule.detect_and_ocr = Mock(side_effect=read)
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertTrue(task._preset_select_by_ocr(rule, '活动'))
        self.assertEqual(events, ['御魂', 'top', '道馆', ('scroll', False), '活动'])
        task.device.click.assert_called_once_with(560, 320, control_name='MD_PRESET_PS_GROUP')

    def test_search_from_top_stops_at_bottom_without_reversing(self):
        for asset in (self.task().O_PS_TEAM, self.task().O_PS_GROUP):
            with self.subTest(column=asset.name):
                task = self.task()
                task._preset_scroll_to_top = Mock(return_value=True)
                task._preset_scroll = Mock()
                rule = copy.copy(asset)
                rule.detect_and_ocr = Mock(return_value=[])
                with patch('tasks.MetaDemon.script_task.time.sleep'):
                    self.assertFalse(task._preset_select_by_ocr(rule, '雪月'))
                self.assertEqual(task._preset_scroll.call_count, 2)
                for call in task._preset_scroll.call_args_list:
                    self.assertFalse(call.kwargs['to_top'])
                task.device.click.assert_not_called()

    def test_reset_to_top_requires_two_unchanged_list_frames(self):
        task = self.task()
        task.swipe = Mock()
        frames = [np.full((720, 1280, 3), value, dtype=np.uint8) for value in (0, 50, 100, 100, 100)]
        task.screenshot = Mock(side_effect=frames)
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertTrue(task._preset_scroll_to_top(task.O_PS_GROUP, float('inf')))
        self.assertEqual(task.swipe.call_count, 4)
        for call in task.swipe.call_args_list:
            swipe = call.args[0]
            self.assertLess(swipe.roi_front[1], swipe.roi_back[1])
            x, y, w, h = task.O_PS_GROUP.roi
            for sx, sy, sw, sh in (swipe.roi_front, swipe.roi_back):
                self.assertTrue(x <= sx < sx + sw <= x + w)
                self.assertTrue(y <= sy < sy + sh <= y + h)

    def test_top_reset_failure_does_not_read_or_click_team(self):
        task = self.task()
        task._preset_scroll_to_top = Mock(return_value=False)
        rule = copy.copy(task.O_PS_TEAM)
        rule.detect_and_ocr = Mock()
        self.assertFalse(task._preset_select_by_ocr(rule, '雪月'))
        rule.detect_and_ocr.assert_not_called()
        task.device.click.assert_not_called()

    def test_top_reset_is_bounded_when_list_keeps_moving(self):
        task = self.task()
        task.swipe = Mock()
        task.screenshot = Mock(side_effect=[np.full((720, 1280, 3), 10*i, dtype=np.uint8) for i in range(11)])
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertFalse(task._preset_scroll_to_top(task.O_PS_TEAM, float('inf')))
        self.assertEqual(task.swipe.call_count, 10)

    def test_preset_search_obeys_outer_deadline_without_click_or_swipe(self):
        task = self.task()
        task.swipe = Mock()
        rule = copy.copy(task.O_PS_GROUP)
        rule.detect_and_ocr = Mock()
        with patch('tasks.MetaDemon.script_task.time.monotonic', return_value=100):
            self.assertFalse(task._preset_select_by_ocr(rule, '活动', deadline=99))
        rule.detect_and_ocr.assert_not_called()
        task.swipe.assert_not_called()
        task.device.click.assert_not_called()

    def test_team_after_top_reset_uses_new_frame_each_page(self):
        task = self.task()
        task._preset_scroll_to_top = Mock(return_value=True)
        task._preset_scroll = Mock()
        rule = copy.copy(task.O_PS_TEAM)
        rule.detect_and_ocr = Mock(side_effect=[[], [SimpleNamespace(
            ocr_text='雪月', box=[[3, 20], [40, 20], [40, 40], [3, 40]])]])
        with patch('tasks.MetaDemon.script_task.time.sleep'):
            self.assertTrue(task._preset_select_by_ocr(rule, '雪月'))
        self.assertEqual(task.screenshot.call_count, 2)
        task._preset_scroll.assert_called_once_with(rule, to_top=False)
        task.device.click.assert_called_once_with(786, 260, control_name='MD_PRESET_PS_TEAM')

    def test_boss_name_stops_before_separate_skill_label(self):
        task = self.task()
        task.O_MD_BOSS_NAME = Mock()
        task.O_MD_BOSS_NAME.detect_and_ocr.return_value = [
            SimpleNamespace(ocr_text=text, box=[[0, y], [10, y], [10, y+15], [0, y+15]])
            for text, y in [('白', 0), ('藏主', 20), ('技能x6', 100)]]
        self.assertEqual(task._detect_boss_name(task.device.image), '白藏主')

    def test_selected_ticket_uses_image_at_marker_and_keeps_shared_roi(self):
        task = self.task()
        task.I_MD_CHECK_SELECTED = copy.copy(task.I_MD_CHECK_SELECTED)
        task.I_MD_CHECK_SELECTED.roi_front = (370, 280, 20, 20)
        rules = {BossType(i): copy.copy(getattr(task, name)) for i, name in enumerate([
            'I_MD_ONE_STAR', 'I_MD_TWO_STARS', 'I_MD_THREE_STARS', 'I_MD_FOUR_STARS', 'I_MD_FIVE_STARS', 'I_MD_SIX_STARS'], 1)}
        template = rules[BossType.THREE_STARS].image
        h, w = template.shape[:2]
        task.device.image[315:315+h, 350:350+w] = template
        originals = {k: r.roi_back for k, r in rules.items()}
        self.assertEqual(task._classify_selected_ticket(rules), BossType.THREE_STARS)
        self.assertEqual({k: r.roi_back for k, r in rules.items()}, originals)

    def test_synthesis_unconfirmed_debit_never_repeats_start(self):
        task = self.task()
        task._read_synth_number = Mock(side_effect=[6, 6])
        original_roi = task.O_MD_SYNTH_COUNT_ONE.roi
        with patch('tasks.MetaDemon.script_task.time.sleep'), self.assertRaises(GameStuckError):
            task._synthesize_one_type(BossType.ONE_STAR)
        starts = [c for c in task.click.call_args_list if c.args[0] is task.I_MD_SYNTH_START]
        self.assertEqual(len(starts), 1)
        self.assertEqual(task.O_MD_SYNTH_COUNT_ONE.roi, original_roi)

    def test_synthesis_failed_ocr_or_no_paid_ticket_never_starts(self):
        for values in ([6, 0], [2]):
            task = self.task()
            task._read_synth_number = Mock(side_effect=values)
            with patch('tasks.MetaDemon.script_task.time.sleep'):
                task._synthesize_one_type(BossType.TWO_STARS)
            task.click.assert_not_called()
        task = self.task()
        with patch('tasks.MetaDemon.script_task.RuleOcr') as rule:
            rule.return_value.detect_and_ocr.return_value = [SimpleNamespace(ocr_text='6?')]
            with self.assertRaises(GameStuckError):
                task._read_synth_number(task.O_MD_SYNTH_COUNT_ONE)

    def test_source_assets_and_json_definitions_match(self):
        from tasks.MetaDemon.assets import MetaDemonAssets
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root/'upstream/meta_demon_update_20261109.json').read_text(encoding='utf-8'))
        for item in manifest['assets']:
            self.assertEqual(hashlib.sha256((root/item['target']).read_bytes()).hexdigest(), item['sha256'])
        for row in json.loads((root/'tasks/MetaDemon/md/image.json').read_text(encoding='utf-8')):
            rule = getattr(MetaDemonAssets, 'I_'+row['itemName'].upper())
            self.assertEqual(Path(rule.file).name, row['imageName'])
            self.assertEqual(tuple(rule.roi_back), tuple(map(int, row['roiBack'].split(','))))


class BossTicketUpdatesTest(unittest.TestCase):
    def test_strict_ticket_parser(self):
        for bad in ('5050', '50/50abc', '51/50', '-1/50', '0/0', '50/5O'):
            self.assertIsNone(parse_boss_num(bad), bad)
        self.assertEqual(parse_boss_num(' 49 / 50 '), (49, 50))

    def test_reader_uses_full_screenshot_public_ocr(self):
        reader = BossNumCheck()
        reader.device = SimpleNamespace(image=np.zeros((720, 1280, 3)))
        with patch('tasks.Component.BossNum.boss_num.RuleOcr') as rule:
            rule.return_value.detect_and_ocr.return_value = [SimpleNamespace(ocr_text='50/50')]
            self.assertEqual(reader.read_settle_boss_num(), (50, 50))
            self.assertIs(rule.return_value.detect_and_ocr.call_args.args[0], reader.device.image)
            self.assertEqual(rule.call_args.kwargs['mode'], 'Full')

    def test_battle_override_legacy_and_new_signature(self):
        task = GeneralBattle.__new__(GeneralBattle)
        for fn in (lambda flag: 'old', lambda flag, boss_num_enable=False: boss_num_enable):
            task.battle_wait = fn
            task.boss_num_full = True
            result = task._battle_wait(False, True)
            self.assertIn(result, ('old', True))
            self.assertFalse(task.boss_num_full)

    def test_full_only_when_exact_fifty_and_once_per_battle(self):
        task = GeneralBattle.__new__(GeneralBattle)
        for ticket, expected in [((30, 30), False), ((49, 50), False), ((50, 50), True)]:
            task.boss_num_read = task.boss_num_full = False
            task.read_settle_boss_num = Mock(return_value=ticket)
            task._try_read_boss_num(True)
            self.assertEqual(task.boss_num_full, expected)
        task._try_read_boss_num(True)
        task.read_settle_boss_num.assert_called_once()

    def exploration(self):
        task = SoloExploration.__new__(SoloExploration)
        task._config = Exploration()
        task.current_boss_cnt = task.current_count = 0
        task.min_boss_cnt = task.limit_count = 100
        task.start_time = datetime.now()
        task.limit_time = timedelta(hours=1)
        task.boss_num_full_pending = True
        task.appear = Mock(return_value=False)
        task.activate_realm_raid = Mock()
        return task

    def test_pending_tickets_finish_only_after_chapter(self):
        task = self.exploration()
        task._config.scrolls.check_boss_num = True
        self.assertFalse(task.check_exit(False))
        self.assertFalse(task.check_exit())
        task.appear.return_value = True
        self.assertTrue(task.check_exit())

    def test_world_ticket_full_returns_to_normal_cleanup(self):
        task = self.exploration()
        task._config.scrolls.check_boss_num = True
        task.read_boss_num = Mock(return_value=(50, 50))
        task.set_next_run = Mock()
        self.assertTrue(task.check_boss_number(task._config.scrolls))
        task.set_next_run.assert_not_called()
        task.read_boss_num.return_value = None
        self.assertFalse(task.check_boss_number(task._config.scrolls))

    def test_exploration_updated_counter_regions_match_json(self):
        from tasks.Exploration.assets import ExplorationAssets
        root = Path(__file__).resolve().parents[1]
        rows = json.loads((root/'tasks/Exploration/res/ocr.json').read_text(encoding='utf-8'))
        for row in rows:
            if row['itemName'] in ('realm_raid_number', 'check_boss_num'):
                rule = getattr(ExplorationAssets, 'O_'+row['itemName'].upper())
                self.assertEqual(tuple(rule.roi), tuple(map(int, row['roiFront'].split(','))))
        self.assertEqual(tuple(ExplorationAssets.O_CHECK_BOSS_NUM.roi), (948, 14, 64, 32))

    def test_breakthrough_check_only_in_chapter_details(self):
        task = self.exploration()
        task._config.scrolls.check_realm_raid = True
        self.assertFalse(task.check_exit())
        task.activate_realm_raid.assert_not_called()
        task.appear.return_value = True
        self.assertFalse(task.check_exit())
        task.activate_realm_raid.assert_called_once()

    def test_breakthrough_threshold_range(self):
        for value in (0, 31, -1):
            with self.assertRaises(ValueError):
                Scrolls(realm_raid_threshold=value)

    def test_breakthrough_does_not_schedule_memory_scrolls_or_accept_bad_counter(self):
        from module.exception import TaskEnd
        from tasks.Exploration.base import BaseExploration
        task = self.exploration()
        del task.activate_realm_raid  # exercise the real implementation
        task._config.scrolls.check_realm_raid = True
        task.device = SimpleNamespace(image=None)
        task.config = SimpleNamespace(realm_raid=SimpleNamespace(scheduler=SimpleNamespace(enable=True)))
        task.screenshot = Mock()
        task.appear = Mock(side_effect=lambda target, **kw: isinstance(target, list))
        task.O_REALM_RAID_NUMBER1 = Mock()
        task.set_next_run = Mock()
        for counter in ((31, -1, 30), (29, 2, 30), (26, 4, 30)):
            task.O_REALM_RAID_NUMBER1.ocr.return_value = counter
            BaseExploration.activate_realm_raid(task, task._config.scrolls, task._config.exploration_config)
            task.set_next_run.assert_not_called()
        task.O_REALM_RAID_NUMBER1.ocr.return_value = (27, 3, 30)
        with self.assertRaises(TaskEnd):
            BaseExploration.activate_realm_raid(task, task._config.scrolls, task._config.exploration_config)
        scheduled = [c.kwargs['task'] for c in task.set_next_run.call_args_list]
        self.assertEqual(scheduled, ['Exploration', 'RealmRaid'])

    def test_evo_member_and_takeover_stop_after_full_settlement(self):
        from tasks.EvoZone.config import EvoZone
        from tasks.EvoZone.script_task import ScriptTask as EvoTask
        for in_room in (True, False):
            task = EvoTask.__new__(EvoTask)
            task.config = SimpleNamespace(evo_zone=EvoZone())
            task.config.evo_zone.evo_zone_config.check_boss_num = True
            task.current_count = 0
            task.limit_count = 10
            task.start_time = datetime.now()
            task.limit_time = timedelta(hours=1)
            task.device = Mock()
            task.screenshot = Mock()
            task.check_pet_reward = Mock(return_value=False)
            task.check_then_accept = Mock(return_value=False)
            task.is_in_room = Mock(return_value=in_room)
            task.wait_battle = Mock(return_value=True)
            def settled(*args, **kwargs):
                self.assertTrue(kwargs['boss_num_enable'])
                task.boss_num_full = True
                return True
            task.run_general_battle = Mock(side_effect=settled)
            task.check_take_over_battle = Mock(side_effect=settled)
            self.assertTrue(task.run_member())
            called = task.run_general_battle if in_room else task.check_take_over_battle
            called.assert_called_once()
            task.screenshot.assert_called_once()

    def test_ticket_polling_is_disabled_by_default_and_throttled(self):
        task = GeneralBattle.__new__(GeneralBattle)
        task.boss_num_read = False
        task._boss_num_last_try = 0.0
        task._try_read_boss_num = Mock()
        with patch('tasks.Component.GeneralBattle.general_battle.time.monotonic', side_effect=[1.0, 1.1, 1.6]):
            task._poll_boss_num(False)
            task._poll_boss_num(True)
            task._poll_boss_num(True)
            task._poll_boss_num(True)
        self.assertEqual(task._try_read_boss_num.call_count, 2)

    def test_evo_leader_stops_after_full_first_or_subsequent_battle(self):
        from tasks.EvoZone.config import EvoZone
        from tasks.EvoZone.script_task import ScriptTask as EvoTask
        for full_at in (1, 2):
            task = EvoTask.__new__(EvoTask)
            task.config = SimpleNamespace(evo_zone=EvoZone())
            task.config.evo_zone.evo_zone_config.check_boss_num = True
            task.current_count = 0
            task.limit_count = 10
            task.start_time = datetime.now()
            task.limit_time = timedelta(hours=1)
            for name in ('ui_goto_page', 'evozone_enter', 'check_layer', 'check_lock', 'create_room',
                         'ensure_private', 'create_ensure', 'screenshot'):
                setattr(task, name, Mock())
            task.appear = task.is_in_room = task.run_invite = Mock(return_value=True)
            task.check_and_invite = task.check_pet_reward = Mock(return_value=False)
            calls = []
            def settled(*args, **kwargs):
                self.assertTrue(kwargs['boss_num_enable'])
                calls.append(kwargs)
                task.boss_num_full = len(calls) == full_at
            task.run_general_battle = Mock(side_effect=settled)
            self.assertTrue(task.run_leader())
            self.assertEqual(len(calls), full_at)

    def test_evo_solo_full_ticket_still_closes_buff_and_schedules(self):
        from module.exception import TaskEnd
        from tasks.EvoZone.config import EvoZone
        from tasks.EvoZone.script_task import ScriptTask as EvoTask
        task = EvoTask.__new__(EvoTask)
        con = EvoZone()
        con.evo_zone_config.check_boss_num = con.evo_zone_config.soul_buff_enable = True
        task.config = SimpleNamespace(evo_zone=con)
        task.start_time = datetime.now()
        task.limit_time = timedelta(hours=1)
        for name in ('ui_goto_page', 'evozone_enter', 'check_layer', 'check_lock', 'screenshot',
                     'ui_click_until_disappear', 'save_progress_current_count', 'check_buff', 'set_next_run'):
            setattr(task, name, Mock())
        task.appear = Mock(return_value=True)
        task.check_pet_reward = Mock(return_value=False)
        def settled(*args, **kwargs):
            self.assertTrue(kwargs['boss_num_enable'])
            task.boss_num_full = True
        task.run_general_battle = Mock(side_effect=settled)
        with self.assertRaises(TaskEnd):
            task.run_alone(con)
        task.run_general_battle.assert_called_once()
        task.check_buff.assert_called_once()
        task.set_next_run.assert_called_once_with('EvoZone', finish=True, success=True)


if __name__ == '__main__':
    unittest.main()
