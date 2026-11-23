# This Python file uses the following encoding: utf-8
"""错误码映射：把异常翻译成普通用户能看懂的中文结论和建议。

错误码是稳定契约，前端（OASX）可以按 code 做分组统计或展示固定文案；
summary / suggestion 允许后续润色，但 code 不要改。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# 错误码 -> (中文结论, 处理建议)
ERROR_CODES: dict[str, dict[str, str]] = {
    "E_ENV_RESOLUTION": {
        "summary": "模拟器分辨率不符合要求（需要 1280x720）",
        "suggestion": "把模拟器分辨率改成 1280x720（DPI 240），再重新运行任务。",
    },
    "E_DEVICE_OFFLINE": {
        "summary": "模拟器或设备没有连上",
        "suggestion": "确认模拟器已启动、端口没变；在设备设置里重新连接一次再运行。",
    },
    "E_ADB": {
        "summary": "ADB 连接异常",
        "suggestion": "重启模拟器的 ADB 调试，或重启模拟器后再试；检查是否被其他程序占用端口。",
    },
    "E_GAME_NOT_RUNNING": {
        "summary": "游戏客户端没有运行",
        "suggestion": "确认游戏已安装并能正常启动；脚本会自动尝试重启游戏。",
    },
    "E_LOGIN": {
        "summary": "游戏停在登录界面或登录态失效",
        "suggestion": "手动登录一次游戏，再让脚本继续运行。",
    },
    "E_PAGE_UNKNOWN": {
        "summary": "无法识别当前游戏界面",
        "suggestion": "查看诊断包里的截图确认停在哪个界面；若是维护公告请等待维护结束。",
    },
    "E_RULE_NOT_FOUND": {
        "summary": "任务需要的界面或图片模板没有找到",
        "suggestion": "可能是游戏界面改版。查看截图与服务端错误目录，必要时更新对应任务的规则图片。",
    },
    "E_CLICK_GUARD_STUCK": {
        "summary": "画面长时间没有变化，任务卡住了",
        "suggestion": "查看截图确认卡在哪个界面；脚本会自动重启游戏，若反复出现请检查任务配置。",
    },
    "E_CLICK_GUARD_TOO_MANY": {
        "summary": "点击次数异常偏多，可能在错误界面反复点击",
        "suggestion": "查看截图确认当前界面；若界面改版导致误识别，需要更新对应任务规则。",
    },
    "E_SERVER_MAINTENANCE": {
        "summary": "游戏服务器可能正在维护",
        "suggestion": "等维护结束后再运行；脚本已暂停相关任务时会自动恢复。",
    },
    "E_ACTIVITY_UI_CHANGED": {
        "summary": "活动界面改版，脚本按旧界面找不到入口",
        "suggestion": "确认活动是否改版；需要更新该活动的界面适配后再运行。",
    },
    "E_TASK_CONFIG": {
        "summary": "任务配置不正确，需要人工处理",
        "suggestion": "按错误提示检查对应任务的设置项（例如未选择的关卡、缺失的编队等）。",
    },
    "E_UNKNOWN": {
        "summary": "发生了未分类的错误",
        "suggestion": "查看诊断包中的堆栈和日志尾部；若无法判断可把诊断包发给开发者。",
    },
}

# 异常类名 -> 错误码。顺序无关，精确匹配类型名。
_EXCEPTION_CODES: dict[str, str] = {
    "GameNotRunningError": "E_GAME_NOT_RUNNING",
    "EmulatorNotRunningError": "E_DEVICE_OFFLINE",
    "GameStuckError": "E_CLICK_GUARD_STUCK",
    "GameTooManyClickError": "E_CLICK_GUARD_TOO_MANY",
    "GamePageUnknownError": "E_PAGE_UNKNOWN",
    "RequestHumanTakeover": "E_TASK_CONFIG",
    "ScriptError": "E_UNKNOWN",
    "GameBugError": "E_PAGE_UNKNOWN",
    "AdbError": "E_ADB",
    "AdbTimeout": "E_ADB",
    "ConnectionError": "E_ADB",
    "DeviceNotFoundError": "E_DEVICE_OFFLINE",
}

# 文本关键词 -> 错误码，按顺序匹配，越靠前越优先。
_MESSAGE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("1280x720", "E_ENV_RESOLUTION"),
    ("resolution", "E_ENV_RESOLUTION"),
    ("分辨率", "E_ENV_RESOLUTION"),
    ("device offline", "E_DEVICE_OFFLINE"),
    ("offline", "E_DEVICE_OFFLINE"),
    ("not running", "E_GAME_NOT_RUNNING"),
    ("未运行", "E_GAME_NOT_RUNNING"),
    ("adb", "E_ADB"),
    ("login", "E_LOGIN"),
    ("登录", "E_LOGIN"),
    ("maintenance", "E_SERVER_MAINTENANCE"),
    ("维护", "E_SERVER_MAINTENANCE"),
    ("template", "E_RULE_NOT_FOUND"),
    ("rule", "E_RULE_NOT_FOUND"),
    ("规则", "E_RULE_NOT_FOUND"),
    ("unknown page", "E_PAGE_UNKNOWN"),
    ("页面未知", "E_PAGE_UNKNOWN"),
    ("ui changed", "E_ACTIVITY_UI_CHANGED"),
    ("界面改版", "E_ACTIVITY_UI_CHANGED"),
)


@dataclass(frozen=True)
class ErrorDiagnosis:
    """一个错误的中文诊断结果。"""

    code: str
    summary: str
    suggestion: str
    exception_type: str = ""


def explain(code: str) -> tuple[str, str]:
    """返回错误码对应的中文结论与建议；未知码回退到通用文案。"""
    item = ERROR_CODES.get(code) or ERROR_CODES["E_UNKNOWN"]
    return item["summary"], item["suggestion"]


def classify_exception(exc: Any) -> ErrorDiagnosis:
    """把异常归类成稳定错误码。

    先按异常类名精确匹配，再按异常文本关键词匹配，最后回退 E_UNKNOWN。
    """
    exception_type = type(exc).__name__ if exc is not None else ""
    code = _EXCEPTION_CODES.get(exception_type)
    if code is None:
        code = classify_text(str(exc) if exc is not None else "")
    summary, suggestion = explain(code)
    return ErrorDiagnosis(
        code=code,
        summary=summary,
        suggestion=suggestion,
        exception_type=exception_type,
    )


def classify_text(text: str) -> str:
    """按错误文本猜测错误码，猜不到返回 E_UNKNOWN。"""
    lowered = str(text or "").lower()
    for keyword, code in _MESSAGE_KEYWORDS:
        if keyword in lowered:
            return code
    return "E_UNKNOWN"
