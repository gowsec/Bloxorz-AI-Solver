"""Benchmark các solver và ghi kết quả ra CSV (architecture v2, mục 6.3).

Cách đo (theo mục 6.3):
  * Lượt 1: chỉ đo thời gian (measure_memory=False), lặp `--repeats` lần, lấy trung vị.
  * Lượt 2: chỉ đo bộ nhớ đỉnh (tracemalloc), chạy riêng một lần.
  * Mỗi lời giải "solved" được phát lại trên engine để xác nhận (cột `valid`).
  * Sau mỗi màn, đối chiếu total_cost giữa các thuật toán (UCS là mốc tối ưu).

Ví dụ:
  python -m experiments.benchmark --repeats 5 --time-limit 30
"""

import argparse
import csv
import datetime
import gc
import glob
import importlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import traceback
from typing import Any, Iterable, Optional

CSV_COLUMNS = [
    "group",
    "level",
    "algorithm",
    "status",
    "valid",
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
    "note",
]

# Tên hiển thị thống nhất cho CSV, biểu đồ và báo cáo.
DISPLAY_NAMES = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "astar": "A*", "a_star": "A*"}

# Các status mà số liệu tìm kiếm có ý nghĩa đầy đủ.
COMPLETE_STATUSES = ("solved", "no_solution")


def display_name(solver_cls: type) -> str:
    raw = getattr(solver_cls, "name", solver_cls.__name__)
    return DISPLAY_NAMES.get(str(raw).lower(), str(raw))


