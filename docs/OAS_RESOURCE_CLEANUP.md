# OAS 未调用资源清理

日期：2026-10-16。本次按用户指定范围清理先前核验的 195 张图片；不删除旧账号切换模块有识别调用的 4 张图片。

## 修改内容

- 删除 195 张图片，分布：SixRealms 114、Component 37、GameUi 25、WeeklyTrifles 14、Chess 4、MemoryScrolls 1。
- 移除 34 个 JSON 文件中的 189 条 imageName 记录。保留其他条目和 JSON 文件；空列表保留为合法 []。
- 移除 CustomCourtyardAffair/assets.py 中 4 个无调用定义及 MemoryScrolls/assets.py 中 I_MS_DOUBLE_SCROLLS_ENTER。CustomCourtyardAffairAssets 空类使用 pass 保持合法导入接口。
- 来源清单保留原始哈希，未改写；本批 195 张图片均未纳入 YYS 来源清单。
- 后续重建资源索引时不应恢复下列已移除的旧 JSON 记录；参考源码同步需尊重本地清理结果。

## 验证

- AST / JSON 语义对比：仅删除目标定义、目标 JSON 条目，空类补 pass。
- 保留的 2417 张图片内容哈希全部不变；195 张目标图片全部已移除。
- 当前来源：920 张仅匹配 YYS、1493 张两仓库共有、4 张仅匹配 OAS。
- 直接缺图资源仍只有 WantedQuests 的 5 个坐标点击定义，没有新增缺图引用。
- 24 项离线 unittest（任务启动、服务启动、配置模板、皮肤资源、滑动兼容）及 pip check 通过。
- 项目协作说明指定的 tests/test_upstream_sync.py、tests/test_port_runtime.py、tests/test_project_update.py 与 dev_tools/verify_port.py 当前不存在，未执行。
- 未连接游戏设备，未验证实际游戏流程。

## 保留的 4 张 OAS 图片

- `tasks/Component/SwitchAccount/res/res_sa_check_select_svr_1.png`
- `tasks/Component/SwitchAccount/res/res_sa_check_select_svr_2.png`
- `tasks/Component/SwitchAccount/res/res_sa_login_form_android.png`
- `tasks/Component/SwitchAccount/res/res_sa_login_form_apple.png`

## 移除的 Python 定义

- `tasks/Component/CustomCourtyardAffair/assets.py`：`I_CHECK_COURTYARD_AFFAIRS_1`、`I_CHECK_IN_DAILY_1`、`I_ENTER_DAILY_1`、`I_ONE_COMPLETE_1`
- `tasks/MemoryScrolls/assets.py`：`I_MS_DOUBLE_SCROLLS_ENTER`

## 清理的 JSON 文件

|文件|移除记录数|
|---|---:|
|`tasks/Component/Costume/main15/image.json`|5|
|`tasks/Component/Costume/main17/image.json`|5|
|`tasks/Component/CostumeBattle/battle12/image.json`|7|
|`tasks/Component/CostumeBattle/battle13/image.json`|7|
|`tasks/Component/CostumeBattle/battle14/image.json`|7|
|`tasks/Component/CustomCourtyardAffair/ca1/image.json`|4|
|`tasks/Component/ReplaceShikigami/rs/supplement.json`|2|
|`tasks/GameUi/page/image_activity.json`|4|
|`tasks/GameUi/page/image_exploration.json`|13|
|`tasks/GameUi/page/image_global.json`|1|
|`tasks/GameUi/page/image_main.json`|4|
|`tasks/GameUi/page/image_town.json`|1|
|`tasks/MemoryScrolls/ms/image.json`|1|
|`tasks/SixRealms/moon_sea/ms/image.json`|18|
|`tasks/SixRealms/moon_sea/ms/image_boss.json`|10|
|`tasks/SixRealms/moon_sea/ms/image_land.json`|5|
|`tasks/SixRealms/moon_sea/ms/image_land_battle.json`|4|
|`tasks/SixRealms/moon_sea/ms/image_land_chaos.json`|2|
|`tasks/SixRealms/moon_sea/ms/image_land_mistery.json`|4|
|`tasks/SixRealms/moon_sea/ms/image_land_star.json`|1|
|`tasks/SixRealms/moon_sea/ms/image_land_store.json`|4|
|`tasks/SixRealms/moon_sea/ms/image_skills.json`|9|
|`tasks/SixRealms/peacock_kingdom/pk/image.json`|9|
|`tasks/SixRealms/peacock_kingdom/pk/image_boss.json`|5|
|`tasks/SixRealms/peacock_kingdom/pk/image_land.json`|5|
|`tasks/SixRealms/peacock_kingdom/pk/image_land_battle.json`|2|
|`tasks/SixRealms/peacock_kingdom/pk/image_land_bloom.json`|1|
|`tasks/SixRealms/peacock_kingdom/pk/image_land_chaos.json`|3|
|`tasks/SixRealms/peacock_kingdom/pk/image_land_mystery.json`|1|
|`tasks/SixRealms/peacock_kingdom/pk/image_land_store.json`|4|
|`tasks/SixRealms/peacock_kingdom/pk/image_skills.json`|10|
|`tasks/SixRealms/sr/image.json`|17|
|`tasks/WeeklyTrifles/broken_amulet/image.json`|4|
|`tasks/WeeklyTrifles/touch_fish/image.json`|10|

