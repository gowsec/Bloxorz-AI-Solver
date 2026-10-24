"""Uniform Cost Search.

UCS luôn mở rộng node có tổng chi phí g nhỏ nhất, nên với chi phí KHÔNG đều nó
trả về đường RẺ NHẤT theo costs.py (không nhất thiết là đường ít nước nhất như BFS).

* Hàng đợi ưu tiên: heap các phần tử (g, counter, state). `counter` tăng dần và
  duy nhất để không bao giờ so sánh State với nhau và để kết quả tái lập được.
* Trạng thái lặp: best_g[state] là chi phí nhỏ nhất đã biết. Chỉ đưa vào heap khi
  tìm được đường rẻ hơn, và bỏ qua mục cũ khi pop (lazy deletion).
* Goal test khi lấy node ra khỏi heap (bắt buộc để đảm bảo tối ưu).
"""

import heapq
import itertools
from typing import Any, Optional

from src.core.move import Action
from src.core.state import State
from src.solvers.base_solver import BaseSolver, Stats


class UCSSolver(BaseSolver):
    name = "ucs"

    def _search(self, start: State, stats: Stats) -> Optional[tuple[list[Action], list[State]]]:
        engine = self.engine
        cost_fn = self._resolve_cost_fn()

        best_g: dict[Any, float] = {start: 0.0}
        parent: dict[Any, Optional[tuple[Any, Action]]] = {start: None}
        counter = itertools.count()
        heap: list[tuple[float, int, Any]] = [(0.0, next(counter), start)]
        stats.on_generate()
        stats.track_frontier(len(heap))

        while heap:
            g, _, state = heapq.heappop(heap)
            if g > best_g[state]:
                continue  # mục cũ: state này đã được tìm thấy với chi phí rẻ hơn

            # Goal test khi lấy node ra khỏi heap.
            if engine.is_goal(state):
                return self._rebuild(parent, state)

            self.check_limits(stats)
            stats.on_expand()

            for action, nxt in engine.get_successors(state):
                step = cost_fn(engine, state, action, nxt)
                if step <= 0:
                    raise ValueError(
                        f"step_cost phải > 0 (nhận {step!r} cho {action!r}); xem costs.py"
                    )
                new_g = g + step
                if new_g < best_g.get(nxt, float("inf")):
                    best_g[nxt] = new_g
                    parent[nxt] = (state, action)
                    heapq.heappush(heap, (new_g, next(counter), nxt))
                    stats.on_generate()
            stats.track_frontier(len(heap))

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