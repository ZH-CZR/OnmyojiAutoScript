# This Python file uses the following encoding: utf-8
"""百鬼棋局「是否确定离开游戏？」弹窗守卫回归测试。

背景
----
2026-11-24 08:56 实例 `一叶禅心(笔记本)`：对局第 5 回合选择符咒时，屏幕上
覆盖着一个误触返回键弹出的退出确认框。标题「选择一个符咒」仍在弹窗上方
可见，`I_SELECT_GRIGRI` 继续命中，于是 `select_grigri` 每秒点一次
`grigri_option_3`，点击全部被模态框吞掉，10 次后触发
``GameTooManyClickError: Too many click for a button: grigri_option_3``。

同一份日志里商店反复 `Chess shop failed to close before timeout`，也是被
该弹窗遮挡导致点击无效。

修复原则：退出流程（`exit_chess_battle`）点「确定」；其余任何流程检测到
弹窗一律点「取消」，保留当前对局，避免吞掉后续点击。
"""
import ast
import unittest
from pathlib import Path

from tasks.GameUi.chess_battle import ChessBattleNavigationMixin

REPO = Path(__file__).resolve().parent.parent
ROUND_STATE = REPO / 'tasks' / 'Chess' / 'runtime' / 'round_state.py'
ECONOMY = REPO / 'tasks' / 'Chess' / 'runtime' / 'economy.py'


class _FakeTask(ChessBattleNavigationMixin):
    """只实现守卫所需的 appear / click。"""

    def __init__(self, visible=()):
        self.I_CHESS_EXIT_CONFIRM = 'confirm'
        self.I_CHESS_EXIT_CANCEL = 'cancel'
        self.visible = set(visible)
        self.clicked = []

    def appear(self, rule):
        return rule in self.visible

    def click(self, rule):
        self.clicked.append(rule)


def _method_calls(path: Path, method_name: str, target_attr: str) -> bool:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == target_attr
                ):
                    return True
    return False


class ChessExitDialogGuardTest(unittest.TestCase):
    def test_unexpected_dialog_chooses_cancel(self):
        task = _FakeTask({'confirm', 'cancel'})
        self.assertTrue(task.dismiss_chess_exit_dialog())
        self.assertEqual(task.clicked, ['cancel'])

    def test_cancel_alone_is_enough_to_close_dialog(self):
        task = _FakeTask({'cancel'})
        self.assertTrue(task.dismiss_chess_exit_dialog())
        self.assertEqual(task.clicked, ['cancel'])

    def test_no_dialog_does_nothing(self):
        task = _FakeTask()
        self.assertFalse(task.dismiss_chess_exit_dialog())
        self.assertEqual(task.clicked, [])

    def test_exit_flow_keeps_confirm_decision(self):
        task = _FakeTask({'confirm', 'cancel'})
        task._chess_exit_flow_active = True
        self.assertFalse(task.dismiss_chess_exit_dialog())
        self.assertEqual(task.clicked, [])

    def test_grigri_selection_guards_against_dialog(self):
        self.assertTrue(
            _method_calls(ROUND_STATE, 'select_grigri', 'dismiss_chess_exit_dialog')
        )

    def test_shop_close_guards_against_dialog(self):
        self.assertTrue(
            _method_calls(ECONOMY, '_ensure_shop_closed', 'dismiss_chess_exit_dialog')
        )


if __name__ == '__main__':
    unittest.main()
