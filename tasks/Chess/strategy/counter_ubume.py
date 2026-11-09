"""反击姑获鸟：固定角色、持有目标和无点击运营决策。"""
from tasks.Chess.strategy.lineup_strategy import build_lineup_strategy
from tasks.Chess.strategy.shikigami_catalog import build_lineup_shikigami


KEY = 'counter_ubume'
UBUME = 'ubume'
KUJIRA = 'kujira'
JINKOUGYOU = 'jinkougyou'
KAPPA = 'kappa'

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


def purchase_limit(name):
    return 6 if name == KUJIRA else 1 if name == KAPPA else 9


def purchase_priority(name, inventory):
    # 以实际折算持有量衡量接近三星的程度；姑获鸟始终优先。
    return (0 if name == UBUME else 1, -inventory.totals.get(name, 0))


def has_primary(inventory):
    return (inventory.totals.get(JINKOUGYOU, 0) > 0
            or any(u.name == JINKOUGYOU for u in inventory.hand)
            or any(u.name == JINKOUGYOU for u in inventory.board.values()))


def can_buy(name, inventory, primary_acquired=False):
    allowed = set(COUNTER_UBUME['shikigami']) | {KAPPA}
    return (name in allowed and inventory.ready and name not in inventory.uncertain
            and not (name == KAPPA and (primary_acquired or has_primary(inventory)))
            and inventory.totals.get(name, 0) < purchase_limit(name))


def confirmed_three_stars(inventory):
    return sum(not u.special and u.star_confirmed and u.star == 3 and u.name != KUJIRA
               for u in inventory.board.values())


def operation(level, inventory):
    """升级以实际场上成品为准；未知账本不启动付费动作。"""
    if not inventory.ready:
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
    if sum(not u.special for u in inventory.board.values()) >= level:
        return []
    available = {u.name for u in inventory.hand if u.star is not None}
    result = []
    for slot in SLOTS:
        if slot['min_level'] > level or slot['position'] in inventory.board:
            continue
        name = slot['name']
        if name == JINKOUGYOU and name not in available:
            if primary_acquired or has_primary(inventory):
                continue
            name = KAPPA
        if name in available:
            result.append({**slot, 'name': name})
    return sorted(result, key=lambda slot: (purchase_priority(slot['name'], inventory), slot['min_level']))
