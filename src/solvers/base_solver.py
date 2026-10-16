import time
import tracemalloc
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from src.solvers.result import SolverResult

STATUS_SOLVED = "solved"
STATUS_NO_SOLUTION = "no_solution"
STATUS_LIMIT = "limit_reached"


@dataclass
class Stats:
    expanded_nodes: int = 0    
    generated_nodes: int = 0   
    max_frontier: int = 0      
    time: float = 0.0          
    peak_memory: float = 0.0   

    def on_expand(self) -> None:
        self.expanded_nodes += 1

    def on_generate(self, n: int = 1) -> None:
        self.generated_nodes += n

    def track_frontier(self, size: int) -> None:
        if size > self.max_frontier:
            self.max_frontier = size


def action_to_str(action: Any) -> str:
    direction = getattr(action, "direction", None)
    if direction is None:
        return str(action)
    name = getattr(direction, "name", str(direction))
    cube = getattr(action, "cube", None)
    return name if cube is None else f"{name}:{cube}"

class BaseSolver(ABC):
    name = "base"

    def __init__(
        self,
        engine: Any,
        max_expanded: Optional[int] = None,
        time_limit: Optional[float] = None,
    ):
        self.engine = engine
        self.max_expanded = max_expanded
        self.time_limit = time_limit
        self._deadline: Optional[float] = None

    @abstractmethod
    def _search(self, start: Any, stats: Stats) -> Optional[tuple[list[Any], list[Any]]]:
        raise NotImplementedError

    def limit_exceeded(self, stats: Stats) -> bool:
        if self.max_expanded is not None and stats.expanded_nodes >= self.max_expanded:
            return True
        return self._deadline is not None and time.perf_counter() > self._deadline

    def solve(self, start: Any = None) -> SolverResult:
        if start is None:
            start = self.engine.initial_state()
        stats = Stats()

        was_tracing = tracemalloc.is_tracing()
        if was_tracing:
            tracemalloc.reset_peak()
            base_mem = tracemalloc.get_traced_memory()[0]
        else:
            tracemalloc.start()
            base_mem = 0

        t0 = time.perf_counter()
        self._deadline = t0 + self.time_limit if self.time_limit is not None else None
        try:
            found = self._search(start, stats)
            status = STATUS_SOLVED if found is not None else STATUS_NO_SOLUTION
        except SearchLimitReached:
            found, status = None, STATUS_LIMIT
        stats.time = time.perf_counter() - t0

        peak = tracemalloc.get_traced_memory()[1]
        if not was_tracing:
            tracemalloc.stop()
        stats.peak_memory = max(0, peak - base_mem) / (1024 * 1024)

        actions, states = found if found is not None else ([], [])
        return SolverResult(
            path=[action_to_str(a) for a in actions],
            states=states,
            time=stats.time,
            peak_memory=stats.peak_memory,
            expanded_nodes=stats.expanded_nodes,
            status=status,
        )


class SearchLimitReached(Exception):
    pass