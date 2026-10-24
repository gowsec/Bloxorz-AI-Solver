import time
import tracemalloc
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Callable

from src.solvers.costs import step_cost
from src.solvers.result import SolverResult

STATUS_SOLVED = "solved"
STATUS_NO_SOLUTION = "no_solution"
STATUS_TIMEOUT = "timeout"
STATUS_NODE_LIMIT = "node_limit"

class SearchLimitReached(Exception):
    def __init__(self, status: str):
        self.status = status

@dataclass
class Stats:
    expanded_nodes: int = 0    
    generated_nodes: int = 0   
    max_frontier: int = 0      
    search_time: float = 0.0          
    peak_memory: int = 0   

    def on_expand(self) -> None:
        self.expanded_nodes += 1

    def on_generate(self, n: int = 1) -> None:
        self.generated_nodes += n

    def track_frontier(self, size: int) -> None:
        if size > self.max_frontier:
            self.max_frontier = size

class BaseSolver(ABC):
    name = "base"

    def __init__(
        self,
        engine: Any,
        node_limit: Optional[int] = None, # Sửa tên tham số
        time_limit: Optional[float] = None,
        cost_fn: Optional[Callable[..., float]] = None, # Thêm để viết hàm UCS
    ):
        self.engine = engine
        self.node_limit = node_limit
        self.time_limit = time_limit
        self.cost_fn = cost_fn # Thêm mới
        self._deadline: Optional[float] = None

    @abstractmethod
    def _search(self, start: Any, stats: Stats) -> Optional[tuple[list[Any], list[Any]]]:
        raise NotImplementedError

    def check_limits(self, stats: Stats) -> None:
        if self.node_limit is not None and stats.expanded_nodes >= self.node_limit:
            raise SearchLimitReached(STATUS_NODE_LIMIT)
        
        if self._deadline is not None and time.perf_counter() >= self._deadline:
            raise SearchLimitReached(STATUS_TIMEOUT)
    def _resolve_cost_fn(self) -> Callable[..., float]:
        """Hàm chi phí dùng cho UCS, A* và total_cost của mọi solver.

        Ưu tiên: cost_fn truyền vào; nếu không thì costs.step_cost cho engine Bloxorz
        (có thuộc tính `level`); engine khác (đồ thị giả trong test) tính mỗi bước 1.0.
        """
        if self.cost_fn is not None:
            return self.cost_fn
        if hasattr(self.engine, "level"):
            return step_cost
        return lambda engine, state, action, next_state: 1.0

    def _path_cost(self, states: list[Any], actions: list[Any]) -> float:
        cost_fn = self._resolve_cost_fn()
        total = 0.0
        for i, action in enumerate(actions):
            total += cost_fn(self.engine, states[i], action, states[i + 1])
        return total

    def solve(self, start: Any = None, measure_memory: bool = True) -> SolverResult:
        if start is None:
            start = self.engine.initial_state()
        stats = Stats()

        # Bóc tách rõ ràng quản lý Memory
        started_here = False
        base_mem = 0
        if measure_memory:
            if not tracemalloc.is_tracing():
                tracemalloc.start()
                started_here = True
            tracemalloc.reset_peak()
            base_mem = tracemalloc.get_traced_memory()[0]

        t0 = time.perf_counter()
        self._deadline = t0 + self.time_limit if self.time_limit is not None else None
        
        try:
            found = self._search(start, stats)
            status = STATUS_SOLVED if found is not None else STATUS_NO_SOLUTION
        except SearchLimitReached as e:
            found, status = None, e.status
        finally:
            # 1. Tính thời gian ngay khi tìm xong, tránh độ trễ của tracemalloc
            stats.search_time = time.perf_counter() - t0
            
            # 2. Đo peak memory nếu có yêu cầu
            if measure_memory:
                peak = tracemalloc.get_traced_memory()[1]
                stats.peak_memory = max(0, peak - base_mem)
                
            # 3. Chỉ tắt tracemalloc nếu HÀM NÀY là người bật nó
            if started_here:
                tracemalloc.stop()

        actions, states = found if found is not None else ([], [])
        solution_length = len(actions)
        
        # Sửa lỗi chi phí bằng 0 khi thất bại
        total_cost = self._path_cost(states, actions) if status == STATUS_SOLVED else float("inf") #Sửa lại dòng này
        
        return SolverResult(
            algorithm=self.name,
            path=actions,
            states=states,
            solution_length=solution_length,
            total_cost=total_cost,
            search_time=stats.search_time,
            peak_memory=stats.peak_memory,
            expanded_nodes=stats.expanded_nodes,
            generated_nodes=stats.generated_nodes,
            max_frontier=stats.max_frontier,
            status=status,
        )