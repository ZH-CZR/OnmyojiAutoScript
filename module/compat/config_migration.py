"""Explicit migration between the two public configuration formats."""
from copy import deepcopy


def migrate_config(data):
    data = deepcopy(data)
    script = data.get("script") or {}
    device = script.get("device") or {}
    # YYS accepts a bare emulator port; OAS needs an ADB transport serial.
    serial = str(device.get("serial", ""))
    if serial.isdigit() and 1 <= int(serial) <= 65535:
        device["serial"] = f"127.0.0.1:{serial}"
    device.pop("card_key", None)
    if device.get("screenshot_method") == "window_win32" or device.get("control_method") == "window_win32" or script.get("device_2", {}).get("emulator_control") == "win32":
        raise ValueError("window_win32 桌面模式尚无公开替代实现，请使用模拟器的 ADB/nemu_ipc 和 minitouch 配置。")
    if device:
        script["device"] = device
        data["script"] = script
    # Invitations moved from GlobalGame to WantedQuests in YYS.
    global_game = data.get("global_game") or {}
    emergency = global_game.get("emergency") or {}
    invitation = emergency.get("friend_invitation")
    if invitation is not None:
        if invitation == "jade_and_food":
            invitation = "jade_sushi_food"
        emergency["friend_invitation"] = invitation
        wanted = data.setdefault("wanted_quests", {})
        wanted.setdefault("emergency", {}).setdefault("friend_invitation", invitation)
    # In the open core, WeeklyPurchase is the shop; RichMan is an older
    # activity name. Do not accidentally load activity settings as shop settings.
    if "weekly_purchase" in data:
        data["rich_man"] = data.pop("weekly_purchase")
    elif isinstance(data.get("rich_man"), dict):
        if not any(key in data["rich_man"] for key in ("special_room", "thousand_things", "guild_store")):
            data.pop("rich_man")
    if data.get("running_task") == "WeeklyPurchase":
        data["running_task"] = "RichMan"
    # Upstream's restart task has no scheduler; the open runtime needs one.
    restart = data.get("restart") or {}
    if restart.get("task_config", {}).get("error_restart") is False:
        restart.setdefault("restart_config", {})["error_restart_limit"] = 0
    if restart:
        data["restart"] = restart
    return data
