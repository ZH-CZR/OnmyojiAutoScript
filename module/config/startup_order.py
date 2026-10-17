"""One startup draw, restricted to due occurrences with equal priority."""
import random

from module.logger import logger


# Server-process snapshots received from the active script process. No disk state.
active_startup_orders = {}


class StartupTaskOrder:
    def __init__(self):
        self.initialized = False
        self.ranks = {}

    @staticmethod
    def key(task):
        return task.command, task.priority, task.next_run

    def initialize(self, pending, enabled):
        if self.initialized:
            return
        self.initialized = True
        if not enabled:
            return
        groups = {}
        for task in pending:
            if task.command != 'Restart':
                groups.setdefault(task.priority, []).append(task)
        groups = [group for group in groups.values() if len(group) > 1]
        if not groups or random.random() >= 0.2:
            return
        for group in groups:
            shuffled = list(group)
            random.shuffle(shuffled)
            # A successful draw should actually change each eligible group.
            if [self.key(t) for t in shuffled] == [self.key(t) for t in group]:
                shuffled = shuffled[1:] + shuffled[:1]
            self.ranks.update({self.key(task): rank for rank, task in enumerate(shuffled)})
            logger.info(f'Startup task order (priority={group[0].priority}): '
                        f'{[task.command for task in shuffled]}')

    def apply(self, pending, running=''):
        result = list(pending)
        positions = {}
        for index, task in enumerate(result):
            if task.command != running and self.key(task) in self.ranks:
                positions.setdefault(task.priority, []).append(index)
        for indices in positions.values():
            ordered = sorted((result[i] for i in indices), key=lambda task: self.ranks[self.key(task)])
            for index, task in zip(indices, ordered):
                result[index] = task
        return result
