# This Python file uses the following encoding: utf-8
"""RichMan 断点续跑、神龛确认购买、海汐拉满移植回归测试。

来源：MaoGi1201/OnmyojiAutoScript ``fix`` 分支
- ``96d9951c`` feat(RichMan): 增加断点续跑，报错重跑从已完成步骤继续
- ``6cbb197e`` fix(RichMan): 神龛购买流程改为确认即购买
- ``2e54b409`` fix(RichMan): 神龛四星达摩按余额买一个或拉满
- ``439419a3`` fix(RichMan): 海汐御魂购买不再按十个切轮，直接拉满

覆盖点：
- 进度按 ISO 周记录，同周跳过、跨周清空；
- 步骤执行异常时不落盘，重跑从失败步骤继续；
- RichMan 主流程五个步骤（含本地独有的鼬乐币商店）都走 ``run_step``；
- 神龛改用「点达摩 → 确认达摩 → 确认购买」，不再引用已删除的 ``I_S_BUY_*`` 素材；
- 四星达摩按余额判定买一个或拉满；
- 海汐非自动模式一次拉满，不再按十个切轮。
"""
import json
import unittest
from datetime import datetime
from pathlib import Path

from tasks.RichMan.config import RichMan
from tasks.RichMan.progress import RichManProgress


ROOT = Path(__file__).resolve().parents[1]


def _current_week() -> str:
    year, week, _ = datetime.now().isocalendar()
    return f'{year}-W{week:02d}'


class _SavedParams:
    def __init__(self, save_week: str = '', done: str = ''):
        self.save_week = save_week
        self.done = done


class _RichManConfig:
    def __init__(self, saved_params: _SavedParams):
        self.saved_params = saved_params


class _Config:
    def __init__(self, saved_params: _SavedParams):
        self.rich_man = _RichManConfig(saved_params)
        self.save_count = 0

    def save(self):
        self.save_count += 1


class _Task(RichManProgress):
    def __init__(self, config: _Config):
        self.config = config


class RichManProgressTests(unittest.TestCase):
    def test_mark_and_skip_in_same_week(self):
        config = _Config(_SavedParams(save_week=_current_week()))
        task = _Task(config)
        self.assertFalse(task.is_step_done('shrine'))
        task.mark_step_done('shrine')
        self.assertEqual(config.rich_man.saved_params.done, 'shrine')

        # 模拟重启后重新加载同一份配置
        reloaded = _Task(config)
        self.assertTrue(reloaded.is_step_done('shrine'))
        self.assertEqual(config.rich_man.saved_params.save_week, _current_week())

    def test_week_changed_clears_progress(self):
        config = _Config(_SavedParams(save_week='2020-W01', done='shrine,mall'))
        task = _Task(config)
        self.assertFalse(task.is_step_done('shrine'))
        self.assertEqual(config.rich_man.saved_params.done, '')
        self.assertEqual(config.rich_man.saved_params.save_week, _current_week())
        self.assertGreaterEqual(config.save_count, 1)

    def test_run_step_records_only_on_success(self):
        config = _Config(_SavedParams(save_week=_current_week()))
        task = _Task(config)
        executed = []

        def boom():
            raise RuntimeError('card dead')

        with self.assertRaises(RuntimeError):
            task.run_step('guild_store', boom)
        self.assertFalse(task.is_step_done('guild_store'))

        task.run_step('mall', lambda: executed.append('mall'))
        self.assertEqual(executed, ['mall'])
        self.assertTrue(task.is_step_done('mall'))

        # 已完成的步骤不再执行
        task.run_step('mall', lambda: executed.append('mall again'))
        self.assertEqual(executed, ['mall'])


class RichManSourceTests(unittest.TestCase):
    def test_script_task_steps_use_run_step(self):
        source = (ROOT / 'tasks' / 'RichMan' / 'script_task.py').read_text(encoding='utf-8')
        for step in ('thousand_things', 'shrine', 'guild_store', 'itachi_coin_shop', 'mall'):
            self.assertIn(f"run_step('{step}'", source)
        self.assertIn('self.init_progress()', source)

    def test_shrine_confirm_only(self):
        source = (ROOT / 'tasks' / 'RichMan' / 'shrine.py').read_text(encoding='utf-8')
        assets = (ROOT / 'tasks' / 'RichMan' / 'assets.py').read_text(encoding='utf-8')
        self.assertNotIn('I_S_BUY', source)
        self.assertNotIn('I_S_BUY', assets)
        for name in ('BLACK', 'WHITE_FIVE', 'WHITE_FOUR'):
            self.assertIn(f'self.ui_click(self.I_S_{name}, self.I_S_CHECK_{name})', source)
            self.assertIn(f'self.ui_get_reward(self.I_S_CONFIRM_{name})', source)

    def test_shrine_white_four_money_threshold(self):
        source = (ROOT / 'tasks' / 'RichMan' / 'shrine.py').read_text(encoding='utf-8')
        start = source.index('def shrine_white_four')
        end = source.index('if __name__', start)
        body = source[start:end]
        self.assertIn('self.shrine_check_money(200)', body)
        self.assertIn('self.shrine_check_money(400)', body)
        self.assertIn('self.buy_more(self.I_S_WHITE_FOUR)', body)

    def test_shrine_assets_consistent(self):
        rules = json.loads((ROOT / 'tasks' / 'RichMan' / 'shrine' / 'image.json').read_text(encoding='utf-8'))
        assets = (ROOT / 'tasks' / 'RichMan' / 'assets.py').read_text(encoding='utf-8')
        for rule in rules:
            image = ROOT / 'tasks' / 'RichMan' / 'shrine' / rule['imageName']
            self.assertTrue(image.exists(), f"缺少素材 {rule['imageName']}")
            self.assertIn(f"I_{rule['itemName'].upper()} =", assets)

    def test_scales_sea_buy_max(self):
        source = (ROOT / 'tasks' / 'RichMan' / 'mall' / 'scales.py').read_text(encoding='utf-8')
        start = source.index('def _scales_sea')
        end = source.index('if __name__', start)
        body = source[start:end]
        # 海汐不再按十个切轮（首领御魂的 20 个切轮不在本次范围）
        self.assertNotIn('buy_cycles_number', body)
        self.assertNotIn('buy_res_number', body)
        self.assertIn('self._scales_buy_sea_more(self.I_SCA_PICTURE_BOOK)', body)

    def test_config_and_template_has_saved_params(self):
        self.assertTrue(hasattr(RichMan(), 'saved_params'))
        template = json.loads((ROOT / 'config' / 'template.json').read_text(encoding='utf-8'))
        self.assertIn('saved_params', template['rich_man'])
        self.assertEqual(template['rich_man']['saved_params']['done'], '')

    def test_i18n_has_saved_params_keys(self):
        i18n = json.loads((ROOT / 'assets' / 'i18n' / 'zh-CN.json').read_text(encoding='utf-8'))
        for key in ('save_week', 'save_week_help', 'done', 'done_help'):
            self.assertIn(key, i18n)
            self.assertTrue(i18n[key])


if __name__ == '__main__':
    unittest.main()
