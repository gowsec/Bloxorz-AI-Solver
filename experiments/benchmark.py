"""Benchmark các solver và ghi kết quả ra CSV (architecture v2, mục 6.3).

Mỗi cặp (màn, thuật toán) chạy HAI lượt riêng:
  1. Lượt thời gian: measure_memory=False, lặp `repeats` lần, lấy trung vị.
     tracemalloc làm chương trình chậm đi nhiều nên số liệu thời gian chỉ lấy từ lượt này.
  2. Lượt bộ nhớ: measure_memory=True, chạy một lần, lấy peak của tracemalloc
     (peak Python-tracked memory, không phải toàn bộ RAM của tiến trình).

Chạy từ thư mục gốc dự án:
    python -m experiments.benchmark
    python -m experiments.benchmark --levels "levels/*.json" --algorithms bfs,dfs \
        --repeats 5 --time-limit 60 --out experiments/results/benchmark.csv

CÁC CỘT CỦA FILE CSV (một dòng cho mỗi cặp màn x thuật toán)
------------------------------------------------------------
level              tên màn (tên file không có đuôi .json)
algorithm          bfs | dfs | ucs | A*
status             solved | no_solution | timeout | node_limit
solution_length    số nước đi của lời giải (0 nếu không có lời giải)
total_cost         tổng chi phí theo costs.py (inf nếu không có lời giải)
expanded_nodes     số node đã mở rộng
generated_nodes    số node đã đưa vào frontier
max_frontier       kích thước frontier lớn nhất
time_median_s      trung vị thời gian tìm kiếm (giây), từ lượt measure_memory=False
time_min_s         thời gian nhỏ nhất trong các lần lặp (giây)
time_max_s         thời gian lớn nhất trong các lần lặp (giây)
time_repeats       số lần lặp thực tế (1 nếu bị timeout ngay lần đầu)
peak_memory_bytes  peak tracemalloc (byte), từ lượt đo bộ nhớ; để TRỐNG nếu status = timeout
node_limit         giới hạn node đã dùng (trống nếu không giới hạn)
time_limit_s       giới hạn thời gian đã dùng (trống nếu không giới hạn)

Các cột expanded/generated/solution_length/total_cost/status lấy từ lượt đo thời gian.
Chúng không phụ thuộc thời gian nên giống hệt lượt đo bộ nhớ, trừ khi status = timeout.
"""

import argparse
import csv
import gc
import glob
import importlib
import os
import statistics
import sys
from typing import Any, Iterable, Optional

CSV_COLUMNS = [
    "level",
    "algorithm",
    "status",
    "solution_length",
    "total_cost",
    "expanded_nodes",
    "generated_nodes",
    "max_frontier",
    "time_median_s",
    "time_min_s",
    "time_max_s",
    "time_repeats",
    "peak_memory_bytes",
    "node_limit",
    "time_limit_s",
]


def available_solvers() -> dict[str, type]:
    """Các solver đã có trong dự án. UCS và A* tự xuất hiện khi file của chúng được thêm."""
    from src.solvers.bfs import BFSSolver
    from src.solvers.dfs import DFSSolver

    registry: dict[str, type] = {"bfs": BFSSolver, "dfs": DFSSolver}
    optional = (
        ("ucs", "src.solvers.ucs", "UCSSolver"),
        ("astar", "src.solvers.astar", "AStarSolver"),
    )
    for key, module, cls in optional:
        try:
            registry[key] = getattr(importlib.import_module(module), cls)
        except (ImportError, AttributeError):
            pass
    return registry


