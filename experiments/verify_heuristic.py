"""Kiểm chứng heuristic của A* bằng vét cạn (dùng cho mục "Kiểm chứng bằng thực nghiệm" của báo cáo).

Với mỗi màn:
  1. Duyệt MỌI trạng thái đạt tới được từ trạng thái đầu bằng engine.get_successors.
  2. Tính h*(s) = chi phí tối ưu thật từ s tới đích (Dijkstra ngược trên đồ thị vừa duyệt,
     chi phí là costs.step_cost).
  3. Admissible: h(s) <= h*(s) với mọi s có đường tới đích.
  4. Consistent: h(s) <= c(s, a, s') + h(s') với MỌI cạnh (s, s').
Bất kỳ vi phạm nào là một phản ví dụ; script thoát với mã 1.

Cách chạy (từ thư mục gốc của repo):
    python -m experiments.verify_heuristic                              # các màn trong levels/
    python -m experiments.verify_heuristic --random 300 --seed 7        # thêm 300 màn ngẫu nhiên
    python -m experiments.verify_heuristic --levels "levels/level0*.json" --state-cap 100000

Kết quả: bảng tóm tắt in ra màn hình, CSV từng màn (--out) và bảng LaTeX (--tex).
Màn có quá nhiều trạng thái (vượt --state-cap) bị bỏ qua và được đếm riêng.
"""
from __future__ import annotations

import argparse
import csv
import glob
import heapq
import itertools
import json
import math
import os
import random
import sys
import tempfile
from collections import defaultdict
from typing import Any, Optional

from src.core.engine import Engine
from src.solvers.costs import step_cost
from src.solvers.heuristics import heuristic
from src.utils.json_loader import load_level

EPS = 1e-9
CSV_COLUMNS = [
    "level", "source", "states", "edges", "has_solution",
    "admissible_violations", "consistent_violations", "h_start", "h_star_start",
]


def explore(engine: Any, cap: int):
    """Trả (tập trạng thái, danh sách cạnh (s, s', chi phí)); None nếu vượt cap trạng thái."""
    start = engine.initial_state()
    seen, stack, edges = {start}, [start], []
    while stack:
        s = stack.pop()
        for action, nxt in engine.get_successors(s):
            edges.append((s, nxt, step_cost(engine, s, action, nxt)))
            if nxt not in seen:
                if len(seen) >= cap:
                    return None, None
                seen.add(nxt)
                stack.append(nxt)
    return seen, edges


def optimal_cost_to_goal(engine: Any, seen, edges) -> dict:
    """h*(s) cho mọi s có đường tới đích (Dijkstra ngược từ các trạng thái đích)."""
    reverse: dict = {}
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


def check_level(name: str, source: str, engine: Any, cap: int) -> Optional[dict]:
    seen, edges = explore(engine, cap)
    if seen is None:
        return None
    h = {s: heuristic(engine, s) for s in seen}
    h_star = optimal_cost_to_goal(engine, seen, edges)

    adm = sum(1 for s, c in h_star.items() if h[s] > c + EPS)
    cons = sum(1 for s, n, c in edges if h[s] > c + h[n] + EPS)
    start = engine.initial_state()
    ratios = [h[s] / c for s, c in h_star.items() if 0 < c < math.inf and h[s] < math.inf]
    return {
        "level": name, "source": source, "states": len(seen), "edges": len(edges),
        "has_solution": start in h_star,
        "admissible_violations": adm, "consistent_violations": cons,
        "h_start": h[start], "h_star_start": h_star.get(start, math.inf),
        "_checked": len(h_star), "_ratios": ratios,
    }


