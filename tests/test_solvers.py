from src.solvers.base_solver import (
    STATUS_NO_SOLUTION,
    STATUS_NODE_LIMIT,
    STATUS_SOLVED,
    STATUS_TIMEOUT,
)
from src.solvers.bfs import BFSSolver

import pytest
import tracemalloc

class FakeGraphEngine:
    def __init__(self, edges: dict, start, goals):
        self.edges = edges
        self.start = start
        self.goals = set(goals)

    def initial_state(self):
        return self.start

    def get_successors(self, state):
        return list(self.edges.get(state, []))

    def is_goal(self, state):
        return state in self.goals


def replay(engine, start, path):
    state = start
    for action in path:
        nxt = dict(engine.get_successors(state)).get(action)
        assert nxt is not None, f"action {action} không hợp lệ tại {state}"
        state = nxt
    return state


def diamond_graph():
    return FakeGraphEngine(
        {
            "A": [("a", "B"), ("b", "C")],
            "B": [("c", "D")],
            "C": [("d", "G")],
            "D": [("e", "G")],
        },
        start="A",
        goals=["G"],
    )


def test_bfs_finds_shortest_path():
    engine = diamond_graph()
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == ["b", "d"]
    assert result.states == ["A", "C", "G"]
    
    # Kiểm tra bất biến
    assert result.solution_length == len(result.path)
    assert len(result.states) == len(result.path) + 1
    
    # Kiểm tra replay
    assert replay(engine, "A", result.path) == "G"


def test_bfs_start_is_goal():
    engine = FakeGraphEngine({"A": [("x", "B")]}, start="A", goals=["A"])
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == []
    assert result.states == ["A"]
    assert result.expanded_nodes == 0
    
    # Kiểm tra bất biến
    assert result.solution_length == 0
    assert len(result.states) == 1


def test_bfs_no_solution():
    engine = FakeGraphEngine({"A": [("x", "B")], "B": []}, start="A", goals=["Z"])
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_NO_SOLUTION
    assert result.path == []
    assert result.states == []
    assert result.expanded_nodes == 2
    
    # Kiểm tra bất biến vô nghiệm
    assert result.solution_length == 0


def test_bfs_handles_cycles():
    engine = FakeGraphEngine(
        {"A": [("x", "B")], "B": [("y", "A"), ("z", "C")], "C": [("w", "G")]},
        start="A",
        goals=["G"],
    )
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == ["x", "z", "w"]
    assert result.solution_length == 3


def test_bfs_counters():
    result = BFSSolver(diamond_graph()).solve()
    assert result.algorithm == "bfs"    # Thêm dòng này
    assert result.expanded_nodes == 4
    assert result.generated_nodes == 5
    assert result.max_frontier == 2
    assert result.peak_memory > 0
    assert result.search_time >= 0

@pytest.mark.skipif(tracemalloc.is_tracing(), reason="tracemalloc đã bật từ bên ngoài")
def test_tracemalloc_is_stopped_after_solve():
    BFSSolver(diamond_graph()).solve()
    assert not tracemalloc.is_tracing()


def test_bfs_limit_reached():
    chain = {i: [("n", i + 1)] for i in range(100)}
    engine = FakeGraphEngine(chain, start=0, goals=[100])
    
    # Truyền node_limit thay vì max_expanded
    result = BFSSolver(engine, node_limit=10).solve()

    assert result.status == STATUS_NODE_LIMIT
    assert result.path == []
    assert result.expanded_nodes == 10
    assert result.solution_length == 0


def test_bfs_timeout():
    chain = {i: [("n", i + 1)] for i in range(100)}
    engine = FakeGraphEngine(chain, start=0, goals=[100])
    
    # Đặt time_limit cực nhỏ để ép văng timeout
    result = BFSSolver(engine, time_limit=0.0).solve()

    assert result.status == STATUS_TIMEOUT
    assert result.path == []
    assert result.solution_length == 0

# Test xác nhận thời gian sạch (không chạy tracemalloc)
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="tracemalloc đã bật từ bên ngoài")
def test_bfs_measure_memory_off_does_not_start_tracemalloc():
    BFSSolver(diamond_graph()).solve(measure_memory=False)
    assert not tracemalloc.is_tracing()

# Test check lệch 1 node
def test_bfs_node_limit_exactly_enough():
    # diamond_graph cần đúng 4 lần mở rộng
    assert BFSSolver(diamond_graph(), node_limit=4).solve().status == STATUS_SOLVED
    assert BFSSolver(diamond_graph(), node_limit=3).solve().status == STATUS_NODE_LIMIT

# Vá lỗi fail oan cho 2 test tracemalloc
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="tracemalloc đã bật từ bên ngoài")
def test_peak_memory_when_tracemalloc_already_running():
    tracemalloc.start()
    try:
        result = BFSSolver(diamond_graph()).solve(measure_memory=True)
        assert result.peak_memory > 0
        assert tracemalloc.is_tracing() 
    finally:
        tracemalloc.stop()

@pytest.mark.skipif(tracemalloc.is_tracing(), reason="tracemalloc đã bật từ bên ngoài")
def test_tracemalloc_stopped_even_when_limit_hit():
    chain = {i: [("n", i + 1)] for i in range(100)}
    engine = FakeGraphEngine(chain, start=0, goals=[100])
    BFSSolver(engine, node_limit=5).solve()
    assert not tracemalloc.is_tracing()

def test_bfs_measure_memory_flag():
    engine = diamond_graph()
    
    # Chạy với cờ tắt đo lường memory
    result = BFSSolver(engine).solve(measure_memory=False)

    assert result.peak_memory == 0
    assert result.search_time >= 0
    assert result.status == STATUS_SOLVED

def test_unsolved_total_cost_is_inf():
    engine = FakeGraphEngine({"A": [("x", "B")], "B": []}, start="A", goals=["Z"])
    assert BFSSolver(engine).solve().total_cost == float("inf")

def test_peak_memory_positive_when_measured():
    assert BFSSolver(diamond_graph()).solve().peak_memory > 0
