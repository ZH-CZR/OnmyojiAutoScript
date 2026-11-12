# This Python file uses the following encoding: utf-8
"""批次 42 上游修复回归测试。

移植 lgg686/self ``a279ab60`` 中的超鬼王门票刷取任务 ``tasks/MetaDemonTicket``：

1. 4 个模块文件（``config.py`` / ``script_task.py`` / ``ticket_farming.py`` / ``__init__.py``）。
2. 新增结算界面门票 OCR ``GeneralBattleAssets.O_METADEMON_PASS``（``gb/ocr.json`` 同步）。
3. 本地适配：门票 OCR 资产改用 ``MetaDemonAssets.O_MD_TICKET``；去掉本地不支持的
   ``settings_layout`` 与 ``module/config/multi_select.py`` 迁移函数；去掉本地不存在的
   协同运行时（``cooperation_runtime``）与探索 ``activate_realm_raid`` 钩子。
4. 注册到 ``ConfigModel.meta_demon_ticket`` 与 Activity Task 菜单。
"""
import json
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from module.config.config_menu import ConfigMenu
from module.config.config_model import ConfigModel
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.MetaDemon.assets import MetaDemonAssets
from tasks.MetaDemonTicket import ticket_farming as tf
from tasks.MetaDemonTicket.config import (
    ExplorationTarget,
    MetaDemonTicket,
    TicketGeneralConfig,
    TicketMode,
)
from tasks.Exploration.config import AutoRotate, ExplorationLevel, UpType, UserStatus
from tasks.EvoZone.config import KirinType, Layer, UserStatus as AwakeUserStatus


def _load_json(path) -> list:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _ocr_entries(path) -> dict:
    return {entry['itemName']: entry for entry in _load_json(path)}


class _FakeDigitCounter:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def ocr_digit_counter(self, image):
        self.calls += 1
        return self.value


class _FakeRewardTask:
    def __init__(self, reward_appear: bool):
        self.reward_appear = reward_appear
        self.device = SimpleNamespace(image='image')

    def appear(self, rule):
        return self.reward_appear


class _FakePage:
    def __init__(self):
        self.on_enter_success = []


class _FakeNavigator:
    def __init__(self, page):
        self.page = page

    def resolve_page(self, page):
        return self.page


# ------------------------------------------------------------ 配置默认值


class TicketConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = MetaDemonTicket()
        general = config.general_config
        self.assertEqual(general.mode, TicketMode.AWAKE)
        self.assertEqual(general.user_status, UserStatus.ALONE)
        self.assertEqual(general.awake_kirin_type, KirinType.LIGHTNINGKIRIN)
        self.assertEqual(general.awake_layer, Layer.SEVEN)
        self.assertFalse(general.exploration_rotate)
        self.assertFalse(general.awake_buff_enable)
        self.assertEqual(general.exploration_target, ExplorationTarget.ALL)
        self.assertEqual(general.limit_time_v, timedelta(minutes=45))

    def test_sections_present(self):
        config = MetaDemonTicket()
        for name in ('scheduler', 'general_config', 'invite_config',
                     'switch_soul_config', 'general_battle_config'):
            self.assertTrue(hasattr(config, name), name)

    def test_mode_values(self):
        self.assertEqual(TicketMode.AWAKE.value, '门票刷取：觉醒')
        self.assertEqual(TicketMode.EXPLORATION.value, '门票刷取：探索')
        self.assertEqual(ExplorationTarget.DARUMA.value, '达摩')


class TicketRegistrationTests(unittest.TestCase):
    def test_config_model_field(self):
        self.assertIn('meta_demon_ticket', ConfigModel.model_fields)

    def test_activity_menu(self):
        menu = ConfigMenu()
        self.assertIn('MetaDemonTicket', menu.menu['Activity Task'])

    def test_task_files_exist(self):
        for name in ('__init__.py', 'config.py', 'script_task.py', 'ticket_farming.py'):
            self.assertTrue(Path(f'tasks/MetaDemonTicket/{name}').exists(), name)


# ------------------------------------------------------------ 资产映射


class TicketAssetTests(unittest.TestCase):
    def test_reward_pass_asset(self):
        # 批次 43（上游 209f8fad4）重新校准了超鬼王门票 OCR 区域。
        rule = GeneralBattleAssets.O_METADEMON_PASS
        self.assertEqual(tuple(rule.roi), (1119, 7, 114, 32))
        self.assertEqual(rule.mode.name, 'DIGITCOUNTER')

    def test_reward_pass_ocr_json(self):
        entry = _ocr_entries('tasks/Component/GeneralBattle/gb/ocr.json')['metademon_pass']
        self.assertEqual(entry['roiFront'], '1119,7,114,32')
        self.assertEqual(entry['roiBack'], '1119,7,114,32')
        self.assertEqual(entry['mode'], 'DigitCounter')

    def test_local_ticket_asset_reused(self):
        rule = MetaDemonAssets.O_MD_TICKET
        self.assertEqual(tuple(rule.roi), (923, 18, 82, 30))
        self.assertEqual(rule.mode.name, 'DIGITCOUNTER')

    def test_source_uses_local_ticket_asset(self):
        source = Path('tasks/MetaDemonTicket/ticket_farming.py').read_text(encoding='utf-8')
        self.assertIn('O_MD_TICKET', source)
        self.assertNotIn('O_METADEMON_PASS_EXP', source)


