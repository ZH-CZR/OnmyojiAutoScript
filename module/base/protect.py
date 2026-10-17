import random
from time import sleep

from module.logger import logger


def click_timing_enabled(config) -> bool:
    script = getattr(config, 'script', None)
    settings = getattr(script, 'anti_ban', None)
    return bool(getattr(settings, 'click_timing_enable', False))


def random_delay(min_value: float = 2.0, max_value: float = 6.0, decimal: int = 1):
    """
    防封
    """
    random_float_in_range = random.uniform(min_value, max_value)
    sleep(round(random_float_in_range, decimal))


def random_sleep(probability: float = 0.05):
    if random.random() <= probability:
        logger.info('Tigger random sleep')
        random_delay()
