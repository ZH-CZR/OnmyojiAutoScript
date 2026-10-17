# 未引用图片资源清理记录

日期：2026-10-16。基于当前工作区静态资源引用审查，未运行游戏任务。

## 最新状态

继续核验此前保守保留的 OAS 图片后，已删除 195 张当前任务没有读取路径的图片、189 条对应 JSON 记录及 5 个无业务调用的 Python 资源定义。
当前任务图片共 2417 张：920 张仅匹配 YYS、1493 张两仓库共有、4 张仅匹配 OAS；后者属于未接入正常调度的旧账号切换模块，按本次范围保留。
保留图片哈希不变，没有新增缺图定义；现存 5 条缺图定义仍为悬赏封印的坐标点击对象。
24 项离线 unittest 和 `pip check` 通过，未进行游戏实测。详细范围及逐文件删除清单见 [OAS_RESOURCE_CLEANUP.md](OAS_RESOURCE_CLEANUP.md)。

以下“结果”和“判定范围”记录前一轮清理过程；最新状态以上述结果为准。

## 结果

- 清理前任务图片 2956 张，删除 344 张，保留 2612 张。
- 删除图片中，211 张是与清单指定的 OAS 提交同路径同内容、但不匹配 YYS 对应路径的图片；130 张有 YYS 来源记录；另 3 张为未纳入清单的两仓库共有图片。删除按引用判定，不按仓库来源判定。
- 保留图片内容哈希全部与清理前一致。仅匹配 OAS 的图片剩余 199 张。
- 现存 27 条直接 RuleImage 缺失路径引用，清理前后相同，本次没有增加；本次未修复这些既有问题。

## 判定范围

- 检查 tasks、module、dev_tools 中 Python AST 字符串与 RuleImage/RuleImageGrid/RuleGif 的静态 file/path 参数。只要存在资源索引定义便保留，未将“定义存在但业务未调用”视为可删除。
- 保留任务 JSON 的 imageName 引用，避免破坏素材编辑、资源索引再生成。JSON 定义是否实际用于运行不在本次删除判定中。
- 保留引用图片对应的隐式 _mask 蒙版。
- 已审查 MainStory、ActivityCommon、Chess 和 RuleList 的目录加载/拼名规则。保留 ActivityCommon 全目录、MainStory/tmp、Chess 的 shikigami/soul/badge/c 目录，以及 mode=image 的 RuleList 文件夹。
- 按项目约定跳过 Hyakkiyakou；不清理 GUI、OCR 模型、用户配置、日志截图和第三方依赖。
- 动态目录采用保守保留；不声称所有保留文件均在当前任务流程实际使用，也不声称无图形识别兼容问题。

## 来源记录与后续同步

upstream/manifest.json 保留原始参考提交与来源哈希，未将哈希改写为本地删除结果。下列 130 张受来源清单记录的图片属于明确的本地删除；当前同步策略工具缺失，将来恢复上游同步时，应审查此清单并实现对应排除或重新进行引用检查，避免无条件重新导入。

## 验证

- 静态检查：Python/JSON 解析无错误，保留图片哈希不变，无新增直接缺失引用。
- unittest：test_task_startup、test_server_startup、test_config_template、test_costume_assets、test_swipe_compatibility 共 24 项通过。
- pip check：通过。
- AGENTS.md 指定的 tests/test_upstream_sync.py、tests/test_port_runtime.py、tests/test_project_update.py 与 dev_tools/verify_port.py 当前不存在，未执行。
- 未做设备、OCR 或游戏流程实测。

## 删除清单

### 后续：清除缺图遗留定义

2026-10-16 继续追踪原有 27 条缺图定义的业务调用，确认其中 22 条没有直接或已审查的动态调用，已删除对应 `assets.py` 定义及 22 条 JSON 源定义，防止资源索引再生成时恢复。
涉及 AbyssShadows、GeneralBattle、GeneralInvite、Dokan、KekkaiActivation、LBS、MetaDemon、MysteryShop、Restart 和 SixRealms，共修改 10 个资源索引及 11 个 JSON 文件。
悬赏封印的 `I_WQ_FRIEND_1` 至 `I_WQ_FRIEND_5` 保持不变：它们在随机邀请分支作为坐标点击对象使用，不加载 PNG。
当前缺图定义从 27 条减少至上述 5 条；不再将它们统一视为未处理的识别图片缺失。
AST 和 JSON 语义对比确认只删除指定条目，24 项离线 unittest 和 `pip check` 再次通过，未进行游戏实测。
原始来源清单哈希保持不变；后续参考源码同步需保留本节记录的定义删除，避免重新导入。

