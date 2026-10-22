"""DFS

Cả hai dùng stack tường minh (không đệ quy) nên không bị giới hạn độ sâu đệ quy
của Python. Hành động được thử theo đúng thứ tự engine trả về (UP, DOWN, LEFT,
RIGHT; khối 0 trước khối 1), nên kết quả tái lập được.

* DFSSolver ("dfs"): visited toàn cục. Nhanh, ít bộ nhớ, nhưng lời giải KHÔNG
  đảm bảo ngắn nhất.
"""

from typing import Optional

from src.core.move import Action
from src.core.state import State
from src.solvers.base_solver import BaseSolver, Stats


def _rebuild_path(
    parent: dict[State, Optional[tuple[State, Action]]], goal: State
) -> tuple[list[Action], list[State]]:
    """Dựng (actions, states) từ goal ngược về start theo con trỏ cha."""
    actions: list[Action] = []
    states: list[State] = [goal]
    node = goal
    while parent[node] is not None:
        node, action = parent[node]
        actions.append(action)
        states.append(node)
    actions.reverse()
    states.reverse()
    return actions, states


class DFSSolver(BaseSolver):
    name = "dfs"

    def _search(self, start: State, stats: Stats) -> Optional[tuple[list[Action], list[State]]]:
        engine = self.engine

        # Trạng thái lặp: visited toàn cục, đánh dấu khi đưa vào stack
        # (khớp định nghĩa "generated = đưa vào frontier").
        parent: dict[State, Optional[tuple[State, Action]]] = {start: None}
        stack: list[State] = [start]
        stats.on_generate()
        stats.track_frontier(len(stack))

        while stack:
            state = stack.pop()

            if engine.is_goal(state):
                return _rebuild_path(parent, state)

            self.check_limits(stats)
            stats.on_expand()

            # Đẩy theo thứ tự ngược để hành động đầu tiên được pop trước.
            for action, nxt in reversed(engine.get_successors(state)):
                if nxt in parent:
                    continue
                parent[nxt] = (state, action)
                stack.append(nxt)
                stats.on_generate()
            stats.track_frontier(len(stack))

        return None


