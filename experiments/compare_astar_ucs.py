"""So sánh hiệu năng A* với UCS (và tùy chọn BFS) trên các màn trong levels/.

Cách chạy (từ thư mục gốc của repo):
    python -m experiments.compare_astar_ucs
    python -m experiments.compare_astar_ucs --levels "levels/level0*.json" --repeats 7 --with-bfs

Quy trình đo (theo kiến trúc mục 6.3):
  * Lượt đo THỜI GIAN: chạy `--repeats` lần với measure_memory=False, lấy trung vị.
  * Lượt đo BỘ NHỚ: một lần với measure_memory=True (tracemalloc làm chậm nên không lấy
    thời gian từ lượt này).
  * Mọi solver dùng cùng một hàm chi phí (costs.step_cost), nên total_cost so sánh được.
  * Bảng heuristic của A* được tính lại mỗi lần chạy và đã nằm trong thời gian và bộ nhớ.

Kết quả ghi ra CSV (mặc định experiments/results/astar_vs_ucs.csv) và in bảng tóm tắt.
Thoát với mã 1 nếu A* và UCS cho chi phí khác nhau trên một màn nào đó (dấu hiệu lỗi).
"""
from __future__ import annotations

import argparse
import csv
import glob
import statistics
import sys
import time
from pathlib import Path

from src.core.engine import Engine
from src.solvers.astar import AStarSolver
from src.solvers.base_solver import STATUS_NO_SOLUTION, STATUS_SOLVED
from src.solvers.bfs import BFSSolver
from src.solvers.costs import step_cost
from src.solvers.heuristics import HeuristicTable
from src.utils.json_loader import load_level

try:
    from src.solvers.ucs import UCSSolver
except ImportError:  # UCS do D cài đặt
    UCSSolver = None

CSV_COLUMNS = [
    "level", "algorithm", "status", "solution_length", "total_cost",
    "expanded_nodes", "generated_nodes", "max_frontier", "search_time_median", "peak_memory",
]


def measure(make_solver, repeats):
    """Trả (kết quả của lượt đo bộ nhớ, trung vị thời gian của lượt đo thời gian)."""
    times = []
    for _ in range(repeats):
        result = make_solver().solve(measure_memory=False)
        times.append(result.search_time)
        if result.status not in (STATUS_SOLVED, STATUS_NO_SOLUTION):
            break                                   # hết giờ/quá node: lặp lại cũng vô ích
    return make_solver().solve(measure_memory=True), statistics.median(times)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--levels", default="levels/level*.json", help="glob các file màn chơi")
    parser.add_argument("--repeats", type=int, default=5, help="số lần chạy cho lượt đo thời gian")
    parser.add_argument("--time-limit", type=float, default=60.0, help="giây cho mỗi lần giải")
    parser.add_argument("--node-limit", type=int, default=None)
    parser.add_argument("--with-bfs", action="store_true", help="đưa thêm BFS vào bảng")
    parser.add_argument("--out", default="experiments/results/astar_vs_ucs.csv")
    args = parser.parse_args(argv)

    if UCSSolver is None:
        print("Chưa có src/solvers/ucs.py (UCSSolver). Cần UCS của D để so sánh.", file=sys.stderr)
        return 2
    paths = sorted(glob.glob(args.levels))
    if not paths:
        print(f"Không tìm thấy màn nào khớp: {args.levels}", file=sys.stderr)
        return 2

    limits = dict(node_limit=args.node_limit, time_limit=args.time_limit)
    solvers = {"ucs": UCSSolver, "astar": AStarSolver}
    if args.with_bfs:
        solvers = {"bfs": BFSSolver, **solvers}

    rows, mismatches, comparison = [], [], []
    for path in paths:
        name = Path(path).stem
        level = load_level(path)
        engine = Engine(level)

        t0 = time.perf_counter()
        HeuristicTable(level)
        precompute_ms = (time.perf_counter() - t0) * 1000

        per_level = {}
        for algo, cls in solvers.items():
            result, median_time = measure(lambda cls=cls: cls(engine, cost_fn=step_cost, **limits), args.repeats)
            per_level[algo] = (result, median_time)
            rows.append({
                "level": name, "algorithm": algo, "status": result.status,
                "solution_length": result.solution_length, "total_cost": result.total_cost,
                "expanded_nodes": result.expanded_nodes, "generated_nodes": result.generated_nodes,
                "max_frontier": result.max_frontier, "search_time_median": median_time,
                "peak_memory": result.peak_memory,
            })

        (u, u_time), (a, a_time) = per_level["ucs"], per_level["astar"]
        if u.status == a.status == STATUS_SOLVED and abs(u.total_cost - a.total_cost) > 1e-9:
            mismatches.append((name, u.total_cost, a.total_cost))
        comparison.append((name, u, u_time, a, a_time, precompute_ms))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    header = (f"{'level':<12}{'status':<12}{'cost UCS':>9}{'cost A*':>9}{'exp UCS':>9}{'exp A*':>8}"
              f"{'A*/UCS':>8}{'ms UCS':>9}{'ms A*':>8}{'KB UCS':>9}{'KB A*':>8}{'h-table ms':>11}")
    print(header)
    print("-" * len(header))
    for name, u, u_time, a, a_time, pre in comparison:
        ratio = a.expanded_nodes / u.expanded_nodes if u.expanded_nodes else float("nan")
        print(f"{name:<12}{a.status:<12}{u.total_cost:>9.1f}{a.total_cost:>9.1f}{u.expanded_nodes:>9}"
              f"{a.expanded_nodes:>8}{ratio:>8.2f}{u_time * 1000:>9.2f}{a_time * 1000:>8.2f}"
              f"{u.peak_memory / 1024:>9.1f}{a.peak_memory / 1024:>8.1f}{pre:>11.2f}")
    print(f"\nĐã ghi {len(rows)} dòng vào {out}")

    if mismatches:
        for name, cu, ca in mismatches:
            print(f"CẢNH BÁO: {name}: chi phí UCS = {cu}, A* = {ca} (phải bằng nhau)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
