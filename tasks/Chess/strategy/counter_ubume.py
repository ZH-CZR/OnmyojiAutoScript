"""反击姑获鸟：固定角色、持有目标和无点击运营决策。"""
from collections import Counter

from tasks.Chess.strategy.lineup_strategy import build_lineup_strategy
from tasks.Chess.strategy.shikigami_catalog import build_lineup_shikigami, SHIKIGAMI_BONDS_BY_ROMAJI


KEY = 'counter_ubume'
UBUME = 'ubume'
KUJIRA = 'kujira'
JINKOUGYOU = 'jinkougyou'
KAPPA = 'kappa'
GASHADOKURO = 'gashadokuro'
FRONTLINE = ('kuro_douji', 'kachou_fuugetsu', 'miketsu', JINKOUGYOU, GASHADOKURO)
ATTACK_ORDER = (UBUME, KUJIRA)
DEFENSIVE_SOULS = frozenset({'beifu', 'bangjing', 'niepanzhihuo', 'qingnvfang', 'dizangxiang', 'jingji'})
KUJIRA_SOULS = ('huoling', 'zhaocaimao')
CORE_SOULS = {UBUME: 'yingshengchong', 'kuro_douji': 'zheng'}
# 已由游戏画面核对的关键羁绊档位；未核对的其他羁绊不猜测。
KEY_BOND_THRESHOLDS = {
    '平安京': (2, 4, 6, 8), '追击': (2, 4, 6), '回响': (2, 4, 6, 8),
    '甲胄': (2, 4, 6, 8), '护佑': (2, 4, 6, 8), '六道': (1,),
}

# 前排依次为1/3/5/7/9/11，后排依次为2/4/6/8/10/12。
SLOTS = (
    {'name': 'miketsu', 'position': 1, 'min_level': 1},
    {'name': 'kachou_fuugetsu', 'position': 3, 'min_level': 1},
    {'name': JINKOUGYOU, 'position': 5, 'min_level': 1, 'substitute': KAPPA},
    {'name': 'kuro_douji', 'position': 7, 'min_level': 1},
    {'name': 'gashadokuro', 'position': 9, 'min_level': 8},
    {'name': KUJIRA, 'position': 4, 'min_level': 7},
    {'name': KUJIRA, 'position': 6, 'min_level': 6},
    {'name': UBUME, 'position': 8, 'min_level': 1},
)

COUNTER_UBUME = build_lineup_strategy({
    'key': KEY, 'display_name': '反击姑获鸟',
    'shikigami_positions': {
        '御馔津': {'position': 1},
        '花鸟卷': {'position': 3},
        '寻香行': {'position': 5},
        '黑童子': {'position': 7},
        '荒骷髅': {'position': 9},
        '久次良': {'position': 6, 'target_star': 2, 'target_count': 2},
        '姑获鸟': {'position': 8, 'weight': 0},
    },
})
COUNTER_UBUME.update(
    slots=SLOTS, final_level=8,
    substitutes=build_lineup_shikigami({'河童': {'position': 5, 'target_star': 1}}),
)


def purchase_limit(name, level=None):
    if name == GASHADOKURO and level is not None and level < 8:
        return 1
    return 6 if name == KUJIRA else 1 if name == KAPPA else 9


def purchase_priority(name, inventory, level=None, primary_acquired=False):
    """核心→补人口/关键羁绊→关键前排二星→接近三星；每次购入重算。"""
    total = inventory.totals.get(name, 0)
    if name == UBUME:
        return (0, 0, -total)
    can_deploy = False
    replacement = False
    if level is not None and not any(c.name == name and c.star is not None for c in inventory.hand):
        population = sum(not u.special for u in inventory.board.values())
        for slot in SLOTS:
            if slot['min_level'] > level:
                continue
            target = slot['name']
            if name == KAPPA and target == JINKOUGYOU and not (primary_acquired or has_primary(inventory)):
                target = KAPPA
            if target != name:
                continue
            occupant = inventory.board.get(slot['position'])
            replacement = name == JINKOUGYOU and occupant is not None and occupant.name == KAPPA
            can_deploy = replacement or (occupant is None and population < level)
            if can_deploy:
                break
    if can_deploy:
        names = {u.name for u in inventory.board.values() if not u.special}
        if replacement:
            names.discard(KAPPA)
        counts = Counter(b for n in names for b in SHIKIGAMI_BONDS_BY_ROMAJI.get(n, ()))
        gain = (name not in names and any(counts[b] + 1 in KEY_BOND_THRESHOLDS.get(b, ())
                                          for b in SHIKIGAMI_BONDS_BY_ROMAJI.get(name, ())))
        return (1, -int(gain), -total)
    one_stars = sum(u.name == name and u.star == 1
                    for u in (*inventory.hand, *inventory.board.values()))
    needs_frontline_two = (name in FRONTLINE and one_stars >= 2
                          and any(u.name == name and u.star == 1 for u in inventory.board.values())
                          and not any(c.name == name and c.star is not None and c.star >= 2 for c in inventory.hand))
    return (2 if needs_frontline_two else 3, 0, -total)


