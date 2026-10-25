"""Test cho A* (solvers/astar.py).

Phần 1 dùng đồ thị giả có trọng số để kiểm tra riêng thuật toán (độc lập engine).
Phần 2 dùng engine thật trên các màn inline của test_heuristics.py, đối chiếu với đáp án
vét cạn (Dijkstra ngược) để chắc chắn A* trả về lời giải tối ưu theo costs.py.
"""
import math

import pytest

from src.core.engine import Engine
from src.solvers.astar import AStarSolver
from src.solvers.base_solver import (
    STATUS_NO_SOLUTION,
    STATUS_NODE_LIMIT,
    STATUS_SOLVED,
    STATUS_TIMEOUT,
)
from src.solvers.bfs import BFSSolver
from src.solvers.costs import step_cost
from src.utils.json_loader import load_level
from tests.test_heuristics import INLINE_LEVELS, _write, explore, optimal_cost_to_goal


# ----------------------------------------------------------------------------------------
# Phần 1: đồ thị giả có trọng số
# ----------------------------------------------------------------------------------------
class WeightedGraphEngine:
    """edges: {state: [(action, next_state, cost), ...]}; action phải duy nhất theo từng state."""

    def __init__(self, edges, start, goals):
        self.edges = edges
        self.start = start
        self.goals = set(goals)
        self.costs = {(s, a): c for s, outs in edges.items() for a, _, c in outs}

    def initial_state(self):
        return self.start

    def get_successors(self, state):
        return [(a, n) for a, n, _ in self.edges.get(state, [])]

    def is_goal(self, state):
        return state in self.goals


def graph_cost(engine, state, action, next_state):
    return engine.costs[(state, action)]


def table_h(table):
    return lambda engine, state: table.get(state, 0.0)


def zero_h(engine, state):
    return 0.0


def solver(engine, h=zero_h, **kw):
    return AStarSolver(engine, cost_fn=graph_cost, heuristic_fn=h, **kw)


def cheap_but_long_graph():
    # A -> G trực tiếp (1 bước, chi phí 10) so với A -> B -> C -> G (3 bước, chi phí 3)
    return WeightedGraphEngine(
        {
            "A": [("direct", "G", 10.0), ("b", "B", 1.0)],
            "B": [("c", "C", 1.0)],
            "C": [("g", "G", 1.0)],
        },
        start="A",
        goals=["G"],
    )


def test_astar_finds_cheapest_path_not_shortest():
    result = solver(cheap_but_long_graph()).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == ["b", "c", "g"]
    assert result.states == ["A", "B", "C", "G"]
    assert result.solution_length == 3
    assert result.total_cost == 3.0
    assert result.algorithm == "astar"


def test_bfs_with_cost_fn_reports_real_cost_of_its_path():
    """BFS tìm đường ít bước nhất, nhưng total_cost phải tính theo hàm chi phí thật."""
    bfs = BFSSolver(cheap_but_long_graph(), cost_fn=graph_cost).solve()

    assert bfs.solution_length == 1
    assert bfs.total_cost == 10.0
    assert BFSSolver(cheap_but_long_graph()).solve().total_cost == 1.0   # cost_fn=None: đếm bước


def test_astar_reopens_nodes_when_heuristic_is_admissible_but_inconsistent():
    # S->X (3), S->Y (1), Y->X (1), X->G (5). h(Y)=6 > c(Y,X)+h(X)=1: không consistent.
    engine = WeightedGraphEngine(
        {
            "S": [("sx", "X", 3.0), ("sy", "Y", 1.0)],
            "Y": [("yx", "X", 1.0)],
            "X": [("xg", "G", 5.0)],
        },
        start="S",
        goals=["G"],
    )
    h = table_h({"S": 0.0, "Y": 6.0, "X": 0.0, "G": 0.0})    # admissible: h* = 7, 6, 5, 0
    result = solver(engine, h).solve()

    assert result.total_cost == 7.0                  # nếu không mở lại X sẽ ra 8 (S->X->G)
    assert result.states == ["S", "Y", "X", "G"]
    assert result.expanded_nodes == 4                # S, X, Y, rồi X lần hai với g tốt hơn


def test_astar_prunes_states_with_infinite_heuristic():
    engine = WeightedGraphEngine(
        {"S": [("dead", "D", 1.0), ("ok", "G", 5.0)], "D": [("loop", "D2", 1.0)]},
        start="S",
        goals=["G"],
    )
    result = solver(engine, table_h({"D": math.inf, "D2": math.inf})).solve()

    assert result.status == STATUS_SOLVED
    assert result.expanded_nodes == 1                # chỉ S; ngõ cụt D không bao giờ được mở rộng


def test_astar_infinite_heuristic_at_start_means_no_solution():
    engine = WeightedGraphEngine({"S": [("a", "G", 1.0)]}, start="S", goals=["G"])
    result = solver(engine, table_h({"S": math.inf})).solve()

    assert result.status == STATUS_NO_SOLUTION
    assert result.expanded_nodes == 0
    assert result.total_cost == math.inf


def test_astar_start_is_goal():
    engine = WeightedGraphEngine({"A": [("x", "B", 1.0)]}, start="A", goals=["A"])
    result = solver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == [] and result.states == ["A"]
    assert result.expanded_nodes == 0
    assert result.total_cost == 0.0