# ---------------------------------------------------------------------------------------
# Sinh màn ngẫu nhiên hợp lệ (tái lập được bằng --seed)
# ---------------------------------------------------------------------------------------
def random_level(rng: random.Random, rows: int, cols: int) -> Optional[dict]:
    g = [["#" if rng.random() < 0.78 else "." for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if g[r][c] == "#" and rng.random() < 0.13:
                g[r][c] = "F"
    floor = [(r, c) for r in range(rows) for c in range(cols) if g[r][c] == "#"]
    if len(floor) < 6:
        return None
    s, goal = rng.sample(floor, 2)
    g[s[0]][s[1]], g[goal[0]][goal[1]] = "S", "G"

    holes = [(r, c) for r in range(rows) for c in range(cols) if g[r][c] == "."]
    rng.shuffle(holes)
    k = min(len(holes), rng.choice([0, 0, 1, 2, 3]))
    bridges = [{"id": i, "pos": list(holes[i]), "initial_open": rng.random() < 0.3} for i in range(k)]

    plain = [(r, c) for r in range(rows) for c in range(cols) if g[r][c] == "#"]
    rng.shuffle(plain)
    switches = []
    if k > 0:
        for _ in range(rng.choice([1, 1, 2])):
            if not plain:
                break
            pos = plain.pop()
            ids = rng.sample(range(k), rng.randint(1, k))
            switches.append({
                "pos": list(pos), "type": rng.choice(["soft", "heavy"]),
                "effect": {"mode": rng.choice(["toggle", "set_open", "set_close"]), "bridges": ids},
            })
    if rng.random() < 0.35 and len(plain) >= 5:
        pos = plain.pop()
        for _ in range(20):
            a, b = rng.sample(plain, 2)
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1:
                switches.append({"pos": list(pos), "type": "split", "split_targets": [list(a), list(b)]})
                break
    return {"name": "random", "grid": ["".join(r) for r in g], "bridges": bridges, "switches": switches}


# ---------------------------------------------------------------------------------------
# Báo cáo
# ---------------------------------------------------------------------------------------
def summarise(rows: list[dict], skipped: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for source in sorted({r["source"] for r in rows} | set(skipped)):
        rs = [r for r in rows if r["source"] == source]
        ratios = [x for r in rs for x in r["_ratios"]]
        out[source] = {
            "levels": len(rs), "solvable": sum(r["has_solution"] for r in rs),
            "skipped": skipped.get(source, 0),
            "states": sum(r["states"] for r in rs), "edges": sum(r["edges"] for r in rs),
            "checked": sum(r["_checked"] for r in rs),
            "adm": sum(r["admissible_violations"] for r in rs),
            "cons": sum(r["consistent_violations"] for r in rs),
            "mean_ratio": (sum(ratios) / len(ratios)) if ratios else float("nan"),
        }
    return out


def write_tex(summary: dict[str, dict], path: str) -> None:
    names = {"file": "Màn cố định trong \\texttt{levels/}", "random": "Màn ngẫu nhiên"}
    lines = [
        "% Sinh tự động bởi experiments/verify_heuristic.py, không sửa tay.",
        "\\begin{tabular}{lrrrrrr}",
        "\\hline",
        "Nguồn màn & Số màn & Có lời giải & Số trạng thái & Số cạnh & Vi phạm admissible & Vi phạm consistent \\\\",
        "\\hline",
    ]
    for source, s in summary.items():
        lines.append(
            f"{names.get(source, source)} & {s['levels']} & {s['solvable']} & {s['states']:,} & "
            f"{s['edges']:,} & {s['adm']} & {s['cons']} \\\\".replace(",", "\\,")
        )
    total = lambda k: sum(s[k] for s in summary.values())
    lines += [
        "\\hline",
        f"\\textbf{{Tổng}} & {total('levels')} & {total('solvable')} & {total('states'):,} & "
        f"{total('edges'):,} & {total('adm')} & {total('cons')} \\\\".replace(",", "\\,"),
        "\\hline",
        "\\end{tabular}",
    ]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--levels", default="levels/*.json", help="glob các file màn chơi")
    parser.add_argument("--random", type=int, default=0, help="số màn ngẫu nhiên cần thêm")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--state-cap", type=int, default=200_000, help="bỏ qua màn có nhiều trạng thái hơn")
    parser.add_argument("--out", default=os.path.join("experiments", "results", "heuristic_check.csv"))
    parser.add_argument("--tex", default=os.path.join("experiments", "results", "heuristic_check.tex"))
    args = parser.parse_args(argv)

    rows: list[dict] = []
    skipped: dict[str, int] = defaultdict(int)
    for path in sorted(glob.glob(args.levels)):
        name = os.path.splitext(os.path.basename(path))[0]
        row = check_level(name, "file", Engine(load_level(path)), args.state_cap)
        if row is None:
            skipped["file"] += 1
            print(f"bỏ qua {name}: vượt {args.state_cap} trạng thái")
        else:
            rows.append(row)

    rng, tmp, made, rejected = random.Random(args.seed), tempfile.mkdtemp(), 0, 0
    while made < args.random:
        data = random_level(rng, rng.randint(3, 6), rng.randint(4, 7))
        if data is None:
            continue
        path = os.path.join(tmp, "level.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        try:
            engine = Engine(load_level(path))
        except ValueError:
            rejected += 1          # màn sinh ra vi phạm luật của loader: bỏ qua, không tính
            continue
        row = check_level(f"random_{made:04d}", "random", engine, args.state_cap)
        made += 1
        if row is None:
            skipped["random"] += 1
        else:
            rows.append(row)

    if not rows:
        print("Không có màn nào để kiểm tra.", file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = summarise(rows, skipped)
    write_tex(summary, args.tex)
    print(f"{'nguồn':<8}{'màn':>6}{'có lời giải':>13}{'bỏ qua':>8}{'trạng thái':>12}{'cạnh':>10}"
          f"{'vi phạm adm':>13}{'vi phạm cons':>14}{'h/h* TB':>10}")
    for source, s in summary.items():
        print(f"{source:<8}{s['levels']:>6}{s['solvable']:>13}{s['skipped']:>8}{s['states']:>12,}{s['edges']:>10,}"
              f"{s['adm']:>13}{s['cons']:>14}{s['mean_ratio']:>10.3f}")
    if rejected:
        print(f"(đã bỏ {rejected} màn ngẫu nhiên bị loader từ chối)")
    print(f"\nĐã ghi {args.out} và {args.tex}")

    violations = sum(s["adm"] + s["cons"] for s in summary.values())
    if violations:
        worst = [r["level"] for r in rows if r["admissible_violations"] or r["consistent_violations"]][:5]
        print(f"\nCÓ {violations} VI PHẠM, ví dụ ở: {worst}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