def has_primary(inventory):
    return (inventory.totals.get(JINKOUGYOU, 0) > 0
            or any(u.name == JINKOUGYOU for u in inventory.hand)
            or any(u.name == JINKOUGYOU for u in inventory.board.values()))


def can_buy(name, inventory, primary_acquired=False, level=None):
    allowed = set(COUNTER_UBUME['shikigami']) | {KAPPA}
    return (name in allowed and inventory.ready and name not in inventory.uncertain
            and not (inventory.deferred_board and (level is None or level >= 6))
            and not (name == KAPPA and (primary_acquired or has_primary(inventory)))
            and inventory.totals.get(name, 0) < purchase_limit(name, level))


def confirmed_three_stars(inventory):
    return sum(not u.special and u.star_confirmed and u.star == 3 and u.name != KUJIRA
               for u in inventory.board.values())


def operation(level, inventory):
    """升级以实际场上成品为准；未知账本不启动付费动作。"""
    if not inventory.ready or (level >= 6 and inventory.deferred_board):
        return 'hold'
    if level < 6:
        return 'experience'
    ubume_ready = any(u.name == UBUME and u.star == 3 and u.star_confirmed
                      for u in inventory.board.values())
    if level == 6:
        return 'experience' if ubume_ready else 'refresh'
    if level == 7:
        return 'experience' if ubume_ready and confirmed_three_stars(inventory) >= 2 else 'refresh'
    if all(inventory.totals.get(name, 0) >= purchase_limit(name)
           for name in COUNTER_UBUME['shikigami']):
        return 'hold'
    return 'refresh'


def reserve(level):
    # 包含严格大于的边界：操作后至少51/31金币；8阶可花光。
    return 51 if level < 6 else 31 if level < 8 else 0


def missing_deployments(level, inventory, primary_acquired=False):
    """只返回已有手牌、人口足够时可部署的空角色；不隐式交换。"""
    if not inventory.ready:
        return []
    unknown = any(u.name is None and not u.special for u in inventory.board.values())
    if sum(not u.special for u in inventory.board.values()) >= level and not unknown:
        return []
    available = {u.name for u in inventory.hand if u.star is not None}
    result = []
    for slot in SLOTS:
        occupant = inventory.board.get(slot['position'])
        if slot['min_level'] > level or (occupant is not None
                                       and (occupant.special or occupant.name is not None)):
            continue
        name = slot['name']
        if name == JINKOUGYOU and name not in available:
            if primary_acquired or has_primary(inventory):
                continue
            name = KAPPA
        if name in available:
            result.append({**slot, 'name': name})
    return sorted(result, key=lambda slot: (purchase_priority(slot['name'], inventory, level, primary_acquired),
                                             slot['min_level']))


def can_equip(position, soul_name, board, attributes):
    """先核验两槽、重复装备，再预留专属魂；双久次良共享火/财最低保障。"""
    unit = board[position]
    equipped = attributes.get(position, (None, None, None))[1:]
    free = sum(s is None for s in equipped)
    if not free or soul_name in equipped:
        return False
    required = CORE_SOULS.get(unit.name)
    if required is not None and required not in equipped and soul_name != required and free <= 1:
        return False
    if unit.name == KUJIRA:
        positions = [p for p, u in board.items() if u.name == KUJIRA and not u.special]
        worn = {s for p in positions for s in attributes.get(p, (None, None, None))[1:] if s is not None}
        missing = set(KUJIRA_SOULS) - worn
        free_total = sum(s is None for p in positions for s in attributes.get(p, (None, None, None))[1:])
        return free_total - 1 >= len(missing - {soul_name})
    return True
