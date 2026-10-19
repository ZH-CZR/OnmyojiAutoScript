# This Python file uses the following encoding: utf-8
"""批次 28 上游修复回归测试。

本轮可落地两项：
1. ``b1c7186c`` 更新共享邀请确认按钮 ``I_INVITE_ENSURE`` 的 ROI（#1939 后续），
   邀请确认按钮在「想做的事」好友邀请界面左移、搜索区扩大；
2. ``107e9542`` 桌面客户端重启时，已登录（窗口在运行）才先停客户端，停在登录页
   则直接复用，避免多关一次导致退出导航被提前打断。

``a70757b1``（Exploration 退出前误返回）面向上游 ``I_BACK_YOLLOW`` 旧退出循环，
本地已改为页面导航（``quit_exp_main`` / ``page_exp_exit``），无该落点，不适用。
"""
import inspect
import json
import unittest
from pathlib import Path

from tasks.Component.GeneralInvite.assets import GeneralInviteAssets
from tasks.WantedQuests.script_task import ScriptTask as WantedQuestsTask


class InviteEnsureRoiTests(unittest.TestCase):
    RULE = GeneralInviteAssets.I_INVITE_ENSURE

    def test_asset_uses_wanted_quests_roi(self):
        self.assertEqual(tuple(self.RULE.roi_front), (517, 553, 132, 60))
        self.assertEqual(tuple(self.RULE.roi_back), (473, 505, 409, 121))
        self.assertEqual(self.RULE.threshold, 0.8)

    def test_image_json_matches_asset(self):
        data = json.loads(Path('tasks/Component/GeneralInvite/gi/image.json').read_text(encoding='utf-8'))
        item = next(entry for entry in data if entry['itemName'] == 'invite_ensure')
        self.assertEqual(item['roiFront'], '517,553,132,60')
        self.assertEqual(item['roiBack'], '473,505,409,121')
        self.assertEqual(item['threshold'], 0.8)

    def test_roi_back_covers_click_target(self):
        x, y, w, h = self.RULE.roi_front
        bx, by, bw, bh = self.RULE.roi_back
        self.assertLessEqual(bx, x)
        self.assertLessEqual(by, y)
        self.assertGreaterEqual(bx + bw, x + w)
        self.assertGreaterEqual(by + bh, y + h)

    def test_wanted_quests_still_uses_shared_invite_confirm(self):
        source = inspect.getsource(WantedQuestsTask.invite_random)
        self.assertIn('self.I_INVITE_ENSURE', source)


if __name__ == '__main__':
    unittest.main()
