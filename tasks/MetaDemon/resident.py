"""Post-task friend assistance, with an explicit scheduler handoff."""
import time

from module.exception import GameStuckError, TaskEnd
from module.logger import logger
import tasks.MetaDemon.inner_page as pages


class MetaDemonResident:
    def run_resident(self):
        original_close = self.ui_close
        self._resident_mode = True
        self._resident_summoned_boss = False
        try:
            self.before_run()
            self._resident_loop()
        finally:
            self._restore_navigation()
            self.ui_close = original_close

    def _resident_loop(self):
        guard = getattr(self.device, 'activity_guard', None)
        if guard is not None:
            guard.finish()
        activity = self.config.__dict__.get('meta_demon_resident_activity', lambda active: None)
        activity(False)
        while True:
            # Observation must not prune requests or save configuration.
            self.config.reload()
            self.conf = self.config.meta_demon
            self.config.update_scheduler()
            pending = list(self.config.normal_pending_task)
            if not self.conf.scheduler.enable:
                self.config.__dict__['meta_demon_residency_requested'] = False
                self._resident_return_to_main()
            # Preserve explicit manual priority at a between-battles checkpoint.
            if any(getattr(item, 'manual_request', None) for item in pending):
                self._resident_return_to_main()
            if guard is not None:
                guard.checkpoint()
                # A rest may have reloaded/disabled the task; read again before
                # navigation or clicking a friend card.
                self.conf = self.config.meta_demon
                if not self.conf.scheduler.enable:
                    self.config.__dict__['meta_demon_residency_requested'] = False
                    self._resident_return_to_main()
                self.config.update_scheduler()
                if any(getattr(item, 'manual_request', None)
                       for item in self.config.normal_pending_task):
                    self._resident_return_to_main()
            if not self._enter_boss_page():
                continue
            self.screenshot()
            fatigue, total = self._read_fatigue()
            can_assist = self.conf.meta_demon_config.auto_tea or fatigue < total
            accepted = False
            if can_assist:
                settling = self.appear(self.I_MD_SETTLING)
                friend_settling = settling and (
                    self._friend_active or self._friend_settlement_pending
                    or self._selected_friend_frame(self.device.image) is not None
                    or (self.appear(self.I_MD_FRIEND_OWNER) and not self.appear(self.I_MD_SELF_SELECTED)))
                if settling:
                    self._resident_summoned_boss = False
                if ((self._friend_active or getattr(self, '_resident_summoned_boss', False))
                        and self.appear(self.I_MD_FIRE) and not settling):
                    accepted = True  # Continue the same live encounter/count.
                else:
                    exclude = settling and self._selected_friend_frame(self.device.image) is not None
                    accepted = self._try_friend_boss(exclude_selected=exclude, skip_settling=True)
                if accepted and self._friend_active:
                    self._resident_summoned_boss = False
                self._friend_settlement_pending = False
                if not accepted and friend_settling:
                    logger.info('无其他合格助战鬼王，直接返回自己发现检查门票')
                    activity(True)
                    if guard is not None:
                        guard.start()
                    try:
                        self._return_to_self_discovery()
                        if not getattr(self, '_tickets_checked', False) or self.has_summon_ticket:
                            accepted = self.check_and_switch_ticket(_summon_only=True)
                    finally:
                        if guard is not None:
                            guard.finish()
                        activity(False)
                    self._resident_summoned_boss = bool(accepted)
            if accepted:
                activity(True)
                if guard is not None:
                    guard.start()
                try:
                    self._refresh_current_boss_type(clear_on_failure=True)
                    if (self.cur_boss_type is None or not self.appear(self.I_MD_FIRE)
                            or (self._friend_active and
                                (not self.cur_boss_name or not self.appear(self.I_MD_FRIEND_OWNER)))):
                        raise GameStuckError('超鬼王驻留鬼王身份未确认，禁止挑战')
                    if not self._prioritize_ticket_boss():
                        continue
                    fatigue, total = self._read_fatigue()
                    if not self.conf.meta_demon_config.auto_tea and fatigue >= total:
                        continue
                    if self._select_attack() and self._prepare_lineup() and self.check_and_switch_powerful():
                        self.start_battle()
                        continue
                    # Respect the configured per-boss attack cap. Keep the live
                    # encounter and wait for it to disappear instead of resetting
                    # its count by reselecting the same card.
                finally:
                    if guard is not None:
                        guard.finish()
                    activity(False)
            # Re-read due tasks after scanning/attempting assistance, without
            # selecting or consuming a manual/cooperation request ourselves.
            self.config.update_scheduler()
            if self.config.normal_pending_task:
                self._resident_return_to_main()
            logger.info('超鬼王驻留：等待符合条件的好友鬼王')
            self.device.stuck_record_clear()  # Intentional wait on a known page.
            self.device.click_record_clear()  # Completed scan, not a stuck action.
            time.sleep(5)

    def _resident_return_to_main(self):
        self._restore_navigation()
        if not self.ui_goto_page(pages.page_main):
            raise GameStuckError('超鬼王驻留让出调度前未返回庭院')
        raise TaskEnd
