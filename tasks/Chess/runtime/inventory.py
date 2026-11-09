"""单局持有账本。数量均为当前持有量，不使用累计购买次数代替。"""
from collections import Counter
from dataclasses import dataclass, field


def copies_for_star(star: int) -> int:
    if type(star) is not int or star not in (1, 2, 3):
        raise ValueError('星级必须为1、2或3')
    return 3 ** (star - 1)


@dataclass(frozen=True)
class HandUnit:
    name: str | None
    star: int | None
    position: tuple[int, int]
    roi: tuple[int, int, int, int]


@dataclass(frozen=True)
class BoardUnit:
    name: str | None
    star: int | None
    special: bool = False
    star_confirmed: bool = True


@dataclass
class CardInventory:
    """None 表示尚未确认，不能按空位或一星处理。每局重新创建。"""
    board: dict[int, BoardUnit] = field(default_factory=dict)
    hand: tuple[HandUnit, ...] = ()
    totals: dict[str, int] = field(default_factory=dict)
    uncertain: set[str] = field(default_factory=set)
    ready: bool = False

    @staticmethod
    def hand_signature(hand):
        # 动画可造成轻微位移；同名同星数量才是账本的稳定依据。
        return Counter((card.name, card.star) for card in hand)

    def reconcile(self, hand, board):
        self.hand, self.board = tuple(hand), dict(board)
        totals = Counter()
        uncertain = set()
        unknown_board = False
        for unit in (*self.hand, *self.board.values()):
            if isinstance(unit, BoardUnit) and unit.special:
                continue
            if unit.name is None:
                unknown_board = True
            elif unit.star is None:
                uncertain.add(unit.name)
            else:
                totals[unit.name] += copies_for_star(unit.star)
        self.totals = dict(totals)
        self.uncertain = uncertain
        self.ready = not unknown_board

    def can_buy(self, name, target_star, target_count=1):
        return (self.ready and name not in self.uncertain
                and self.totals.get(name, 0) < copies_for_star(target_star) * target_count)

    def purchased(self, name):
        # 商店确认买入的是一星；自动合成不改变折算张数。
        self.totals[name] = self.totals.get(name, 0) + 1

    def excess(self, card, target_star, target_count=1):
        """仅在另有一张达标实体卡时出售；不把尚未合成的材料当成成品。"""
        if not self.ready or card.star is None or card.name in self.uncertain:
            return False
        others = [u for u in self.board.values()
                  if not u.special and u.name == card.name and u.star is not None
                  and u.star_confirmed]
        others.extend(u for u in self.hand if u is not card
                      and u.name == card.name and u.star is not None)
        # 优先保留最高星；同星保留场上卡，手牌保留最左侧一张。
        return sum(u.star >= target_star and u.star >= card.star
                   and (u.star > card.star or isinstance(u, BoardUnit)
                        or u.position[0] < card.position[0]) for u in others) >= target_count

    def snapshot(self):
        units = [*self.hand, *(u for u in self.board.values() if not u.special)]
        names = {u.name for u in units if u.name is not None}
        return {
            'ready': self.ready,
            'equivalent_copies': dict(self.totals),
            'uncertain': sorted(self.uncertain),
            'cards': {name: {'count': sum(u.name == name for u in units),
                              'stars': dict(Counter(u.star for u in units
                                                    if u.name == name and u.star is not None)),
                              'equivalent_copies': self.totals.get(name, 0)} for name in sorted(names)},
            'hand': [{'name': u.name, 'star': u.star, 'position': u.position}
                     for u in self.hand],
            'board': {i: ({'name': self.board[i].name, 'star': self.board[i].star,
                           'special': self.board[i].special,
                           'star_confirmed': self.board[i].star_confirmed} if i in self.board else None)
                      for i in range(1, 13)},
        }
