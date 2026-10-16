"""Unavailable business implementations, checked before device activity."""
UNAVAILABLE_TASKS = {
    "SwitchAccountMany": "上游仅提供闭源账号管理实现，尚未独立实现。",
    "SwitchAccountOnce": "依赖尚未迁移的账号管理组件。",
    "SwitchAccountLoop": "依赖尚未迁移的账号管理组件。",
    "TongXinTeam": "上游仅提供闭源同心队实现，尚未独立实现。",
    "Hyakkiyakou": "第一仓库也依赖 oashya 二进制跟踪器；公开替代实现完成前暂不启用。",
}


def require_task(command):
    if command in UNAVAILABLE_TASKS:
        from module.exception import RequestHumanTakeover
        raise RequestHumanTakeover(f"{command}: {UNAVAILABLE_TASKS[command]}")