def natural_key(text: str) -> list:
    """Sắp xếp tự nhiên: level2 đứng trước level10."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]


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


def validate(engine: Any, result: Any) -> bool:
    """Phát lại result.path trên engine; True nếu mọi nước hợp lệ và kết thúc ở goal."""
    from src.core.constants import Outcome

    if result.status != "solved":
        return False
    state = engine.initial_state()
    for action in result.path:
        state, outcome = engine.try_step(state, action)
        if outcome != Outcome.OK or state is None:
            return False
    return bool(engine.is_goal(state))


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def write_meta(out_path: str, args: argparse.Namespace, solver_names: list[str]) -> None:
    """Ghi cấu hình máy và tham số chạy ra file JSON bên cạnh CSV."""
    meta_path = os.path.splitext(out_path)[0] + "_meta.json"
    meta = {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_cores": os.cpu_count(),
        "python_version": sys.version,
        "git_commit": git_commit(),
        "levels": args.levels,
        "test_set": args.test_set,
        "algorithms": solver_names,
        "repeats": args.repeats,
        "time_limit": args.time_limit,
        "node_limit": args.node_limit,
        "memory_pass_time_limit": (args.time_limit * 5.0) if args.time_limit is not None else None,
        "notes": [
            "Thời gian lấy từ lượt measure_memory=False, trung vị của các lần lặp.",
            "Bộ nhớ là peak của tracemalloc (chỉ bộ nhớ Python theo dõi được), đo ở lượt riêng.",
            "Với timeout / node_limit, các cột số liệu để trống.",
        ],
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)


def _blank_row(group: str, level: str, algo: str, node_limit, time_limit) -> dict[str, Any]:
    row = {c: "" for c in CSV_COLUMNS}
    row.update({
        "group": group,
        "level": level,
        "algorithm": algo,
        "node_limit": "" if node_limit is None else node_limit,
        "time_limit_s": "" if time_limit is None else time_limit,
    })
    return row


def benchmark_one(
    level_name: str,
    group_name: str,
    engine: Any,
    solver_cls: type,
    repeats: int = 5,
    node_limit: Optional[int] = None,
    time_limit: Optional[float] = None,
) -> dict[str, Any]:
    """Chạy một cặp (màn, thuật toán) và trả về một dòng CSV."""
    row = _blank_row(group_name, level_name, display_name(solver_cls), node_limit, time_limit)
    notes: list[str] = []

    # ---- Lượt 1: thời gian, không tracemalloc ----
    times: list[float] = []
    result = None
    for _ in range(max(1, repeats)):
        gc.collect()
        res = solver_cls(engine, node_limit=node_limit, time_limit=time_limit).solve(
            measure_memory=False
        )
        result = res
        if res.status not in COMPLETE_STATUSES:
            break  # chạm giới hạn: không lặp tiếp
        times.append(res.search_time)

    status = result.status
    row["status"] = status

    # Chạm timeout / node_limit: số liệu chỉ là một phần, để trống.
    if status not in COMPLETE_STATUSES:
        row["time_repeats"] = 1
        return row

    row["time_median_s"] = statistics.median(times)
    row["time_min_s"] = min(times)
    row["time_max_s"] = max(times)
    row["time_repeats"] = len(times)
    row["solution_length"] = result.solution_length
    row["total_cost"] = result.total_cost
    row["expanded_nodes"] = result.expanded_nodes
    row["generated_nodes"] = result.generated_nodes
    row["max_frontier"] = result.max_frontier

    if status == "solved":
        ok = validate(engine, result)
        row["valid"] = ok
        if not ok:
            notes.append("INVALID_SOLUTION")

    # ---- Lượt 2: bộ nhớ, riêng biệt ----
    # Nới time_limit vì tracemalloc làm chậm, tránh timeout giả.
    gc.collect()
    mem_time_limit = (time_limit * 5.0) if time_limit is not None else None
    mem_result = solver_cls(engine, node_limit=node_limit, time_limit=mem_time_limit).solve(
        measure_memory=True
    )
    if mem_result.status == status:
        row["peak_memory_bytes"] = mem_result.peak_memory
    else:
        notes.append(f"mem_pass_status={mem_result.status}")

    row["note"] = ";".join(notes)
    return row


def cross_check(level_name: str, rows: list[dict[str, Any]]) -> None:
    """Đối chiếu total_cost giữa các thuật toán trên cùng một màn.

    UCS là mốc tối ưu: A* phải bằng UCS; BFS/DFS không được rẻ hơn UCS.
    Kết quả ghi vào cột `note` và in cảnh báo ra stderr.
    """
    solved = {r["algorithm"]: r for r in rows if r["status"] == "solved"}
    ucs = solved.get("UCS")
    if ucs is None:
        return
    base = ucs["total_cost"]
    for algo, r in solved.items():
        if algo == "UCS":
            continue
        cost = r["total_cost"]
        msg = None
        if algo == "A*" and not math.isclose(cost, base):
            msg = f"COST_MISMATCH_VS_UCS(A*={cost},UCS={base})"
        elif algo != "A*" and cost < base and not math.isclose(cost, base):
            msg = f"CHEAPER_THAN_UCS({algo}={cost},UCS={base})"
        if msg:
            r["note"] = ";".join(x for x in (r["note"], msg) if x)
            print(f"--> [CẢNH BÁO] Màn {level_name}: {msg}", file=sys.stderr)


def _format_verbose(row: dict[str, Any]) -> str:
    t = row["time_median_s"]
    t_str = f"{t:.4f}s" if isinstance(t, float) else "   -   "
    return (
        f"[{str(row['group'])[:8]:<8}] {row['level']:<12} {row['algorithm']:<4} "
        f"{row['status']:<12} valid={str(row['valid']):<5} len={row['solution_length']!s:<4} "
        f"exp={row['expanded_nodes']!s:<7} t={t_str} mem={row['peak_memory_bytes']}"
        + (f"  !{row['note']}" if row["note"] else "")
    )


def run_benchmark(
    cases: list[tuple[str, str, Any]],  # (level_name, group_name, engine)
    solver_classes: Iterable[type],
    out_path: str,
    repeats: int = 5,
    node_limit: Optional[int] = None,
    time_limit: Optional[float] = None,
    verbose: bool = False,
) -> None:
    solver_classes = list(solver_classes)

    folder = os.path.dirname(out_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        f.flush()

        for level_name, group_name, engine in cases:
            level_rows: list[dict[str, Any]] = []

            for solver_cls in solver_classes:
                try:
                    row = benchmark_one(
                        level_name, group_name, engine, solver_cls,
                        repeats, node_limit, time_limit,
                    )
                except Exception as exc:  # lỗi của một solver không làm sập cả lượt chạy
                    traceback.print_exc(file=sys.stderr)
                    row = _blank_row(
                        group_name, level_name, display_name(solver_cls), node_limit, time_limit
                    )
                    row["status"] = f"error:{type(exc).__name__}"
                    row["note"] = str(exc)[:200].replace("\n", " ")
                level_rows.append(row)

            # Đối chiếu chéo trước khi ghi để `note` có mặt trong CSV.
            cross_check(level_name, level_rows)
            for row in level_rows:
                writer.writerow(row)
                if verbose:
                    print(_format_verbose(row), flush=True)
            f.flush()


def load_cases(patterns: list[str], test_set_path: Optional[str]) -> list[tuple[str, str, Any]]:
    """Nạp các file màn chơi JSON thành (tên, nhóm, Engine)."""
    from src.core.engine import Engine
    from src.utils.json_loader import load_level

    # test_set.json có dạng {"Group 1": ["level01", "level02"], ...}
    level_groups: dict[str, str] = {}
    if test_set_path and os.path.exists(test_set_path):
        try:
            with open(test_set_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for group_name, levels in data.items():
                for lvl in levels:
                    level_groups[lvl] = group_name
        except Exception as exc:
            print(f"Không thể đọc test_set: {exc}", file=sys.stderr)
    elif test_set_path:
        print(f"Không thấy test_set: {test_set_path}", file=sys.stderr)

    paths: list[str] = []
    for pattern in patterns:
        paths.extend(glob.glob(pattern))
    paths = sorted(set(paths), key=lambda p: natural_key(os.path.basename(p)))
    if not paths:
        raise SystemExit(f"Không tìm thấy file màn chơi nào khớp: {patterns}")

    cases = []
    for p in paths:
        level_name = os.path.splitext(os.path.basename(p))[0]
        group_name = level_groups.get(level_name)
        if group_name is None:
            print(f"Cảnh báo: màn {level_name} không thuộc nhóm nào trong test_set", file=sys.stderr)
            group_name = "Unknown"
        cases.append((level_name, group_name, Engine(load_level(p))))
    return cases


def main(argv: Optional[list[str]] = None) -> None:
    registry = available_solvers()
    parser = argparse.ArgumentParser(description="Benchmark các solver Bloxorz, ghi CSV.")
    parser.add_argument("--levels", nargs="+", default=["levels/level*.json"])
    parser.add_argument("--test-set", type=str, default="experiments/test_set.json",
                        help="File JSON chia nhóm độ khó")
    parser.add_argument("--algorithms", default=",".join(registry),
                        help=f"Danh sách cách nhau bằng dấu phẩy. Hiện có: {','.join(registry)}")
    parser.add_argument("--repeats", type=int, default=5, help="Số lần lặp lượt đo thời gian")
    parser.add_argument("--node-limit", type=int, default=None)
    parser.add_argument("--time-limit", type=float, default=30.0, help="Giây")
    parser.add_argument("--out", default=None,
                        help="Đường dẫn CSV. Mặc định có timestamp để không ghi đè kết quả cũ")
    args = parser.parse_args(argv)

    if args.out is None:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.out = os.path.join("experiments", "results", f"benchmark_{stamp}.csv")

    names = [n.strip() for n in args.algorithms.split(",") if n.strip()]
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise SystemExit(f"Thuật toán chưa có: {unknown}. Hiện có: {list(registry)}")

    cases = load_cases(args.levels, args.test_set)
    write_meta(args.out, args, names)

    run_benchmark(
        cases,
        [registry[n] for n in names],
        out_path=args.out,
        repeats=args.repeats,
        node_limit=args.node_limit,
        time_limit=args.time_limit,
        verbose=True,
    )
    print(f"Đã ghi {args.out} và file metadata", file=sys.stderr)


if __name__ == "__main__":
    main()