## 删除图片清单

- `tasks/Chess/c/c_back_red.png`
- `tasks/Chess/c/c_question_check.png`
- `tasks/Chess/c/c_restart_again.png`
- `tasks/Chess/c/c_reward_chess.png`
- `tasks/Component/Costume/main15/main15_check_main_15.png`
- `tasks/Component/Costume/main15/main15_main_goto_exploration_15.png`
- `tasks/Component/Costume/main15/main15_main_goto_summon_15.png`
- `tasks/Component/Costume/main15/main15_main_goto_town_15.png`
- `tasks/Component/Costume/main15/main15_pet_house_15.png`
- `tasks/Component/Costume/main17/main17_check_main_17.png`
- `tasks/Component/Costume/main17/main17_main_goto_exploration_17.png`
- `tasks/Component/Costume/main17/main17_main_goto_summon_17.png`
- `tasks/Component/Costume/main17/main17_main_goto_town_17.png`
- `tasks/Component/Costume/main17/main17_pet_house_17.png`
- `tasks/Component/CostumeBattle/battle12/battle12_battle_info_12.png`
- `tasks/Component/CostumeBattle/battle12/battle12_de_win_12.png`
- `tasks/Component/CostumeBattle/battle12/battle12_exit_12.png`
- `tasks/Component/CostumeBattle/battle12/battle12_false_12.png`
- `tasks/Component/CostumeBattle/battle12/battle12_friends_12.png`
- `tasks/Component/CostumeBattle/battle12/battle12_local_12.png`
- `tasks/Component/CostumeBattle/battle12/battle12_win_12.png`
- `tasks/Component/CostumeBattle/battle13/battle13_battle_info_13.png`
- `tasks/Component/CostumeBattle/battle13/battle13_de_win_13.png`
- `tasks/Component/CostumeBattle/battle13/battle13_exit_13.png`
- `tasks/Component/CostumeBattle/battle13/battle13_false_13.png`
- `tasks/Component/CostumeBattle/battle13/battle13_friends_13.png`
- `tasks/Component/CostumeBattle/battle13/battle13_local_13.png`
- `tasks/Component/CostumeBattle/battle13/battle13_win_13.png`
- `tasks/Component/CostumeBattle/battle14/battle14_battle_info_14.png`
- `tasks/Component/CostumeBattle/battle14/battle14_de_win_14.png`
- `tasks/Component/CostumeBattle/battle14/battle14_exit_14.png`
- `tasks/Component/CostumeBattle/battle14/battle14_false_14.png`
- `tasks/Component/CostumeBattle/battle14/battle14_friends_14.png`
- `tasks/Component/CostumeBattle/battle14/battle14_local_14.png`
- `tasks/Component/CostumeBattle/battle14/battle14_win_14.png`
- `tasks/Component/CustomCourtyardAffair/ca1/ca1_check_courtyard_affairs_1.png`
- `tasks/Component/CustomCourtyardAffair/ca1/ca1_check_in_daily_1.png`
- `tasks/Component/CustomCourtyardAffair/ca1/ca1_enter_daily_1.png`
- `tasks/Component/CustomCourtyardAffair/ca1/ca1_one_complete_1.png`
- `tasks/Component/ReplaceShikigami/rs/rs_u_circle_alternate.png`
- `tasks/Component/ReplaceShikigami/rs/rs_u_confirm_alternate.png`
- `tasks/GameUi/page/page_activity_signin_close.png`
- `tasks/GameUi/page/page_activity_skip.png`
- `tasks/GameUi/page/page_back_blue.png`
- `tasks/GameUi/page/page_back_yollow.png`
- `tasks/GameUi/page/page_check_activity.png`
- `tasks/GameUi/page/page_check_demon_encounter_2.png`
- `tasks/GameUi/page/page_check_incense_realm.png`
- `tasks/GameUi/page/page_check_lineup_helper.png`
- `tasks/GameUi/page/page_check_main_set.png`
- `tasks/GameUi/page/page_check_mall_recommend.png`
- `tasks/GameUi/page/page_check_mantra_tower.png`
- `tasks/GameUi/page/page_check_moon_sea.png`
- `tasks/GameUi/page/page_check_peacock_kingdom.png`
- `tasks/GameUi/page/page_check_pure_buddha_realm.png`
- `tasks/GameUi/page/page_check_seasonrift_forest.png`
- `tasks/GameUi/page/page_check_shrin.png`
- `tasks/GameUi/page/page_exploration_to_incense_realm.png`
- `tasks/GameUi/page/page_exploration_to_mantra_tower.png`
- `tasks/GameUi/page/page_exploration_to_moon_sea.png`
- `tasks/GameUi/page/page_exploration_to_peacock_kingdom.png`
- `tasks/GameUi/page/page_exploration_to_pure_buddha_realm.png`
- `tasks/GameUi/page/page_exploration_to_seasonrift_forest.png`
- `tasks/GameUi/page/page_guild_to_shrin.png`
- `tasks/GameUi/page/page_main_goto_activity.png`
- `tasks/GameUi/page/page_realm_raid_goto_shikigami_records.png`
- `tasks/MemoryScrolls/ms/ms_ms_double_scrolls_enter.png`
- `tasks/SixRealms/moon_sea/ms/ms_battle_common.png`
- `tasks/SixRealms/moon_sea/ms/ms_battle_fire.png`
- `tasks/SixRealms/moon_sea/ms/ms_battle_team_lock.png`
- `tasks/SixRealms/moon_sea/ms/ms_battle_team_unlock.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_battle_again.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_battle_giveup.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_fire.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_fire_prepare.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_get_exp.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_share.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_shutu.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_skip.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_team_lock.png`
- `tasks/SixRealms/moon_sea/ms/ms_boss_team_unlock.png`
- `tasks/SixRealms/moon_sea/ms/ms_chaos_box_exit.png`
- `tasks/SixRealms/moon_sea/ms/ms_chaos_elite_flag.png`
- `tasks/SixRealms/moon_sea/ms/ms_coin.png`
- `tasks/SixRealms/moon_sea/ms/ms_exit_sixrealms.png`
- `tasks/SixRealms/moon_sea/ms/ms_m_store.png`
- `tasks/SixRealms/moon_sea/ms/ms_m_store_activity.png`
- `tasks/SixRealms/moon_sea/ms/ms_mconinue.png`
- `tasks/SixRealms/moon_sea/ms/ms_mfirst_skill.png`
- `tasks/SixRealms/moon_sea/ms/ms_mistery_coin_right_top.png`
- `tasks/SixRealms/moon_sea/ms/ms_mistery_imitate.png`
- `tasks/SixRealms/moon_sea/ms/ms_mistery_imitate_skill_101.png`
- `tasks/SixRealms/moon_sea/ms/ms_mistery_imitate_success.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_check_exit_prepare.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_check_main.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_check_map.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_check_open_store.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_land_chaos.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_land_fire.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_land_mystery.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_land_shop.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_land_star.png`
- `tasks/SixRealms/moon_sea/ms/ms_ms_skill_unlock.png`
- `tasks/SixRealms/moon_sea/ms/ms_mshouzu.png`
- `tasks/SixRealms/moon_sea/ms/ms_mshouzu_select.png`
- `tasks/SixRealms/moon_sea/ms/ms_mskip.png`
- `tasks/SixRealms/moon_sea/ms/ms_mstart.png`
- `tasks/SixRealms/moon_sea/ms/ms_mstart_check.png`
- `tasks/SixRealms/moon_sea/ms/ms_mstart_confirm.png`
- `tasks/SixRealms/moon_sea/ms/ms_mstart_confirm2.png`
- `tasks/SixRealms/moon_sea/ms/ms_mstart_uncheck.png`
- `tasks/SixRealms/moon_sea/ms/ms_select_0.png`
- `tasks/SixRealms/moon_sea/ms/ms_select_1.png`
- `tasks/SixRealms/moon_sea/ms/ms_select_2.png`
- `tasks/SixRealms/moon_sea/ms/ms_select_3.png`
- `tasks/SixRealms/moon_sea/ms/ms_skill101.png`
- `tasks/SixRealms/moon_sea/ms/ms_skill102.png`
- `tasks/SixRealms/moon_sea/ms/ms_skill105.png`
- `tasks/SixRealms/moon_sea/ms/ms_skill_refresh.png`
- `tasks/SixRealms/moon_sea/ms/ms_star_danger.png`
- `tasks/SixRealms/moon_sea/ms/ms_store_exit.png`
- `tasks/SixRealms/moon_sea/ms/ms_store_refresh.png`
- `tasks/SixRealms/moon_sea/ms/ms_store_skill_101.png`
- `tasks/SixRealms/moon_sea/ms/ms_store_stable_flag.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_kp_boss_share.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_battle_common.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_battle_fire.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_battle_thunder.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_bloom_exit.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_boss_fire.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_boss_lock.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_boss_prepare.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_boss_unlock.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_chaos_box.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_chaos_elite_flag.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_chaos_exit.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_check_main.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_check_map.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_continue.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_exit_main.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_land_bloom.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_land_chaos.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_land_fire.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_land_mystery.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_land_store.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_mystery_imitate.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_select_0.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_select_1.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_select_2.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_select_3.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_select_4.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_skill_charm.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_skill_power.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_skill_refresh.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_skill_roaring_thunder.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_skill_strange_power.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_start.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_start_confirm.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_start_confirm2.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_start_third_skill.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_store_exit.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_store_refresh.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_store_skill_thunder.png`
- `tasks/SixRealms/peacock_kingdom/pk/pk_pk_store_stable_flag.png`
- `tasks/SixRealms/sr/sr_sr_check_buy_box.png`
- `tasks/SixRealms/sr/sr_sr_double_reward_cancel.png`
- `tasks/SixRealms/sr/sr_sr_double_reward_use.png`
- `tasks/SixRealms/sr/sr_sr_incense_realm_info.png`
- `tasks/SixRealms/sr/sr_sr_mantra_tower_info.png`
- `tasks/SixRealms/sr/sr_sr_moon_sea_info.png`
- `tasks/SixRealms/sr/sr_sr_not_tip.png`
- `tasks/SixRealms/sr/sr_sr_peacock_kingdom_info.png`
- `tasks/SixRealms/sr/sr_sr_pure_buddha_realm_info.png`
- `tasks/SixRealms/sr/sr_sr_seasonrift_forest_info.png`
- `tasks/SixRealms/sr/sr_sr_switch.png`
- `tasks/SixRealms/sr/sr_sr_to_incense_realm.png`
- `tasks/SixRealms/sr/sr_sr_to_mantra_tower.png`
- `tasks/SixRealms/sr/sr_sr_to_moon_sea.png`
- `tasks/SixRealms/sr/sr_sr_to_peacock_kingdom.png`
- `tasks/SixRealms/sr/sr_sr_to_pure_buddha_realm.png`
- `tasks/SixRealms/sr/sr_sr_to_seasonrift_forest.png`
- `tasks/WeeklyTrifles/broken_amulet/broken_amulet_bm_again.png`
- `tasks/WeeklyTrifles/broken_amulet/broken_amulet_bm_confirm.png`
- `tasks/WeeklyTrifles/broken_amulet/broken_amulet_bm_enter.png`
- `tasks/WeeklyTrifles/broken_amulet/broken_amulet_bmt_check.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_check_touch_fish.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_guild_goto_tf.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_fold_window.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_happy_get.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_last_save.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_open_fold_window.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_save_all.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_tf_confirm.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_tf_goto_main.png`
- `tasks/WeeklyTrifles/touch_fish/touch_fish_wt_tf_save_success.png`
