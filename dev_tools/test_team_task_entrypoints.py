"""Exercise public-room tasks and guard against bypassing the shared click API."""
import ast
import importlib
import inspect
from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from module.config.config_model import ConfigModel
from module.exception import TaskEnd
from tasks.Component.Costume.config import TeamType
from tasks.Component.GeneralInvite.general_invite import GeneralInvite, RoomType


class TeamEntrypointTest(unittest.TestCase):
    def replay(self, cls, scene, join_at=None, method='run', solo=False):
        task = cls.__new__(cls)
        task.config = ConfigModel()
        task.start_time = datetime(2026, 10, 19)
        task.check_costume_team(scene)
        clock = [0.0]
        state = {'in_room': method != 'run', 'created': 0.0, 'clicks': []}

        class Timer:
            def __init__(self, seconds):
                self.seconds = seconds

            def start(self):
                self.start_at = clock[0]
                return self

            def reached(self):
                return clock[0] - self.start_at >= self.seconds

        def create():
            state.update(in_room=True, created=clock[0])
            task._room_animation_timer = None
            task._room_member_checks = {}
            return True

        def appear(asset, **kwargs):
            if not state['in_room']:
                return False
            if asset.name in ('I_GI_IN_ROOM', 'I_FIRE'):
                return True
            if asset.name in ('I_ADD_1', 'I_ADD_2', 'I_ADD_5_1'):
                elapsed = clock[0] - state['created']
                return elapsed >= 1 and (join_at is None or elapsed < join_at)
            return False

        def click(asset, **kwargs):
            if asset.name != 'I_FIRE':
                return False
            elapsed = clock[0] - state['created']
            if not solo:
                self.assertIsNotNone(join_at, 'An empty room cannot start a team battle')
                self.assertGreaterEqual(elapsed, join_at)
            state['clicks'].append(elapsed)
            state['in_room'] = False
            return True

        for name in ('ui_goto_page', 'check_zones', 'ensure_public', 'create_ensure',
                     'run_general_battle', 'set_next_run', 'check_buff'):
            setattr(task, name, Mock())
        task.exit_room = Mock(side_effect=lambda: state.update(in_room=False))
        task.create_room = Mock(side_effect=create)
        task.screenshot = Mock(side_effect=lambda: clock.__setitem__(0, clock[0] + 0.2))
        task.appear = Mock(side_effect=appear)
        task.appear_then_click = Mock(side_effect=click)
        with patch(cls.__module__ + '.Timer', Timer), \
                patch('tasks.Component.GeneralInvite.general_invite.Timer', Timer), \
                patch('tasks.Component.GeneralInvite.general_invite.monotonic', side_effect=lambda: clock[0]):
            if method == 'run':
                with self.assertRaises(TaskEnd):
                    task.run()
            elif method == 'wait_in_room':
                task.wait_in_room(12)
            else:
                self.assertTrue(task.netherworld())
        return task, state

    def test_gold_and_tako_empty_rooms_do_not_start(self):
        from tasks.GoldYoukai.script_task import ScriptTask as Gold
        from tasks.Tako.script_task import ScriptTask as Tako
        for cls in (Gold, Tako):
            for scene in TeamType:
                with self.subTest(task=cls.__module__, scene=scene):
                    task, state = self.replay(cls, scene)
                    self.assertFalse(state['clicks'])
                    task.run_general_battle.assert_not_called()
                    task.exit_room.assert_called_once()
                    if cls is Gold:
                        self.assertFalse(task.set_next_run.call_args.kwargs['success'])

    def test_public_room_tasks_start_after_a_member_joins(self):
        from tasks.GoldYoukai.script_task import ScriptTask as Gold
        from tasks.Tako.script_task import ScriptTask as Tako
        from tasks.NianTrue.script_task import ScriptTask as Nian
        for cls, method in ((Gold, 'run'), (Tako, 'run'), (Nian, 'wait_in_room')):
            for scene in TeamType:
                with self.subTest(task=cls.__module__, scene=scene):
                    task, state = self.replay(cls, scene, join_at=6, method=method)
                    self.assertTrue(state['clicks'])
                    self.assertTrue(task.run_general_battle.called)

    def test_nian_timeout_and_hunt_keep_explicit_solo_behavior(self):
        from tasks.NianTrue.script_task import ScriptTask as Nian
        from tasks.Hunt.script_task import ScriptTask as Hunt
        for scene in TeamType:
            task, state = self.replay(Nian, scene, method='wait_in_room', solo=True)
            self.assertEqual(len(state['clicks']), 1)
            self.assertGreaterEqual(state['clicks'][0], 12)
            _, state = self.replay(Hunt, scene, method='netherworld', solo=True)
            self.assertEqual(len(state['clicks']), 1)
            self.assertGreaterEqual(state['clicks'][0], 3)

    def test_click_api_cannot_omit_room_or_assume_members(self):
        task = GeneralInvite.__new__(GeneralInvite)
        with self.assertRaises(TypeError):
            task.click_fire()
        task.screenshot = Mock()
        task.is_in_room = Mock(return_value=True)
        task._room_animation_timer = Mock()
        task._room_animation_timer.reached.return_value = True
        task.room_has_members = Mock(return_value=False)
        task.appear_then_click = Mock()
        self.assertFalse(task.click_fire(RoomType.NORMAL_3))
        task.appear_then_click.assert_not_called()

    def test_exploration_waits_for_stable_members_and_rechecks_before_start(self):
        from tasks.Exploration.solo import SoloExploration, Scene
        for stable, clicked in ((False, False), (True, False), (True, True)):
            with self.subTest(stable=stable, clicked=clicked):
                task = SoloExploration.__new__(SoloExploration)
                task.config = ConfigModel()
                task.__dict__['_config'] = task.config.exploration
                task.screenshot = Mock()
                task.get_current_scene = Mock(side_effect=[Scene.TEAM, RuntimeError('end replay')])
                task.room_has_members = Mock(return_value=stable)
                task.appear = Mock(return_value=False)
                task.click_fire = Mock(return_value=clicked)
                task.is_first = True
                with self.assertRaisesRegex(RuntimeError, 'end replay'):
                    task.run_leader()
                task.room_has_members.assert_called_once_with(RoomType.NORMAL_2)
                if stable:
                    task.click_fire.assert_called_once_with(RoomType.NORMAL_2)
                else:
                    task.click_fire.assert_not_called()
                self.assertEqual(task.is_first, not clicked)

    def test_task_sources_do_not_bypass_common_team_start(self):
        root = Path(__file__).resolve().parents[1] / 'tasks'
        from module.config.config_menu import ConfigMenu
        paths = set()
        for tasks in ConfigMenu().gui_menu_list.values():
            for name in tasks:
                if name in {'Script', 'GlobalGame'}:
                    continue
                cls = importlib.import_module(f'tasks.{name}.script_task').ScriptTask
                if not issubclass(cls, GeneralInvite):
                    continue
                for base in cls.__mro__:
                    if base is not GeneralInvite and issubclass(base, GeneralInvite):
                        paths.add(Path(inspect.getfile(base)).resolve().relative_to(root))
        # Exploration selects this helper dynamically rather than inheriting it.
        paths.add(Path('Exploration/solo.py'))
        for path in paths:
            tree = ast.parse((root / path).read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr == 'click_fire':
                    self.assertTrue(node.args, (path, node.lineno))
                if node.func.attr in ('click', 'appear_then_click', 'ui_click_until_disappear'):
                    for arg in node.args:
                        self.assertFalse(isinstance(arg, ast.Attribute)
                                         and isinstance(arg.value, ast.Name)
                                         and arg.value.id == 'self' and arg.attr == 'I_FIRE',
                                         (path, node.lineno))


if __name__ == '__main__':
    unittest.main()
