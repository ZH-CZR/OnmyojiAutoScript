"""Exercise outgoing cooperation filters without a device or game input."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from module.config.config_model import ConfigModel
from tasks.WantedQuests.config import (
    CooperationSelectMask, CooperationSelectMaskDescription, WantedQuestsConfig,
)
from tasks.WantedQuests.script_task import ScriptTask


class WantedCooperationTest(unittest.TestCase):
    def setUp(self):
        self.task = ScriptTask.__new__(ScriptTask)
        self.settings = WantedQuestsConfig(cooperation_type='GoldAndFoodAndSushi')
        self.task.config = SimpleNamespace(wanted_quests=SimpleNamespace(
            wanted_quests_config=self.settings))
        self.task.screenshot = Mock()
        self.task.ui_click = Mock()
        self.task.click = Mock()
        self.task.ui_click_until_disappear = Mock()
        self.task.cooperation_invite = Mock(return_value=True)
        self.visible = set()
        self.task.appear = Mock(side_effect=lambda image: image.name in self.visible)
        self.sleep = patch('tasks.WantedQuests.script_task.sleep')
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def button(self, slot):
        return getattr(self.task, f'I_WQ_INVITE_{slot}')

    def show(self, *rewards):
        self.visible = {self.task.I_WQ_INVITE_SELECTED.name}
        for slot, reward in enumerate(rewards, 1):
            if reward is None:
                continue
            self.visible.add(self.button(slot).name)
            if reward != 'UNKNOWN':
                self.visible.add(getattr(self.task, f'I_WQ_COOPERATION_TYPE_{reward}_{slot}').name)
            # 食协附带金币，不能因此误识别为金币协作。
            if reward in ('CAT_FOOD', 'DOG_FOOD'):
                self.visible.add(getattr(self.task, f'I_WQ_COOPERATION_TYPE_GOLD_{slot}').name)

    def test_every_mask_filters_both_invitation_modes(self):
        for selection in CooperationSelectMaskDescription:
            self.settings.cooperation_type = selection
            mask = CooperationSelectMask[selection.value].value
            for reward, bit in (('GOLD', 1), ('JADE', 2), ('DOG_FOOD', 4),
                                ('CAT_FOOD', 4), ('SUSHI', 8)):
                for named in (False, True):
                    with self.subTest(selection=selection, reward=reward, named=named):
                        self.show(reward)
                        self.task.ui_click.reset_mock()
                        self.task.cooperation_invite.reset_mock()
                        if named:
                            self.task.all_cooperation_invite('测试好友')
                            invited = self.task.cooperation_invite.called
                        else:
                            self.task.invite_five()
                            invited = self.task.ui_click.called
                        self.assertEqual(invited, bool(mask & bit))

    def test_skipping_jade_does_not_skip_later_slots(self):
        for named in (False, True):
            with self.subTest(named=named):
                self.show('JADE', 'CAT_FOOD', 'SUSHI')
                if named:
                    self.task.all_cooperation_invite('测试好友')
                    self.assertEqual(self.task.cooperation_invite.call_args_list, [
                        call(self.button(2), '测试好友'), call(self.button(3), '测试好友')])
                else:
                    self.task.invite_five()
                    self.assertEqual([args.args[0] for args in self.task.ui_click.call_args_list],
                                     [self.button(2), self.button(3)])

    def test_missing_first_button_does_not_hide_later_cooperations(self):
        self.show(None, 'GOLD', 'UNKNOWN')
        info = self.task.get_cooperation_info()
        self.assertEqual([item['inviteBtn'] for item in info], [self.button(2)])
        self.task.all_cooperation_invite('测试好友')
        self.task.cooperation_invite.assert_called_once_with(self.button(2), '测试好友')
        self.task.invite_five()
        self.assertEqual([args.args[0] for args in self.task.ui_click.call_args_list], [self.button(2)])

    def test_changed_list_is_checked_before_next_invitation(self):
        for named in (False, True):
            with self.subTest(named=named):
                self.show('GOLD', 'SUSHI')
                self.task.ui_click.reset_mock()
                self.task.cooperation_invite.reset_mock()

                def accepted(*args, **kwargs):
                    self.show(None, 'JADE')
                    return True

                if named:
                    self.task.cooperation_invite.side_effect = accepted
                    self.task.all_cooperation_invite('测试好友')
                    self.task.cooperation_invite.assert_called_once_with(self.button(1), '测试好友')
                else:
                    self.task.ui_click_until_disappear.side_effect = accepted
                    self.task.invite_five()
                    self.assertEqual([args.args[0] for args in self.task.ui_click.call_args_list],
                                     [self.button(1)])

    def test_failed_named_invitation_rechecks_type_before_retry(self):
        self.show('GOLD')

        def changed(*args):
            self.show('JADE')
            return False

        self.task.cooperation_invite.side_effect = changed
        self.task.all_cooperation_invite('测试好友')
        self.task.cooperation_invite.assert_called_once_with(self.button(1), '测试好友')

    def test_unknown_reward_is_skipped_even_with_all_types_enabled(self):
        self.settings.cooperation_type = CooperationSelectMaskDescription.Any
        self.show('UNKNOWN')
        self.task.invite_five()
        self.task.all_cooperation_invite('测试好友')
        self.task.ui_click.assert_not_called()
        self.task.cooperation_invite.assert_not_called()

    def test_selection_roundtrips_and_is_exposed_with_chinese_labels(self):
        self.assertEqual(WantedQuestsConfig().cooperation_type, CooperationSelectMaskDescription.Any)
        restored = WantedQuestsConfig.model_validate_json(self.settings.model_dump_json())
        self.assertEqual(restored.cooperation_type, CooperationSelectMaskDescription.GoldAndFoodAndSushi)
        fields = ConfigModel().script_task('WantedQuests')['wanted_quests_config']
        field = next(item for item in fields if item['name'] == 'cooperation_type')
        self.assertIn('GoldAndFoodAndSushi', field['enumEnum'])
        labels = json.loads((Path(__file__).resolve().parents[1] / 'assets/i18n/zh-CN.json').read_text('utf-8'))
        for option in field['enumEnum']:
            self.assertIn(option, labels)
        self.assertNotIn('仅在存在', labels[field['description']])


if __name__ == '__main__':
    unittest.main()