# ------------------------------------------------------------ 配置适配


class TicketFarmingConfigTests(unittest.TestCase):
    def _meta(self, **general):
        meta = MetaDemonTicket()
        meta.general_config = TicketGeneralConfig(**general)
        return meta

    def test_awake_config(self):
        meta = self._meta(mode=TicketMode.AWAKE, user_status=UserStatus.LEADER,
                          awake_layer=Layer.TEN, awake_kirin_type=KirinType.FIREKIRIN,
                          awake_buff_enable=True)
        config = tf.ticket_farming_config(meta, TicketMode.AWAKE)
        self.assertEqual(config.evo_zone_config.user_status, AwakeUserStatus.LEADER)
        self.assertEqual(config.evo_zone_config.layer, Layer.TEN)
        self.assertEqual(config.evo_zone_config.kirin_type, KirinType.FIREKIRIN)
        self.assertEqual(config.evo_zone_config.limit_count, 2 ** 31 - 1)
        self.assertTrue(config.evo_zone_config.soul_buff_enable)
        self.assertIs(config.invite_config, meta.invite_config)
        self.assertIs(config.general_battle_config, meta.general_battle_config)

    def test_exploration_config_targets(self):
        targets = {
            ExplorationTarget.ALL: UpType.ALL,
            ExplorationTarget.COIN: UpType.COIN,
            ExplorationTarget.EXP: UpType.EXP,
            ExplorationTarget.DARUMA: UpType.DARUMAA,
        }
        for target, expected in targets.items():
            meta = self._meta(exploration_target=target)
            config = tf.ticket_farming_config(meta, TicketMode.EXPLORATION)
            exploration = config.exploration_config
            self.assertEqual(exploration.up_type, expected)
            self.assertEqual(exploration.exploration_level, ExplorationLevel.EXPLORATION_28)
            self.assertEqual(exploration.minions_cnt, 2 ** 31 - 1)
            self.assertEqual(exploration.auto_rotate, AutoRotate.no)
            self.assertEqual(config.invite_config, meta.invite_config)

    def test_exploration_rotate_disables_lock_team(self):
        meta = self._meta(exploration_rotate=True, user_status=UserStatus.MEMBER)
        meta.general_battle_config = meta.general_battle_config.model_copy(
            update={'lock_team_enable': True})
        config = tf.ticket_farming_config(meta, TicketMode.EXPLORATION)
        self.assertEqual(config.exploration_config.auto_rotate, AutoRotate.yes)
        self.assertFalse(config.general_battle_config.lock_team_enable)
        self.assertTrue(meta.general_battle_config.lock_team_enable, '原配置不应被修改')

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            tf.ticket_farming_config(MetaDemonTicket(), 'unknown')


class TicketConfigProxyTests(unittest.TestCase):
    def test_proxy_overrides_only_target_attribute(self):
        real = MetaDemonTicket()
        payload = tf.ticket_farming_config(real, TicketMode.AWAKE)
        proxy = tf.TicketConfigProxy(real, 'evo_zone', payload)
        self.assertIs(proxy.evo_zone, payload)
        self.assertIs(proxy.general_config, real.general_config)
        self.assertIs(proxy.invite_config, real.invite_config)


# ------------------------------------------------------------ 满票判定


class TicketFullDetectTests(unittest.TestCase):
    def _run(self, reward, value):
        ocr = _FakeDigitCounter(value)
        task = _FakeRewardTask(reward)
        with mock.patch.object(GeneralBattleAssets, 'O_METADEMON_PASS', ocr):
            result = tf.metademon_tickets_full(task)
        return result, ocr

    def test_skip_without_reward_screen(self):
        result, ocr = self._run(False, (5, 0, 5))
        self.assertFalse(result)
        self.assertEqual(ocr.calls, 0, '非奖励页不应触发 OCR')

    def test_partial_tickets_not_full(self):
        result, ocr = self._run(True, (3, 2, 5))
        self.assertFalse(result)
        self.assertEqual(ocr.calls, 1)

    def test_full_tickets(self):
        result, _ = self._run(True, (5, 0, 5))
        self.assertTrue(result)

    def test_invalid_total_not_full(self):
        result, _ = self._run(True, (0, 0, 0))
        self.assertFalse(result)


class TicketRewardMixinTests(unittest.TestCase):
    def test_raises_when_full(self):
        task = SimpleNamespace()
        with mock.patch.object(tf, 'metademon_tickets_full', return_value=True):
            with self.assertRaises(tf.TicketsFull):
                tf.TicketRewardMixin.check_ticket_reward(task)

    def test_ignores_after_farming_complete(self):
        task = SimpleNamespace(_ticket_farming_complete=True)
        with mock.patch.object(tf, 'metademon_tickets_full', return_value=True):
            self.assertIsNone(tf.TicketRewardMixin.check_ticket_reward(task))

    def test_install_reward_hook(self):
        page = _FakePage()
        called = []
        task = SimpleNamespace(navigator=_FakeNavigator(page),
                               check_ticket_reward=lambda: called.append(1))
        tf.TicketRewardMixin.install_ticket_reward_hook(task)
        self.assertEqual(len(page.on_enter_success), 1)
        page.on_enter_success[0](task)
        self.assertEqual(called, [1])


if __name__ == '__main__':
    unittest.main()