def benchmark_one(
    level_name: str,
    engine: Any,
    solver_cls: type,
    repeats: int = 5,
    node_limit: Optional[int] = None,
    time_limit: Optional[float] = None,
) -> dict[str, Any]:
    """Chạy một cặp (màn, thuật toán) và trả về một dòng CSV (dict theo CSV_COLUMNS)."""
    # Lượt 1: thời gian, không tracemalloc.
    times: list[float] = []
    result = None
    for _ in range(max(1, repeats)):
        gc.collect()
        result = solver_cls(engine, node_limit=node_limit, time_limit=time_limit).solve(
            measure_memory=False
        )
        times.append(result.search_time)
        if result.status == "timeout":
            break  # thời gian của lần chạy bị cắt không có ý nghĩa để lặp lại

    # Lượt 2: bộ nhớ, riêng biệt. Không đặt time_limit (tracemalloc làm chậm, dễ timeout giả);
    # bỏ qua nếu lượt 1 đã timeout vì khi đó không biết lượt này có kết thúc không.
    peak_memory: Any = ""
    if result.status != "timeout":
        gc.collect()
        mem_result = solver_cls(engine, node_limit=node_limit, time_limit=None).solve(
            measure_memory=True
        )
        peak_memory = mem_result.peak_memory

    return {
        "level": level_name,
        "algorithm": solver_cls.name,
        "status": result.status,
        "solution_length": result.solution_length,
        "total_cost": result.total_cost,
        "expanded_nodes": result.expanded_nodes,
        "generated_nodes": result.generated_nodes,
        "max_frontier": result.max_frontier,
        "time_median_s": statistics.median(times),
        "time_min_s": min(times),
        "time_max_s": max(times),
        "time_repeats": len(times),
        "peak_memory_bytes": peak_memory,
        "node_limit": "" if node_limit is None else node_limit,
        "time_limit_s": "" if time_limit is None else time_limit,
    }


def write_csv(rows: Iterable[dict[str, Any]], out_path: str) -> None:
    folder = os.path.dirname(out_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(
    cases: list[tuple[str, Any]],
    solver_classes: Iterable[type],
    out_path: Optional[str] = None,
    repeats: int = 5,
    node_limit: Optional[int] = None,
    time_limit: Optional[float] = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """cases: danh sách (tên màn, engine). Trả về các dòng kết quả, ghi CSV nếu có out_path."""
    solver_classes = list(solver_classes)
    rows: list[dict[str, Any]] = []
    for level_name, engine in cases:
        for solver_cls in solver_classes:
            try:
                row = benchmark_one(level_name, engine, solver_cls, repeats, node_limit, time_limit)
            except Exception as e:
                row = {c: "" for c in CSV_COLUMNS} | {
                    "level": level_name, "algorithm": solver_cls.name, "status": f"error:{type(e).__name__}"}
            rows.append(row)
            if verbose:
                print(
                    f"{level_name:<20} {row['algorithm']:<6} {row['status']:<12} "
                    f"len={row['solution_length']:<4} exp={row['expanded_nodes']:<8} "
                    f"t={row['time_median_s']:.4f}s mem={row['peak_memory_bytes']}",
                    flush=True,
                )
    if out_path is not None:
        write_csv(rows, out_path)
    return rows


def load_cases(patterns: list[str]) -> list[tuple[str, Any]]:
    """Nạp các file màn chơi JSON (hỗ trợ ký tự đại diện *) thành (tên, Engine)."""
    from src.core.engine import Engine
    from src.utils.json_loader import load_level

    paths: list[str] = []
    for pattern in patterns:
        paths.extend(sorted(glob.glob(pattern)))
    if not paths:
        raise SystemExit(f"Không tìm thấy file màn chơi nào khớp: {patterns}")
    return [
        (os.path.splitext(os.path.basename(p))[0], Engine(load_level(p))) for p in paths
    ]


def main(argv: Optional[list[str]] = None) -> None:
    registry = available_solvers()
    parser = argparse.ArgumentParser(description="Benchmark các solver Bloxorz, ghi CSV.")
    parser.add_argument("--levels", nargs="+", default=["levels/*.json"])
    parser.add_argument("--algorithms", default=",".join(registry))
    parser.add_argument("--repeats", type=int, default=5, help="số lần lặp lượt đo thời gian")
    parser.add_argument("--node-limit", type=int, default=None)
    parser.add_argument("--time-limit", type=float, default=None, help="giây")
    parser.add_argument("--out", default=os.path.join("experiments", "results", "benchmark.csv"))
    args = parser.parse_args(argv)

    names = [n.strip() for n in args.algorithms.split(",") if n.strip()]
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise SystemExit(f"Thuật toán chưa có: {unknown}. Hiện có: {list(registry)}")

    run_benchmark(
        load_cases(args.levels),
        [registry[n] for n in names],
        out_path=args.out,
        repeats=args.repeats,
        node_limit=args.node_limit,
        time_limit=args.time_limit,
        verbose=True,
    )
    print(f"Đã ghi {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()