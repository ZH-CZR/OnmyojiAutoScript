"""Idle goals, durable weekly coin inhibition, and whole-game checkpoints."""
from datetime import datetime, timedelta
import time

from module.exception import GameStuckError
from module.config.idle import WEEKLY
from tasks.GameUi.page import page_chess, page_main


class ChessIdleMixin:
    def _chess_now(self):
        execution = self.config.__dict__.get('idle_execution')
        return execution.now() if execution is not None else datetime.now()

    def _record_chess_coin_week(self):
        now = self._chess_now()
        monday = now.date() - timedelta(days=now.weekday())
        until = datetime.combine(monday + timedelta(days=7), datetime.min.time())
        self.config.idle_store.block('chess', until, '本周鼬乐币已满')

    def _chess_coin_full(self, *, strict=False):
        """Require two fresh full readings; unknown is never equivalent to full."""
        full_frames = 0
        week = None
        for _ in range(3):
            self.screenshot()
            current_week = self.config.idle_store.period(WEEKLY, self._chess_now())
            if current_week != week:
                full_frames, week = 0, current_week
            coin = self._read_coin() if self.appear(self.I_CHECK_CHESS) else None
            if coin is not None:
                if coin['current'] != 600 or coin['total'] != 600:
                    return False
                full_frames += 1
                if full_frames >= 2:
                    return True
            else:
                full_frames = 0
            time.sleep(.35)
        return None if strict else False

    def _confirm_chess_idle_lobby(self):
        deadline, stable = time.monotonic() + 15, None
        while time.monotonic() < deadline:
            self.screenshot()
            if self.appear(self.I_UI_REWARD, threshold=.6):
                self.ui_reward_appear_click()
                stable = None
            elif self.appear(self.I_CHECK_CHESS):
                if stable is None:
                    stable = time.monotonic()
                elif time.monotonic() - stable >= 1:
                    return
            else:
                stable = None
            time.sleep(.3)
        raise GameStuckError('Chess: 奖励未处理完或大厅未稳定出现')

    def _chess_idle_checkpoint(self):
        execution = self.config.__dict__['idle_execution']
        execution.refresh_config()
        settings = self.config.chess.chess_config
        check_coin = execution.scope == WEEKLY or settings.coin_full_exit
        full = check_coin and self._chess_coin_full(strict=True)
        if full is None:
            execution.yield_task(self, '鼬乐币识别失败，保留进度后重试', retry_seconds=60)
        if full:
            self._record_chess_coin_week()
        self.idle_checkpoint(goal_complete=bool(full))

    def run_chess_idle(self):
        execution = self.config.__dict__['idle_execution']
        self.select_lineup_strategy(self.config.chess.chess_config.lineup_bond)
        # Recovery exits are not completed games or outstanding protection exits.
        self._recover_interrupted_chess_game()
        if not self.ui_goto_page(page_chess):
            raise GameStuckError('Chess: 闲时任务未进入大厅')
        self._confirm_chess_idle_lobby()
        self._chess_idle_checkpoint()

        while True:
            settings = self.config.chess.chess_config
            debt = int(execution.store.read_task_state('chess').get('rank_exits', 0))
            self._rank_protection_exit_requested = bool(settings.rank_protection and debt > 0)
            self._rank_protection_exit_succeeded = False
            self._idle_chess_game_settled = False
            rank = self.run_one_game()
            self._confirm_chess_idle_lobby()
            if self._rank_protection_exit_requested:
                if not self._rank_protection_exit_succeeded:
                    raise GameStuckError('Chess: 保段位退出未确认，不能计数')
                execution.store.update_task_state('chess', rank_exits=max(0, debt - 1))
                completed = 0
            else:
                if not self._idle_chess_game_settled:
                    raise GameStuckError('Chess: 整局结算未确认，不能计数')
                debt = 3 if settings.rank_protection and rank is not None and 1 <= rank <= 4 else 0
                if settings.rank_protection:
                    execution.store.update_task_state('chess', rank_exits=debt)
                completed = 1
            # Commit a verified game's count before a potentially failing OCR.
            execution.record(completed)
            self._chess_idle_checkpoint()

    def idle_return_to_main(self):
        if not self.ui_goto_page(page_main, confirm_wait=.5, skip_first_screenshot=False):
            raise GameStuckError('Chess: 闲时任务返回庭院失败')
        self.screenshot()
        if not self.ui_page_appear(page_main):
            raise GameStuckError('Chess: 尚未确认返回庭院')
