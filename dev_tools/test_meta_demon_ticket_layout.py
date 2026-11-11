"""Real template matching on variable ticket layouts; no game or device."""
import copy
import unittest
from types import SimpleNamespace

import numpy as np

from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemon.config import BossType
from tasks.MetaDemon.script_task import ScriptTask


class TicketLayoutTest(unittest.TestCase):
    def test_missing_and_reordered_tickets_follow_actual_positions(self):
        names = ('ONE_STAR', 'TWO_STARS', 'THREE_STARS', 'FOUR_STARS', 'FIVE_STARS', 'SIX_STARS')
        for stars in ((2, 3, 4, 5, 6), (1, 3, 6), (6,), (5, 2, 4), tuple(range(1, 7)), ()):
            with self.subTest(stars=stars):
                task = ScriptTask.__new__(ScriptTask)
                image = np.zeros((720, 1280, 3), dtype=np.uint8)
                rules = {BossType(i): copy.deepcopy(getattr(MetaDemonAssets, 'I_MD_' + name))
                         for i, name in enumerate(names, 1)}
                original_rois = {star: tuple(rule.roi_front) for star, rule in rules.items()}
                for column, star in enumerate(stars):
                    icon = rules[BossType(star)].image
                    h, w = icon.shape[:2]
                    x = 330 + column * 99
                    image[317:317+h, x:x+w] = icon
                task.device = SimpleNamespace(image=image)
                tickets = task._visible_summon_tickets(rules)
                self.assertEqual([int(star) for star, _ in tickets], list(stars))
                for column, (_, rule) in enumerate(tickets):
                    self.assertTrue(rule.match(image, threshold=.92))
                    self.assertLess(abs(rule.roi_front[0] - (330 + column * 99)), 3)
                self.assertEqual({star: tuple(rule.roi_front) for star, rule in rules.items()}, original_rois)


if __name__ == '__main__':
    unittest.main()