### 图片文件删除明细

“来源清单记录”指 upstream/manifest.json 中有记录；“仅匹配 OAS”按审查时固定的两个提交分类，不表示最初作者。

|图片路径|来源清单记录|仅匹配 OAS|
|---|---|---|
|`tasks/AbyssShadows/res/abyss_in_shenshe.png`|否|是|
|`tasks/AbyssShadows/res/res_abyss_enemy_fire.png`|否|是|
|`tasks/AbyssShadows/res/res_abyss_enemy_info_exit.png`|否|是|
|`tasks/AbyssShadows/res/res_abyss_quick_loadout_fight.png`|否|是|
|`tasks/AbyssShadows/res/res_btn_start.png`|否|是|
|`tasks/AbyssShadows/res/res_check_abyss.png`|否|是|
|`tasks/AbyssShadows/res/res_check_finish.png`|否|是|
|`tasks/AbyssShadows/res/res_check_shenshe.png`|否|是|
|`tasks/AbyssShadows/res/res_difficulty_easy.png`|否|是|
|`tasks/AbyssShadows/res/res_difficulty_extreme.png`|否|是|
|`tasks/AbyssShadows/res/res_difficulty_hard.png`|否|是|
|`tasks/AbyssShadows/res/res_difficulty_normal.png`|否|是|
|`tasks/AbyssShadows/res/res_ensure_button.png`|是|否|
|`tasks/AbyssShadows/res/res_equipping.png`|否|是|
|`tasks/AbyssShadows/res/res_mark_main.png`|否|是|
|`tasks/AbyssShadows/res/res_open_abyss_shadows_abyss.png`|否|是|
|`tasks/AbyssShadows/res/res_open_quick_loadout.png`|否|是|
|`tasks/AbyssShadows/res/res_select_difficulty.png`|否|是|
|`tasks/AbyssShadows/res/res_start_ensure.png`|否|是|
|`tasks/AbyssShadows/res/res_to_abyss_shadows.png`|是|否|
|`tasks/AreaBoss/res/ab_num_challenge_rail.png`|否|是|
|`tasks/AreaBoss/res/res_ab_close_red.png`|是|否|
|`tasks/AreaBoss/res/res_close_red.png`|是|否|
|`tasks/BondlingFairyland/ball/ball_ball_area.png`|否|是|
|`tasks/BondlingFairyland/ball/ball_check_area.png`|否|是|
|`tasks/BondlingFairyland/ball/ball_create_team.png`|否|是|
|`tasks/BondlingFairyland/ball/room_team.png`|是|否|
|`tasks/BondlingFairyland/bf/bf_bf_local_1_one.png`|是|否|
|`tasks/BondlingFairyland/bf/bf_bf_local_5_little_kuro.png`|是|否|
|`tasks/BondlingFairyland/capture/capture_c_continuous_disable.png`|否|是|
|`tasks/BondlingFairyland/capture/capture_c_continuous_enable.png`|否|是|
|`tasks/BondlingFairyland/capture/capture_c_minimal_mode_disable.png`|否|是|
|`tasks/BondlingFairyland/capture/capture_c_minimal_mode_enable.png`|否|是|
|`tasks/BondlingFairyland/capture/capture_cap_again.png`|否|是|
|`tasks/BondlingFairyland/stone/stone_stone_close.png`|否|是|
|`tasks/CollectiveMissions/cm/cm_cm_close.png`|否|是|
|`tasks/CollectiveMissions/cm/cm_cm_get_reward.png`|否|是|
|`tasks/CollectiveMissions/cm/cm_cm_switch.png`|否|是|
|`tasks/Component/Buy/buy/buy_buy_success.png`|否|是|
|`tasks/Component/Buy/buy/buy_cancel.png`|是|否|
|`tasks/Component/Costume/main1/image_name.png`|是|否|
|`tasks/Component/Costume/main13/main13_harvest_guild_reward_13.png`|否|是|
|`tasks/Component/Costume/main13/main13_harvest_jade_13.png`|否|是|
|`tasks/Component/Costume/main13/main13_harvest_mail_13.png`|否|是|
|`tasks/Component/Costume/main13/main13_harvest_sign_13.png`|否|是|
|`tasks/Component/Costume/main13/main13_harvest_soul_13.png`|否|是|
|`tasks/Component/Costume/main13/main13_wq_done_13.png`|否|是|
|`tasks/Component/Costume/main14/main14_check_main_14.png`|否|是|
|`tasks/Component/Costume/main17/main16_check_main_16.png`|否|是|
|`tasks/Component/Costume/main17/main16_main_goto_exploration_16.png`|否|是|
|`tasks/Component/Costume/main17/main16_main_goto_summon_16.png`|否|是|
|`tasks/Component/Costume/main17/main16_main_goto_town_16.png`|否|是|
|`tasks/Component/Costume/main17/main16_pet_house_16.png`|否|是|
|`tasks/Component/CostumeBattle/battle1/battle1_battle_info_1.png`|否|是|
|`tasks/Component/CostumeBattle/battle10/battle10_battle_info_10.png`|否|是|
|`tasks/Component/CostumeBattle/battle11/battle11_battle_info_11.png`|否|是|
|`tasks/Component/CostumeBattle/battle2/battle2_battle_info_2.png`|否|是|
|`tasks/Component/CostumeBattle/battle3/battle3_battle_info_3.png`|否|是|
|`tasks/Component/CostumeBattle/battle4/battle4_battle_info_4.png`|否|是|
|`tasks/Component/CostumeBattle/battle5/battle5_battle_info_5.png`|否|是|
|`tasks/Component/CostumeBattle/battle6/battle6_battle_info_6.png`|否|是|
|`tasks/Component/CostumeBattle/battle7/battle7_battle_info_7.png`|否|是|
|`tasks/Component/CostumeBattle/battle8/battle8_battle_info_8.png`|否|是|
|`tasks/Component/CostumeBattle/battle9/battle9_battle_info_9.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_battle_state_info.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_confirm.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_confirm_close_diff_soul.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_de_gold.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_disable_7days_diff_soul.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_exit_ensure.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_exit_ensure1.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_gb_check_team_exit.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_gb_close_red.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_gb_skin_confirm.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_green_marker.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_green_marker_bottom.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_green_marker_left_top.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_over_ghost.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_prepare_highlight.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_reward.png`|是|否|
|`tasks/Component/GeneralBattle/gb/gb_reward_particulars.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_reward_particulars_orchi.png`|否|是|
|`tasks/Component/GeneralBattle/gb/gb_statistics.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_add_2.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_add_2_mask.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_buff.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_cancel.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_default_invite.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_default_no.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_gi_sure.png`|是|否|
|`tasks/Component/GeneralInvite/gi/gi_i_accept_apprentice.png`|否|是|
|`tasks/Component/GeneralInvite/gi/gi_i_load.png`|否|是|
|`tasks/Component/GeneralInvite/gi/gi_sure.png`|是|否|
|`tasks/Component/GeneralRoom/gr/gr_gr_back_yellow.png`|是|否|
|`tasks/Component/GeneralRoom/斗町.png`|是|否|
|`tasks/Component/GeneralRoom/连携召唤.png`|是|否|
|`tasks/Component/ReplaceShikigami/rs/rs_detect_empty_1.png`|否|是|
|`tasks/Component/ReplaceShikigami/rs/rs_detect_empty_2.png`|是|否|
|`tasks/Component/ReplaceShikigami/rs/rs_detect_empty_3.png`|是|否|
|`tasks/Component/ReplaceShikigami/rs/rs_detect_empty_4.png`|是|否|
|`tasks/Component/ReplaceShikigami/rs/rs_detect_empty_5.png`|是|否|
|`tasks/Component/ReplaceShikigami/rs/rs_detect_empty_6.png`|是|否|
|`tasks/Component/ReplaceShikigami/rs/rs_rs_all_selected.png`|否|是|
|`tasks/Component/SwitchAccount/res/sa_.png`|否|否|
|`tasks/Component/SwitchAccount/res/sa_account_drop_down_opened.png`|否|否|
|`tasks/Component/SwitchAccount/res/sa_check_select_svr.png`|否|否|
|`tasks/Component/SwitchAccount/res/sa_login_form_android.png`|否|是|
|`tasks/Component/SwitchAccount/res/sa_login_form_apple.png`|否|是|
|`tasks/Component/SwitchSoul/ss/ss_sou_switch_1.png`|是|否|
|`tasks/Component/SwitchSoul/ss/ss_sou_switch_2.png`|是|否|
|`tasks/Component/SwitchSoul/ss/ss_sou_switch_3.png`|是|否|
|`tasks/Component/SwitchSoul/ss/ss_sou_switch_4.png`|是|否|
|`tasks/DailyTrifles/dt/dt_dt_gw_donate_red.png`|是|否|
|`tasks/DailyTrifles/dt/dt_dt_gw_give.png`|是|否|
|`tasks/DailyTrifles/dt/dt_dt_gw_one_collect.png`|是|否|
|`tasks/DailyTrifles/love/love_close_luck_red.png`|否|是|
|`tasks/Delegation/d/d_d_cancel.png`|是|否|
|`tasks/Delegation/d/d_d_select_first.png`|否|是|
|`tasks/DemonEncounter/boss/boss_boss_done_check.png`|否|是|
|`tasks/DemonEncounter/boss/boss_boss_wait.png`|否|是|
|`tasks/DemonEncounter/demon/demon_de_box_center.png`|否|是|
|`tasks/DemonEncounter/demon/demon_de_to_real_world.png`|否|是|
|`tasks/DemonEncounter/demon/demon_jade_50.png`|否|是|
|`tasks/DemonEncounter/demon/demon_mystery_amulet.png`|否|是|
|`tasks/DemonEncounter/demon/demon_sushi.png`|否|是|
|`tasks/DemonRetreat/DemonRetreat/open_retreat_sure.png`|是|否|
|`tasks/Dokan/res/Screenshots_ok.png`|是|否|
|`tasks/Dokan/res/Screenshots_quit_dokan_sure.png`|是|否|
|`tasks/Dokan/res/dokan_attacking.png`|是|否|
|`tasks/Dokan/res/gb_prepare_dark.png`|是|否|
|`tasks/Dokan/res/gb_prepare_highlight.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_abandoned_toppa.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_abandoned_toppa_abandoned.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_abandoned_toppa_continue.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_abandoned_toppa_ensure.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_abandoned_toppa_title.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_activated.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_battle_master_first.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_battle_master_second.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_battle_over.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_challenge_ensure.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_cheering.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_cheering_gray.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_create_dokan.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_create_dokan_ensure.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_dokan_info_close.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_exit_ensure.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_failed_vote_battle_again.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_failed_vote_keep_bounty.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_failed_vote_no.png.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_have_dokan.png`|否|是|
|`tasks/Dokan/res/res_ryou_dokan_master_battle.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_quit_battle_ensure.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_refresh_ensure.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_remain_attack_count_done.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_remain_attack_count_one.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_remain_attack_count_zero.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_shikigami.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_start_challenge2.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_today_attack_count.png`|是|否|
|`tasks/Dokan/res/res_ryou_dokan_toppa_rank.png`|是|否|
|`tasks/Dokan/res/scene_shenshe.png`|是|否|
|`tasks/Duel/ban/sp云外镜.png`|否|是|
|`tasks/Duel/ban/封阳君.png`|否|是|
|`tasks/Duel/ban/星熊童子.png`|否|是|
|`tasks/Duel/ban/祸津神.png`|否|是|
|`tasks/Duel/ban/荒骷髅.png`|否|是|
|`tasks/Duel/duel/d_win_share.png`|否|是|
|`tasks/Duel/duel/duel_ban_ensure.png`|否|是|
|`tasks/Duel/duel/duel_cancel.png`|是|否|
|`tasks/Duel/duel/duel_d_check_ban.png`|否|是|
|`tasks/Duel/duel/duel_d_confirm.png`|是|否|
|`tasks/Duel/duel/duel_duel_celeb_honor.png`|否|是|
|`tasks/Duel/duel/duel_duel_exit.png`|否|是|
|`tasks/Duel/duel/duel_duel_honor.png`|否|是|
|`tasks/Duel/duel/duel_duel_main_uesless_message.png`|否|是|
|`tasks/Duel/duel/duel_exit_waiting.png`|否|是|
|`tasks/Duel/duel/duel_white_dog.png`|否|是|
|`tasks/Duel/duel/gb_exit.png`|是|否|
|`tasks/EternitySea/res/res_eternity_sea_fire.png`|否|是|
|`tasks/EternitySea/res/res_eternitysea_unlock.png`|否|是|
|`tasks/EternitySea/res/res_form_team.png`|否|是|
|`tasks/EternitySea/res/res_neweternitysea_lock.png`|否|是|
|`tasks/EvoZone/o/o_evozone_fire.png`|是|否|
|`tasks/Exploration/highlight/highlight_up_coin - 副本.png`|是|否|
|`tasks/Exploration/highlight/highlight_up_daruma - 副本.png`|是|否|
|`tasks/Exploration/highlight/highlight_up_exp - 副本.png`|是|否|
|`tasks/Exploration/res/res_check_main_title.png`|否|是|
|`tasks/Exploration/res/res_check_play_title.png`|否|是|
|`tasks/Exploration/res/res_e_check_exit.png`|否|是|
|`tasks/Exploration/res/res_e_exit_cancel.png`|否|是|
|`tasks/Exploration/res/res_e_open_folder.png`|否|是|
|`tasks/Exploration/res/res_e_reward_box_big.png`|否|是|
|`tasks/Exploration/res/res_e_reward_box_small.png`|否|是|
|`tasks/FallenSun/f/f_pet_present.png`|是|否|
|`tasks/FrogBoss/fb/fb_forg_mall_close.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_last_lose.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_last_select_blue.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_last_select_red.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_last_win.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_log.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_log_check.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_log_close.png`|否|是|
|`tasks/FrogBoss/fb/fb_frog_mall.png`|否|是|
|`tasks/GameUi/win_false/gb_win_4.png`|是|否|
|`tasks/GlobalGame/gg/gg_accept.png`|是|否|
|`tasks/GlobalGame/gg/gg_client_clear.png`|否|是|
|`tasks/GlobalGame/gg/gg_f_accept.png`|是|否|
|`tasks/GlobalGame/gg/gg_f_jade.png`|是|否|
|`tasks/GlobalGame/gg/gg_f_reject.png`|是|否|
|`tasks/GlobalGame/gg/gg_network_abnormal.png`|否|是|
|`tasks/GlobalGame/gg/gg_network_error.png`|否|是|
|`tasks/GlobalGame/gg/gg_reject.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_back_blue.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_back_circle.png`|否|是|
|`tasks/GlobalGame/ui/ui_ui_back_red.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_back_yellow.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_back_yellow_2.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_cancel.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_cancel_samll.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_confirm_samll.png`|否|是|
|`tasks/GlobalGame/ui/ui_ui_ensure.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_exit.png`|是|否|
|`tasks/GlobalGame/ui/ui_ui_rewards.png`|是|否|
|`tasks/GuildBanquet/res/res_banquet_all_put.png`|否|是|
|`tasks/GuildBanquet/res/res_banquet_clear_all.png`|否|是|
|`tasks/GuildBanquet/res/res_banquet_confirm.png`|否|是|
|`tasks/GuildBanquet/res/res_banquet_exp_full.png`|否|是|
|`tasks/GuildBanquet/res/res_banquet_flag.png`|否|是|
|`tasks/GuildBanquet/res/res_banquet_switch.png`|否|是|
|`tasks/HeroTest/as/as_bcmj_reset_close.png`|是|否|
|`tasks/HeroTest/as/as_gbb_back2.png`|是|否|
|`tasks/KekkaiUtilize/ku/ku_check_guild_lottery.png`|否|是|
|`tasks/KekkaiUtilize/ku/ku_guild_lottery.png`|否|是|
|`tasks/KekkaiUtilize/ku/ku_guild_lottery_special_reward.png`|否|是|
|`tasks/KekkaiUtilize/ku/ku_ku_check_can_lottery.png`|否|是|
|`tasks/KekkaiUtilize/realm/realm_auto_fill.png`|否|是|
|`tasks/KekkaiUtilize/realm/realm_check_guild_card.png`|否|是|
|`tasks/KekkaiUtilize/realm/realm_remove_all.png`|否|是|
|`tasks/KekkaiUtilize/utilize/utilize_u_empty_card.png`|否|是|
|`tasks/KittyShop/ks/image_name.png`|是|否|
|`tasks/KittyShop/ks/ks_main_finsh.png`|是|否|
|`tasks/LBS/res/lbs_create_ensure.png`|否|是|
|`tasks/LBS/res/lbs_ensure_private.png`|否|是|
|`tasks/LBS/res/lbs_ensure_private_false.png`|否|是|
|`tasks/LBS/res/lbs_ensure_public.png`|否|是|
|`tasks/LBS/res/lbs_ensure_public_false.png`|否|是|
|`tasks/LBS/res/lbs_entry.png`|否|是|
|`tasks/LBS/res/lbs_find_team.png`|否|是|
|`tasks/LBS/res/lbs_map_entry.png`|否|是|
|`tasks/LBS/res/lbs_match_cancel.png`|否|是|
|`tasks/LBS/res/lbs_settle_confirm.png`|否|是|
|`tasks/LBS/res/lbs_team_challenge.png`|否|是|
|`tasks/MetaDemon/md/md_md_friend_selected.png`|否|是|
|`tasks/MetaDemon/md/md_md_invite.png`|否|是|
|`tasks/MetaDemon/md/md_md_invite_friends.png`|否|是|
|`tasks/MetaDemon/md/md_md_start_synthesis.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_empty.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_five_star.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_four_star.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_need_money.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_one_star.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_three_star.png`|否|是|
|`tasks/MetaDemon/md/md_md_synthesis_two_star.png`|否|是|
|`tasks/MetaDemon/md/md_md_ticket_empty.png`|否|是|
|`tasks/MysteryShop/ms/ms_ms_reward_4.png`|是|否|
|`tasks/NianTrue/nian/gr_create_ensure .png`|是|否|
|`tasks/NianTrue/nian/nian_n_ok.png`|是|否|
|`tasks/Orochi/o/o_orochi_check_10.png`|否|是|
|`tasks/Orochi/o/o_orochi_check_11.png`|否|是|
|`tasks/Orochi/o/o_orochi_check_12.png`|否|是|
|`tasks/Orochi/o/o_orochi_check_13.png`|否|是|
|`tasks/Orochi/o/o_orochi_fire.png`|是|否|
|`tasks/Orochi/o/o_orochi_wild_fire.png`|是|否|
|`tasks/Pets/pet/pet_pet_claw.png`|否|是|
|`tasks/Pets/pet/pet_pet_house.png`|否|是|
|`tasks/Quiz/quiz/alone_ensure.png`|否|是|
|`tasks/Quiz/quiz/entry.png`|否|是|
|`tasks/Quiz/quiz/fail_quit.png`|否|是|
|`tasks/Quiz/quiz/message.png`|否|是|
|`tasks/RealmRaid/res/res_fire_again.png`|否|是|
|`tasks/RealmRaid/res/res_fresh_ensure.png`|是|否|
|`tasks/RealmRaid/res/res_show_again.png`|否|是|
|`tasks/Restart/harvest/harvest_harvest_mail_2.png`|否|是|
|`tasks/Restart/harvest/harvest_mail_red_point.png`|否|是|
|`tasks/Restart/harvest/harvest_special_mail_close.png`|否|是|
|`tasks/Restart/harvest/harvest_special_mail_open.png`|否|是|
|`tasks/Restart/harvest/harvest_system_mail_close.png`|否|是|
|`tasks/Restart/harvest/harvest_system_mail_open.png`|否|是|
|`tasks/Restart/harvest/harvest_zidu.png`|是|否|
|`tasks/Restart/harvest/image_name.png`|是|否|
|`tasks/Restart/harvest/mail_cancel.png`|是|否|
|`tasks/Restart/login/login_cancel_battle.png`|否|是|
|`tasks/Restart/login/login_courtyard.png`|否|是|
|`tasks/Restart/login/login_early_server.png`|否|是|
|`tasks/Restart/login/login_early_server_cancel.png`|否|是|
|`tasks/Restart/login/login_login_cancel_battle.png`|是|否|
|`tasks/Restart/login/login_login_cancel_bind_phone.png`|是|否|
|`tasks/Restart/login/login_login_red_close_1.png`|是|否|
|`tasks/Restart/login/login_return_chess_cancel.png`|否|是|
|`tasks/Restart/login/login_watch_video_cancel.png`|是|否|
|`tasks/RichMan/guild/guild_guild_check_scrap2.png`|是|否|
|`tasks/RichMan/tt/tt_share_ok.png`|是|否|
|`tasks/RyouToppa/res/res_ryou_reward_90.png`|否|是|
|`tasks/SixRealms/l102/l102_.png`|是|否|
|`tasks/SixRealms/moon_sea/ms/ms_ms_exit_prepare.png`|否|是|
|`tasks/SixRealms/sr/sr_sr_switch_gate.png`|否|是|
|`tasks/SixRealms_jue/gate1/gate1_select_shikigami_and_confirm.png`|是|否|
|`tasks/SixRealms_jue/l102/l102_.png`|是|否|
|`tasks/Sougenbi/s/s_s_fire.png`|是|否|
|`tasks/Sougenbi/s/s_s_fire_anger.png`|是|否|
|`tasks/Sougenbi/s/s_s_fire_foolery.png`|是|否|
|`tasks/Sougenbi/s/s_s_fire_greed.png`|是|否|
|`tasks/SoulsTidy/simple/simple_st_abandoned_selected.png`|否|是|
|`tasks/SoulsTidy/simple/simple_st_gold.png`|否|是|
|`tasks/SoulsTidy/simple/simple_st_level_0.png`|否|是|
|`tasks/SoulsTidy/simple/simple_st_luck.png`|否|是|
|`tasks/SoulsTidy/simple/simple_st_small_luck.png`|否|是|
|`tasks/SoulsTidy/simple/simple_st_soul_overflow.png`|否|是|
|`tasks/SoulsTidy/simple/simple_st_souls_close.png`|否|是|
|`tasks/TalismanPass/tp/tp_overflow_confirme.png`|是|否|
|`tasks/TalismanPass/tp/tp_red_point_month.png`|否|是|
|`tasks/TalismanPass/tp/tp_tp_soul_1.png`|否|是|
|`tasks/TalismanPass/tp/tp_tp_soul_2.png`|否|是|
|`tasks/TalismanPass/tp/tp_tp_soul_3.png`|否|是|
|`tasks/TrueOrochi/st/st_module.png`|否|是|
|`tasks/TrueOrochi/st/st_st_fire_confirm.png`|是|否|
|`tasks/WantedQuests/invite/wq_invite_cancel.png`|是|否|
|`tasks/WantedQuests/invite/wq_invite_diff_svr_highlight.png`|否|是|
|`tasks/WantedQuests/invite/wq_invite_friend_list_appear.png`|否|是|
|`tasks/WantedQuests/wq/wq_goto_1.png`|否|是|
|`tasks/WantedQuests/wq/wq_goto_2.png`|否|是|
|`tasks/WantedQuests/wq/wq_goto_3.png`|否|是|
|`tasks/WantedQuests/wq/wq_goto_4.png`|否|是|
|`tasks/WantedQuests/wq/wq_list_top_bottom_check.png`|否|是|
|`tasks/WantedQuests/wq/wq_trace_disable.png`|否|是|
|`tasks/WantedQuests/wq/wq_trace_one_check_opened.png`|否|是|
|`tasks/WantedQuests/wq/wq_trace_one_disable.png`|否|是|
|`tasks/WantedQuests/wq/wq_trace_one_enable.png`|否|是|
|`tasks/WantedQuests/wq/wq_trace_one_realworld.png`|否|是|
|`tasks/WantedQuests/wq/wq_wq_d1111.png`|否|是|
|`tasks/WantedQuests/wq/wq_wq_nian.png`|否|是|
|`tasks/WantedQuests/wq/wq_wqse_special_fire.png`|否|是|
