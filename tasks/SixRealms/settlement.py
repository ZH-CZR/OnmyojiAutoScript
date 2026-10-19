"""Whole-run settlement shared by Jiaotu and Jue, never island checkpoints."""
from enum import Enum
from time import monotonic, sleep

from module.exception import GameStuckError


class RoundResult(Enum):
    NOT_STARTED = 'not_started'
    NO_TICKETS = 'no_tickets'
    FINISHED = 'finished'  # A whole run ended; this does not imply a victory.
    FAILED = 'failed_settled'


class SixRealmsSettlement:
    round_result = RoundResult.NOT_STARTED

    @property
    def idle_active(self):
        execution = self.config.__dict__.get('idle_execution')
        return execution is not None and execution.key == 'six_realms'

    def finish_round(self, buttons, result):
        if self.idle_active:
            if not self.ui_click(buttons, stop=self.I_MSTART, timeout=15):
                raise GameStuckError('六道整局结算后未返回准备页')
            self.confirm_idle_ready()
        else:
            # Preserve the timed task's original interaction and boolean contract.
            self.ui_click(buttons, stop=self.I_MSTART)
        self.round_result = result
        return True

    def confirm_idle_ready(self):
        """Drain late rewards and require a stable ready screen on fresh frames."""
        deadline, stable_since = monotonic() + 15, None
        close_buttons = [getattr(self, name, None) for name in (
            'I_BOSS_GET_EXP', 'I_BOSS_OVER', 'I_BOSS_SHUTU', 'I_BOSS_SHUTU_2')]
        close_buttons = [button for button in close_buttons if button is not None]
        while monotonic() < deadline:
            self.screenshot()
            if self.appear(self.I_UI_REWARD, threshold=.6):
                self.ui_reward_appear_click()
                stable_since = None
            elif any(self.appear(button) for button in close_buttons):
                for button in close_buttons:
                    if self.appear_then_click(button, interval=.5):
                        break
                stable_since = None
            elif self.appear(self.I_MSTART):
                if stable_since is None:
                    stable_since = monotonic()
                elif monotonic() - stable_since >= 1:
                    return True
            else:
                stable_since = None
            sleep(.3)
        raise GameStuckError('六道奖励未处理完或准备页未稳定出现')
