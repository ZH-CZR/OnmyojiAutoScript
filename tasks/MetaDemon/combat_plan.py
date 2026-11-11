"""Per-run lineup cache and bounded, per-encounter attack progression."""
import copy
import time
from module.exception import GameStuckError
from module.logger import logger
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig, GreenMarkType
from tasks.MetaDemon.lineups import BossAttack
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
import tasks.MetaDemon.inner_page as pages


class MetaDemonCombatPlan:
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
                powerful=self.cur_boss_type in self.conf.meta_demon_config.powerful_list_v)
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
            if changed:
                self._switch_lineup_souls(*pair)
            if cfg.preset_enable and (changed or getattr(self, '_last_preset_lineup', None) != pair):
                self._applied_preset = None
                if not self._apply_preset_team(*pair):
                    raise GameStuckError('超鬼王预设应用未确认')
                self._last_preset_lineup = pair
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
        return GeneralBattleConfig(green_enable=bool(attack and attack.mark_main),
                                   green_mark=GreenMarkType.GREEN_MAIN)
