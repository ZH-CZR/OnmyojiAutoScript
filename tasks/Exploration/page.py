from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Exploration.assets import ExplorationAssets
from tasks.GameUi.page import (all_of, any_of, page_battle, page_battle_prepare, page_battle_team, page_exploration,
                               page_main, page_shikigami_records, page_reward, page_battle_team_exit, random_click, page_battle_result)
from tasks.GameUi.page_definition import Page
from tasks.GlobalGame.assets import GlobalGameAssets

# 探索副本入口
page_exp_entrance = Page(ExplorationAssets.I_E_EXPLORATION_CLICK)
page_exp_entrance.connect(page_exploration, GlobalGameAssets.I_UI_BACK_YELLOW, key="page_exp_entrance->page_exploration")
page_exploration.connect(page_exp_entrance, action=lambda task: task.open_expect_level,
                         key="page_exploration->page_exp_entrance")

# 探索退出弹窗
page_exp_exit = Page(all_of(ExplorationAssets.I_E_CHECK_EXIT,
                            ExplorationAssets.I_E_EXIT_CONFIRM, ExplorationAssets.I_E_EXIT_CANCEL), priority=88)
page_exp_exit.connect(page_exp_entrance, ExplorationAssets.I_E_EXIT_CONFIRM, key="page_exp_exit->page_exp_entrance")

# 探索副本主界面
# priority=60：副本地图里 page_exploration（GameUi 共享页，优先级 50）的锚点可能同时命中，
# 同级时按注册顺序 page_exploration 会压过本页，导航于是把「选关」动作当成本页的动作反复执行。
page_exp_main = Page(any_of(ExplorationAssets.I_E_SETTINGS_BUTTON, ExplorationAssets.I_E_AUTO_ROTATE_ON,
                            ExplorationAssets.I_E_AUTO_ROTATE_OFF), priority=60)
page_exp_main.connect(page_exp_exit, GlobalGameAssets.I_UI_BACK_YELLOW, key="page_exp_main->page_exp_exit")
page_exp_entrance.connect(page_exp_main, ExplorationAssets.I_E_EXPLORATION_CLICK, key="page_exp_entrance->page_exp_main")
page_exp_exit.connect(page_exp_main, ExplorationAssets.I_E_EXIT_CANCEL, key="page_exp_exit->page_exp_main")

# 探索设置界面
page_exp_settings = Page(ExplorationAssets.I_E_OPEN_SETTINGS, priority=75)
page_exp_settings.connect(page_exp_main, ExplorationAssets.I_E_SURE_BUTTON, key="page_exp_settings->page_exp_main")
page_exp_main.connect(page_exp_settings, ExplorationAssets.C_CLICK_SETTINGS, key="page_exp_main->page_exp_settings")
