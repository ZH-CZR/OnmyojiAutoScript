"""Per-run lineup cache and bounded, per-encounter attack progression."""
import copy
import time
from module.base.timer import Timer
from module.exception import GameStuckError
from module.logger import logger
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig, GreenMarkType
from tasks.MetaDemon.lineups import BossAttack
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
import tasks.MetaDemon.inner_page as pages


class MetaDemonCombatPlan:
    def green_mark(self, enable=False, mark_mode=GreenMarkType.GREEN_MAIN):
        if not enable:
            return
        if mark_mode != GreenMarkType.GREEN_MAIN:
            return self._mark_ally(mark_mode)
        marked = self._mark_main()
        attack = getattr(self, '_active_attack', None)
        if marked and attack and attack.green_enable:
            return self._mark_ally(attack.green_mark)
        return marked

    def _mark_ally(self, mark_mode):
        positions = {
            GreenMarkType.GREEN_LEFT1: self.C_GREEN_LEFT_1,
            GreenMarkType.GREEN_LEFT2: self.C_GREEN_LEFT_2,
            GreenMarkType.GREEN_LEFT3: self.C_GREEN_LEFT_3,
            GreenMarkType.GREEN_LEFT4: self.C_GREEN_LEFT_4,
            GreenMarkType.GREEN_LEFT5: self.C_GREEN_LEFT_5,
        }
        target = positions[mark_mode]
        timeout = Timer(15).start()
        while not timeout.reached():
            self.screenshot()
            if self.is_in_prepare(False):
                continue
            if self.appear(self.I_WIN) or self.appear(self.I_FALSE) or self._boss_page_visible():
                return False
            if self.is_in_battle(False):
                self.click(target)
                logger.info(f'超鬼王绿标队友：{mark_mode.value}')
                return True
        raise GameStuckError('超鬼王绿标队友等待战斗超过15秒')

    def _mark_main(self):
        # MetaDemon marks the boss through its fixed top portrait, rather than
        # the general ally green-mark coordinates. This is a toggle: submit
        # once and observe confirmation instead of cancelling a delayed mark.
        timeout = Timer(15).start()
        clicked = False
        while not timeout.reached():
            self.screenshot()
            if self.is_in_prepare(False):
                continue
            # GeneralBattle.is_in_battle also includes victory/defeat screens.
            if self.appear(self.I_WIN) or self.appear(self.I_FALSE) or self._boss_page_visible():
                logger.info('超鬼王战斗已结束，本场不再标记')
                return False
            if self.is_in_battle(False):
                if self.appear(self.I_MD_MAIN_MARKED):
                    logger.info('超鬼王主怪已标记')
                    return True
                if not clicked:
                    self.click(self.C_MD_MARK_MAIN)
                    clicked = True
                continue
        raise GameStuckError('超鬼王主怪标记超过15秒未确认，禁止重复点击')

    def click(self, click=None, interval=None):
        result = super().click(click, interval)
        if (result or interval is None) and getattr(self, '_tracking_soul_confirmation', False) and (
                click is self.I_UI_SURE or click is self.I_SOU_SWITCH_SURE):
            self._soul_confirmation_clicked = True
        return result

    def appear_then_click(self, target, *args, **kwargs):
        result = super().appear_then_click(target, *args, **kwargs)
        if result and getattr(self, '_tracking_soul_confirmation', False) and (
                target is self.I_UI_SURE or target is self.I_SOU_SWITCH_SURE):
            self._soul_confirmation_clicked = True
        return result

    def screenshot(self, *args, **kwargs):
        deadline = getattr(self, '_lineup_deadline', None)
        if deadline is not None and time.monotonic() >= deadline:
            raise GameStuckError('超鬼王阵容切换超过120秒')
        return super().screenshot(*args, **kwargs)

    def _reset_combat_plan(self):
        self._encounter_attempts = 0
        self._last_lineup = None
        self._last_preset_lineup = None
        self._active_attack = None
        self._lineup_deadline = None

    def _new_encounter(self):
        self._encounter_attempts = 0
        self._active_attack = None

    def _select_attack(self):
        cfg = self.conf.lineup_config
        special = cfg.specific(self.cur_boss_name)
        attempts = getattr(self, '_encounter_attempts', 0)
        if special:
            # Two configured attacks get one final retry with the second setup.
            maximum = 3 if special.attack_count == 2 else 1
            if attempts >= maximum:
                logger.warning('特定鬼王进攻次数已用尽，保留当前鬼王并停止本轮')
                self.State.done = True
                return False
            attack = special.first_attack if attempts == 0 else special.second_attack
            self._active_attack = attack.model_copy(deep=True)
            if not self._active_attack.lineup:
                self._active_attack.lineup = cfg.common_lineup(self.cur_boss_type)
        else:
            self._active_attack = BossAttack(lineup=cfg.common_lineup(self.cur_boss_type),
                powerful=self.cur_boss_type in self.conf.meta_demon_config.powerful_list_v,
                green_enable=cfg.green_enable, green_mark=cfg.green_mark)
        return True

    def _prepare_lineup(self):
        cfg = self.conf.lineup_config
        attack = self._active_attack
        if not cfg.enable or not attack.lineup:
            return True
        if self.cur_boss_type is None:
            raise GameStuckError('鬼王星级未知，禁止猜测阵容')
        pair = tuple(attack.lineup.split(','))
        changed = getattr(self, '_last_lineup', None) != pair
        self._lineup_deadline = time.monotonic() + 120
        try:
            if cfg.preset_enable:
                # Applying the boss-page preset also equips its saved souls.
                if changed or getattr(self, '_last_preset_lineup', None) != pair:
                    SwitchSoul._current_switch_soul = '-'
                    self._applied_preset = None
                    if not self._apply_preset_team(*pair):
                        raise GameStuckError('超鬼王预设及御魂应用未确认')
                    self._last_preset_lineup = pair
            elif changed:
                self._switch_lineup_souls(*pair)
                self._last_preset_lineup = None
            self._last_lineup = pair
            return True
        except Exception:
            self._last_lineup = self._last_preset_lineup = None
            self._applied_preset = None
            raise
        finally:
            self._lineup_deadline = None

    def _switch_lineup_souls(self, group, team):
        # Bypass SwitchSoul's process-global optimistic cache. Only the confirmed
        # task-local cache above can skip a switch in this task.
        SwitchSoul._current_switch_soul = '-'
        if not self.ui_goto_page(pages.page_shikigami_records):
            raise GameStuckError('超鬼王切换阵容未进入式神录')
        rules = {name: self.__dict__.get(name) for name in ('O_SS_GROUP_NAME', 'O_SS_TEAM_NAME')}
        for name in rules:
            setattr(self, name, copy.copy(getattr(self, name)))
        self._tracking_soul_confirmation = True
        self._soul_confirmation_clicked = False
        try:
            self.click_preset()
            if group.isdigit() and team.isdigit():
                self.switch_souls((int(group), int(team)))
            else:
                self.switch_soul_by_name(group, team)
            self.screenshot()
            if not self._soul_confirmation_clicked or self.appear(self.I_UI_SURE) or self.appear(self.I_SOU_SWITCH_SURE):
                raise GameStuckError('超鬼王御魂装配确认未完成，禁止记录已切换')
            if not self.ui_goto_page(pages.page_meta_demon_boss):
                raise GameStuckError('超鬼王切换阵容后未返回挑战页')
        finally:
            self._tracking_soul_confirmation = False
            for name, original in rules.items():
                if original is None:
                    self.__dict__.pop(name, None)
                else:
                    setattr(self, name, original)

    def _attack_battle_config(self):
        attack = getattr(self, '_active_attack', None)
        return GeneralBattleConfig(green_enable=bool(attack and (attack.mark_main or attack.green_enable)),
                                   green_mark=GreenMarkType.GREEN_MAIN if not attack or attack.mark_main or not attack.green_enable
                                   else GreenMarkType(attack.green_mark.value))
