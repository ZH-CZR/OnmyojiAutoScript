"""RuleClick 拟人采样的不变量。

RuleClick 现在默认走 `_human_coord`：以最近若干落点的加权重心为采样中心，
按上一落点的方向拉椭圆、按点击次数收缩方差。这套改动对全仓每一次点击生效，
因此必须钉死三件事：

1. 落点永远落在 roi 内 —— 一旦点出界，任务会卡死在点不到按钮上；
2. 重复点击同一目标时方差要收敛 —— 这是"拟人"的核心观感，也是 shrink 的存在意义；
3. humanize=False 必须完全退回旧行为且不留下任何状态 —— 给敏感点击留的退路。
"""
import random
import statistics

import numpy as np
import pytest

from module.atom.click import RuleClick

ROIS = [
    (679, 164, 83, 54),      # 常规整数 roi
    (232.5, 196, 55, 151),   # 浮点 roi，AbyssShadows/C_ABYSS_DRAGON
    (104, 79, 1050, 507),    # 全屏随机点击，GeneralBattle/C_RANDOM_CLICK
    (20, 36, 30, 14),        # 极小 roi，AbyssShadows/C_QUIT_AREA
    (1185, 115, 79, 388),    # 狭长 roi，GeneralBattle/C_RANDOM_RIGHT
]


def in_roi(point, roi):
    x, y, width, height = roi
    return x <= point[0] < x + width and y <= point[1] < y + height


def spread(points):
    """落点在 x/y 两轴上的总体标准差之和。"""
    return statistics.pstdev([p[0] for p in points]) + statistics.pstdev([p[1] for p in points])


@pytest.mark.parametrize('roi', ROIS)
def test_humanized_points_stay_inside_roi(roi):
    RuleClick.reset_task_points()
    random.seed(0)
    np.random.seed(0)
    rule = RuleClick(roi_front=roi, roi_back=roi, name='bounded')

    points = [rule.coord() for _ in range(300)]

    assert all(in_roi(point, roi) for point in points)


def test_humanized_coord_more_stays_inside_roi_back():
    RuleClick.reset_task_points()
    random.seed(0)
    np.random.seed(0)
    roi_front, roi_back = (10, 10, 20, 20), (200, 300, 400, 250)
    rule = RuleClick(roi_front=roi_front, roi_back=roi_back, name='bounded_back')

    points = [rule.coord_more() for _ in range(200)]

    assert all(in_roi(point, roi_back) for point in points)


def spread_at_count(roi, count, samples=200, name='probe'):
    """把规则的点数钉在 count 上再测离散度，隔离出 shrink 本身的效果。

    直接对比"前 N 次"和"后 N 次"不可靠：shrink 在 count≈19 就触到 0.45 下限，
    前 40 次里大部分已经在收缩段，窗口比值只有 0.81 左右，掩盖了真实差异。
    """
    RuleClick.reset_task_points()
    rule = RuleClick(roi_front=roi, roi_back=roi, name=name)
    rule.coord()  # 先建立该规则的 state
    state = RuleClick._rule_state[(name, tuple(roi))]

    points = []
    for _ in range(samples):
        state['count'] = count
        points.append(rule.coord())
    return spread(points)


def test_variance_shrinks_with_click_count():
    random.seed(1)
    np.random.seed(1)
    roi = (100, 100, 400, 400)

    assert spread_at_count(roi, 120) < spread_at_count(roi, 0) * 0.7


def test_click_count_and_recent_window_grow():
    RuleClick.reset_task_points()
    rule = RuleClick(roi_front=(0, 0, 80, 60), roi_back=(0, 0, 80, 60), name='counter')

    for _ in range(5):
        rule.coord()
    state = RuleClick._rule_state[('counter', (0, 0, 80, 60))]
    assert state['count'] == 5
    assert len(state['recent']) == 5

    for _ in range(10):
        rule.coord()
    assert state['count'] == 15
    # 近期落点窗口必须有上限，否则中心会被整段历史拖住而失去"近期"的含义
    assert len(state['recent']) == RuleClick._RECENT_LIMIT


def test_humanize_false_keeps_legacy_behaviour():
    RuleClick.reset_task_points()
    random.seed(2)
    np.random.seed(2)
    roi = (10, 20, 30, 40)
    rule = RuleClick(roi_front=roi, roi_back=roi, name='legacy', humanize=False)

    points = [rule.coord() for _ in range(50)]

    assert all(in_roi(point, roi) for point in points)
    # 旧路径不参与拟人记忆，也不应污染全局上一落点
    assert not RuleClick._rule_state
    assert RuleClick._previous_point is None


def test_reset_task_points_clears_memory():
    RuleClick.reset_task_points()
    rule = RuleClick(roi_front=(0, 0, 100, 100), roi_back=(0, 0, 100, 100), name='reset')
    rule.coord()
    assert RuleClick._rule_state
    assert RuleClick._previous_point is not None

    RuleClick.reset_task_points()

    assert not RuleClick._rule_state
    assert RuleClick._previous_point is None


def test_degenerate_roi_does_not_crash():
    RuleClick.reset_task_points()
    rule = RuleClick(roi_front=(5, 6, 0, 0), roi_back=(5, 6, 0, 0), name='degenerate')

    assert rule.coord() == (5, 6)