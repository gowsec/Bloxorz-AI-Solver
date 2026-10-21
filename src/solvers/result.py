from dataclasses import dataclass
from typing import List, Any


@dataclass
class SolverResult:
    algorithm: str          # Thêm thuật toán ("bfs", "dfs"...)
    path: List[Any]         # Giữ nguyên kiểu Action thật để có thể replay
    states: List[Any]
    solution_length: int    # Thêm
    total_cost: float       # Thêm
    search_time: float      # Đổi tên từ 'time'
    peak_memory: int        # Đổi kiểu về int (byte)
    expanded_nodes: int
    generated_nodes: int    # Thêm
    max_frontier: int       # Thêm
    status: str
