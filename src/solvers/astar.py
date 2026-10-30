"""Thuật toán A*.

f(n) = g(n) + h(n), trong đó
  * g(n): tổng chi phí đã đi, tính bằng `cost_fn` (mặc định `costs.step_cost`);
  * h(n): heuristic admissible và consistent từ `heuristics.py`.

Quy ước thống nhất với BFS/UCS (kiến trúc mục 6.3):
  * goal test khi LẤY node ra khỏi hàng đợi (bắt buộc để A* tối ưu);
  * `check_limits` gọi ngay trước khi mở rộng node, sau goal test;
  * expanded: mỗi lần `get_successors` được gọi trên một node không phải goal;
  * generated: mỗi lần một state được đẩy vào hàng đợi (kể cả khi đẩy lại với g tốt hơn).

Chi tiết cài đặt:
  * Xóa lười (lazy deletion): không sửa key trong heap, mục cũ bị bỏ qua khi `g > best_g`.
  * Cho phép mở lại node: nếu tìm được g nhỏ hơn thì đẩy lại. Với heuristic consistent việc
    này không bao giờ xảy ra, nhưng giữ lại để A* vẫn tối ưu với heuristic chỉ admissible.
  * Hòa f: ưu tiên h nhỏ hơn (sâu hơn), rồi tới thứ tự đẩy vào để kết quả tái lập được.
  * State có h = vô cực (chắc chắn không tới được goal) bị loại ngay, không vào hàng đợi.
  * Bảng heuristic được tính lại ở MỖI lần `solve()` và nằm trong `search_time` và
    `peak_memory`, để so sánh với UCS công bằng (UCS không có bước tính trước).
"""
from __future__ import annotations

import heapq
import itertools
import math
from typing import Any, Callable, Optional

from src.solvers.base_solver import BaseSolver, Stats
from src.solvers.heuristics import HeuristicTable


class AStarSolver(BaseSolver):
    name = "astar"

    def __init__(
        self,
        engine: Any,
        node_limit: Optional[int] = None,
        time_limit: Optional[float] = None,
        cost_fn: Optional[Callable[[Any, Any, Any, Any], float]] = None,
        heuristic_fn: Optional[Callable[[Any, Any], float]] = None,
    ):
        """cost_fn: như UCS (None -> costs.step_cost với engine Bloxorz, xem BaseSolver).

        heuristic_fn(engine, state) -> float. None: dùng HeuristicTable của heuristics.py,
        chỉ admissible khi cost_fn là costs.step_cost. Nếu đổi cost_fn thì phải đổi cả heuristic.
        """
        super().__init__(engine, node_limit=node_limit, time_limit=time_limit, cost_fn=cost_fn)
        if heuristic_fn is None and not hasattr(engine, "level"):
            raise ValueError("Engine không có `level`: cần truyền heuristic_fn cho A*")
        self.heuristic_fn = heuristic_fn

    def _make_heuristic(self) -> Callable[[Any], float]:
        if self.heuristic_fn is not None:
            fn = self.heuristic_fn
            return lambda state: fn(self.engine, state)
        return HeuristicTable(self.engine.level)  # tính trước, tra O(1)

    def _search(self, start: Any, stats: Stats) -> Optional[tuple[list[Any], list[Any]]]:
        engine = self.engine
        cost_fn = self._resolve_cost_fn()
        h = self._make_heuristic()

        h0 = h(start)
        if h0 == math.inf:      # heuristic admissible nên h = inf nghĩa là vô nghiệm thật sự
            return None

        tie = itertools.count()
        best_g: dict[Any, float] = {start: 0.0}
        parent: dict[Any, Optional[tuple[Any, Any]]] = {start: None}
        frontier = [(h0, h0, next(tie), 0.0, start)]    # (f, h, thứ tự đẩy, g, state)
        stats.on_generate()
        stats.track_frontier(len(frontier))

        while frontier:
            _, _, _, g, state = heapq.heappop(frontier)
            if g > best_g[state]:
                continue                                  # mục cũ, đã có đường tốt hơn

            if engine.is_goal(state):
                return self._rebuild(parent, state)

            self.check_limits(stats)                      # ngay trước khi mở rộng
            stats.on_expand()

            for action, nxt in engine.get_successors(state):
                step = cost_fn(engine, state, action, nxt)
                if step <= 0:
                    raise ValueError(
                        f"step_cost phải > 0 (nhận {step!r} cho {action!r}); xem costs.py"
                    )
                new_g = g + step
                if new_g >= best_g.get(nxt, math.inf):
                    continue
                hn = h(nxt)
                if hn == math.inf:
                    continue                              # ngõ cụt chắc chắn
                best_g[nxt] = new_g
                parent[nxt] = (state, action)
                heapq.heappush(frontier, (new_g + hn, hn, next(tie), new_g, nxt))
                stats.on_generate()
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
