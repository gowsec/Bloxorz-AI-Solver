from collections import deque
from typing import Any, Optional

from src.solvers.base_solver import BaseSolver, Stats


class BFSSolver(BaseSolver):
    name = "bfs"

    def _search(self, start: Any, stats: Stats) -> Optional[tuple[list[Any], list[Any]]]:
        engine = self.engine
        stats.on_generate()

        parent: dict[Any, Optional[tuple[Any, Any]]] = {start: None}
        frontier = deque([start])
        stats.track_frontier(len(frontier))

        while frontier:
            state = frontier.popleft()

            # 1. Kiểm tra đích trước
            if engine.is_goal(state):
                return self._rebuild(parent, state)
            
            self.check_limits(stats)

            # 2. Nếu không phải đích thì mới tính là "mở rộng" (expand)
            stats.on_expand()

            # 3. Sinh các trạng thái tiếp theo
            for action, nxt in engine.get_successors(state):
                if nxt in parent:
                    continue
                stats.on_generate()
                parent[nxt] = (state, action)
                frontier.append(nxt)
                
            stats.track_frontier(len(frontier))

        return None

    @staticmethod
    def _rebuild(parent: dict, goal: Any) -> tuple[list[Any], list[Any]]:
        actions, states = [], [goal]
        node = goal
        while parent[node] is not None:
            node, action = parent[node]
            actions.append(action)
            states.append(node)
        actions.reverse()
        states.reverse()
        return actions, states