def test_astar_no_solution():
    engine = WeightedGraphEngine({"A": [("x", "B", 1.0)], "B": []}, start="A", goals=["Z"])
    result = solver(engine).solve()

    assert result.status == STATUS_NO_SOLUTION
    assert result.path == [] and result.states == []
    assert result.expanded_nodes == 2
    assert result.total_cost == math.inf


def test_astar_handles_cycles():
    engine = WeightedGraphEngine(
        {"A": [("x", "B", 1.0)], "B": [("y", "A", 1.0), ("z", "C", 1.0)], "C": [("w", "G", 1.0)]},
        start="A",
        goals=["G"],
    )
    result = solver(engine).solve()

    assert result.path == ["x", "z", "w"]
    assert result.total_cost == 3.0


def chain_engine(n):
    edges = {i: [("n", i + 1, 1.0)] for i in range(n)}
    return WeightedGraphEngine(edges, start=0, goals=[n])


def test_astar_node_limit_exactly_enough():
    # chuỗi 0 -> 1 -> 2 -> 3 -> 4(goal) cần đúng 4 lần mở rộng
    assert solver(chain_engine(4), node_limit=4).solve().status == STATUS_SOLVED
    limited = solver(chain_engine(4), node_limit=3).solve()
    assert limited.status == STATUS_NODE_LIMIT
    assert limited.expanded_nodes == 3
    assert limited.total_cost == math.inf


def test_astar_timeout():
    result = solver(chain_engine(100), time_limit=0.0).solve()
    assert result.status == STATUS_TIMEOUT
    assert result.path == []


def test_astar_exact_heuristic_expands_only_the_optimal_path():
    engine = WeightedGraphEngine(
        {
            "S": [("good", "A", 1.0), ("bad1", "X", 1.0), ("bad2", "Y", 1.0)],
            "A": [("g", "G", 1.0)],
            "X": [("x2", "X2", 1.0)],
            "Y": [("y2", "Y2", 1.0)],
        },
        start="S",
        goals=["G"],
    )
    exact = table_h({"S": 2.0, "A": 1.0, "G": 0.0, "X": 5.0, "Y": 5.0, "X2": 5.0, "Y2": 5.0})
    informed = solver(engine, exact).solve()
    blind = solver(engine, zero_h).solve()

    assert informed.total_cost == blind.total_cost == 2.0
    assert informed.expanded_nodes < blind.expanded_nodes


def test_astar_needs_explicit_heuristic_for_non_bloxorz_engine():
    with pytest.raises(ValueError):
        AStarSolver(chain_engine(2))      # engine giả không có `level` và không có heuristic_fn


def test_astar_rejects_non_positive_step_cost():
    engine = WeightedGraphEngine({"A": [("x", "G", 0.0)]}, start="A", goals=["G"])
    with pytest.raises(ValueError):
        solver(engine).solve()


# ----------------------------------------------------------------------------------------
# Phần 2: engine thật, đối chiếu với đáp án vét cạn
# ----------------------------------------------------------------------------------------
@pytest.fixture(params=sorted(INLINE_LEVELS), ids=sorted(INLINE_LEVELS))
def engine(request, tmp_path):
    return Engine(load_level(_write(tmp_path, INLINE_LEVELS[request.param])))


def replay_cost(engine, path):
    """Phát lại path trên engine, trả (state cuối, tổng chi phí)."""
    state, total = engine.initial_state(), 0.0
    for action in path:
        nxt = dict((a, n) for a, n in engine.get_successors(state)).get(action)
        assert nxt is not None, f"action {action} không hợp lệ tại {state}"
        total += step_cost(engine, state, action, nxt)
        state = nxt
    return state, total


def test_astar_returns_the_optimal_cost(engine):
    seen, edges = explore(engine)
    optimal = optimal_cost_to_goal(engine, seen, edges)[engine.initial_state()]

    result = AStarSolver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.total_cost == pytest.approx(optimal)
    assert len(result.states) == len(result.path) + 1
    final_state, cost = replay_cost(engine, result.path)
    assert engine.is_goal(final_state)
    assert cost == pytest.approx(result.total_cost)
    assert final_state == result.states[-1]


def test_astar_measure_memory_flag(engine):
    assert AStarSolver(engine).solve(measure_memory=True).peak_memory > 0
    assert AStarSolver(engine).solve(measure_memory=False).peak_memory == 0


def test_heuristic_reduces_expansions_overall(tmp_path):
    informed = blind = 0
    for name, data in INLINE_LEVELS.items():
        eng = Engine(load_level(_write(tmp_path, data, f"{name}.json")))
        informed += AStarSolver(eng).solve().expanded_nodes
        blind += AStarSolver(eng, heuristic_fn=lambda e, s: 0.0).solve().expanded_nodes
    assert informed < blind


def test_astar_matches_ucs_cost_when_ucs_is_available(engine):
    ucs_module = pytest.importorskip("src.solvers.ucs")
    ucs = ucs_module.UCSSolver(engine, cost_fn=step_cost).solve()
    astar = AStarSolver(engine).solve()

    assert ucs.status == astar.status == STATUS_SOLVED
    assert astar.total_cost == pytest.approx(ucs.total_cost)
