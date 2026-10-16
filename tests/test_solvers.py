from src.solvers.base_solver import STATUS_LIMIT, STATUS_NO_SOLUTION, STATUS_SOLVED
from src.solvers.bfs import BFSSolver


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
    assert replay(engine, "A", result.path) == "G"


def test_bfs_start_is_goal():
    engine = FakeGraphEngine({"A": [("x", "B")]}, start="A", goals=["A"])
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == []
    assert result.states == ["A"]
    assert result.expanded_nodes == 0


def test_bfs_no_solution():
    engine = FakeGraphEngine({"A": [("x", "B")], "B": []}, start="A", goals=["Z"])
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_NO_SOLUTION
    assert result.path == []
    assert result.states == []
    assert result.expanded_nodes == 2


def test_bfs_handles_cycles():
    engine = FakeGraphEngine(
        {"A": [("x", "B")], "B": [("y", "A"), ("z", "C")], "C": [("w", "G")]},
        start="A",
        goals=["G"],
    )
    result = BFSSolver(engine).solve()

    assert result.status == STATUS_SOLVED
    assert result.path == ["x", "z", "w"]


def test_bfs_expanded_nodes_and_stats_fields():
    result = BFSSolver(diamond_graph()).solve()

    assert result.expanded_nodes == 3
    assert result.time >= 0
    assert result.peak_memory >= 0


def test_bfs_limit_reached():
    chain = {i: [("n", i + 1)] for i in range(100)}
    engine = FakeGraphEngine(chain, start=0, goals=[100])
    result = BFSSolver(engine, max_expanded=10).solve()

    assert result.status == STATUS_LIMIT
    assert result.path == []
    assert result.expanded_nodes == 10