"""新版协作红色加号与收到邀请的局部截图离线回放。"""
from pathlib import Path
import unittest

import cv2
import numpy as np

from dev_tools.test_wanted_ui import make_task
from dev_tools import test_wanted_invitation as invitation_tests
from tasks.GlobalGame.config_emergency import FriendInvitation
from tasks.WantedQuests.config import CooperationType


FIXTURES = Path(__file__).parent / 'fixtures' / 'wanted_cooperation'


def paste(image, name, x, y):
    patch = cv2.cvtColor(cv2.imread(str(FIXTURES / (name + '.png'))), cv2.COLOR_BGR2RGB)
    h, w = patch.shape[:2]
    image[y:y+h, x:x+w] = patch


class WantedCooperationLayoutTest(unittest.TestCase):
    def outgoing(self):
        task = make_task()
        image = np.full((720, 1280, 3), 90, dtype=np.uint8)
        paste(image, 'outgoing', 104, 385)
        title = task.I_WQ_PANEL.image
        image[54:89, 578:704] = title
        task.appear = lambda rule: rule.match(image)
        return task, image

    def test_real_two_cooperations_and_food_before_gold(self):
        task, image = self.outgoing()
        info = task.get_cooperation_info()
        self.assertEqual([(v['type'], v['inviteBtn'].name) for v in info],
                         [(CooperationType.Jade, 'I_WQ_INVITE_1'),
                          (CooperationType.Food, 'I_WQ_INVITE_2')])
        # 默认不邀请勾协；食协即使附带金币也按食协筛选。
        self.assertFalse(task._cooperation_allowed(task.I_WQ_INVITE_1))
        self.assertTrue(task._cooperation_allowed(task.I_WQ_INVITE_2))
        for slot in (1, 2):
            for _ in range(100):
                x, y = task._cooperation_click(getattr(task, f'I_WQ_INVITE_{slot}')).coord()
                self.assertLess((x-(135+268*(slot-1)))**2+(y-416)**2, 25**2)

    def test_text_without_plus_cannot_start_invitation(self):
        task, image = self.outgoing()
        image[385:449, 104:170] = 90
        self.assertEqual([v['inviteBtn'].name for v in task.get_cooperation_info()], ['I_WQ_INVITE_2'])

    def test_incoming_jade_and_food_all_policies_through_public_handler(self):
        for kind in ('jade', 'food'):
            for policy in (FriendInvitation.ACCEPT, FriendInvitation.REJECT, FriendInvitation.IGNORE,
                           FriendInvitation.ONLY_JADE, FriendInvitation.JADE_SUSHI_FOOD):
                with self.subTest(kind=kind, policy=policy):
                    replay = invitation_tests.WantedInvitationImageTests()
                    replay.setUp()
                    image = replay.device.image
                    paste(image, kind + '_reward', 565, 465)
                    paste(image, kind + '_actions', 830, 460)
                    paste(image, kind + '_close', 780, 75)
                    replay.task.config.config_reload_event = None
                    replay.task.config.wanted_quests.emergency.friend_invitation = policy
                    self.assertEqual(replay.task.appear(replay.task.I_G_JADE), kind == 'jade')
                    self.assertEqual(replay.task.appear(replay.task.I_G_CAT_FOOD), kind == 'food')
                    accepted = policy in (FriendInvitation.ACCEPT, FriendInvitation.JADE_SUSHI_FOOD) or (
                        policy == FriendInvitation.ONLY_JADE and kind == 'jade')
                    expected = 'I_G_ACCEPT' if accepted else (
                        'I_G_REJECT' if policy == FriendInvitation.REJECT else 'I_G_IGNORE')
                    replay.task.screenshot()
                    replay.device.click.assert_called_once()
                    self.assertEqual(replay.device.click.call_args.kwargs['control_name'], expected)
                    self.assertEqual(replay.task.config.cooperation_store.request.call_count, int(accepted))
                    self.assertIn('BATTLE_STATUS_S', replay.device.detect_record)


if __name__ == '__main__':
    unittest.main()
