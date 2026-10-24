"""Explicit task boundaries enforced before scheduling or importing task code."""
from module.config.utils import convert_to_underscore


UNAVAILABLE_TASKS = {
    'hyakkiyakou': '百鬼夜行暂缓开放：现有实现包含未审查的字节码封装，等待公开实现。',
}


def unavailable_reason(task: str) -> str | None:
    return UNAVAILABLE_TASKS.get(convert_to_underscore(task))
