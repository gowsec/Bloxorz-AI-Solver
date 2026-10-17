"""Kiểm tra costs.py và heuristics.py bằng vét cạn (brute-force) trên các màn nhỏ.

Với mỗi màn, test:
  1. Duyệt hết không gian trạng thái đạt tới được từ trạng thái đầu.
  2. Tính h*(s) = chi phí tối ưu thật từ s tới goal (Dijkstra ngược trên đồ thị đó).
  3. Admissible: h(s) <= h*(s) với mọi s có đường tới goal.
  4. Consistent: h(s) <= c(s, s') + h(s') với MỌI cạnh (s, s').
Các màn inline bên dưới được chọn từ bộ sinh ngẫu nhiên, mỗi màn có lời giải và đủ lớn
(45 đến 556 trạng thái) để thực sự thử heuristic: màn thường, ô dễ vỡ, cầu + công tắc,
công tắc split kèm cầu và ô dễ vỡ, và một màn mà split là đường duy nhất tới goal. Thêm cả mọi file levels/level*.json nếu đủ nhỏ.
"""
import dataclasses
import heapq
import itertools
import json
import math
from pathlib import Path

import pytest

from src.core.engine import Engine
from src.core.state import BlockPose, cells
from src.solvers.costs import BASE_COST, C_MIN, FRAGILE_PENALTY, FRAGILE_TILE, step_cost
from src.solvers.heuristics import heuristic
from src.utils.json_loader import load_level

EPS = 1e-9
STATE_CAP = 200_000

INLINE_LEVELS = {
    "plain": {
        "name": "plain",
        "grid": ["S###G#.", "###..##", "##.####", "#######"],
        "bridges": [],
        "switches": [],
    },
    "fragile": {
        "name": "fragile",
        "grid": ["..#.#.F", "##SF#.F", "F#FFG#.", "#F.####", "####F##"],
        "bridges": [],
        "switches": [],
    },
    "bridge": {
        "name": "bridge",
        "grid": ["#.####", ".##...", "S#####", "####G#"],
        "bridges": [
            {"id": 0, "pos": [1, 0], "initial_open": True},
            {"id": 1, "pos": [1, 4], "initial_open": False},
        ],
        "switches": [
            {"pos": [0, 5], "type": "heavy", "effect": {"mode": "toggle", "bridges": [0]}},
        ],
    },
    "split_bridge_fragile": {
        "name": "split_bridge_fragile",
        "grid": ["#.##G", "S###.", "#####", "FFF#."],
        "bridges": [{"id": 0, "pos": [0, 1], "initial_open": False}],
        "switches": [
            {"pos": [2, 3], "type": "soft", "effect": {"mode": "toggle", "bridges": [0]}},
            {"pos": [2, 4], "type": "split", "split_targets": [[0, 3], [3, 3]]},
        ],
    },
    "split_shortcut": {
        # Goal KHÔNG tới được nếu chỉ lăn khối nguyên: bắt buộc phải qua công tắc split.
        # Test này bắt lỗi "heuristic quên tính đường tắt của split" (sẽ trả h = vô cực).
        "name": "split_shortcut",
        "grid": ["...##", "#####", ".#.S#", "#G..#"],
        "bridges": [
            {"id": 0, "pos": [2, 2], "initial_open": True},
            {"id": 1, "pos": [0, 0], "initial_open": False},
            {"id": 2, "pos": [0, 1], "initial_open": False},
        ],
        "switches": [
            {"pos": [1, 3], "type": "soft", "effect": {"mode": "set_close", "bridges": [0, 1, 2]}},
            {"pos": [0, 4], "type": "heavy", "effect": {"mode": "set_open", "bridges": [1, 0]}},
            {"pos": [1, 0], "type": "split", "split_targets": [[1, 4], [3, 0]]},
        ],
    },
}

LEVEL_FILES = sorted((Path(__file__).parent.parent / "levels").glob("level*.json"))


