"""Exercise HeroTest selection loops without a Config, Device or running game.

背景：本文件最初按「超时后回退点击默认技能」的设想编写，用 ``Timer`` 桩驱动
循环；但仓库内从未存在对应的 fallback 资产与实现（全部历史分支均无 ``C_BCMJ*``
坐标），现行实现是重构后的**单次选择**：按优先级尝试技能，无论是否命中都点
确认，不进入重试循环，因此天然不存在「无限重试」问题。

这些测试改为守住当前实现真正需要保证的不变量：
1. 技能按优先级顺序尝试，命中即停止；
2. 一个技能都识别不到时仍按一次确认，不重复重试；
3. 技能面板不在时不下发确认点击。
"""

import unittest
from types import SimpleNamespace

from tasks.HeroTest.config import SkillMode
from tasks.HeroTest.script_task import ScriptTask


class ScriptedHeroTest(ScriptTask):
    def __init__(self, *, mode=SkillMode.PVE, panel_visible=True):
        # Skip BaseTask.__init__, which requires a real Config and Device.
        self.conf = SimpleNamespace(herotest=SimpleNamespace(skill_mode=mode))
        self.panel_visible = panel_visible
        self.frames = 0
        self.visible_skills = []
        self.attempted_skills = []
        self.events = []

    def screenshot(self):
        self.frames += 1
        if self.frames > 3:
            raise AssertionError('Skill selection kept retrying instead of confirming once')

    def wait_until_appear(self, button, **kwargs):
        return self.appear(button)

    def appear(self, button, **kwargs):
        return button is self.I_BCMJ_SKILL_ADD_CONFIRM and self.panel_visible

    def appear_then_click(self, button, **kwargs):
        if button is self.I_BCMJ_SKILL_ADD_CONFIRM:
            if not self.panel_visible:
                return False
            self.events.append(('confirm', button))
            self.panel_visible = False
            return True
        self.attempted_skills.append(button)
        if any(button is skill for skill in self.visible_skills):
            self.events.append(('preferred', button))
            return True
        return False

    def click(self, button, **kwargs):
        self.events.append(('click', button))
        return True

    def ui_click_until_disappear(self, button, **kwargs):
        self.appear_then_click(button)


class HeroTestSkillSelectionTests(unittest.TestCase):
    def test_hero1_unrecognized_skills_confirm_once(self):
        task = ScriptedHeroTest()
        self.assertTrue(task.hero1_skill_wait())
        self.assertEqual([event for event, _ in task.events], ['confirm'])
        self.assertEqual(len(task.attempted_skills), 5)
        self.assertEqual(task.frames, 0)

    def test_hero2_unrecognized_skills_confirm_once(self):
        task = ScriptedHeroTest()
        self.assertTrue(task.hero2_skill_wait())
        self.assertEqual([event for event, _ in task.events], ['confirm'])
        self.assertEqual(len(task.attempted_skills), 6)
        self.assertEqual(task.frames, 0)

    def test_empty_hero2_pvp_priority_list_does_not_retry_forever(self):
        task = ScriptedHeroTest(mode=SkillMode.PVP)
        self.assertTrue(task.hero2_skill_wait())
        self.assertEqual([event for event, _ in task.events], ['confirm'])
        self.assertEqual(task.frames, 0)

    def test_hero1_recognized_skills_keep_their_priority(self):
        task = ScriptedHeroTest()
        task.visible_skills = [task.I_BCMJ_SKILL_ADD2, task.I_BCMJ_BLESS]
        self.assertTrue(task.hero1_skill_wait())
        self.assertEqual([event for event, _ in task.events], ['preferred', 'confirm'])
        self.assertIs(task.events[0][1], task.I_BCMJ_SKILL_ADD2)
        self.assertEqual(len(task.attempted_skills), 2)
        self.assertEqual(task.frames, 0)

    def test_hero2_recognized_skills_keep_their_priority(self):
        task = ScriptedHeroTest()
        task.visible_skills = [task.I_HERO2_SKILL2, task.I_HERO2_SKILL3]
        self.assertTrue(task.hero2_skill_wait())
        self.assertEqual([event for event, _ in task.events], ['preferred', 'confirm'])
        self.assertIs(task.events[0][1], task.I_HERO2_SKILL2)
        self.assertEqual(len(task.attempted_skills), 2)
        self.assertEqual(task.frames, 0)

    def test_no_panel_does_not_click(self):
        for method in ('hero1_skill_wait', 'hero2_skill_wait'):
            with self.subTest(method=method):
                task = ScriptedHeroTest(panel_visible=False)
                self.assertFalse(getattr(task, method)())
                self.assertEqual(task.events, [])
                self.assertEqual(task.frames, 0)


if __name__ == '__main__':
    unittest.main()
