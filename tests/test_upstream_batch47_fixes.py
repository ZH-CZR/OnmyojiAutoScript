# This Python file uses the following encoding: utf-8
"""批次 47 上游修复回归测试（仅 nearaura/dev 窗口）。

``13221d2c`` fix(CollectiveMissions)：捐赠后领奖与超时
- 领奖循环超时由 3s 固定改为 5s，且每领到一次奖励就重置计时（双倍奖励不再被截断）；
- 捐赠流程额外点击 ``I_CM_REWARDS``（赠送按钮消失后出现的奖励入口）；
- 上游 ``click_cnt == 8 → click_record_clear()`` 不移植：本地已在每次切换任务点击后清理点击记录。
"""
import unittest
from pathlib import Path

from tasks.CollectiveMissions.assets import CollectiveMissionsAssets
from tasks.CollectiveMissions.script_task import ScriptTask


ROOT = Path(__file__).resolve().parents[1]


class _RewardStub:
    """仅实现 get_reward_and_close 依赖的接口。"""

    def __init__(self, reward_times):
        self.reward_pending = reward_times
        self.close_calls = 0
        self.target_clicks = 0

    def screenshot(self):
        pass

    def ui_reward_appear_click(self, click):
        if click:
            self.close_calls += 1
            return False
        if self.reward_pending > 0:
            self.reward_pending -= 1
            return True
        return False

    def appear_then_click(self, asset, interval=1):
        self.target_clicks += 1
        return False


class DonateRewardTests(unittest.TestCase):
    def test_double_reward_claimed_then_final_close(self):
        stub = _RewardStub(reward_times=2)
        ScriptTask.get_reward_and_close(
            stub, CollectiveMissionsAssets.I_CM_PRESENT,
            extra_target=CollectiveMissionsAssets.I_CM_REWARDS,
        )
        self.assertEqual(stub.reward_pending, 0)
        self.assertEqual(stub.close_calls, 1)
        self.assertEqual(stub.target_clicks, 0, '奖励弹窗期间不应点击赠送/奖励按钮')

    def test_timeout_is_five_seconds(self):
        src = (ROOT / 'tasks' / 'CollectiveMissions' / 'script_task.py').read_text(encoding='utf-8')
        self.assertIn('Timer(5).start()', src)

    def test_donate_passes_rewards_entry(self):
        src = (ROOT / 'tasks' / 'CollectiveMissions' / 'script_task.py').read_text(encoding='utf-8')
        self.assertIn('get_reward_and_close(self.I_CM_PRESENT, extra_target=self.I_CM_REWARDS)', src)


if __name__ == '__main__':
    unittest.main()