def _write(tmp_path, data, name="level.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture(params=sorted(INLINE_LEVELS), ids=sorted(INLINE_LEVELS))
def inline_engine(request, tmp_path):
    return Engine(load_level(_write(tmp_path, INLINE_LEVELS[request.param])))


def explore(engine):
    """Trả (tập state đạt tới được, danh sách cạnh (s, s', cost)). Skip nếu quá lớn."""
    start = engine.initial_state()
    seen, stack, edges = {start}, [start], []
    while stack:
        s = stack.pop()
        for action, nxt in engine.get_successors(s):
            edges.append((s, nxt, step_cost(engine, s, action, nxt)))
            if nxt not in seen:
                if len(seen) >= STATE_CAP:
                    pytest.skip("không gian trạng thái quá lớn để vét cạn")
                seen.add(nxt)
                stack.append(nxt)
    return seen, edges


def optimal_cost_to_goal(engine, seen, edges):
    """h*(s) cho mọi s có đường tới goal (Dijkstra ngược từ các state goal)."""
    reverse = {}
    for s, nxt, cost in edges:
        reverse.setdefault(nxt, []).append((s, cost))
    dist = {s: 0.0 for s in seen if engine.is_goal(s)}
    tie = itertools.count()
    heap = [(0.0, next(tie), s) for s in dist]
    heapq.heapify(heap)
    while heap:
        d, _, node = heapq.heappop(heap)
        if d > dist[node]:
            continue
        for prev, cost in reverse.get(node, ()):
            if d + cost < dist.get(prev, math.inf):
                dist[prev] = d + cost
                heapq.heappush(heap, (d + cost, next(tie), prev))
    return dist


def check_heuristic(engine):
    seen, edges = explore(engine)
    h = {s: heuristic(engine, s) for s in seen}
    h_star = optimal_cost_to_goal(engine, seen, edges)

    assert engine.initial_state() in h_star, "màn kiểm thử phải có lời giải"
    for s, true_cost in h_star.items():
        assert h[s] <= true_cost + EPS, f"overestimate tại {s}: h={h[s]} > h*={true_cost}"
    for s, nxt, cost in edges:
        assert h[s] <= cost + h[nxt] + EPS, f"không consistent: {s} -> {nxt}"
    for s in seen:
        if engine.is_goal(s):
            assert h[s] == 0
    return seen, edges


def test_heuristic_admissible_and_consistent_inline(inline_engine):
    check_heuristic(inline_engine)


@pytest.mark.parametrize("path", LEVEL_FILES, ids=lambda p: p.name)
def test_heuristic_admissible_and_consistent_level_files(path):
    check_heuristic(Engine(load_level(path)))


def test_heuristic_is_computed_once_per_engine(inline_engine):
    s = inline_engine.initial_state()
    heuristic(inline_engine, s)
    table = inline_engine._heuristic_table
    heuristic(inline_engine, s)
    assert inline_engine._heuristic_table is table


def test_step_cost_follows_cost_model(inline_engine):
    seen, edges = explore(inline_engine)
    terrain = inline_engine.level.terrain
    for s, nxt, cost in edges:
        on_fragile = isinstance(nxt.pose, BlockPose) and any(
            terrain[r][c] == FRAGILE_TILE for r, c in cells(nxt.pose)
        )
        expected = BASE_COST + (FRAGILE_PENALTY if on_fragile else 0.0)
        assert cost == pytest.approx(expected), f"{s} -> {nxt}"
        assert cost >= C_MIN


def test_step_cost_ignores_bridge_state(inline_engine):
    """Heuristic dựa vào việc chi phí chỉ phụ thuộc tư thế mới, không phụ thuộc cầu."""
    seen, edges = explore(inline_engine)
    for s, nxt, cost in edges[:200]:
        other = dataclasses.replace(nxt, bridges=nxt.bridges ^ 0b1)
        action = next(a for a, n in inline_engine.get_successors(s) if n == nxt)
        assert step_cost(inline_engine, s, action, other) == cost


def test_fragile_level_has_non_uniform_costs(tmp_path):
    """UCS chỉ khác BFS khi chi phí không đồng nhất: phải có cả cạnh giá 1 và giá 2."""
    engine = Engine(load_level(_write(tmp_path, INLINE_LEVELS["fragile"])))
    _, edges = explore(engine)
    assert {cost for _, _, cost in edges} == {BASE_COST, BASE_COST + FRAGILE_PENALTY}


def test_cost_constants_are_sane():
    assert BASE_COST > 0 and FRAGILE_PENALTY >= 0
    assert C_MIN == BASE_COST
