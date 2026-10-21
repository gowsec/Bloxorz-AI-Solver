"""Heuristic cho A*: chi phí của bài toán đã NỚI LỎNG, tính trước bằng Dijkstra.

Bài toán nới lỏng R (chỉ giữ địa hình TĨNH):
  * Bỏ cầu và công tắc: mọi ô cầu coi như sàn (cầu có thể đang mở).
  * Giữ nguyên ô trống '.' vĩnh viễn, biên bàn, và luật "khối đứng không được trên ô dễ vỡ".
  * Mỗi nước lăn có chi phí đúng bằng roll_cost() (giống hệt costs.py).
Mọi nước đi thật đều là nước đi của R với cùng chi phí, nên chi phí tối ưu của R
là cận dưới của chi phí tối ưu thật.

Khối tách (công tắc split) là cách DUY NHẤT thoát khỏi R, nên xét thêm:
  h(s) = min( D_goal(s) , D_split(s) + SPLIT_MIN_REMAINING )
  * D_goal : chi phí ngắn nhất trong R đến việc ĐỨNG trên ô đích.
  * D_split: chi phí ngắn nhất trong R đến việc ĐỨNG trên một công tắc split.
  * SPLIT_MIN_REMAINING = 2*C_MIN: ở chế độ tách còn ít nhất 2 nước đi (một nước ghép
    thành khối nằm, một nước nữa để đứng lên ô đích).
Với SplitPose: h = SPLIT_MIN_REMAINING.

Chứng minh admissible và consistent: xem docs/heuristic_proof.md.
"""
from __future__ import annotations

import heapq
import itertools
import math

from src.core.board import SwitchType
from src.core.constants import Direction, Orientation
from src.core.move import move_block
from src.core.state import BlockPose, SplitPose, State, cells
from src.solvers.costs import C_MIN, FRAGILE_TILE, roll_cost

VOID_TILE = "."  # ký tự ô trống trong level.terrain
SPLIT_MIN_REMAINING = 2 * C_MIN


def _dijkstra(sources: dict, reverse_edges: dict) -> dict:
    """Dijkstra nhiều nguồn trên đồ thị ngược: dist[p] = chi phí nhỏ nhất đi từ p tới một nguồn."""
    dist = dict(sources)
    tie = itertools.count()
    heap = [(d, next(tie), node) for node, d in sources.items()]
    heapq.heapify(heap)
    while heap:
        d, _, node = heapq.heappop(heap)
        if d > dist.get(node, math.inf):
            continue
        for prev, cost in reverse_edges.get(node, ()):
            nd = d + cost
            if nd < dist.get(prev, math.inf):
                dist[prev] = nd
                heapq.heappush(heap, (nd, next(tie), prev))
    return dist


class HeuristicTable:
    """Bảng heuristic cho MỘT màn chơi. Tạo một lần, tra O(1) cho mỗi state."""

    def __init__(self, level):
        self.level = level
        poses = [p for p in self._all_poses() if self._supported(p)]
        pose_set = set(poses)

        # Đồ thị ngược của R: với mỗi nước p --d--> q hợp lệ, thêm cạnh ngược q <- p.
        reverse_edges: dict = {p: [] for p in poses}
        for p in poses:
            for d in Direction:
                q = move_block(p, d)
                if q in pose_set:
                    reverse_edges[q].append((p, roll_cost(level, q)))

        goal = BlockPose(level.goal[0], level.goal[1], Orientation.STANDING)
        self.goal_dist = _dijkstra({goal: 0.0}, reverse_edges)

        split_sources = {
            BlockPose(r, c, Orientation.STANDING): 0.0
            for (r, c), sw in level.switches.items()
            if sw.type is SwitchType.SPLIT
        }
        self.split_dist = _dijkstra(split_sources, reverse_edges) if split_sources else {}

    def _all_poses(self):
        for r in range(self.level.rows):
            for c in range(self.level.cols):
                for o in Orientation:
                    yield BlockPose(r, c, o)

    def _supported(self, pose) -> bool:
        """Pose có đứng vững xét riêng địa hình tĩnh (cầu coi như sàn)?"""
        lv = self.level
        for r, c in cells(pose):
            if not (0 <= r < lv.rows and 0 <= c < lv.cols):
                return False
            ch = lv.terrain[r][c]
            if ch == VOID_TILE and (r, c) not in lv.bridge_at:
                return False
            if ch == FRAGILE_TILE and pose.orient is Orientation.STANDING:
                return False
        return True

    def __call__(self, state: State) -> float:
        pose = state.pose
        if isinstance(pose, SplitPose):
            return SPLIT_MIN_REMAINING
        to_goal = self.goal_dist.get(pose, math.inf)
        to_split = self.split_dist.get(pose, math.inf) + SPLIT_MIN_REMAINING
        return min(to_goal, to_split)


def heuristic(engine, state: State) -> float:
    """Interface theo mục 6.5. Bảng được tính một lần cho mỗi engine rồi lưu lại."""
    table = getattr(engine, "_heuristic_table", None)
    if table is None:
        table = HeuristicTable(engine.level)
        engine._heuristic_table = table
    return table(state)
